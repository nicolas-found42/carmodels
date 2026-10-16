"""Native GT1 identity/specification/paint joins and intended corrupt-input controls."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import gt_metadata as gt


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = gt.ROOT / 'games/gran-turismo/cars/_metadata'
        cls.spec = (cls.directory / 'sections/13.bin').read_bytes()
        cls.colour = (cls.directory / 'sections/38.bin').read_bytes()
        cls.system = (cls.directory / 'SYSTEM.DAT').read_bytes()
        cls.database = gt.load_database(cls.directory)

    def metadata(self, code='_afr7n', ids=None):
        return gt.model_metadata(self.database, code, [49, 53, 54, 98, 115] if ids is None else ids)

    def test_independent_native_coverage_and_no_suffix_inheritance(self):
        codes = gt.native_directory(self.system)
        self.assertEqual((len(codes), codes[0], codes[-1]), (344, '0logn', 'vgrfr'))
        self.assertEqual(codes[28:30], ['afr7n', 'afr7r'])
        self.assertEqual(len(self.database['specs']), 178)
        self.assertEqual(len(self.database['colours']), 142)
        self.assertEqual(sum(len(rows) for rows in self.database['colours'].values()), 877)
        for code in ['afr7r', 'a-odn', 'c-67n', 'lplan', 'lplbn', 'lplin']:
            with self.subTest(code=code):
                result = self.metadata('_' + code)
                self.assertEqual(result['identity'], {'status': 'unresolved', 'name': None, 'spec_index': None})
                self.assertIsNone(result['specifications'])
                self.assertTrue(all(row['name'] is None for row in result['colour_variants']))
                gt.validate_model_metadata(result)
        for code in ['__afr7n', '_AFR7N', 'simulation/_afr7n', '_afr7', '_afr7n/night', '_zzzzn']:
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'code'):
                self.metadata(code)

    def test_fixed_rx7_and_roadster_specifications(self):
        rx7 = self.metadata()
        self.assertEqual(rx7['identity'], {'status': 'verified', 'name': 'RX-7 FC GT-X', 'spec_index': 131})
        spec = rx7['specifications']
        self.assertEqual([spec[name] for name in ['mass_kg', 'length_mm', 'width_mm', 'height_mm',
                         'wheelbase_mm', 'front_tread_mm', 'rear_tread_mm']],
                         [1250, 4335, 1690, 1270, 2430, 1450, 1440])
        self.assertEqual([spec[name] for name in ['power_raw', 'power_hp_game', 'power_rpm',
                         'torque_raw', 'torque_kgm', 'torque_rpm']], [205, 202, 6500, 2750, 27.5, 3500])
        self.assertEqual([spec[name] for name in ['drive', 'engine_type', 'engine_configuration',
                         'aspiration', 'suspension_front', 'suspension_rear']],
                         ['FR', 'Rotary', 'RE', 'Turbo', 'Strut', 'Multilink'])
        self.assertEqual((spec['displacement_raw'], spec['displacement_cc'],
                          spec['displacement_rotary_chamber_cc'], spec['displacement_rotary_factor']),
                         (654, None, 654, 2))
        roadster = self.metadata('_an16n', [49, 52, 98, 104, 113])
        self.assertEqual(roadster['identity']['name'], "EUNOS ROADSTER '89 NORMAL")
        self.assertEqual(roadster['specifications']['mass_kg'], 980)
        self.assertEqual(roadster['specifications']['displacement_cc'], 1597)
        self.assertIsNone(roadster['specifications']['displacement_rotary_factor'])
        self.assertNotIn('year', roadster['specifications'])
        self.assertNotIn('manufacturer', roadster['specifications'])
        self.assertEqual(gt.validate_model_metadata(rx7), rx7)
        self.assertEqual(self.metadata('afr7n'), rx7)

    def test_palette_identifiers_not_ordinal_positions_and_source_anomalies(self):
        result = self.metadata('_tchvn', [49, 52, 53, 97, 101, 109, 113])
        self.assertEqual([row['name'] for row in result['colour_variants']],
                         ['SUPER WHITEII', 'SILVER METALLIC', 'GRAYISH GREEN MICA METALLIC',
                          'WHITE PEARL MICA', 'WINE RED MICA', 'DARK GREEN MICA P.I.O', 'DARK BLUE MICA'])
        duplicate = self.metadata('_arodn', [103])
        found = duplicate['provenance']['colour_name_matches'][0]['matching_slots']
        self.assertEqual([row['slot'] for row in found], [4, 5])
        self.assertEqual([row['colour_id'] for row in found], [103, 103])
        missing = self.metadata('_hcvon', [49, 54])
        self.assertIsNone(missing['colour_variants'][0]['name'])
        self.assertEqual(missing['colour_variants'][0]['label'], 'Native colour 1 (0x31)')
        self.assertEqual(self.metadata('_afr7n', [ord('B')])['colour_variants'][0]['name'], 'BLAZE RED')
        for metadata in [result, duplicate, missing]:
            gt.validate_model_metadata(metadata)

    def test_source_and_lookup_pins_and_required_system(self):
        for index, source in enumerate([self.spec, self.colour, self.system]):
            wrong = bytearray(source)
            wrong[-1] ^= 1
            inputs = [self.spec, self.colour, self.system]
            inputs[index] = bytes(wrong)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'source pin'):
                gt.database_from_bytes(*inputs)
        wrong = bytearray(self.system)
        wrong[0xb9c:0xba2], wrong[0xba2:0xba8] = wrong[0xba2:0xba8], wrong[0xb9c:0xba2]
        with self.assertRaisesRegex(ValueError, 'SYSTEM source pin'):
            gt.native_directory(wrong)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'requires CARINF sections13/38 and SYSTEM.DAT'):
                gt.load_database(root)
            receipt = json.loads(gt.LOOKUPS.read_text())
            receipt['identities'][131]['model'] = 'Invented'
            path = root / 'lookups.json'
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'lookup receipt pin'):
                gt._lookup_tables(path)

    def test_bounded_structure_strings_and_references(self):
        controls = []
        wrong = bytearray(self.spec)
        wrong[4] = ord('X')
        controls.append((wrong, 'section header'))
        wrong = bytearray(self.spec)
        struct.pack_into('<I', wrong, 20, 8)
        controls.append((wrong, 'section header'))
        controls.append((self.spec[:100], 'record extent'))
        wrong = bytearray(self.spec)
        pool = 24 + 178 * 424
        struct.pack_into('<I', wrong, pool, 100000)
        controls.append((wrong, 'string-group extent'))
        wrong = bytearray(self.spec)
        wrong[pool + 4] = 1
        controls.append((wrong, 'string pointers'))
        wrong = bytearray(self.spec)
        wrong[pool + 15 + len('STARLET')] = 1
        controls.append((wrong, 'terminator'))
        wrong = bytearray(self.spec)
        wrong[pool + 15] = 255
        controls.append((wrong, 'not ASCII'))
        controls.append((self.spec + b'X', 'trailing section'))
        for data, reason in controls:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                gt._section(data, b'@(#)SPEC', 424)
        wrong = bytearray(self.spec)
        struct.pack_into('<I', wrong, 24 + 0x188, 0xffffffff)
        records, strings = gt._section(wrong, b'@(#)SPEC', 424)
        with self.assertRaisesRegex(ValueError, 'reference outside pool'):
            gt._string(strings, gt._u32(records[0], 0x188))
        wrong = bytearray(self.system)
        wrong[0xb9c] = ord('_')
        with patch.object(gt, 'SYSTEM_SHA256', gt.sha(wrong)):
            with self.assertRaisesRegex(ValueError, 'native code outside'):
                gt.native_directory(wrong)

    def test_detached_metadata_rejects_fabrication_nonfinite_and_inconsistent_values(self):
        original = self.metadata()
        controls = []
        wrong = copy.deepcopy(original)
        wrong['identity']['name'] = 'Invented RX-7'
        controls.append((wrong, 'identity name/status/index'))
        wrong = self.metadata('_afr7r')
        wrong['specifications'] = original['specifications']
        controls.append((wrong, 'unresolved identity carries specifications'))
        for key, value, reason in [('mass_kg', float('nan'), 'numeric mass_kg'),
                                   ('length_mm', -1, 'numeric length_mm'),
                                   ('mass_kg', True, 'numeric mass_kg'),
                                   ('torque_kgm', float('inf'), 'torque conversion'),
                                   ('power_hp_game', 205, 'power conversion'),
                                   ('displacement_rotary_factor', 2.0, 'displacement representation')]:
            wrong = copy.deepcopy(original)
            wrong['specifications'][key] = value
            controls.append((wrong, reason))
        wrong = copy.deepcopy(original)
        wrong['identity']['spec_index'] = True
        controls.append((wrong, 'identity name/status/index'))
        wrong = copy.deepcopy(original)
        wrong['colour_variants'][0]['name'] = 'Invented paint'
        controls.append((wrong, 'native colour name'))
        wrong = copy.deepcopy(original)
        wrong['colour_variants'][0]['index'] = 1
        controls.append((wrong, 'colour index/identifier'))
        wrong = copy.deepcopy(original)
        wrong['provenance']['colour_source_slots'][0]['name'] = 'Invented paint'
        controls.append((wrong, 'native colour slots'))
        wrong = copy.deepcopy(original)
        wrong['provenance']['system_sha256'] = '0' * 64
        controls.append((wrong, 'provenance system_sha256'))
        for metadata, reason in controls:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                gt.validate_model_metadata(metadata)
        for ids in [[], [True], [256], [1] * 17]:
            with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, 'CTEX profile'):
                self.metadata(ids=ids)

    def test_metadata_results_do_not_mutate_shared_database(self):
        result = self.metadata()
        result['specifications']['mass_kg'] = 1
        result['provenance']['claim_limits'].clear()
        result['provenance']['colour_source_slots'][0]['name'] = 'Edited'
        original = self.metadata()
        self.assertEqual(original['specifications']['mass_kg'], 1250)
        self.assertEqual(original['colour_variants'][0]['name'], 'CRYSTAL WHITE')
        gt.validate_model_metadata(original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
