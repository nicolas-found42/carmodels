#!/usr/bin/env python3
"""Export original packed-coordinate candidates as GLB, one mesh per record.

Coordinates: signed16 * per-axis max(abs(bbox endpoints)) / 16384.
Candidate attributes: normalize signed8 XYZ as normals, signed16 UV / 2048,
third halfword as texture index, triangle strip with W=1 suppressing draw.
Named-part ownership is source-traced; observed state selection and winding remain open.
The GLB extras preserve these limits; this is not a finished assembled car.
"""
import argparse
from array import array
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'research/evidence/original-recovery'


def pack_array(values, code):
    a=array(code,values)
    if sys.byteorder!='little': a.byteswap()
    return a.tobytes()


def build(car, data):
    binary=bytearray()
    doc={'asset':{'version':'2.0','generator':'FR2 bounded coordinate experiment'},
         'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'meshes':[],'accessors':[],
         'bufferViews':[],'buffers':[],'materials':[],'images':[],'textures':[],
         'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':10497,'wrapT':10497}],
         'extras':{'car':car['code'],'originalModelSha256':car['sha256'],
                   'status':'Original coordinate candidates with independent records and translated tree candidates.',
                   'limits':['Source-named ownership joined; runtime state and observed LOD selection unresolved; tree scenes retain all states.',
                             'Normals, UV, texture-index and ADC triangle semantics are candidate interpretations.',
                             'Display alpha min(255,2*a); glTF shading differs from original GS rendering.']}}
    def view(payload,target=None):
        binary.extend(b'\0'*((-len(binary))%4));i=len(doc['bufferViews'])
        row={'buffer':0,'byteOffset':len(binary),'byteLength':len(payload)}
        if target:row['target']=target
        doc['bufferViews'].append(row);binary.extend(payload);return i
    def accessor(values,width,kind='f',bounds=False):
        payload=pack_array(values,kind)
        index=len(doc['accessors']); row={'bufferView':view(payload,34963 if kind=='I' else 34962),
                                       'componentType':5125 if kind=='I' else 5126,
                                       'count':len(values)//width,'type':{1:'SCALAR',2:'VEC2',3:'VEC3'}[width]}
        if bounds:
            stored=[v[0] for v in struct.iter_unpack('<f',payload)]
            row['min']=[min(stored[j::width]) for j in range(width)]
            row['max']=[max(stored[j::width]) for j in range(width)]
        doc['accessors'].append(row);return index
    for t in car['textures']:
        image=len(doc['images']);doc['images'].append({'bufferView':view((EVIDENCE/t['png']).read_bytes()),'mimeType':'image/png','name':t['name']})
        doc['textures'].append({'sampler':0,'source':image})
        doc['materials'].append({'name':t['name'],'doubleSided':True,
                                 'pbrMetallicRoughness':{'baseColorTexture':{'index':image},'metallicFactor':0,'roughnessFactor':1}})
    doc['materials'].append({'name':'Untextured candidate','doubleSided':True,
                             'pbrMetallicRoughness':{'baseColorFactor':[.65,.68,.72,1],'metallicFactor':0,'roughnessFactor':1}})
    table=car['geometry']['table'];cursor=0; stats=Counter(); records=[]
    for record,pair in enumerate(car['geometry']['group_header_counts']):
        bounds=struct.unpack_from('<6f',data,table['offset']+record*52+4)
        scale=[max(abs(bounds[2*j]),abs(bounds[2*j+1]))/16384 for j in range(3)]
        headers=car['geometry']['headers'][cursor:cursor+sum(pair)];cursor+=sum(pair);primitives=[];triangle_count=0
        for hi,h in enumerate(headers):
            n=h['count'];p=h['planes']['six_byte']; raw=list(struct.iter_unpack('<3h',data[p['offset']:p['end']]))
            if len(raw)!=n:raise ValueError('sample count mismatch')
            positions=[v[j]*scale[j] for v in raw for j in range(3)]
            p=h['planes']['four_byte']; packed=list(struct.iter_unpack('<4b',data[p['offset']:p['end']]))
            if len(packed)!=n:raise ValueError('attribute count mismatch')
            normals=[]
            for x,y,z,w in packed:
                length=math.sqrt(x*x+y*y+z*z)
                normals.extend([x/length,y/length,z/length] if length else [0,1,0])
            indices=[]
            for v in range(2,n):
                if packed[v][3]!=0:stats['adc_suppressed']+=1;continue
                tri=[v-2,v-1,v] if v%2==0 else [v-1,v-2,v]
                if len({raw[k] for k in tri})<3:stats['degenerate_triangles']+=1;continue
                indices.extend(tri)
            if not indices:continue
            attrs={'POSITION':accessor(positions,3,bounds=True),'NORMAL':accessor(normals,3)}
            material=len(car['textures'])
            if h['third']!=65535:
                if not 0<=h['third']<len(car['textures']):raise ValueError('candidate texture index exceeds library')
                p=h['planes']['third_four_byte'];uvs=list(struct.iter_unpack('<2h',data[p['offset']:p['end']]))
                if len(uvs)!=n:raise ValueError('UV count mismatch')
                attrs['TEXCOORD_0']=accessor([component/2048 for uv in uvs for component in uv],2)
                material=h['third']
            primitives.append({'attributes':attrs,'indices':accessor(indices,1,'I'),'mode':4,'material':material,
                               'extras':{'headerOffset':h['offset'],'flags':h['flags'],'count':n,'third':h['third'],
                                         'group':0 if hi<pair[0] else 1,'candidateSemantics':True}})
            stats['vertices']+=n;stats['triangles']+=len(indices)//3;triangle_count+=len(indices)//3
        if primitives:
            mesh=len(doc['meshes']);doc['meshes'].append({'name':f'record_{record:03d}','primitives':primitives})
            node=len(doc['nodes']);doc['nodes'].append({'name':f'record_{record:03d}','mesh':mesh,
                                                       'extras':{'geometryRecord':record,'serializedBounds':list(bounds)}})
            doc['scenes'][0]['nodes'].append(node)
            records.append({'record':record,'node':node,'bounds':list(bounds),'triangles':triangle_count})
    # Additional scenes preserve the serialized hierarchy without choosing a
    # moving/static wheel, light or LOD state. Zero rotation fields are checked.
    sys.path.insert(0,str(ROOT.parents[1]/'reverse-engineering/tools'))
    import ps2_sections
    parsed=ps2_sections.parse(data)
    from recover_assembly_semantics import join
    ownership=join(data,parsed)
    owned_nodes={n['offset']:n for record in ownership['records'] for n in record['nodes']}
    doc['extras']['sourceNameTables']=ownership['name_tables']
    doc['extras']['distanceThresholds']=ownership['records'][0]['thresholds']
    geometry_mesh={n['extras']['geometryRecord']:n['mesh'] for n in doc['nodes']}
    assemblies=[]; stack=[]; current_root=None
    for row in parsed['later']['records'][0]['nodes_2c']:
        identifier,flags,*floats=struct.unpack_from('<2I6f',data,row['offset'])
        if any(floats[3:]):raise ValueError('nonzero node rotation is outside candidate assembly profile')
        if identifier and identifier not in geometry_mesh:raise ValueError('node references missing geometry')
        depth=row['depth']; node={'name':f'tree_node_{row["offset"]:x}',
                                'translation':floats[:3],
                                'extras':{'serializedNodeOffset':row['offset'],'geometryRecord':identifier,
                                          'assemblyCandidate':True,'flags':flags,'runtimeSelectionUnresolved':True}}
        owned=owned_nodes[row['offset']]
        if owned['source_names']:
            node['name']=' / '.join(owned['source_names'])+'_'+hex(row['offset'])
        node['extras'].update({'sourceNames':owned['source_names'],
                              'sourceNamedPairs':owned['pairs'],
                              'runtimeMutable':owned['runtime_mutable']})
        if identifier:node['mesh']=geometry_mesh[identifier]
        ni=len(doc['nodes']);doc['nodes'].append(node)
        while len(stack)>depth:stack.pop()
        if depth==0:
            current_root=ni;assemblies.append({'tree':len(assemblies),'rootNode':ni})
            doc['scenes'].append({'name':f'Candidate tree {len(assemblies)-1} — all states','nodes':[ni],
                                  'extras':{'status':'Serialized translation hierarchy; all alternative states retained.'}})
        else:
            if not stack:raise ValueError('missing candidate parent')
            doc['nodes'][stack[-1]].setdefault('children',[]).append(ni)
        stack.append(ni)
    if assemblies:doc['scene']=1
    doc['buffers']=[{'byteLength':len(binary)}]
    j=json.dumps(doc,separators=(',',':'),allow_nan=False).encode();j+=b' '*((-len(j))%4)
    binary.extend(b'\0'*((-len(binary))%4))
    glb=struct.pack('<3I',0x46546c67,2,12+8+len(j)+8+len(binary))+struct.pack('<2I',len(j),0x4e4f534a)+j+struct.pack('<2I',len(binary),0x004e4942)+binary
    return glb,records,dict(stats),assemblies


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'viewer/public/recovered')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    census=json.loads((EVIDENCE/'car-asset-census.json').read_text());entries=[]
    for car in census['cars']:
        data=next((ROOT/'reference/ford/cars'/car['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(data).hexdigest()!=car['sha256']:raise ValueError('model hash changed')
        glb,records,stats,assemblies=build(car,data);filename=car['code']+'.glb';(args.output/filename).write_bytes(glb)
        entries.append({'code':car['code'],'file':filename,'sha256':hashlib.sha256(glb).hexdigest(),'bytes':len(glb),'records':records,'assemblies':assemblies,'stats':stats})
        print(json.dumps({'car':car['code'],**stats}),flush=True)
    index={'status':'Experimental geometry: bounds-validated positions, tentative topology/normals/UV/materials and translated trees retaining all runtime states.','cars':entries}
    (args.output/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    (EVIDENCE/'geometry-export-index.json').write_text(json.dumps(index,indent=2)+'\n')


if __name__=='__main__':main()
