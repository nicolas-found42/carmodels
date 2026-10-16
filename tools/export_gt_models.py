#!/usr/bin/env python3
"""Export one day-derived GT1 model per vehicle family, retaining native provenance."""
import argparse
import json
from pathlib import Path
import re
import tempfile

from gt_model import LIMITS, build_glb, sha
from gt_metadata import load_database, model_metadata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'games/gran-turismo/cars'
OUTPUT = ROOT/'dealership/public/gran-turismo'
SPECIAL_FAMILIES = {'_0logn', '_lcupn'}


def canonical_pairs(cars):
    """Keep distinct source families; arcade aliases require exact CAR+CTEX pins."""
    seen, families, arcade = set(), {}, []
    for car in cars:
        identity = car['id']
        if identity in seen:
            raise ValueError('Duplicate GT native pair ID')
        seen.add(identity)
        if car['mode'] == 'simulation':
            if car['variant'] not in ('day', 'night') or identity != f"simulation/{car['code']}/{car['variant']}":
                raise ValueError('Invalid GT simulation identity')
            families.setdefault(car['code'], {})[car['variant']] = car
        elif car['mode'] == 'arcade' and identity == 'arcade/' + car['code']:
            arcade.append(car)
        else:
            raise ValueError('Invalid GT native collection')
    aliases, signatures = {}, {}
    for code, editions in families.items():
        if 'day' not in editions:
            raise ValueError('GT family has no canonical day source')
        aliases[code] = [row['id'] for row in editions.values()]
        row = editions['day']
        signature = tuple(sorted((Path(a['file']).suffix, a['sha256']) for a in row['assets']))
        signatures.setdefault(signature, set()).add(code)
    for row in arcade:
        signature = tuple(sorted((Path(a['file']).suffix, a['sha256']) for a in row['assets']))
        matches = signatures.get(signature, set())
        if not matches:
            raise ValueError('GT arcade pair has no exact simulation day match')
        # Different native families can have byte-identical bodies/textures.
        # Keep those families distinct; resolve the old arcade ID deterministically.
        aliases[sorted(matches)[0]].append(row['id'])
    return [(editions['day'], sorted(aliases[code])) for code, editions in families.items()
            if code not in SPECIAL_FAMILIES]


def install(stage, output, expected):
    """Replace only indexed exports; quarantine originals until installation verifies."""
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob('*')):
        raise ValueError('GT export output contains symlink')
    actual = {p.relative_to(output).as_posix(): p for p in output.rglob('*') if p.is_file()}
    owned = {'index.json'}
    if actual:
        prior = json.loads((output/'index.json').read_text())
        if prior.get('game') != 'gran-turismo':
            raise ValueError('GT output index has wrong game')
        for row in prior['cars']:
            target = safe_file(output, row['file'])
            if target.stat().st_size != row['bytes'] or sha(target.read_bytes()) != row['sha256']:
                raise ValueError('GT prior export differs from its pin')
            owned.add(row['file'])
        if set(actual)-owned:
            raise ValueError('GT output contains unrelated files; refusing replacement')
    output.mkdir(parents=True, exist_ok=True)
    backup = stage/'prior'
    moved, installed = [], []
    try:
        for name, path in actual.items():
            saved = safe_file(backup, name)
            saved.parent.mkdir(parents=True, exist_ok=True)
            path.replace(saved)
            moved.append((path, saved))
        for name, path in expected.items():
            target = safe_file(output, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            installed.append(target)
            target.write_bytes(path.read_bytes())
            if target.read_bytes() != path.read_bytes():
                raise ValueError('GT installation byte comparison differs')
    except BaseException:
        for target in installed:
            target.unlink(missing_ok=True)
        for target, saved in moved:
            saved.replace(target)
        raise


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
    database = load_database(source / '_metadata') if index.get('schema', 1) >= 2 else None
    entries, native_files = [], {}
    # Stage every byte before replacing an export; invalid source leaves existing outputs intact.
    with tempfile.TemporaryDirectory(prefix='gt-models-',dir=output.parent if output.parent.is_dir() else None) as temporary:
        stage = Path(temporary)
        pairs = canonical_pairs(index['cars'])
        for car in index['cars']:
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
            native_files[car['id']] = files
        for car, aliases in pairs:
            identity = 'simulation/' + car['code']
            files = native_files[car['id']]
            metadata = None
            if database is not None:
                colour_count = int.from_bytes(files['.tex'][14:16], 'little')
                metadata = model_metadata(database, car['code'], list(files['.tex'][16:16 + colour_count]))
                if metadata != car.get('native_metadata'):
                    raise ValueError('GT native decoded metadata differs from pinned source: ' + car['id'])
            glb, records = build_glb(files['.car'],files['.tex'],identity, metadata=metadata)
            name = identity+'.glb'
            target = safe_file(stage,name)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(glb)
            entries.append({'code':identity,'file':name,'sha256':sha(glb),'bytes':len(glb),'records':records,
                            'display_name':(metadata['identity']['name'] if metadata and metadata['identity']['status'] == 'verified'
                                            else car['code']), 'aliases':aliases,
                            'native_metadata': metadata,
                            'canonical_source_id':car['id'],
                            'source_profile':'gran-turismo-native-candidate',
                            'source_variant':'canonical',
                            'source_mode':car['mode'],'source_code':car['code'],
                            'source_car_sha256':sha(files['.car']),'source_tex_sha256':sha(files['.tex']),
                            'claim_limits':LIMITS})
        report = {'schema':2,'game':'gran-turismo','source_index_sha256':sha(index_data),
                  'selection':{'edition':'day','colour_set':0,'excluded_families':sorted(SPECIAL_FAMILIES)},
                  'arcade_alias_policy':'Lexicographically first simulation family with exact day CAR and CTEX hashes; other matching families stay distinct.',
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
            install(stage, output, expected)
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
