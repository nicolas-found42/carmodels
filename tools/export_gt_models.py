#!/usr/bin/env python3
"""Export all retained GT1 native pairs as bounded, independently indexed source GLBs."""
import argparse
import json
from pathlib import Path
import re
import tempfile

from gt_model import LIMITS, build_glb, sha

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'gran-turismo/cars'
OUTPUT = ROOT/'dealership/public/gran-turismo'


def safe_file(root, name):
    if not isinstance(name,str):
        raise ValueError('GT export path is not a string')
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or not re.fullmatch(r'[a-zA-Z0-9_./-]+',name):
        raise ValueError('GT export path outside allowed relative profile')
    target = root/path
    if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
        raise ValueError('GT export path outside root or symlink')
    return target


def export(source=SOURCE, output=OUTPUT, check=False):
    source, output = Path(source), Path(output)
    if source.resolve().is_relative_to(output.resolve()) or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('GT export output overlaps native source')
    index_data = (source/'index.json').read_bytes()
    index = json.loads(index_data)
    if index.get('game') != 'gran-turismo' or not index.get('cars'):
        raise ValueError('GT native index game/coverage missing')
    entries, seen = [], set()
    # Stage every byte before replacing an export; invalid source leaves existing outputs intact.
    with tempfile.TemporaryDirectory(prefix='gt-models-',dir=output.parent if output.parent.is_dir() else None) as temporary:
        stage = Path(temporary)
        for car in index['cars']:
            identity = car['id']
            if identity in seen:
                raise ValueError('Duplicate GT native pair ID')
            seen.add(identity)
            files = {}
            for asset in car['assets']:
                target = safe_file(source,asset['file'])
                data = target.read_bytes()
                if len(data) != asset['decoded_bytes'] or sha(data) != asset['sha256']:
                    raise ValueError('GT native asset differs from extraction pin: '+asset['file'])
                if target.suffix in files:
                    raise ValueError('Duplicate GT native asset type')
                files[target.suffix] = data
            if set(files) != {'.car','.tex'}:
                raise ValueError('GT native pair missing CAR/CTEX')
            glb, records = build_glb(files['.car'],files['.tex'],identity)
            name = identity+'.glb'
            target = safe_file(stage,name)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(glb)
            entries.append({'code':identity,'file':name,'sha256':sha(glb),'bytes':len(glb),'records':records,
                            'display_name':car['code']+' · '+car['variant'],
                            'source_profile':'gran-turismo-native-candidate',
                            'source_variant':car['variant'] if car['mode']=='simulation' else 'arcade',
                            'source_mode':car['mode'],'source_code':car['code'],
                            'source_car_sha256':sha(files['.car']),'source_tex_sha256':sha(files['.tex']),
                            'claim_limits':LIMITS})
        report = {'schema':1,'game':'gran-turismo','source_index_sha256':sha(index_data),
                  'status':'Native body LODs and shared native wheel templates with source colour0 CTEX; rendered equivalence remains unverified.',
                  'claim_limits':LIMITS,'cars':entries}
        (stage/'index.json').write_text(json.dumps(report,indent=2)+'\n')
        if (source/'index.json').read_bytes() != index_data:
            raise ValueError('GT native index changed during export')
        expected = {p.relative_to(stage).as_posix():p for p in stage.rglob('*') if p.is_file()}
        if check:
            actual = {p.relative_to(output).as_posix():p for p in output.rglob('*') if p.is_file()}
            if set(expected) != set(actual):
                raise ValueError('GT source export file inventory differs')
            for name,path in expected.items():
                if actual[name].is_symlink() or actual[name].read_bytes() != path.read_bytes():
                    raise ValueError('GT source export byte comparison differs: '+name)
        else:
            if output.is_symlink():
                raise ValueError('GT export output is symlink')
            if output.exists():
                actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
                if actual-set(expected):
                    raise ValueError('GT output contains unrelated files; refusing replacement')
                if any(p.is_symlink() for p in output.rglob('*')):
                    raise ValueError('GT output contains symlink')
            output.mkdir(parents=True,exist_ok=True)
            for name,path in expected.items():
                target = safe_file(output,name)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(path.read_bytes())
    return {'models':len(entries),'lods':sum(len(c['records']) for c in entries),
            'triangles':sum(r['triangles'] for c in entries for r in c['records']),
            'bytes':sum(c['bytes'] for c in entries),'source_index_sha256':sha(index_data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    result = export(args.source,args.output,args.check)
    print(('VERIFY OK' if args.check else 'EXPORTED')+': '+json.dumps(result,sort_keys=True))


if __name__ == '__main__':
    main()
