#!/usr/bin/env python3
"""Independently check exported variant mappings against original texture flag words."""
import copy
import hashlib
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[1]


def original_flags(data, textures):
    # Independent walk: name-pool boundary, palette table/blocks, then headers.
    def word(at):
        if at<0 or at+4>len(data):raise ValueError('source word outside file')
        return struct.unpack_from('<I',data,at)[0]
    align=lambda n:(n+15)&~15
    start=align(word(0));a,b,c=(word(start+4*i) for i in range(3))
    if max(a,b,c)>4096:raise ValueError('palette count exceeds bound')
    cursor=align(start+12+(a+b+c)*12)+1024*(a+c)+64*b
    if word(cursor)!=len(textures):raise ValueError('texture count differs')
    cursor+=8;flags=[]
    for t in textures:
        f,length=word(cursor),word(cursor+4);cursor+=8
        if not 1<=length<=256 or cursor+length>len(data):raise ValueError('source name outside file')
        name=data[cursor:cursor+length]
        if name[-1:]!=b'\0' or name.split(b'\0')[0].decode('ascii')!=t['name']:raise ValueError('source name differs')
        cursor=align(cursor+length)
        if cursor!=t['descriptor_offset'] or f!=t['flags']:raise ValueError('source descriptor/flags differ')
        if cursor+64>len(data):raise ValueError('source descriptor outside file')
        cursor+=64+16*data[cursor+53];flags.append(f)
    return flags


def check(car,doc):
    tex=car['textures'];expected={}
    refs={p['extras']['third'] for mesh in doc['meshes'] for p in mesh['primitives']}
    for base in refs:
        if base==65535:continue
        flag=tex[base]['flags'];count=(flag>>16)&255
        if flag&4096 and count:
            if base+count>=len(tex):raise ValueError('source group outside texture table')
            expected[base]={tex[i]['flags']>>24:i for i in range(base,base+count+1)}
    complete=sorted(set.intersection(*(set(v) for v in expected.values()))) if expected else []
    variants=doc.get('extensions',{}).get('KHR_materials_variants',{}).get('variants',[])
    if [v['extras']['originalSelector'] for v in variants]!=complete:raise ValueError('root selectors differ from source')
    if [v['name'] for v in variants]!=[f'Original selector {i}' for i in complete]:raise ValueError('selector labels differ')
    mappings_count=0
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            base=p['extras']['third'];mappings=p.get('extensions',{}).get('KHR_materials_variants',{}).get('mappings',[])
            actual={}
            for row in mappings:
                for vi in row['variants']:
                    if vi in actual:raise ValueError('repeated variant index')
                    actual[vi]=row['material']
            wanted={i:expected[base][s] for i,s in enumerate(complete)} if base in expected else {}
            if actual!=wanted:raise ValueError('primitive selector descriptor differs')
            mappings_count+=len(mappings)
    return {'selectors':complete,'variant_groups':len(expected),'mapping_entries':mappings_count}


def main():
    cars=json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text())['cars'];rows=[];negative=None
    for car in cars:
        raw=(ROOT/'viewer/public/recovered'/f'{car["code"]}.glb').read_bytes();size,kind=struct.unpack_from('<II',raw,12)
        if kind!=0x4e4f534a:raise ValueError('missing JSON chunk')
        doc=json.loads(raw[20:20+size]);source=next((ROOT/'reference/ford/cars'/car['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(source).hexdigest()!=car['sha256']:raise ValueError('original source hash differs')
        original_flags(source,car['textures']);result=check(car,doc)
        rows.append({'car':car['code'],'glb_sha256':hashlib.sha256(raw).hexdigest(),**result})
        if negative is None and result['mapping_entries']:
            bad=copy.deepcopy(doc);p=next(p for m in bad['meshes'] for p in m['primitives'] if p.get('extensions'))
            p['extensions']['KHR_materials_variants']['mappings'][0]['material']=len(car['textures'])
            try:check(car,bad)
            except ValueError:negative={'wrong_source_material_rejected':True}
            else:raise ValueError('corrupt material accepted')
    report={'cars':len(rows),'numeric_variants':sum(len(r['selectors']) for r in rows),'mapping_entries':sum(r['mapping_entries'] for r in rows),'negative':negative,'failures':0,'results':rows,'limits':'Independent serialization check against flag words independently walked from original source files, not GS rendering equivalence.'}
    (ROOT/'research/evidence/continuation/source-refresh/texture-variant-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='results'}))
if __name__=='__main__':main()
