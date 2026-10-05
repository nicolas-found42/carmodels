#!/usr/bin/env python3
"""Recover selector remapping from original flags and execute the original EE loop.

Host emulation covers only the bounded remap loop; it never writes emulator memory.
A missing selector preserves the prior pointer, as the original instructions do.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
from recover_car_rotation import ROOT, SOURCE, EXPORT, ELF


def u32(data, at):
    if at < 0 or at+4 > len(data): raise ValueError('word outside bounded buffer')
    return struct.unpack_from('<I',data,at)[0]


def groups(car):
    textures=car['textures'];refs=sorted({h['third'] for h in car['geometry']['headers'] if h['third']!=65535})
    result=[];occupied=set()
    for i in refs:
        t=textures[i];f=t['flags'];n=(f>>16)&255
        if not f&0x1000 or not n:continue
        if i+n>=len(textures):raise ValueError('variant group exceeds texture table')
        members=textures[i:i+n+1]
        if occupied.intersection(range(i,i+n+1)):raise ValueError('overlapping groups')
        occupied.update(range(i,i+n+1))
        selectors=[(x['flags']>>24)&255 for x in members]
        if len(set(selectors))!=len(selectors):raise ValueError('duplicate selector')
        if any(x['name']!=t['name'] for x in members):raise ValueError('variant names differ')
        result.append({'base_texture_index':i,'additional_members':n,'name':t['name'],
                       'selector_to_texture':{str(s):i+j for j,s in enumerate(selectors)}})
    valid=sorted(set.intersection(*(set(map(int,g['selector_to_texture'])) for g in result))) if result else []
    return {'car':car['code'],'source_sha256':car['sha256'],'referenced_texture_indices':refs,
            'groups':result,'complete_selectors':valid,
            'variants':[{'selector':s,'material_remap':{str(g['base_texture_index']):g['selector_to_texture'][str(s)] for g in result}} for s in valid]}


def instructions():
    raw=(EXPORT/'inventory.json').read_bytes();receipt=json.loads((ROOT/'research/evidence/continuation/source-refresh/refresh-identity.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=receipt['inventory_sha256']:raise ValueError('inventory changed')
    inv=json.loads(raw);f=next(x for x in inv['functions'] if x['entry']=='001248a0');span=[i for i in f['instructions'] if 0x124900<=int(i['address'],16)<=0x1249b4]
    elf=ELF.read_bytes()
    if hashlib.sha256(elf).hexdigest()!=receipt['executable_sha256']:raise ValueError('ELF changed')
    loads=[];phoff=u32(elf,28);stride,count=struct.unpack_from('<HH',elf,42)
    for i in range(count):
        kind,off,va,_,size,*_=struct.unpack_from('<8I',elf,phoff+i*stride)
        if kind==1:loads.append((va,va+size,off))
    helper=next(x for x in inv['functions'] if x['entry']=='0021b6e0')['instructions']
    for ins in span+helper:
        a=int(ins['address'],16);hit=[x for x in loads if x[0]<=a and a+4<=x[1]]
        if len(hit)!=1:raise ValueError('ELF mapping ambiguous')
        start,end,off=hit[0]
        if elf[off+a-start:off+a-start+4]!=bytes.fromhex(ins['bytes']):raise ValueError('instruction differs from ELF')
    return span,helper,receipt


def execute(span,mem,lib,desc,selector):
    """Decode raw EE integer instructions with branch/likely delay semantics."""
    words={int(i['address'],16):int.from_bytes(bytes.fromhex(i['bytes']),'little') for i in span}
    r=[0]*32;r[17]=lib;r[11]=desc;r[13]=selector;r[8]=mem[desc+14]
    pc=0x124900;steps=0;writes=[]
    if r[8]==0:return {'steps':0,'writes':[]}
    def simple(w):
        op,rs,rt,rd,sa,fn=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,(w>>6)&31,w&63
        imm=w&65535;sign=imm if imm<32768 else imm-65536
        if w==0:pass
        elif op==0 and fn==0:r[rd]=(r[rt]<<sa)&0xffffffff
        elif op==0 and fn in [33,45]:r[rd]=(r[rs]+r[rt])&0xffffffff
        elif op==0 and fn==42:r[rd]=int((r[rs] if r[rs]<2**31 else r[rs]-2**32)<(r[rt] if r[rt]<2**31 else r[rt]-2**32))
        elif op==9:r[rt]=(r[rs]+sign)&0xffffffff
        elif op==12:r[rt]=r[rs]&imm
        elif op in [35,36,43]:
            at=(r[rs]+sign)&0xffffffff
            if at>=len(mem) or (op!=36 and at+4>len(mem)):raise ValueError('memory access outside bounded buffer')
            if op==35:r[rt]=u32(mem,at)
            elif op==36:r[rt]=mem[at]
            else:struct.pack_into('<I',mem,at,r[rt]);writes.append(at)
        else:raise ValueError(f'unsupported EE instruction {w:08x}')
        r[0]=0
    while pc<=0x1249b4:
        if pc not in words or steps>100000:raise ValueError('bounded loop failure')
        w=words[pc];op=w>>26;steps+=1
        if op in [4,5,20,21]:
            rs,rt=(w>>21)&31,(w>>16)&31;imm=w&65535;sign=imm if imm<32768 else imm-65536
            taken=(r[rs]==r[rt]) if op in [4,20] else (r[rs]!=r[rt])
            if taken or op in [4,5]:simple(words[pc+4])
            pc=pc+4+sign*4 if taken else pc+8
        else:simple(w);pc+=4
    return {'steps':steps,'writes':writes}


def synthetic(car,contract,span,selector,prior=0):
    mem=bytearray(65536);lib,desc,flags,pointers,refs=256,768,2048,4096,6144
    struct.pack_into('<I',mem,lib+244,flags);struct.pack_into('<I',mem,lib+236,pointers)
    bases=[g['base_texture_index'] for g in contract['groups']]
    mem[desc+14]=len(bases);struct.pack_into('<I',mem,desc+28,refs)
    initial=list(range(len(car['textures'])))
    for g in contract['groups']:
        initial[g['base_texture_index']]=g['selector_to_texture'].get(str(prior),g['base_texture_index'])
    for i,t in enumerate(car['textures']):
        struct.pack_into('<2I',mem,flags+i*8,t['flags'],16384+i*96)
        struct.pack_into('<I',mem,pointers+i*4,16384+initial[i]*96)
    for i,b in enumerate(bases):struct.pack_into('<I',mem,refs+i*4,b)
    run=execute(span,mem,lib,desc,selector)
    expected=initial.copy()
    for g in contract['groups']:
        if str(selector) in g['selector_to_texture']:expected[g['base_texture_index']]=g['selector_to_texture'][str(selector)]
    actual=[(u32(mem,pointers+i*4)-16384)//96 for i in range(len(initial))]
    if actual!=expected:raise ValueError('raw instruction mapping differs')
    return run


def main():
    census_path=ROOT/'research/evidence/original-recovery/car-asset-census.json';cars=json.loads(census_path.read_text())['cars'];span,helper,identity=instructions()
    contracts=[groups(c) for c in cars];probes=0
    for car,contract in zip(cars,contracts):
        data=next((ROOT/'reference/ford/cars'/car['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(data).hexdigest()!=car['sha256']:raise ValueError('car identity changed')
        for selector in contract['complete_selectors']+[255]:
            for prior in contract['complete_selectors'] or [0]:synthetic(car,contract,span,selector,prior);probes+=1
    negative=[]
    for name,address,replacement in [('selector_byte','00124948','02008290'),('pointer_store','001249a0','040064ac'),('flag_mask','00124920','00004230')]:
        mutated=copy.deepcopy(span)
        next(i for i in mutated if i['address']==address)['bytes']=replacement
        rejected=False
        for probe_selector in contracts[0]['complete_selectors']:
            try:synthetic(cars[0],contracts[0],mutated,probe_selector,prior=1)
            except ValueError:rejected=True;break
        if not rejected:raise ValueError('changed-word negative control was accepted')
        negative.append({'name':name,'address':address,'changed_bytes':replacement,'rejected':True})
    runtime=[]
    for label in ['race95','race97']:
        directory=ROOT/'research/evidence/continuation/runtime/linux';memory_path=directory/f'{label}-eeMemory.bin';memory=memory_path.read_bytes()
        joins=json.loads((directory/f'{label}-car-source-joins.json').read_text());states=json.loads((directory/f'{label}-instance-states.json').read_text())
        if hashlib.sha256(memory).hexdigest()!=states['memory_sha256'] or hashlib.sha256(memory).hexdigest()!=joins['memory_sha256']:raise ValueError('runtime identity changed')
        for joined in joins['cars']:
            car=next(c for c in cars if c['code']==joined['car']);contract=next(c for c in contracts if c['car']==joined['car']);instance=next(c for c in states['cars'] if c['car']==joined['car'])
            for join in joined['joins']:
                for obj in join['objects']:
                    lib=obj['address'];table=u32(memory,lib+244);pointers=u32(memory,lib+236);desc=instance['descriptor'];n=memory[desc+14];refs=u32(memory,desc+28);base=join['source_base']
                    for i,t in enumerate(car['textures']):
                        if (u32(memory,table+i*8),u32(memory,table+i*8+4))!=(t['flags'],base+t['descriptor_offset']):raise ValueError('runtime original flags/descriptor differs')
                    actual_refs=[u32(memory,refs+i*4) for i in range(n)]
                    if sorted(actual_refs)!=sorted(g['base_texture_index'] for g in contract['groups']):raise ValueError('runtime variant group list differs')
                    for ent in instance['entities']:
                        klass=u32(memory,ent['address']+4)
                        if 0x233070+((klass>>20)&15)*0x114!=lib:raise ValueError('class library address differs')
                        selector=struct.unpack_from('<H',memory,ent['address']+100)[0];trial=bytearray(memory);run=execute(span,trial,lib,desc,selector)
                        if trial!=memory:raise ValueError('captured selector remap differs from captured pointer table')
                        remap={str(g['base_texture_index']):g['selector_to_texture'].get(str(selector)) for g in contract['groups']}
                        runtime.append({'capture':label,'car':car['code'],'entity':ent['address'],'selector':selector,'library':lib,'original_flags_checked':len(car['textures']),'descriptor_group_indices':actual_refs,'material_remap':remap,'raw_loop_writes':len(run['writes']),'captured_table_matches':True})
    receipt={'inventory_sha256':identity['inventory_sha256'],'elf_sha256':identity['executable_sha256'],'census_sha256':hashlib.sha256(census_path.read_bytes()).hexdigest(),'original_loop_words':span,'library_helper_words':helper,'synthetic_source_probes':probes,'changed_word_negative_controls':negative,'runtime':runtime,'cars':contracts,'limits':['Missing selectors leave prior descriptor pointers intact. Complete selectors apply across all referenced variant groups.','Numeric selector IDs are proven; human livery labels and UI variant paths remain separate.','Host emulation checks descriptor remapping only, not actual GS draw execution or shading.']}
    out=ROOT/'research/evidence/continuation/source-refresh/texture-variant-contract.json';out.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cars':len(cars),'variant_groups':sum(len(c['groups']) for c in contracts),'source_probes':probes,'runtime_entities':len(runtime),'variants':sum(len(c['variants']) for c in contracts),'failures':0}))

if __name__=='__main__':main()
