#!/usr/bin/env python3
"""Compile the editable dealership catalog/GLBs; never read or regenerate recovery assets."""
import argparse
import json
from pathlib import Path
import re

from bake_models import ROOT, bake_car

DEALERSHIP = ROOT / 'dealership/dealership'
OUTPUT = ROOT / 'dealership/public/dealership/cars.json'


def load_all(dealership=DEALERSHIP):
    dealership = Path(dealership)
    catalog = json.loads((dealership / 'catalog.json').read_text())
    if not isinstance(catalog, list) or not catalog:
        raise ValueError('Dealership catalog is empty or not an array')
    cars, seen = [], set()
    for entry in catalog:
        code = entry.get('code') if isinstance(entry, dict) else None
        if not isinstance(code, str) or not re.fullmatch(r'[A-Z0-9_]+', code) or code in seen:
            raise ValueError('Dealership vehicle code is invalid or duplicated')
        if 'model' in entry or 'silhouette' in entry:
            raise ValueError('Dealership catalog contains generated geometry; edit the model GLB instead')
        seen.add(code)
        model = dealership / 'models' / f'{code}.glb'
        if model.is_symlink() or model.stat().st_nlink != 1:
            raise ValueError(f'{code}: dealership model must be an independent file')
        baked = bake_car(code, model.read_bytes(), source_mode=False)
        baked['source']['glb'] = f'dealership/models/{code}.glb'
        baked['source']['preset'] = 'dealership'
        baked['source'].pop('originalModelSha256', None)
        baked['claimLimits'] = ['Editable dealership copy; not a recovery artifact or original-game fidelity claim.',
                                'Surface tones and icon tint are illustrative; static geometry only.']
        if entry.get('displayMode') == 'textured-glb':
            # Validate the edited static GLB with the same strict baker, but load its
            # actual texture maps in the viewer rather than the compact tone mesh.
            baked = {key: baked[key] for key in ('source', 'triangleCount')}
            baked.update(schema=2, claimLimits=[
                'Editable static model with its embedded textures; not original-game rendering fidelity.',
                'Default GLB scene only; source identities and names retain their conversion limits.'])
        cars.append({**entry, 'model': baked})
    return cars


def compiled_text(cars):
    return json.dumps(cars, indent=1) + '\n'


def check(dealership=DEALERSHIP, output=OUTPUT):
    """Check freshness without writing inputs, output or temporary files."""
    expected = compiled_text(load_all(dealership))
    output = Path(output)
    if not output.is_file() or output.read_text() != expected:
        raise ValueError('Dealership display data is stale; run python3 tools/build_dealership.py')


def build(dealership=DEALERSHIP, output=OUTPUT):
    output = Path(output)
    public = ROOT / 'dealership/public'
    protected_paths = [ROOT / 'ford-racing-2', ROOT / 'gran-turismo', ROOT / 'redline',
                       public / 'models.json', Path(dealership)]
    protected_paths.extend(path for path in public.iterdir()
                           if path.is_dir() and path.name != 'dealership')
    for protected in protected_paths:
        if output.resolve() == protected.resolve() or protected.resolve() in output.resolve().parents:
            raise ValueError('Dealership build output must not replace source or editable model files')
    cars = load_all(dealership)
    text = compiled_text(cars)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.json.tmp')
    try:
        temporary.write_text(text)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return cars


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dealership', type=Path, default=DEALERSHIP)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true', help='Fail on stale compiled data; write nothing')
    args = parser.parse_args()
    if args.check:
        try:
            check(args.dealership, args.output)
        except (ValueError, OSError) as error:
            parser.exit(1, f'{error}\n')
        print('PASS dealership freshness: compiled data matches current models and catalog')
    else:
        cars = build(args.dealership, args.output)
        print(f'{len(cars)} dealership cars -> {args.output}; editable models preserved')
