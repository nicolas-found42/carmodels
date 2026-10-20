"""MCLA native coverage, static identity and re-derivation tamper controls."""

import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from bake_models import read_glb
from gt4_glb import Builder
import import_mcla_catalog as catalog

CODE = "vp_test_car_01"


def preview(_extraction, code):
    b = Builder()
    positions = b.accessor([(0, 0, 0), (1, 0, 0), (0, 1, 0)], "position")
    normals = b.accessor([(0, 0, 1)] * 3, "normal")
    indices = b.accessor([0, 1, 2], "index")
    material = b.material("neutral", [0.6, 0.6, 0.6, 1])
    b.doc["meshes"] = [
        {
            "primitives": [
                {
                    "attributes": {"POSITION": positions, "NORMAL": normals},
                    "indices": indices,
                    "material": material,
                }
            ]
        }
    ]
    b.doc["nodes"] = [{"mesh": 0, "name": "body"}]
    b.doc["scenes"] = [{"nodes": [0]}]
    b.doc["extras"] = {"car": code, "source_profile": catalog.PROFILE}
    return b.finish(), {"triangles": 1}


def fixture(root):
    extraction, output = root / "cars", root / "public" / catalog.GAME
    file = CODE + "/resources/vehicle/" + CODE + "/body_lod_0.xrsc"
    path = extraction / file
    path.parent.mkdir(parents=True)
    path.write_bytes(b"checked native data")
    row = {
        "file": file,
        "bytes": path.stat().st_size,
        "sha256": catalog.sha(path.read_bytes()),
        "source": {"archive_path": file[len(CODE) + 1 :]},
    }
    manifest = {"id": CODE, "files": [row]}
    (extraction / CODE / "manifest.json").write_text(json.dumps(manifest))
    vehicle = {"id": CODE, "manifest": CODE + "/manifest.json"}
    (extraction / "index.json").write_text(
        json.dumps({"vehicles": [vehicle], "source": {"sha256": "a" * 64}})
    )
    identities = {
        CODE: {"name": CODE, "name_source": {"kind": "code-fallback", "code": CODE}}
    }
    return extraction, output, identities


def export(extraction, output, identities):
    with patch.object(catalog, "build_car", preview):
        return catalog.export_catalog(extraction, output, identities)


