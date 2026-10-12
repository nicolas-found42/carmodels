#!/usr/bin/env python3
"""Publish Gran Turismo 4 cars to the source catalog: a static GLB preview per car plus its
native files.

Each row's `file` is a textured GLB built from the car's CAR4 showroom model; `native_package`
is a ZIP of that car's extracted native files at their GT4.VOL paths plus its manifest.
Display names come from the decoded spec database.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

from bake_models import ROOT, read_glb
from extract_gt4_cars import CODE, check_extraction
from gt4_glb import PROFILE as PREVIEW_PROFILE, build_car
from gt4_specdb import car_specs
from model_png import decode_png

GAME = 'gran-turismo-4'
PROFILE = 'gt4-ps2-native-car-v1'
VARIANT = 'showroom'
SPECDB = 'provenance/specdb/GT4_EU2560'
LIMITS = ['Static showroom-model preview decoded from native CAR4/MDLS/Tex1 data; game lighting, reflections, animation and runtime VM state are not reproduced.',
          'Retail names, wheelbase, tread and tire sizes come from the decoded GT4 spec database (EU, british locale); wheel placement is a reading of those values.',
          'The native ZIP holds the files matched to this model code; shared wheels, tires, wings and spec-database rows are not included in it.']
MAX_PACKAGE = 64 * 1024 * 1024
STAMP = (1980, 1, 1, 0, 0, 0)  # Fixed member time: the manifest keeps each volume timestamp.


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return json.dumps(value, indent=1) + '\n'


def regular(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('GT4 paths must not contain symlinks')
    if path.exists() and path.is_file() and path.stat().st_nlink != 1:
        raise ValueError('GT4 package must be an independent file')


def display_name(name):
    # GT4 strings use a backtick where the model year takes an apostrophe ("Camaro `69").
    return name.replace('`', "'")


def member_names(code, names):
    """Only this code's native paths and its manifest may appear, each once."""
    allowed = re.compile(rf'(car/(lod|open)/{code}(\.pat)?|car/menu/{code}|wheel/(lod|menu|open)/{code}|manifest\.json)')
    if len(set(names)) != len(names) or not all(allowed.fullmatch(n) for n in names):
        raise ValueError('GT4 package member names differ')
    if not {'manifest.json', f'car/lod/{code}', f'car/lod/{code}.pat', f'car/menu/{code}'} <= set(names):
        raise ValueError('GT4 package lacks its race model, colour patch, menu model or manifest')


