"""Extraction controls derive expectations from a synthetic disc, never its index."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from extract_gt4_cars import check_extraction, derive, write_extraction
from test_gt4_volume import volume_fixture
from test_mc3_archive import iso_fixture

CAR = [
    ("car/lod/test0001", b"CAR4\0\0\0\0race", True),
    ("car/lod/test0001.pat", b"Pat0\0\0\0\0", True),
    ("car/menu/test0001", b"CAR4\0\0\0\0menu", True),
    ("car/open/test0001", b"CAR4\0\0\0\0open", True),
    ("car/open/test0001.pat", b"Pat0\0\0\0\0open", True),
    ("wheel/lod/test0001", b"MDLS race wheel", True),
    ("wheel/menu/test0001", b"MDLS menu wheel", True),
]
SHARED = [
    ("wheel/lod/bbs_001w", b"MDLS aftermarket", True),
    ("tire/lod/bs__0001", b"MDLS tire", True),
    ("wing/lod/p001", b"MDLS wing", True),
    ("specdb/GT4_TEST/GENERIC_CAR.dbt", b"GTDB table", True),
    ("specdb/GT4_TEST/RACES/0000000000000001", b"race row", True),
    ("crs/test/track", b"not a car", False),
]


def fixture(path, files=CAR + SHARED):
    path.write_bytes(
        iso_fixture(
            [
                ("GT4.VOL;1", volume_fixture(files)),
                ("SYSTEM.CNF;1", b"BOOT2 = cdrom0:\\SCES_517.19;1\r\n"),
            ]
        )
    )
    return path


class ExtractionTests(unittest.TestCase):
    def test_per_car_shared_and_provenance_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            iso = fixture(root / "source.iso")
            original = iso.read_bytes()
            index, files = write_extraction(iso, root / "cars")
            self.assertEqual([v["id"] for v in index["vehicles"]], ["test0001"])
            self.assertEqual(index["vehicles"][0]["files"], 7)
            names = {row["file"] for row in files}
            for path, payload, _ in CAR:
                self.assertEqual((root / "cars/test0001" / path).read_bytes(), payload)
            self.assertTrue(
                {
                    "shared/wheel/lod/bbs_001w",
                    "shared/tire/lod/bs__0001",
                    "shared/wing/lod/p001",
                    "provenance/specdb/GT4_TEST/GENERIC_CAR.dbt",
                    "provenance/SYSTEM.CNF",
                    "provenance/GT4.VOL.inventory.json",
                    "test0001/manifest.json",
                    "index.json",
                }
                <= names
            )
            self.assertFalse(
                any("RACES" in name or name.startswith("crs") for name in names)
            )
            manifest = json.loads((root / "cars/test0001/manifest.json").read_text())
            roles = {
                row["source"]["volume_path"]: row["source"]["role"]
                for row in manifest["files"]
            }
            self.assertEqual(roles["car/lod/test0001.pat"], "colour-patch")
            self.assertEqual(roles["wheel/menu/test0001"], "menu-wheel")
            self.assertTrue(
                all(
                    row["source"]["stored_sha256"] != row["sha256"]
                    for row in manifest["files"]
                )
            )
            repeated, checked = check_extraction(iso, root / "cars")
            self.assertEqual(index, repeated)
            self.assertEqual(files, checked)
            self.assertEqual(iso.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "absent or empty"):
                write_extraction(iso, root / "cars")

    def test_rewritten_index_cannot_mask_payload_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            iso = fixture(root / "source.iso")
            output = root / "cars"
            index, _ = write_extraction(iso, output)
            (output / "test0001/car/lod/test0001").write_bytes(b"tamper")
            index["files"] = []
            (output / "index.json").write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, "byte mismatch"):
                check_extraction(iso, output)

    def test_missing_extra_and_symlink_controls(self):
        for control in ("missing", "extra", "linked_file"):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                iso = fixture(root / "source.iso")
                output = root / "cars"
                write_extraction(iso, output)
                target = output / "test0001/car/menu/test0001"
                if control == "extra":
                    (output / "test0001/extra").write_bytes(b"!")
                elif control == "missing":
                    target.unlink()
                else:
                    target.unlink()
                    target.symlink_to(iso)
                with self.assertRaisesRegex(
                    ValueError, "coverage mismatch|linked extraction"
                ):
                    check_extraction(iso, output)

    def test_incomplete_or_orphan_car_files_fail(self):
        cases = [
            (
                "missing a race model, colour patch or menu model",
                [f for f in CAR if f[0] != "car/menu/test0001"],
            ),
            (
                "car file without a car/lod model",
                CAR + [("car/menu/other001", b"CAR4", True)],
            ),
            ("unexpected car file name", CAR + [("car/lod/short", b"CAR4", True)]),
            ("no car models found", SHARED),
        ]
        for reason, files in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                iso = fixture(Path(temp) / "source.iso", files)
                with self.assertRaisesRegex(ValueError, reason):
                    derive(iso, lambda path, data: None)

    def test_changed_source_detected_before_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            iso = fixture(root / "source.iso")
            from mc3_archive import file_digest

            real = file_digest(iso)
            with patch("extract_gt4_cars.file_digest", side_effect=[real, "0" * 64]):
                with self.assertRaisesRegex(ValueError, "disc changed"):
                    write_extraction(iso, root / "cars")
            self.assertFalse((root / "cars").exists())
            self.assertFalse(
                any(p.name.startswith("gt4-stage-") for p in root.iterdir())
            )


if __name__ == "__main__":
    unittest.main()
