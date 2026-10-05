#!/usr/bin/env python3
"""Recover original material header fields and lane-specific CPU color recipes."""
import static_inputs
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[1]
RE=static_inputs.bundle_path()
EXPORT=RE/'.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po'
OUT=ROOT/'research/evidence/continuation/source-refresh/material-header-contract.json'


def decode(data,h):
    start=h['offset'];end=start+h['size'];cursor=start+8;fields=[]
    if end>len(data):raise ValueError('header outside source')
    def take(kind):
        nonlocal cursor
        if cursor+4>end:raise ValueError('material field outside header')
        v=struct.unpack_from('<I',data,cursor)[0];fields.append({'kind':kind,'offset':cursor,'word':f'0x{v:08x}'})
        cursor+=4;return v
    flags=h['flags']
    if flags&256:
        value=take('distance_parameter_float_bits')
        if not math.isfinite(struct.unpack('<f',struct.pack('<I',value))[0]):raise ValueError('nonfinite source distance parameter')
    base=take('base_color_AARRGGBB') if h['third']==65535 or flags&6 else 0x80808080
    for mask,kind in [(8,'secondary_color_AARRGGBB'),(16,'third_color_AARRGGBB'),(128,'auxiliary_texture_word_70003000'),(64,'auxiliary_texture_word_70003010')]:
        if flags&mask:take(kind)
    if cursor!=end:raise ValueError('material recipe does not consume header exactly')
    rgba=[(base>>16)&255,(base>>8)&255,base&255,(base>>24)&255]
    return {'offset':start,'flags':flags,'texture_index':h['third'],'raw_header_hex':data[start:end].hex(),
            'base_color_word':f'0x{base:08x}','base_color_rgba_unscaled':rgba,'fields':fields,
            'base_color_scaling':{'xyz':'FLOAT_0028f178' if flags&1 else 'unchanged',
                                  'w':'unchanged' if flags&1 else 'DAT_70003560 * FLOAT_0028f1e8'},
            'limit':'Unscaled shader values and CPU recipe, not glTF PBR factors or a final blend.'}


