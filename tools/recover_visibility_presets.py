#!/usr/bin/env python3
"""Source-derived post-update visibility presets; no inferred runtime transforms."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from recover_assembly_semantics import join

ROOT=Path(__file__).resolve().parents[1]
RE=ROOT.parents[1]/'reverse-engineering'
EXPORT=RE/'.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po'
OUT=ROOT/'research/evidence/continuation/source-refresh/visibility-presets.json'


def preset(record, moving=False):
    nodes=record['nodes'];contains={}
    def geometry_below(i):
        n=nodes[i];child=[geometry_below(c) for c in n['children']]
        contains[i]=bool(n['geometry_record']&65535) or any(child)
        return contains[i]
    for r in record['roots']:geometry_below(r)
    named={'WHEEL_STATIC':not moving,'WHEEL_MOVING':moving,
           'BRAKE_LIGHTS_ON':False,'BRAKE_LIGHTS_OFF':True,
           'REVERSE_LIGHTS_ON':False,'REVERSE_LIGHTS_OFF':True}
    for side in ['LEFT','RIGHT']:
        for i in range(1,5):named[f'{side}_EXHAUST_{i}']=False
    states=[]
    for n in nodes:
        value=contains[n['index']] if n['runtime_mutable'] else True
        overrides={named[x] for x in n['source_names'] if x in named}
        if len(overrides)>1:raise ValueError('conflicting named visibility setters')
        if overrides:
            if not n['runtime_mutable']:raise ValueError('named visibility setter targets immutable node')
            value=overrides.pop()
        states.append({'offset':n['offset'],'mutable':n['runtime_mutable'],
                       'constructor_contains_geometry':contains[n['index']],
                       'local_visible':value,'names':n['source_names']})
    def visit(i,ancestor):
        s=states[i];s['visible_with_ancestors']=ancestor and s['local_visible']
        for c in nodes[i]['children']:visit(c,s['visible_with_ancestors'])
    for r in record['roots']:visit(r,True)
    return states


def main():
    import sys
    sys.path.insert(0,str(RE/'tools'));import ps2_sections
    elf=(RE/'games/ford-racing-2/extracted/SLES_517.05').read_bytes()
    invpath=EXPORT/'inventory.json';inv=json.loads(invpath.read_text())
    identity=json.loads((OUT.parent/'refresh-identity.json').read_text())
    if hashlib.sha256(invpath.read_bytes()).hexdigest()!=identity['inventory_sha256'] or hashlib.sha256(elf).hexdigest()!=identity['executable_sha256']:raise ValueError('source identity changed')
    phoff=struct.unpack_from('<I',elf,28)[0];stride,count=struct.unpack_from('<HH',elf,42)
    loads=[struct.unpack_from('<8I',elf,phoff+i*stride) for i in range(count)]
    def offset(va,size):
        segments=[l for l in loads if l[0]==1 and l[2]<=va and va+size<=l[2]+l[4]]
        if len(segments)!=1:raise ValueError('ambiguous ELF mapping')
        l=segments[0];return l[1]+va-l[2]
    pins=[];instructions=0
    for entry in ['001208d0','00123590','001236b0','001217f8','0019b900','0019bfe0','0019c680','0019ecd8','0019a7b8','0019a1b8']:
        f=next(f for f in inv['functions'] if f['entry']==entry)
        for ins in f['instructions']:
            payload=bytes.fromhex(ins['bytes']);o=offset(int(ins['address'],16),len(payload))
            if elf[o:o+len(payload)]!=payload:raise ValueError('instruction differs from ELF')
            instructions+=1
        p=EXPORT/'decompilation/functions'/f'{entry}.c'
        pins.append({'entry':entry,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'instructions_checked':len(f['instructions'])})
    strings={}
    for va,expected in [(0x261600,'WHEEL_STATIC'),(0x261610,'WHEEL_MOVING'),(0x2619a0,'BRAKE_LIGHTS_ON'),(0x2619b0,'BRAKE_LIGHTS_OFF'),(0x2619c8,'REVERSE_LIGHTS_ON'),(0x2619e0,'REVERSE_LIGHTS_OFF'),(0x2619f8,'LEFT_EXHAUST_%d'),(0x261a08,'RIGHT_EXHAUST_%d')]:
        o=offset(va,len(expected)+1)
        if elf[o:o+len(expected)+1]!=expected.encode()+b'\0':raise ValueError('source selector string differs')
        strings[hex(va)]=expected
    census=json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text());cars=[];counts=Counter()
    for c in census['cars']:
        data=next((ROOT/'reference/ford/cars'/c['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(data).hexdigest()!=c['sha256']:raise ValueError('model identity changed')
        assembly=join(data,ps2_sections.parse(data));record=assembly['records'][0]
        low=preset(record);fast=preset(record,True)
        for s in low:counts['mutable_nodes']+=s['mutable'];counts['locally_hidden_nodes']+=not s['local_visible']
        cars.append({'car':c['code'],'source_sha256':c['sha256'],'low_speed':low,'moving_wheels':fast})
    initial=ROOT/'research/evidence/continuation/runtime/linux/race95-instance-states.json'
    if not initial.exists():initial=ROOT/'research/evidence/continuation/runtime/race95-instance-states.json'
    captured=json.loads(initial.read_text());rows=captured.get('cars',captured.get('results'));checks=[];descriptor_checks=[]
    memory_path=initial.with_name('race95-eeMemory.bin');memory=memory_path.read_bytes()
    if hashlib.sha256(memory).hexdigest()!=captured['memory_sha256']:raise ValueError('runtime memory changed')
    if rows is None:raise ValueError('unknown capture schema')
    for c in rows:
        expected={s['offset']:s for s in next(x for x in cars if x['car']==c['car'])['low_speed']}
        for e in c['entities']:
            for s in e['states']:
                want=expected[s['source_node_offset']]['constructor_contains_geometry']
                actual=bool(struct.unpack_from('<I',memory,s['runtime_node']+4)[0]&0x4000)
                descriptor_checks.append({'car':c['car'],'offset':s['source_node_offset'],'expected':want,'actual':actual,'pass':want==actual})
                if s['mutable']:
                    want=expected[s['source_node_offset']]['local_visible']
                    checks.append({'car':c['car'],'offset':s['source_node_offset'],'expected':int(want),'actual':s['visibility_bit'],'pass':int(want)==s['visibility_bit']})
    mismatches=[c for c in checks if not c['pass']]
    descriptor_mismatches=[c for c in descriptor_checks if not c['pass']]
    result={'schema':'fr2-source-visibility-presets/v1','source_head':identity['source_head'],
            'executable_sha256':identity['executable_sha256'],'pins':pins,'source_strings':strings,
            'contract':'Constructor descriptor bit 14 is recursively geometry ID low16 != 0 or any child. Mutable instance bit0 copies bit14. Named light/exhaust setters then apply explicit initial values; wheel update sets STATIC to param6&1, MOVING to ~param6&1 (global override forces STATIC). The low-speed preset uses param6=1, lights off, exhaust off; moving-wheels uses param6=0 and global override=0.',
            'limits':['These are explicit source-derived state inputs, not an assertion that every captured frame uses this state.',
                      'Translations/rotations remain original serialized values; suspension, animated transforms, live LOD and shading are separate.',
                      'Runtime comparison proves local visibility for six loaded cars in race95, not their executed draw calls.'],
            'instructions_checked':instructions,'cars':cars,'counts':dict(counts),
            'race95_comparison':{'capture_path':str(initial.relative_to(ROOT)),'sha256':hashlib.sha256(initial.read_bytes()).hexdigest(),
                                'ee_memory_sha256':captured['memory_sha256'],'mutable_states':len(checks),'mismatches':mismatches,'checks':checks,
                                'descriptor_geometry_bits':len(descriptor_checks),'descriptor_mismatches':descriptor_mismatches,'descriptor_checks':descriptor_checks}}
    OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'cars':len(cars),'instructions_checked':instructions,'counts':dict(counts),'runtime_states':len(checks),'runtime_mismatches':len(mismatches)}))
    if mismatches or descriptor_mismatches:raise ValueError('source preset differs from observed initial runtime states')

if __name__=='__main__':main()
