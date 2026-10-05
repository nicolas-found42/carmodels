#!/usr/bin/env python3
"""Build source-bound positive, contradiction and missing-evidence controls.

Expected labels are kept outside Jev model state. These evaluate this small local
battery only; they are not calibration of Jev on arbitrary game reverse engineering.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RE = ROOT.parents[1]/'reverse-engineering'
OUT = ROOT/'research/evidence/original-recovery'


def main():
    groups = []
    def add(name, path, supports, contradicts, silent, evidence=None):
        groups.append({'id':name,'source':str(path),'evidence':evidence or path.read_text(),
                       'cases':[{'claim':s,'expected':label} for label,values in
                                [('verified',supports),('contradicted',contradicts),('unsupported',silent)] for s in values]})
    add('container-code',RE/'tools/ps2_container.py',[
        'The parser derives texture width from descriptor bits 15 through 18.',
        'The decoder returns the image plane directly for format 1.',
        'The indexed RGBA decoder selects 16 palette entries for format 4.',
        'The parser aligns each stored mip image start to a 16-byte boundary.'
    ],[
        'The parser derives texture width from descriptor bits 19 through 22.',
        'The decoder doubles every stored alpha byte before returning RGBA.',
        'The indexed RGBA decoder selects 256 palette entries for format 4.',
        'The parser stores mip images without aligning their starts.'
    ],[
        'The original Gran Torino mesh has a proven world-space vertex scale of 1/16384.',
        'The texture decoder was compared against a live game screenshot.',
        'The material-to-mesh UV binding is recovered for every car.',
        'All 171 car PTG files decode into complete icons and liveries.'
    ])
    add('index-code',RE/'tools/ps2_texture_indices.py',[
        'Packed format 3 uses unswizzle8; direct format 3 retains the linear image plane.',
        'Direct format 4 expands each byte into its low nibble followed by its high nibble.',
        'Descriptor bit 8 selects packed upload.',
        'The decoder rejects a texture item whose dimensions disagree with its descriptor.'
    ],[
        'Direct format 3 is always unswizzled by unswizzle8.',
        'Direct format 4 expands each byte into its high nibble followed by its low nibble.',
        'Descriptor bit 9 selects packed upload.',
        'The decoder accepts a texture item whose dimensions disagree with its descriptor.'
    ],[
        'The car PTG menu icon uses this same format 4 decoder.',
        'The runtime GS chooses exactly the same material for every car part.',
        'Every stored mip level is decoded by decode_indices.',
        'The recovered car meshes have been exported as faithful GLBs.'
    ])
    p=RE/'tools/ps2_sections.py'
    source=p.read_text(); source=source[:source.index('\ndef parse(')]
    add('geometry-layout',p,[
        'The geometry table uses 0x34-byte records.',
        'The two geometry group counts come from offsets +0x1c and +0x28.',
        'Each geometry header always has a six-byte plane and a four-byte plane.',
        'Flag 0x800 adds a twenty-byte-per-sample geometry plane.'
    ],[
        'The geometry table uses 0x58-byte records.',
        'The two geometry group counts come from offsets +0x20 and +0x2c.',
        'Each geometry header always has a twenty-byte plane.',
        'Flag 0x800 adds a sixteen-byte-per-sample geometry plane.'
    ],[
        'The six-byte samples are proven to be world-space XYZ in meters.',
        'The four-byte samples are proven to be packed normals.',
        'The third four-byte plane is proven to be UV coordinates.',
        'The parser proves the final triangle-strip winding order.'
    ],evidence=source)
    add('vif-order',RE/'notes/evidence/fr2-geometry-vif-preamble/README.md',[
        'The audited geometry tail appends MSCNT before BASE and OFFSET.',
        'The audited row update contains three raw words 0x44400000 and a zero fourth word.',
        'Overlay 5 pair 213 is E-marked nop, pair 214 is its delay nop, and pair 215 is xtop vi01.',
        'The first render iteration inherited VIF state remains unresolved.'
    ],[
        'The audited geometry tail appends BASE and OFFSET before MSCNT.',
        'The audited row update contains three raw words 0x45c00000 and a zero fourth word.',
        'Overlay 5 pair 214 is E-marked nop, pair 215 is its delay nop, and pair 216 is xtop vi01.',
        'The first render iteration inherited VIF state has been proven.'
    ],[
        'The row constants establish a world-space position scale of 1/768.',
        'The recovered vertex data produced a faithful rendered Ford GT screenshot.',
        'The original Gran Torino front-wheel normals are known.',
        'The camera projection matrix for all tracks has been recovered.'
    ])
    add('vu-consumer',RE/'notes/evidence/fr2-geometry-vu-consumer/README.md',[
        'Pair 221 reads TOP+3.z into vi03.',
        'The writer header qword 3 is [count, 0, uVar14, 0].',
        'Only the first four of the eight matrix-packet vectors come from param_1.',
        'There is no XGKICK after pair 215 in this saved overlay.'
    ],[
        'Pair 221 reads TOP+3.x into vi03.',
        'The writer header qword 3 is [count, uVar14, 0, 0].',
        'All eight matrix-packet vectors come from param_1.',
        'This saved overlay has an XGKICK after pair 215 that uses vi03.'
    ],[
        'The selected vi03 value is proven to be the final XGKICK output pointer.',
        'The last four matrix-packet vectors are definitely the camera projection matrix.',
        'The original mesh normals have been decoded.',
        'The emitted vertices have been tested against original hardware.'
    ])
    profile=json.loads((ROOT/'research/evidence/ptg-investigation/ptg-profile-carmodels.json').read_text())
    excerpt=json.dumps({k:v for k,v in profile.items() if k!='per_file'},indent=2)
    add('ptg-census',ROOT/'research/evidence/ptg-investigation/ptg-profile-carmodels.json',[
        'The measured car PTG corpus has 171 files.',
        'The measured car PTG corpus has 35 images with dimensions 165x98.',
        'The measured car PTG corpus has 136 images with dimensions 227x85.',
        'All 171 measured car PTGs are classified as tiled_header_only.'
    ],[
        'The measured car PTG corpus has 170 files.',
        'The measured car PTG corpus has 35 images with dimensions 227x85.',
        'The measured car PTG corpus has 136 images with dimensions 165x98.',
        'All 171 measured car PTGs are classified as completely_decoded.'
    ],[
        'The measured PTG pixels have been decoded correctly.',
        'The PTG palettes are identical to the corresponding embedded model palettes.',
        'The icon and livery with the same code have byte-identical contents.',
        'Every car PTG mip level has been recovered.'
    ],evidence=excerpt)
    census=json.loads((OUT/'car-asset-census.json').read_text())
    excerpt=json.dumps({k:census[k] for k in ['summary','formats','upload_profiles','limits']},indent=2)
    add('fresh-export',OUT/'car-asset-census.json',[
        'The fresh export inspected 35 car models.',
        'The fresh export decoded 700 level-zero textures.',
        'The fresh export counted 657139 geometry samples.',
        'The export includes 94 stored mip levels but claims level-zero decoding only.'
    ],[
        'The fresh export inspected 56 car models.',
        'The fresh export decoded 701 level-zero textures.',
        'The fresh export counted 657138 geometry samples.',
        'The export claims every stored mip level is decoded.'
    ],[
        'The exported images are bit-exact with a running GS emulator.',
        'Every original car triangle has been reconstructed.',
        'The exported textures are bound to original mesh UVs.',
        'Every alternate livery texture has been recovered.'
    ],evidence=excerpt)
    (OUT/'claim-control-fixtures.json').write_text(json.dumps(groups,indent=2)+'\n')
    print(json.dumps({'groups':len(groups),'claims':sum(len(g['cases']) for g in groups)}))


if __name__=='__main__':
    main()
