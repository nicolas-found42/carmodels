import copy
import json
import unittest

import mc3_vehicle_raster as raster


class VehicleRasterTests(unittest.TestCase):
    def test_native_fixture_input_and_output_bindings(self):
        proof = json.loads(raster.FIXTURE.read_text())
        cases = raster.cases()
        self.assertEqual(
            [row["case"] for row in proof["records"]],
            [c for c in cases for _ in range(2)],
        )
        self.assertEqual(
            [row["mode"] for row in proof["records"]], ["color", "depth"] * len(cases)
        )
        self.assertEqual(
            raster.verify_reference(proof, copy.deepcopy(proof))["contexts"], 10
        )
        changed = copy.deepcopy(proof)
        changed["records"][0]["frames"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "framebuffer bytes differ"):
            raster.verify_reference(changed, proof)

    def test_expected_colors_never_feed_gif_builder(self):
        case = raster.cases()[0]
        before = b"".join(raster.packets(case))
        case["expected_rgba"] = [255] * 4
        self.assertEqual(before, b"".join(raster.packets(case)))
        case["vertices"][0]["rgba"][0] ^= 1
        self.assertNotEqual(before, b"".join(raster.packets(case)))
        self.assertNotEqual(
            b"".join(raster.packets(case, False)), b"".join(raster.packets(case, True))
        )

    def test_explicit_flat_projective_scissor_controls(self):
        flat, gouraud, textured, projective, clipped = raster.cases()
        self.assertFalse(flat["gouraud"])
        self.assertNotEqual(
            flat["vertices"][2]["xy"][1], max(v["xy"][1] for v in flat["vertices"])
        )
        self.assertTrue(gouraud["gouraud"])
        self.assertTrue(textured["textured"])
        self.assertEqual(len({v["stq"][2] for v in projective["vertices"]}), 3)
        self.assertEqual(clipped["scissor"], [31, 29, 201, 219])
        self.assertTrue(all(len(p) % 16 == 0 for p in raster.packets(projective)))


if __name__ == "__main__":
    unittest.main()
