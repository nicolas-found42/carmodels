"""Native GS blend namespace and alpha-only pre-sky control cases."""

import copy
import json
import unittest

from mc3_environment_gs import (EVIDENCE, blend_rgb, contract, material_alpha_register,
                                prefill_garage_alpha)


class EnvironmentGSTests(unittest.TestCase):
    def test_native_namespace_and_literal(self):
        self.assertEqual([material_alpha_register(i) for i in range(7)],
                         [0x44, 0x8000000068, 0x8000000062, 0x81,
                          0x58, 0x80000000a8, 0x54])
        self.assertEqual(material_alpha_register(7), 0)
        self.assertEqual(material_alpha_register(0x1000a), 0x0a)
        self.assertEqual(material_alpha_register(0x18068), 0x8000000068)

    def test_material_lightmap_subtract_is_not_ordinary_modulation(self):
        # With native sourcealpha128, mode3 is destination minus source.
        self.assertEqual(blend_rgb((20, 40, 100), (100, 100, 90), 128, 48, 0x81), (80, 60, 0))
        self.assertEqual(blend_rgb((20, 40, 100), (100, 100, 90), 64, 48, 0x81), (40, 30, 0))

    def test_signed_difference_shift_precedes_destination_add(self):
        self.assertEqual(blend_rgb((0, 0, 0), (1, 3, 5), 64, 128, 0x44), (0, 1, 2))

    def test_additive_and_reverse_subtract_clamp(self):
        self.assertEqual(blend_rgb((200, 10, 40), (100, 20, 30), 0, 0, 0x8000000068),
                         (255, 30, 70))
        self.assertEqual(blend_rgb((200, 10, 40), (100, 20, 30), 0, 0, 0x8000000062),
                         (0, 10, 0))

    def test_destination_alpha_native128_unity(self):
        self.assertEqual(blend_rgb((128, 64, 32), (10, 20, 30), 128, 48, 0x58), (58, 44, 42))

    def test_literal_floor_first_pass_copy(self):
        self.assertEqual(blend_rgb((75, 69, 65), (255, 0, 20), 128, 128,
                                  material_alpha_register(0x1000a)), (75, 69, 65))

    def test_prefill_preserves_every_rgb_and_replaces_alpha(self):
        image = bytes([17, 123, 245, 26]) * (256 * 256)
        result = prefill_garage_alpha(image)
        self.assertEqual(result, bytes([17, 123, 245, 48]) * (256 * 256))
        self.assertEqual(image[3], 26)
        self.assertEqual(contract()['prefill_write_mask'], 8)

    def test_prefill_native_destination_alpha_test(self):
        image = bytes([17, 123, 245, 128, 18, 124, 246, 127]) * (256 * 128)
        result = prefill_garage_alpha(image)
        self.assertEqual(result[:8], bytes([17, 123, 245, 128, 18, 124, 246, 48]))
        self.assertEqual(contract()['prefill_destination_alpha_msb'], 0)

    def test_garage_native_scalar_and_alpha_rounding(self):
        import struct
        scalar = struct.unpack('<f', bytes.fromhex('ee7cbf3e'))[0]
        native = (round(struct.unpack('<f', struct.pack('<f', scalar * 255))[0]) + 1) >> 1
        self.assertEqual(native, contract()['prefill_native_alpha'])

    def test_evidence_mutation_fails_closed(self):
        original = json.loads(EVIDENCE.read_text())
        mutations = [('material_alpha_registers', []), ('garage', {}), ('selected_words', {})]
        for key, value in mutations:
            with self.subTest(key=key):
                proof = copy.deepcopy(original)
                proof[key] = value
                with self.assertRaisesRegex(ValueError, 'receipt changed'):
                    contract(proof)

    def test_bad_inputs(self):
        for value in (-1, 1 << 32, True, '3'):
            with self.assertRaises(ValueError):
                material_alpha_register(value)
        with self.assertRaises(ValueError):
            prefill_garage_alpha(bytes(64 * 64 * 4))
        with self.assertRaises(ValueError):
            blend_rgb((0, 0, 0), (0, 0, 0), 128, 128, 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
