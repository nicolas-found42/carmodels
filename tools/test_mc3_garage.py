"""Bounded world/sky packet profiles and refusal controls."""
import copy
import base64
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

from mc3_garage import (
    SHARED_TEXTURE_PROOF, decode_batches, decode_native_shared_tex,
    decode_prop_inputs, material_pass_inputs, shared_texture_contract,
)
from mc3_pck import Pck, decode_batches as car_batches, vif_planes


def plane(address, components, bits, rows):
    return {'address': address, 'components': components, 'bits': bits,
            'count': len(rows), 'values': rows, 'cl': 1, 'wl': 1, 'offset': 128}


def fixture(world=True):
    origin = 0x9e if world else 0x98
    scale = 1/1024 if world else 1/256
    scale_word = struct.unpack('<I', struct.pack('<f', scale))[0]
    result = [plane(origin, 4, 32, [(scale_word, 0, 0, 0x3f800000), (3, 0, 0, 3)]),
              plane(origin + (0x62 if world else 0x56), 3, 16,
                    [(0, 0, 0), (1024, -1024, 1), (-1, 2, 3)]),
              plane(origin + (0x32 if world else 0x2c), 4, 16,
                    [(0, 4096, 2048, -4096)] * 3),
              plane(origin + 2, 4 if world else 3, 8,
                    [(1, -128, 127, 60) if world else (1, -128, 127)] * 3)]
    if not world:
        result.append(plane(origin + 0x80, 4, 8, [(128, 0, 255, 128)] * 3))
    return result


