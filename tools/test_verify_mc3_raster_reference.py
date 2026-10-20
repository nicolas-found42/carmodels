"""Independent-reference carrier guards and completion comparison controls."""

import base64
import copy
import json
import contextlib
import io
import hashlib
from pathlib import Path
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch

from mc3_reference_runtime import RuntimeUnavailable
from verify_mc3_raster_reference import (
    capture_packets,
    compare_frames,
    main,
    tex0,
    texture_bytes,
)
from mc3_environment import OUTPUT

ROOT = Path(__file__).resolve().parents[1]


def image(width, height):
    return {
        "width": width,
        "height": height,
        "rgba_base64": base64.b64encode(
            bytes([11, 22, 33, 128]) * width * height
        ).decode(),
    }


def fixture():
    return {
        "images": {
            "floorBase": image(128, 128),
            "floorLightmap": image(256, 256),
            "panorama": image(512, 256),
        },
        "native_gs": {
            "schema": 1,
            "context": {
                "depth_format": "PSMZ16S",
                "xy_offset": [27648, 29184],
                "scissor": [0, 0, 256, 256],
            },
            "passes": [
                {
                    "material_index": 8,
                    "pass_index": index,
                    "gif_chunks": [base64.b64encode(bytes(16)).decode()],
                }
                for index in [0] * 4 + [1] * 4
            ],
        },
    }


class ReferenceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_shared_prediction_cli_matches_independently_executed_golden(self):
        proof = json.loads(
            (
                ROOT
                / "research/evidence/midnight-club-3-remix/previews/environment/raster-reference.json"
            ).read_text()
        )
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(
                [
                    "node",
                    str(ROOT / "tools/mc3_raster_reference.mjs"),
                    str(OUTPUT),
                    temp,
                ],
                capture_output=True,
                check=True,
            )
            for row in proof["comparisons"]:
                raw = (Path(temp) / (row["name"] + ".rgba")).read_bytes()
                self.assertEqual(len(raw), row["size"][0] * row["size"][1] * 4)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["rgba_sha256"])

    def test_unavailable_runtime_skips_but_corrupt_runtime_fails(self):
        for error, code in [
            (RuntimeUnavailable("not provisioned"), 1),
            (ValueError("wrong binary pin"), 2),
        ]:
            with (
                patch("sys.argv", ["verify", "--available"]),
                patch("verify_mc3_raster_reference.identity", side_effect=error),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(main(), code)
                self.assertIn(str(error), output.getvalue())

    def test_native_stream_has_one_state_change_per_pass(self):
        pack = fixture()
        packets = capture_packets(pack)
        # Two uploads, clear, two material flush groups, eight literal batches,
        # alpha prefill, and FINISH. Rewriting state per batch could change the
        # GS draw-wide Q optimization and invalidate the comparison.
        self.assertEqual(len(packets), 17)
        self.assertEqual(sum(value == bytes(16) for value in packets), 8)
        self.assertGreater(
            len(capture_packets(pack, panorama_offset16=7, copy_specular=True)),
            len(packets),
        )

    def test_reject_incomplete_or_unbounded_native_context(self):
        for mutate, message in [
            (
                lambda p: p["native_gs"]["context"].__setitem__(
                    "depth_format", "PSMZ32"
                ),
                "context",
            ),
            (
                lambda p: p["native_gs"]["context"].__setitem__(
                    "xy_offset", [65535, 0]
                ),
                "XYOFFSET",
            ),
            (
                lambda p: p["native_gs"]["context"].__setitem__(
                    "scissor", [0, 0, 257, 256]
                ),
                "scissor",
            ),
            (lambda p: p["native_gs"]["passes"].pop(), "complete original passes"),
            (
                lambda p: p["native_gs"]["passes"][0].__setitem__("material_index", 9),
                "unsupported material",
            ),
            (
                lambda p: p["native_gs"]["passes"][0].__setitem__(
                    "gif_chunks", ["AA=="]
                ),
                "chunk extent",
            ),
        ]:
            pack = fixture()
            mutate(pack)
            with self.assertRaisesRegex(ValueError, message):
                capture_packets(pack)
        pack = fixture()
        pack["native_gs"]["passes"].reverse()
        with self.assertRaisesRegex(ValueError, "pass order"):
            capture_packets(pack)
        with self.assertRaisesRegex(ValueError, "panorama offset"):
            capture_packets(fixture(), panorama_offset16=8192)
        with self.assertRaisesRegex(ValueError, "power-of-two"):
            tex0(0, 3, 256)
        broken = image(2, 2)
        broken["rgba_base64"] = ""
        with self.assertRaisesRegex(ValueError, "texture length"):
            texture_bytes(broken)

    def test_compare_requires_three_complete_byte_equal_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            rows = []
            for index in range(3):
                name = f"00001_f{index:05}_rt1_00000_C_32.rgba"
                (directory / name).write_bytes(bytes(16))
                rows.append({"file": name, "size": [2, 2]})
            receipt = {"frames": rows}
            self.assertEqual(
                len(compare_frames(receipt, directory, bytes(16), (2, 2))), 3
            )
            with self.assertRaisesRegex(ValueError, "incomplete"):
                compare_frames({"frames": rows[:2]}, directory, bytes(16), (2, 2))
            with self.assertRaisesRegex(ValueError, "extent mismatch"):
                compare_frames(receipt, directory, bytes(12), (2, 2))
            (directory / rows[1]["file"]).write_bytes(bytes([1]) + bytes(15))
            with self.assertRaisesRegex(ValueError, "differs in 1 RGBA bytes"):
                compare_frames(receipt, directory, bytes(16), (2, 2))
            # Recomputing or ignoring a reported hash cannot bypass byte comparison.
            changed = copy.deepcopy(receipt)
            changed["frames"][1]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "differs in 1 RGBA bytes"):
                compare_frames(
                    json.loads(json.dumps(changed)), directory, bytes(16), (2, 2)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
