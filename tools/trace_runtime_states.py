#!/usr/bin/env python3
"""Read source-bound hierarchy and instance state from a paused original EE capture."""
import static_inputs
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from trace_runtime_cars import ROOT, occurrences, u32
from recover_assembly_semantics import distance_root


def f32(x):
    return struct.unpack('<f',struct.pack('<f',x))[0]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory',type=Path,required=True)
    parser.add_argument('--joins',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    memory=args.memory.read_bytes()
    joins=json.loads(args.joins.read_text())
    require(len(memory)==32*1024*1024, 'EE memory must be exactly 32 MiB')
    require(hashlib.sha256(memory).hexdigest()==joins['memory_sha256'], 'EE capture hash differs from joins')
    assembly={c['code']:c for c in json.loads((ROOT/'research/evidence/continuation/assembly-semantics.json').read_text())['cars']}
    elf=(static_inputs.bundle_path()/'games/ford-racing-2/extracted/SLES_517.05').read_bytes()
    phoff=struct.unpack_from('<I',elf,28)[0];size,count=struct.unpack_from('<HH',elf,42)
    reginfo=next(struct.unpack_from('<8I',elf,phoff+i*size) for i in range(count)
                 if struct.unpack_from('<I',elf,phoff+i*size)[0]==0x70000000)
    gp=u32(elf,reginfo[1]+20)
    camera=u32(memory,gp+0x937c-65536)
    scale=struct.unpack_from('<f',memory,camera+0x20)[0] if camera else 1.0
    bias=struct.unpack_from('<i',memory,gp+0x93c0-65536)[0]
    minimum=struct.unpack_from('<i',memory,gp+0x93bc-65536)[0]
    last_renderer_entity=u32(memory,gp+0x947c-65536)
    results=[]
    for car in joins['cars']:
        row=assembly[car['car']]; source=next((ROOT/'ford-racing-2/cars'/car['car']/'model').iterdir()).read_bytes()
        require(hashlib.sha256(source).hexdigest()==row['sha256'], 'original car source hash differs')
        record=row['records'][0];nodes=record['nodes']
        for bound in car['joins']:
            for object_row in bound['objects']:
                obj=object_row['address'];descriptor=u32(memory,obj+0x10)
                root_table=u32(memory,descriptor+0x54)
                require(memory[descriptor+0x11]==len(record['roots']), 'runtime root count differs')
                require(memory[descriptor+0x12]==len(record['thresholds']), 'runtime threshold count differs')
                thresholds=list(struct.unpack_from('<'+'f'*len(record['thresholds']),memory,u32(memory,descriptor+0x4c)))
                require(thresholds==record['thresholds'], 'runtime thresholds differ from source')
                addresses={}
                def bind(index,address,parent):
                    n=nodes[index];flags=u32(memory,address+4)
                    require(u32(memory,address)&65535==n['geometry_record'], 'runtime geometry ID differs')
                    require((flags&255)==len(n['children']), 'runtime child count differs')
                    require(((flags>>8)&63)==len(n['pairs']), 'runtime named pair count differs')
                    require(bool(flags&65536)==n['runtime_mutable'], 'runtime mutable flag differs')
                    require(((flags>>15)&1)==(n['serialized_flags']&1), 'runtime source flag bit 0 differs')
                    require(((flags>>24)&1)==((n['serialized_flags']>>1)&1), 'runtime source flag bit 1 differs')
                    require(u32(memory,address+0x24)==parent, 'runtime descriptor parent differs')
                    require(memory[address+0xc:address+0x24]==source[n['offset']+8:n['offset']+32], 'runtime transform differs from source')
                    pair_pointer=u32(memory,address+8)
                    for i,pair in enumerate(n['pairs']):
                        require(struct.unpack_from('<HH',memory,pair_pointer+i*4)==(pair['name_id'],pair['child_index']), 'runtime named pair differs')
                    addresses[index]=address
                    child_pointer=u32(memory,address+0x28)
                    for i,child in enumerate(n['children']):bind(child,child_pointer+i*44,address)
                for i,root in enumerate(record['roots']):bind(root,root_table+i*44,0)
                cls=u32(memory,descriptor)
                registry_slot=0x233080+((cls>>20)&15)*0x114
                registry_descriptor=u32(memory,registry_slot)+(cls&65535)*0x58
                require(registry_descriptor==descriptor, 'runtime class registry does not resolve descriptor')
                entity_class=(cls&0xfff0ffff)|0x20000
                entities=[]
                for hit in occurrences(memory,struct.pack('<I',entity_class)):
                    entity=hit-4
                    if entity<0 or entity+0x90>len(memory) or entity%4:continue
                    instance=u32(memory,entity+0x6c)
                    if not (0<instance<len(memory)-80 and u32(memory,instance)==entity):continue
                    states=[]
                    def visit(index,address,parent,ancestor_visible):
                        n=nodes[index]
                        require(u32(memory,address)==parent, 'runtime instance parent differs')
                        mutable=n['runtime_mutable'];visibility=u32(memory,address+8)&1 if mutable else None
                        visible=ancestor_visible and (bool(visibility) if mutable else True)
                        state={'source_node_offset':n['offset'],'runtime_node':addresses[index],
                               'instance':address,'names':n['source_names'],'mutable':mutable,
                               'visibility_bit':visibility,'passes_ancestor_visibility':visible}
                        if mutable:
                            values=list(struct.unpack_from('<8f',memory,address+0x10))
                            require(all(math.isfinite(v) for v in values), 'nonfinite runtime mutable transform')
                            state.update({'translation_xyzw':values[:4],'rotation_xyzw':values[4:]})
                        states.append(state)
                        cursor=u32(memory,address+4)
                        for child in n['children']:
                            visit(child,cursor,address,visible)
                            cursor+=64 if nodes[child]['runtime_mutable'] else 16
                    cursor=instance
                    for root in record['roots']:
                        visit(root,cursor,entity,True)
                        cursor+=64 if nodes[root]['runtime_mutable'] else 16
                    camera_vector=list(struct.unpack_from('<4f',memory,entity+0x50))
                    require(all(math.isfinite(v) for v in camera_vector), 'nonfinite camera-relative vector')
                    z=camera_vector[2]
                    predicted=distance_root(f32(z*scale),thresholds,len(record['roots']),bias=bias,minimum=minimum)
                    entities.append({'address':entity,'instance_table':instance,'camera_relative_xyzw':camera_vector,
                                     'selector_input_lane':'Z at entity+0x58; PEXTUW Rt.UL[2]',
                                     'predicted_root_for_captured_inputs':predicted,
                                     'matches_last_renderer_entity_global':entity==last_renderer_entity,
                                     'states':states})
                results.append({'car':car['car'],'object':obj,'descriptor':descriptor,
                                'class_registry_slot':registry_slot,'class_registry_descriptor':registry_descriptor,
                                'root_table':root_table,'descriptor_nodes_checked':len(addresses),
                                'thresholds':thresholds,'entities':entities})
    report={'memory_sha256':hashlib.sha256(memory).hexdigest(),'elf_sha256':hashlib.sha256(elf).hexdigest(),
            'gp_from_elf_reginfo':gp,'camera_object':camera,'camera_scale':scale,'selector_bias':bias,
            'selector_minimum':minimum,'last_renderer_entity_global':last_renderer_entity,
            'cars':results,'failures':0,
            'limits':['This reads paused source-bound descriptors and instance state, not a draw call log.',
                      'Predicted roots use captured inputs; retained entities may have stale vectors or be culled.',
                      'Visibility is hierarchical draw eligibility; GS packet execution remains a separate check.']}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cars':len(results),'descriptor_nodes':sum(r['descriptor_nodes_checked'] for r in results),
                      'entities':sum(len(r['entities']) for r in results),'failures':0}))


if __name__=='__main__':main()
