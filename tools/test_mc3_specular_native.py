"""Native __specular__ copy contract and GS integer sampling controls."""

import array
import copy
import hashlib
import json
import unittest

from mc3_specular_native import (
    EVIDENCE,
    contract,
    copy_environment_rgba,
    prop_reflection_masks,
)


class SpecularCopyTests(unittest.TestCase):
    def test_contract_target_and_independent_gain(self):
        value = contract()
        self.assertEqual(value["native_modulate_rgba"], [127, 127, 127, 128])
        self.assertEqual(value["source_uv_origin"], 0)
        self.assertEqual(value["linear_half_texel"], -0.5)
        self.assertEqual(value["wrap"], "clamp-to-edge")
        self.assertIn("not reconstructed", value["input_scope"])

    def test_source_instruction_tamper(self):
        proof = json.loads(EVIDENCE.read_text())
        proof["selected_words"]["003b52a4"] = "24090010"
        with self.assertRaisesRegex(ValueError, "instructions changed"):
            contract(proof)

    def test_source_interval_cannot_be_omitted(self):
        proof = json.loads(EVIDENCE.read_text())
        del proof["intervals"]["blit"]
        with self.assertRaisesRegex(ValueError, "source pins changed"):
            contract(proof)

    def test_target_blend_tint_tamper(self):
        original = json.loads(EVIDENCE.read_text())
        for key, value in [
            ("target_size", [128, 128]),
            ("color_tint_native", [128] * 4),
            ("blend", "(Cs-0)*128/128+Cd"),
            ("clear_needed", True),
            ("destination_rectangle", [0, 0, 256, 256]),
            ("source_clamp", 0),
            ("target_clamp", 5),
        ]:
            with self.subTest(key=key):
                proof = copy.deepcopy(original)
                proof["derived_contract"][key] = value
                with self.assertRaises(ValueError):
                    contract(proof)

    def test_constant_native_byte_precision(self):
        source = bytes([255, 128, 1, 84]) * (256 * 256)
        self.assertEqual(
            copy_environment_rgba(source), bytes([253, 127, 0, 84]) * (64 * 64)
        )

    def test_integer_sample_origin_and_clamp(self):
        source = bytearray(256 * 256 * 4)
        for y in range(256):
            for x in range(256):
                i = (y * 256 + x) * 4
                source[i : i + 4] = bytes([x, y, 0, 128])
        result = copy_environment_rgba(source)
        self.assertEqual(result[:4], bytes([0, 0, 0, 128]))
        self.assertEqual(result[4:8], bytes([2, 0, 0, 128]))
        self.assertEqual(result[64 * 4 : 64 * 4 + 4], bytes([0, 2, 0, 128]))
        self.assertEqual(result[-4:], bytes([249, 249, 0, 128]))

    def test_horizontal_then_vertical_floor(self):
        source = bytearray(256 * 256 * 4)
        # At output1,1, contributors are source3/4 in each dimension.
        # Horizontal floors are0 and1, whose vertical floor is0.
        for (x, y), value in [((3, 3), 0), ((4, 3), 1), ((3, 4), 1), ((4, 4), 2)]:
            source[(y * 256 + x) * 4 + 3] = value
        result = copy_environment_rgba(source)
        self.assertEqual(result[(64 + 1) * 4 + 3], 0)

    def test_patterned_copy_matches_independent_javascript(self):
        source = bytes(
            (i * 17 + (i // 4) * 29 + (i // 1024) * 31) & 255
            for i in range(256 * 256 * 4)
        )
        self.assertEqual(
            hashlib.sha256(copy_environment_rgba(source)).hexdigest(),
            "277f27013b4445e695f3f920effd313bb4727bdf1116c9ae22e7740cea9f5168",
        )

    def test_not_area_box_resize(self):
        source = bytearray(256 * 256 * 4)
        # A box resize would retain this texel; the native sparse bilinear copy does not.
        source[(5 * 256 + 5) * 4 : (5 * 256 + 5) * 4 + 4] = bytes([255] * 4)
        self.assertFalse(any(copy_environment_rgba(source)))

    def test_rejects_other_image_layouts(self):
        for source in [
            None,
            [0] * (256 * 256 * 4),
            b"",
            bytes(64 * 64 * 4),
            memoryview(array.array("H", [0] * (256 * 256 * 4))),
        ]:
            with self.subTest(kind=type(source)):
                with self.assertRaisesRegex(ValueError, "native 256x256 RGBA8"):
                    copy_environment_rgba(source)

    def test_native_prop_capture_masks(self):
        self.assertEqual(prop_reflection_masks(0, 0x80), [0x20])
        self.assertEqual(prop_reflection_masks(0x10000, 0x07A30080), [2])
        self.assertEqual(prop_reflection_masks(0x100, 0x80), [])
        self.assertEqual(prop_reflection_masks(0, 0x40), [])
        self.assertEqual(prop_reflection_masks(0x1000000, 0x40), [0x20])

    def test_rejects_invalid_prop_flags(self):
        for definition, instance in [
            (-1, 0),
            (0, -1),
            (1 << 32, 0),
            (0, 1 << 32),
            ("0", 0),
        ]:
            with self.assertRaisesRegex(ValueError, "native prop"):
                prop_reflection_masks(definition, instance)


if __name__ == "__main__":
    unittest.main(verbosity=2)
