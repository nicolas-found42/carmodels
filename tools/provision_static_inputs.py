#!/usr/bin/env python3
"""Copy a supplied private input bundle locally, verify pins, and configure tools.

The source contains data only; parser code is owned by this repository. No symlink
or source checkout is used after provisioning. See docs/static-inputs.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import static_inputs
from corpus_contract import corpus_identity

LAYOUT = {
    'game': 'games/ford-racing-2',
    'overlays': '.scratch/evidence/vu/private-work-016dac24781c4c9ea7c99aa0fa79c310',
    'typed_export': '.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po',
    'historical_inventory': '.scratch/evidence/static-export.json',
    'historical_functions': '.scratch/mesh/codex-root/decompile-all-02',
    'dispatch_functions': '.scratch/mesh/codex-root/decompile-dispatch-all-3837-02',
    'vif_contract': '.scratch/mesh/codex-root/github-raw-Vif_Unpack.cpp',
    'gs_tables': '.scratch/mesh/codex-root/github-raw-GSTables.cpp',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def copy_paths(source, destination, relatives):
    """Copy real files, reject traversal/symlinks, preserve an existing differing destination."""
    if source.resolve() == destination.resolve():
        raise ValueError('source and destination must differ')
    copied = 0
    for relative in relatives:
        part = Path(relative)
        if part.is_absolute() or '..' in part.parts:
            raise ValueError('relative input path escapes the bundle')
        start = source / part
        if not start.exists():
            raise ValueError('required input is missing: ' + relative)
        files = sorted(start.rglob('*')) if start.is_dir() else [start]
        for path in [start, *files]:
            if path.is_symlink():
                raise ValueError('symlink input is not an independent copy: ' + relative)
        for path in files:
            if not path.is_file():
                continue
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.is_symlink() or digest(target) != digest(path):
                    raise ValueError('existing local input differs: ' + str(target))
                continue
            shutil.copy2(path, target)
            copied += 1
    return copied


def validate_bundle(bundle):
    """Validate archive identity and the executable, typed inventory and overlay byte pins."""
    identity = corpus_identity(bundle / LAYOUT['game'])
    expected = static_inputs.pins()
    if digest(bundle / LAYOUT['typed_export'] / 'inventory.json') != expected['inventory_sha256']:
        raise ValueError('typed inventory differs from receipt pin')
    overlays = bundle / LAYOUT['overlays']
    for n, pin in expected['overlays'].items():
        if digest(overlays / ('overlay-%d.bin' % n)) != pin:
            raise ValueError('overlay %d differs from receipt pin' % n)
        if not (overlays / ('overlay-%d.s' % n)).is_file():
            raise ValueError('overlay %d disassembly missing' % n)
    return identity


def configure(bundle, config):
    values = {
        'CARMODELS_BUNDLE': str(bundle.resolve()),
        'CARMODELS_OVERLAY_DIR': str((bundle / LAYOUT['overlays']).resolve()),
        'CARMODELS_TYPED_EXPORT': str((bundle / LAYOUT['typed_export']).resolve()),
        'CARMODELS_EXECUTABLE': str((bundle / LAYOUT['game'] / 'extracted/SLES_517.05').resolve()),
    }
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps(values, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-bundle', required=True, type=Path)
    parser.add_argument('--destination', type=Path, default=static_inputs.ROOT / '.scratch/inputs')
    args = parser.parse_args()
    source, destination = args.from_bundle.expanduser(), args.destination.expanduser()
    validate_bundle(source)
    relatives = list(LAYOUT.values())
    if (source / 'notes/evidence').is_dir():
        relatives += [str(p.relative_to(source)) for p in sorted((source / 'notes/evidence').glob('fr2-*'))]
    relatives += [str(p.relative_to(source)) for p in (source / 'tools').glob('ptg*.py')]
    if (source / 'tools/verify_ptg.py').is_file():
        relatives.append('tools/verify_ptg.py')
    copied = copy_paths(source, destination, relatives)
    identity = validate_bundle(destination)
    (destination / 'bundle-identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    configure(destination, static_inputs.CONFIG)
    print('PASS provision_static_inputs: %d files copied; archive and static pins verified' % copied)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit('static input provisioning failed: ' + str(error)) from error
