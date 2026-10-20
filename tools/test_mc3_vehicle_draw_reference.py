"""Whole-program source binding and VIF expansion refusal controls."""

import copy
from pathlib import Path
import struct
import tempfile
import unittest

import mc3_vehicle_draw_reference as draw


class VehicleDrawTests(unittest.TestCase):
    def test_bounded_original_output_contract(self):
        proof = draw.source_contract()
        self.assertEqual(len(proof["probes"]), 13)
        self.assertEqual({p["material_class"] for p in proof["probes"]}, {4})
        for probe in proof["probes"]:
            self.assertEqual(len(probe["calls"]), 3)
            self.assertEqual(probe["calls"][0]["pc"], 10)
            self.assertTrue(all(c["pc"] == 6 for c in probe["calls"][1:]))
            self.assertGreater(probe["outputs"]["gif-chunks.bin"]["bytes"], 0)

    def test_receipt_changes_rejected(self):
        for field in ("job_sha256", "packet_sha256", "source_pass_program_index"):
            proof = copy.deepcopy(draw.source_contract())
            proof["probes"][0][field] = 0
            with self.assertRaisesRegex(ValueError, "receipt changed"):
                draw.source_contract(receipt=proof)

    def test_signed_normal_and_v3_following_lane_expansion(self):
        header = struct.pack("<I8I", 0x6C024098, 0x38800000, 0, 0, 0, 2, 0, 0, 2)
        normal = struct.pack("<I6b2x", 0x6A02009A, -127, 3, -4, 5, -6, 7)
        origin, patches = draw.batch_patches(header + normal, 0)
        self.assertEqual(origin, 0x98)
        values = struct.unpack("<8i", patches[1][1])
        self.assertEqual(values, (-127, 3, -4, 5, 5, -6, 7, 0))

    def test_missing_header_and_vif_state_rejected(self):
        with self.assertRaisesRegex(ValueError, "source batch missing"):
            draw.batch_patches(bytes(16), 1)
        with self.assertRaisesRegex(ValueError, "header changed"):
            draw.batch_patches(struct.pack("<I2I", 0x60020098, 1, 2), 0)
        header = struct.pack("<I8I", 0x6C024098, *([0] * 8))
        with self.assertRaisesRegex(ValueError, "VIF state"):
            draw.batch_patches(struct.pack("<I", 0x01000201) + header, 4)

    def test_unexecuted_reference_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                draw.verify_reference_output(
                    Path(directory), draw.source_contract()["probes"][0]
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
