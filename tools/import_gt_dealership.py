#!/usr/bin/env python3
"""Add verified Gran Turismo exports as independent editable dealership models.

Existing catalog entries and models are preserved, including later edits. No
performance or retail names are inferred from community archive identifiers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from bake_models import ROOT, bake_car, read_glb


def sha(data):
    return hashlib.sha256(data).hexdigest()


def imported_entry(row):
    if not isinstance(row, dict) or not isinstance(row.get('code'), str):
        raise ValueError('Invalid GT export record')
    parts = row['code'].split('/')
    if len(parts) == 2 and parts[0] == 'arcade':
        collection, identifier = parts
        variant = 'arcade'
    elif len(parts) == 3 and parts[0] == 'simulation':
        collection, identifier, variant = parts
    else:
        raise ValueError('Invalid GT collection/variant identifier')
    if (not re.fullmatch(r'[a-z0-9_-]+', identifier) or
            variant not in ('day', 'night', 'arcade')):
        raise ValueError('Invalid GT asset identifier')
    code = 'GT_' + '_'.join(parts).upper().replace('-', '_')
    limits = row.get('claim_limits', [])
    if not isinstance(limits, list) or any(not isinstance(value, str) for value in limits):
        raise ValueError('Invalid GT conversion claim limits')
    return dict(code=code, name=f'{identifier} · {collection} · {variant}',
                game='gran-turismo', gameLabel='Gran Turismo', sourceCode=row['code'],
                sourceCollection=collection, sourceVariant=variant,
                displayMode='textured-glb', bodyStyle='unknown', group=collection.upper(),
                year=None, topSpeed=None, bhp=None, kg=None, agility=None, accel=None,
                speed=None, weight=None, liveries=[], paint=None, sound=None,
                claimLimits=['Archive asset identifier; retail car identity and performance not decoded.',
                             'Independent editable copy; native source files remain separate.', *limits])


def import_cars(source=ROOT / 'dealership/public/gran-turismo',
                destination=ROOT / 'dealership/dealership', upgrade_unedited=False):
    source, destination = Path(source), Path(destination)
    if (source.resolve() == destination.resolve() or source.resolve() in destination.resolve().parents
            or destination.resolve() in source.resolve().parents):
        raise ValueError('Source and editable destination must be separate directories')
    catalog_path, origins_path = destination / 'catalog.json', destination / 'origins.json'
    catalog = json.loads(catalog_path.read_text())
    origins = json.loads(origins_path.read_text())
    if not isinstance(catalog, list) or not catalog or origins.get('schema') != 1 or not isinstance(origins.get('cars'), list):
        raise ValueError('Existing editable dealership catalog/origins are invalid')
    existing = {car['code']: car for car in catalog}
    if len(existing) != len(catalog):
        raise ValueError('Existing editable codes are duplicated')
    origin_entries = {row['code']: row for row in origins['cars']}
    if len(origin_entries) != len(origins['cars']):
        raise ValueError('Existing editable origins are duplicated')
    index = json.loads((source / 'index.json').read_text())
    if not isinstance(index.get('cars'), list) or not index['cars']:
        raise ValueError('GT source index has no cars')
    added, seen, payloads, upgraded = [], set(), [], 0
    for row in index['cars']:
        entry = imported_entry(row)
        code = entry['code']
        if code in seen:
            raise ValueError('GT export identifiers collide')
        seen.add(code)
        if not isinstance(row.get('file'), str):
            raise ValueError('GT model path is invalid')
        relative = Path(row['file'])
        if (relative.is_absolute() or '..' in relative.parts or relative.as_posix() != row['code'] + '.glb'):
            raise ValueError('GT model path is invalid')
        model = source / relative
        if model.is_symlink() or source.resolve() not in model.resolve().parents:
            raise ValueError('GT model path escapes the source folder')
        data = model.read_bytes()
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise ValueError('GT source model differs from index hash/size')
        if code in existing:
            old = existing[code]
            if old.get('game') != 'gran-turismo' or old.get('sourceCode') != row['code']:
                raise ValueError('GT identifier conflicts with an existing dealership entry')
            if not upgrade_unedited:
                continue
            target = destination / 'models' / f'{code}.glb'
            if target.is_symlink() or target.resolve().parent != (destination / 'models').resolve():
                raise ValueError('Editable GT model path is invalid')
            working = target.read_bytes()
            origin = origin_entries.get(code)
            previous = origin.get('latestSource', origin.get('initialSource', {})) if origin else {}
            # Only an exact copy of its recorded source may be upgraded. User edits
            # (including metadata edits) remain owned by the working dealership.
            if sha(working) != previous.get('sha256') or sha(working) == row['sha256']:
                continue
            if previous.get('game') != 'gran-turismo' or previous.get('code') != row['code']:
                raise ValueError('Editable GT source provenance conflicts')
            bake_car(code, data, source_mode=False)
            payloads.append((target, data, working))
            previous_doc, _ = read_glb(working)
            source_limits = previous_doc.get('extras', {}).get('claim_limits', [])
            old_limits = old.get('claimLimits', [])
            if any(not isinstance(values, list) or any(not isinstance(v, str) for v in values)
                   for values in (source_limits, old_limits)):
                raise ValueError('Editable GT claim limit metadata is invalid')
            # The verified prior GLB identifies source-owned limits. Anything
            # else may be a custom catalog note; preserve it conservatively.
            custom_limits = [value for value in old_limits
                             if value not in source_limits and value not in entry['claimLimits'][:2]]
            old['claimLimits'] = list(dict.fromkeys([*entry['claimLimits'], *custom_limits]))
            origin.setdefault('sourceUpgrades', []).append({
                'fromSha256': previous['sha256'], 'toSha256': row['sha256']})
            origin['latestSource'] = {'game': 'gran-turismo', 'code': row['code'],
                                     'glb': 'public/gran-turismo/' + row['file'], 'sha256': row['sha256']}
            upgraded += 1
            continue
        target = destination / 'models' / f'{code}.glb'
        if target.exists() or target.is_symlink():
            raise ValueError('An uncatalogued dealership model occupies the GT identifier')
        bake_car(code, data, source_mode=False)  # Fail before any destination mutation.
        added.append(entry)
        payloads.append((target, data, None))
        origins['cars'].append({'code': code, 'initialSource': {
            'game': 'gran-turismo', 'code': row['code'],
            'glb': 'public/gran-turismo/' + row['file'], 'sha256': row['sha256']}})
    if not added and not upgraded:
        return 0
    original_catalog, original_origins = catalog_path.read_bytes(), origins_path.read_bytes()
    # Stage every copy and metadata before touching the working dealership.
    with tempfile.TemporaryDirectory(prefix='.gt-import-', dir=destination.parent) as temp:
        stage = Path(temp)
        for target, data, _ in payloads:
            (stage / target.name).write_bytes(data)
        (stage / 'catalog.json').write_text(json.dumps(catalog + added, indent=1) + '\n')
        (stage / 'origins.json').write_text(json.dumps(origins, indent=1) + '\n')
        moved = []
        try:
            for target, _, previous_data in payloads:
                (stage / target.name).replace(target)
                moved.append((target, previous_data))
            (stage / 'origins.json').replace(origins_path)
            (stage / 'catalog.json').replace(catalog_path)
        except BaseException:
            catalog_path.write_bytes(original_catalog)
            origins_path.write_bytes(original_origins)
            for target, previous_data in moved:
                if previous_data is None:
                    target.unlink()
                else:
                    target.write_bytes(previous_data)
            raise
    return len(added) + upgraded


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'dealership/public/gran-turismo')
    parser.add_argument('--destination', type=Path, default=ROOT / 'dealership/dealership')
    parser.add_argument('--upgrade-unedited', action='store_true',
                        help='Refresh only models equal to their recorded source; preserve edited models')
    args = parser.parse_args()
    try:
        count = import_cars(args.source, args.destination, args.upgrade_unedited)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Imported {count} independent editable GT models; existing dealership entries preserved')
