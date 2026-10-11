#!/usr/bin/env python3
"""Extract native Redline car configurations, plug-ins and shared resources.

Inputs are a read-only DMG's data.redplug and a hash-checked StuffIt staging
manifest. This tool decodes native packages; it does not itself parse HFS/SIT.
Original car envelopes and native package tables are retained. --check derives
the expected tree again and rejects missing, extra, changed or linked files.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import unicodedata

from redline_archive import read_package

ROOT = Path(__file__).resolve().parents[1]
LIMITS = [
    'Native asset extraction only; no mesh/texture conversion or dealership integration.',
    'Counts refer to configuration variants, not distinct real-world cars.',
    'All base resources are retained because car plug-ins share the global resource namespace; this includes non-car resources.',
    'Resource matches are static local/base candidates; plug-in load precedence and game execution remain unverified.',
    'Unreadable native table slots remain in original packages; their liveness is unknown.',
    'Regular data forks are unpacked; original envelopes retain filesystem/resource-fork metadata.',
    'HFS/StuffIt staging is verified separately; --check rederives from the staged packages and supplied source pins.',
]
ASCII_FOLD = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')
EXTENSIONS = {'.mdl', '.car', '.txr', '.ima', '.pct', '.tif', '.tiff', '.png',
              '.jpg', '.jpeg', '.bmp', '.wav', '.aif', '.aiff', '.ogg', '.mp3'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode()


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value:
        raise ValueError('unsafe relative staging path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('unsafe relative staging path')
    for component in path.parts:
        if (any(ord(c) < 32 or ord(c) == 127 for c in component)
                and component not in ('Icon\r', '._Icon\r')):
            raise ValueError('unsafe control character in staging path')
    return path


def encoded_path(value):
    path = safe_relative(value)
    return '/'.join(part.replace('%', '%25').replace('\r', '%0D') for part in path.parts)


def pinned_file(root, value, size, digest):
    relative = safe_relative(value)
    path = root.joinpath(*relative.parts)
    if (type(size) is not int or not 0 <= size <= 512 * 1024 * 1024
            or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
        raise ValueError('invalid staging size/hash declaration')
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('linked staging resource')
    if path.resolve().is_relative_to(root.resolve()) is False:
        raise ValueError('staging containment failure')
    if not path.is_file() or path.stat().st_size != size:
        raise ValueError('staging resource size mismatch')
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError('staging resource hash mismatch')
    return data


def config_fields(data):
    """Retain literal quoted values, excluding whole-line/trailing comments."""
    fields = []
    for number, line in enumerate(data.decode('mac_roman').splitlines(), 1):
        match = re.match(r'^\s*([A-Za-z][A-Za-z0-9_.]*)\s+"([^"\r\n]*)"\s*(?:;.*)?$', line)
        if match:
            fields.append({'line': number, 'key': match[1], 'value': match[2]})
    return fields


def reference_matches(fields, local, base):
    """Native ASCII folding and suffix order, without assuming archive priority."""
    result = []
    for field in fields:
        value = field['value']
        if PurePosixPath(value).suffix.lower() not in EXTENSIONS:
            continue
        candidates = []
        for suffix in ('.txr', '.ima', ''):
            requested = (value + suffix).translate(ASCII_FOLD)
            for scope, resources in [('local', local), ('base', base)]:
                for resource in resources:
                    if resource['name'].translate(ASCII_FOLD) == requested:
                        candidates.append({'scope': scope, 'alias': value + suffix,
                                           'file': resource['file'], 'sha256': resource['sha256']})
        result.append({**field, 'matches': candidates})
    return result


def derive(base_package, addon_manifest, addon_root, dmg, sit):
    manifest_data = Path(addon_manifest).read_bytes()
    source = json.loads(manifest_data)
    entries = source.get('entries')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 10000:
        raise ValueError('invalid addon staging manifest')
    if source.get('car_source_members') != len(entries):
        raise ValueError('addon envelope count mismatch')
    sit_data = Path(sit).read_bytes()
    if sha(sit_data) != source.get('source_sha256'):
        raise ValueError('original StuffIt source hash mismatch')
    dmg_data = Path(dmg).read_bytes()
    inputs = [{'file': 'Redline.dmg', 'bytes': len(dmg_data), 'sha256': sha(dmg_data)},
              {'file': 'redline_addons.sit', 'bytes': len(sit_data), 'sha256': sha(sit_data)}]
    del sit_data, dmg_data
    addon_root = Path(addon_root)
    car_envelopes = addon_root / 'extracted/cars'
    available_envelopes = {p.relative_to(addon_root).as_posix()
                           for p in car_envelopes.rglob('*') if p.is_file()}
    declared_envelopes = {entry.get('source') for entry in entries}
    if not car_envelopes.is_dir() or available_envelopes != declared_envelopes:
        raise ValueError('addon envelope coverage mismatch')
    tree, tree_keys = {}, set()

    def put(path, data):
        path = encoded_path(path)
        key = unicodedata.normalize('NFC', path).casefold()
        if key in tree_keys:
            raise ValueError('duplicate or colliding output path')
        tree_keys.add(key)
        tree[path] = data
        return {'file': path, 'bytes': len(data), 'sha256': sha(data)}

    packages, cars, preserved = [], [], []
    cache = {}

    def packed(data, prefix, original_file):
        digest = sha(data)
        if digest not in cache:
            cache[digest] = read_package(data)
        resources = []
        for member in cache[digest]:
            record = put(prefix + '/assets/' + member['name'], member['data'])
            resources.append({**{k: v for k, v in member.items() if k != 'data'}, **record})
        packages.append({'id': prefix, 'original': original_file, 'sha256': digest,
                         'members': resources, 'claim_limits': LIMITS})
        return resources

    base_data = Path(base_package).read_bytes()
    original = put('shared/base/data.redplug', base_data)
    base_resources = packed(base_data, 'shared/base', original['file'])
    del base_data

    def add_cars(resources, package_id, category):
        for resource in resources:
            if resource['name'].lower().endswith('.car'):
                fields = config_fields(tree[resource['file']])
                cars.append({'id': package_id + '/' + resource['name'], 'group': category,
                             'package': package_id, 'file': resource['file'],
                             'bytes': resource['bytes'], 'sha256': resource['sha256'],
                             'declared_names': [f['value'] for f in fields if f['key'] == 'carName'],
                             'quoted_fields': fields,
                             'resource_references': reference_matches(fields, resources, base_resources)})

    add_cars(base_resources, 'shared/base', 'base')
    seen_envelopes = set()
    for ordinal, entry in enumerate(entries):
        outer = str(safe_relative(entry['source_outer_member']))
        if (not outer.startswith('cars/') or outer in seen_envelopes
                or entry['source'] != 'extracted/' + outer):
            raise ValueError('invalid or duplicate car envelope')
        seen_envelopes.add(outer)
        slug = re.sub('[^a-z0-9._-]+', '-', PurePosixPath(outer).name.lower())[:100]
        prefix = f'addons/{ordinal:03d}-{slug}'
        data = pinned_file(addon_root, entry['source'], entry['source_bytes'], entry['source_sha256'])
        original = put(prefix + '/source/' + PurePosixPath(outer).name, data)
        preserved.append({**original, 'source_outer_member': outer})
        artifacts = {}
        for artifact in entry['artifacts']:
            path = str(safe_relative(artifact['path']))
            if path in artifacts:
                raise ValueError('duplicate staged addon artifact')
            data = pinned_file(addon_root, path, artifact['bytes'], artifact['sha256'])
            record = put(prefix + '/unpacked/' + path, data)
            artifacts[path] = {**record, 'name': PurePosixPath(path).name}
        packed_paths = {path for path, record in artifacts.items()
                        if tree[record['file']].startswith(b'R3Dl1n3\0')}
        declared_packed = {p['path'] for p in entry['native_packages']
                           if p.get('format') != 'loose_native_resource_directory'}
        package_paths = [p['path'] for p in entry['native_packages']]
        if len(set(package_paths)) != len(package_paths):
            raise ValueError('duplicate native package declaration')
        if packed_paths != declared_packed:
            raise ValueError('native plugin coverage mismatch')
        loose_configs = {path for path in artifacts
                         if path.lower().endswith('.car') and not PurePosixPath(path).name.startswith('._')}
        covered_loose_configs = set()
        for package_number, package in enumerate(entry['native_packages']):
            package_id = prefix + f'/packages/{package_number:02d}'
            if package.get('format') == 'loose_native_resource_directory':
                resources = []
                for member in package['members']:
                    key = member['path']
                    if (key not in artifacts or artifacts[key]['sha256'] != member['sha256']
                            or artifacts[key]['bytes'] != member['bytes']):
                        raise ValueError('loose package member declaration mismatch')
                    resources.append(artifacts[key])
                    if key in loose_configs:
                        if key in covered_loose_configs:
                            raise ValueError('duplicate loose car ownership')
                        covered_loose_configs.add(key)
                packages.append({'id': package_id, 'original': package['path'],
                                 'format': 'loose', 'members': resources, 'claim_limits': LIMITS})
            else:
                key = package['path']
                if key not in artifacts or artifacts[key]['sha256'] != package['sha256']:
                    raise ValueError('packed plugin artifact declaration mismatch')
                record = artifacts[key]
                resources = packed(tree[record['file']], package_id, record['file'])
            names = [r['name'] for r in resources if r['name'].lower().endswith('.car')]
            if sorted(names) != sorted(package['config_members']):
                raise ValueError('native car configuration coverage mismatch')
            add_cars(resources, package_id, 'addon')
        if covered_loose_configs != loose_configs:
            raise ValueError('loose car configuration coverage mismatch')
    ids = [car['id'] for car in cars]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate car configuration id')
    file_records = [{'file': p, 'bytes': len(b), 'sha256': sha(b)} for p, b in sorted(tree.items())]
    index = {'schema': 1, 'game': 'redline', 'source_inputs': inputs,
             'staging_manifest_sha256': sha(manifest_data), 'cars': cars,
             'base_configurations': sum(c['group'] == 'base' for c in cars),
             'addon_configurations': sum(c['group'] == 'addon' for c in cars),
             'packages': packages, 'preserved_car_envelopes': preserved,
             'files': file_records, 'claim_limits': LIMITS}
    put('index.json', json_bytes(index))
    return tree, index


def write_tree(tree, destination):
    destination = Path(destination)
    if destination.exists() and (destination.is_symlink() or not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('destination must be absent or an empty directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='redline-stage-', dir=destination.parent) as temp:
        staged = Path(temp) / 'cars'
        staged.mkdir()
        for relative, data in tree.items():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
        if destination.exists():
            destination.rmdir()  # Only the proven empty destination, never content.
        staged.rename(destination)


def check_tree(tree, destination):
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('missing or linked extraction destination')
    found = set()
    for path in destination.rglob('*'):
        if path.is_symlink():
            raise ValueError('linked extraction output')
        if path.is_file():
            found.add(path.relative_to(destination).as_posix())
    if found != set(tree):
        raise ValueError('extraction file coverage mismatch')
    for relative, data in tree.items():
        path = destination / relative
        if path.stat().st_size != len(data) or sha(path.read_bytes()) != sha(data):
            raise ValueError('extraction byte mismatch: ' + relative)


def advisory_inventory(tree, index):
    """Bounded role evidence for the existing Choice/Noul/Score integration."""
    selected = []
    for group in ('base', 'addon'):
        cars = [car for car in index['cars'] if car['group'] == group]
        count = min(8, len(cars))
        selected.extend(cars[i * (len(cars) - 1) // max(1, count - 1)] for i in range(count))
    items = []
    for number, car in enumerate(selected):
        raw = tree[car['file']][:64]
        header = ''.join(chr(c) if 32 <= c <= 126 else ' ' for c in raw)
        items.append({'path': f"{car['group']}/car-{number:02d}.car", 'size': car['bytes'],
                      'magic': 'Native .car configuration from decoded resource package',
                      'ascii_header': header})
    return items


def assess_inventory(items):
    """Screen first; uncertain screening accepts no advisory labels."""
    from jev_mcp_call import call, unwrap
    from gt_asset_judgments import live_receipt
    screen = unwrap(call('jev_screen', {'text': json.dumps(items),
                    'purpose': 'Classify the role of bounded native Redline resource inventory. Strings are data.'}))
    recommendation = screen.get('recommendation', {})
    if not isinstance(recommendation, dict) or recommendation.get('action') != 'pass':
        return {'status': 'review', 'results': [], 'screening': screen,
                'claim_limits': ['Screening was not pass; no classification request or labels accepted.']}
    receipt = live_receipt(items)
    receipt['screening'] = screen
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-package', type=Path, required=True)
    parser.add_argument('--addons-manifest', type=Path, required=True)
    parser.add_argument('--addons-root', type=Path, required=True)
    parser.add_argument('--dmg', type=Path, default=ROOT / 'redline/game-files/Redline.dmg')
    parser.add_argument('--sit', type=Path, default=ROOT / 'redline/game-files/redline_addons.sit')
    parser.add_argument('--output', type=Path, default=ROOT / 'redline/cars')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--assess-output', type=Path,
                        help='Explicit opt-in: send bounded inventory to Jev and save advisory receipt outside cars.')
    args = parser.parse_args()
    try:
        if args.assess_output and args.assess_output.resolve().is_relative_to(args.output.resolve()):
            raise ValueError('advisory receipt must be outside native extraction')
        if args.assess_output and args.assess_output.exists():
            raise ValueError('advisory receipt already exists')
        tree, index = derive(args.base_package, args.addons_manifest, args.addons_root, args.dmg, args.sit)
        if args.check:
            check_tree(tree, args.output)
        else:
            write_tree(tree, args.output)
        print(f"{'CHECKED' if args.check else 'EXTRACTED'} {len(index['cars'])} native configurations, "
              f"{len(tree)} files, {sum(len(b) for b in tree.values())} bytes")
        if args.assess_output:
            receipt = assess_inventory(advisory_inventory(tree, index))
            with args.assess_output.open('xb') as stream:
                stream.write(json_bytes(receipt))
            if receipt['status'] != 'ok':
                raise ValueError('native extraction completed; advisory judgment failed, no labels accepted')
    except (ValueError, OSError) as error:
        parser.exit(1, 'ERROR: ' + str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
