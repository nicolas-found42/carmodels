#!/usr/bin/env python3
"""Independently validate lossless material fields embedded in every GLB primitive."""
import copy
import hashlib
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[1]


def check(data,headers,doc):
    source={h['offset']:h for h in headers};seen=set()
    wanted_offsets=set()
    for h in headers:
        p=h['planes']['six_byte'];positions=list(struct.iter_unpack('<3h',data[p['offset']:p['end']]))
        p=h['planes']['four_byte'];attributes=list(struct.iter_unpack('<4b',data[p['offset']:p['end']]))
        if any(attributes[i][3]==0 and len(set(positions[i-2:i+1]))==3 for i in range(2,h['count'])):
            wanted_offsets.add(h['offset'])
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            offset=p['extras']['headerOffset']
            if offset in seen or offset not in wanted_offsets:raise ValueError('duplicate or ineligible material header')
            h=source[offset];seen.add(offset)
            r=p['extras']['originalMaterialHeader'];start=offset+8;flags=h['flags']
            if r['raw_header_hex']!=data[offset:offset+h['size']].hex() or r['flags']!=flags or r['texture_index']!=h['third']:raise ValueError('original header differs')
            cursor=start;expected=[]
            kinds=[]
            if flags&0x100:kinds.append('distance_parameter_float_bits')
            if h['third']==0xffff or flags&6:kinds.append('base_color_AARRGGBB')
            kinds.extend(kind for mask,kind in [(8,'secondary_color_AARRGGBB'),(16,'third_color_AARRGGBB'),(128,'auxiliary_texture_word_70003000'),(64,'auxiliary_texture_word_70003010')] if flags&mask)
            base=0x80808080
            for kind in kinds:
                word=struct.unpack_from('<I',data,cursor)[0]
                expected.append({'kind':kind,'offset':cursor,'word':f'0x{word:08x}'})
                if kind=='base_color_AARRGGBB':base=word
                cursor+=4
            if cursor!=offset+h['size'] or r['fields']!=expected:raise ValueError('material field ownership differs')
            if r['base_color_word']!=f'0x{base:08x}' or r['base_color_rgba_unscaled']!=[(base>>16)&255,(base>>8)&255,base&255,base>>24]:raise ValueError('packed material color differs')
            wanted={'xyz':'FLOAT_0028f178' if flags&1 else 'unchanged','w':'unchanged' if flags&1 else 'DAT_70003560 * FLOAT_0028f1e8'}
            if r['base_color_scaling']!=wanted:raise ValueError('material color lane recipe differs')
            # The glTF material an untextured primitive points at must carry the header's
            # own colour, and below the GS opaque stop (128) it must be alpha-blended at alpha/128.
            rgba=[(base>>16)&255,(base>>8)&255,base&255,base>>24]
            if h['third']==0xffff:
                material=doc['materials'][p['material']]
                if ('baseColorFactor' not in material.get('pbrMetallicRoughness',{})
                        or 'baseColorTexture' in material.get('pbrMetallicRoughness',{})):raise ValueError('untextured material has no plain base colour')
                factor=material['pbrMetallicRoughness']['baseColorFactor']
                wanted_factor=[c/255 for c in rgba[:3]]+[min(1.0,rgba[3]/128)]
                if any(abs(a-b)>1e-6 for a,b in zip(factor,wanted_factor)):raise ValueError('material base colour differs from header colour')
                wanted_mode='BLEND' if rgba[3]<128 else None
                if material.get('alphaMode')!=wanted_mode:raise ValueError('material blend mode differs from header alpha')
    # Zero-area/ADC-only source headers may not create a glTF primitive.
    if seen!=wanted_offsets:raise ValueError('source material header coverage differs')
    return len(seen)


def main():
    cars=json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text())['cars'];rows=[];negative=False;controls={}
    for c in cars:
        data=next((ROOT/'reference/ford/cars'/c['code']/'model').iterdir()).read_bytes()
        if hashlib.sha256(data).hexdigest()!=c['sha256']:raise ValueError('original source differs')
        raw=(ROOT/'viewer/public/recovered'/f'{c["code"]}.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length])
        n=check(data,c['geometry']['headers'],doc);rows.append({'car':c['code'],'glb_sha256':hashlib.sha256(raw).hexdigest(),'primitive_material_headers':n})
        if not negative:
            bad=copy.deepcopy(doc);bad['meshes'][0]['primitives'][0]['extras']['originalMaterialHeader']['base_color_rgba_unscaled'][3]^=1
            try:check(data,c['geometry']['headers'],bad)
            except ValueError:negative=True
            else:raise ValueError('modified original alpha accepted')
            for kind in ['missing','duplicate']:
                bad=copy.deepcopy(doc);primitives=bad['meshes'][0]['primitives']
                if kind=='missing':primitives.pop(0)
                else:primitives.append(copy.deepcopy(primitives[0]))
                try:check(data,c['geometry']['headers'],bad)
                except ValueError:controls[kind+'_material_header_rejected']=True
                else:raise ValueError(kind+' material header accepted')
            for kind,word in [('changed_colour',{'pbrMetallicRoughness':{'baseColorFactor':[0.1,0.9,0.3,1.0]}}),
                              ('changed_alpha',{'pbrMetallicRoughness':{'baseColorFactor':[0.0,0.0,0.0,1.0]}}),
                              ('missing',{'pbrMetallicRoughness':{'baseColorFactor':None}})]:
                bad=copy.deepcopy(doc);primitives=bad['meshes'][0]['primitives']
                target=next(p for p in primitives if p['extras']['third']==0xffff)
                if kind=='missing':target['material']=len(bad['materials']);bad['materials'].append({'name':'Validator control extra material'})
                else:bad['materials'][target['material']]=word
                try:check(data,c['geometry']['headers'],bad)
                except ValueError:controls[kind+'_material_rejected']=True
                else:raise ValueError(kind+' material accepted')
    receipt={'cars':len(rows),'embedded_material_headers':sum(r['primitive_material_headers'] for r in rows),'modified_original_alpha_rejected':negative,'coverage_controls':controls,'failures':0,'results':rows,
             'limits':'Original header/field/packed-color preservation and CPU lane recipe; not glTF material equivalence.'}
    (ROOT/'research/evidence/continuation/source-refresh/material-header-export-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='results'}))
if __name__=='__main__':main()
