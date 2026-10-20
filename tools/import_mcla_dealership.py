#!/usr/bin/env python3
"""Add verified Midnight Club: Los Angeles previews as independent editable dealership models.

Existing catalog entries and models are preserved, including later edits. Exact UI string names
are retained; unsupported retail identities, years, performance and body styles stay unknown.
"""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from bake_models import ROOT, bake_car, read_glb
from import_mcla_catalog import GAME, LIMITS, regular, source_package

GAME_LABEL = "Midnight Club: Los Angeles"
SPECDB = ROOT / "games/gran-turismo-4/cars/provenance/specdb/MCLA_EU2560"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def editable_code(source_code):
    return "MCLA_" + source_code.upper()


def entry_for(row):
    return dict(
        code=editable_code(row["code"]),
        name=row["display_name"],
        game=GAME,
        gameLabel=GAME_LABEL,
        sourceCode=row["code"],
        sourceCollection="stock",
        sourceVariant="stock",
        displayMode="textured-glb",
        bodyStyle="unknown",
        group="STOCK",
        year=None,
        topSpeed=None,
        bhp=None,
        kg=None,
        agility=None,
        accel=None,
        speed=None,
        weight=None,
        liveries=[],
        paint=None,
        sound=None,
        claimLimits=[
            "Exact UI string names or source-code fallbacks; retail year, manufacturer and performance remain unknown.",
            "Independent editable copy; native source files remain separate.",
            *LIMITS,
        ],
    )


def import_cars(
    source=ROOT / "dealership/public" / GAME,
    destination=ROOT / "dealership/dealership",
    upgrade_unedited=False,
):
    source, destination = Path(source), Path(destination)
    if (
        source.resolve() == destination.resolve()
        or source.resolve() in destination.resolve().parents
        or destination.resolve() in source.resolve().parents
    ):
        raise ValueError("Source and editable destination must be separate directories")
    catalog_path, origins_path = (
        destination / "catalog.json",
        destination / "origins.json",
    )
    if any(
        any(q.is_symlink() for q in (p, *p.parents))
        for p in (destination, catalog_path, origins_path, destination / "models")
    ):
        raise ValueError("Editable dealership paths must not be symlinks")
    catalog = json.loads(catalog_path.read_text())
    origins = json.loads(origins_path.read_text())
    if (
        not isinstance(catalog, list)
        or not catalog
        or origins.get("schema") != 1
        or not isinstance(origins.get("cars"), list)
    ):
        raise ValueError("Existing editable dealership catalog/origins are invalid")
    existing = {car["code"]: car for car in catalog}
    origin_entries = {row["code"]: row for row in origins["cars"]}
    if len(existing) != len(catalog) or len(origin_entries) != len(origins["cars"]):
        raise ValueError("Existing editable codes are duplicated")
    regular(source / "index.json")
    rows = json.loads((source / "index.json").read_text()).get("cars")
    if not isinstance(rows, list) or not rows:
        raise ValueError("MCLA source index has no cars")
    added, payloads, upgraded, seen = [], [], 0, set()
    for row in rows:
        data = source_package(row, source)
        entry = entry_for(row)
        code = entry["code"]
        if code in seen:
            raise ValueError("MCLA editable identifiers collide")
        seen.add(code)
        bake_car(
            code, data, source_mode=False
        )  # Validate even on a preserving repeat import.
        target = destination / "models" / f"{code}.glb"
        record = {
            "game": GAME,
            "code": row["code"],
            "glb": f"public/{GAME}/" + row["file"],
            "sha256": row["sha256"],
        }
        if code in existing:
            old = existing[code]
            if old.get("game") != GAME or old.get("sourceCode") != row["code"]:
                raise ValueError(
                    "MCLA identifier conflicts with an existing dealership entry"
                )
            if target.is_symlink() or target.stat().st_nlink != 1:
                raise ValueError("Editable MCLA model path is invalid")
            origin = origin_entries.get(code)
            recorded = (
                origin.get("latestSource", origin.get("initialSource", {}))
                if origin
                else {}
            )
            if recorded.get("game") != GAME or recorded.get("code") != row["code"]:
                raise ValueError("Editable MCLA source provenance conflicts")
            if not upgrade_unedited:
                continue
            working = target.read_bytes()
            origin = origin_entries.get(code)
            previous = (
                origin.get("latestSource", origin.get("initialSource", {}))
                if origin
                else {}
            )
            # Only an exact copy of its recorded source may be upgraded; edits stay with the dealership.
            if sha(working) != previous.get("sha256") or sha(working) == row["sha256"]:
                continue
            if (
                origin is None
                or previous.get("game") != GAME
                or previous.get("code") != row["code"]
            ):
                raise ValueError("Editable MCLA source provenance conflicts")
            read_glb(working)
            payloads.append((target, data, working))
            origin.setdefault("sourceUpgrades", []).append(
                {"fromSha256": previous["sha256"], "toSha256": row["sha256"]}
            )
            origin["latestSource"] = record
            upgraded += 1
            continue
        if code in origin_entries or target.exists() or target.is_symlink():
            raise ValueError(
                "An uncatalogued dealership model occupies the MCLA identifier"
            )
        added.append(entry)
        payloads.append((target, data, None))
        origins["cars"].append({"code": code, "initialSource": record})
    if not added and not upgraded:
        return 0
    (destination / "models").mkdir(exist_ok=True)
    original_catalog, original_origins = (
        catalog_path.read_bytes(),
        origins_path.read_bytes(),
    )
    # Stage every copy and metadata before touching the working dealership.
    with tempfile.TemporaryDirectory(
        prefix=".mcla-import-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        for target, data, _ in payloads:
            (stage / target.name).write_bytes(data)
        (stage / "catalog.json").write_text(
            json.dumps(catalog + added, indent=1) + "\n"
        )
        (stage / "origins.json").write_text(json.dumps(origins, indent=1) + "\n")
        moved = []
        try:
            for target, _, previous_data in payloads:
                (stage / target.name).replace(target)
                moved.append((target, previous_data))
            (stage / "origins.json").replace(origins_path)
            (stage / "catalog.json").replace(catalog_path)
        except BaseException:
            catalog_path.write_bytes(original_catalog)
            origins_path.write_bytes(original_origins)
            for target, previous_data in moved:
                if previous_data is None:
                    target.unlink()
                else:
                    target.write_bytes(previous_data)
            raise
    return len(added) + upgraded


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=ROOT / "dealership/public" / GAME
    )
    parser.add_argument(
        "--destination", type=Path, default=ROOT / "dealership/dealership"
    )
    parser.add_argument(
        "--upgrade-unedited",
        action="store_true",
        help="Refresh only models equal to their recorded source; preserve edited models",
    )
    args = parser.parse_args()
    try:
        count = import_cars(args.source, args.destination, args.upgrade_unedited)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")
    print(
        f"Imported {count} independent editable Midnight Club: Los Angeles models; existing dealership entries preserved"
    )
