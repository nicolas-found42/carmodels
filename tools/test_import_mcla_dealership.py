"""MCLA independent editable imports preserve user edits and reject bad source batches."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bake_models import read_glb
from test_build_dealership import write_glb
from import_mcla_catalog import sha

from import_mcla_dealership import entry_for, import_cars
from test_import_mcla_catalog import CODE, export, fixture


def setup(root):
    extraction, source, identities = fixture(root)
    export(extraction, source, identities)
    dealer = root / "dealer"
    dealer.mkdir()
    (dealer / "models").mkdir()
    (dealer / "catalog.json").write_text(json.dumps([{"code": "EXISTING"}]))
    (dealer / "origins.json").write_text(json.dumps({"schema": 1, "cars": []}))
    return source, dealer


class Tests(unittest.TestCase):
    def test_import_independent_and_preserve_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dealer = setup(Path(temp).resolve())
            self.assertEqual(import_cars(source, dealer), 1)
            row = json.loads((source / "index.json").read_text())["cars"][0]
            entry = entry_for(row)
            self.assertTrue(
                all(
                    entry[k] is None
                    for k in (
                        "year",
                        "bhp",
                        "kg",
                        "agility",
                        "accel",
                        "speed",
                        "weight",
                    )
                )
            )
            model = dealer / "models" / ("MCLA_" + CODE.upper() + ".glb")
            self.assertEqual(model.read_bytes(), (source / row["file"]).read_bytes())
            self.assertEqual(model.stat().st_nlink, 1)
            model.write_bytes(b"user edits")
            rows = json.loads((dealer / "catalog.json").read_text())
            rows[-1]["name"] = "Custom name"
            (dealer / "catalog.json").write_text(json.dumps(rows))
            self.assertEqual(import_cars(source, dealer, True), 0)
            self.assertEqual(model.read_bytes(), b"user edits")
            self.assertEqual(
                json.loads((dealer / "catalog.json").read_text())[-1]["name"],
                "Custom name",
            )

    def test_upgrade_unedited_preserves_metadata_and_history(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dealer = setup(Path(temp).resolve())
            import_cars(source, dealer)
            index = json.loads((source / "index.json").read_text())
            row = index["cars"][0]
            path = source / row["file"]
            old = path.read_bytes()
            doc, binary = read_glb(old)
            doc["asset"]["generator"] = "new-synthetic-source"
            write_glb(path, doc, binary)
            new = path.read_bytes()
            row.update(bytes=len(new), sha256=sha(new))
            (source / "index.json").write_text(json.dumps(index))
            rows = json.loads((dealer / "catalog.json").read_text())
            rows[-1]["name"] = "Custom name"
            (dealer / "catalog.json").write_text(json.dumps(rows))
            self.assertEqual(import_cars(source, dealer), 0)
            self.assertEqual(import_cars(source, dealer, True), 1)
            origins = json.loads((dealer / "origins.json").read_text())["cars"][0]
            self.assertEqual(origins["initialSource"]["sha256"], sha(old))
            self.assertEqual(origins["latestSource"]["sha256"], sha(new))
            self.assertEqual(
                origins["sourceUpgrades"][0],
                {"fromSha256": sha(old), "toSha256": sha(new)},
            )
            self.assertEqual(
                json.loads((dealer / "catalog.json").read_text())[-1]["name"],
                "Custom name",
            )
            self.assertEqual(import_cars(source, dealer, True), 0)

    def test_whole_batch_preflight_and_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dealer = setup(Path(temp).resolve())
            before = (dealer / "catalog.json").read_bytes()
            index = json.loads((source / "index.json").read_text())
            index["cars"] *= 2
            (source / "index.json").write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, "collide"):
                import_cars(source, dealer)
            self.assertEqual((dealer / "catalog.json").read_bytes(), before)
            self.assertEqual(list((dealer / "models").iterdir()), [])
            with self.assertRaisesRegex(ValueError, "separate"):
                import_cars(source, source)

    def test_failed_metadata_commit_restores_models_and_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dealer = setup(Path(temp).resolve())
            before = (dealer / "catalog.json").read_bytes()
            real_replace = Path.replace

            def failing(path, target):
                if path.name == "catalog.json":
                    raise OSError("commit failure")
                return real_replace(path, target)

            with (
                patch.object(Path, "replace", failing),
                self.assertRaisesRegex(OSError, "commit failure"),
            ):
                import_cars(source, dealer)
            self.assertEqual((dealer / "catalog.json").read_bytes(), before)
            self.assertEqual(list((dealer / "models").iterdir()), [])

    def test_hash_rejection_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            source, dealer = setup(Path(temp).resolve())
            before = (dealer / "catalog.json").read_bytes()
            next((source / "previews").iterdir()).write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "hash/size"):
                import_cars(source, dealer)
            self.assertEqual((dealer / "catalog.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
