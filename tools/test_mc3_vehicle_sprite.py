import copy
import base64
import json
import unittest

import mc3_vehicle_sprite as sprite


class SpriteTests(unittest.TestCase):
    def test_original_input_and_output_contexts(self):
        proof = json.loads(sprite.FIXTURE.read_text())
        self.assertEqual(
            proof["reference_commit"], "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3"
        )
        self.assertEqual(proof["sources"], sprite.SOURCES)
        self.assertEqual([row["case"] for row in proof["records"]], sprite.cases())
        self.assertEqual(len(proof["records"]), 8)
        for row in proof["records"]:
            packets = sprite.packets(row["case"])
            self.assertEqual(
                [base64.b64decode(v) for v in row["draw_chunks"]],
                [packets[0], *packets[5:]],
            )
            self.assertEqual(
                row["execution"]["runtime"]["binary_sha256"],
                "9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a",
            )
            for field in ["frames", "depth_frames"]:
                self.assertEqual(len(row[field]), 3)
                self.assertEqual(len({frame["sha256"] for frame in row[field]}), 1)

    def test_expected_pixels_never_enter_native_packets(self):
        case = sprite.cases()[1]
        before = sprite.packets(case)
        changed = copy.deepcopy(case)
        changed["expected_rgba"] = [255] * 4
        self.assertEqual(before, sprite.packets(changed))
        changed["vertices"][1]["rgba"][0] ^= 1
        self.assertNotEqual(before, sprite.packets(changed))
        changed = copy.deepcopy(case)
        changed["vertices"][1]["uv"][0] += 1
        self.assertNotEqual(before, sprite.packets(changed))
        with self.assertRaisesRegex(ValueError, "source changed"):
            sprite.verify_sources({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
