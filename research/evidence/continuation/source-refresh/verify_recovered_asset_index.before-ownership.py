#!/usr/bin/env python3
"""Independent destination-side inventory and source-receipt parity audit."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def check(index):
    roster=json.loads((ROOT/'reference/ford/inventory.json').read_text())['cars'];names=[x['car'] for x in index['cars']]
    disk={p.name for p in (ROOT/'recovered/cars').iterdir() if p.is_dir()}
    if len(names)!=len(set(names)) or set(names)!=set(roster) or disk!=set(names):raise ValueError('roster/index/disk mismatch')
    for item in index['source_receipts'].values():
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('source receipt changed')
    counters=Counter();paths=set();manifests=[]
    for row in index['cars']:
        payload=(ROOT/row['manifest']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row['manifest_sha256']:raise ValueError('manifest hash mismatch')
        doc=json.loads(payload)
        if doc['car']!=row['car'] or len(doc['assets'])!=row['assets']:raise ValueError('manifest identity/count mismatch')
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
    receipts={k:json.loads((ROOT/v['path']).read_text()) for k,v in index['source_receipts'].items()};expected=set()
    for c in receipts['model_census']['cars']:
        expected.add(next((ROOT/'reference/ford/cars'/c['code']/'model').iterdir()).relative_to(ROOT).as_posix())
        expected.add('viewer/public/recovered/'+c['code']+'.glb')
        for t in c['textures']:
            expected.update('research/evidence/original-recovery/'+t[k] for k in ['png','raw_alpha_png'])
    for c in receipts['mips']['cars']:
        for m in c['extra_mip_levels']:expected.update('research/evidence/mip-continuation/'+m[k] for k in ['raw_plane','png'])
    for p in receipts['ptgs']['assets']:
        expected.add(p['reference_path']);expected.update(o['path'] for o in p['outputs'].values())
    for m in receipts['matrix']['assets']:
        expected.add(m['original_copy']);expected.update(m['outputs'][k]['path'] for k in ['csm0-swap-raw','csm0-swap-display'])
    if paths!=expected:raise ValueError('canonical source-receipt file set differs')
    return {'cars':len(names),'assets':len(paths),'counts':dict(counters),'producer_receipt_set_equality':True}


def main():
    p=ROOT/'recovered/index.json';index=json.loads(p.read_text());result=check(index)
    bad=copy.deepcopy(index);bad['cars'][0]['manifest_sha256']='0'*64
    try:check(bad)
    except ValueError:result['corrupt_manifest_hash_rejected']=True
    else:raise ValueError('corrupt manifest accepted')
    result.update(result='VERIFY OK',index_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (ROOT/'research/evidence/continuation/source-refresh/recovered-asset-index-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
