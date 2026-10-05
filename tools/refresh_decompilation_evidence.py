#!/usr/bin/env python3
"""Snapshot and byte-check newer read-only decompilation resources for recovery."""
import static_inputs
import difflib
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = static_inputs.bundle_path()
OUT = ROOT/'research/evidence/continuation/source-refresh'
EXPORT = SOURCE/'.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    inventory_bytes = (EXPORT/'inventory.json').read_bytes()
    inventory = json.loads(inventory_bytes)
    manifest_bytes = (EXPORT/'decompilation/manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    old_bytes = (SOURCE/'.scratch/evidence/static-export.json').read_bytes()
    old = json.loads(old_bytes)
    elf = (SOURCE/'games/ford-racing-2/extracted/SLES_517.05').read_bytes()
    if any(x['executable_sha256'] != sha(elf) for x in (inventory,manifest,old)):
        raise ValueError('executable identity mismatch')
    phoff = struct.unpack_from('<I',elf,28)[0]
    stride,count = struct.unpack_from('<HH',elf,42)
    loads = []
    for i in range(count):
        kind,offset,va,_,size,*_ = struct.unpack_from('<8I',elf,phoff+i*stride)
        if kind == 1:loads.append((va,va+size,offset))
    checked = 0
    for f in inventory['functions']:
        for ins in f['instructions']:
            address = int(ins['address'],16)
            payload = bytes.fromhex(ins['bytes'])
            blocks = [b for b in loads if b[0] <= address and address+len(payload) <= b[1]]
            if len(blocks) != 1:raise ValueError('ambiguous instruction location')
            b = blocks[0]; offset = b[2]+address-b[0]
            if elf[offset:offset+len(payload)] != payload:raise ValueError('instruction differs from ELF')
            checked += 1
    for f in manifest['functions']:
        data = (EXPORT/'decompilation'/f['path']).read_bytes()
        if len(data) != f['bytes'] or sha(data) != f['sha256']:
            raise ValueError('pseudocode differs from manifest')
    entries = {f['entry'] for f in inventory['functions']}
    old_entries = {f['entry'] for f in old['functions']}
    selected = ['00121cd0','001213d8','00121590','00122300','00115560','00127c00','00128518',
                '00119df0','0019a1b8','0019a7b8','0019b900','0019bfe0','0019c680',
                '00229080','002296c8','00229d50','00128ca0','00128e88',
                '00220fe0','0021fd50','0015b280','00174300']
    (OUT/'functions').mkdir(exist_ok=True)
    selected_rows = []
    for entry in selected:
        file = EXPORT/'decompilation/functions'/(entry+'.c')
        if not file.exists():continue
        data = file.read_bytes();(OUT/'functions'/file.name).write_bytes(data)
        old_file = SOURCE/'.scratch/mesh/codex-root/decompile-all-02/functions'/file.name
        old_data = old_file.read_bytes() if old_file.exists() else b''
        diff = ''.join(difflib.unified_diff(old_data.decode().splitlines(True),data.decode().splitlines(True),fromfile='historical/'+file.name,tofile='typed/'+file.name))
        (OUT/(entry+'.diff')).write_text(diff)
        selected_rows.append({'entry':entry,'old_sha256':sha(old_data) if old_data else None,
                              'new_sha256':sha(data),'bytes':len(data),'changed':old_data != data})
    candidates = []
    for p in sorted((SOURCE/'notes/evidence').glob('fr2-*/README.md')):
        text = p.read_text();candidates.append({'id':str(p.relative_to(SOURCE)),
                  'text':text if len(text) <= 1950 else text[:1450]+'\n[bounded excerpt; middle omitted]\n'+text[-400:]})
    (OUT/'resource-candidates.json').write_text(json.dumps(candidates,indent=2)+'\n')
    result = {'source_head':json.loads((OUT/'refresh-identity.json').read_text())['source_head'],
              'executable_sha256':sha(elf),'inventory_path':str(EXPORT/'inventory.json'),
              'inventory_sha256':sha(inventory_bytes),'manifest_sha256':sha(manifest_bytes),
              'historical_inventory_sha256':sha(old_bytes),'historical_functions':len(old_entries),
              'new_functions':len(entries),'new_only_entries':sorted(entries-old_entries),
              'old_only_entries':sorted(old_entries-entries),'instructions_checked':checked,
              'pseudocode_hashes_checked':len(manifest['functions']),'selected':selected_rows,
              'claim_limits':manifest['claim_limits'],'failures':0}
    (OUT/'refresh-identity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['source_head','historical_functions','new_functions','instructions_checked','pseudocode_hashes_checked','failures']}))


if __name__ == '__main__':main()
