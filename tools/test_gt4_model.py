"""GT4 CAR4/MDLS/Tex1 decoding: golden values from the committed extraction plus tamper controls."""
import hashlib
from pathlib import Path
import struct
import unittest

from gt4_model import (GSMemory, ModelSet, PSMT8, car4_slots, car_info, collision_bounds,
                       packet_geometry, vif_commands, walk_model)

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / 'games/gran-turismo-4/cars/acra0001/car/menu/acra0001'
MENU_SHA = 'a73725cfd7696daef93f21c297aba9921119ba6fa6ef55348fd8fc9362bd223c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RealModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = MENU.read_bytes()
        assert digest(cls.data) == MENU_SHA, 'committed acra0001 menu model changed'
        cls.slots = car4_slots(cls.data)
        cls.body = ModelSet(cls.data, cls.slots['body'])

    def test_car4_slots_info_and_collision(self):
        self.assertEqual({k: self.slots[k] for k in ('car_info', 'collision', 'body', 'wheel', 'tire_front', 'tire_rear')},
                         {'car_info': 0x40, 'collision': 0xA24, 'body': 0xD00, 'wheel': 0x76680,
                          'tire_front': 0x82640, 'tire_rear': 0x8A280})
        info = car_info(self.data, self.slots['car_info'])
        self.assertAlmostEqual(info['tire_pos_related'][0], 0.64602, places=4)
        self.assertAlmostEqual(info['tire_pos_related'][1], 0.6991, places=4)
        low, high = collision_bounds(self.data, self.slots['collision'])
        self.assertAlmostEqual(low[1], 0.0)
        self.assertAlmostEqual(high[2], 2.4915, places=3)

    def test_shapes_strips_and_render_walk(self):
        shape = self.body.shape(9)
        self.assertEqual((shape['vertices'], shape['triangles']), (1892, 1528))
        first = shape['packets'][0]
        self.assertAlmostEqual(first['positions'][0][2], -2.20035, places=4)
        self.assertEqual(len(first['uvs']), len(first['positions']))
        draws = walk_model(self.body, 0, 0)
        self.assertEqual(len(draws), 20)
        self.assertEqual(sorted({table for _, table, _, _ in draws}), [0, 5])
        self.assertTrue(any(not state['depth_mask'] for *_, state in draws))  # Glass pass.

    def test_textures_decode_to_pinned_pixels(self):
        pins = {0: (64, 64, '8585b066acb6a185'), 23: (128, 128, '94febbc894d57a7e'),
                45: (32, 16, 'f2de021e2ce12d84')}
        textures = self.body.texture_set(0, 0)
        self.assertEqual(len(textures.textures), 48)
        for index, (w, h, pin) in pins.items():
            image = textures.image(index)
            self.assertEqual((image['width'], image['height'], digest(image['rgba'])[:16]), (w, h, pin))
        self.assertEqual(textures.textures[46]['psm'], PSMT8)
        image = textures.image(46)
        self.assertEqual((image['width'], image['height'], digest(image['rgba'])[:16]), (256, 256, '7a3216f6671ae9d4'))
        image = self.body.texture_set(0, 5).image(0)
        self.assertEqual((image['width'], image['height'], digest(image['rgba'])[:16]), (64, 32, 'f150583f6b01e518'))
        self.assertEqual(self.body.texture_set(0, 1).textures, [])  # Size-0 placeholder set.


class ControlTests(unittest.TestCase):
    def test_vif_and_strip_controls(self):
        positions = struct.pack('<HBB', 0x8000, 4, 0x69) + struct.pack('<12h', *range(12))
        strips = struct.pack('<HBB', 0xC040, 2, 0x72) + bytes([1, 6, 0, 0])
        packet = positions + strips
        packet += bytes(-len(packet) % 16)
        geometry = packet_geometry(vif_commands(packet, 0, len(packet) // 16))
        self.assertEqual(len(geometry['triangles']), 2)
        self.assertAlmostEqual(geometry['positions'][1][0], 3 / 4096)
        bad = positions + struct.pack('<HBB', 0xC040, 2, 0x72) + bytes([1, 9, 0, 0])
        bad += bytes(-len(bad) % 16)
        with self.assertRaisesRegex(ValueError, 'strip lengths differ'):
            packet_geometry(vif_commands(bad, 0, len(bad) // 16))
        with self.assertRaisesRegex(ValueError, 'VIF unpack outside packet'):
            vif_commands(positions[:16], 0, 1)
        with self.assertRaisesRegex(ValueError, 'unsupported VIF command'):
            vif_commands(struct.pack('<HBB', 0, 0, 0x4A) + bytes(12), 0, 1)

    def test_model_set_controls(self):
        data = bytearray(MENU.read_bytes())
        with self.assertRaisesRegex(ValueError, 'not a CAR4'):
            car4_slots(b'XXXX' + bytes(data[4:]))
        body = 0xD00
        corrupt = bytearray(data)
        corrupt[body:body + 4] = b'MDLX'
        with self.assertRaisesRegex(ValueError, 'lacks MDLS'):
            car4_slots(bytes(corrupt))
        ms = ModelSet(bytes(data), body)
        with self.assertRaisesRegex(ValueError, 'shape index outside'):
            ms.shape(ms.shape_count)
        with self.assertRaisesRegex(ValueError, 'texture set outside'):
            ms.texture_set(ms.colour_count, 0)
        # An unknown render opcode at the start of model 0 must stop the walk.
        commands, _, _ = ms.model_commands(0)
        corrupt = bytearray(data)
        corrupt[commands] = 0xFE
        with self.assertRaisesRegex(ValueError, 'unsupported render command'):
            walk_model(ModelSet(bytes(corrupt), body), 0)
        # A shape whose header totals disagree with its strips is rejected.
        offset = struct.unpack_from('<I', data, body + ms.shapes_at + 4 * 9)[0]
        corrupt = bytearray(data)
        struct.pack_into('<H', corrupt, body + offset + 12, 1)
        with self.assertRaisesRegex(ValueError, 'strip totals differ'):
            ModelSet(bytes(corrupt), body).shape(9)

    def test_gs_transfer_bounds(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            GSMemory().write_ct32(0, 1, 8, 8, bytes(16))
        with self.assertRaisesRegex(ValueError, 'outside memory'):
            GSMemory().write_ct32(16383, 1, 64, 64, bytes(4 * 64 * 64))


if __name__ == '__main__':
    unittest.main()
