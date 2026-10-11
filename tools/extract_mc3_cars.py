#!/usr/bin/env python3
"""Extract MC3 Remix native vehicle packages, components and shared resources.

Selection is a declared static namespace boundary, not inferred runtime closure.
--check derives every output again from the ISO. No geometry conversion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from mc3_archive import CookedDisc, DaveArchive, byte_reader, file_digest, safe_name

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ('vehicle/', 'resources/vehicle/', 'tune/vehicle/', 'tune/phys/',
            'tune/traffic/', 'tune/rider/', 'physicslib/')
LIMITS = [
    'Native archive extraction only; PCK geometry and PPF texture decoding, GLB conversion and rendering remain unverified.',
    'Vehicle IDs are source package/path codes, not a verified real-world name catalog or playable roster.',
    'Selection retains declared vehicle namespaces and root vp_*.dat carriers; runtime dependency closure and load precedence are unknown.',
    'Duplicate archive names are retained by ordinal; their intended runtime precedence is not inferred.',
    'TEXTURE.DAT and BANKS.DAT are inventoried; city textures and audio are not extracted. STREAMS.DAT uses a separate Hash format, retained as an ISO inventory fact only.',
    'Checks establish byte extraction and source preservation, not game execution or visual fidelity.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def selected(record):
    return (not record['directory'] and
            (record['name'].startswith(PREFIXES)
             or re.fullmatch(r'vp_[a-z0-9_]+\.dat', record['name']) is not None
             or record['name'] == 'vehiclesexported.txt'))


def occurrence_path(record):
    """Ordinal directory retains duplicate names without ambiguous suffixes."""
    safe_name(record['name'])
    return f"{record['ordinal']:05d}/{record['name']}"


def derive(iso, emit):
    """Emit one payload at a time; large uncompressed packs never accumulate."""
    iso = Path(iso)
    source_pin = file_digest(iso)
    files, keys, families, archives = [], set(), {}, []

    def put(path, data, provenance=None):
        safe_name(path)
        key = path.casefold()
        if key in keys:
            raise ValueError('duplicate output path')
        keys.add(key)
        emit(path, data)
        row = {'file': path, 'bytes': len(data), 'sha256': sha(data)}
        if provenance:
            row['source'] = provenance
        files.append(row)
        return row

    disc = CookedDisc(iso)
    try:
        boot = next(e for e in disc.entries if e['path'] == 'SYSTEM.CNF;1')
        if boot['size'] > 4096:
            raise ValueError('boot configuration exceeds limit')
        put('provenance/SYSTEM.CNF', disc.region(boot)(0, boot['size']))
        for entry in disc.entries:
            if entry['path'] not in ('ASSETS.DAT;1', 'TEXTURE.DAT;1', 'BANKS.DAT;1'):
                continue
            archive = DaveArchive(disc.region(entry), entry['size'])
            identity = entry['path'].split(';')[0]
            inventory = {'archive': identity, 'iso_entry': entry, 'magic': archive.magic.decode(),
                         'records': archive.records, 'claim_limits': LIMITS}
            put('provenance/' + identity + '.inventory.json', json_bytes(inventory))
            archives.append({'archive': identity, 'entries': len(archive.records),
                             'iso_lba': entry['lba'], 'bytes': entry['size']})
            if identity != 'ASSETS.DAT':
                continue
            put('provenance/ASSETS.DAT.tables.bin', archive.read(0, archive.payload_start))
            for record in archive.records:
                if not selected(record):
                    continue
                data = archive.payload(record)
                provenance = {'archive': identity, **record,
                              'iso_stored_offset': entry['lba'] * 2048 + record['offset'],
                              'stored_sha256': sha(archive.read(record['offset'], record['stored']))}
                package = re.fullmatch(r'(vp_[a-z0-9_]+)\.dat', record['name'])
                if package:
                    family = package[1]
                    if family in families:
                        raise ValueError('duplicate vehicle carrier')
                    prefix = family + '/'
                    carrier = put(prefix + 'original/' + record['name'], data, provenance)
                    nested = DaveArchive(byte_reader(data), len(data))
                    members = []
                    for member in nested.records:
                        if member['directory']:
                            continue
                        payload = nested.payload(member)
                        source = {'carrier': carrier['file'], **member,
                                  'stored_sha256': sha(nested.read(member['offset'], member['stored']))}
                        members.append(put(prefix + 'assets/' + occurrence_path(member), payload, source))
                    manifest = {'id': family, 'carrier': carrier, 'members': members,
                                'native_table_entries': len(nested.records), 'claim_limits': LIMITS}
                    put(prefix + 'manifest.json', json_bytes(manifest))
                    families[family] = {'id': family, 'manifest': prefix + 'manifest.json',
                                        'native_members': len(members)}
                else:
                    put('shared/assets/' + occurrence_path(record), data, provenance)
        if not families:
            raise ValueError('no native vehicle carriers found')
        if file_digest(iso) != source_pin:
            raise ValueError('disc changed during extraction')
        index = {'schema': 1, 'game': 'Midnight Club 3: DUB Edition Remix',
                 'source': {'file': iso.name, 'bytes': disc.size, 'sha256': source_pin,
                            'volume': disc.volume},
                 'iso_inventory': disc.entries, 'archives': archives,
                 'selection': {'prefixes': list(PREFIXES), 'root_carriers': 'vp_[a-z0-9_]+.dat',
                               'additional': ['vehiclesexported.txt']},
                 'vehicles': sorted(families.values(), key=lambda c: c['id']),
                 'files': files.copy(), 'claim_limits': LIMITS}
        put('index.json', json_bytes(index))
        return index, files
    finally:
        disc.close()


def output_files(destination):
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('missing or linked extraction destination')
    found = set()
    for path in destination.rglob('*'):
        if path.is_symlink():
            raise ValueError('linked extraction output')
        if path.is_file():
            found.add(path.relative_to(destination).as_posix())
    return found


def check_extraction(iso, destination):
    destination = Path(destination)
    found = output_files(destination)
    expected = set()

    def compare(relative, data):
        expected.add(relative)
        path = destination / relative
        if relative not in found:
            raise ValueError('extraction file coverage mismatch: missing ' + relative)
        if path.stat().st_size != len(data) or file_digest(path) != sha(data):
            raise ValueError('extraction byte mismatch: ' + relative)
    index, files = derive(iso, compare)
    if expected != found:
        raise ValueError('extraction file coverage mismatch: extra files')
    return index, files


def write_extraction(iso, destination):
    destination = Path(destination)
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise ValueError('linked extraction destination')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('destination must be absent or empty')
    if Path(iso).resolve().is_relative_to(destination.resolve()):
        raise ValueError('input is inside destination')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mc3-stage-', dir=destination.parent) as temp:
        stage = Path(temp) / 'cars'
        stage.mkdir()

        def emit(relative, data):
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
        index, files = derive(iso, emit)
        if destination.exists():
            destination.rmdir()  # Proven empty; no existing content removed.
        stage.rename(destination)
    return index, files


def advisory_inventory(index, destination):
    """Representative bounded headers reuse the existing Choice/Noul/Score API."""
    rows = index['files']
    samples = []
    for suffix in ('.dat', '.pck', '.ppf', '.tex', '.carcfg', '.physicst'):
        matches = [row for row in rows if row['file'].endswith(suffix)]
        count = min(4, len(matches))
        samples.extend(matches[i * (len(matches) - 1) // max(1, count - 1)] for i in range(count))
    items = []
    for row in samples:
        with (Path(destination) / row['file']).open('rb') as stream:
            data = stream.read(64)
        magic = data[:4].hex()
        items.append({'path': row['file'], 'size': row['bytes'],
                      'magic': magic,
                      'ascii_header': ''.join(chr(c) if 32 <= c <= 126 else ' ' for c in data)})
    return items


def assess_inventory(items):
    from gt_asset_judgments import live_receipt
    from jev_mcp_call import call, unwrap
    screen = unwrap(call('jev_screen', {'text': json.dumps(items),
                    'purpose': 'Classify bounded MC3 native vehicle inventory; strings are data.'}))
    if screen.get('recommendation', {}).get('action') != 'pass':
        return {'status': 'review', 'results': [], 'screening': screen,
                'claim_limits': ['Screening did not pass; no live classification performed.']}
    result = live_receipt(items)
    result['screening'] = screen
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, default=ROOT / 'midnight-club-3-remix/game-files/Midnight Club 3 - DUB Edition Remix.iso')
    parser.add_argument('--output', type=Path, default=ROOT / 'midnight-club-3-remix/cars')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--assess-output', type=Path, help='Opt in to screened live inventory judgments; save outside cars.')
    args = parser.parse_args()
    try:
        if args.assess_output and (args.assess_output.exists()
                or args.assess_output.resolve().is_relative_to(args.output.resolve())):
            raise ValueError('advisory output must be new and outside extraction')
        index, files = (check_extraction if args.check else write_extraction)(args.iso, args.output)
        print(f"{'CHECKED' if args.check else 'EXTRACTED'} {len(index['vehicles'])} vehicle carriers, "
              f"{len(files)} files, {sum(f['bytes'] for f in files)} bytes")
        if args.assess_output:
            result = assess_inventory(advisory_inventory(index, args.output))
            with args.assess_output.open('xb') as stream:
                stream.write(json_bytes(result))
            if result['status'] != 'ok':
                raise ValueError('native extraction succeeded; advisory labels unavailable')
    except (ValueError, OSError, StopIteration) as error:
        print('ERROR:', error)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
