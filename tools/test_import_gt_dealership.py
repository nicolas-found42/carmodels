#!/usr/bin/env python3
"""GT imports reject corrupt sources and preserve existing editable copies."""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

from bake_models import ROOT, read_glb
from build_dealership import build, check
from import_gt_dealership import import_cars, imported_entry
from gt_metadata import load_database, model_metadata


class GTImportTests(unittest.TestCase):
    def metadata_fixture(self, base, code="_afr7n"):
        source, dest, row = self.fixture(base)
        old = source / row["file"]
        row.update(code="simulation/" + code, file="simulation/" + code + ".glb")
        old.rename(source / row["file"])
        (source / "index.json").write_text(json.dumps({"cars": [row]}))
        return source, dest, row

    def enrich_source(self, source, row, code="_afr7n"):
        database = load_database(ROOT / "games/gran-turismo/cars/_metadata")
        metadata = model_metadata(database, code, [49, 53, 54, 98, 115])
        data = self.change_source(source, row)
        doc, binary = read_glb(data)
        doc["extras"]["nativeMetadata"] = metadata
        encoded = json.dumps(doc).encode()
        encoded += b" " * (-len(encoded) % 4)
        data = (
            struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(binary))
            + struct.pack("<I4s", len(encoded), b"JSON")
            + encoded
            + struct.pack("<I4s", len(binary), b"BIN\0")
            + binary
        )
        (source / row["file"]).write_bytes(data)
        row.update(
            native_metadata=metadata,
            sha256=hashlib.sha256(data).hexdigest(),
            bytes=len(data),
        )
        (source / "index.json").write_text(json.dumps({"cars": [row]}))
        return data, metadata

    def test_verified_metadata_enrichment_preserves_owner_fields_and_edited_geometry(
        self,
    ):
        for edited in (False, True):
            with (
                self.subTest(edited=edited),
                tempfile.TemporaryDirectory() as temporary,
            ):
                source, dest, row = self.metadata_fixture(Path(temporary))
                import_cars(source, dest)
                catalog = json.loads((dest / "catalog.json").read_text())
                catalog[1]["name"] = "Owner name"
                catalog[1]["kg"] = 1400
                catalog[1]["claimLimits"].append("Owner note")
                (dest / "catalog.json").write_text(json.dumps(catalog))
                working = dest / "models/GT_SIMULATION__AFR7N.glb"
                if edited:
                    working.write_bytes(working.read_bytes() + b"owner geometry")
                before = working.read_bytes()
                data, metadata = self.enrich_source(source, row)
                self.assertEqual(import_cars(source, dest, True), 1)
                current = json.loads((dest / "catalog.json").read_text())[1]
                self.assertEqual((current["name"], current["kg"]), ("Owner name", 1400))
                self.assertEqual(current["specifications"]["mass_kg"], 1250)
                self.assertEqual(current["bhp"], 202)
                self.assertIsNone(current["year"])
                self.assertEqual(current["nativeMetadata"], metadata)
                self.assertEqual(current["colourVariants"], metadata["colour_variants"])
                self.assertIn("Owner note", current["claimLimits"])
                self.assertEqual(working.read_bytes(), before if edited else data)
                origin = json.loads((dest / "origins.json").read_text())["cars"][0]
                self.assertEqual(origin["latestMetadata"]["name"], "RX-7 FC GT-X")
                after = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                self.assertEqual(import_cars(source, dest, True), 0)
                self.assertEqual(
                    after, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                )

    def test_generated_names_specs_and_unresolved_racing_metadata(self):
        for code, expected in [("_afr7n", "RX-7 FC GT-X"), ("_afr7r", "_afr7r")]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temporary:
                source, dest, row = self.metadata_fixture(Path(temporary), code)
                import_cars(source, dest)
                self.enrich_source(source, row, code)
                self.assertEqual(import_cars(source, dest, True), 1)
                current = json.loads((dest / "catalog.json").read_text())[1]
                self.assertEqual(current["name"], expected)
                if code.endswith("r"):
                    self.assertIsNone(current["specifications"])
                    self.assertIsNone(current["kg"])
                    self.assertIsNone(current["bhp"])
                else:
                    self.assertEqual(current["kg"], 1250)

    def test_detached_or_changed_metadata_rejected_before_writes(self):
        for mutation in ("code", "embedded", "name", "racing"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as temporary,
            ):
                source, dest, row = self.metadata_fixture(Path(temporary))
                self.enrich_source(source, row)
                if mutation == "code":
                    row.update(code="simulation/_hcvon", file="simulation/_hcvon.glb")
                elif mutation == "embedded":
                    row["native_metadata"]["colour_variants"].pop()
                    row["native_metadata"]["provenance"]["colour_name_matches"].pop()
                elif mutation == "name":
                    row["native_metadata"]["identity"]["name"] = "Invented name"
                else:
                    row["native_metadata"]["identity"]["status"] = "unresolved"
                (source / "index.json").write_text(json.dumps({"cars": [row]}))
                before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                with self.assertRaisesRegex(ValueError, "metadata"):
                    import_cars(source, dest, True)
                self.assertEqual(
                    before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                )

    def test_consolidation_metadata_history_keeps_source_defaults_separate_from_owner_edits(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            source, dest, canonical = self.metadata_fixture(Path(temporary))
            data = (source / canonical["file"]).read_bytes()
            editions = []
            (source / "simulation/_afr7n").mkdir()
            for edition in ("day", "night"):
                row = {
                    **canonical,
                    "code": canonical["code"] + "/" + edition,
                    "file": "simulation/_afr7n/" + edition + ".glb",
                }
                (source / row["file"]).write_bytes(data)
                editions.append(row)
            (source / "index.json").write_text(json.dumps({"cars": editions}))
            import_cars(source, dest)
            catalog = json.loads((dest / "catalog.json").read_text())
            catalog[1].update(name="Owner label", kg=1400)
            (dest / "catalog.json").write_text(json.dumps(catalog))
            canonical.update(
                canonical_source_id=editions[0]["code"],
                aliases=[r["code"] for r in editions],
            )
            self.enrich_source(source, canonical)
            self.assertEqual(import_cars(source, dest, True, True), 1)
            entry = json.loads((dest / "catalog.json").read_text())[1]
            self.assertEqual((entry["name"], entry["kg"]), ("Owner label", 1400))
            origin = json.loads((dest / "origins.json").read_text())["cars"][0]
            self.assertEqual(
                (origin["latestMetadata"]["name"], origin["latestMetadata"]["kg"]),
                ("RX-7 FC GT-X", 1250),
            )
            before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            self.assertEqual(import_cars(source, dest, True), 0)
            self.assertEqual(
                before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            )
            self.change_source(
                source, canonical, generator="Second source fixture version"
            )
            self.assertEqual(import_cars(source, dest, True), 1)
            refreshed = json.loads((dest / "catalog.json").read_text())[1]
            self.assertEqual(
                (refreshed["name"], refreshed["kg"]), ("Owner label", 1400)
            )

    def legacy_fixture(self, base):
        source, dest, day = self.fixture(base)
        night = {
            **day,
            "code": "simulation/_test/night",
            "file": "simulation/_test/night.glb",
        }
        (source / night["file"]).write_bytes((source / day["file"]).read_bytes())
        (source / "index.json").write_text(json.dumps({"cars": [day, night]}))
        import_cars(source, dest)
        catalog = json.loads((dest / "catalog.json").read_text())
        catalog[1]["name"] = "Owner name"
        catalog[1]["ownerNote"] = "Keep me"
        catalog[2]["ownerNote"] = "Night history"
        (dest / "catalog.json").write_text(json.dumps(catalog))
        canonical = {
            **day,
            "code": "simulation/_test",
            "file": "simulation/_test.glb",
            "canonical_source_id": day["code"],
            "aliases": [day["code"], night["code"]],
        }
        (source / canonical["file"]).write_bytes((source / day["file"]).read_bytes())
        (source / "index.json").write_text(json.dumps({"cars": [canonical]}))
        return source, dest, canonical

    def test_consolidation_preserves_custom_metadata_and_retired_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest, row = self.legacy_fixture(Path(tmp))
            before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "--consolidate"):
                import_cars(source, dest, upgrade_unedited=True)
            self.assertEqual(
                before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            )
            self.assertEqual(import_cars(source, dest, True, True), 1)
            catalog = json.loads((dest / "catalog.json").read_text())
            self.assertEqual(len(catalog), 2)
            car = catalog[1]
            self.assertEqual(
                (car["code"], car["sourceVariant"], car["name"], car["ownerNote"]),
                ("GT_SIMULATION__TEST", "canonical", "Owner name", "Keep me"),
            )
            self.assertEqual(
                car["sourceAliases"],
                ["GT_SIMULATION__TEST_DAY", "GT_SIMULATION__TEST_NIGHT"],
            )
            origin = json.loads((dest / "origins.json").read_text())["cars"][0]
            self.assertEqual(origin["initialSource"]["code"], "simulation/_test/day")
            self.assertEqual(origin["latestSource"]["code"], row["code"])
            self.assertEqual(
                origin["retiredVariants"][1]["catalog"]["ownerNote"], "Night history"
            )
            self.assertFalse((dest / "models/GT_SIMULATION__TEST_DAY.glb").exists())
            self.assertFalse((dest / "models/GT_SIMULATION__TEST_NIGHT.glb").exists())
            self.assertEqual(
                (dest / "models/GT_SIMULATION__TEST.glb").read_bytes(),
                (source / row["file"]).read_bytes(),
            )
            after = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            self.assertEqual(import_cars(source, dest, True, True), 0)
            self.assertEqual(
                after, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            )

    def test_consolidation_invalid_source_or_edited_duplicate_leaves_all_files_intact(
        self,
    ):
        for mutation in ("source", "duplicate"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.legacy_fixture(Path(tmp))
                if mutation == "source":
                    row["sha256"] = "0" * 64
                    (source / "index.json").write_text(json.dumps({"cars": [row]}))
                else:
                    path = dest / "models/GT_SIMULATION__TEST_NIGHT.glb"
                    path.write_bytes(path.read_bytes() + b"owned edit")
                before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                with self.assertRaisesRegex(ValueError, "hash/size|edited duplicate"):
                    import_cars(source, dest, True, True)
                self.assertEqual(
                    before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                )

    def test_consolidation_rolls_back_retirement_when_metadata_install_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest, _ = self.legacy_fixture(Path(tmp))
            before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            replace = Path.replace

            def fail_metadata(path, target):
                if path.name == "catalog.json" and path.parent.name.startswith(
                    ".gt-import-"
                ):
                    raise OSError("simulated metadata failure")
                return replace(path, target)

            with patch.object(Path, "replace", fail_metadata):
                with self.assertRaisesRegex(OSError, "simulated"):
                    import_cars(source, dest, True, True)
            self.assertEqual(
                before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            )

    def test_consolidation_carries_edited_day_model_into_canonical_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest, row = self.legacy_fixture(Path(tmp))
            original, original_row = (source / row["file"]).read_bytes(), dict(row)
            edited = self.change_source(source, row)
            (dest / "models/GT_SIMULATION__TEST_DAY.glb").write_bytes(edited)
            (source / row["file"]).write_bytes(original)
            (source / "index.json").write_text(json.dumps({"cars": [original_row]}))
            self.assertEqual(import_cars(source, dest, True, True), 1)
            self.assertEqual(
                (dest / "models/GT_SIMULATION__TEST.glb").read_bytes(), edited
            )
            self.assertEqual(import_cars(source, dest, True, True), 0)

    def change_source(self, source, row, generator="Updated source fixture"):
        path = source / row["file"]
        doc, binary = read_glb(path.read_bytes())
        doc["asset"]["generator"] = generator
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
        row.update(
            sha256=hashlib.sha256(data).hexdigest(),
            bytes=len(data),
            claim_limits=["Updated native assembly fixture."],
        )
        (source / "index.json").write_text(json.dumps({"cars": [row]}))
        return data

    def test_explicit_upgrade_only_unedited_models_and_preserve_history(self):
        for edited in (False, True):
            with self.subTest(edited=edited), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.fixture(Path(tmp))
                import_cars(source, dest)
                initial_origins = json.loads((dest / "origins.json").read_text())
                catalog = json.loads((dest / "catalog.json").read_text())
                catalog[1]["name"] = "Custom name"
                catalog[1]["claimLimits"].append("Custom owner limitation.")
                (dest / "catalog.json").write_text(json.dumps(catalog))
                target = dest / f"models/{catalog[1]['code']}.glb"
                if edited:
                    target.write_bytes(target.read_bytes() + b"owned edit")
                before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                updated = self.change_source(source, row)
                self.assertEqual(import_cars(source, dest), 0)
                self.assertEqual(
                    before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                )
                self.assertEqual(
                    import_cars(source, dest, upgrade_unedited=True), int(not edited)
                )
                if edited:
                    self.assertEqual(
                        before,
                        {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()},
                    )
                else:
                    self.assertEqual(target.read_bytes(), updated)
                    current = json.loads((dest / "catalog.json").read_text())[1]
                    self.assertEqual(current["name"], "Custom name")
                    self.assertIn(row["claim_limits"][0], current["claimLimits"])
                    self.assertIn("Custom owner limitation.", current["claimLimits"])
                    origin = json.loads((dest / "origins.json").read_text())["cars"][0]
                    self.assertEqual(
                        origin["initialSource"],
                        initial_origins["cars"][0]["initialSource"],
                    )
                    self.assertEqual(origin["latestSource"]["sha256"], row["sha256"])
                    self.assertEqual(len(origin["sourceUpgrades"]), 1)
                    self.assertEqual(target.stat().st_nlink, 1)
                after = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                self.assertEqual(import_cars(source, dest, upgrade_unedited=True), 0)
                self.assertEqual(
                    after, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                )

    def test_asset_namespaces_and_unknown_values(self):
        day = imported_entry({"code": "simulation/_test/day"})
        night = imported_entry({"code": "simulation/_test/night"})
        arcade = imported_entry({"code": "arcade/pair-0039"})
        self.assertEqual(len({day["code"], night["code"], arcade["code"]}), 3)
        self.assertEqual(arcade["sourceVariant"], "arcade")
        self.assertEqual(arcade["code"], "GT_ARCADE_PAIR_0039")
        for car in (day, night, arcade):
            self.assertEqual(car["bodyStyle"], "unknown")
            self.assertIsNone(car["kg"])
        for code in (
            "arcade/pair-0039/guess",
            "simulation/_test/guess",
            "simulation/../day",
        ):
            with self.assertRaises(ValueError):
                imported_entry({"code": code})

    def fixture(self, base):
        source, dest = base / "source", base / "editable"
        (source / "simulation/_test").mkdir(parents=True)
        (dest / "models").mkdir(parents=True)
        initial = json.loads((ROOT / "dealership/dealership/catalog.json").read_text())[
            0
        ]
        shutil.copyfile(
            ROOT / f"dealership/dealership/models/{initial['code']}.glb",
            dest / f"models/{initial['code']}.glb",
        )
        (dest / "catalog.json").write_text(json.dumps([initial]))
        (dest / "origins.json").write_text(json.dumps({"schema": 1, "cars": []}))
        data = (
            ROOT / f"dealership/dealership/models/{initial['code']}.glb"
        ).read_bytes()
        (source / "simulation/_test/day.glb").write_bytes(data)
        row = dict(
            code="simulation/_test/day",
            file="simulation/_test/day.glb",
            sha256=hashlib.sha256(data).hexdigest(),
            bytes=len(data),
            claim_limits=[
                "Native wheel geometry is not recovered; this is a body preview."
            ],
        )
        (source / "index.json").write_text(json.dumps({"cars": [row]}))
        return source, dest, row

    def test_add_preserve_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, dest, row = self.fixture(base)
            original = (dest / "catalog.json").read_text()
            self.assertEqual(import_cars(source, dest), 1)
            catalog = json.loads((dest / "catalog.json").read_text())
            self.assertEqual(catalog[0], json.loads(original)[0])
            entry = catalog[1]
            self.assertIsNone(entry["bhp"])
            self.assertIsNone(entry["speed"])
            self.assertIn(row["claim_limits"][0], entry["claimLimits"])
            working = dest / f"models/{entry['code']}.glb"
            self.assertEqual(working.stat().st_nlink, 1)
            self.assertEqual(working.read_bytes(), (source / row["file"]).read_bytes())
            result = build(dest, base / "cars.json")
            self.assertEqual(result[1]["model"]["schema"], 2)
            check(dest, base / "cars.json")
            entry["name"] = "Edited custom name"
            (dest / "catalog.json").write_text(json.dumps(catalog))
            working.write_bytes(working.read_bytes() + b"custom edit")
            before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            self.assertEqual(import_cars(source, dest), 0)
            self.assertEqual(
                before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            )

    def test_corruption_collision_and_traversal_fail_before_writes(self):
        mutations = [
            lambda r: r.update(sha256="0" * 64),
            lambda r: r.update(bytes=r["bytes"] + 1),
            lambda r: r.update(file="../outside.glb"),
            lambda r: r.update(code="simulation/../day"),
            lambda r: r.update(code="simulation/_test/guess"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                source, dest, row = self.fixture(Path(tmp))
                before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                mutate(row)
                (source / "index.json").write_text(json.dumps({"cars": [row]}))
                with self.assertRaises(ValueError):
                    import_cars(source, dest)
                self.assertEqual(
                    before, {p: p.read_bytes() for p in dest.rglob("*") if p.is_file()}
                )
        with tempfile.TemporaryDirectory() as tmp:
            source, dest, row = self.fixture(Path(tmp))
            (source / "index.json").write_text(json.dumps({"cars": [row, row]}))
            with self.assertRaisesRegex(ValueError, "collide"):
                import_cars(source, dest)
            with self.assertRaisesRegex(ValueError, "separate"):
                import_cars(source, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
