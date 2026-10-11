"""Extraction controls derive expectations from a synthetic disc, never its index."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from extract_mc3_cars import (advisory_inventory, assess_inventory, check_extraction,
                              derive, output_files, write_extraction)
from test_mc3_archive import archive_fixture, iso_fixture


def fixture(path):
    nested = archive_fixture([('resources/vehicle/vp_test_04/car.pck', b'PCK native fixture'),
                              ('vehicle/vp_test_04/car.tex', b'TEX native fixture'),
                              ('vehicle/vp_test_04/car.tex', b'TEX distinct duplicate')], packed=True)
    outer = archive_fixture([('vp_test_04.dat', nested), ('tune/vehicle/vp_test_04.carcfg', b'Car physics'),
                             ('resources/vehicle/shared_tex.ppf', b'Packed texture fixture'),
                             ('resources/vehicle/shared_tex.ppf', b'Another shared occurrence'),
                             ('city/track.pck', b'Do not select city')], packed=True)
    other = archive_fixture([('city/tex.ppf', b'city')])
    path.write_bytes(iso_fixture([('ASSETS.DAT;1', outer), ('TEXTURE.DAT;1', other),
                                 ('SYSTEM.CNF;1', b'BOOT2 = fixture;1\r\n')]))
    return path


class ExtractionTests(unittest.TestCase):
    def test_rederive_nested_occurrences_provenance_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso = fixture(root / 'source.iso'); original = iso.read_bytes()
            index, files = write_extraction(iso, root / 'cars')
            self.assertEqual(len(index['vehicles']), 1)
            self.assertEqual(index['vehicles'][0]['native_members'], 3)
            self.assertTrue(any(r['file'].endswith('00002/vehicle/vp_test_04/car.tex') for r in files))
            self.assertEqual(len([r for r in files if r['file'].endswith('shared_tex.ppf')]), 2)
            self.assertFalse(any(r['file'].endswith('track.pck') for r in files))
            repeated, checked = check_extraction(iso, root / 'cars')
            self.assertEqual(index, repeated); self.assertEqual(files, checked)
            self.assertEqual(iso.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'absent or empty'):
                write_extraction(iso, root / 'cars')
            items = advisory_inventory(index, root / 'cars')
            self.assertTrue(items)
            self.assertTrue(all(len(i['ascii_header']) <= 64 for i in items))

    def test_rewritten_index_cannot_mask_payload_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso = fixture(root / 'source.iso'); output = root / 'cars'
            index, files = write_extraction(iso, output)
            row = next(r for r in files if r['file'].endswith('.tex'))
            (output / row['file']).write_bytes(b'tamper')
            index['files'] = []
            (output / 'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, 'byte mismatch'):
                check_extraction(iso, output)

    def test_missing_extra_symlink_and_destination_controls(self):
        for control in ('missing', 'extra', 'linked_file', 'linked_directory'):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve(); iso = fixture(root / 'source.iso'); output = root / 'cars'
                _, files = write_extraction(iso, output)
                target = output / next(r['file'] for r in files if r['file'].endswith('.tex'))
                if control == 'extra': (output / 'extra').write_bytes(b'!')
                elif control == 'missing': target.unlink()
                elif control == 'linked_file': target.unlink(); target.symlink_to(iso)
                else: (output / 'alias').symlink_to(root, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'coverage mismatch|linked extraction'):
                    check_extraction(iso, output)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso = fixture(root / 'source.iso')
            (root / 'alias').symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'linked extraction destination'):
                write_extraction(iso, root / 'alias/cars')

    def test_changed_source_detected_before_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); iso = fixture(root / 'source.iso')
            from mc3_archive import file_digest
            real = file_digest(iso)
            with patch('extract_mc3_cars.file_digest', side_effect=[real, '0' * 64]):
                with self.assertRaisesRegex(ValueError, 'disc changed'):
                    write_extraction(iso, root / 'cars')
            self.assertFalse((root / 'cars').exists())
            self.assertFalse(any(p.name.startswith('mc3-stage-') for p in root.iterdir()))

    def test_no_vehicle_carriers_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'source.iso'
            p.write_bytes(iso_fixture([('ASSETS.DAT;1', archive_fixture([('city/a.pck', b'city')])),
                                      ('SYSTEM.CNF;1', b'boot')]))
            with self.assertRaisesRegex(ValueError, 'no native vehicle carriers'):
                derive(p, lambda path, data: None)

    def test_screening_does_not_send_nonpass_to_live_provider(self):
        for action in ('review', 'block', 'skip'):
            with self.subTest(action=action), patch('jev_mcp_call.call', return_value={
                    'recommendation': {'action': action}}), patch('gt_asset_judgments.live_receipt') as live:
                result = assess_inventory([{'path': 'car.tex', 'size': 10}])
                self.assertEqual(result['status'], 'review')
                self.assertEqual(result['results'], [])
                live.assert_not_called()
        with patch('jev_mcp_call.call', return_value={'recommendation': {'action': 'pass'}}), \
                patch('gt_asset_judgments.live_receipt', return_value={'status': 'error', 'results': []}):
            self.assertEqual(assess_inventory([])['status'], 'error')

    def test_output_files_rejects_linked_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); (root / 'alias').symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'linked extraction'):
                output_files(root / 'alias')


if __name__ == '__main__':
    unittest.main()
