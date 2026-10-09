#!/usr/bin/env python3
"""Check illustration sampling against decoded reference pixels and manifest pins."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from showcase_metadata import CARS, body_paint, load_source_metadata, sample_icon_rgba
from recover_car_ptg import decode_file


class ShowcaseTests(unittest.TestCase):
    def test_pixel_selection(self):
        self.assertEqual(sample_icon_rgba(bytes([255, 0, 0, 0, 32, 128, 208, 128]))["rgb"], [40, 136, 216])
        self.assertEqual(sample_icon_rgba(bytes([240, 240, 240, 128]))["selection"], "neutral")
        self.assertIsNone(sample_icon_rgba(bytes([0, 0, 0, 128])))

    def test_corpus_and_pin_control(self):
        cars = load_source_metadata()
        self.assertEqual(len(cars), 35)
        for car in cars:
            m = json.loads((CARS / car["code"] / "manifest.json").read_text())
            record = next(r for r in m["files"] if "/icon/" in r["dst"])
            data = (CARS.parent / record["dst"]).read_bytes()
            metadata, pixels, _ = decode_file(data, record["dst"])
            paint = car["paint"]
            self.assertEqual(paint["source_sha256"], record["sha256"])
            self.assertEqual(paint["rgba_sha256"], hashlib.sha256(pixels).hexdigest())
            self.assertEqual(paint["dimensions"], [165, 98])
            self.assertEqual(metadata["rgba_bytes"], 165 * 98 * 4)
            # Count independently, without using the sampling helper.
            bucket = tuple(v >> 4 for v in paint["rgb"])
            count = 0
            for i in range(0, len(pixels), 4):
                r, g, b, alpha = pixels[i:i + 4]
                if tuple(v >> 4 for v in (r, g, b)) != bucket or alpha != 128:
                    continue
                if max(r, g, b) < 40 or (r > 216 and g > 216 and b < 200):
                    continue
                if paint["selection"] == "saturated" and max(r, g, b) - min(r, g, b) < 32:
                    continue
                count += 1
            self.assertEqual(paint["count"], count)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.ptg"
            path.write_bytes(data[:-1])
            with self.assertRaisesRegex(ValueError, "differs from manifest pin"):
                body_paint(path, record["sha256"])


if __name__ == "__main__":
    unittest.main()
