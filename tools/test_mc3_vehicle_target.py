"""Bounded original SDK target/default-state receipt and negative controls."""

import copy
import unittest

import mc3_vehicle_target as target


class TargetTests(unittest.TestCase):
    def test_source_profile_and_sdk_packet(self):
        proof = target.source_contract()
        profile = proof["profile"]
        self.assertEqual(
            [profile["display_width"], profile["display_height"]], [512, 512]
        )
        self.assertEqual(
            [profile["target_width"], profile["target_height"]], [256, 256]
        )
        words = {address: value for value, address in profile["source_sdk_ad_words"]}
        self.assertEqual(words[0x18], 0x700000007000)
        self.assertEqual(words[0x46], 1)
        self.assertEqual(words[0x1A], 1)
        self.assertEqual(profile["depth_psm"], "PSMZ16S")
        altered = copy.deepcopy(proof)
        altered["profile"]["display_width"] = 256
        with self.assertRaisesRegex(ValueError, "receipt differs"):
            target.source_contract(receipt=altered)

    def test_three_original_emission_controls_and_measured_crop(self):
        proof = target.source_contract()
        cases = {row["name"]: row for row in proof["cases"]}
        self.assertEqual(set(cases), {"positive", "clipped", "disabled"})
        self.assertEqual(
            [cases[name]["coupled"]["gif_bytes"] for name in cases], [4256, 1040, 1008]
        )
        self.assertEqual(
            len({tuple(row["initial_gif_sha256"]) for row in cases.values()}), 1
        )
        gs = proof["positive_gs"]
        self.assertEqual([frame["size"] for frame in gs["frames"]], [[177, 135]] * 3)
        self.assertEqual(
            {frame["sha256"] for frame in gs["frames"]},
            {"b19367d232f9c88551aea3714d8febf7910dacae7e8c2805ecbd6d4b12d51815"},
        )
        self.assertEqual(
            {frame["sha256"] for frame in gs["depth_frames"]},
            {"987b708492ee68525a057113e1fa6cdd97ff36a5f98b6251780c28ac441bed8f"},
        )

    def test_invalid_executable_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, "executable differs"):
            target.source_contract(bytes(128))


if __name__ == "__main__":
    unittest.main(verbosity=2)
