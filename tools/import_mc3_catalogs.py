#!/usr/bin/env python3
"""Publish verified native MC3 packages and add independent dealership copies.

These entries have no decoded geometry. No GLB or preview is synthesized.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from bake_models import ROOT
from extract_mc3_cars import check_extraction
from mc3_archive import DaveArchive, byte_reader

GAME = 'midnight-club-3-remix'
PROFILE = 'mc3-ps2-native-package-v1'
LIMITS = ['Native PS2 vehicle package; 3D preview and geometry/texture conversion are unavailable.',
          'Source package identifier; retail vehicle name and playable roster are unverified.',
          'Package includes its nested members; shared resources and runtime dependency closure are not included in this download.']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return json.dumps(value, indent=1) + '\n'


def regular(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('MC3 paths must not contain symlinks')
    if path.exists() and path.is_file() and path.stat().st_nlink != 1:
        raise ValueError('MC3 package must be an independent file')


def package_data(path, size, digest, members):
    regular(path)
    if (not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= 256 * 1024 * 1024
            or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)
            or not isinstance(members, int) or isinstance(members, bool) or not 0 < members <= 100000):
        raise ValueError('Invalid MC3 package metadata')
    if path.stat().st_size != size:
        raise ValueError('MC3 package hash/size differs')
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError('MC3 package hash/size differs')
    archive = DaveArchive(byte_reader(data), len(data))
    if sum(not r['directory'] for r in archive.records) != members:
        raise ValueError('MC3 package member count differs')
    for record in archive.records:
        if not record['directory']:
            archive.payload(record)  # Validate stored/decoded lengths and DEFLATE, not geometry.
    return data


def source_package(row, source):
    code = row.get('code') if isinstance(row, dict) else None
    if (not isinstance(code, str) or not re.fullmatch(r'vp_[a-z0-9_]+', code)
            or row.get('file') != f'native/{code}.dat' or row.get('asset_kind') != 'native-package'
            or row.get('source_profile') != PROFILE or row.get('source_variant') != 'native'
            or row.get('records') != [] or row.get('display_name') != code
            or row.get('claim_limits') != LIMITS):
        raise ValueError('Invalid MC3 source package identity/profile')
    return package_data(Path(source) / row['file'], row['bytes'], row['sha256'], row['native_members'])


def export_packages(iso, extraction, output):
    extraction, output, iso = Path(extraction), Path(output), Path(iso)
    regular(output)
    if (output.resolve().is_relative_to(extraction.resolve())
            or extraction.resolve().is_relative_to(output.resolve())
            or iso.resolve().is_relative_to(output.resolve())):
        raise ValueError('MC3 export must be separate from original source files')
    index, _ = check_extraction(iso, extraction)
    rows, payloads = [], []
    for vehicle in index['vehicles']:
        code = vehicle['id']
        manifest = json.loads((extraction / vehicle['manifest']).read_text())
        carrier = manifest['carrier']
        data = package_data(extraction / carrier['file'], carrier['bytes'], carrier['sha256'], vehicle['native_members'])
        row = dict(code=code, file=f'native/{code}.dat', bytes=len(data), sha256=sha(data), records=[],
                   display_name=code, source_profile=PROFILE, source_variant='native',
                   asset_kind='native-package', native_members=vehicle['native_members'], claim_limits=LIMITS)
        rows.append(row); payloads.append((row['file'], data))
    contents = text({'cars': rows, 'source': index['source'], 'claim_limits': LIMITS})
    if output.exists():
        if not output.is_dir() or (output / 'index.json').read_text() != contents:
            raise ValueError('Existing MC3 source export differs; nothing overwritten')
        expected = {name for name, _ in payloads} | {'index.json'}
        for path in output.rglob('*'):
            regular(path)
        if {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} != expected:
            raise ValueError('MC3 source export file coverage differs')
        for row in rows:
            source_package(row, output)
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mc3-export-', dir=output.parent) as temp:
        stage = Path(temp) / 'source'; stage.mkdir()
        for name, data in payloads:
            path = stage / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        (stage / 'index.json').write_text(contents)
        stage.rename(output)
    return len(rows)


def native_model(entry, dealership):
    code, package = entry['code'], entry.get('nativePackage', {})
    if (not isinstance(code, str) or not isinstance(package, dict)
            or entry.get('game') != GAME or entry.get('displayMode') != 'native-package'
            or package.get('file') != f'assets/{code}.dat' or package.get('profile') != PROFILE
            or code != 'MC3_' + str(entry.get('sourceCode', '')).upper()
            or not re.fullmatch(r'vp_[a-z0-9_]+', str(entry.get('sourceCode', '')))):
        raise ValueError('Invalid native dealership package identity/profile')
    data = package_data(Path(dealership) / package['file'], package['bytes'], package['sha256'], package['members'])
    return {'schema': 3, 'previewStatus': 'unavailable', 'source': {
        'package': 'dealership/' + package['file'], 'sha256': sha(data), 'bytes': len(data),
        'nativeMembers': package['members'], 'preset': 'dealership', 'profile': PROFILE}, 'claimLimits': LIMITS}


def import_packages(source=ROOT / 'dealership/public' / GAME, destination=ROOT / 'dealership/dealership'):
    source, destination = Path(source), Path(destination)
    if (source.resolve().is_relative_to(destination.resolve())
            or destination.resolve().is_relative_to(source.resolve())):
        raise ValueError('MC3 source and dealership must be separate')
    catalog_path, origins_path = destination / 'catalog.json', destination / 'origins.json'
    for path in (source, destination, catalog_path, origins_path, destination / 'assets'):
        regular(path)
    catalog = json.loads(catalog_path.read_text()); origins = json.loads(origins_path.read_text())
    if (not isinstance(catalog, list) or not catalog or origins.get('schema') != 1
            or not isinstance(origins.get('cars'), list)):
        raise ValueError('Existing dealership catalog/origins are invalid')
    existing = {row['code']: row for row in catalog}
    origin_codes = {r['code'] for r in origins['cars']}
    if len(existing) != len(catalog) or len(origin_codes) != len(origins['cars']):
        raise ValueError('Existing dealership identities are duplicated')
    rows = json.loads((source / 'index.json').read_text())['cars']
    if not isinstance(rows, list) or not rows:
        raise ValueError('MC3 source index has no packages')
    added, payloads, seen = [], [], set()
    for row in rows:
        data = source_package(row, source); code = 'MC3_' + row['code'].upper()
        if code in seen:
            raise ValueError('MC3 source identities are duplicated')
        seen.add(code)
        if code in existing:
            old = existing[code]
            if old.get('sourceCode') != row['code']:
                raise ValueError('MC3 identity conflicts with dealership entry')
            # A later preview conversion keeps the same retained native package.
            native_model({**old, 'displayMode': 'native-package'}, destination)
            continue
        if code in origin_codes:
            raise ValueError('MC3 identity conflicts with existing origin record')
        target = destination / 'assets' / f'{code}.dat'
        regular(target)
        if target.exists():
            raise ValueError('Uncatalogued MC3 dealership package already exists')
        added.append(dict(code=code, name=row['code'], game=GAME, gameLabel='Midnight Club 3 Remix',
                          sourceCode=row['code'], sourceCollection='native', sourceVariant='native',
                          displayMode='native-package', bodyStyle='unknown', group='NATIVE',
                          year=None, topSpeed=None, bhp=None, kg=None, agility=None, accel=None,
                          speed=None, weight=None, liveries=[], paint=None, sound=None,
                          claimLimits=LIMITS, nativePackage={'file': f'assets/{code}.dat',
                          'profile': PROFILE, 'bytes': len(data), 'sha256': sha(data), 'members': row['native_members']}))
        payloads.append((target, data))
        origins['cars'].append({'code': code, 'initialSource': {'game': GAME, 'code': row['code'],
            'package': f'public/{GAME}/' + row['file'], 'sha256': row['sha256']}})
    if not added:
        return 0
    before_catalog, before_origins = catalog_path.read_bytes(), origins_path.read_bytes()
    with tempfile.TemporaryDirectory(prefix='.mc3-import-', dir=destination.parent) as temp:
        stage = Path(temp)
        for target, data in payloads:
            (stage / target.name).write_bytes(data)
        (stage / 'catalog.json').write_text(text(catalog + added))
        (stage / 'origins.json').write_text(text(origins))
        (destination / 'assets').mkdir(exist_ok=True)
        moved = []
        try:
            for target, _ in payloads:
                (stage / target.name).replace(target); moved.append(target)
            (stage / 'origins.json').replace(origins_path)
            (stage / 'catalog.json').replace(catalog_path)
        except BaseException:
            catalog_path.write_bytes(before_catalog); origins_path.write_bytes(before_origins)
            for target in moved:
                target.unlink()
            raise
    return len(added)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, default=ROOT / GAME / 'game-files/Midnight Club 3 - DUB Edition Remix.iso')
    parser.add_argument('--extraction', type=Path, default=ROOT / GAME / 'cars')
    parser.add_argument('--source', type=Path, default=ROOT / 'dealership/public' / GAME)
    parser.add_argument('--destination', type=Path, default=ROOT / 'dealership/dealership')
    args = parser.parse_args()
    try:
        exported = export_packages(args.iso, args.extraction, args.source)
        imported = import_packages(args.source, args.destination)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Published {exported} source packages; added {imported} independent dealership packages. 3D previews unavailable.')
