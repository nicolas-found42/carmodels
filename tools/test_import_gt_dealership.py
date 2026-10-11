#!/usr/bin/env python3
"""GT imports reject corrupt sources and preserve existing editable copies."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

from bake_models import ROOT, read_glb
from build_dealership import build, check
from import_gt_dealership import import_cars, imported_entry


class GTImportTests(unittest.TestCase):
    def change_source(self, source, row):
        path = source / row['file']
        doc, binary = read_glb(path.read_bytes())
        doc['asset']['generator'] = 'Updated source fixture'
        encoded = json.dumps(doc).encode()
        encoded += b' ' * (-len(encoded) % 4)
        data = (struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(binary)) +
                struct.pack('<I4s', len(encoded), b'JSON') + encoded +
                struct.pack('<I4s', len(binary), b'BIN\0') + binary)
        path.write_bytes(data)
        row.update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   claim_limits=['Updated native assembly fixture.'])
        (source / 'index.json').write_text(json.dumps({'cars': [row]}))
        return data

    def test_explicit_upgrade_only_unedited_models_and_preserve_history(self):
        for edited in (False, True):
            with self.subTest(edited=edited), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.fixture(Path(tmp))
                import_cars(source, dest)
                initial_origins = json.loads((dest / 'origins.json').read_text())
                catalog = json.loads((dest / 'catalog.json').read_text())
                catalog[1]['name'] = 'Custom name'
                catalog[1]['claimLimits'].append('Custom owner limitation.')
                (dest / 'catalog.json').write_text(json.dumps(catalog))
                target = dest / f"models/{catalog[1]['code']}.glb"
                if edited:
                    target.write_bytes(target.read_bytes() + b'owned edit')
                before = {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()}
                updated = self.change_source(source, row)
                self.assertEqual(import_cars(source, dest), 0)
                self.assertEqual(before, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})
                self.assertEqual(import_cars(source, dest, upgrade_unedited=True), int(not edited))
                if edited:
                    self.assertEqual(before, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})
                else:
                    self.assertEqual(target.read_bytes(), updated)
                    current = json.loads((dest / 'catalog.json').read_text())[1]
                    self.assertEqual(current['name'], 'Custom name')
                    self.assertIn(row['claim_limits'][0], current['claimLimits'])
                    self.assertIn('Custom owner limitation.', current['claimLimits'])
                    origin = json.loads((dest / 'origins.json').read_text())['cars'][0]
                    self.assertEqual(origin['initialSource'], initial_origins['cars'][0]['initialSource'])
                    self.assertEqual(origin['latestSource']['sha256'], row['sha256'])
                    self.assertEqual(len(origin['sourceUpgrades']), 1)
                    self.assertEqual(target.stat().st_nlink, 1)
                after = {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()}
                self.assertEqual(import_cars(source, dest, upgrade_unedited=True), 0)
                self.assertEqual(after, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})

    def test_asset_namespaces_and_unknown_values(self):
        day = imported_entry({'code': 'simulation/_test/day'})
        night = imported_entry({'code': 'simulation/_test/night'})
        arcade = imported_entry({'code': 'arcade/pair-0039'})
        self.assertEqual(len({day['code'], night['code'], arcade['code']}), 3)
        self.assertEqual(arcade['sourceVariant'], 'arcade')
        self.assertEqual(arcade['code'], 'GT_ARCADE_PAIR_0039')
        for car in (day, night, arcade):
            self.assertEqual(car['bodyStyle'], 'unknown')
            self.assertIsNone(car['kg'])
        for code in ('arcade/pair-0039/guess', 'simulation/_test/guess', 'simulation/../day'):
            with self.assertRaises(ValueError):
                imported_entry({'code': code})

    def fixture(self, base):
        source, dest = base / 'source', base / 'editable'
        (source / 'simulation/_test').mkdir(parents=True)
        (dest / 'models').mkdir(parents=True)
        initial = json.loads((ROOT / 'dealership/dealership/catalog.json').read_text())[0]
        shutil.copyfile(ROOT / f"dealership/dealership/models/{initial['code']}.glb",
                        dest / f"models/{initial['code']}.glb")
        (dest / 'catalog.json').write_text(json.dumps([initial]))
        (dest / 'origins.json').write_text(json.dumps({'schema': 1, 'cars': []}))
        data = (ROOT / f"dealership/dealership/models/{initial['code']}.glb").read_bytes()
        (source / 'simulation/_test/day.glb').write_bytes(data)
        row = dict(code='simulation/_test/day', file='simulation/_test/day.glb',
                   sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   claim_limits=['Native wheel geometry is not recovered; this is a body preview.'])
        (source / 'index.json').write_text(json.dumps({'cars': [row]}))
        return source, dest, row

    def test_add_preserve_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, dest, row = self.fixture(base)
            original = (dest / 'catalog.json').read_text()
            self.assertEqual(import_cars(source, dest), 1)
            catalog = json.loads((dest / 'catalog.json').read_text())
            self.assertEqual(catalog[0], json.loads(original)[0])
            entry = catalog[1]
            self.assertIsNone(entry['bhp'])
            self.assertIsNone(entry['speed'])
            self.assertIn(row['claim_limits'][0], entry['claimLimits'])
            working = dest / f"models/{entry['code']}.glb"
            self.assertEqual(working.stat().st_nlink, 1)
            self.assertEqual(working.read_bytes(), (source / row['file']).read_bytes())
            result = build(dest, base / 'cars.json')
            self.assertEqual(result[1]['model']['schema'], 2)
            check(dest, base / 'cars.json')
            entry['name'] = 'Edited custom name'
            (dest / 'catalog.json').write_text(json.dumps(catalog))
            working.write_bytes(working.read_bytes() + b'custom edit')
            before = {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()}
            self.assertEqual(import_cars(source, dest), 0)
            self.assertEqual(before, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})

    def test_corruption_collision_and_traversal_fail_before_writes(self):
        mutations = [lambda r: r.update(sha256='0' * 64),
                     lambda r: r.update(bytes=r['bytes'] + 1),
                     lambda r: r.update(file='../outside.glb'),
                     lambda r: r.update(code='simulation/../day'),
                     lambda r: r.update(code='simulation/_test/guess')]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.fixture(Path(tmp))
                before = {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()}
                mutate(row)
                (source / 'index.json').write_text(json.dumps({'cars': [row]}))
                with self.assertRaises(ValueError):
                    import_cars(source, dest)
                self.assertEqual(before, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})
        with tempfile.TemporaryDirectory() as tmp:
            source, dest, row = self.fixture(Path(tmp))
            (source / 'index.json').write_text(json.dumps({'cars': [row, row]}))
            with self.assertRaisesRegex(ValueError, 'collide'):
                import_cars(source, dest)
            with self.assertRaisesRegex(ValueError, 'separate'):
                import_cars(source, source)


if __name__ == '__main__':
    unittest.main()
