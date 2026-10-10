"""Native package imports preserve prior catalogs and reject corruption before mutation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_dealership import build, check, load_all
from build_model_catalog import model_catalog
from extract_mc3_cars import write_extraction
from import_mc3_catalogs import GAME, export_packages, import_packages, native_model
from test_extract_mc3_cars import fixture


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def setup(root):
    iso = fixture(root / 'source.iso'); cars = root / 'cars'
    write_extraction(iso, cars)
    source = root / 'public' / GAME
    work = root / 'work'; work.mkdir()
    (work / 'catalog.json').write_text(json.dumps([{'code': 'CUSTOM', 'name': 'Prior user entry'}]))
    (work / 'origins.json').write_text(json.dumps({'schema': 1, 'cars': [{'code': 'CUSTOM', 'custom': True}]}))
    return iso, cars, source, work


class Tests(unittest.TestCase):
    def test_real_fixture_import_repeat_and_freshness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso, cars, source, work = setup(root)
            before = snapshot(cars); disc = iso.read_bytes()
            self.assertEqual(export_packages(iso, cars, source), 1)
            self.assertEqual(import_packages(source, work), 1)
            compiled = model_catalog(root / 'public')['cars'][0]
            self.assertEqual(compiled['asset_kind'], 'native-package')
            self.assertEqual(compiled['native_members'], 3)
            self.assertEqual(compiled['records'], [])
            catalog = json.loads((work / 'catalog.json').read_text())
            self.assertEqual(catalog[0], {'code': 'CUSTOM', 'name': 'Prior user entry'})
            entry = catalog[1]; self.assertEqual(entry['code'], 'MC3_VP_TEST_04')
            native = work / entry['nativePackage']['file']; public = source / 'native/vp_test_04.dat'
            self.assertEqual(native.read_bytes(), public.read_bytes())
            self.assertNotEqual(native.stat().st_ino, public.stat().st_ino)
            self.assertEqual(native.stat().st_nlink, 1)
            catalog[1]['name'] = 'My catalog name'; catalog[1]['customField'] = 'keep'
            (work / 'catalog.json').write_text(json.dumps(catalog))
            prior = snapshot(work)
            self.assertEqual(import_packages(source, work), 0)
            self.assertEqual(export_packages(iso, cars, source), 0)
            self.assertEqual(snapshot(work), prior)
            for malformed in (None, [], 'assets/MC3_VP_TEST_04.dat'):
                with self.assertRaisesRegex(ValueError, 'identity/profile'):
                    native_model({**catalog[1], 'nativePackage': malformed}, work)
            # Isolate the native entry to exercise the actual builder, without a fake GLB.
            (work / 'catalog.json').write_text(json.dumps([catalog[1]]))
            output = root / 'compiled.json'; build(work, output); check(work, output)
            self.assertEqual(load_all(work)[0]['model']['schema'], 3)
            self.assertFalse(list(work.rglob('*.glb')))
            native.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash/size'):
                check(work, output)
            self.assertEqual(snapshot(cars), before); self.assertEqual(iso.read_bytes(), disc)

    def test_corruption_identity_and_duplicate_controls_before_write(self):
        for control in ('hash', 'profile', 'path', 'members', 'duplicate', 'kind', 'name', 'source_tamper'):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve(); iso, cars, source, work = setup(root)
                export_packages(iso, cars, source)
                index = source / 'index.json'; v = json.loads(index.read_text()); row = v['cars'][0]
                reason = 'identity/profile'
                if control == 'hash': row['sha256'] = '0' * 64; reason = 'hash/size'
                elif control == 'profile': row['source_profile'] = 'glb'
                elif control == 'path': row['file'] = '../../source.iso'
                elif control == 'members': row['native_members'] += 1; reason = 'member count'
                elif control == 'duplicate': v['cars'].append(dict(row)); reason = 'duplicated'
                elif control == 'kind': row.pop('asset_kind')
                elif control == 'name': row['display_name'] = 'Invented retail identity'
                elif control == 'source_tamper':
                    (source / row['file']).write_bytes(b'changed'); reason = 'hash/size'
                index.write_text(json.dumps(v)); before = snapshot(work)
                with self.assertRaisesRegex(ValueError, reason): import_packages(source, work)
                self.assertEqual(snapshot(work), before)
                if control != 'duplicate':
                    with self.assertRaises(ValueError): model_catalog(root / 'public')

    def test_rehashed_extraction_tamper_and_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso, cars, source, work = setup(root)
            with self.assertRaisesRegex(ValueError, 'separate'):
                export_packages(iso, cars, cars / 'public')
            p = cars / 'vp_test_04/original/vp_test_04.dat'; p.write_bytes(b'changed')
            index = json.loads((cars / 'index.json').read_text()); index['files'] = []
            (cars / 'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, 'byte mismatch'):
                export_packages(iso, cars, source)
            self.assertFalse(source.exists())

    def test_links_conflicts_and_transaction_rollback(self):
        for control in ('symlink', 'hardlink', 'conflict', 'origin_conflict', 'rollback'):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve(); iso, cars, source, work = setup(root)
                export_packages(iso, cars, source)
                public = source / 'native/vp_test_04.dat'
                if control in ('symlink', 'hardlink'):
                    original = root / 'original.dat'; public.replace(original)
                    if control == 'symlink': public.symlink_to(original)
                    else: os.link(original, public)
                    reason = 'symlinks|independent'
                elif control == 'conflict':
                    (work / 'assets').mkdir(); (work / 'assets/MC3_VP_TEST_04.dat').write_bytes(b'custom')
                    reason = 'Uncatalogued'
                elif control == 'origin_conflict':
                    origins = work / 'origins.json'; v = json.loads(origins.read_text())
                    v['cars'].append({'code': 'MC3_VP_TEST_04', 'custom': True})
                    origins.write_text(json.dumps(v)); reason = 'existing origin record'
                else: reason = 'injected installation failure'
                before = snapshot(work)
                if control == 'rollback':
                    real = Path.replace
                    def reject(path, target):
                        if str(target).endswith('catalog.json'): raise OSError(reason)
                        return real(path, target)
                    with patch.object(Path, 'replace', reject), self.assertRaisesRegex(OSError, reason):
                        import_packages(source, work)
                else:
                    with self.assertRaisesRegex(ValueError, reason): import_packages(source, work)
                self.assertEqual(snapshot(work), before)


if __name__ == '__main__':
    unittest.main()
