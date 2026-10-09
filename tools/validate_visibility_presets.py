#!/usr/bin/env python3
"""Validate pruned GLB scenes directly against serialized nodes and named pairs."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ps2_sections


def expected(data,moving):
    cursor=4;count=struct.unpack_from('<I',data,cursor)[0];cursor+=4+4*count
    count=struct.unpack_from('<I',data,cursor)[0];labels=[]
    for i in range(count):
        o=struct.unpack_from('<I',data,cursor+4+i*4)[0];labels.append(data[o:data.index(b'\0',o)].decode('ascii'))
    spans=ps2_sections.parse(data)['later']['records'][0]['nodes_2c'];rows=[];roots=[];stack=[]
    for s in spans:
        while len(stack)>s['depth']:stack.pop()
        identifier=struct.unpack_from('<I',data,s['offset'])[0]
        row={'offset':s['offset'],'geometry':identifier,'translation':list(struct.unpack_from('<3f',data,s['offset']+8)),
             'names':[],'children':[],'mutable':False}
        if stack:rows[stack[-1]]['children'].append(len(rows))
        else:roots.append(len(rows))
        stack.append(len(rows));rows.append(row)
    for s,r in zip(spans,rows):
        for i in range(s['pairs']['count']):
            name,target=struct.unpack_from('<II',data,s['pairs']['offset']+i*8)
            rows[r['children'][target&65535]]['names'].append(labels[name&65535])
        for i in r['children'][:s['pairs']['count']]:rows[i]['mutable']=True
    # Postorder geometry presence is descriptor bit14 from 001236b0.
    for r in reversed(rows):r['contains']=bool(r['geometry']&65535) or any(rows[c]['contains'] for c in r['children'])
    named={'WHEEL_STATIC':not moving,'WHEEL_MOVING':moving,'BRAKE_LIGHTS_ON':False,
           'BRAKE_LIGHTS_OFF':True,'REVERSE_LIGHTS_ON':False,'REVERSE_LIGHTS_OFF':True}
    named.update({f'{side}_EXHAUST_{i}':False for side in ['LEFT','RIGHT'] for i in range(1,5)})
    for r in rows:
        r['visible']=r['contains'] if r['mutable'] else True
        values={named[n] for n in r['names'] if n in named}
        if len(values)>1:raise ValueError('conflicting source aliases')
        if values:r['visible']=values.pop()
    return rows,roots


def check(data,doc):
    matched=0
    record_mesh={n['extras']['geometryRecord']:n['mesh'] for n in doc['nodes']
                 if not n.get('extras',{}).get('assemblyCandidate') and 'mesh' in n}
    for moving,name in [(False,'low_speed'),(True,'moving_wheels')]:
        rows,roots=expected(data,moving)
        scenes=[s for s in doc['scenes'] if s.get('extras',{}).get('visibilityPreset')==name]
        if len(scenes)!=len(roots):raise ValueError('preset root count mismatch')
        def visit(source_index,node_index):
            nonlocal matched
            r=rows[source_index];n=doc['nodes'][node_index];e=n['extras']
            if not r['visible'] or e['serializedNodeOffset']!=r['offset'] or e['geometryRecord']!=r['geometry'] or n.get('translation')!=r['translation']:
                raise ValueError('preset node differs from source or visibility')
            if e['sourceNames']!=r['names'] or e['runtimeMutable']!=r['mutable'] or e['visibilityPreset']!=name:raise ValueError('preset node metadata differs')
            if r['geometry']:
                if n.get('mesh')!=record_mesh[r['geometry']]:raise ValueError('preset mesh differs')
            elif 'mesh' in n:raise ValueError('null source geometry has mesh')
            wanted=[c for c in r['children'] if rows[c]['visible']];actual=n.get('children',[])
            if len(wanted)!=len(actual):raise ValueError('preset child count differs')
            matched+=1
            for a,b in zip(wanted,actual):visit(a,b)
        for tree,scene in enumerate(scenes):
            if scene['extras']['sourceTree']!=tree:raise ValueError('preset source tree differs')
            inputs={'wheelStaticBit':not moving,'wheelMovingBit':moving,
                    'wheelGlobalOverride':0,'brakeLightsOn':False,
                    'reverseLightsOn':False,'exhaustOn':False,
                    'transforms':'original serialized values'}
            if scene['extras'].get('stateInputs')!=inputs:raise ValueError('preset state inputs differ')
            r=roots[tree]
            if not rows[r]['visible']:
                if scene['nodes']:raise ValueError('hidden root retained')
            else:
                if len(scene['nodes'])!=1:raise ValueError('preset root missing')
                visit(r,scene['nodes'][0])
    return matched


def main():
    entries=json.loads((ROOT/'dealership/public/ford-racing-2/index.json').read_text())['cars'];results=[];negative={}
    for c in entries:
        raw=(ROOT/'dealership/public/ford-racing-2'/c['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=c['sha256']:raise ValueError('GLB index identity differs')
        length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length])
        data=next((ROOT/'ford-racing-2/cars'/c['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(data).hexdigest()!=doc['extras']['originalModelSha256']:raise ValueError('original model identity differs')
        checked=check(data,doc);results.append({'car':c['code'],'glb_sha256':c['sha256'],'preset_nodes':checked})
        if not negative:
            bad=copy.deepcopy(doc);scene=next(s for s in bad['scenes'] if s.get('extras',{}).get('visibilityPreset')=='low_speed')
            bad['nodes'][scene['nodes'][0]]['translation'][0]+=0.25
            try:check(data,bad)
            except ValueError:negative['changed_preset_translation_rejected']=True
            else:raise ValueError('changed preset translation accepted')
            bad=copy.deepcopy(doc);scene=next(s for s in bad['scenes'] if s.get('extras',{}).get('visibilityPreset')=='low_speed')
            scene['nodes']=[]
            try:check(data,bad)
            except ValueError:negative['missing_visible_root_rejected']=True
            else:raise ValueError('missing preset root accepted')
            bad=copy.deepcopy(doc);scene=next(s for s in bad['scenes'] if s.get('extras',{}).get('visibilityPreset')=='moving_wheels')
            scene['extras']['stateInputs']['wheelGlobalOverride']=1
            try:check(data,bad)
            except ValueError:negative['contradictory_wheel_override_rejected']=True
            else:raise ValueError('contradictory wheel override accepted')
    receipt={'cars':len(results),'preset_scenes':len(results)*10,'preset_nodes_checked':sum(r['preset_nodes'] for r in results),
             'negative':negative,'failures':0,'results':results,
             'limits':'Original node, ownership and explicit visibility-input parity; not animated state or shader equivalence.'}
    (ROOT/'research/evidence/continuation/source-refresh/visibility-export-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='results'}))
if __name__=='__main__':main()
