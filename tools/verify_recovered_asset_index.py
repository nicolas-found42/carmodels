#!/usr/bin/env python3
"""Independent destination-side inventory and source-receipt parity audit."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def expected_records(receipts):
    """Derive ownership, types and metadata independently from producer receipts."""
    by_car={c['code']:{} for c in receipts['model_census']['cars']}
    def add(car,path,kind,digest,**metadata):
        if path in by_car[car]:raise ValueError('duplicate producer path for car')
        by_car[car][path]={'path':path,'kind':kind,'sha256':digest,
                           'bytes':(ROOT/path).stat().st_size,**metadata}
    for c in receipts['model_census']['cars']:
        code=c['code'];models=list((ROOT/'reference/ford/cars'/code/'model').iterdir())
        if len(models)!=1:raise ValueError('ambiguous original model')
        add(code,models[0].relative_to(ROOT).as_posix(),'original_model',c['sha256'])
        g=next(x for x in receipts['glbs']['cars'] if x['code']==code)
        add(code,'viewer/public/recovered/'+g['file'],'glb',g['sha256'])
        for t in c['textures']:
            for key,kind in [('png','model_texture_display'),('raw_alpha_png','model_texture_raw')]:
                add(code,'research/evidence/original-recovery/'+t[key],kind,t[key+'_sha256'],
                    texture_index=t['index'],texture_name=t['name'],level=0)
    for c in receipts['mips']['cars']:
        for m in c['extra_mip_levels']:
            meta={'texture_index':m['texture_index'],'texture_name':m['texture_name'],
                  'level':m['level'],'source_file_offset':m['source_file_offset']}
            add(c['car'],'research/evidence/mip-continuation/'+m['raw_plane'],'mip_plane',m['source_sha256'],**meta)
            add(c['car'],'research/evidence/mip-continuation/'+m['png'],'mip_stored_alpha',m['png_sha256'],**meta)
    for p in receipts['ptgs']['assets']:
        meta={'source_archive_path':p['source_path']};code=p['car_code']
        add(code,p['reference_path'],'original_'+p['role'],p['sha256'],**meta)
        for key,o in p['outputs'].items():add(code,o['path'],p['role']+'_'+key,o['sha256'],**meta)
    for m in receipts['matrix']['assets']:
        if m['authoritative_palette_lookup']!='csm0-swap':raise ValueError('unexpected MATRIX palette contract')
        meta={'source_archive_path':m['source']};code=m['car']
        add(code,m['original_copy'],'original_matrix',m['source_sha256'],**meta)
        for key in ['csm0-swap-raw','csm0-swap-display']:
            o=m['outputs'][key];add(code,o['path'],'matrix_'+key,o['sha256'],**meta)
    return by_car


def check(index, manifest_overrides=None):
    if index['schema']!='fr2-canonical-recovered-asset-index/v1' or index.get('render_fidelity_complete') is not False:
        raise ValueError('index schema/fidelity declaration mismatch')
    if index['status']!='Asset/index integrity checked. Rendering-fidelity completion not asserted.':
        raise ValueError('index status declaration mismatch')
    roster=json.loads((ROOT/'reference/ford/inventory.json').read_text())['cars'];names=[x['car'] for x in index['cars']]
    disk={p.name for p in (ROOT/'recovered/cars').iterdir() if p.is_dir()}
    if len(names)!=len(set(names)) or set(names)!=set(roster) or disk!=set(names):raise ValueError('roster/index/disk mismatch')
    for item in index['source_receipts'].values():
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('source receipt changed')
    receipts={k:json.loads((ROOT/v['path']).read_text()) for k,v in index['source_receipts'].items()}
    expected=expected_records(receipts)
    counters=Counter();paths=set();manifests=[]
    for row in index['cars']:
        payload=(manifest_overrides or {}).get(row['manifest'])
        if payload is None:payload=(ROOT/row['manifest']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row['manifest_sha256']:raise ValueError('manifest hash mismatch')
        doc=json.loads(payload)
        if doc['schema']!='fr2-canonical-recovered-asset-index/v1' or doc.get('render_fidelity_complete') is not False:
            raise ValueError('manifest schema/fidelity declaration mismatch')
        if doc['status']!='Recovered source assets and interoperable GLB; final game-render fidelity remains incomplete.':
            raise ValueError('manifest status declaration mismatch')
        if doc['limits']!=[
                'glTF materials, normalized normals, strip winding and retained runtime-state trees still carry the documented rendering limits.',
                'MATRIX and LIVERY paths are associated by verified archive/roster basenames; numeric selector-to-UI-label assignment is separate.',
                'Display-alpha PNGs are inspection conversions. Original source bytes and stored-alpha outputs are retained. Negative-control images and reconstructed thumbnail previews are excluded.']:
            raise ValueError('manifest limitation declaration mismatch')
        if doc['car']!=row['car'] or len(doc['assets'])!=row['assets']:raise ValueError('manifest identity/count mismatch')
        actual={a['path']:a for a in doc['assets']}
        if actual!=expected[row['car']]:raise ValueError('per-car producer ownership/type/metadata mismatch')
        c=next(c for c in receipts['model_census']['cars'] if c['code']==row['car'])
        v=next(c for c in receipts['variants']['cars'] if c['car']==row['car'])
        if doc['source_model_sha256']!=c['sha256'] or doc['numeric_texture_variants']!=v['variants'] or row['texture_selectors']!=v['complete_selectors']:
            raise ValueError('source model or selector metadata mismatch')
        per=Counter()
        for a in doc['assets']:
            path=ROOT/a['path']
            if not path.resolve().is_relative_to(ROOT) or a['path'] in paths:raise ValueError('unsafe/duplicate path')
            if '/negative-controls/' in a['path'] or 'reference-preview' in a['path']:raise ValueError('diagnostic image in canonical assets')
            data=path.read_bytes()
            if len(data)!=a['bytes'] or hashlib.sha256(data).hexdigest()!=a['sha256']:raise ValueError('asset hash/size mismatch')
            paths.add(a['path']);per[a['kind']]+=1
        if dict(per)!=doc['counts']:raise ValueError('per-car category count mismatch')
        counters.update(per);manifests.append(doc)
    if dict(counters)!=index['counts'] or len(paths)!=index['total_assets']:raise ValueError('total counts mismatch')
    # Independently derive the complete canonical path set from producer receipts.
    expected_paths=set()
    for c in receipts['model_census']['cars']:
        expected_paths.add(next((ROOT/'reference/ford/cars'/c['code']/'model').iterdir()).relative_to(ROOT).as_posix())
        expected_paths.add('viewer/public/recovered/'+c['code']+'.glb')
        for t in c['textures']:
            expected_paths.update('research/evidence/original-recovery/'+t[k] for k in ['png','raw_alpha_png'])
    for c in receipts['mips']['cars']:
        for m in c['extra_mip_levels']:expected_paths.update('research/evidence/mip-continuation/'+m[k] for k in ['raw_plane','png'])
    for p in receipts['ptgs']['assets']:
        expected_paths.add(p['reference_path']);expected_paths.update(o['path'] for o in p['outputs'].values())
    for m in receipts['matrix']['assets']:
        expected_paths.add(m['original_copy']);expected_paths.update(m['outputs'][k]['path'] for k in ['csm0-swap-raw','csm0-swap-display'])
    if paths!=expected_paths:raise ValueError('canonical source-receipt file set differs')
    return {'cars':len(names),'assets':len(paths),'counts':dict(counters),'producer_receipt_set_equality':True,'per_car_producer_record_equality':True}


def main():
    p=ROOT/'recovered/index.json';index=json.loads(p.read_text());result=check(index)
    bad=copy.deepcopy(index);bad['cars'][0]['manifest_sha256']='0'*64
    try:check(bad)
    except ValueError:result['corrupt_manifest_hash_rejected']=True
    else:raise ValueError('corrupt manifest accepted')
    # Rehash two swapped original-model records: global paths/counts remain valid.
    bad=copy.deepcopy(index);overrides={};docs=[]
    for row in bad['cars'][:2]:docs.append(json.loads((ROOT/row['manifest']).read_text()))
    positions=[next(i for i,a in enumerate(d['assets']) if a['kind']=='original_model') for d in docs]
    docs[0]['assets'][positions[0]],docs[1]['assets'][positions[1]]=docs[1]['assets'][positions[1]],docs[0]['assets'][positions[0]]
    for row,doc in zip(bad['cars'][:2],docs):
        payload=(json.dumps(doc,indent=2)+'\n').encode();overrides[row['manifest']]=payload
        row['manifest_sha256']=hashlib.sha256(payload).hexdigest()
    try:check(bad,overrides)
    except ValueError as e:
        if str(e)!='per-car producer ownership/type/metadata mismatch':raise
        result['rehashed_cross_car_model_swap_rejected']=True
    else:raise ValueError('cross-car model swap accepted')
    for key,value in [('schema','invalid-control'),('render_fidelity_complete',True),('status','Complete original renderer'),('limits',[])]:
        bad=copy.deepcopy(index);row=bad['cars'][0];doc=json.loads((ROOT/row['manifest']).read_text());doc[key]=value
        payload=(json.dumps(doc,indent=2)+'\n').encode();row['manifest_sha256']=hashlib.sha256(payload).hexdigest()
        try:check(bad,{row['manifest']:payload})
        except ValueError as e:
            if 'declaration mismatch' not in str(e):raise
        else:raise ValueError('changed manifest declaration accepted')
    result['rehashed_schema_fidelity_status_limits_controls_rejected']=True
    result.update(result='VERIFY OK',index_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (ROOT/'research/evidence/continuation/source-refresh/recovered-asset-index-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
