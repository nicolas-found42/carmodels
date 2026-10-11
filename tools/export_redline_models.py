#!/usr/bin/env python3
"""Convert hash-pinned Redline configurations into indexed source GLBs."""
import argparse
import json
from pathlib import Path
import re
import tempfile

from redline_model import LIMITS, PROFILE, NoDrawableGeometry, build_glb, safe_file, sha

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'redline/cars'
OUTPUT = ROOT / 'dealership/public/redline'


def identifier(car):
    stem = re.sub(r'[^a-zA-Z0-9_-]', '_', Path(car['file']).stem)[:80] or 'car'
    digest = sha(car['id'].encode())[:12]
    if car['group'] == 'base':
        return 'base/' + stem + '_' + digest
    if car['group'] != 'addon':
        raise ValueError('Invalid native Redline collection')
    parts = car['package'].split('/')
    package_name = parts[1] if parts[0] == 'addons' and len(parts) > 1 else parts[-1]
    package = re.sub(r'[^a-zA-Z0-9_-]', '_', package_name)[:80] or 'package'
    return 'addon/' + package + '/' + stem + '_' + digest


def export(source=SOURCE, output=OUTPUT, check=False):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or source.resolve() in output.resolve().parents or output.resolve() in source.resolve().parents:
        raise ValueError('Redline export overlaps native source')
    if source.is_symlink() or output.is_symlink():
        raise ValueError('Redline source/output is a symlink')
    index_data = safe_file(source, 'index.json').read_bytes()
    index = json.loads(index_data)
    if index.get('game') != 'redline' or not index.get('cars'):
        raise ValueError('Native Redline index has no configurations')
    entries, seen, non_drawable = [], set(), []
    if not check:
        output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='redline-models-', dir=output.parent if output.parent.is_dir() else None) as temporary:
        stage = Path(temporary) / 'next'
        stage.mkdir()
        for car in index['cars']:
            code = identifier(car)
            if code in seen:
                raise ValueError('Duplicate Redline export identity')
            seen.add(code)
            try:
                data, records, warnings, name = build_glb(source, index, car, code)
            except NoDrawableGeometry as exc:
                non_drawable.append({'code': code, 'native_car_id': car['id'], 'display_name': exc.name,
                                     'source_variant': car['group'], 'native_config_sha256': car['sha256'],
                                     'reason': str(exc), 'native_resources': exc.resources, 'warnings': exc.warnings})
                continue
            target = safe_file(stage, code + '.glb')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entries.append({'code': code, 'file': code + '.glb', 'bytes': len(data), 'sha256': sha(data),
                            'records': records, 'display_name': name, 'source_profile': PROFILE,
                            'source_variant': car['group'], 'native_car_id': car['id'],
                            'warnings': warnings, 'claim_limits': LIMITS + [f"{w['kind']}: {w['resource']} — {w['reason']}" for w in warnings]})
        report = {'schema': 1, 'game': 'redline', 'source_index_sha256': sha(index_data),
                  'claim_limits': LIMITS, 'cars': entries, 'non_drawable_configurations': non_drawable}
        (stage / 'index.json').write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n')
        if safe_file(source, 'index.json').read_bytes() != index_data:
            raise ValueError('Native index changed during conversion')
        expected = {p.relative_to(stage).as_posix(): p for p in stage.rglob('*') if p.is_file()}
        actual = {p.relative_to(output).as_posix(): p for p in output.rglob('*') if p.is_file()} if output.exists() else {}
        if any(p.is_symlink() for p in output.rglob('*')):
            raise ValueError('Redline output contains symlink')
        if check:
            if set(expected) != set(actual):
                raise ValueError('Redline export inventory differs')
            for name, path in expected.items():
                if actual[name].read_bytes() != path.read_bytes():
                    raise ValueError('Redline export bytes differ: ' + name)
        else:
            if set(actual) - set(expected):
                raise ValueError('Redline output contains unrelated files')
            backup = Path(temporary) / 'previous'
            moved = False
            try:
                if output.exists():
                    output.replace(backup)
                    moved = True
                stage.replace(output)
            except BaseException:
                if moved:
                    backup.replace(output)
                raise
    return {'configurations': len(seen), 'models': len(entries), 'non_drawable_configurations': len(non_drawable),
            'triangles': sum(r['triangles'] for c in entries for r in c['records']),
            'bytes': sum(c['bytes'] for c in entries), 'warnings': sum(len(c['warnings']) for c in entries),
            'source_index_sha256': sha(index_data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(('VERIFY OK: ' if args.check else 'EXPORTED: ') + json.dumps(export(args.source, args.output, args.check), sort_keys=True))


if __name__ == '__main__':
    main()
