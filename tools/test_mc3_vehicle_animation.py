"""Native wheel/morph source, packet and input preservation controls."""

import copy
import struct
import unittest
from unittest.mock import patch

import mc3_vehicle_animation as animation
from mc3_reference_runtime import validate_job


class AnimationTests(unittest.TestCase):
    def test_source_lookup_and_output_tampering_rejected(self):
        proof = animation.source_contract()
        for mutate in [
            lambda p: p["lookup_words"][32].__setitem__(0, 0x3F800000),
            lambda p: p["numerical_probes"][1]["output"]["palette_words"][
                0
            ].__setitem__(3, 0),
            lambda p: p["source_intervals"]["roll_update"].__setitem__("end", 0x226DF0),
        ]:
            changed = copy.deepcopy(proof)
            mutate(changed)
            with self.assertRaisesRegex(ValueError, "receipt changed"):
                animation.source_contract(receipt=changed)
        with self.assertRaisesRegex(ValueError, "executable changed"):
            animation.source_contract(bytes(512))

    def test_lookup_preserves_native_nonunit_and_signed_zero_values(self):
        proof = animation.source_contract()
        self.assertEqual(len(proof["lookup_words"]), 128)
        self.assertEqual(proof["lookup_words"][32], [0x3F800001, 0x80000000])
        self.assertEqual(
            animation.wheel_basis_words(0),
            [0x3F800000, 0, 0, 0, 0x3F800000, 0x80000000, 0, 0, 0x3F800000, 0, 0, 0],
        )
        rolled = animation.wheel_basis_words(32, suspension_word=0x80000000)
        self.assertEqual(rolled[5], 0xBF800001)
        self.assertEqual(rolled[7], 0x3F800001)
        self.assertEqual(rolled[10], 0x80000000)
        steered = animation.wheel_basis_words(32, steering=True)
        self.assertEqual(steered[:3], [0x80000000, 0, 0xBF800001])
        self.assertEqual(steered[6:9], [0x3F800001, 0, 0x80000000])
        for index in [-1, 128, 0.5, True]:
            with self.assertRaisesRegex(ValueError, "lookup index"):
                animation.wheel_basis_words(index)

    def test_original_helper_jobs_keep_raw_frames_and_explicit_actor_state(self):
        proof = animation.source_contract()
        with patch.object(animation, "source_contract", return_value=proof):
            for job in [
                animation.lookup_job(b""),
                animation.rotation_job(b"", 16, 8),
                animation.frame_job(b"", [0x80000000] * 12, [0x3F800001] * 12),
                animation.morph_palette_job(b"", 128),
            ]:
                validate_job(job, "ee")
            frame = animation.frame_job(b"", [0x80000000] * 12, [0x3F800001] * 12)
            self.assertIn(struct.pack("<12I", *([0x80000000] * 12)), frame)
            self.assertIn(struct.pack("<12I", *([0x3F800001] * 12)), frame)
            morph = animation.morph_palette_job(b"", 128)
            self.assertIn(bytes(0x157) + bytes([128]), morph)
            for state in [-1, 256, 1.5, True]:
                with self.assertRaisesRegex(ValueError, "morph state byte"):
                    animation.morph_palette_job(b"", state)
            with self.assertRaisesRegex(ValueError, "compact frame"):
                animation.frame_job(b"", [0] * 11, [0] * 12)

    def test_morph_packets_have_original_headers_and_special_selector(self):
        proof = animation.source_contract()
        cases = {
            p["state_byte"]: p["output"]
            for p in proof["numerical_probes"]
            if p["kind"] == "morph"
        }
        self.assertEqual(cases[0]["palette_words"], [[0] * 4 for _ in range(16)])
        self.assertEqual(cases[128]["palette_words"][1][3], 0x3B808081)
        self.assertEqual(
            cases[128]["palette_words"][0][3], cases[255]["palette_words"][0][3]
        )
        self.assertEqual(cases[255]["palette_words"][1][3], 0)
        ram = bytearray(32 * 1024 * 1024)
        struct.pack_into(
            "<4I", ram, animation.LEFT, 0x10000001, 0, 0x11000000, 0x6C014034
        )
        struct.pack_into("<4I", ram, animation.LEFT + 16, *cases[128]["vu52_words"])
        struct.pack_into(
            "<4I", ram, animation.LEFT + 32, 0x10000010, 0, 0x11000000, 0x6C104318
        )
        for index, vector in enumerate(cases[128]["palette_words"]):
            struct.pack_into("<4I", ram, animation.LEFT + 48 + index * 16, *vector)
        self.assertEqual(animation.read_morph_palette(bytes(ram)), cases[128])
        ram[animation.LEFT + 12] ^= 1
        with self.assertRaisesRegex(ValueError, "headers changed"):
            animation.read_morph_palette(bytes(ram))
        with self.assertRaisesRegex(ValueError, "RAM output"):
            animation.read_morph_palette(bytes(48))


if __name__ == "__main__":
    unittest.main(verbosity=2)
