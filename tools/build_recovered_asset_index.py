#!/usr/bin/env python3
"""Consolidate canonical recovered outputs without copying or altering source assets."""
from collections import Counter
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'ford-racing-2/recovered'


def read(relative):return json.loads((ROOT/relative).read_text())
def sha(data):return hashlib.sha256(data).hexdigest()


def asset(relative,expected,kind,**metadata):
    path=ROOT/relative
    if not path.resolve().is_relative_to(ROOT):raise ValueError('asset outside project')
    payload=path.read_bytes()
    if sha(payload)!=expected:raise ValueError(f'asset hash differs: {relative}')
    return {'path':relative,'bytes':len(payload),'sha256':expected,'kind':kind,**metadata}


def main():
    paths={'model_census':'research/evidence/original-recovery/car-asset-census.json',
           'mips':'research/evidence/mip-continuation/mip-index.json',
           'ptgs':'research/evidence/ptg-continuation/recovered-car-ptgs.json',
           'matrix':'research/evidence/matrix-continuation/recovered-matrix-ptgs.json',
           'variants':'research/evidence/continuation/source-refresh/texture-variant-contract.json',
           'glbs':'dealership/public/ford-racing-2/index.json'}
    inputs={k:read(p) for k,p in paths.items()};cars=inputs['model_census']['cars'];rows=[];counts=Counter()
    for car in cars:
        code=car['code'];assets=[];original=next((ROOT/'ford-racing-2/cars'/code/'model').iterdir())
        assets.append(asset(original.relative_to(ROOT).as_posix(),car['sha256'],'original_model'))
        glb=next(x for x in inputs['glbs']['cars'] if x['code']==code);assets.append(asset('dealership/public/ford-racing-2/'+glb['file'],glb['sha256'],'glb'))
        for t in car['textures']:
            for field,kind in [('png','model_texture_display'),('raw_alpha_png','model_texture_raw')]:
                assets.append(asset('research/evidence/original-recovery/'+t[field],t[field+'_sha256'],kind,texture_index=t['index'],texture_name=t['name'],level=0))
        mips=next(x for x in inputs['mips']['cars'] if x['car']==code)
        for m in mips['extra_mip_levels']:
            meta={'texture_index':m['texture_index'],'texture_name':m['texture_name'],'level':m['level'],'source_file_offset':m['source_file_offset']}
            assets.append(asset('research/evidence/mip-continuation/'+m['raw_plane'],m['source_sha256'],'mip_plane',**meta))
            assets.append(asset('research/evidence/mip-continuation/'+m['png'],m['png_sha256'],'mip_stored_alpha',**meta))
        for p in inputs['ptgs']['assets']:
            if p['car_code']!=code:continue
            assets.append(asset(p['reference_path'],p['sha256'],'original_'+p['role'],source_archive_path=p['source_path']))
            for name,output in p['outputs'].items():assets.append(asset(output['path'],output['sha256'],p['role']+'_'+name,source_archive_path=p['source_path']))
        for m in inputs['matrix']['assets']:
            if m['car']!=code:continue
            if m['authoritative_palette_lookup']!='csm0-swap':raise ValueError('unknown canonical palette contract')
            assets.append(asset(m['original_copy'],m['source_sha256'],'original_matrix',source_archive_path=m['source']))
            for name in ['csm0-swap-raw','csm0-swap-display']:
                o=m['outputs'][name];assets.append(asset(o['path'],o['sha256'],'matrix_'+name,source_archive_path=m['source']))
        if len({a['path'] for a in assets})!=len(assets):raise ValueError('duplicate asset path')
        variants=next(x for x in inputs['variants']['cars'] if x['car']==code)
        per=Counter(a['kind'] for a in assets);counts.update(per)
        manifest={'schema':'fr2-canonical-recovered-asset-index/v1','car':code,'status':'Recovered source assets and interoperable GLB; final game-render fidelity remains incomplete.','render_fidelity_complete':False,
                  'source_model_sha256':car['sha256'],'assets':assets,'counts':dict(per),'numeric_texture_variants':variants['variants'],
                  'limits':['glTF materials, normalized normals, strip winding and retained runtime-state trees still carry the documented rendering limits.',
                            'MATRIX and LIVERY paths are associated by verified archive/roster basenames; numeric selector-to-UI-label assignment is separate.',
                            'Display-alpha PNGs are inspection conversions. Original source bytes and stored-alpha outputs are retained. Negative-control images and reconstructed thumbnail previews are excluded.']}
        folder=OUT/'cars'/code;folder.mkdir(parents=True,exist_ok=True);payload=(json.dumps(manifest,indent=2)+'\n').encode();(folder/'manifest.json').write_bytes(payload)
        rows.append({'car':code,'manifest':(folder/'manifest.json').relative_to(ROOT).as_posix(),'manifest_sha256':sha(payload),'assets':len(assets),'texture_selectors':variants['complete_selectors']})
    index={'schema':'fr2-canonical-recovered-asset-index/v1','source_receipts':{k:{'path':p,'sha256':sha((ROOT/p).read_bytes())} for k,p in paths.items()},'cars':rows,'counts':dict(counts),'total_assets':sum(counts.values()),'status':'Asset/index integrity checked. Rendering-fidelity completion not asserted.','render_fidelity_complete':False}
    (OUT/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    (OUT/'README.md').write_text('# Recovered Ford Racing 2 source assets\n\nThe index links canonical outputs in place; original reference files are preserved. Each car has a hash-verified manifest under `cars/<CAR>/manifest.json`.\n\nThis includes 35 original models and GLBs, 700 level-zero texture pairs, 94 stored-alpha mip PNGs and verbatim mip planes, 171 CARS/LIVERY PTG pairs, and 136 MATRIX PTG pairs. Numeric selector variants are embedded in the GLBs. Negative-control PNGs and approximate historical thumbnail previews are excluded.\n\nThe meshes retain all five serialized trees and alternate wheel/light states. Final game-render equivalence, some shader paths and UI usage remain open; see [the recovery report](../../research/original-recovery.md).\n')
    print(json.dumps({'cars':len(rows),'assets':sum(counts.values()),'counts':dict(counts),'result':'BUILD OK'}))
if __name__=='__main__':main()
