"""Bounded source-order and refusal controls for native vehicle inputs."""
import copy
import struct
import unittest

from mc3_vehicle_inputs import (fragment_fixture, from_executable, native_material_inputs,
                                native_input_table, source_contract, verify_fragment_source)


class VehicleInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fragment_fixture()
        data = bytearray(cls.fixture['source_bytes'])
        for row in cls.fixture['fragments']:
            raw = bytes.fromhex(row['hex'])
            data[row['offset']:row['offset'] + len(raw)] = raw
        cls.data = bytes(data)
        cls.collection = cls.fixture['collection_offset']

    def test_original_order_and_default_words_are_retained(self):
        rows = native_material_inputs(self.data, self.collection)
        self.assertEqual(rows, self.fixture['expected_inputs'])
        self.assertEqual(rows[14]['name'], 'CarPaintEnvScale')
        self.assertEqual(rows[17]['word'], 0x3F7D70A4)
        self.assertEqual(rows[28]['name'], 'WindowsBroken')
        self.assertEqual(rows[39]['name'], 'blights_on')

    def test_raw_integer_selector_is_not_reinterpreted_as_float(self):
        data = bytearray(self.data)
        row = self.fixture['expected_inputs'][9]
        struct.pack_into('<I', data, row['source_offset'] + 8, 1)
        self.assertEqual(native_material_inputs(bytes(data), self.collection)[9]['word'], 1)

    def test_reordered_list_changes_the_indices(self):
        data = bytearray(self.data)
        first, second, third = self.fixture['expected_inputs'][:3]
        base = struct.unpack_from('<I', data)[0]
        address = lambda offset: offset + base - 128
        struct.pack_into('<I', data, self.collection + 12, address(second['source_offset']))
        struct.pack_into('<I', data, second['source_offset'], address(first['source_offset']))
        struct.pack_into('<I', data, first['source_offset'], address(third['source_offset']))
        rows = native_material_inputs(bytes(data), self.collection)
        self.assertEqual([r['name'] for r in rows[:3]], ['shadowG', 'shadowR', 'shadowB'])
        self.assertEqual(rows[1]['index'], 1)

    def test_empty_table_has_no_invented_defaults(self):
        data = bytearray(self.data)
        struct.pack_into('<I', data, self.collection + 12, 0)
        self.assertEqual(native_material_inputs(bytes(data), self.collection), [])

    def test_cycle_pointer_null_and_non_ascii_controls(self):
        row = self.fixture['expected_inputs'][0]
        for mode in ('cycle', 'pointer', 'null-name', 'non-ascii'):
            data = bytearray(self.data)
            if mode == 'cycle':
                pointer = struct.unpack_from('<I', data, self.collection + 12)[0]
                struct.pack_into('<I', data, row['source_offset'], pointer)
            elif mode == 'pointer':
                struct.pack_into('<I', data, self.collection + 12, 0xFFFFFFFF)
            elif mode == 'null-name':
                struct.pack_into('<I', data, row['source_offset'] + 4, 0)
            else:
                data[row['name_offset']] = 255
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                native_material_inputs(bytes(data), self.collection)

    def test_explicit_page_pointer_mapping_is_used(self):
        calls = []
        base = struct.unpack_from('<I', self.data)[0]
        def pointer(value):
            calls.append(value)
            return value - base + 128
        self.assertEqual(native_material_inputs(self.data, self.collection, pointer), self.fixture['expected_inputs'])
        self.assertEqual(len(calls), 82)

    def test_export_table_binds_original_carrier_and_collection(self):
        import hashlib
        table = native_input_table(self.data, self.collection)
        self.assertEqual(table['source_carrier_sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(table['collection_offset'], self.collection)
        self.assertEqual(table['inputs'], self.fixture['expected_inputs'])
        self.assertIn('runtime-appended', table['claim_limits'][0])

    def test_source_guards_do_not_accept_sparse_or_forged_identity(self):
        with self.assertRaisesRegex(ValueError, 'source identity'):
            verify_fragment_source(self.data)
        proof = copy.deepcopy(source_contract())
        proof['parameter_list']['value_offset'] = 4
        with self.assertRaisesRegex(ValueError, 'receipt changed'):
            source_contract(proof)
        with self.assertRaisesRegex(ValueError, 'executable identity'):
            from_executable(b'fake')


if __name__ == '__main__':
    unittest.main(verbosity=2)
