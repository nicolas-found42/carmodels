"""Original material graph, inheritance and corruption controls."""

import copy
import hashlib
import json
import struct
import unittest

from mc3_vehicle_material import EVIDENCE, fragment_fixture, native_material, source_contract, verify_fragment_source


FIXTURE = EVIDENCE.with_name('vehicle-material-fragments.json')


class VehicleMaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fragment_fixture()
        cls.data = bytearray(cls.fixture['source_bytes'])
        for row in cls.fixture['fragments']:
            raw = bytes.fromhex(row['hex'])
            assert hashlib.sha256(raw).hexdigest() == row['sha256']
            cls.data[row['offset']:row['offset'] + len(raw)] = raw
        cls.data = bytes(cls.data)

    def root(self, template, kind='material'):
        return next(row for row in self.fixture['roots']
                    if row['template'] == template and row['expected_root']['kind'] == kind)

    def parse(self, row, data=None):
        return native_material(self.data if data is None else data, {'file_offset': row['offset']})['root']

    def test_all_original_fragments_match_retained_graph(self):
        self.assertEqual(len(self.fixture['roots']), 10)
        for row in self.fixture['roots']:
            with self.subTest(template=row['template'], offset=row['offset']):
                self.assertEqual(self.parse(row), row['expected_root'])

    def test_native_specialized_class_and_parameter_bindings(self):
        paint = self.parse(self.root('carpaint'))
        self.assertEqual((paint['class_id'], paint['bind_address']), (4, 0x3B6928))
        self.assertEqual(paint['paint_input_indices'], [14, 15, 16, 17])
        self.assertEqual(paint['passes'][0]['program'], 4)
        self.assertEqual(len(paint['passes'][0]['textures']), 3)
        glass = self.parse(self.root('colored_glass'))
        self.assertEqual(glass['bind_address'], 0x3B7408)
        self.assertEqual(glass['glass_rgba_words'], [0x3CA0A0A1] * 3 + [0x3F800000])
        self.assertEqual(glass['glass_light_mode'], 0)

    def test_pass_order_preserves_destination_alpha_and_inheritance(self):
        chrome = self.parse(self.root('masked_chrome'))
        self.assertEqual(len(chrome['passes']), 2)
        self.assertEqual(next(x['value'] for x in chrome['passes'][0]['state'] if x['command'] == 9), 8)
        self.assertEqual(next(x['value'] for x in chrome['passes'][1]['state'] if x['command'] == 9), 15)
        # No cull command means inherit caller state, not an inferred default.
        self.assertTrue(all(x['command'] != 0 for p in chrome['passes'] for x in p['state']))
        self.assertNotEqual(chrome['passes'][0]['source_offset'], chrome['passes'][1]['source_offset'])

    def test_gameplay_window_damage_texture_variants_remain_distinct(self):
        window = self.parse(self.root('car_window'))
        self.assertEqual(window['bind_address'], 0x3B7B38)
        self.assertEqual(window['passes'][0]['program'], 12)
        self.assertEqual(len(window['window_texture_variants']), 2)
        self.assertNotEqual(window['window_texture_variants'][0], window['window_texture_variants'][1])

    def test_composite_children_are_not_flattened_to_first_template(self):
        for template, count in [('car_decal', 2), ('carpaint', 2), ('carpaint_novinyl', 3)]:
            graph = self.parse(self.root(template, 'composite'))
            self.assertEqual(len(graph['children']), count)
            self.assertEqual(graph['passes'][0]['state'], [])
            self.assertEqual(graph['children'][0]['kind'], 'material')
        self.assertEqual(self.parse(self.root('car_decal', 'composite'))['selected'], 1)

    def test_decal_children_retain_native_rgba_allocated_by_parent_loader(self):
        node = self.parse(self.root('car_decal', 'composite'))
        self.assertEqual([len(c['parameter_words']) for c in node['children']], [4, 4])
        self.assertEqual(node['children'][0]['parameter_words'], [0x3F800000] * 3 + [0x3F4CCCCD])
        self.assertEqual(node['children'][1]['parameter_words'], [0x3F800000] * 3 + [0x3E4CCCCD])

    def test_specialized_class45_is_a_twelve_byte_texture_wrapper(self):
        # Native3b4800 case2d calls2aff20 and replaces its vtable. Its
        # sourcefactory allocation is12bytes; an ordinary48byte pass read
        # must fail this boundary even though current showroom cars omit it.
        row = self.root('carpaint')
        data = bytearray(self.data)
        base = struct.unpack_from('<I', data)[0]
        listing = struct.unpack_from('<I', data, row['offset'] + 16)[0] - base + 128
        texture_ref = struct.unpack_from('<I', data, listing)[0]
        offset = len(data) - 12
        struct.pack_into('<3I', data, offset, 0x12345678, 0x2D, texture_ref)
        graph = native_material(bytes(data), {'file_offset': offset})['root']
        self.assertEqual((graph['class_id'], graph['kind']), (0x2D, 'texture-wrapper'))
        self.assertEqual(graph['runtime_vtable'], 0x62F890)
        self.assertEqual(graph['texture']['name'], '__metalflake__')
        self.assertNotIn('passes', graph)
        with self.assertRaisesRegex(ValueError, 'outside carrier'):
            native_material(bytes(data[:-1]), {'file_offset': offset})

    def test_linked_pass_cycle_is_rejected(self):
        row = self.root('masked_chrome')
        data = bytearray(self.data)
        struct.pack_into('<I', data, row['offset'] + 36, row['offset'] + 8 - 128 + struct.unpack_from('<I', data)[0])
        with self.assertRaisesRegex(ValueError, 'pass cycle'):
            self.parse(row, bytes(data))

    def test_child_cycle_is_rejected(self):
        row = self.root('car_decal', 'composite')
        data = bytearray(self.data)
        base = struct.unpack_from('<I', data)[0]
        listing = struct.unpack_from('<I', data, row['offset'] + 48)[0] - base + 128
        struct.pack_into('<I', data, listing, row['offset'] + base - 128)
        with self.assertRaisesRegex(ValueError, 'child cycle'):
            self.parse(row, bytes(data))

    def test_state_and_texture_extent_mutations_are_rejected(self):
        row = self.root('carpaint')
        for mutation in ('count', 'state'):
            data = bytearray(self.data)
            if mutation == 'count':
                data[row['offset'] + 32] = 9
            else:
                base = struct.unpack_from('<I', data)[0]
                state = struct.unpack_from('<I', data, row['offset'] + 8)[0] - base + 128
                data[state] = 63
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.parse(row, bytes(data))

    def test_omitted_fragment_bytes_do_not_claim_original_source_identity(self):
        with self.assertRaisesRegex(ValueError, 'fixture source identity'):
            verify_fragment_source(self.data)

    def test_source_receipt_and_executable_tampering_fail_closed(self):
        proof = json.loads(EVIDENCE.read_text())
        changed = copy.deepcopy(proof)
        changed['classes']['4']['bind'] ^= 4
        with self.assertRaisesRegex(ValueError, 'receipt changed'):
            source_contract(receipt=changed)
        with self.assertRaisesRegex(ValueError, 'executable identity'):
            source_contract(b'wrong executable')


if __name__ == '__main__':
    unittest.main(verbosity=2)
