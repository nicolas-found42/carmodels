#!/usr/bin/env python3
"""Publish checked MCLA static assemblies and separately downloadable native car ZIPs."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import tempfile
import zipfile

from bake_models import ROOT, bake_car, read_glb
from extract_mcla_cars import CODE, DEFAULT_ISO, check_extraction
from import_gt4_catalog import same_glb
from mcla_preview import PROFILE, build_car

GAME = 'midnight-club-los-angeles'
NATIVE_PROFILE = 'mcla-xbox360-native-car-v1'
VARIANT = 'stock'
LIMITS = [
    'Static LOD 0 stock-index assembly with half-resolution diffuse textures and neutral paint; '
    'slot attachment, wheel placement and material interpretation are readings, not runtime observations. Shared wheel radius and width use geometric approximations because runtime tire-size configuration is undecoded.',
    'Runtime customization, animation, damage, paint, reflections and original shader passes are not reproduced.',
    'Names use exact English UI-string key joins when available; other entries retain source codes. '
    'Retail year, manufacturer and performance are not inferred from codes.',
    'Native ZIPs hold this car manifest and its extracted files, excluding separately shared rims, tires and brakes.',
    'Ambient and player namespace entries remain distinct; this is not a verified playable roster.',
]
MAX_FILE = 128 * 1024 * 1024
STAMP = (1980, 1, 1, 0, 0, 0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return json.dumps(value, indent=1) + '\n'


def regular(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('MCLA paths must not contain symlinks')
    if path.is_file() and path.stat().st_nlink != 1:
        raise ValueError('MCLA files must be independent')


def checked_file(path, size, digest):
    regular(path)
    if (type(size) is not int or not 0 < size <= MAX_FILE
            or not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest)):
        raise ValueError('Invalid MCLA file metadata')
    if Path(path).stat().st_size != size:
        raise ValueError('MCLA file hash/size differs')
    data = Path(path).read_bytes()
    if sha(data) != digest:
        raise ValueError('MCLA file hash/size differs')
    return data


def member_path(code, row):
    file = row.get('file')
    path = Path(file) if isinstance(file, str) else Path('/')
    if (path.is_absolute() or '..' in path.parts or '\\' in file or
            not file.startswith(code + '/') or len(path.parts) < 3):
        raise ValueError('Unsafe MCLA native member path')
    name = path.relative_to(code).as_posix()
    if name != row.get('source', {}).get('archive_path'):
        raise ValueError('MCLA member path differs from source')
    return name


def checked_manifest(extraction, vehicle):
    code = vehicle['id']
    if not CODE.fullmatch(code) or vehicle['manifest'] != code + '/manifest.json':
        raise ValueError('Invalid MCLA extraction identity')
    path = Path(extraction) / vehicle['manifest']
    regular(path)
    raw = path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get('id') != code or not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise ValueError('Invalid MCLA car manifest')
    names = [member_path(code, row) for row in manifest['files']]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate MCLA native members')
    return raw, manifest


def package_members(code, data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if any(i.is_dir() or stat.S_IFMT(i.external_attr >> 16) not in (0, stat.S_IFREG) for i in infos):
            raise ValueError('MCLA ZIP members must be regular files')
        if (len(names) != len(set(names)) or 'manifest.json' not in names
                or sum(i.file_size for i in infos) > MAX_FILE * 4):
            raise ValueError('Invalid MCLA native package coverage/size')
        members = {i.filename: archive.read(i) for i in infos}
    manifest = json.loads(members['manifest.json'])
    if manifest.get('id') != code:
        raise ValueError('MCLA package manifest identity differs')
    rows = manifest.get('files', [])
    expected = [member_path(code, row) for row in rows]
    if not expected or len(set(expected)) != len(expected) or set(expected) != set(members) - {'manifest.json'}:
        raise ValueError('MCLA package manifest member coverage differs')
    for row, name in zip(rows, expected):
        if len(members[name]) != row['bytes'] or sha(members[name]) != row['sha256']:
            raise ValueError('MCLA package member hash differs')
    return members


def build_package(extraction, vehicle):
    raw, manifest = checked_manifest(extraction, vehicle)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for row in sorted(manifest['files'], key=lambda r: r['file']):
            data = checked_file(Path(extraction) / row['file'], row['bytes'], row['sha256'])
            info = zipfile.ZipInfo(member_path(vehicle['id'], row), STAMP)
            info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            archive.writestr(info, data, compresslevel=9)
        info = zipfile.ZipInfo('manifest.json', STAMP)
        info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
        archive.writestr(info, raw, compresslevel=9)
    return buffer.getvalue(), len(manifest['files'])


def validate_identity(row):
    code, name, source = row['code'], row['display_name'], row.get('name_source')
    if not isinstance(source, dict):
        raise ValueError('MCLA display-name source missing')
    receipt_path = ROOT / 'research/evidence/midnight-club-los-angeles/display-names.json'
    identities = {r['id']: r for r in json.loads(receipt_path.read_text())['vehicles']}
    if code in identities:
        expected = identities[code]
        if name != expected['name'] or source != expected['name_source']:
            raise ValueError('MCLA display-name source differs from pinned receipt')
    elif source != {'kind': 'code-fallback', 'code': code} or name != code:
        raise ValueError('MCLA unknown display identity must retain its source code')


def source_package(row, source):
    code = row.get('code') if isinstance(row, dict) else None
    package = row.get('native_package') if isinstance(row, dict) else None
    if (not isinstance(code, str) or not CODE.fullmatch(code)
            or row.get('file') != f'previews/{code}.glb' or row.get('source_code') != code
            or row.get('asset_kind', 'glb') != 'glb' or row.get('source_profile') != PROFILE
            or row.get('source_variant') != VARIANT or row.get('claim_limits') != LIMITS
            or not isinstance(row.get('display_name'), str) or not row['display_name'].strip()
            or not isinstance(row.get('records'), list) or len(row['records']) != 1
            or not isinstance(package, dict) or package.get('profile') != NATIVE_PROFILE
            or package.get('file') != f'native/{code}.zip' or type(package.get('members')) is not int
            or not 0 < package['members'] <= 10000):
        raise ValueError('Invalid MCLA source identity/profile')
    validate_identity(row)
    if (type(package.get('bytes')) is not int or not 0 < package['bytes'] <= MAX_FILE
            or not isinstance(package.get('sha256'), str) or not re.fullmatch('[a-f0-9]{64}', package['sha256'])):
        raise ValueError('Invalid MCLA native metadata')
    data = checked_file(Path(source) / row['file'], row.get('bytes'), row.get('sha256'))
    doc, _ = read_glb(data)
    extras = doc.get('extras', {})
    if extras.get('car') != code or extras.get('source_profile') != PROFILE:
        raise ValueError('MCLA preview GLB identity differs')
    record = row['records'][0]
    if record.get('role') != 'stock' or type(record.get('triangles')) is not int or record['triangles'] <= 0:
        raise ValueError('Invalid MCLA preview triangle declaration')
    if bake_car('MCLA_' + code.upper(), data, source_mode=False)['triangleCount'] != record['triangles']:
        raise ValueError('MCLA preview triangle declaration differs')
    native = Path(source) / package['file']
    regular(native)
    if native.exists():
        members = package_members(code, checked_file(native, package.get('bytes'), package.get('sha256')))
        if len(members) - 1 != package['members']:
            raise ValueError('MCLA native member count differs')
    return data


def _derive_one(args):
    extraction, vehicle = args
    package, members = build_package(extraction, vehicle)
    data, record = build_car(Path(extraction), vehicle['id'])
    return vehicle['id'], (data, record, package, members)


def derive_outputs(extraction, index, workers=1):
    args = [(str(extraction), vehicle) for vehicle in index['vehicles']]
    if workers == 1:
        return dict(map(_derive_one, args))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(_derive_one, args))


def catalog_rows(index, outputs, identities):
    rows = []
    for vehicle in index['vehicles']:
        code = vehicle['id']
        data, record, package, members = outputs[code]
        identity = identities[code]
        rows.append(dict(code=code, file=f'previews/{code}.glb', bytes=len(data), sha256=sha(data),
                         records=[{'role': 'stock', 'triangles': record['triangles']}],
                         display_name=identity['name'], name_source=identity['name_source'],
                         source_profile=PROFILE, source_code=code, source_variant=VARIANT,
                         native_package={'file': f'native/{code}.zip', 'profile': NATIVE_PROFILE,
                                         'bytes': len(package), 'sha256': sha(package), 'members': members},
                         claim_limits=LIMITS))
    return rows


def verify_published(extraction, output, index, outputs, identities, allow_missing_native=False):
    regular(output / 'index.json')
    current = json.loads((output / 'index.json').read_text())
    expected_rows = catalog_rows(index, outputs, identities)
    # Compression versions may differ; JSON/geometry and decoded native member bytes stay authoritative.
    def comparable(rows):
        return [{k: v for k, v in row.items() if k not in ('bytes', 'sha256', 'native_package')} |
                {'native_package': {k: v for k, v in row['native_package'].items() if k not in ('bytes', 'sha256')}}
                for row in rows]
    if (comparable(current['cars']) != comparable(expected_rows) or current.get('source') != index['source']
            or current.get('claim_limits') != LIMITS):
        raise ValueError('MCLA source index differs from derivation')
    expected = {'index.json'} | {row['file'] for row in current['cars']} | {row['native_package']['file'] for row in current['cars']}
    missing = {row['native_package']['file'] for row in current['cars']
               if not (output / row['native_package']['file']).exists()}
    if allow_missing_native:
        expected -= missing
    for path in output.rglob('*'):
        regular(path)
    if {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} != expected:
        raise ValueError('MCLA source export file coverage differs')
    for row in current['cars']:
        if not same_glb(source_package(row, output), outputs[row['code']][0]):
            raise ValueError('MCLA preview differs from derivation')
        native = output / row['native_package']['file']
        if native.exists():
            members = package_members(row['code'], native.read_bytes())
            if members != package_members(row['code'], outputs[row['code']][2]):
                raise ValueError('MCLA native package differs from extraction')
        elif (not allow_missing_native or sha(outputs[row['code']][2]) != row['native_package']['sha256']
              or len(outputs[row['code']][2]) != row['native_package']['bytes']):
            raise ValueError('Rebuilt MCLA ZIP differs from its pin; nothing overwritten')
    return len(current['cars'])


def export_catalog(extraction, output, identities, workers=1):
    extraction, output = Path(extraction), Path(output)
    regular(extraction); regular(output)
    if output.resolve().is_relative_to(extraction.resolve()) or extraction.resolve().is_relative_to(output.resolve()):
        raise ValueError('MCLA source export must be separate from extraction')
    regular(extraction / 'index.json')
    index = json.loads((extraction / 'index.json').read_text())
    vehicles = index.get('vehicles')
    if not isinstance(vehicles, list) or not vehicles or len({v['id'] for v in vehicles}) != len(vehicles):
        raise ValueError('Invalid or duplicate MCLA extracted vehicles')
    if set(identities) != {vehicle['id'] for vehicle in index['vehicles']}:
        raise ValueError('MCLA display identity coverage differs')
    outputs = derive_outputs(extraction, index, workers)
    if output.exists():
        verify_published(extraction, output, index, outputs, identities, allow_missing_native=True)
        rows = json.loads((output / 'index.json').read_text())['cars']
        missing = [(output / row['native_package']['file'], outputs[row['code']][2]) for row in rows
                   if not (output / row['native_package']['file']).exists()]
        with tempfile.TemporaryDirectory(prefix='.mcla-restore-', dir=output.parent) as temp:
            stage = Path(temp)
            for target, payload in missing:
                (stage / target.name).write_bytes(payload)
            moved = []
            try:
                for target, _ in missing:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    (stage / target.name).replace(target); moved.append(target)
                verify_published(extraction, output, index, outputs, identities)
            except BaseException:
                for target in moved: target.unlink()
                raise
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = catalog_rows(index, outputs, identities)
    with tempfile.TemporaryDirectory(prefix='.mcla-export-', dir=output.parent) as temp:
        stage = Path(temp) / 'source'; stage.mkdir()
        for row in rows:
            data, _, package, _ = outputs[row['code']]
            for name, payload in ((row['file'], data), (row['native_package']['file'], package)):
                path = stage / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
        (stage / 'index.json').write_text(text({'cars': rows, 'source': index['source'], 'claim_limits': LIMITS}))
        for row in rows:
            source_package(row, stage)
        stage.rename(output)
    return len(rows)


def main():
    from mcla_names import load_from_disc, identities_for
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, default=DEFAULT_ISO)
    parser.add_argument('--extraction', type=Path, default=ROOT / GAME / 'cars')
    parser.add_argument('--output', type=Path, default=ROOT / 'dealership/public' / GAME)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--available', action='store_true')
    args = parser.parse_args()
    if args.available:
        index = json.loads((args.extraction / 'index.json').read_text())
        present = sum((args.extraction / v['manifest']).is_file() for v in index['vehicles'])
        return 0 if args.iso.is_file() and present == len(index['vehicles']) else 1 if not present else 2
    if not 1 <= args.workers <= 16:
        parser.error('workers must be 1 to 16')
    index = json.loads((args.extraction / 'index.json').read_text())
    table = load_from_disc(args.iso)
    identities = identities_for([v['id'] for v in index['vehicles']], table)
    if args.check:
        count = verify_published(args.extraction, args.output, index,
                                 derive_outputs(args.extraction, index, args.workers), identities)
    else:
        check_extraction(args.iso, args.extraction)
        count = export_catalog(args.extraction, args.output, identities, args.workers)
    print(f'{"CHECKED" if args.check else "EXPORTED"} {count} MCLA previews and native packages')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        raise SystemExit(str(error)) from None
