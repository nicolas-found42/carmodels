import hashlib
import json
import unittest

import mc3_vehicle_sampler as sampler


class VehicleSamplerTests(unittest.TestCase):
    def test_source_images_and_original_controls(self):
        proof = json.loads(sampler.FIXTURE.read_text())
        self.assertEqual(proof["reference_commit"], sampler.COMMIT)
        self.assertEqual(proof["sources"], sampler.SOURCES)
        self.assertEqual([row["case"] for row in proof["records"]], sampler.controls())
        self.assertEqual(len(proof["records"]), 9)
        images = sampler.images()
        self.assertEqual(
            (images["window"]["width"], images["window"]["height"]), (8, 8)
        )
        self.assertEqual(
            bytes(images["window"]["data"]), bytes([255, 255, 255, 128]) * 64
        )
        self.assertGreater(
            len(
                set(
                    tuple(images["carbon"]["data"][i : i + 4])
                    for i in range(0, len(images["carbon"]["data"]), 4)
                )
            ),
            1,
        )
        for image in images.values():
            self.assertEqual(
                hashlib.sha256(bytes(image["data"])).hexdigest(), image["rgba_sha256"]
            )
        for row in proof["records"]:
            self.assertEqual(row["execution"]["status"], "executed")
            for field in ["frames", "depth_frames"]:
                self.assertEqual(len(row[field]), 3)
                self.assertEqual(len({v["sha256"] for v in row[field]}), 1)

    def test_input_profiles_are_explicit(self):
        controls = sampler.controls()
        self.assertEqual(
            [int(v["tex1"], 16) >> 6 & 7 for v in controls[:6]], [4, 4, 0, 1, 4, 7]
        )
        self.assertTrue(all(int(v["tex1"], 16) >> 2 & 7 == 0 for v in controls))
        with self.assertRaisesRegex(ValueError, "source changed"):
            sampler.verify_sources({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