def main():
    identity=json.loads((OUT.parent/'refresh-identity.json').read_text())
    inventory_path=EXPORT/'inventory.json';inventory=json.loads(inventory_path.read_text())
    if hashlib.sha256(inventory_path.read_bytes()).hexdigest()!=identity['inventory_sha256']:raise ValueError('inventory identity changed')
    elf=(RE/'games/ford-racing-2/extracted/SLES_517.05').read_bytes()
    if hashlib.sha256(elf).hexdigest()!=identity['executable_sha256']:raise ValueError('ELF identity changed')
    phoff=struct.unpack_from('<I',elf,28)[0];stride,count=struct.unpack_from('<HH',elf,42)
    loads=[struct.unpack_from('<8I',elf,phoff+i*stride) for i in range(count)]
    f=next(f for f in inventory['functions'] if f['entry']=='0021bc18')
    words={i['address']:i for i in f['instructions']}
    for i in f['instructions']:
        address=int(i['address'],16);payload=bytes.fromhex(i['bytes'])
        segment=[l for l in loads if l[0]==1 and l[2]<=address and address+len(payload)<=l[2]+l[4]]
        if len(segment)!=1:raise ValueError('ambiguous source instruction')
        l=segment[0];o=l[1]+address-l[2]
        if elf[o:o+len(payload)]!=payload:raise ValueError('instruction differs from ELF')
    anchors={'0021bc64':'pextlb v1,zero,a2','0021bc6c':'pextlh v1,zero,v1','0021bc70':'pexew v1,v1',
             '0021bc8c':'vmulx.xyz vf2,vf2,vf3','0021bcb4':'vmulx.w vf2,vf2,vf3',
             '0021bd0c':'vmulx.w vf2,vf2,vf3','0021bd10':'vmulx.xyz vf2,vf2,vf1',
             '0021bd74':'vmulx.xyz vf2,vf2,vf3'}
    for a,text in anchors.items():
        if words[a]['text']!=text:raise ValueError('color instruction anchor differs')
    mmi_path=ROOT/'research/evidence/continuation/runtime/MMI-v2.8.2.cpp'
    mmi=mmi_path.read_text();mmi_excerpts={}
    for op in ['PEXTLB','PEXTLH','PEXEW']:
        start=mmi.index('void '+op+'()');end=mmi.index('\n}',start)+2
        mmi_excerpts[op]=mmi[start:end]
    # Independent register lane simulation follows pinned PCSX2 field assignments.
    lane_checks=0;negative_swapped=0;negative_interleave=0
    for lane in range(4):
        for value in range(256):
            original=[13,29,47,83];original[lane]=value
            packed_word=int.from_bytes(bytes(original),'little')
            rt=struct.pack('<I',packed_word)+bytes(12);rs=bytes(16)
            # Execute PEXTLB from the original packed register, then PEXTLH.
            byte_reg=[v for i in range(8) for v in (rt[i],rs[i])]
            halves=list(struct.unpack('<8H',bytes(byte_reg)))
            half_reg=sum(([x,0] for x in halves[:4]),[])
            lanes=list(struct.unpack('<4I',struct.pack('<8H',*half_reg)))
            actual=[lanes[2],lanes[1],lanes[0],lanes[3]]
            expected=[original[2],original[1],original[0],original[3]]
            if actual!=expected:raise ValueError('color lane simulation differs')
            lane_checks+=1;negative_swapped+=int(lanes!=expected)
            wrong_bytes=[v for i in range(8) for v in (rs[i],rt[i])]
            wrong_halves=struct.unpack('<8H',bytes(wrong_bytes))
            wrong_half_reg=[v for h in wrong_halves[:4] for v in (h,0)]
            wrong_words=struct.unpack('<4I',struct.pack('<8H',*wrong_half_reg))
            wrong_lanes=[wrong_words[2],wrong_words[1],wrong_words[0],wrong_words[3]]
            negative_interleave+=int(wrong_lanes!=expected)
    if negative_swapped==0:raise ValueError('omitted PEXEW control not distinguished')
    cars=[];counts=Counter()
    for c in json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text())['cars']:
        data=next((ROOT/'reference/ford/cars'/c['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(data).hexdigest()!=c['sha256']:raise ValueError('model differs')
        recipes=[decode(data,h) for h in c['geometry']['headers']]
        for r in recipes:
            counts['headers']+=1;counts['explicit_base_color']+=any(f['kind']=='base_color_AARRGGBB' for f in r['fields'])
            counts['source_alpha_below_128']+=r['base_color_rgba_unscaled'][3]<128
        cars.append({'car':c['code'],'source_sha256':c['sha256'],'headers':recipes})
    c=next(c for c in json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text())['cars'] if c['code']=='COBRA')
    data=next((ROOT/'reference/ford/cars/COBRA/model').iterdir()).read_bytes();h=dict(c['geometry']['headers'][0]);bad=dict(h,size=h['size']-4)
    try:decode(data,bad)
    except ValueError:negative=True
    else:raise ValueError('truncated header accepted')
    result={'schema':'fr2-material-header-contract/v1','executable_sha256':identity['executable_sha256'],
            'inventory_sha256':identity['inventory_sha256'],'function':'0021bc18','instructions_checked':len(f['instructions']),
            'raw_lane_mask_anchors':{a:words[a] for a in anchors},'cars':cars,'counts':dict(counts),
            'pcsx2_mmi_lane_contract':{'source':'https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/MMI.cpp',
                                     'path':str(mmi_path.relative_to(ROOT)),'sha256':hashlib.sha256(mmi_path.read_bytes()).hexdigest(),
                                     'excerpts':mmi_excerpts,'lane_fixtures':lane_checks,
                                     'packed_word_to_rgba_full_chain':True,
                                     'reversed_pextlb_control_differing_fixtures':negative_interleave,
                                     'omitted_pexew_control_differing_fixtures':negative_swapped},
            'truncated_material_header_rejected':negative,
            'limits':['Typed decompiler hides EE COP2 vector destination masks; raw XYZ and W masks are authoritative.',
                      'Header base packed word is AARRGGBB via PEXTLB, PEXTLH, PEXEW. Texture pixel byte order is a separate contract.',
                      'Runtime scratchpad factors, optional pass routing, GS blend/test and source-to-live draw joins remain separate.']}
    OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'cars':len(cars),'counts':dict(counts),'source_instructions':len(f['instructions']),'negative':negative}))
if __name__=='__main__':main()
