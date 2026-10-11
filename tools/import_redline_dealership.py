#!/usr/bin/env python3
"""Add verified Redline exports as independent editable dealership models.

Existing catalog entries and models are preserved, including later edits. No
performance values or vehicle categories are inferred from native configuration names.
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
        raise ValueError('Invalid Redline export record')
    identifier = row['code']
    if (len(identifier) > 400 or
            not re.fullmatch(r'[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*', identifier) or
            row.get('source_variant') not in ('base', 'addon') or
            row.get('source_profile') != 'redline-static-car-v1' or
            identifier.split('/')[0] != row.get('source_variant')):
        raise ValueError('Invalid Redline asset identifier/profile/variant')
    name = row.get('display_name')
    if not isinstance(name, str) or not name.strip() or len(name) > 500 or any(ord(c) < 32 for c in name):
        raise ValueError('Invalid literal Redline display name')
    # Native punctuation/case identities remain distinct in the editable namespace.
    digest = hashlib.sha256(identifier.encode()).hexdigest()[:16].upper()
    code = 'REDLINE_' + re.sub(r'[^A-Z0-9_]', '_', identifier.upper()) + '_' + digest
    if len(code) > 240:
        raise ValueError('Redline editable identifier is too long')
    collection = variant = row['source_variant']
    limits = row.get('claim_limits', [])
    if not isinstance(limits, list) or any(not isinstance(value, str) for value in limits):
        raise ValueError('Invalid Redline conversion claim limits')
    return dict(code=code, name=name,
                game='redline', gameLabel='Redline', sourceCode=row['code'],
                sourceCollection=collection, sourceVariant=variant,
                displayMode='textured-glb', bodyStyle='unknown', group=collection.upper(),
                year=None, topSpeed=None, bhp=None, kg=None, agility=None, accel=None,
                speed=None, weight=None, liveries=[], paint=None, sound=None,
                claimLimits=['Literal native configuration name; performance and vehicle category are not decoded.',
                             'Independent editable copy; native source files remain separate.', *limits])


def import_cars(source=ROOT / 'dealership/public/redline',
                destination=ROOT / 'dealership/dealership', upgrade_unedited=False):
    source, destination = Path(source), Path(destination)
    if (source.resolve() == destination.resolve() or source.resolve() in destination.resolve().parents
            or destination.resolve() in source.resolve().parents):
        raise ValueError('Source and editable destination must be separate directories')
    catalog_path, origins_path = destination / 'catalog.json', destination / 'origins.json'
    if any(p.is_symlink() for p in (destination, catalog_path, origins_path, destination / 'models')):
        raise ValueError('Editable dealership paths must not be symlinks')
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
        raise ValueError('Redline source index has no cars')
    added, seen, payloads, upgraded = [], set(), [], 0
    for row in index['cars']:
        entry = imported_entry(row)
        code = entry['code']
        if code in seen:
            raise ValueError('Redline export identifiers collide')
        seen.add(code)
        if not isinstance(row.get('file'), str):
            raise ValueError('Redline model path is invalid')
        relative = Path(row['file'])
        if (relative.is_absolute() or '..' in relative.parts or relative.as_posix() != row['code'] + '.glb'):
            raise ValueError('Redline model path is invalid')
        model = source / relative
        if (any(p.is_symlink() for p in (source, model, *model.parents) if p == source or source in p.parents) or
                source.resolve() not in model.resolve().parents):
            raise ValueError('Redline model path escapes the source folder')
        data = model.read_bytes()
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise ValueError('Redline source model differs from index hash/size')
        doc, _ = read_glb(data)
        if (doc.get('extras', {}).get('source_profile') != 'redline-static-car-v1' or
                doc['extras'].get('car') != row['code'] or
                doc['extras'].get('source_variant') != row['source_variant']):
            raise ValueError('Redline source GLB identity/profile differs from index')
        bake_car(code, data, source_mode=False)  # Validate even on a preserving repeat import.
        if code in existing:
            old = existing[code]
            if old.get('game') != 'redline' or old.get('sourceCode') != row['code']:
                raise ValueError('Redline identifier conflicts with an existing dealership entry')
            target = destination / 'models' / f'{code}.glb'
            if (target.is_symlink() or target.stat().st_nlink != 1 or
                    target.resolve().parent != (destination / 'models').resolve()):
                raise ValueError('Editable Redline model path is invalid')
            if not upgrade_unedited:
                continue
            working = target.read_bytes()
            origin = origin_entries.get(code)
            previous = origin.get('latestSource', origin.get('initialSource', {})) if origin else {}
            # Only an exact copy of its recorded source may be upgraded. User edits
            # (including metadata edits) remain owned by the working dealership.
            if sha(working) != previous.get('sha256') or sha(working) == row['sha256']:
                continue
            if previous.get('game') != 'redline' or previous.get('code') != row['code']:
                raise ValueError('Editable Redline source provenance conflicts')
            payloads.append((target, data, working))
            previous_doc, _ = read_glb(working)
            source_limits = previous_doc.get('extras', {}).get('claim_limits', [])
            old_limits = old.get('claimLimits', [])
            if any(not isinstance(values, list) or any(not isinstance(v, str) for v in values)
                   for values in (source_limits, old_limits)):
                raise ValueError('Editable Redline claim limit metadata is invalid')
            # The verified prior GLB identifies source-owned limits. Anything
            # else may be a custom catalog note; preserve it conservatively.
            custom_limits = [value for value in old_limits
                             if value not in source_limits and value not in entry['claimLimits'][:2]]
            old['claimLimits'] = list(dict.fromkeys([*entry['claimLimits'], *custom_limits]))
            origin.setdefault('sourceUpgrades', []).append({
                'fromSha256': previous['sha256'], 'toSha256': row['sha256']})
            origin['latestSource'] = {'game': 'redline', 'code': row['code'],
                                     'glb': 'public/redline/' + row['file'], 'sha256': row['sha256']}
            upgraded += 1
            continue
        target = destination / 'models' / f'{code}.glb'
        if target.exists() or target.is_symlink():
            raise ValueError('An uncatalogued dealership model occupies the Redline identifier')
        added.append(entry)
        payloads.append((target, data, None))
        origins['cars'].append({'code': code, 'initialSource': {
            'game': 'redline', 'code': row['code'],
            'glb': 'public/redline/' + row['file'], 'sha256': row['sha256']}})
    if not added and not upgraded:
        return 0
    original_catalog, original_origins = catalog_path.read_bytes(), origins_path.read_bytes()
    # Stage every copy and metadata before touching the working dealership.
    with tempfile.TemporaryDirectory(prefix='.redline-import-', dir=destination.parent) as temp:
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
    parser.add_argument('--source', type=Path, default=ROOT / 'dealership/public/redline')
    parser.add_argument('--destination', type=Path, default=ROOT / 'dealership/dealership')
    parser.add_argument('--upgrade-unedited', action='store_true',
                        help='Refresh only models equal to their recorded source; preserve edited models')
    args = parser.parse_args()
    try:
        count = import_cars(args.source, args.destination, args.upgrade_unedited)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Imported {count} independent editable Redline models; existing dealership entries preserved')
