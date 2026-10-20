#!/usr/bin/env python3
"""Build the multi-game source-model catalog without touching editable dealership models."""

import hashlib
import json
from pathlib import Path

from bake_models import read_glb

from import_gt4_catalog import GAME as GT4_GAME, source_package as gt4_package
from import_mc3_catalogs import GAME as MC3_GAME, source_package as mc3_package
from import_mc3_previews import source_preview as mc3_preview
from import_mcla_catalog import GAME as MCLA_GAME, source_package as mcla_package
from gt_metadata import validate_model_metadata

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "dealership/public"
# Native-only games publish packages; each game's validator owns its package format.
NATIVE_PACKAGES = {MC3_GAME: mc3_package}
# Games whose GLB rows also carry a native package validate the whole row themselves.
ROW_VALIDATORS = {GT4_GAME: gt4_package, MCLA_GAME: mcla_package, MC3_GAME: mc3_preview}


def model_catalog(public=PUBLIC):
    """Combine per-game export indexes, retaining game identity for duplicate car codes."""
    cars = []
    ids = set()
    for index_path in sorted(public.glob("*/index.json")):
        game = index_path.parent.name
        index = json.loads(index_path.read_text())
        for entry in index["cars"]:
            identifier = game + "/" + entry["code"]
            if identifier in ids:
                raise ValueError("Duplicate dealership model: " + identifier)
            ids.add(identifier)
            model = index_path.parent / entry["file"]
            if not model.resolve().is_relative_to(index_path.parent.resolve()):
                raise ValueError("Model outside game folder: " + identifier)
            if entry.get("asset_kind") == "native-package" or (
                game in NATIVE_PACKAGES and entry.get("asset_kind") is None
            ):
                if game not in NATIVE_PACKAGES:
                    raise ValueError("Unsupported native package game: " + identifier)
                NATIVE_PACKAGES[game](entry, index_path.parent)
            elif entry.get("asset_kind") not in (None, "glb"):
                raise ValueError("Unsupported source asset kind: " + identifier)
            else:
                data = model.read_bytes()
                if (
                    hashlib.sha256(data).hexdigest() != entry["sha256"]
                    or len(data) != entry["bytes"]
                ):
                    raise ValueError("Model hash/size differs: " + identifier)
                if game in ROW_VALIDATORS:
                    ROW_VALIDATORS[game](entry, index_path.parent)
                elif "native_package" in entry:
                    raise ValueError("Unsupported native package game: " + identifier)
            metadata = {
                key: entry[key] for key in ["code", "sha256", "bytes", "records"]
            }
            if entry.get("native_metadata") is not None:
                if game != "gran-turismo":
                    raise ValueError("Unsupported native metadata game: " + identifier)
                validate_model_metadata(entry["native_metadata"])
                parts = entry["code"].split("/")
                if (
                    len(parts) not in (2, 3)
                    or parts[0] != "simulation"
                    or parts[1].removeprefix("_")
                    != entry["native_metadata"]["provenance"]["native_code"]
                ):
                    raise ValueError(
                        "Native metadata is detached from source model: " + identifier
                    )
                doc, _ = read_glb(data)
                if (
                    doc.get("extras", {}).get("nativeMetadata")
                    != entry["native_metadata"]
                ):
                    raise ValueError(
                        "Source catalog metadata differs from model: " + identifier
                    )
                identity = entry["native_metadata"]["identity"]
                name = (
                    identity["name"] if identity["status"] == "verified" else parts[1]
                )
                if entry.get("display_name") != name:
                    raise ValueError(
                        "Source catalog display name differs from native identity: "
                        + identifier
                    )
                metadata["native_metadata"] = entry["native_metadata"]
            if "aliases" in entry:
                aliases = entry["aliases"]
                if not isinstance(aliases, list) or any(
                    not isinstance(alias, str)
                    or not alias
                    or Path(alias).is_absolute()
                    or ".." in Path(alias).parts
                    for alias in aliases
                ):
                    raise ValueError("Invalid model aliases: " + identifier)
                metadata["aliases"] = [game + "/" + alias for alias in aliases]
            # Exporters can describe source identities without inventing display names.
            for key in [
                "display_name",
                "source_profile",
                "source_variant",
                "claim_limits",
                "asset_kind",
                "native_members",
                "native_package",
            ]:
                if key in entry:
                    value = entry[key]
                    if key == "claim_limits":
                        if not isinstance(value, list) or not all(
                            isinstance(item, str) for item in value
                        ):
                            raise ValueError(
                                "Invalid model claim limits: " + identifier
                            )
                    elif key == "native_package":
                        if not isinstance(value, dict) or not isinstance(
                            value.get("file"), str
                        ):
                            raise ValueError("Invalid native package: " + identifier)
                        value = {
                            **value,
                            "file": (index_path.parent / value["file"])
                            .relative_to(public)
                            .as_posix(),
                        }
                    elif key == "native_members":
                        if (
                            not isinstance(value, int)
                            or isinstance(value, bool)
                            or value < 1
                        ):
                            raise ValueError(
                                "Invalid native member count: " + identifier
                            )
                    elif not isinstance(value, str):
                        raise ValueError("Invalid model metadata: " + identifier)
                    metadata[key] = value
            cars.append(
                {
                    **metadata,
                    "id": identifier,
                    "game": game,
                    "file": model.relative_to(public).as_posix(),
                }
            )
    aliases = set()
    for car in cars:
        for alias in car.get("aliases", []):
            if alias in ids or alias in aliases:
                raise ValueError("Duplicate model alias: " + alias)
            aliases.add(alias)
    return {"cars": cars}


if __name__ == "__main__":
    catalog = model_catalog()
    (PUBLIC / "models.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"{len(catalog['cars'])} source entries -> {PUBLIC / 'models.json'}")
