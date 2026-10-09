"""Independent native table, header transform, PSLZ and corrupt-input controls."""
import base64
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from gt_wheels import (LOAD, TABLE_RECEIPT, assemble_wheels, decode_pslz,
                       load_tables, sha)


def pslz_fixture():
    """Four packed bytes expand to32 zeros: one literal, one31-byte backref."""
    source = bytearray(2048 + 128)
    source[:8] = b'PS-X EXE'
    struct.pack_into('<III', source, 16, LOAD + 33, 0, LOAD)
    struct.pack_into('<I', source, 28, 128)
    source[2048:2052] = bytes([0, 28, 0, 2])
    struct.pack_into('<7I', source, 2053, 0x5a4c5350, LOAD + 31, 32,
                     LOAD + 3, LOAD + 32, 28, LOAD)
    return bytes(source)


class WheelTests(unittest.TestCase):
    def test_independent_native_tables_and_uv(self):
        tables = load_tables()
        self.assertEqual([t['quad_count'] for t in tables], [31, 23, 15, 11, 1])
        self.assertEqual(tables[0]['vertices'][:4],
                         ((4176, 0, -2048, 0x3805), (0, 0, -2048, 0x381a),
                          (2953, -2953, -2048, 0x2a0c), (3858, -1598, -2048, 0x3007)))
        self.assertEqual(tables[4]['vertices'],
                         ((4096, -4096, -2048, 0x2406), (4096, 4096, -2048, 0x4c06),
                          (-4096, 4096, -2048, 0x4c2e), (-4096, -4096, -2048, 0x242e)))
        positions = b''.join(struct.pack('<3h', *v[:3]) for t in tables for v in t['vertices'])
        uv = bytes(v[3] & 255 for t in tables for v in t['vertices']) + bytes(v[3] >> 8 for t in tables for v in t['vertices'])
        self.assertEqual(sha(positions), '582b901f330e4700454710db6c8366c07c6b82199b39aa6dc920d4df1f21a711')
        self.assertEqual(sha(uv), 'a77aa872b4a4aeb31a9d069b83f190204a7d9b88e15039c22aa9f2ce068cca6b')

    def test_receipt_tamper_controls(self):
        original = json.loads(TABLE_RECEIPT.read_text())
        controls = []
        wrong = copy.deepcopy(original)
        wrong['unpacked_sha256'] = '0' * 64
        controls.append((wrong, 'provenance'))
        wrong = copy.deepcopy(original)
        raw = bytearray(base64.b64decode(wrong['tables'][0]['base64']))
        raw[5] ^= 1
        wrong['tables'][0]['base64'] = base64.b64encode(raw).decode()
        controls.append((wrong, 'byte pin'))
        wrong = copy.deepcopy(original)
        wrong['tables'][0]['quad_count'] = 30
        controls.append((wrong, 'declarations'))
        wrong = copy.deepcopy(original)
        wrong['tables'].pop()
        controls.append((wrong, 'coverage'))
        wrong = copy.deepcopy(original)
        wrong['pointer_array_base64'] = base64.b64encode(bytes(20)).decode()
        controls.append((wrong, 'pointer array'))
        wrong = copy.deepcopy(original)
        wrong['tables'][0]['base64'] = '?'
        controls.append((wrong, 'base64'))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'tables.json'
            for changed, reason in controls:
                path.write_text(json.dumps(changed))
                with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                    load_tables(path)

    def test_neutral_side_basis_radius_width_and_fixed_rounding(self):
        car = {'wheels': [(-1000, 200, 3000, 0), (1000, 200, 3000, 0),
                          (-1100, 210, -3000, 0), (1100, 210, -3000, 0)],
               'wheel_dimensions': (512, 1024, 256, 512)}
        wheels = assemble_wheels(car, 4)
        self.assertEqual(len(wheels), 4)
        self.assertEqual(wheels[0]['positions'][0], (-1000, -824, 1976))
        self.assertEqual(wheels[1]['positions'][0], (1000, -824, 4024))
        self.assertEqual(wheels[2]['positions'][0], (-1100, -302, -3512))
        self.assertEqual(wheels[3]['positions'][0], (1100, -302, -2488))
        self.assertEqual(wheels[0]['uv'], [(6, 36), (6, 76), (46, 76), (46, 36)])
        self.assertEqual(wheels[0]['quads'], [(0, 1, 2, 3)])
        # Deliberately nonexact aspect preserves native integer ratio and z-shift.
        car['wheel_dimensions'] = (513, 1025, 0, 0)
        wheels = assemble_wheels(car, 4)
        self.assertEqual([w['wheel_index'] for w in wheels], [0, 1])
        self.assertEqual(wheels[0]['aspect_fixed'], 2049)
        self.assertEqual(wheels[0]['positions'][0][0], -1000 + 256 - 1025 * 1025 / 4096)
        self.assertEqual(wheels[1]['positions'][0][0], 1000 - 257 + 1025 * 1025 / 4096)
        for value, reason in [(-1, 'LOD'), (5, 'LOD'), (True, 'LOD')]:
            with self.assertRaisesRegex(ValueError, reason):
                assemble_wheels(car, value)
        car['wheel_dimensions'] = (40000, 1024, 0, 0)
        with self.assertRaisesRegex(ValueError, 'signed draw profile'):
            assemble_wheels(car)
        car['wheel_dimensions'] = (512, 1, 0, 0)
        with self.assertRaisesRegex(ValueError, 'aspect'):
            assemble_wheels(car)

    def test_backward_pslz_and_intended_failures(self):
        original = pslz_fixture()
        self.assertEqual(decode_pslz(original, sha(original)), bytes(32))
        with self.assertRaisesRegex(ValueError, 'source pin'):
            decode_pslz(original)
        with self.assertRaisesRegex(ValueError, 'packed extent'):
            decode_pslz(original[:-1], sha(original[:-1]))
        wrong = bytearray(original)
        struct.pack_into('<I', wrong, 2053 + 8, 16 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, 'loader fields'):
            decode_pslz(wrong, sha(wrong))
        wrong = bytearray(original)
        wrong[2048] = 127
        with self.assertRaisesRegex(ValueError, 'match outside decoded extent'):
            decode_pslz(wrong, sha(wrong))
        wrong = bytearray(original)
        wrong[2049] = 29
        with self.assertRaisesRegex(ValueError, 'match outside decoded extent'):
            decode_pslz(wrong, sha(wrong))


if __name__ == '__main__':
    unittest.main()
