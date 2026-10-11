#!/usr/bin/env python3
"""Export separate MC3 preview conversions without modifying native extraction."""
import argparse
import json
from pathlib import Path
import re
import tempfile

from bake_models import ROOT, bake_car
from mc3_model import PROFILE, preview_vehicle, sha, source_path, native_executable
from import_mc3_catalogs import regular

DEFAULT = ROOT / 'midnight-club-3-remix/recovered-models'


def export(extraction=ROOT / 'midnight-club-3-remix/cars', output=DEFAULT):
    extraction, output = Path(extraction), Path(output)
    regular(output)
    if extraction.resolve().is_relative_to(output.resolve()) or output.resolve().is_relative_to(extraction.resolve()):
        raise ValueError('preview export must be separate from native extraction')
    index = json.loads(source_path(extraction, 'index.json').read_text())
    identities, manifests = set(), set()
    for car in index['vehicles']:
        code, manifest = car['id'], car['manifest']
        if (not isinstance(code, str) or not re.fullmatch(r'vp_[a-z0-9_]+', code)
                or manifest != code+'/manifest.json' or code in identities or manifest in manifests):
            raise ValueError('duplicate or invalid native vehicle/output identity')
        source_path(extraction, manifest)
        identities.add(code);manifests.add(manifest)
    if not identities:
        raise ValueError('native preview corpus is empty')
    rows, files = [], {}
    executable = native_executable()
    for car in index['vehicles']:
        manifest = json.loads(source_path(extraction, car['manifest']).read_text())
        if manifest['id'] != car['id']:
            raise ValueError('preview manifest identity differs')
        data, evidence = preview_vehicle(extraction, manifest, index, executable)
        code = car['id']
        baked = bake_car('MC3_'+code.upper(), data, source_mode=False)
        # Export provenance paths remain relative to the repository, never machine-specific.
        rows.append({'code': code, 'file': code+'.glb', 'source_profile': PROFILE,
                     'bytes': len(data), 'sha256': sha(data), 'triangle_count': baked['triangleCount'], **evidence})
        files[code+'.glb'] = data
    files['index.json'] = (json.dumps({'schema': 1, 'cars': rows, 'source': index['source']}, indent=1)+'\n').encode()
    if output.exists():
        expected = set(files)
        actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError('existing preview export coverage differs')
        for name, data in files.items():
            regular(output/name)
            if (output/name).read_bytes() != data:
                raise ValueError('existing preview export differs; nothing overwritten')
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mc3-preview-', dir=output.parent) as temp:
        stage = Path(temp)/'models';stage.mkdir()
        for name, data in files.items():
            (stage/name).write_bytes(data)
        stage.rename(output)
    return len(rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--extraction', type=Path, default=ROOT/'midnight-club-3-remix/cars')
    p.add_argument('--output', type=Path, default=DEFAULT)
    a = p.parse_args()
    print(f'Exported {export(a.extraction, a.output)} source-bound static MC3 previews')
