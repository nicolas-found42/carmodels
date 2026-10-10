"""Native wheel page/handle controls and optional recovered-source checks."""
from pathlib import Path
import struct
import tempfile
import unittest
import os

from mc3_pck import Pck
from mc3_wheels import (_elf_address, ppf_page, read_default_config, read_default_wheels,
                        read_page_model, read_vehicle_class, read_wheel_sizing, select_handle)


class WheelTests(unittest.TestCase):
    def test_native_ppf_offset_mask_and_length(self):
        data = bytearray(8192)
        struct.pack_into('<4s3I', data, 0, b'pf05', 1, 2048, (1 << 20) | 2)
        self.assertEqual(ppf_page(data, 0),
                         {'index': 0, 'packed_page': (1 << 20) | 2, 'offset': 4096, 'bytes': 2048})
        for word, reason in ((2, 'page outside source'), ((5 << 20) | 2, 'page outside source')):
            changed = bytearray(data)
            struct.pack_into('<I', changed, 12, word)
            with self.assertRaisesRegex(ValueError, reason):
                ppf_page(changed, 0)
        with self.assertRaisesRegex(ValueError, 'page outside PPF table'):
            ppf_page(data, 1)
        with self.assertRaisesRegex(ValueError, 'unknown wheel PPF header'):
            ppf_page(b'bad!', 0)

    def test_library_handle_preserves_actual_page_and_rejects_wrong_archive(self):
        data = bytearray(512)
        base = 0x6800000
        struct.pack_into('<4I', data, 0, base, 0x25, 1, len(data) - 128)
        struct.pack_into('<2I', data, 128, base + 32, 1)
        struct.pack_into('<I', data, 160, base + 64)
        struct.pack_into('<4I', data, 192, 0x7AA718, 0, 0x5400, (5 << 23) | 143)
        result = select_handle(Pck(data), 128, 0, 5)
        self.assertEqual(result['page'], 143)
        self.assertEqual(result['library_row_offset'], 192)
        with self.assertRaisesRegex(ValueError, 'unexpected native archive'):
            select_handle(Pck(data), 128, 0, 3)
        with self.assertRaisesRegex(ValueError, 'index outside library'):
            select_handle(Pck(data), 128, 1, 5)
        struct.pack_into('<I', data, 192, 0xdeadbeef)
        with self.assertRaisesRegex(ValueError, 'unknown wheel resource handle'):
            select_handle(Pck(data), 128, 0, 5)

    def test_conflicting_default_configs_are_not_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ordinal, text in ((0, 'RimMdlIdx 136'), (1, 'RimMdlIdx 135')):
                folder = root / 'shared' / str(ordinal)
                folder.mkdir(parents=True)
                (folder / 'vp_350z_04.carcfg').write_text(text)
            with self.assertRaisesRegex(ValueError, 'conflicting shared wheel source copies'):
                read_default_config(root, 'vp_350z_04')
            with self.assertRaisesRegex(ValueError, 'invalid vehicle source ID'):
                read_default_config(root, '../vp_350z_04')

    def test_recovered_350z_join_and_native_geometry(self):
        root = Path(__file__).resolve().parents[1] / 'midnight-club-3-remix/cars'
        if not (root / 'shared').exists():
            self.skipTest('recovered shared source inputs unavailable')
        result = read_default_wheels(root, 'vp_350z_04')
        self.assertEqual([c['page'] for c in result['components']], [143, 6, 6])
        self.assertEqual(result['config']['fields']['RimMdlIdx'], 136)
        self.assertEqual(result['components'][0]['model']['model_file_offset'], 0x82EC20)
        mesh = result['components'][0]['model']['lods']['high'][0]
        self.assertEqual(sum(d['vertex_count'] for d in mesh['draws']), 1115)
        self.assertEqual(len(mesh['draws']), 6)
        self.assertEqual(mesh['source']['sha256'], result['sources']['rim']['sha256'])
        self.assertEqual(mesh['ppf_file_offset'], 0x830290)
        for component in result['components']:
            self.assertTrue(component['model']['lods']['high'])
            self.assertTrue(component['model']['materials'])

    def test_source_model_corruption_controls(self):
        root = Path(__file__).resolve().parents[1] / 'midnight-club-3-remix/cars'
        paths = sorted((root / 'shared').rglob('rim.ppf'))
        if not paths:
            self.skipTest('recovered shared source inputs unavailable')
        data = paths[0].read_bytes()
        page = ppf_page(data, 143)
        for offset, value, reason in ((0x82EC20, 0, 'body missing or ambiguous'),
                                      (0x82EC0C, 0xffffffff, 'body missing or ambiguous'),
                                      (0x830284, 0, 'unknown native wheel mesh collection'),
                                      (0x830288, 0x068FFFFF, 'range outside payload')):
            changed = bytearray(data)
            struct.pack_into('<I', changed, offset, value)
            with self.subTest(offset=hex(offset)), self.assertRaisesRegex(ValueError, reason):
                read_page_model(changed, page)


    def test_elf_virtual_mapping_and_ambiguous_segments(self):
        data = bytearray(512)
        data[:7] = b'\x7fELF\x01\x01\x01'
        struct.pack_into('<I', data, 28, 52)
        struct.pack_into('<2H', data, 42, 32, 1)
        struct.pack_into('<5I', data, 52, 1, 128, 0x600000, 0x600000, 128)
        self.assertEqual(_elf_address(data, 0x600020, 36), 160)
        with self.assertRaisesRegex(ValueError, 'missing or ambiguous'):
            _elf_address(data, 0x60007f, 4)
        struct.pack_into('<H', data, 44, 2)
        data[84:116] = data[52:84]
        with self.assertRaisesRegex(ValueError, 'missing or ambiguous'):
            _elf_address(data, 0x600020, 36)

    def test_nested_class_source_and_ambiguous_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            folder = root / 'shared'
            folder.mkdir()
            path = folder / 'vehicle.lst'
            record = 'Vehicle {\nName vp_test_04\nClass CHOPPER\nPerformanceBase { X 0.5 }\n}\n'
            path.write_text(record)
            result = read_vehicle_class(root, 'vp_test_04')
            self.assertEqual((result['class'], result['native_class_value']), ('CHOPPER', 5))
            path.write_text(record + record)
            with self.assertRaisesRegex(ValueError, 'ambiguous native vehicle class record'):
                read_vehicle_class(root, 'vp_test_04')
            path.write_text(record[:-3])
            with self.assertRaisesRegex(ValueError, 'unbalanced'):
                read_vehicle_class(root, 'vp_test_04')

    def test_native_sizing_car_bike_and_failure_controls(self):
        root = Path(__file__).resolve().parents[1]
        disc = root / 'midnight-club-3-remix/game-files/Midnight Club 3 - DUB Edition Remix.iso'
        if not disc.is_file():
            self.skipTest('supplied game disc source input unavailable')
        from mc3_model import native_executable
        source = native_executable()
        config = read_default_config(root / 'midnight-club-3-remix/cars', 'vp_350z_04')['fields']
        cop_class = read_vehicle_class(root / 'midnight-club-3-remix/cars', 'vp_kwz_cop_98')
        self.assertEqual((cop_class['class'], cop_class['native_class_value']), ('COPBIKE', 10))
        result = read_wheel_sizing(source, config, axle=0)
        self.assertAlmostEqual(result['rim_scale'][0], 0.4300000071525574)
        self.assertAlmostEqual(result['rim_scale'][1], 0.5333999991416931)
        self.assertAlmostEqual(result['tire_scale'][1], 0.682097194)
        self.assertEqual(result['native']['tables']['width']['address'], 0x619a18)
        for vehicle_class, expected in [('SPORTBIKE', 0.7), ('CHOPPER', 0.85), ('COPBIKE', 0.7)]:
            bike = read_wheel_sizing(source, {}, axle=0, bike=True,
                                     vehicle_class=vehicle_class, wheel_max_x=0.08, wheel_rest_y=0.33)
            self.assertAlmostEqual(bike['tire_scale'][0], 0.2848)
            self.assertAlmostEqual(bike['tire_scale'][1], 0.66)
            self.assertAlmostEqual(bike['rim_scale'][1], 0.66 * expected)
        damaged = bytearray(source)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            read_wheel_sizing(bytes(damaged), config, axle=0)
        for change in [('TireWidth0', 9), ('TireProfile0', -1), ('RimSize0', 29)]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'outside table'):
                read_wheel_sizing(source, {**config, change[0]: change[1]}, axle=0)
        with self.assertRaisesRegex(ValueError, 'unknown native bike class'):
            read_wheel_sizing(source, config, axle=0, bike=True)
        with self.assertRaisesRegex(ValueError, 'joint dimensions'):
            read_wheel_sizing(source, config, axle=0, bike=True, vehicle_class='SPORTBIKE',
                              wheel_max_x=float('nan'), wheel_rest_y=.3)

    def test_source_rejects_linked_files_and_directory_ancestry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            folder = root / 'shared'
            folder.mkdir()
            actual = root / 'actual.lst'
            actual.write_text('Vehicle {\nName vp_test_04\nClass CHOPPER\n}\n')
            link = folder / 'vehicle.lst'
            link.symlink_to(actual)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                read_vehicle_class(root, 'vp_test_04')
            link.unlink()
            os.link(actual, link)
            with self.assertRaisesRegex(ValueError, 'hard-linked'):
                read_vehicle_class(root, 'vp_test_04')
            link.unlink()
            # A source directory symlink is rejected before discovery or reads.
            folder.rmdir()
            folder.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                read_vehicle_class(root, 'vp_test_04')


if __name__ == '__main__':
    unittest.main()
