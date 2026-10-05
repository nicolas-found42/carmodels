#!/usr/bin/env python3
"""Recover archive-bound six-tile indexed MATRIX car thumbnails.

Source TEX0 uses PSMT8/CPSM32/CSM=0/CSA0: swap CLUT address bits3/4.
Keep the unpermuted palette output as a negative control, never as an asset.
Observed game consumer/blending remain separate from byte recovery.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

from recover_car_ptg import png_bytes, verify_png, manifest_assets
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parents[1]/'reverse-engineering'
sys.path.insert(0,str(SOURCE/'tools'))
from corpus_binding import Baseline
from ps2_texture_indices import decode_indices

OUT=ROOT/'research/evidence/matrix-continuation'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)

def decode(b):
    need(len(b)==7744,'unsupported MATRIX length')
    need(struct.unpack_from('<8I',b)==(6,3,2,32,32,90,64,1),'unsupported MATRIX header')
    need(struct.unpack_from('<III',b,560)[1:]==(0,0),'unsupported palette wrapper flags')
    palette=[b[576+i*4:580+i*4] for i in range(256)]
    need(max(x[3] for x in palette)<=128,'palette alpha exceeds source range')
    canvases={name:bytearray(90*64*4) for name in ['linear-clut','csm0-swap']};descriptors=[]
    for tile in range(6):
        u,v,pointer,pad=struct.unpack_from('<4I',b,80+16*tile)
        need((u,v,pad)==(struct.unpack('<I',struct.pack('<f',1 if tile%3<2 else 26/32))[0],0x3f800000,0xdddddddd),'tile extents differ')
        descriptor=176+64*tile;fields=struct.unpack_from('<16I',b,descriptor)
        need(all(fields[i]==0xdddddddd for i in [2,3,4,5,6,7,8,9,11,15]),'descriptor padding differs')
        need(fields[1]==0 and b[descriptor+52]==3,'descriptor format differs')
        item={'descriptor_offset':descriptor,'format':3,'width':32,'height':32,'levels':[{'width':32,'height':32,'size':1024,'offset':1600+tile*1024}]}
        indices=decode_indices(b,item)
        need(not struct.unpack_from('<Q',b,descriptor+56)[0]&256,'unexpected packed MATRIX upload')
        descriptors.append({'descriptor':descriptor,'index_span':[1600+tile*1024,1600+(tile+1)*1024],'indices_sha256':sha(indices)})
        for y in range(32):
            for x in range(32):
                targetx=(tile%3)*32+x;targety=(tile//3)*32+y
                if targetx>=90:continue
                i=indices[y*32+x];swapped=(i&~24)|((i&8)<<1)|((i&16)>>1)
                at=(targety*90+targetx)*4
                canvases['linear-clut'][at:at+4]=palette[i]
                canvases['csm0-swap'][at:at+4]=palette[swapped]
    return {k:bytes(v) for k,v in canvases.items()},descriptors

def main():
    baseline=Baseline(SOURCE/'games/ford-racing-2')
    entries=[e for e in baseline.entries('.ptg;1') if e.path.lstrip('/').lower().startswith('graphics/game/matrix/')]
    liveries={Path(v['source_path']).name.lower().removesuffix('.ptg;1'):v for v in manifest_assets().values() if v['role']=='livery'}
    need(len(entries)==136,'MATRIX census differs')
    need({e.name.lower().removesuffix('.ptg;1') for e in entries}==set(liveries),'MATRIX names differ from the136 associated liveries')
    OUT.mkdir(exist_ok=True);rows=[]
    for e in entries:
        b=e.load();canvases,descriptors=decode(b);stem=e.name.lower().removesuffix('.ptg;1');outputs={}
        original=OUT/'originals'/liveries[stem]['car_code']/e.name
        original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(b)
        need(sha(original.read_bytes())==e.sha256,'copied MATRIX original differs')
        for mode,rgba in canvases.items():
            folder=OUT/('assets' if mode=='csm0-swap' else 'negative-controls')/liveries[stem]['car_code'];folder.mkdir(parents=True,exist_ok=True)
            for alpha in ['raw','display']:
                decoded=bytearray(rgba)
                if alpha=='display':decoded[3::4]=bytes(min(255,x*2) for x in rgba[3::4])
                path=folder/(stem+'.'+mode+'.'+alpha+'.png');payload=png_bytes(90,64,decoded);path.write_bytes(payload)
                verify_png(path,90,64,decoded)
                outputs[mode+'-'+alpha]={'path':str(path.relative_to(ROOT)),'sha256':sha(payload),'rgba_sha256':sha(decoded)}
        rows.append({'source':e.path,'source_bytes':len(b),'source_sha256':sha(b),'original_copy':str(original.relative_to(ROOT)),'car':liveries[stem]['car_code'],'variant':stem,'source_palette_span':[576,1600],'pixel_span':[1600,7744],'descriptors':descriptors,'authoritative_palette_lookup':'csm0-swap','outputs':outputs})
    b=entries[0].load();negative=[]
    for label,changed in [('truncation',b[:-1]),('format',b[:228]+b'\x01'+b[229:]),('grid',struct.pack('<I',7)+b[4:]),('edge_extent',b[:112]+bytes(4)+b[116:]),('palette_alpha',b[:579]+b'\xff'+b[580:])]:
        try:decode(changed)
        except ValueError:negative.append(label)
        else:raise ValueError('negative MATRIX fixture escaped '+label)
    receipt={'schema':'fr2-matrix-ptg/v1','provenance':baseline.provenance,'assets':rows,'assets_verified':len(rows),'outputs':len(rows)*4,'authoritative_png_outputs':len(rows)*2,'negative_control_png_outputs':len(rows)*2,'negative_controls':negative,'decode_code_sha256':sha(Path(__file__).read_bytes()),'palette_contract':{'source_functions':['0022acc8','00220fe0','00220d60','0022f948'],'psm':19,'cpsm':0,'csm_bit':0,'pcsx2_name':'CSM1','csa':0,'cld':1,'index_lookup':'(i&~24)|((i&8)<<1)|((i&16)>>1)'},'limits':['Archive bytes are authoritative.','CSM=0 bit3/4-swap lookup is source-derived. Unpermuted outputs are retained only as negative controls.','Source alpha is preserved; conventional 2x-alpha previews do not prove game blending.','MATRIX filenames join all136 livery records; actual consumer/runtime joins remain separate.']}
    (OUT/'recovered-matrix-ptgs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'assets_verified':len(rows),'outputs':len(rows)*4,'negative_controls':negative}))

if __name__=='__main__':main()
