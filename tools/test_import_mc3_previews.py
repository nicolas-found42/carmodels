"""Verify native preservation, independent GLBs and fail-before-write import controls."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from bake_models import ROOT, read_glb
from import_mc3_previews import import_previews
from import_mc3_catalogs import LIMITS as NATIVE_LIMITS
from mc3_model import build_glb, PROFILE, sha


class PreviewImportTest(unittest.TestCase):
    def fixture(self, root):
        dealer, source = root/'dealer', root/'source'
        (dealer/'assets').mkdir(parents=True);source.mkdir()
        catalog = json.loads((ROOT/'dealership/dealership/catalog.json').read_text())
        entry = copy.deepcopy(next(r for r in catalog if r.get('game') == 'midnight-club-3-remix'))
        entry.update(displayMode='native-package', claimLimits=NATIVE_LIMITS)
        code = entry['code']
        origins = json.loads((ROOT/'dealership/dealership/origins.json').read_text())
        origin = {'code': code, 'initialSource': next(r['initialSource'] for r in origins['cars'] if r['code'] == code)}
        native = ROOT/'dealership/dealership'/entry['nativePackage']['file']
        (dealer/entry['nativePackage']['file']).write_bytes(native.read_bytes())
        (dealer/'catalog.json').write_text(json.dumps([entry]))
        (dealer/'origins.json').write_text(json.dumps({'schema': 1, 'cars': [origin]}))
        b = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128}
        data, records = build_glb(entry['sourceCode'], [{'name': 'source.mesh', 'bone': 0,
            'mesh': {'source': {'sha256': 'a'*64}, 'draws': [{'material': 0, 'batches': [b]}]}}],
            [{'shader_category': 'unmapped', 'base_color': [.65]*3+[1], 'alpha_mode': 'OPAQUE'}], [])
        row = {'code': entry['sourceCode'], 'file': entry['sourceCode']+'.glb', 'source_profile': PROFILE,
               'bytes': len(data), 'sha256': sha(data), 'triangle_count': 1, 'records': records,
               'claim_limits': ['Static test preview']}
        (source/row['file']).write_bytes(data)
        (source/'index.json').write_text(json.dumps({'cars': [row]}))
        return dealer, source, entry, row

    def test_independent_model_preserves_native_and_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            dealer, source, entry, row = self.fixture(Path(tmp).resolve())
            native = (dealer/entry['nativePackage']['file']).read_bytes()
            self.assertEqual(import_previews(source, dealer), 1)
            model = dealer/'models'/f"{entry['code']}.glb"
            self.assertEqual(model.stat().st_nlink, 1)
            model.write_bytes(b'user edited working copy')
            catalog = json.loads((dealer/'catalog.json').read_text());catalog[0]['name'] = 'Custom name'
            (dealer/'catalog.json').write_text(json.dumps(catalog))
            self.assertEqual(import_previews(source, dealer), 0)
            self.assertEqual(model.read_bytes(), b'user edited working copy')
            self.assertEqual((dealer/entry['nativePackage']['file']).read_bytes(), native)
            self.assertEqual(json.loads((dealer/'catalog.json').read_text())[0]['name'], 'Custom name')

    def test_hash_and_rehashed_identity_controls(self):
        for mutation, reason in [('hash', 'hash/size'), ('identity', 'identity/profile'), ('triangles', 'triangle declaration')]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                dealer, source, entry, row = self.fixture(Path(tmp).resolve())
                before = (dealer/'catalog.json').read_bytes()
                if mutation == 'hash':
                    (source/row['file']).write_bytes(b'wrong')
                elif mutation == 'identity':
                    row['source_profile'] = 'wrong'
                else:
                    row['triangle_count'] = 9
                (source/'index.json').write_text(json.dumps({'cars': [row]}))
                with self.assertRaisesRegex(ValueError, reason):
                    import_previews(source, dealer)
                self.assertEqual((dealer/'catalog.json').read_bytes(), before)
                self.assertFalse((dealer/'models'/f"{entry['code']}.glb").exists())

    def changed_source(self, source, row):
        path = source/row['file']
        doc, binary = read_glb(path.read_bytes())
        doc['extras']['conversion_revision'] = 2
        encoded = json.dumps(doc).encode();encoded += b' ' * (-len(encoded) % 4)
        data = (struct.pack('<4sII', b'glTF', 2, 28+len(encoded)+len(binary)) +
                struct.pack('<I4s', len(encoded), b'JSON') + encoded +
                struct.pack('<I4s', len(binary), b'BIN\0') + binary)
        row.update(bytes=len(data), sha256=sha(data), claim_limits=['Revised inspection limit'])
        path.write_bytes(data)
        (source/'index.json').write_text(json.dumps({'cars': [row]}))
        return data

    def test_refresh_requires_unedited_copy_and_preserves_custom_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            dealer, source, entry, row = self.fixture(Path(tmp).resolve())
            import_previews(source, dealer)
            model = dealer/'models'/f"{entry['code']}.glb"
            old = model.read_bytes()
            catalog = json.loads((dealer/'catalog.json').read_text())
            catalog[0]['name'] = 'Custom name';catalog[0]['claimLimits'].append('Custom caveat')
            (dealer/'catalog.json').write_text(json.dumps(catalog))
            revised = self.changed_source(source, row)
            self.assertEqual(import_previews(source, dealer), 0)
            self.assertEqual(model.read_bytes(), old)
            self.assertEqual(import_previews(source, dealer, refresh_unedited=True), 1)
            self.assertEqual(model.read_bytes(), revised)
            result = json.loads((dealer/'catalog.json').read_text())[0]
            self.assertEqual(result['name'], 'Custom name')
            self.assertIn('Custom caveat', result['claimLimits'])
            self.assertNotIn('Static test preview', result['claimLimits'])
            self.assertEqual(import_previews(source, dealer, refresh_unedited=True), 0)
            model.write_bytes(b'user edited model')
            self.changed_source(source, row)
            self.assertEqual(import_previews(source, dealer, refresh_unedited=True), 0)
            self.assertEqual(model.read_bytes(), b'user edited model')

    def test_failed_refresh_restores_existing_model_and_both_metadata_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dealer, source, entry, row = self.fixture(Path(tmp).resolve())
            import_previews(source, dealer)
            paths = [dealer/'models'/f"{entry['code']}.glb", dealer/'catalog.json', dealer/'origins.json']
            before = {p: p.read_bytes() for p in paths}
            self.changed_source(source, row)
            replace = Path.replace
            def failing_replace(path, target):
                if Path(target) == dealer/'catalog.json':
                    raise OSError('injected catalog commit failure')
                return replace(path, target)
            with patch.object(Path, 'replace', failing_replace), self.assertRaisesRegex(OSError, 'injected'):
                import_previews(source, dealer, refresh_unedited=True)
            self.assertEqual({p: p.read_bytes() for p in paths}, before)


if __name__ == '__main__':
    unittest.main()
