#!/usr/bin/env python3
"""Add verified Gran Turismo exports as independent editable dealership models.

Existing catalog entries and models are preserved, including later edits. No
performance or retail names are inferred from community archive identifiers.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile

from bake_models import ROOT, bake_car, read_glb
from gt_metadata import validate_model_metadata


def sha(data):
    return hashlib.sha256(data).hexdigest()


def imported_entry(row):
    if not isinstance(row, dict) or not isinstance(row.get('code'), str):
        raise ValueError('Invalid GT export record')
    parts = row['code'].split('/')
    if len(parts) == 2 and parts[0] == 'simulation':
        collection, identifier = parts
        variant = 'canonical'
    elif len(parts) == 2 and parts[0] == 'arcade':
        collection, identifier = parts
        variant = 'arcade'
    elif len(parts) == 3 and parts[0] == 'simulation':
        collection, identifier, variant = parts
    else:
        raise ValueError('Invalid GT collection/variant identifier')
    if (not re.fullmatch(r'[a-z0-9_-]+', identifier) or
            variant not in ('day', 'night', 'arcade', 'canonical')):
        raise ValueError('Invalid GT asset identifier')
    code = 'GT_' + '_'.join(parts).upper().replace('-', '_')
    limits = row.get('claim_limits', [])
    if not isinstance(limits, list) or any(not isinstance(value, str) for value in limits):
        raise ValueError('Invalid GT conversion claim limits')
    aliases = row.get('aliases', [])
    if not isinstance(aliases, list) or any(not isinstance(a, str) for a in aliases):
        raise ValueError('Invalid GT aliases')
    alias_codes = [imported_entry({'code': alias})['code'] for alias in aliases]
    metadata = row.get('native_metadata')
    if metadata is not None:
        validate_model_metadata(metadata)
        if collection != 'simulation' or metadata['provenance']['native_code'] != identifier.removeprefix('_'):
            raise ValueError('GT metadata is detached from source model code')
    verified = metadata is not None and metadata['identity']['status'] == 'verified'
    specifications = metadata['specifications'] if verified else None
    fallback_name = identifier if variant == 'canonical' else f'{identifier} · {collection} · {variant}'
    return dict(code=code, name=metadata['identity']['name'] if verified else fallback_name,
                game='gran-turismo', gameLabel='Gran Turismo', sourceCode=row['code'],
                sourceAliases=alias_codes,
                sourceCollection=collection, sourceVariant=variant,
                displayMode='textured-glb', bodyStyle='unknown', group=collection.upper(),
                nativeMetadata=copy.deepcopy(metadata), specifications=copy.deepcopy(specifications),
                colourVariants=copy.deepcopy(metadata['colour_variants']) if metadata else [],
                year=None, topSpeed=None, bhp=specifications['power_hp_game'] if specifications else None,
                kg=specifications['mass_kg'] if specifications else None, agility=None, accel=None,
                speed=None, weight=None, liveries=[], paint=None, sound=None,
                claimLimits=[('Retail name and base specifications use an exact native SPEC code join; equipment-modified performance is not inferred.'
                              if verified else 'Archive asset identifier; retail identity and racing specifications remain unassigned.'),
                             'Independent editable copy; native source files remain separate.', *limits])


METADATA_FIELDS = ('name', 'kg', 'bhp', 'nativeMetadata', 'specifications', 'colourVariants')


def refresh_catalog_metadata(current, incoming, origin, source_code):
    """Update generated defaults while retaining owner edits and source history."""
    if incoming['nativeMetadata'] is None:
        return False
    defaults = imported_entry({'code': source_code})
    previous = origin.get('latestMetadata', defaults)
    if not isinstance(previous, dict):
        raise ValueError('Editable GT source metadata history is invalid')
    before = copy.deepcopy(current)
    previous_source = copy.deepcopy(origin.get('latestMetadata'))
    for key in METADATA_FIELDS:
        if key not in current or current[key] == previous.get(key, defaults.get(key)):
            current[key] = copy.deepcopy(incoming[key])
    # This records source metadata even when a custom catalog value takes precedence.
    origin['latestMetadata'] = {key: copy.deepcopy(incoming[key]) for key in METADATA_FIELDS}
    limits = current.get('claimLimits', [])
    if not isinstance(limits, list) or any(not isinstance(value, str) for value in limits):
        raise ValueError('Editable GT claim limit metadata is invalid')
    source_prefixes = {defaults['claimLimits'][0],
                       'Archive asset identifier; retail car identity and performance not decoded.'}
    current['claimLimits'] = list(dict.fromkeys(
        [incoming['claimLimits'][0], *[value for value in limits if value not in source_prefixes]]))
    return current != before or origin['latestMetadata'] != previous_source


def legacy_migrations(rows, catalog, origins, destination, upgrade_unedited, consolidate):
    """Preflight retirement and carry custom metadata/history into the canonical car."""
    existing = {entry['code']: entry for entry in catalog}
    provenance = {entry['code']: entry for entry in origins['cars']}
    migrations, retired, history = {}, {}, []

    def retire(old, allow_edit=False):
        code = old['code']
        target = destination/'models'/f'{code}.glb'
        if target.is_symlink() or target.resolve().parent != (destination/'models').resolve():
            raise ValueError('Editable GT model path is invalid')
        data = target.read_bytes()
        origin = provenance.get(code)
        previous = origin.get('latestSource', origin.get('initialSource', {})) if origin else {}
        if previous.get('game') != 'gran-turismo' or previous.get('code') != old.get('sourceCode'):
            raise ValueError('Editable GT source provenance conflicts')
        edited = sha(data) != previous.get('sha256')
        if edited and not allow_edit:
            raise ValueError(f'{code}: edited duplicate cannot be retired')
        bake_car(code, data, source_mode=False)
        retired[code] = (target, data)
        return {'catalog': old, 'origin': origin}, data, previous, edited

    for row in rows:
        entry = imported_entry(row)
        if entry['sourceVariant'] != 'canonical':
            continue
        old_codes = entry['sourceAliases']
        olds = [existing[code] for code in old_codes if code in existing]
        if not olds:
            continue
        if not consolidate:
            raise ValueError('GT legacy variants require --consolidate')
        if entry['code'] in existing:
            raise ValueError('GT canonical and legacy entries coexist')
        day_code = imported_entry({'code': row['canonical_source_id']})['code']
        preferred = existing.get(day_code)
        records = []
        chosen = None
        for old in olds:
            if old.get('game') != 'gran-turismo' or old.get('sourceCode') not in row['aliases']:
                raise ValueError('GT legacy alias conflicts with existing entry')
            record, data, previous, edited = retire(old, old is preferred)
            records.append(record)
            if old is preferred:
                chosen = data, previous, edited
        origin = {'code': entry['code'], 'retiredVariants': records}
        if preferred:
            default = imported_entry({'code': preferred['sourceCode']})
            custom = {key: value for key, value in preferred.items() if value != default.get(key)}
            # Identity/filter fields belong to this migration, even if older metadata differs.
            for key in ('code', 'game', 'sourceCode', 'sourceCollection', 'sourceVariant', 'sourceAliases', 'claimLimits'):
                custom.pop(key, None)
            entry.update(custom)
            old_identity_limits = {default['claimLimits'][0],
                                   'Archive asset identifier; retail car identity and performance not decoded.'}
            retained_limits = [value for value in preferred.get('claimLimits', [])
                               if value not in old_identity_limits]
            entry['claimLimits'] = list(dict.fromkeys([*entry['claimLimits'], *retained_limits]))
            origin.update({key: copy.deepcopy(value) for key, value in provenance[day_code].items() if key != 'code'})
            origin['retiredVariants'] = records
            data, previous, edited = chosen
            use_source = upgrade_unedited and not edited
            origin['latestSource'] = {'game':'gran-turismo', 'code':row['code'],
                                      'glb':'public/gran-turismo/'+row['file'],
                                      'sha256':row['sha256'] if use_source else previous['sha256']}
            if use_source:
                origin.setdefault('sourceUpgrades', []).append({'fromSha256':previous['sha256'], 'toSha256':row['sha256']})
            migrations[entry['code']] = entry, origin, None if use_source else data
        else:
            origin['initialSource'] = {'game':'gran-turismo', 'code':row['code'],
                                       'glb':'public/gran-turismo/'+row['file'], 'sha256':row['sha256']}
            migrations[entry['code']] = entry, origin, None
    if consolidate:
        for old in catalog:
            if (old.get('game') == 'gran-turismo' and old.get('sourceCode') in
                    {f'simulation/{code}/{edition}' for code in ('_0logn', '_lcupn') for edition in ('day', 'night')}):
                record, _, _, _ = retire(old)
                history.append(record)
    return migrations, retired, history


def import_cars(source=ROOT / 'dealership/public/gran-turismo',
                destination=ROOT / 'dealership/dealership', upgrade_unedited=False, consolidate=False):
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
    migrations, retired, excluded = legacy_migrations(index['cars'], catalog, origins, destination,
                                                     upgrade_unedited, consolidate)
    if retired:
        catalog = [entry for entry in catalog if entry['code'] not in retired]
        origins['cars'] = [entry for entry in origins['cars'] if entry['code'] not in retired]
        origins.setdefault('excludedGTAssets', []).extend(excluded)
        existing = {entry['code']: entry for entry in catalog}
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
        if row.get('native_metadata') is not None:
            doc, _ = read_glb(data)
            if doc.get('extras', {}).get('nativeMetadata') != row['native_metadata']:
                raise ValueError('GT catalog metadata differs from embedded native metadata')
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
            if previous.get('game') != 'gran-turismo' or previous.get('code') != row['code']:
                raise ValueError('Editable GT source provenance conflicts')
            metadata_changed = refresh_catalog_metadata(old, entry, origin, row['code'])
            # Only an exact copy of its recorded source may be upgraded. User edits
            # (including metadata edits) remain owned by the working dealership.
            if sha(working) != previous.get('sha256') or sha(working) == row['sha256']:
                upgraded += int(metadata_changed)
                continue
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
            known_limits = {*entry['claimLimits'][:2], *imported_entry({'code': row['code']})['claimLimits'][:2],
                            'Archive asset identifier; retail car identity and performance not decoded.'}
            custom_limits = [value for value in old_limits
                             if value not in source_limits and value not in known_limits]
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
        source_metadata_defaults = {key: copy.deepcopy(entry[key]) for key in METADATA_FIELDS}
        migration = migrations.get(code)
        if migration:
            entry, origin, working = migration
            if working is not None:
                data = working
                bake_car(code, data, source_mode=False)
        else:
            origin = {'code': code, 'initialSource': {
                'game': 'gran-turismo', 'code': row['code'],
                'glb': 'public/gran-turismo/' + row['file'], 'sha256': row['sha256']}}
        if row.get('native_metadata') is not None:
            origin['latestMetadata'] = source_metadata_defaults
        added.append(entry)
        payloads.append((target, data, None))
        origins['cars'].append(origin)
    if not added and not upgraded and not retired:
        return 0
    original_catalog, original_origins = catalog_path.read_bytes(), origins_path.read_bytes()
    # Stage every copy and metadata before touching the working dealership.
    with tempfile.TemporaryDirectory(prefix='.gt-import-', dir=destination.parent) as temp:
        stage = Path(temp)
        for target, data, _ in payloads:
            (stage / target.name).write_bytes(data)
        (stage / 'catalog.json').write_text(json.dumps(catalog + added, indent=1) + '\n')
        (stage / 'origins.json').write_text(json.dumps(origins, indent=1) + '\n')
        moved, quarantined = [], []
        try:
            for target, _ in retired.values():
                saved = stage/('retired-'+target.name)
                target.replace(saved)
                quarantined.append((target, saved))
            for target, data, previous_data in payloads:
                (stage / target.name).replace(target)
                moved.append((target, previous_data))
                if target.read_bytes() != data:
                    raise ValueError('GT editable installation byte comparison differs')
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
            for target, saved in quarantined:
                saved.replace(target)
            raise
    return len(added) + upgraded


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'dealership/public/gran-turismo')
    parser.add_argument('--destination', type=Path, default=ROOT / 'dealership/dealership')
    parser.add_argument('--upgrade-unedited', action='store_true',
                        help='Refresh only models equal to their recorded source; preserve edited models')
    parser.add_argument('--consolidate', action='store_true', help='Migrate legacy variants to canonical entries; retire only unedited duplicates')
    args = parser.parse_args()
    try:
        count = import_cars(args.source, args.destination, args.upgrade_unedited, args.consolidate)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Imported {count} independent editable GT models; existing dealership entries preserved')
