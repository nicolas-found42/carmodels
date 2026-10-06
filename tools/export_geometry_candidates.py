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
    contract_path=ROOT/'research/evidence/continuation/source-refresh/texture-variant-contract.json'
    contract=json.loads(contract_path.read_text())
    census_path=EVIDENCE/'car-asset-census.json'
    if hashlib.sha256(census_path.read_bytes()).hexdigest()!=contract['census_sha256']:raise ValueError('variant census changed')
    variant=next(v for v in contract['cars'] if v['car']==car['code'])
    if variant['source_sha256']!=car['sha256']:raise ValueError('variant car identity differs')
    material_path=ROOT/'research/evidence/continuation/source-refresh/material-header-contract.json'
    material_contract=json.loads(material_path.read_text())
    material_car=next(c for c in material_contract['cars'] if c['car']==car['code'])
    if material_car['source_sha256']!=car['sha256']:raise ValueError('material source differs')
    material_headers={h['offset']:h for h in material_car['headers']}
    binary=bytearray()
    doc={'asset':{'version':'2.0','generator':'FR2 bounded coordinate experiment'},
         'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'meshes':[],'accessors':[],
         'bufferViews':[],'buffers':[],'materials':[],'images':[],'textures':[],
         'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':10497,'wrapT':10497}],
         'extras':{'car':car['code'],'originalModelSha256':car['sha256'],
                   'status':'Original coordinate candidates with independent records and translated tree candidates.',
                   'limits':['Source-named ownership joined; runtime state and observed LOD selection unresolved; tree scenes retain all states.',
                             'Normals, UV, texture-index and ADC triangle semantics are candidate interpretations.',
                             'Display alpha min(255,2*a); glTF shading differs from original GS rendering.',
                             'Untextured headers use their stored Header colour with GS-scale alpha, opacity alpha/128 below 128; the lane reading is a candidate, not proven shading.']}}
    doc['extras']['textureVariantContractSha256']=hashlib.sha256(contract_path.read_bytes()).hexdigest()
    doc['extras']['textureSelectorIds']=variant['complete_selectors']
    doc['extras']['materialHeaderContractSha256']=hashlib.sha256(material_path.read_bytes()).hexdigest()
    # Untextured headers draw with their own stored Header colour (labelled candidate:
    # it matches the captured draw's RGBA but is not proven for every lane). Alpha is the
    # GS 0..128 scale, so stored alpha <128 blends with opacity alpha/128 (0x80 = 1.0).
    untextured_colours=sorted({h['base_color_word'] for h in material_headers.values()
                               if h['texture_index']==65535})
    untextured_material={}
    for colour in untextured_colours:
        rgba=material_headers[next(k for k,v in material_headers.items()
                                   if v['texture_index']==65535 and v['base_color_word']==colour)]['base_color_rgba_unscaled']
        alpha=rgba[3]
        material={'name':'Header untextured '+colour,'doubleSided':True,
                  'pbrMetallicRoughness':{'baseColorFactor':[c/255 for c in rgba[:3]]+[min(1.0,alpha/128)],
                                          'metallicFactor':0,'roughnessFactor':1}}
        if alpha<128:
            material['alphaMode']='BLEND'
        untextured_material[colour]=len(doc['materials']);doc['materials'].append(material)
    if variant['variants']:
        doc['extensionsUsed']=['KHR_materials_variants']
        doc['extensions']={'KHR_materials_variants':{'variants':[{'name':f'Original selector {v["selector"]}','extras':{'originalSelector':v['selector']}} for v in variant['variants']]}}
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
            material=untextured_material[material_headers[h['offset']]['base_color_word']] \
                if h['third']==65535 else None
            if h['third']!=65535:
                if not 0<=h['third']<len(car['textures']):raise ValueError('candidate texture index exceeds library')
                p=h['planes']['third_four_byte'];uvs=list(struct.iter_unpack('<2h',data[p['offset']:p['end']]))
                if len(uvs)!=n:raise ValueError('UV count mismatch')
                attrs['TEXCOORD_0']=accessor([component/2048 for uv in uvs for component in uv],2)
                material=h['third']
            primitives.append({'attributes':attrs,'indices':accessor(indices,1,'I'),'mode':4,'material':material,
                               'extras':{'headerOffset':h['offset'],'flags':h['flags'],'count':n,'third':h['third'],
                                         'group':0 if hi<pair[0] else 1,'candidateSemantics':True}})
            if str(h['third']) in (variant['variants'][0]['material_remap'] if variant['variants'] else {}):
                primitives[-1]['extensions']={'KHR_materials_variants':{'mappings':[{'material':v['material_remap'][str(h['third'])],'variants':[vi]} for vi,v in enumerate(variant['variants'])]}}
            stats['vertices']+=n;stats['triangles']+=len(indices)//3;triangle_count+=len(indices)//3
        if primitives:
            mesh=len(doc['meshes']);doc['meshes'].append({'name':f'record_{record:03d}','primitives':primitives})
            node=len(doc['nodes']);doc['nodes'].append({'name':f'record_{record:03d}','mesh':mesh,
                                                       'extras':{'geometryRecord':record,'serializedBounds':list(bounds)}})
            doc['scenes'][0]['nodes'].append(node)
            records.append({'record':record,'node':node,'bounds':list(bounds),'triangles':triangle_count})
    # Additional scenes preserve the serialized hierarchy without choosing a
    # moving/static wheel, light or LOD state. Zero rotation fields are checked.
    sys.path.insert(0,str(ROOT/'tools'))
    import ps2_sections
    parsed=ps2_sections.parse(data)
    from recover_assembly_semantics import join
    ownership=join(data,parsed)
    owned_nodes={n['offset']:n for record in ownership['records'] for n in record['nodes']}
    doc['extras']['sourceNameTables']=ownership['name_tables']
    doc['extras']['distanceThresholds']=ownership['records'][0]['thresholds']
    geometry_mesh={n['extras']['geometryRecord']:n['mesh'] for n in doc['nodes']}
    assemblies=[]; stack=[]
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
            assemblies.append({'tree':len(assemblies),'rootNode':ni})
            doc['scenes'].append({'name':f'Candidate tree {len(assemblies)-1} — all states','nodes':[ni],
                                  'extras':{'status':'Serialized translation hierarchy; all alternative states retained.'}})
        else:
            if not stack:raise ValueError('missing candidate parent')
            doc['nodes'][stack[-1]].setdefault('children',[]).append(ni)
        stack.append(ni)
    if assemblies:doc['scene']=1
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            primitive['extras']['originalMaterialHeader']=material_headers[primitive['extras']['headerOffset']]
    # Standard glTF scenes encode explicit source-derived visibility inputs.
    # Original all-state trees remain intact; pruned clones share mesh buffers.
    visibility_path=ROOT/'research/evidence/continuation/source-refresh/visibility-presets.json'
    visibility=json.loads(visibility_path.read_text())
    state_car=next(c for c in visibility['cars'] if c['car']==car['code'])
    if state_car['source_sha256']!=car['sha256']:raise ValueError('visibility source differs')
    doc['extras']['visibilityContractSha256']=hashlib.sha256(visibility_path.read_bytes()).hexdigest()
    import copy
    for preset_name,label in [('low_speed','Low-speed wheels, lights off'),('moving_wheels','Moving wheels, lights off')]:
        states={s['offset']:s for s in state_car[preset_name]}
        def clone_visible(index):
            source=doc['nodes'][index];offset=source['extras']['serializedNodeOffset']
            if not states[offset]['local_visible']:return None
            node=copy.deepcopy(source);node.pop('children',None)
            node['extras']['visibilityPreset']=preset_name
            node['extras']['runtimeSelectionUnresolved']=True
            ni=len(doc['nodes']);doc['nodes'].append(node)
            children=[clone_visible(c) for c in source.get('children',[])]
            children=[c for c in children if c is not None]
            if children:node['children']=children
            return ni
        for a in assemblies:
            root=clone_visible(a['rootNode']);scene_index=len(doc['scenes'])
            doc['scenes'].append({'name':f'Tree {a["tree"]} — {label}',
                                  'nodes':[] if root is None else [root],
                                  'extras':{'visibilityPreset':preset_name,'sourceTree':a['tree'],
                                            'stateInputs':{'wheelStaticBit':preset_name=='low_speed',
                                                           'wheelMovingBit':preset_name=='moving_wheels',
                                                           'wheelGlobalOverride':0,'brakeLightsOn':False,
                                                           'reverseLightsOn':False,'exhaustOn':False,
                                                           'transforms':'original serialized values'},
                                            'status':'Source-derived explicit state inputs; original transforms, live game frame not asserted.'}})
            a.setdefault('presetScenes',{})[preset_name]=scene_index
    if assemblies:doc['scene']=assemblies[0]['presetScenes']['low_speed']
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
        entries.append({'code':car['code'],'file':filename,'sha256':hashlib.sha256(glb).hexdigest(),'bytes':len(glb),'records':records,'assemblies':assemblies,'stats':stats,'textureSelectorIds':json.loads(glb[20:20+struct.unpack_from('<I',glb,12)[0]])['extras']['textureSelectorIds']})
        print(json.dumps({'car':car['code'],**stats}),flush=True)
    index={'status':'Original bounds and source-derived visibility presets, all states retained; original shading and draw fidelity remain incomplete.','cars':entries}
    (args.output/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    (EVIDENCE/'geometry-export-index.json').write_text(json.dumps(index,indent=2)+'\n')


if __name__=='__main__':main()
