"""Native factory source closure, caller-context and projection corruption controls."""

import copy
import hashlib
import json
import unittest

from mc3_vehicle_paint_factory import (
    EXECUTABLE_SHA,
    factory_job,
    initializer_job,
    load_receipt,
    pack_for_context,
    parse_context,
    project_ram,
    verify_source,
    wrapper,
)


class FactoryTests(unittest.TestCase):
    def test_pinned_native_calls_and_initializer(self):
        proof = load_receipt()
        self.assertEqual(proof["executable_sha256"], EXECUTABLE_SHA)
        table = proof["table_initializer"]
        self.assertEqual(
            hashlib.sha256(bytes.fromhex(table["data_hex"])).hexdigest(),
            table["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(bytes.fromhex(table["source_hex"])).hexdigest(),
            table["source_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(initializer_job()).hexdigest(), table["job_sha256"]
        )
        for control, context in proof["contexts"].items():
            raw = factory_job(context, control)
            self.assertEqual(parse_context(raw, control), context)
            self.assertEqual(
                wrapper(control), bytes.fromhex(context["chunks"][-1]["data_hex"])
            )
            self.assertEqual(
                [c["data_hex"] for c in context["chunks"] if c["address"] == 0x6BE8E0],
                [table["data_hex"]],
            )
            pack = pack_for_context(proof, control)
            self.assertLess(sum(len(c["data_hex"]) // 2 for c in pack["chunks"]), 32768)
            self.assertLess(len(pack["code"]) * 4, 32768)
            self.assertGreater(len(pack["regions"]), 100)
        for section in ["source_code", "source_data"]:
            for chunk in proof[section]:
                self.assertEqual(
                    hashlib.sha256(bytes.fromhex(chunk["data_hex"])).hexdigest(),
                    chunk["sha256"],
                )

    def test_unchanged_writes_and_zero_source_bytes_survive_projection(self):
        native = bytearray(0x2000000)
        native[100:108] = bytes([7, 7, 0, 7, 7, 7, 7, 7])
        # Byte101 models a write equal to the original value, byte102 is an
        # explicitly retained zero initial field. Final-value diff cannot infer either.
        actual = project_ram(
            native, [[100, 8, 0]], [[102, 1]], [[101, 1]], dict(chunks=[])
        )
        self.assertEqual(actual[100:108], bytes([0, 7, 0, 0, 0, 0, 0, 0]))
        with self.assertRaisesRegex(ValueError, "extent differs"):
            project_ram(b"", [], [], [], dict(chunks=[]))

    def test_corrupt_contexts_receipts_and_source_fail_closed(self):
        proof = load_receipt()
        context = copy.deepcopy(proof["contexts"]["positive"])
        context["chunks"][0]["data_hex"] = "01" + context["chunks"][0]["data_hex"][2:]
        with self.assertRaisesRegex(ValueError, "initialized context changed"):
            factory_job(context, "positive")
        with self.assertRaisesRegex(ValueError, "source receipt changed"):
            load_receipt(json.dumps(proof).encode())
        with self.assertRaisesRegex(ValueError, "executable differs"):
            verify_source(b"not original MC3", proof)
        with self.assertRaisesRegex(ValueError, "unknown factory context"):
            pack_for_context(proof, "invented")
        with self.assertRaisesRegex(ValueError, "unsupported factory context"):
            wrapper("invented")


if __name__ == "__main__":
    unittest.main(verbosity=2)
