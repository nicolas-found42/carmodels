"""Literal XYZ2 high-depth controls and native carrier reconstruction."""

import copy
import hashlib
import json
import tempfile
import struct
import unittest
from pathlib import Path

from mc3_reference_runtime import write_gs_dump
from mc3_vehicle_depth_trace import (
    FIXTURE,
    READBACK_SOURCES,
    SOURCES,
    cases,
    draw_packets,
    packets,
)


class DepthTraceControls(unittest.TestCase):
    def test_original_carriers_and_full_outputs(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(proof["sources"], SOURCES)
        self.assertEqual(proof["depth_readback_sources"], READBACK_SOURCES)
        self.assertEqual(proof["commit"], "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3")
        self.assertEqual(len(proof["records"]), 13)
        self.assertEqual(
            {r["execution"]["runtime"]["binary_sha256"] for r in proof["records"]},
            {"9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a"},
        )
        for case, row in zip(cases(), proof["records"], strict=True):
            self.assertEqual(case, row["case"])
            primitive = (
                struct.unpack_from("<Q", draw_packets(case)[-2])[0] >> 47
            ) & 0x7FF
            self.assertEqual(bool(primitive & 16), "image" in case)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "native.gs"
                write_gs_dump(path, packets(case))
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    row["execution"]["dump_sha256"],
                )
            for field in ["frames", "depth_frames"]:
                self.assertEqual(len(row[field]), 3)
                self.assertEqual(len({v["sha256"] for v in row[field]}), 1)
                for frame in row[field]:
                    self.assertEqual(
                        frame["bytes"], frame["size"][0] * frame["size"][1] * 4
                    )

    def test_input_precision_boundaries_and_independence(self):
        rows = cases()
        self.assertEqual({r["ztst"] for r in rows}, {1, 2})
        self.assertEqual({r["primitive"] for r in rows}, {3, 4, 5})
        self.assertTrue(
            any(
                max(v["z"] for v in r["vertices"])
                > 0x80000000
                > min(v["z"] for v in r["vertices"])
                for r in rows
            )
        )
        proof = json.loads(FIXTURE.read_text())
        changed = copy.deepcopy(proof)
        changed["records"][0]["depth_frames"][0]["sha256"] = "0" * 64
        self.assertEqual(packets(changed["records"][0]["case"]), packets(rows[0]))
        textured = copy.deepcopy(next(row for row in rows if "image" in row))
        before = packets(textured)
        textured["image"]["data"][0] ^= 1
        self.assertNotEqual(packets(textured), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
