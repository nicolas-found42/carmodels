"""Source-catalog previews and packages must equal a fresh conversion; each tamper control must fail."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from build_model_catalog import model_catalog
from extract_gt4_cars import write_extraction
import gt4_glb
from gt4_specdb import car_specs
from import_gt4_catalog import GAME, check_export, export_packages, source_package
from test_extract_gt4_cars import CAR, SHARED, fixture

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / 'gran-turismo-4/cars'
OTHER = [(path.replace('test0001', 'test0002'), data + b'2', compressed) for path, data, compressed in CAR[:3]]
REAL_MENU = (REAL / 'acra0001/car/menu/acra0001').read_bytes()
REAL_SPEC = car_specs(REAL / 'provenance/specdb/GT4_EU2560')['acra0001']


def fake_specs(_folder):
    return {code: {**REAL_SPEC, 'label': code + '_label', 'name': f'Test Car {code} `04'} for code in ('test0001', 'test0002')}


def real_build(_data, code, spec, source):
    """Synthetic menu bytes stand for the real Acura model so conversion runs end to end."""
    return gt4_glb.build_car(REAL_MENU, code, spec, source)


def converted(test):
    for target, replacement in (('import_gt4_catalog.car_specs', fake_specs), ('import_gt4_catalog.build_car', real_build)):
        test = patch(target, replacement)(test)
    return test


def setup(root):
    iso = fixture(root / 'source.iso', CAR + OTHER + SHARED)
    write_extraction(iso, root / 'cars')
    public = root / 'public'
    return iso, public, public / GAME


def rewrite(output, change):
    index = json.loads((output / 'index.json').read_text())
    change(index['cars'])
    (output / 'index.json').write_text(json.dumps(index))


def repack(path, mutate):
    with zipfile.ZipFile(path) as archive:
        members = {i.filename: archive.read(i) for i in archive.infolist()}
    mutate(members)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    path.write_bytes(buffer.getvalue())


def rehash(output, code, key):
    def change(rows):
        row = next(r for r in rows if r['code'] == code)
        target = row if key == 'file' else row['native_package']
        data = (output / target['file']).read_bytes()
        target['bytes'], target['sha256'] = len(data), hashlib.sha256(data).hexdigest()
    return change


class CatalogTests(unittest.TestCase):
    @converted
    def test_export_check_catalog_and_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso, public, output = setup(root)
            self.assertEqual(export_packages(iso, root / 'cars', output), 2)
            self.assertEqual(check_export(root / 'cars', output), 2)
            self.assertEqual(export_packages(iso, root / 'cars', output), 0)  # Existing equal export stands.
            catalog = model_catalog(public)['cars']
            self.assertEqual([c['id'] for c in catalog], ['gran-turismo-4/test0001', 'gran-turismo-4/test0002'])
            first = catalog[0]
            self.assertEqual((first['display_name'], first['source_variant'], first['file']),
                             ("Test Car test0001 '04", 'showroom', 'gran-turismo-4/previews/test0001.glb'))
            self.assertEqual(first['native_package']['file'], 'gran-turismo-4/native/test0001.zip')
            self.assertEqual(first['native_package']['members'], 7)
            with zipfile.ZipFile(output / 'native/test0001.zip') as archive:
                self.assertEqual(archive.read('car/lod/test0001.pat'), b'Pat0\0\0\0\0')

    @converted
    def test_tamper_controls(self):
        cases = [
            ('hash/size differs', lambda o: (o / 'native/test0001.zip').write_bytes(b'PK' + bytes(100)), None),
            ('hash/size differs', lambda o: (o / 'previews/test0001.glb').write_bytes(b'glTF'), None),
            ('member hash differs', lambda o: repack(o / 'native/test0001.zip', lambda m: m.__setitem__('car/lod/test0001', b'edit')), ('test0001', 'native')),
            ('member names differ', lambda o: repack(o / 'native/test0001.zip', lambda m: m.__setitem__('car/lod/test0002', b'x')), ('test0001', 'native')),
            ('manifest differs from members', lambda o: repack(o / 'native/test0001.zip', lambda m: m.pop('wheel/lod/test0001')), ('test0001', 'native')),
            ('identity/profile|source index differs', lambda o: None, 'name'),
            ('preview GLB identity|differs from re-derived', lambda o: (o / 'previews/test0001.glb').write_bytes((o / 'previews/test0002.glb').read_bytes()), ('test0001', 'file')),
        ]
        for reason, tamper, change in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve(); iso, public, output = setup(root)
                export_packages(iso, root / 'cars', output)
                tamper(output)
                if change == 'name':
                    rewrite(output, lambda rows: rows[0].__setitem__('display_name', ''))
                elif change:
                    rewrite(output, rehash(output, change[0], change[1]))
                with self.assertRaisesRegex(ValueError, reason):
                    check_export(root / 'cars', output)
                if 're-derived' not in reason:
                    with self.assertRaisesRegex(ValueError, reason.split('|')[0]):
                        model_catalog(public)

    @converted
    def test_extraction_divergence_and_overwrite_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso, public, output = setup(root)
            export_packages(iso, root / 'cars', output)
            (root / 'cars/test0001/wheel/menu/test0001').write_bytes(b'edited extraction')
            with self.assertRaisesRegex(ValueError, 'differs from extraction'):
                check_export(root / 'cars', output)
            with self.assertRaisesRegex(ValueError, 'byte mismatch'):
                export_packages(iso, root / 'cars', output)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso, public, output = setup(root)
            export_packages(iso, root / 'cars', output)
            rewrite(output, lambda rows: rows.pop())
            with self.assertRaisesRegex(ValueError, 'differs; nothing overwritten'):
                export_packages(iso, root / 'cars', output)
            with self.assertRaisesRegex(ValueError, 'export must be separate'):
                export_packages(iso, root / 'cars', root / 'cars/inside')

    @converted
    def test_rejects_wrong_row_shapes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso, public, output = setup(root)
            export_packages(iso, root / 'cars', output)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            for key, value in [('file', 'previews/../x.glb'), ('code', 'TOOLONG001'), ('records', []),
                               ('asset_kind', 'native-package'), ('source_variant', 'day'), ('source_code', 'other001'),
                               ('native_package', {**row['native_package'], 'file': 'native/other.zip'})]:
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Invalid GT4'):
                    source_package({**row, key: value}, output)


if __name__ == '__main__':
    unittest.main()
