"""MCLA native coverage, static identity and re-derivation tamper controls."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from bake_models import read_glb
from gt4_glb import Builder
import import_mcla_catalog as catalog

CODE = 'vp_test_car_01'


def preview(_extraction, code):
    b = Builder()
    positions = b.accessor([(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'position')
    normals = b.accessor([(0, 0, 1)] * 3, 'normal')
    indices = b.accessor([0, 1, 2], 'index')
    material = b.material('neutral', [.6, .6, .6, 1])
    b.doc['meshes'] = [{'primitives': [{'attributes': {'POSITION': positions, 'NORMAL': normals},
                                       'indices': indices, 'material': material}]}]
    b.doc['nodes'] = [{'mesh': 0, 'name': 'body'}]
    b.doc['scenes'] = [{'nodes': [0]}]
    b.doc['extras'] = {'car': code, 'source_profile': catalog.PROFILE}
    return b.finish(), {'triangles': 1}


def fixture(root):
    extraction, output = root / 'cars', root / 'public' / catalog.GAME
    file = CODE + '/resources/vehicle/' + CODE + '/body_lod_0.xrsc'
    path = extraction / file; path.parent.mkdir(parents=True)
    path.write_bytes(b'checked native data')
    row = {'file': file, 'bytes': path.stat().st_size, 'sha256': catalog.sha(path.read_bytes()),
           'source': {'archive_path': file[len(CODE) + 1:]}}
    manifest = {'id': CODE, 'files': [row]}
    (extraction / CODE / 'manifest.json').write_text(json.dumps(manifest))
    vehicle = {'id': CODE, 'manifest': CODE + '/manifest.json'}
    (extraction / 'index.json').write_text(json.dumps({'vehicles': [vehicle], 'source': {'sha256': 'a' * 64}}))
    identities = {CODE: {'name': CODE, 'name_source': {'kind': 'code-fallback', 'code': CODE}}}
    return extraction, output, identities


def export(extraction, output, identities):
    with patch.object(catalog, 'build_car', preview):
        return catalog.export_catalog(extraction, output, identities)


class Tests(unittest.TestCase):
    def test_availability_distinguishes_missing_disc_and_partial_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            extraction, _, _ = fixture(root)
            iso = root / 'disc.iso'
            def available():
                with patch('sys.argv', ['import_mcla_catalog', '--available', '--iso', str(iso),
                                        '--extraction', str(extraction)]):
                    return catalog.main()
            self.assertEqual(available(), 1, 'complete extraction without optional disc must skip')
            iso.write_bytes(b'available input')
            self.assertEqual(available(), 0)
            index = json.loads((extraction / 'index.json').read_text())
            index['vehicles'].append({'id': 'vp_missing', 'manifest': 'vp_missing/manifest.json'})
            (extraction / 'index.json').write_text(json.dumps(index))
            self.assertEqual(available(), 2, 'partial extraction must fail')
            iso.unlink()
            self.assertEqual(available(), 2, 'missing disc must not hide partial extraction')
            (extraction / CODE / 'manifest.json').unlink()
            self.assertEqual(available(), 1, 'committed index without local files must skip')

    def test_export_repeat_and_rederive(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            self.assertEqual(export(extraction, output, identities), 1)
            self.assertEqual(export(extraction, output, identities), 0)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            data = catalog.source_package(row, output)
            self.assertEqual(read_glb(data)[0]['extras']['car'], CODE)
            members = catalog.package_members(CODE, (output / row['native_package']['file']).read_bytes())
            self.assertEqual(members['resources/vehicle/' + CODE + '/body_lod_0.xrsc'], b'checked native data')
            self.assertEqual(row['display_name'], CODE)

    def test_missing_zip_restored_and_catalog_permits_local_absence(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve()); export(extraction, output, identities)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            path = output / row['native_package']['file']; expected = path.read_bytes(); path.unlink()
            catalog.source_package(row, output)
            self.assertEqual(export(extraction, output, identities), 0)
            self.assertEqual(path.read_bytes(), expected)

    def test_restore_and_display_identity_fail_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve()); export(extraction, output, identities)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            native = output / row['native_package']['file']; native.unlink()
            model = output / row['file']; original = model.read_bytes(); model.write_bytes(b'edited')
            with self.assertRaisesRegex(ValueError, 'hash/size'): export(extraction, output, identities)
            self.assertFalse(native.exists())
            model.write_bytes(original)
            current = json.loads((output / 'index.json').read_text())
            current['cars'][0]['native_package']['bytes'] = 1
            (output / 'index.json').write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError, 'differs from its pin'): export(extraction, output, identities)
            self.assertFalse(native.exists())
            row.update(display_name='Invented Ferrari', name_source={'kind': 'ui-string', 'key': 'vp_wrong'})
            with self.assertRaisesRegex(ValueError, 'display identity'): catalog.source_package(row, output)

    def test_changed_native_prevents_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            next(extraction.rglob('*.xrsc')).write_bytes(b'changed native data')
            with self.assertRaisesRegex(ValueError, 'hash/size differs'):
                export(extraction, output, identities)
            self.assertFalse(output.exists())

    def test_rehashed_wrong_identity_and_triangle_declaration(self):
        for field, value, reason in [('source_code', 'vp_wrong', 'identity'), ('source_variant', 'night', 'identity'),
                                     ('records', [{'role': 'stock', 'triangles': 9}], 'triangle declaration')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                extraction, output, identities = fixture(Path(temp).resolve()); export(extraction, output, identities)
                row = json.loads((output / 'index.json').read_text())['cars'][0]
                row[field] = value
                with self.assertRaisesRegex(ValueError, reason): catalog.source_package(row, output)
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve()); export(extraction, output, identities)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            data, _ = preview(extraction, 'vp_wrong')
            (output / row['file']).write_bytes(data)
            row.update(bytes=len(data), sha256=catalog.sha(data))
            with self.assertRaisesRegex(ValueError, 'GLB identity differs'): catalog.source_package(row, output)

    def test_paths_duplicates_corrupt_zip_and_manifest(self):
        for file in ('../outside', '/' + CODE + '/file', CODE + '/../../outside', CODE + '/bad\\file'):
            with self.subTest(file=file), self.assertRaisesRegex(ValueError, 'Unsafe'):
                catalog.member_path(CODE, {'file': file})
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve()); export(extraction, output, identities)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            native = output / row['native_package']['file']
            members = catalog.package_members(CODE, native.read_bytes())
            members['extra.txt'] = b'wrong'
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as archive:
                for name, payload in members.items(): archive.writestr(name, payload)
            with self.assertRaisesRegex(ValueError, 'coverage differs'): catalog.package_members(CODE, data.getvalue())
            native.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash/size'): catalog.source_package(row, output)

    def test_duplicate_extraction_symlink_index_and_zip_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            index = extraction / 'index.json'; original = index.read_text(); data = json.loads(original)
            data['vehicles'] *= 2; index.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'duplicate'): export(extraction, output, identities)
            self.assertFalse(output.exists())
            index.write_text(original); export(extraction, output, identities)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            members = catalog.package_members(CODE, (output / row['native_package']['file']).read_bytes())
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                for name, payload in members.items():
                    info = zipfile.ZipInfo(name); info.create_system = 3
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, payload)
            with self.assertRaisesRegex(ValueError, 'regular files'): catalog.package_members(CODE, buffer.getvalue())
            native = output / row['native_package']['file']; native.unlink()
            row['native_package'].update(bytes=-1, sha256='not-a-hash')
            with self.assertRaisesRegex(ValueError, 'native metadata'): catalog.source_package(row, output)
            saved = output / 'saved.json'; (output / 'index.json').rename(saved)
            (output / 'index.json').symlink_to(saved)
            with self.assertRaisesRegex(ValueError, 'symlinks'): export(extraction, output, identities)

    def test_changed_outputs_never_overwritten_and_unsafe_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve()); export(extraction, output, identities)
            model = output / 'previews' / (CODE + '.glb'); model.write_bytes(b'edited')
            with self.assertRaisesRegex(ValueError, 'hash/size'): export(extraction, output, identities)
            self.assertEqual(model.read_bytes(), b'edited')
            with self.assertRaisesRegex(ValueError, 'separate'): export(extraction, extraction / 'public', identities)
            with self.assertRaisesRegex(ValueError, 'coverage'): export(extraction, output, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
