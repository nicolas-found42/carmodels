"""Source pins and independently executed original model-dispatch controls."""

import copy
import hashlib
import json
import unittest

import mc3_vehicle_dispatch as dispatch


class VehicleDispatchTests(unittest.TestCase):
    def test_receipt_and_observer_are_bound(self):
        proof = dispatch.source_contract()
        self.assertEqual(
            dispatch.sha(dispatch.observer()), proof["observer"]["code_sha256"]
        )
        altered = copy.deepcopy(proof)
        altered["observer"]["stride_bytes"] += 4
        with self.assertRaisesRegex(ValueError, "receipt differs"):
            dispatch.source_contract(altered)

    def test_actual_native_selection_controls(self):
        proof = dispatch.source_contract()
        self.assertEqual(len(proof["sources"]), 3)
        self.assertEqual(len(proof["cases"]), 12)
        for case in proof["cases"]:
            source = proof["sources"][case["source"]]
            binding = source["binding"] | {
                key: case[key] for key in ("lod", "bucket", "mask_words")
            }
            binding["palette_words"] = dispatch.control_palette(source["joint_count"])
            rows = dispatch.expected_records(binding)
            digest = hashlib.sha256(
                json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            self.assertEqual(digest, case["expected"]["records_sha256"], case["name"])
            self.assertEqual(len(rows), case["expected"]["record_count"], case["name"])
            if case["mask_words"] is not None and not any(case["mask_words"]):
                self.assertEqual(rows, [])
            else:
                self.assertTrue(rows)

    def test_mask_bucket_and_frame_tamper_controls(self):
        proof = dispatch.source_contract()
        case = proof["cases"][0]
        source = proof["sources"][case["source"]]
        binding = copy.deepcopy(source["binding"]) | {
            key: case[key] for key in ("lod", "bucket", "mask_words")
        }
        binding["palette_words"] = dispatch.control_palette(source["joint_count"])
        rows = dispatch.expected_records(binding)
        altered = copy.deepcopy(binding)
        altered["bucket"] = 31
        self.assertNotEqual(dispatch.expected_records(altered), rows)
        altered = copy.deepcopy(binding)
        altered["mask_words"] = [0] * ((source["joint_count"] + 31) // 32)
        self.assertNotEqual(dispatch.expected_records(altered), rows)
        altered = copy.deepcopy(binding)
        altered["palette_words"][9] ^= 1
        self.assertNotEqual(dispatch.expected_records(altered), rows)

    def test_invalid_carrier_refuses_before_native_execution(self):
        with self.assertRaisesRegex(ValueError, "LOD or bucket"):
            dispatch.native_context(
                "missing.pck", lod=3, bucket=0, mask_words=None, palette_words=[]
            )
        with self.assertRaisesRegex(ValueError, "output extent"):
            dispatch.output(bytes(32))
        with self.assertRaisesRegex(ValueError, "output bounds"):
            dispatch.output(bytes(0x2000000))
        with self.assertRaisesRegex(ValueError, "executable differs"):
            dispatch.from_executable(bytes(128))


if __name__ == "__main__":
    unittest.main(verbosity=2)