class GaragePacketTests(unittest.TestCase):
    def test_native_palette_bgra_alpha_and_low_first_nibbles(self):
        for kind, entries in [(14, 256), (16, 16)]:
            palette = bytes((1, 2, 3, 255, 5, 6, 7, 127)) + bytes((entries-2)*4)
            pixels = bytes([0, 1])*128 if kind == 14 else bytes([0x10])*128
            data = struct.pack('<7H', 16, 16, kind, 1, 1, 0, 0) + palette + pixels
            result = decode_native_shared_tex(data)
            rgba = base64.b64decode(result['rgba_base64'])
            self.assertEqual(rgba[:8], bytes((3, 2, 1, 128, 7, 6, 5, 63)))
            with self.assertRaisesRegex(ValueError, 'mip extent'):
                decode_native_shared_tex(data[:-1])

    def test_original_glow_texture_native_pixels(self):
        path = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/tire-alpha-native/garage-packet-fragments.json'
        row = json.loads(path.read_text())['glow_texture']
        source = base64.b64decode(row['source_base64'])
        actual = decode_native_shared_tex(source)
        self.assertEqual(actual, row['expected'])
        rgba = base64.b64decode(actual['rgba_base64'])
        self.assertEqual(set(rgba[0::4]), {255})
        self.assertEqual(max(rgba[3::4]), 128)

    def test_native_texture_contract_rejects_source_and_formula_tampering(self):
        original = json.loads(SHARED_TEXTURE_PROOF.read_text())
        for key, value in [('native_alpha_max', 255), ('file_palette_order', 'RGBA'),
                           ('format16_nibble_order', 'high then low')]:
            changed = copy.deepcopy(original)
            changed['derived_contract'][key] = value
            with self.assertRaisesRegex(ValueError, 'contract changed'):
                shared_texture_contract(changed)
        changed = copy.deepcopy(original)
        changed['selected_words']['0x5248bc'] = '0x0'
        with self.assertRaisesRegex(ValueError, 'pins changed'):
            shared_texture_contract(changed)
        changed = copy.deepcopy(original)
        del changed['intervals']['palette_reader']
        with self.assertRaisesRegex(ValueError, 'pins changed'):
            shared_texture_contract(changed)

    def test_original_compiled_pass_graph_keeps_second_lightmap(self):
        path = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/tire-alpha-native/garage-packet-fragments.json'
        graph = json.loads(path.read_text())['material_graph']
        data = zlib.decompress(base64.b64decode(graph['zlib_base64']))
        for span in graph['retained_ranges']:
            raw = data[span['offset']:span['offset']+span['bytes']]
            self.assertEqual(hashlib.sha256(raw).hexdigest(), span['sha256'])
        actual = material_pass_inputs(Pck(data), graph['material_offset'])
        self.assertEqual(actual, graph['expected'])
        self.assertEqual(actual[0]['textures'][0]['name'], 's_gar_sign_01')
        self.assertEqual(actual[1]['textures'][0]['name'], 'walls')

    def test_original_prop_graph_uses_native_category_lists_and_flags(self):
        path = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/tire-alpha-native/garage-packet-fragments.json'
        graph = json.loads(path.read_text())['prop_graph']
        data = zlib.decompress(base64.b64decode(graph['zlib_base64']))
        self.assertEqual(len(data), graph['source_bytes'])
        for span in graph['retained_ranges']:
            chunk = data[span['offset']:span['offset']+span['bytes']]
            self.assertEqual(hashlib.sha256(chunk).hexdigest(), span['sha256'])

        def geometry(pck, offset):
            # Geometry decoding has its own original packet test. Here isolate
            # the native category/definition graph while keeping the mesh join.
            self.assertEqual(pck.u32(offset), 0x7a1e18)
            return {'offset': offset, 'draws': []}

        with patch('mc3_garage.read_mesh', side_effect=geometry) as mesh:
            result = decode_prop_inputs(data)
        actual = [{key: instance.get(key, []) for key in graph['expected'][0]}
                  for instance in result['instances']]
        self.assertEqual(actual, graph['expected'])
        self.assertEqual(mesh.call_count, 9)
        by_name = {item['name']: item for item in result['instances']}
        self.assertEqual(by_name['s_prop_garage_reflect_2x']['reflection_masks'], [])
        self.assertEqual(by_name['s_prop_garage_floor_x']['reflection_masks'], [2])
        changed = bytearray(data)
        struct.pack_into('<I', changed, 128+0x10, 6)
        with self.assertRaisesRegex(ValueError, 'category counts'):
            decode_prop_inputs(bytes(changed))

    def test_material_pass_chain_keeps_lightmap_binding_and_rejects_cycle(self):
        data = bytearray(512)
        struct.pack_into('<4I', data, 0, 0x6800000, 0x40, 1, len(data)-128)
        pointer = lambda offset: 0x6800000 + offset - 128
        for body, state in [(136, 208), (168, 212)]:
            struct.pack_into('<I', data, body, pointer(state))
            struct.pack_into('<I', data, body+8, pointer(224))
            data[body+24] = 1
        data[208:211] = bytes([0, 2, 255])
        data[212:215] = bytes([8, 127, 255])
        struct.pack_into('<I', data, 136+28, pointer(168))
        struct.pack_into('<I', data, 224, pointer(256))
        struct.pack_into('<I', data, 256, 0x7a2320)
        struct.pack_into('<I', data, 256+0x78, pointer(416))
        data[416:422] = b'walls\0'
        passes = material_pass_inputs(Pck(bytes(data)), 128)
        self.assertEqual([p['commands'][0]['command'] for p in passes], [0, 8])
        self.assertEqual(passes[1]['textures'][0]['name'], 'walls')
        struct.pack_into('<I', data, 168+28, pointer(136))
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            material_pass_inputs(Pck(bytes(data)), 128)

    def test_original_world_packet_fragment_and_scale_tamper(self):
        path = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/tire-alpha-native/garage-packet-fragments.json'
        receipt = json.loads(path.read_text())
        raw = base64.b64decode(receipt['packet_base64'], validate=True)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt['packet_sha256'])
        carrier = struct.pack('<4I', 0x6800000, 0x40, 1, len(raw)) + bytes(112) + raw
        planes = vif_planes(Pck(carrier), 128, len(raw))
        batches = decode_batches(planes)
        expected = receipt['expected']
        self.assertEqual(len(batches), expected['batch_count'])
        self.assertEqual(sum(len(b['positions']) for b in batches), expected['vertex_count'])
        batch = batches[0]
        self.assertEqual(batch['scale'], expected['scale'])
        for key in ('positions', 'normal_integers', 'uv_integers'):
            self.assertEqual([list(row) for row in batch[key]], expected[key])
        corrupted = copy.deepcopy(planes)
        words = list(corrupted[0]['values'][0]); words[0] = 0x3f800000
        corrupted[0]['values'][0] = tuple(words)
        with self.assertRaisesRegex(ValueError, 'position scale'):
            decode_batches(corrupted)

    def test_world_keeps_second_uv_and_unknown_normal_w(self):
        batch = decode_batches(fixture())[0]
        self.assertEqual(batch['positions'][1], (1, -1, 1/1024))
        self.assertEqual(batch['normals'][0], (1/128, -1, 127/128))
        self.assertEqual(batch['adc'], [1, 1, 1])
        self.assertEqual(batch['normal_w_raw'], [60, 60, 60])
        self.assertEqual(batch['uvs'][0], (0, 1))
        self.assertEqual(batch['lightmap_uvs'][0], (.5, -1))
        self.assertEqual(batch['colors'], [])

    def test_sky_scale_and_color_are_separate_from_world_profile(self):
        batch = decode_batches(fixture(False))[0]
        self.assertEqual(batch['positions'][1], (4, -4, 1/256))
        self.assertEqual(batch['colors'][0], (128/255, 0, 1))
        self.assertFalse(batch['world_layout'])
        with self.assertRaises(ValueError):
            car_batches(fixture(False))

    def test_packet_refusals(self):
        mutations = []
        changed = fixture(); changed[0]['values'][0] = (0x3f800000, 0, 0, 0x3f800000)
        mutations.append((changed, 'position scale'))
        changed = fixture(); changed[1]['cl'] = 2
        mutations.append((changed, 'destination skip'))
        changed = fixture(); changed.append(copy.deepcopy(changed[1]))
        mutations.append((changed, 'overlapping'))
        changed = fixture(); changed.pop()
        mutations.append((changed, 'complete vertex'))
        changed = fixture(); changed[1]['address'] += 1
        mutations.append((changed, 'exceeds vertex'))
        for changed, reason in mutations:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                decode_batches(changed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
