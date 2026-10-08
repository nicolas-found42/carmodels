#!/usr/bin/env python3
"""Fork recovered GLBs and metadata once; never overwrite an existing dealership."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from bake_models import ROOT, load_source_model
from showcase_metadata import load_source_metadata

DEALERSHIP = ROOT / 'viewer/dealership'


def seed(destination=DEALERSHIP):
    destination = Path(destination)
    if destination.exists():
        return False  # Check before reading source files; an existing fork is independent.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.dealership-fork-', dir=destination.parent) as temp:
        staged = Path(temp) / 'dealership'
        models = staged / 'models'
        models.mkdir(parents=True)
        cars = load_source_metadata()
        origins = []
        for car in cars:
            code = car['code']
            initial = load_source_model(code)  # Verify source identity and manifest pin first.
            original = ROOT / f'viewer/public/recovered/{code}.glb'
            copy = models / f'{code}.glb'
            shutil.copyfile(original, copy)  # Independent regular files, never symlinks/hardlinks.
            if hashlib.sha256(copy.read_bytes()).hexdigest() != initial['source']['sha256']:
                raise ValueError(f'{code}: dealership fork differs from source')
            origins.append({'code': code, 'initialSource': initial['source']})
        (staged / 'catalog.json').write_text(json.dumps(cars, indent=1) + '\n')
        (staged / 'origins.json').write_text(json.dumps({'schema': 1, 'cars': origins}, indent=1) + '\n')
        staged.rename(destination)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=DEALERSHIP)
    args = parser.parse_args()
    created = seed(args.destination)
    print(f'{"Created independent dealership" if created else "Preserved existing dealership; no files changed"}: {args.destination}')
