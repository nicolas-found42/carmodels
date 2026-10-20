"""GT4 dealership imports copy verified previews, preserve edits and reject conflicts."""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

from bake_models import ROOT, read_glb
from gt4_specdb import car_specs
from import_gt4_dealership import SPECDB, entry_for, import_cars

PUBLIC = ROOT / "dealership/public/gran-turismo-4"
CODES = ("acra0001", "chev0001")


def fixture(root):
    source, dest = root / "source", root / "dealership"
    rows = [
        r
        for r in json.loads((PUBLIC / "index.json").read_text())["cars"]
        if r["code"] in CODES
    ]
    for row in (
        rows
    ):  # Native ZIPs are local only; the import validates previews without them.
        (source / row["file"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PUBLIC / row["file"], source / row["file"])
    (source / "index.json").write_text(json.dumps({"cars": rows}))
    (dest / "models").mkdir(parents=True)
    (dest / "catalog.json").write_text(
        json.dumps([{"code": "EXISTING_CAR", "game": "redline"}])
    )
    (dest / "origins.json").write_text(json.dumps({"schema": 1, "cars": []}))
    return source, dest, rows


def change_source(source, rows, code):
    """Rewrite one preview's JSON (generator text) and rehash its row."""
    row = next(r for r in rows if r["code"] == code)
    path = source / row["file"]
    doc, binary = read_glb(path.read_bytes())
    doc["asset"]["generator"] = "Updated source fixture"
    encoded = json.dumps(doc).encode()
    encoded += b" " * (-len(encoded) % 4)
    data = (
        struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(binary))
        + struct.pack("<I4s", len(encoded), b"JSON")
        + encoded
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )
    path.write_bytes(data)
    row.update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    (source / "index.json").write_text(json.dumps({"cars": rows}))
    return data


def snapshot(folder):
    return {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}


class DealershipImportTests(unittest.TestCase):
    def test_factory_colour_metadata_uses_native_order_and_names(self):
        row = next(
            r
            for r in json.loads((PUBLIC / "index.json").read_text())["cars"]
            if r["code"] == "acra0001"
        )
        colours = entry_for(row, car_specs(SPECDB)["acra0001"])["colourVariants"]
        self.assertEqual([colour["index"] for colour in colours], list(range(5)))
        self.assertEqual(
            [colour["name"] for colour in colours],
            [
                "Sundance Gold",
                "San Marino Red",
                "Nighthawk Black Pearl",
                "Satin Silver Metallic",
                "Taffeta White",
            ],
        )

    def test_import_entries_and_preserving_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dest, rows = fixture(Path(temp).resolve())
            self.assertEqual(import_cars(source, dest), 2)
            catalog = json.loads((dest / "catalog.json").read_text())
            camaro = next(c for c in catalog if c["code"] == "GT4_CHEV0001")
            self.assertEqual(
                (
                    camaro["name"],
                    camaro["year"],
                    camaro["kg"],
                    camaro["game"],
                    camaro["displayMode"],
                ),
                (
                    "Chevrolet Camaro Z28 302 '69",
                    1969,
                    1415,
                    "gran-turismo-4",
                    "textured-glb",
                ),
            )
            self.assertIsNone(camaro["bhp"])
            for row in rows:
                self.assertEqual(
                    (dest / f"models/GT4_{row['code'].upper()}.glb").read_bytes(),
                    (source / row["file"]).read_bytes(),
                )
            origins = json.loads((dest / "origins.json").read_text())["cars"]
            self.assertEqual(
                {o["code"] for o in origins}, {"GT4_ACRA0001", "GT4_CHEV0001"}
            )
            before = snapshot(dest)
            self.assertEqual(import_cars(source, dest), 0)
            self.assertEqual(before, snapshot(dest))

    def test_upgrade_only_unedited_models(self):
        for edited in (False, True):
            with self.subTest(edited=edited), tempfile.TemporaryDirectory() as temp:
                source, dest, rows = fixture(Path(temp).resolve())
                import_cars(source, dest)
                target = dest / "models/GT4_ACRA0001.glb"
                if edited:
                    target.write_bytes(target.read_bytes() + b"owned edit")
                before = snapshot(dest)
                updated = change_source(source, rows, "acra0001")
                self.assertEqual(import_cars(source, dest), 0)
                self.assertEqual(before, snapshot(dest))
                self.assertEqual(
                    import_cars(source, dest, upgrade_unedited=True), int(not edited)
                )
                if edited:
                    self.assertEqual(before, snapshot(dest))
                else:
                    self.assertEqual(target.read_bytes(), updated)
                    origin = next(
                        o
                        for o in json.loads((dest / "origins.json").read_text())["cars"]
                        if o["code"] == "GT4_ACRA0001"
                    )
                    self.assertEqual(
                        origin["latestSource"]["sha256"],
                        hashlib.sha256(updated).hexdigest(),
                    )
                    self.assertEqual(len(origin["sourceUpgrades"]), 1)

    def test_conflict_and_corruption_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dest, rows = fixture(Path(temp).resolve())
            (source / rows[0]["file"]).write_bytes(b"glTF corrupt")
            with self.assertRaisesRegex(ValueError, "hash/size differs"):
                import_cars(source, dest)
        with tempfile.TemporaryDirectory() as temp:
            source, dest, _ = fixture(Path(temp).resolve())
            (dest / "catalog.json").write_text(
                json.dumps(
                    [{"code": "GT4_ACRA0001", "game": "redline", "sourceCode": "x"}]
                )
            )
            (dest / "models/GT4_ACRA0001.glb").write_bytes(b"x")
            with self.assertRaisesRegex(
                ValueError, "conflicts with an existing dealership entry"
            ):
                import_cars(source, dest)
        with tempfile.TemporaryDirectory() as temp:
            source, dest, _ = fixture(Path(temp).resolve())
            (dest / "models/GT4_CHEV0001.glb").write_bytes(b"stray")
            before = snapshot(dest)
            with self.assertRaisesRegex(ValueError, "occupies the GT4 identifier"):
                import_cars(source, dest)
            self.assertEqual(before, snapshot(dest))


if __name__ == "__main__":
    unittest.main()
