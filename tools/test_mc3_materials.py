"""Synthetic native-profile material reads and precise corruption controls."""
import struct
import unittest

from mc3_materials import find_material_tables, read_material_table


def fixture(delta=0):
    data = bytearray(1024)
    base = 0x6800000
    struct.pack_into('<4I', data, 0, base, 0x38e030, 1, len(data) - 128)
    struct.pack_into('<IIHHI', data, 128, 0x7a1138 + delta, base + 64,
                     3, 3, base + 240)
    for index, (obj, kind) in enumerate([(256, 0x7a9920),
                                       (384, 0x7aa948), (512, 0x7ffff0)]):
        struct.pack_into('<I', data, 192 + index * 4, base + obj - 128)
        struct.pack_into('<I', data, obj, kind + delta)
    struct.pack_into('<4f', data, 384 + 0x50, 0.1, 0.2, 0.3, 0.4)
    return data


class MaterialTests(unittest.TestCase):
    def test_all_three_profiles_preserve_indices_and_native_vector(self):
        for delta, profile in ((0, 'original'), (0x200, 'mercedes'), (0x1308, 'remix')):
            with self.subTest(profile=profile):
                result = read_material_table(fixture(delta), 128)
                self.assertEqual([m['shader_category'] for m in result],
                                 ['carpaint', 'colored_glass', 'unmapped'])
                self.assertEqual([m['index'] for m in result], [0, 1, 2])
                self.assertEqual(result[1]['profile'], profile)
                self.assertAlmostEqual(result[1]['native_rgba'][3], 0.4)
                self.assertEqual(result[1]['native_rgba_offset'], 464)
                self.assertEqual(result[1]['base_color'], result[1]['native_rgba'])
                self.assertEqual(result[1]['alpha_mode'], 'BLEND')
                self.assertEqual(result[1]['display_factor_source'], 'native-colored-glass-vector')
                self.assertEqual(result[0]['display_factor_source'], 'neutral-inspection-fallback')
                self.assertEqual(result[2]['base_color'], [0.65, 0.65, 0.65, 1])
                # Generic collection discovery doesn't select among valid roots.
                self.assertEqual(find_material_tables(fixture(delta)), [])

    def test_corrupt_source_vectors(self):
        for bad in (float('nan'), float('inf'), -0.1, 1.1):
            changed = fixture()
            struct.pack_into('<f', changed, 464, bad)
            with self.assertRaisesRegex(ValueError, 'invalid colored-glass source vector'):
                read_material_table(changed, 128)
        opaque = fixture()
        struct.pack_into('<f', opaque, 476, 1.0)
        self.assertEqual(read_material_table(opaque, 128)[1]['alpha_mode'], 'OPAQUE')

    def test_bounds_profile_and_capacity(self):
        for offset, value, reason in ((128, 0xdeadbeef, 'unsupported material collection'),
                                      (132, 0x123, 'pointer before PCK body'),
                                      (132, 0x680ffff, 'read outside PCK'),
                                      (136, 0x00020003, 'invalid material collection count'),
                                      (192, 0x680ffff, 'read outside PCK')):
            changed = fixture()
            struct.pack_into('<I', changed, offset, value)
            with self.assertRaisesRegex(ValueError, reason):
                read_material_table(changed, 128)
        with self.assertRaisesRegex(ValueError, 'payload length mismatch'):
            read_material_table(fixture()[:460], 128)

    def test_header_and_discovery(self):
        data = fixture()
        struct.pack_into('<I', data, 512, 0x7aa7c8)
        tables = find_material_tables(data)
        self.assertEqual([t['file_offset'] for t in tables], [128])
        self.assertEqual(len(tables[0]['materials']), 3)
        for offset, value, reason in ((8, 2, 'version or payload length mismatch'),
                                      (12, 1, 'version or payload length mismatch'),
                                      (0, 0xffffffff, 'serialized address outside bound')):
            changed = bytearray(data)
            struct.pack_into('<I', changed, offset, value)
            with self.assertRaisesRegex(ValueError, reason):
                read_material_table(changed, 128)


if __name__ == '__main__':
    unittest.main()
