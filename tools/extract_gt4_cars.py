#!/usr/bin/env python3
"""Extract Gran Turismo 4 native car files from GT4.VOL inside the supplied ISO.

Selection is a declared namespace boundary (car/, wheel/, tire/, wing/ and the
car spec database), not inferred runtime closure. --check derives every output
again from the ISO. No geometry or texture conversion.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile

from gt4_volume import Gt4Volume
from mc3_archive import CookedDisc, file_digest, safe_name

ROOT = Path(__file__).resolve().parents[1]
GAME = "Gran Turismo 4"
CODE = re.compile(r"[a-z0-9_]{8}")
# Per-car namespaces are joined on the eight-character model code in the file name.
CAR_PATHS = (
    ("car/lod/", "race-model"),
    ("car/menu/", "menu-model"),
    ("car/open/", "open-model"),
)
WHEEL_PATHS = (
    ("wheel/lod/", "race-wheel"),
    ("wheel/menu/", "menu-wheel"),
    ("wheel/open/", "open-wheel"),
)
SHARED = ("wheel/", "tire/", "wing/")
SPECDB = "specdb/"
EXCLUDED_SPECDB = "/RACES/"
LIMITS = [
    "Native volume extraction only; CAR4/MDLS model and Pat0 colour-patch decoding, GLB conversion and rendering remain unverified.",
    "Car IDs are eight-character model codes from car/lod file names, not decoded retail names or a verified playable roster.",
    "Wheels are assigned to a car only by an exact code match; other wheels, tires and wings are shared with ownership unknown.",
    "The spec database is retained as native tables; rows, names and car-to-model mappings are not decoded here.",
    "Selection is a declared namespace boundary; runtime dependency closure and load precedence are unknown.",
    "Checks establish byte extraction and source preservation, not game execution or visual fidelity.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def role(path, prefixes):
    for prefix, name in prefixes:
        if path.startswith(prefix) and "/" not in path[len(prefix) :]:
            return name
    return None


def car_code(record):
    name = record["name"]
    code = name[:-4] if name.endswith(".pat") else name
    if not CODE.fullmatch(code) or name not in (code, code + ".pat"):
        raise ValueError("unexpected car file name: " + record["path"])
    return code


def derive(iso, emit):
    """Emit one payload at a time; the 3 GB volume is never held in memory."""
    iso = Path(iso)
    source_pin = file_digest(iso)
    files, keys = [], set()

    def put(path, data, provenance=None):
        safe_name(path)
        if path.casefold() in keys:
            raise ValueError("duplicate output path")
        keys.add(path.casefold())
        emit(path, data)
        row = {"file": path, "bytes": len(data), "sha256": sha(data)}
        if provenance:
            row["source"] = provenance
        files.append(row)
        return row

    disc = CookedDisc(iso)
    try:
        by_path = {e["path"]: e for e in disc.entries}
        boot, entry = by_path.get("SYSTEM.CNF;1"), by_path.get("GT4.VOL;1")
        if boot is None or entry is None or boot["size"] > 4096:
            raise ValueError("GT4 boot configuration or volume missing")
        put("provenance/SYSTEM.CNF", disc.region(boot)(0, boot["size"]))
        volume = Gt4Volume(disc.region(entry), entry["size"])
        records = [r for r in volume.records if r["kind"] != "directory"]
        codes = sorted({car_code(r) for r in records if role(r["path"], CAR_PATHS[:1])})
        if not codes:
            raise ValueError("no car models found in car/lod")
        car_set = set(codes)
        cars = {code: [] for code in codes}

        def extract(record, target, extra):
            stored = volume.stored(record)
            data = volume.payload(record)
            provenance = {
                "volume_path": record["path"],
                "kind": record["kind"],
                "volume_offset": record["offset"],
                "iso_offset": entry["lba"] * 2048 + record["offset"],
                "stored_bytes": record["stored"],
                "stored_sha256": sha(stored),
                "modified": utc(record["modified"]),
                **extra,
            }
            return put(target, data, provenance)

        selected = 0
        for record in sorted(records, key=lambda r: r["path"]):
            path = record["path"]
            car_role = role(path, CAR_PATHS)
            wheel_role = role(path, WHEEL_PATHS)
            if car_role:
                code = car_code(record)
                if code not in car_set:
                    raise ValueError("car file without a car/lod model: " + path)
                kind = "colour-patch" if record["name"].endswith(".pat") else car_role
                cars[code].append(extract(record, code + "/" + path, {"role": kind}))
            elif wheel_role and record["name"] in car_set:
                cars[record["name"]].append(
                    extract(record, record["name"] + "/" + path, {"role": wheel_role})
                )
            elif path.startswith(SHARED):
                extract(
                    record, "shared/" + path, {"role": "shared-" + path.split("/")[0]}
                )
            elif path.startswith(SPECDB) and EXCLUDED_SPECDB not in path:
                extract(record, "provenance/" + path, {"role": "spec-database"})
            else:
                continue
            selected += 1
        vehicles = []
        for code in codes:
            roles = sorted({row["source"]["role"] for row in cars[code]})
            if not {"race-model", "colour-patch", "menu-model"} <= set(roles):
                raise ValueError(
                    "car is missing a race model, colour patch or menu model: " + code
                )
            manifest = {
                "id": code,
                "files": cars[code],
                "roles": roles,
                "claim_limits": LIMITS,
            }
            put(code + "/manifest.json", json_bytes(manifest))
            vehicles.append(
                {
                    "id": code,
                    "manifest": code + "/manifest.json",
                    "files": len(cars[code]),
                    "bytes": sum(row["bytes"] for row in cars[code]),
                    "roles": roles,
                }
            )
        inventory = {
            "iso_entry": entry,
            "table_offset": volume.toc_offset,
            "encrypted": volume.encrypted,
            "table_pages": volume.table_pages,
            "index_pages": volume.index_pages,
            "data_offset": volume.data_offset,
            "records": [
                {
                    k: r[k]
                    for k in ("path", "kind", "page", "stored", "size", "modified")
                    if k in r
                }
                for r in volume.records
            ],
            "claim_limits": [
                "Complete RoFS table listing; only selected namespaces are extracted."
            ],
        }
        put("provenance/GT4.VOL.inventory.json", json_bytes(inventory))
        if file_digest(iso) != source_pin:
            raise ValueError("disc changed during extraction")
        index = {
            "schema": 1,
            "game": GAME,
            "source": {
                "file": iso.name,
                "bytes": disc.size,
                "sha256": source_pin,
                "volume": disc.volume,
                "boot": "SCES_517.19",
            },
            "iso_inventory": disc.entries,
            "volume": {
                "file": "GT4.VOL",
                "iso_lba": entry["lba"],
                "bytes": entry["size"],
                "table_offset": volume.toc_offset,
                "records": len(volume.records),
                "selected_files": selected,
            },
            "selection": {
                "per_car": [p for p, _ in CAR_PATHS + WHEEL_PATHS],
                "shared": list(SHARED),
                "provenance": [SPECDB + " (excluding RACES/)", "SYSTEM.CNF"],
            },
            "vehicles": vehicles,
            "files": files.copy(),
            "claim_limits": LIMITS,
        }
        put("index.json", json_bytes(index))
        return index, files
    finally:
        disc.close()


def output_files(destination):
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("missing or linked extraction destination")
    found = set()
    for path in destination.rglob("*"):
        if path.is_symlink():
            raise ValueError("linked extraction output")
        if path.is_file():
            found.add(path.relative_to(destination).as_posix())
    return found


def check_extraction(iso, destination):
    destination = Path(destination)
    found = output_files(destination)
    expected = set()

    def compare(relative, data):
        expected.add(relative)
        path = destination / relative
        if relative not in found:
            raise ValueError("extraction file coverage mismatch: missing " + relative)
        if path.stat().st_size != len(data) or file_digest(path) != sha(data):
            raise ValueError("extraction byte mismatch: " + relative)

    index, files = derive(iso, compare)
    if expected != found:
        raise ValueError("extraction file coverage mismatch: extra files")
    return index, files


def write_extraction(iso, destination):
    destination = Path(destination)
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise ValueError("linked extraction destination")
    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise ValueError("destination must be absent or empty")
    if Path(iso).resolve().is_relative_to(destination.resolve()):
        raise ValueError("input is inside destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="gt4-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp) / "cars"
        stage.mkdir()

        def emit(relative, data):
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)

        index, files = derive(iso, emit)
        if destination.exists():
            destination.rmdir()  # Proven empty; no existing content removed.
        stage.rename(destination)
    return index, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iso",
        type=Path,
        default=ROOT
        / "games/gran-turismo-4/game-files/Gran Turismo 4 (axekin.com).iso",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "games/gran-turismo-4/cars"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        index, files = (check_extraction if args.check else write_extraction)(
            args.iso, args.output
        )
        print(
            f"{'CHECKED' if args.check else 'EXTRACTED'} {len(index['vehicles'])} cars, "
            f"{len(files)} files, {sum(f['bytes'] for f in files)} bytes"
        )
    except (ValueError, OSError) as error:
        print("ERROR:", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