def package_members(code, data):
    """Decoded members; every CRC is checked and the manifest pins each native file."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        member_names(code, [i.filename for i in infos])
        if sum(i.file_size for i in infos) > MAX_PACKAGE * 4:
            raise ValueError('GT4 package exceeds decoded limit')
        members = {i.filename: archive.read(i) for i in infos}
    manifest = json.loads(members['manifest.json'])
    pinned = {row['source']['volume_path']: row for row in manifest.get('files', [])}
    if manifest.get('id') != code or set(pinned) != set(members) - {'manifest.json'}:
        raise ValueError('GT4 package manifest differs from members')
    for name, row in pinned.items():
        if row['file'] != f'{code}/{name}' or row['bytes'] != len(members[name]) or row['sha256'] != sha(members[name]):
            raise ValueError('GT4 package member hash differs: ' + name)
    return members


def checked_file(path, size, digest, limit=MAX_PACKAGE):
    regular(path)
    if (not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= limit
            or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
        raise ValueError('Invalid GT4 file metadata')
    if Path(path).stat().st_size != size:
        raise ValueError('GT4 file hash/size differs')
    data = Path(path).read_bytes()
    if sha(data) != digest:
        raise ValueError('GT4 file hash/size differs')
    return data


def source_package(row, source):
    """Validate one source-catalog row: identity, preview GLB identity and its native package."""
    code = row.get('code') if isinstance(row, dict) else None
    package = row.get('native_package') if isinstance(row, dict) else None
    if (not isinstance(code, str) or not CODE.fullmatch(code)
            or row.get('file') != f'previews/{code}.glb' or row.get('asset_kind', 'glb') != 'glb'
            or row.get('source_profile') != PREVIEW_PROFILE or row.get('source_variant') != VARIANT
            or row.get('source_code') != code or not isinstance(row.get('records'), list) or len(row['records']) != 1
            or not isinstance(row.get('display_name'), str) or not row['display_name'].strip()
            or row.get('claim_limits') != LIMITS or not isinstance(package, dict)
            or package.get('file') != f'native/{code}.zip' or package.get('profile') != PROFILE
            or not isinstance(package.get('members'), int) or not 0 < package['members'] <= 16):
        raise ValueError('Invalid GT4 source package identity/profile')
    glb = checked_file(Path(source) / row['file'], row['bytes'], row['sha256'])
    doc, _ = read_glb(glb)
    extras = doc.get('extras', {})
    if extras.get('source_profile') != PREVIEW_PROFILE or extras.get('car') != code:
        raise ValueError('GT4 preview GLB identity differs from its row')
    data = checked_file(Path(source) / package['file'], package['bytes'], package['sha256'])
    if len(package_members(code, data)) - 1 != package['members']:
        raise ValueError('GT4 package member count differs')
    return glb


def build_package(extraction, vehicle):
    """Deterministic for a given zlib build; equality is judged on decoded members."""
    extraction = Path(extraction)
    manifest_bytes = (extraction / vehicle['manifest']).read_bytes()
    manifest = json.loads(manifest_bytes)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for row in sorted(manifest['files'], key=lambda r: r['source']['volume_path']):
            info = zipfile.ZipInfo(row['source']['volume_path'], STAMP)
            info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            archive.writestr(info, (extraction / row['file']).read_bytes(), compresslevel=9)
        info = zipfile.ZipInfo('manifest.json', STAMP)
        info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
        archive.writestr(info, manifest_bytes, compresslevel=9)
    return buffer.getvalue(), len(manifest['files'])


def build_preview(extraction, vehicle, spec):
    """The showroom (menu) model, verified against its extraction manifest before decoding."""
    extraction, code = Path(extraction), vehicle['id']
    manifest = json.loads((extraction / vehicle['manifest']).read_text())
    row = next(r for r in manifest['files'] if r['source']['volume_path'] == f'car/menu/{code}')
    data = (extraction / row['file']).read_bytes()
    if len(data) != row['bytes'] or sha(data) != row['sha256']:
        raise ValueError('GT4 extraction differs from its manifest: ' + row['file'])
    source = {'file': row['file'], 'sha256': row['sha256'], 'spec_label': spec['label']}
    return build_car(data, code, spec, source)


def same_glb(a, b):
    """Equal geometry/JSON and equal decoded pixels; PNG compression bytes may differ."""
    doc_a, bin_a = read_glb(a)
    doc_b, bin_b = read_glb(b)
    strip = lambda d: {k: v for k, v in d.items() if k not in ('bufferViews', 'buffers')}  # noqa: E731
    if strip(doc_a) != strip(doc_b) or len(doc_a['bufferViews']) != len(doc_b['bufferViews']):
        return False
    images = {image['bufferView'] for image in doc_a.get('images', [])}
    for i, (va, vb) in enumerate(zip(doc_a['bufferViews'], doc_b['bufferViews'])):
        part_a = bin_a[va['byteOffset']:va['byteOffset'] + va['byteLength']]
        part_b = bin_b[vb['byteOffset']:vb['byteOffset'] + vb['byteLength']]
        if part_a != part_b and (i not in images or decode_png(part_a) != decode_png(part_b)):
            return False
    return True


def catalog_rows(index, specs, outputs):
    rows = []
    for vehicle in index['vehicles']:
        code = vehicle['id']
        glb, record, package, members = outputs[code]
        spec = specs[code]
        rows.append(dict(code=code, file=f'previews/{code}.glb', bytes=len(glb), sha256=sha(glb),
                         records=[{'role': 'showroom', 'triangles': record['triangles'], 'textures': record['textures']}],
                         display_name=display_name(spec['name']), source_profile=PREVIEW_PROFILE,
                         source_variant=VARIANT, source_code=code, spec_label=spec['label'],
                         native_package={'file': f'native/{code}.zip', 'profile': PROFILE, 'bytes': len(package),
                                         'sha256': sha(package), 'members': members},
                         claim_limits=LIMITS))
    return rows


def derive_outputs(extraction, index):
    specs = car_specs(Path(extraction) / SPECDB)
    if set(specs) != {v['id'] for v in index['vehicles']}:
        raise ValueError('GT4 spec database and extracted model codes differ')
    outputs = {}
    for vehicle in index['vehicles']:
        glb, record = build_preview(extraction, vehicle, specs[vehicle['id']])
        package, members = build_package(extraction, vehicle)
        outputs[vehicle['id']] = (glb, record, package, members)
    return specs, outputs


def comparable(rows):
    """Row content that does not depend on DEFLATE byte choices."""
    return [{k: v for k, v in r.items() if k not in ('bytes', 'sha256', 'native_package')}
            | {'native_package': {k: v for k, v in r['native_package'].items() if k not in ('bytes', 'sha256')}}
            for r in rows]


def verify_published(extraction, output, index, specs, outputs):
    current = json.loads((output / 'index.json').read_text())
    rows = current['cars']
    if comparable(rows) != comparable(catalog_rows(index, specs, outputs)):
        raise ValueError('GT4 source index differs from extraction')
    if current.get('source') != index['source'] or current.get('claim_limits') != LIMITS:
        raise ValueError('GT4 source index provenance differs')
    for path in output.rglob('*'):
        regular(path)
    expected = {r['file'] for r in rows} | {r['native_package']['file'] for r in rows} | {'index.json'}
    if {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} != expected:
        raise ValueError('GT4 source export file coverage differs')
    for row in rows:
        glb = source_package(row, output)
        derived, _, _, _ = outputs[row['code']]
        if not same_glb(glb, derived):
            raise ValueError('GT4 preview differs from re-derived conversion: ' + row['code'])
        members = package_members(row['code'], (output / row['native_package']['file']).read_bytes())
        for name, data in members.items():
            path = Path(extraction) / row['code'] / name
            regular(path)
            if path.read_bytes() != data:
                raise ValueError('GT4 package differs from extraction: ' + row['code'] + '/' + name)
    return len(rows)


def export_packages(iso, extraction, output):
    extraction, output, iso = Path(extraction), Path(output), Path(iso)
    regular(output)
    if (output.resolve().is_relative_to(extraction.resolve())
            or extraction.resolve().is_relative_to(output.resolve())
            or iso.resolve().is_relative_to(output.resolve())):
        raise ValueError('GT4 export must be separate from original source files')
    index, _ = check_extraction(iso, extraction)
    specs, outputs = derive_outputs(extraction, index)
    if output.exists():
        # Existing outputs stand only when they equal a fresh conversion; nothing is overwritten.
        try:
            verify_published(extraction, output, index, specs, outputs)
        except (ValueError, OSError, KeyError) as error:
            raise ValueError('Existing GT4 source export differs; nothing overwritten (' + str(error) + ')') from error
        return 0
    rows = catalog_rows(index, specs, outputs)
    contents = text({'cars': rows, 'source': index['source'], 'claim_limits': LIMITS})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.gt4-export-', dir=output.parent) as temp:
        stage = Path(temp) / 'source'
        for row in rows:
            glb, _, package, _ = outputs[row['code']]
            for name, data in ((row['file'], glb), (row['native_package']['file'], package)):
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        (stage / 'index.json').write_text(contents)
        for row in rows:
            source_package(row, stage)
        stage.rename(output)
    return len(rows)


def check_export(extraction, output):
    """Offline: re-derive every preview and package from the committed extraction and compare."""
    extraction, output = Path(extraction), Path(output)
    index = json.loads((extraction / 'index.json').read_text())
    specs, outputs = derive_outputs(extraction, index)
    return verify_published(extraction, output, index, specs, outputs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, default=ROOT / GAME / 'game-files/Gran Turismo 4 (axekin.com).iso')
    parser.add_argument('--extraction', type=Path, default=ROOT / GAME / 'cars')
    parser.add_argument('--output', type=Path, default=ROOT / 'dealership/public' / GAME)
    parser.add_argument('--check', action='store_true', help='Offline: compare published files with a fresh conversion.')
    args = parser.parse_args()
    try:
        if args.check:
            print(f'CHECKED {check_export(args.extraction, args.output)} GT4 source previews and packages')
        else:
            print(f'EXPORTED {export_packages(args.iso, args.extraction, args.output)} GT4 source previews and packages')
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print('ERROR:', error)
        raise SystemExit(1)
