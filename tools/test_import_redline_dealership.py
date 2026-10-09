#!/usr/bin/env python3
"""Redline imports reject corrupt sources and preserve existing editable copies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

from bake_models import ROOT, read_glb
from build_dealership import build, check
from import_redline_dealership import import_cars, imported_entry


class RedlineImportTests(unittest.TestCase):
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
                   source_profile='redline-static-car-v1', source_variant='base', display_name='Literal Redline Car',
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
        def row(code, variant='addon'):
            return {'code': code, 'source_variant': variant,
                    'source_profile': 'redline-static-car-v1', 'display_name': 'Literal Redline Name'}
        entries = [imported_entry(row(code)) for code in ('addon/a-b/car', 'addon/a_b/car', 'addon/A_b/car')]
        self.assertEqual(len({e['code'] for e in entries}), 3)
        for entry in entries:
            self.assertEqual(entry['name'], 'Literal Redline Name')
            self.assertEqual(entry['sourceVariant'], 'addon')
            self.assertEqual(entry['bodyStyle'], 'unknown')
            self.assertIsNone(entry['kg'])
        for code in ('addon/../car', '/addon/a/car', 'addon/a/car.glb', 'addon/a\\car'):
            with self.assertRaises(ValueError):
                imported_entry(row(code))
        for changes in ({'source_variant': 'night'}, {'source_profile': 'guess'}, {'display_name': ''},
                        {'display_name': 'name\nredirect'}, {'claim_limits': 'guess'}):
            with self.assertRaises(ValueError):
                imported_entry({**row('base/car'), **changes})

    def fixture(self, base):
        source, dest = base / 'source', base / 'editable'
        (source / 'base').mkdir(parents=True)
        (dest / 'models').mkdir(parents=True)
        initial = json.loads((ROOT / 'dealership/dealership/catalog.json').read_text())[0]
        shutil.copyfile(ROOT / f"dealership/dealership/models/{initial['code']}.glb",
                        dest / f"models/{initial['code']}.glb")
        (dest / 'catalog.json').write_text(json.dumps([initial]))
        (dest / 'origins.json').write_text(json.dumps({'schema': 1, 'cars': []}))
        data = (ROOT / f"dealership/dealership/models/{initial['code']}.glb").read_bytes()
        doc, binary = read_glb(data)
        doc['extras'] = {'source_profile': 'redline-static-car-v1', 'source_variant': 'base', 'car': 'base/day'}
        encoded = json.dumps(doc).encode()
        encoded += b' ' * (-len(encoded) % 4)
        data = (struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(binary)) +
                struct.pack('<I4s', len(encoded), b'JSON') + encoded +
                struct.pack('<I4s', len(binary), b'BIN\0') + binary)
        (source / 'base/day.glb').write_bytes(data)
        row = dict(code='base/day', file='base/day.glb',
                   sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   source_profile='redline-static-car-v1', source_variant='base', display_name='Literal Redline Car',
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

    def test_profile_identity_links_and_rollback_fail_before_writes(self):
        for field, value in [('car', 'base/wrong'), ('source_profile', 'wrong'), ('source_variant', 'addon')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.fixture(Path(tmp))
                path = source / row['file']
                doc, binary = read_glb(path.read_bytes())
                doc['extras'][field] = value
                encoded = json.dumps(doc).encode()
                encoded += b' ' * (-len(encoded) % 4)
                data = (struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(binary)) +
                        struct.pack('<I4s', len(encoded), b'JSON') + encoded +
                        struct.pack('<I4s', len(binary), b'BIN\0') + binary)
                path.write_bytes(data)
                row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                (source / 'index.json').write_text(json.dumps({'cars': [row]}))
                before = {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()}
                with self.assertRaisesRegex(ValueError, 'identity/profile'):
                    import_cars(source, dest)
                self.assertEqual(before, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})
        with tempfile.TemporaryDirectory() as tmp:
            source, dest, row = self.fixture(Path(tmp))
            before = {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()}
            replace = Path.replace
            def interrupted(path, target):
                if path.name == 'catalog.json':
                    raise OSError('simulated metadata replacement failure')
                return replace(path, target)
            with patch.object(Path, 'replace', interrupted):
                with self.assertRaisesRegex(OSError, 'simulated'):
                    import_cars(source, dest)
            self.assertEqual(before, {p: p.read_bytes() for p in dest.rglob('*') if p.is_file()})
            import_cars(source, dest)
            target = dest / 'models' / (imported_entry(row)['code'] + '.glb')
            target.unlink()
            os.link(source / row['file'], target)
            with self.assertRaisesRegex(ValueError, 'model path'):
                import_cars(source, dest)
        for kind in ('source-directory', 'editable-directory'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.fixture(Path(tmp))
                if kind == 'source-directory':
                    directory = source / 'base'
                    moved = source / 'actual'
                else:
                    directory = dest / 'models'
                    moved = dest / 'actual'
                directory.rename(moved)
                directory.symlink_to(moved, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'path'):
                    import_cars(source, dest)

    def test_corruption_collision_and_traversal_fail_before_writes(self):
        mutations = [lambda r: r.update(sha256='0' * 64),
                     lambda r: r.update(bytes=r['bytes'] + 1),
                     lambda r: r.update(file='../outside.glb'),
                     lambda r: r.update(code='base/../day'),
                     lambda r: r.update(source_variant='guess')]
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