class Tests(unittest.TestCase):
    def old_edition(self, extraction, output, identities):
        with (
            patch.object(catalog, "PROFILE", catalog.PREVIOUS_PROFILE),
            patch.object(catalog, "LIMITS", catalog.PREVIOUS_LIMITS),
        ):
            export(extraction, output, identities)

    def refreshed(self, extraction, output, identities):
        with patch.object(catalog, "build_car", preview):
            return catalog.export_catalog(extraction, output, identities, refresh=True)

    def snapshot(self, output):
        return {
            p.relative_to(output).as_posix(): p.read_bytes()
            for p in output.rglob("*")
            if p.is_file()
        }

    def test_refresh_accepts_pinned_v1_before_the_v2_geometry_upgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            with (
                patch.object(catalog, "PROFILE", "mcla-xbox360-static-stock-v1"),
                patch.object(catalog, "LIMITS", catalog.PREVIOUS_LIMITS),
            ):
                export(extraction, output, identities)
            native = output / "native" / (CODE + ".zip")
            original = native.read_bytes()
            self.assertEqual(self.refreshed(extraction, output, identities), 1)
            self.assertEqual(native.read_bytes(), original)
            self.assertEqual(
                json.loads((output / "index.json").read_text())["cars"][0][
                    "source_profile"
                ],
                catalog.PROFILE,
            )

    def test_refresh_migrates_old_profile_and_preserves_exact_zip_encoding(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            self.old_edition(extraction, output, identities)
            current = json.loads((output / "index.json").read_text())
            row = current["cars"][0]
            native = output / row["native_package"]["file"]
            members = catalog.package_members(CODE, native.read_bytes())
            buffer = io.BytesIO()
            with zipfile.ZipFile(
                buffer, "w", compression=zipfile.ZIP_STORED
            ) as archive:
                for name, data in members.items():
                    archive.writestr(name, data)
            native.write_bytes(buffer.getvalue())
            row["native_package"].update(
                bytes=native.stat().st_size, sha256=catalog.sha(native.read_bytes())
            )
            (output / "index.json").write_text(json.dumps(current))
            old = self.snapshot(output)
            with patch.object(catalog, "PROFILE", "mcla-xbox360-static-stock-v2"):
                with self.assertRaisesRegex(ValueError, "index differs"):
                    export(extraction, output, identities)
            self.assertEqual(self.snapshot(output), old)
            self.assertEqual(self.refreshed(extraction, output, identities), 1)
            updated = json.loads((output / "index.json").read_text())["cars"][0]
            self.assertEqual(updated["source_profile"], "mcla-xbox360-static-stock-v3")
            self.assertEqual(
                read_glb((output / updated["file"]).read_bytes())[0]["extras"][
                    "source_profile"
                ],
                updated["source_profile"],
            )
            self.assertEqual(native.read_bytes(), old[row["native_package"]["file"]])
            self.assertNotEqual((output / row["file"]).read_bytes(), old[row["file"]])

    def test_refresh_corrupt_old_files_and_unsupported_metadata_fail_before_write(self):
        for mutation in (
            "glb",
            "native",
            "profile",
            "source",
            "limits",
            "extra",
            "native-rehashed",
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                extraction, output, identities = fixture(Path(temp).resolve())
                self.old_edition(extraction, output, identities)
                current = json.loads((output / "index.json").read_text())
                row = current["cars"][0]
                if mutation in ("glb", "native"):
                    name = (
                        row["file"]
                        if mutation == "glb"
                        else row["native_package"]["file"]
                    )
                    (output / name).write_bytes(b"corrupt old bytes")
                elif mutation == "profile":
                    row["source_profile"] = "unrecognized"
                elif mutation == "source":
                    current["source"] = {"sha256": "b" * 64}
                elif mutation == "limits":
                    current["claim_limits"] = ["unsupported promise"]
                elif mutation == "extra":
                    (output / "unexpected.txt").write_text("user file")
                else:
                    native = output / row["native_package"]["file"]
                    members = catalog.package_members(CODE, native.read_bytes())
                    file = "resources/vehicle/" + CODE + "/body_lod_0.xrsc"
                    members[file] = b"other data"
                    manifest = json.loads(members["manifest.json"])
                    manifest["files"][0].update(
                        bytes=len(members[file]), sha256=catalog.sha(members[file])
                    )
                    members["manifest.json"] = json.dumps(manifest).encode()
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, "w") as archive:
                        for name, data in members.items():
                            archive.writestr(name, data)
                    native.write_bytes(buffer.getvalue())
                    row["native_package"].update(
                        bytes=native.stat().st_size,
                        sha256=catalog.sha(native.read_bytes()),
                    )
                (output / "index.json").write_text(json.dumps(current))
                old = self.snapshot(output)
                reason = {
                    "glb": "hash/size",
                    "native": "hash/size",
                    "profile": "Unsupported",
                    "source": "identity/coverage",
                    "limits": "claim limits",
                    "extra": "file coverage",
                    "native-rehashed": "differs from extraction",
                }[mutation]
                with self.assertRaisesRegex(ValueError, reason):
                    self.refreshed(extraction, output, identities)
                self.assertEqual(self.snapshot(output), old)

    def test_refresh_missing_native_requires_old_pin_and_restores_matching_zip(self):
        for corrupt_pin in (False, True):
            with (
                self.subTest(corrupt_pin=corrupt_pin),
                tempfile.TemporaryDirectory() as temp,
            ):
                extraction, output, identities = fixture(Path(temp).resolve())
                self.old_edition(extraction, output, identities)
                current = json.loads((output / "index.json").read_text())
                row = current["cars"][0]
                native = output / row["native_package"]["file"]
                original = native.read_bytes()
                native.unlink()
                if corrupt_pin:
                    row["native_package"]["sha256"] = "b" * 64
                    (output / "index.json").write_text(json.dumps(current))
                    old = self.snapshot(output)
                    with self.assertRaisesRegex(ValueError, "differs from its pin"):
                        self.refreshed(extraction, output, identities)
                    self.assertEqual(self.snapshot(output), old)
                else:
                    self.refreshed(extraction, output, identities)
                    self.assertEqual(native.read_bytes(), original)

    def test_refresh_symlinks_fail_without_modifying_their_targets(self):
        for target in ("directory", "model", "native", "index"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                extraction, output, identities = fixture(root)
                self.old_edition(extraction, output, identities)
                before = self.snapshot(output)
                if target == "directory":
                    saved = root / "saved"
                    output.rename(saved)
                    output.symlink_to(saved, target_is_directory=True)
                    link = output
                else:
                    name = {
                        "model": "previews/" + CODE + ".glb",
                        "native": "native/" + CODE + ".zip",
                        "index": "index.json",
                    }[target]
                    link = output / name
                    saved = root / "saved"
                    link.rename(saved)
                    link.symlink_to(saved)
                saved_bytes = saved.read_bytes() if saved.is_file() else None
                with self.assertRaisesRegex(ValueError, "symlinks"):
                    self.refreshed(extraction, output, identities)
                self.assertTrue(link.is_symlink())
                if saved_bytes is not None:
                    self.assertEqual(saved.read_bytes(), saved_bytes)
                else:
                    self.assertEqual(self.snapshot(saved), before)

    def test_source_refresh_keeps_edited_dealership_model_and_metadata(self):
        from import_mcla_dealership import import_cars

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            extraction, output, identities = fixture(root)
            self.old_edition(extraction, output, identities)
            dealer = root / "dealer"
            dealer.mkdir()
            (dealer / "models").mkdir()
            (dealer / "catalog.json").write_text(json.dumps([{"code": "EXISTING"}]))
            (dealer / "origins.json").write_text(json.dumps({"schema": 1, "cars": []}))
            with (
                patch.object(catalog, "PROFILE", catalog.PREVIOUS_PROFILE),
                patch.object(catalog, "LIMITS", catalog.PREVIOUS_LIMITS),
            ):
                import_cars(output, dealer)
            model = dealer / "models" / ("MCLA_" + CODE.upper() + ".glb")
            model.write_bytes(b"edited dealership model")
            metadata = json.loads((dealer / "catalog.json").read_text())
            metadata[-1]["name"] = "User name"
            (dealer / "catalog.json").write_text(json.dumps(metadata))
            old = self.snapshot(dealer)
            self.refreshed(extraction, output, identities)
            self.assertEqual(import_cars(output, dealer, upgrade_unedited=True), 0)
            self.assertEqual(self.snapshot(dealer), old)

    def test_refresh_rolls_back_directory_on_failed_install_or_final_verification(self):
        for failure in ("install", "verify"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                extraction, output, identities = fixture(Path(temp).resolve())
                self.old_edition(extraction, output, identities)
                old = self.snapshot(output)
                rename = Path.rename
                verify = catalog.verify_published

                def failed_rename(path, destination):
                    if (
                        failure == "install"
                        and path.name == "source"
                        and Path(destination) == output
                    ):
                        raise OSError("injected install failure")
                    return rename(path, destination)

                def failed_verify(extraction, destination, *args, **kwargs):
                    if failure == "verify" and destination == output:
                        raise ValueError("injected final verification failure")
                    return verify(extraction, destination, *args, **kwargs)

                with (
                    patch.object(Path, "rename", failed_rename),
                    patch.object(catalog, "verify_published", failed_verify),
                ):
                    with self.assertRaisesRegex((OSError, ValueError), "injected"):
                        self.refreshed(extraction, output, identities)
                self.assertEqual(self.snapshot(output), old)
                self.assertFalse(list(output.parent.glob(".mcla-refresh-*")))

    def test_availability_cli_never_skips_malformed_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            extraction, _, _ = fixture(root)

            def available():
                result = subprocess.run(
                    [
                        sys.executable,
                        str(Path(catalog.__file__)),
                        "--available",
                        "--iso",
                        str(root / "missing.iso"),
                        "--extraction",
                        str(extraction),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return result.returncode

            self.assertEqual(available(), 1)
            for payload in [
                "broken JSON",
                "{}",
                '{"vehicles": []}',
                '{"vehicles": {}}',
                json.dumps(
                    {"vehicles": [{"id": CODE, "manifest": "../manifest.json"}]}
                ),
                json.dumps({"vehicles": [None]}),
            ]:
                (extraction / "index.json").write_text(payload)
                self.assertEqual(available(), 2, payload)
            (extraction / "index.json").unlink()
            self.assertEqual(
                available(), 2, "existing local files without their index must fail"
            )
            missing = root / "absent"
            self.assertEqual(catalog.source_available(missing, root / "missing.iso"), 1)

    def test_availability_distinguishes_missing_disc_and_partial_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            extraction, _, _ = fixture(root)
            iso = root / "disc.iso"

            def available():
                with patch(
                    "sys.argv",
                    [
                        "import_mcla_catalog",
                        "--available",
                        "--iso",
                        str(iso),
                        "--extraction",
                        str(extraction),
                    ],
                ):
                    return catalog.main()

            self.assertEqual(
                available(), 1, "complete extraction without optional disc must skip"
            )
            iso.write_bytes(b"available input")
            self.assertEqual(available(), 0)
            index = json.loads((extraction / "index.json").read_text())
            index["vehicles"].append(
                {"id": "vp_missing", "manifest": "vp_missing/manifest.json"}
            )
            (extraction / "index.json").write_text(json.dumps(index))
            self.assertEqual(available(), 2, "partial extraction must fail")
            iso.unlink()
            self.assertEqual(
                available(), 2, "missing disc must not hide partial extraction"
            )
            (extraction / CODE / "manifest.json").unlink()
            self.assertEqual(
                available(), 2, "native files without any manifests are partial"
            )
            index_only = root / "index-only"
            index_only.mkdir()
            (index_only / "index.json").write_text(json.dumps(index))
            self.assertEqual(
                catalog.source_available(index_only, iso),
                1,
                "committed index without local files must skip",
            )

    def test_export_repeat_and_rederive(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            self.assertEqual(export(extraction, output, identities), 1)
            self.assertEqual(export(extraction, output, identities), 0)
            row = json.loads((output / "index.json").read_text())["cars"][0]
            data = catalog.source_package(row, output)
            self.assertEqual(read_glb(data)[0]["extras"]["car"], CODE)
            members = catalog.package_members(
                CODE, (output / row["native_package"]["file"]).read_bytes()
            )
            self.assertEqual(
                members["resources/vehicle/" + CODE + "/body_lod_0.xrsc"],
                b"checked native data",
            )
            self.assertEqual(row["display_name"], CODE)

    def test_missing_zip_restored_and_catalog_permits_local_absence(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            export(extraction, output, identities)
            row = json.loads((output / "index.json").read_text())["cars"][0]
            path = output / row["native_package"]["file"]
            expected = path.read_bytes()
            path.unlink()
            catalog.source_package(row, output)
            self.assertEqual(export(extraction, output, identities), 0)
            self.assertEqual(path.read_bytes(), expected)

    def test_restore_and_display_identity_fail_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            export(extraction, output, identities)
            row = json.loads((output / "index.json").read_text())["cars"][0]
            native = output / row["native_package"]["file"]
            native.unlink()
            model = output / row["file"]
            original = model.read_bytes()
            model.write_bytes(b"edited")
            with self.assertRaisesRegex(ValueError, "hash/size"):
                export(extraction, output, identities)
            self.assertFalse(native.exists())
            model.write_bytes(original)
            current = json.loads((output / "index.json").read_text())
            current["cars"][0]["native_package"]["bytes"] = 1
            (output / "index.json").write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError, "differs from its pin"):
                export(extraction, output, identities)
            self.assertFalse(native.exists())
            row.update(
                display_name="Invented Ferrari",
                name_source={"kind": "ui-string", "key": "vp_wrong"},
            )
            with self.assertRaisesRegex(ValueError, "display identity"):
                catalog.source_package(row, output)

    def test_changed_native_prevents_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            next(extraction.rglob("*.xrsc")).write_bytes(b"changed native data")
            with self.assertRaisesRegex(ValueError, "hash/size differs"):
                export(extraction, output, identities)
            self.assertFalse(output.exists())

    def test_rehashed_wrong_identity_and_triangle_declaration(self):
        for field, value, reason in [
            ("source_code", "vp_wrong", "identity"),
            ("source_variant", "night", "identity"),
            ("records", [{"role": "stock", "triangles": 9}], "triangle declaration"),
        ]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                extraction, output, identities = fixture(Path(temp).resolve())
                export(extraction, output, identities)
                row = json.loads((output / "index.json").read_text())["cars"][0]
                row[field] = value
                with self.assertRaisesRegex(ValueError, reason):
                    catalog.source_package(row, output)
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            export(extraction, output, identities)
            row = json.loads((output / "index.json").read_text())["cars"][0]
            data, _ = preview(extraction, "vp_wrong")
            (output / row["file"]).write_bytes(data)
            row.update(bytes=len(data), sha256=catalog.sha(data))
            with self.assertRaisesRegex(ValueError, "GLB identity differs"):
                catalog.source_package(row, output)

    def test_paths_duplicates_corrupt_zip_and_manifest(self):
        for file in (
            "../outside",
            "/" + CODE + "/file",
            CODE + "/../../outside",
            CODE + "/bad\\file",
        ):
            with self.subTest(file=file), self.assertRaisesRegex(ValueError, "Unsafe"):
                catalog.member_path(CODE, {"file": file})
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            export(extraction, output, identities)
            row = json.loads((output / "index.json").read_text())["cars"][0]
            native = output / row["native_package"]["file"]
            members = catalog.package_members(CODE, native.read_bytes())
            members["extra.txt"] = b"wrong"
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                for name, payload in members.items():
                    archive.writestr(name, payload)
            with self.assertRaisesRegex(ValueError, "coverage differs"):
                catalog.package_members(CODE, data.getvalue())
            native.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash/size"):
                catalog.source_package(row, output)

    def test_duplicate_extraction_symlink_index_and_zip_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            index = extraction / "index.json"
            original = index.read_text()
            data = json.loads(original)
            data["vehicles"] *= 2
            index.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                export(extraction, output, identities)
            self.assertFalse(output.exists())
            index.write_text(original)
            export(extraction, output, identities)
            row = json.loads((output / "index.json").read_text())["cars"][0]
            members = catalog.package_members(
                CODE, (output / row["native_package"]["file"]).read_bytes()
            )
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                for name, payload in members.items():
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, payload)
            with self.assertRaisesRegex(ValueError, "regular files"):
                catalog.package_members(CODE, buffer.getvalue())
            native = output / row["native_package"]["file"]
            native.unlink()
            row["native_package"].update(bytes=-1, sha256="not-a-hash")
            with self.assertRaisesRegex(ValueError, "native metadata"):
                catalog.source_package(row, output)
            saved = output / "saved.json"
            (output / "index.json").rename(saved)
            (output / "index.json").symlink_to(saved)
            with self.assertRaisesRegex(ValueError, "symlinks"):
                export(extraction, output, identities)

    def test_changed_outputs_never_overwritten_and_unsafe_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            extraction, output, identities = fixture(Path(temp).resolve())
            export(extraction, output, identities)
            model = output / "previews" / (CODE + ".glb")
            model.write_bytes(b"edited")
            with self.assertRaisesRegex(ValueError, "hash/size"):
                export(extraction, output, identities)
            self.assertEqual(model.read_bytes(), b"edited")
            with self.assertRaisesRegex(ValueError, "separate"):
                export(extraction, extraction / "public", identities)
            with self.assertRaisesRegex(ValueError, "coverage"):
                export(extraction, output, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
