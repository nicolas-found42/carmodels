#!/usr/bin/env python3
"""Extract bounded, hashed PCSX2 capture members for independent source joins."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('state',type=Path)
    p.add_argument('--label',required=True)
    p.add_argument('--output',type=Path,default=ROOT/'research/evidence/continuation/runtime/linux')
    a=p.parse_args()
    if not re.fullmatch('[a-z][a-z0-9-]{0,40}',a.label):raise ValueError('invalid output label')
    a.output.mkdir(exist_ok=True)
    sizes={'eeMemory.bin':32*1024*1024,'Scratchpad.bin':16384,'vu1MicroMem.bin':16384,'vu1Memory.bin':16384,'PCSX2 Savestate Version.id':36}
    optional={'GS.bin','Screenshot.png'}
    rows=[]
    with zipfile.ZipFile(a.state) as z:
        members=z.infolist()
        if len({i.filename for i in members})!=len(members):raise ValueError('duplicate ZIP members')
        if sum(i.file_size for i in members)>256*1024*1024:raise ValueError('savestate decompression exceeds bound')
        if z.testzip() is not None:raise ValueError('savestate ZIP CRC mismatch')
        for name,expected in sizes.items():
            if z.getinfo(name).file_size!=expected:raise ValueError('unexpected capture member size '+name)
        for name in [*sizes,*sorted(optional)]:
            info=z.getinfo(name)
            if not 0<info.file_size<64*1024*1024:raise ValueError('capture member outside bounds')
            data=z.read(name)
            target=a.output/(a.label+'-'+name.replace(' ','-'))
            target.write_bytes(data)
            rows.append({'member':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'output':str(target)})
    result={'state':str(a.state.resolve()),'state_sha256':hashlib.sha256(a.state.read_bytes()).hexdigest(),
            'members':rows,'zip_crc_failures':0,
            'limits':['Raw capture members only; no CPU register layout or guest state is decoded here.']}
    (a.output/(a.label+'-state-identity.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'state_sha256':result['state_sha256'],'members':len(rows),'zip_crc_failures':0}))


if __name__=='__main__':main()
