#!/usr/bin/env python3
"""Extract all native GT1 car/texture pairs and shared car metadata from a PS1 disc.

Never replaces an existing nonempty destination. --check recomputes the entire
expected tree from the disc, including hashes and manifests, and checks every
output byte. This is extraction, not mesh/texture conversion or render recovery.
"""
import argparse
import json
from pathlib import Path
import re
import tempfile

from gt_archive import Disc, archive_entries, car_pairs, decompress, digest, file_digest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ROOT / 'tools/gt1/usa-car-codes.txt'
NAMES_SHA256 = 'e9da7e42d2e643948fcd0c9ecca9635d635fa2299d20ffd0411ec5701f851c97'
CODE_SHA256 = 'f8796a0e9fcd77ba905c056ad22e8d606c75f06052ab02dbbba7776ad5080472'
LIMITS = [
    'Native GT-CAR and GT-CTEX payloads only; no geometry, palette, PNG or GLB conversion.',
    'All archive variants retained; pair counts are not counts of distinct drivable cars.',
    'Simulation codes/day-night labels come from a pinned external USA retail map, not embedded filenames.',
    'Arcade names remain unknown; byte-identical simulation matches are recorded without discarding variants.',
    'Shared CARINF sections are preserved; per-car specification and equipment relationships are not decoded.',
    'No game execution, rendered fidelity or dealership integration is established.'
]


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def names_for_disc(boot, entries):
    if b'SCUS_941.94;1' not in boot:
        return {}
    data = NAMES.read_bytes()
    if digest(data) != CODE_SHA256:
        raise ValueError('USA name map hash mismatch')
    codes = data.decode('ascii').splitlines()
    if len(codes) != 344 or len(set(codes)) != 344 or not all(re.fullmatch(r'[a-z0-9_-]+', c) for c in codes):
        raise ValueError('Invalid USA car code map')
    if len(entries) != len(codes) * 4:
        raise ValueError('USA name map coverage does not match car directory')
    mapping = {i: (codes[(i % 688) // 2] + ('_night' if i >= 688 else ''), 'car' if i % 2 else 'tex')
               for i in range(len(entries))}
    for i in range(0, len(entries), 2):
        if mapping[i][1] != 'tex' or mapping[i + 1][1] != 'car' or mapping[i][0] != mapping[i + 1][0]:
            raise ValueError('USA name map pair mismatch')
    return mapping


def entry_manifest(entry, path, source):
    return {k: v for k, v in entry.items() if k != 'data'} | {'file': path, 'source_archive': source}


def derive(image):
    """Return an expected relative-path/byte tree; no destination writes."""
    disc = Disc(image)
    try:
        files = {e['path']: e for e in disc.entries if not e['directory']}
        required = ['/CAR.DAT;1', '/CARCADE.DAT;1', '/CARINF.DAT;1', '/SYSTEM.CNF;1']
        if any(path not in files for path in required):
            raise ValueError('Disc lacks required GT1 car archives or boot configuration')
        source_hash = file_digest(image)
        boot = disc.read(files['/SYSTEM.CNF;1'])
        tree = {}
        cars = []
        archive_records = []
        simulation_hashes = {}
        used_paths = set()
        inventory = []
        for iso_entry in disc.entries:
            if iso_entry['directory']:
                continue
            # Only the first sector, bounded ASCII, never arbitrary game content.
            inventory.append({'path': iso_entry['path'].lstrip('/'), 'size': iso_entry['size'],
                              'ascii_header': disc.inventory_header(iso_entry['lba'])})
        for archive_name, mode in [('CAR.DAT', 'simulation'), ('CARCADE.DAT', 'arcade')]:
            iso = files['/' + archive_name + ';1']
            raw = disc.read(iso)
            entries = archive_entries(raw)
            pairs = car_pairs(entries)
            mapping = names_for_disc(boot, entries) if mode == 'simulation' else {}
            archive_records.append(iso | {'sha256': digest(raw), 'entries': len(entries), 'pairs': len(pairs)})
            for pair_index, (texture, model) in enumerate(pairs):
                stem = mapping[texture['index']][0] if mapping else f'pair-{pair_index:04d}'
                variant = 'night' if mapping and stem.endswith('_night') else 'day' if mapping else 'unknown'
                code = stem.removesuffix('_night') if mapping else stem
                folder = f'{mode}/{code}/{variant}' if mapping else f'{mode}/{code}'
                if folder in used_paths:
                    raise ValueError('Car output path collision')
                used_paths.add(folder)
                tex_path, model_path = folder + '/textures.tex', folder + '/model.car'
                tree[tex_path], tree[model_path] = texture['data'], model['data']
                identity = (texture['sha256'], model['sha256'])
                record = {'id': folder, 'mode': mode, 'code': code, 'variant': variant, 'pair_index': pair_index,
                          'name_authority': 'external-usa-retail-map' if mapping else 'archive-ordinal',
                          'assets': [entry_manifest(texture, tex_path, archive_name), entry_manifest(model, model_path, archive_name)],
                          'byte_identical_simulation_pairs': simulation_hashes.get(identity, []) if mode == 'arcade' else [],
                          'claim_limits': LIMITS}
                tree[folder + '/manifest.json'] = json_bytes(record)
                cars.append(record)
                if mode == 'simulation':
                    simulation_hashes.setdefault(identity, []).append(folder)
        metadata_iso = files['/CARINF.DAT;1']
        packed_metadata = disc.read(metadata_iso)
        metadata = decompress(packed_metadata)
        sections = archive_entries(metadata)
        tree['_metadata/CARINF.DAT'] = packed_metadata
        tree['_metadata/CARINF.decoded.arc'] = metadata
        tree['_metadata/SYSTEM.CNF'] = boot
        section_records = []
        for section in sections:
            path = f"_metadata/sections/{section['index']:02d}.bin"
            tree[path] = section['data']
            section_records.append(entry_manifest(section, path, 'CARINF.decoded.arc'))
        tree['_metadata/manifest.json'] = json_bytes(metadata_iso | {'sha256': digest(packed_metadata),
            'decoded_sha256': digest(metadata), 'decoded_bytes': len(metadata), 'sections': section_records,
            'claim_limits': LIMITS})
        index = {'schema': 1, 'game': 'gran-turismo', 'volume': disc.volume,
                 'source': {'file': Path(image).name, 'bytes': disc.size, 'sha256': source_hash,
                            'sector_bytes': disc.stride, 'iso_inventory': disc.entries},
                 'archives': archive_records, 'car_pairs': len(cars),
                 'simulation_pairs': sum(c['mode'] == 'simulation' for c in cars),
                 'arcade_pairs': sum(c['mode'] == 'arcade' for c in cars),
                 'simulation_codes': len({c['code'] for c in cars if c['mode'] == 'simulation'}),
                 'metadata_sections': len(sections), 'name_map_sha256': NAMES_SHA256 if any(c['name_authority'] == 'external-usa-retail-map' for c in cars) else None,
                 'cars': cars, 'claim_limits': LIMITS}
        tree['index.json'] = json_bytes(index)
        if file_digest(image) != source_hash:
            raise ValueError('Source disc changed during extraction')
        return tree, index, inventory
    finally:
        disc.close()


def check_tree(destination, expected):
    destination = Path(destination)
    actual = {}
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('Extraction destination is not a regular directory')
    for path in destination.rglob('*'):
        if path.is_symlink():
            raise ValueError('Extraction contains a symlink')
        if path.is_file():
            actual[path.relative_to(destination).as_posix()] = path
    if set(actual) != set(expected):
        raise ValueError('Extraction file inventory mismatch')
    for name, data in expected.items():
        if actual[name].read_bytes() != data:
            raise ValueError('Extraction byte mismatch: ' + name)


def extract(image, destination, check=False):
    image, destination = Path(image).resolve(), Path(destination).absolute()
    if destination.is_symlink() or destination.resolve() == image or destination.resolve() in image.parents:
        raise ValueError('Unsafe extraction destination')
    if not check and destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Refusing to replace nonempty extraction destination; use --check')
    tree, index, inventory = derive(image)
    if check:
        check_tree(destination, tree)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Existing empty cars/ is user-supplied. Stage complete contents alongside it.
        with tempfile.TemporaryDirectory(prefix='.gt-extract-', dir=destination.parent) as temp:
            staged = Path(temp) / 'cars'
            staged.mkdir()
            for name, data in tree.items():
                path = staged / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            check_tree(staged, tree)
            if destination.exists():
                destination.rmdir()  # Only the verified-empty directory; never remove files.
            staged.rename(destination)
    return index, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, default=ROOT / 'gran-turismo/game-files/gran-turismo.bin')
    parser.add_argument('--output', type=Path, default=ROOT / 'gran-turismo/cars')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--semantic-report', type=Path, help='Opt-in live TypeSafe inventory assessment, outside extracted tree')
    args = parser.parse_args()
    try:
        if args.semantic_report and (args.semantic_report.resolve() == args.image.resolve() or
                                    args.output.resolve() == args.semantic_report.resolve() or
                                    args.output.resolve() in args.semantic_report.resolve().parents):
            raise ValueError('Semantic report must be separate from source image and extracted tree')
        index, inventory = extract(args.image, args.output, args.check)
        if args.semantic_report:
            from gt_asset_judgments import live_receipt
            receipt = live_receipt(inventory)
            args.semantic_report.parent.mkdir(parents=True, exist_ok=True)
            with args.semantic_report.open('xb') as stream:
                stream.write(json_bytes(receipt))
            if receipt['status'] != 'ok':
                print('SEMANTIC REPORT FAILED: extraction retained; see ' + str(args.semantic_report))
                return 1
        print(f"{'VERIFY OK' if args.check else 'EXTRACT OK'}: {index['simulation_pairs']} simulation pairs, "
              f"{index['arcade_pairs']} arcade pairs, {index['metadata_sections']} metadata sections")
        return 0
    except (ValueError, OSError) as error:
        print('EXTRACTION FAILED: ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
