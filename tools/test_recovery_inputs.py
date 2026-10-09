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
import build_showcase

ROOT = Path(__file__).resolve().parents[1]


def test_parsers():
    census = json.loads((ROOT / 'research/evidence/original-recovery/car-asset-census.json').read_text())
    for name, pin in census['source_code_sha256'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == pin, name
    textures = 0
    for car in census['cars']:
        raw = next((ROOT / 'ford-racing-2/cars' / car['code'] / 'model').iterdir()).read_bytes()
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


def test_dealership_catalog():
    with tempfile.TemporaryDirectory() as tmp:
        public = Path(tmp)
        raw = b'model fixture'
        entry = {'code': 'SHARED_CAR', 'file': 'car.glb', 'bytes': len(raw),
                 'sha256': hashlib.sha256(raw).hexdigest(), 'records': []}
        for game in ['ford-racing-2', 'another game']:
            folder = public / game
            folder.mkdir()
            (folder / 'car.glb').write_bytes(raw)
            (folder / 'index.json').write_text(json.dumps({'cars': [entry]}))
        cars = build_showcase.model_catalog(public)['cars']
        assert {c['id'] for c in cars} == {'ford-racing-2/SHARED_CAR', 'another game/SHARED_CAR'}
        assert {c['file'] for c in cars} == {'ford-racing-2/car.glb', 'another game/car.glb'}
        (public / 'another game/car.glb').write_bytes(b'changed model')
        try:
            build_showcase.model_catalog(public)
        except ValueError as error:
            assert 'hash/size differs' in str(error)
        else:
            raise AssertionError('changed dealership model accepted')
        (public / 'another game/car.glb').write_bytes(raw)
        for bad, reason in [([entry, entry], 'Duplicate'),
                            ([{**entry, 'file': '../ford-racing-2/car.glb'}], 'outside game folder')]:
            (public / 'another game/index.json').write_text(json.dumps({'cars': bad}))
            try:
                build_showcase.model_catalog(public)
            except ValueError as error:
                assert reason in str(error)
            else:
                raise AssertionError('invalid dealership catalog accepted')


if __name__ == '__main__':
    test_parsers()
    test_copy()
    test_local_configuration()
    test_dealership_catalog()
    print('PASS test_recovery_inputs: 35 models, decoded textures, independent copies, configuration and multi-game dealership controls')
