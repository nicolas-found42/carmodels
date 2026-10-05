#!/usr/bin/env python3
"""Check repo-owned parsers against the committed corpus and independent-copy controls."""
import hashlib
import json
from pathlib import Path
import tempfile

import evidence_common
import provision_static_inputs as provision
import ps2_container
import ps2_sections
import static_inputs

ROOT = Path(__file__).resolve().parents[1]


def test_parsers():
    census = json.loads((ROOT / 'research/evidence/original-recovery/car-asset-census.json').read_text())
    for name, pin in census['source_code_sha256'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == pin, name
    textures = 0
    for car in census['cars']:
        raw = next((ROOT / 'reference/ford/cars' / car['code'] / 'model').iterdir()).read_bytes()
        parsed = ps2_sections.parse(raw)
        assert json.loads(json.dumps(parsed['geometry'])) == car['geometry'], car['code']
        assert len(parsed['textures']['items']) == len(car['textures'])
        for item, expected in zip(parsed['textures']['items'], car['textures']):
            rgba = ps2_container.decode_rgba(raw, item)
            assert hashlib.sha256(rgba).hexdigest() == expected['rgba_sha256']
            textures += 1
        try:
            ps2_sections.parse(raw[:16])
        except (evidence_common.Invalid, evidence_common.Incomplete):
            pass
        else:
            raise AssertionError('truncated model accepted: ' + car['code'])
    assert len(census['cars']) == 35 and textures == census['summary']['textures']


def test_copy():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source, dest = root / 'source', root / 'dest'
        source.mkdir()
        (source / 'file').write_bytes(b'original')
        assert provision.copy_paths(source, dest, ['file']) == 1
        (source / 'file').write_bytes(b'changed source')
        assert (dest / 'file').read_bytes() == b'original'
        assert (dest / 'file').stat().st_ino != (source / 'file').stat().st_ino
        for paths in [['file'], ['../outside'], ['missing']]:
            try:
                provision.copy_paths(source, dest, paths)
            except ValueError:
                pass
            else:
                raise AssertionError('bad copy accepted: ' + str(paths))
        (source / 'link').symlink_to(source / 'file')
        try:
            provision.copy_paths(source, dest, ['link'])
        except ValueError as error:
            assert 'symlink' in str(error)
        else:
            raise AssertionError('symlink input accepted')
        config = root / 'config.json'
        provision.configure(dest, config)
        values = json.loads(config.read_text())
        assert values['CARMODELS_BUNDLE'] == str(dest.resolve())
        assert all(str(dest.resolve()) in v for v in values.values())


def test_local_configuration():
    import os
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / 'paths.json'
        values = {v: tmp for v in static_inputs.VARIABLES.values()}
        config.write_text(json.dumps(values))
        env = {'CARMODELS_INPUT_CONFIG': str(config)}
        with patch.dict(os.environ, env, clear=True):
            assert static_inputs.available()
            assert static_inputs.typed_export() == Path(tmp)
        env['CARMODELS_TYPED_EXPORT'] = str(Path(tmp) / 'override')
        with patch.dict(os.environ, env, clear=True):
            assert static_inputs.configured('CARMODELS_TYPED_EXPORT') == env['CARMODELS_TYPED_EXPORT']


if __name__ == '__main__':
    test_parsers()
    test_copy()
    test_local_configuration()
    print('PASS test_recovery_inputs: 35 models, decoded textures, truncated-model controls, independent copies and configuration')
