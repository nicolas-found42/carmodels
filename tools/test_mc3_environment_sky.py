"""Offline original-source sky fragment parsing and refusal controls."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zlib

from mc3_environment_sky import decode_sky

FIXTURE = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/environment/sky-fragments.json'


class SkyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text())
        cls.source = zlib.decompress(base64.b64decode(cls.fixture['fixture_zlib_base64']))
        assert len(cls.source) == cls.fixture['source_bytes']
        for span in cls.fixture['retained_ranges']:
            chunk = cls.source[span['offset']:span['offset'] + span['bytes']]
            assert hashlib.sha256(chunk).hexdigest() == span['sha256']
        cls.sky = decode_sky(cls.source)

    def test_native_selected_mesh_and_image_bytes(self):
        self.assertEqual(len(self.sky['primitives']), 5)
        self.assertEqual(sum(len(p['positions']) for p in self.sky['primitives']), 144)
        self.assertEqual(self.sky['sky_offset'], self.fixture['expected_sky']['sky_offset'])
        for index, texture in self.sky['textures'].items():
            rgba = base64.b64decode(texture['rgba_base64'])
            self.assertEqual(hashlib.sha256(rgba).hexdigest(), self.fixture['expected_rgba_sha256'][index])
            self.assertEqual(len(rgba), texture['width'] * texture['height'] * 4)
            self.assertLessEqual(max(rgba[3::4]), 128)  # Stored GS alpha, never display-scaled.
        self.assertTrue(all(c == [110, 110, 110, 255] or tuple(c) == (110, 110, 110, 255)
                            for p in self.sky['primitives'] for c in p['colors_native']))

    def reject_word(self, offset, value, reason):
        data = bytearray(self.source)
        struct.pack_into('<I', data, offset, value)
        with self.assertRaisesRegex(ValueError, reason):
            decode_sky(bytes(data))

    def test_root_and_selected_mesh_ownership_controls(self):
        self.reject_word(128, 0, 'city sky profile')
        self.reject_word(128 + 0x190, 0, 'PCK range')
        self.reject_word(self.sky['sky_offset'] + 0x30, 1, 'serialized sky object')
        # An in-range change to a draw's texture namespace must not select the other sky.
        mesh = self.sky['mesh_offset']
        base = struct.unpack_from('<I', self.source)[0]
        materials = struct.unpack_from('<I', self.source, mesh + 12)[0] - base + 128
        changed = bytearray(self.source)
        struct.pack_into('<H', changed, materials, 0)
        with self.assertRaisesRegex(ValueError, 'texture ownership changed'):
            decode_sky(bytes(changed))

    def test_texture_format_extent_and_padding_controls(self):
        texture = self.sky['textures']['5']['source']
        slot, start = texture['slot_offset'], texture['upload_offset']
        self.reject_word(slot, 0, 'sky image class')
        self.reject_word(slot + 0x10, 0, 'PSMT8')
        self.reject_word(slot + 12, 0, 'transfer extent')
        self.reject_word(start - 16, 0, 'upload padding')
        self.reject_word(start + 128 * 64 + 1024, 0, 'upload extent')

    def test_image_bytes_are_data_not_display_appearance(self):
        changed = bytearray(self.source)
        start = self.sky['textures']['5']['source']['upload_offset']
        changed[start] ^= 1
        result = decode_sky(bytes(changed))
        self.assertNotEqual(result['textures']['5']['rgba_sha256'], self.sky['textures']['5']['rgba_sha256'])
        for index in ['6', '7', '8', '9']:
            self.assertEqual(result['textures'][index], self.sky['textures'][index])
        self.assertEqual(result['primitives'], self.sky['primitives'])
        self.assertEqual(result['native_initial_state'], self.sky['native_initial_state'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
