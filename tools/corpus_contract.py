"""Identity and full input accounting for the issue #2 PAL corpus."""

import csv
import hashlib
import json
from pathlib import Path
from evidence_common import Invalid, Incomplete, identity
from format_contracts import archive, bank, model, sprite

BASELINE = {
    "ford-racing-2.bin": (
        678667248,
        "ae8d5a32c9d832f34a08fad6f0e97ce6e89e6b040597011f6362d886145b9d3d",
    ),
    "ford-racing-2.cue": (
        79,
        "c2e0aaf75a43150567f4ffe02ac863c8d1bda8f2fdf744012361436ec582edb6",
    ),
    "extracted/SLES_517.05": (
        1662804,
        "216711210898aee296eed73d0776e7f733bac04c334002683bce769c86beea95",
    ),
    "extracted/FILES.HDR": (
        29428,
        "f4e4a4f91cd89bcaa8c2772e6cba2a839d92fbe222290c8c751777a81963731d",
    ),
    "extracted/FILES.DAT": (
        334641152,
        "357fc371f47e366bf507b721e26eed9f1205516c19b793e0316ccecc2175a722",
    ),
}


OS_METADATA_NAME = ".DS_Store"


def corpus_identity(game: Path) -> dict:
    identities = {name: identity(game / name) for name in BASELINE}
    for name, (size, digest) in BASELINE.items():
        if identities[name] != {"bytes": size, "sha256": digest}:
            raise Invalid(f"changed corpus input: {name}")
    return {
        "profile": "fr2-pal-sles-517.05",
        "sources": identities,
        "corpus_id": hashlib.sha256(
            json.dumps(identities, sort_keys=True).encode()
        ).hexdigest(),
    }


def coverage(game: Path, manifest: Path) -> dict:
    provenance = corpus_identity(game)
    ex = game / "extracted"
    files = ex / "files"
    if not files.is_dir():
        raise Incomplete("missing extracted files directory")
    result = archive((ex / "FILES.HDR").read_bytes(), (ex / "FILES.DAT").read_bytes())
    failures = []
    expected_counts = {
        "segments": 48,
        "records": 1037,
        "files": 990,
        "raw": 386,
        "zlib": 604,
    }
    if result["counts"] != expected_counts:
        failures.append(f"archive counts differ: {result['counts']}")
    on_disk = sorted(p for p in files.rglob("*") if p.is_file())
    # Finder writes these into any browsed folder; they are never archive members.
    # Only this exact basename is excluded, and every exclusion stays in the result.
    ignored = [
        {"path": p.relative_to(files).as_posix(), **identity(p)}
        for p in on_disk
        if p.name == OS_METADATA_NAME
    ]
    discovered = [p for p in on_disk if p.name != OS_METADATA_NAME]
    actual_paths = {p.relative_to(files).as_posix(): p for p in discovered}
    expected_paths = {f["path"].lstrip("/"): f for f in result["files"]}
    for path in sorted(actual_paths.keys() ^ expected_paths.keys()):
        failures.append(f"extraction path missing or additional: {path}")
    with manifest.open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    manifest_rows = {row["path"].lstrip("/"): row for row in rows}
    if len(rows) != 990 or set(manifest_rows) != set(expected_paths):
        failures.append("manifest does not cover exactly the archive file paths")
    extraction = []
    for name, record in expected_paths.items():
        path = actual_paths.get(name)
        if path is None:
            continue
        raw = path.read_bytes()
        observed = identity(path)
        if observed != {
            "bytes": record["output_bytes"],
            "sha256": record["output_sha256"],
        }:
            failures.append(
                f"extracted output differs from independent archive read: {name}"
            )
        row = manifest_rows.get(name)
        if row is not None and (
            int(row["idx"]) != record["idx"]
            or int(row["chunk"]) != record["u1"]
            or int(row["stored_bytes"]) != record["u2"]
            or row["status"] != "ok(" + record["classification"] + ")"
            or int(row["out_bytes"]) != len(raw)
            or row["sha1_16"] != hashlib.sha1(raw).hexdigest()[:16]
        ):
            failures.append(f"legacy manifest differs: {name}")
        extraction.append({"path": name, **observed})
    families = {"banks": [], "models": [], "ptg": []}
    gears = json.loads(Path(__file__).with_name("gear_pixels.json").read_text())
    seen_gears = set()
    for name, path in actual_paths.items():
        suffix = path.name.split(";")[0].rsplit(".", 1)[-1].lower()
        if suffix not in {"msh", "msb", "ps2", "ptg"}:
            continue
        if suffix == "msb":
            pair = path.with_name(path.name.replace(".msb;", ".msh;"))
            if not pair.exists():
                failures.append(f"orphan bank payload: {name}")
            continue
        entry = {"path": name, **identity(path)}
        target = {"msh": "banks", "ps2": "models", "ptg": "ptg"}[suffix]
        try:
            if suffix == "msh":
                payload = path.with_name(path.name.replace(".msh;", ".msb;"))
                entry["contract"] = bank(path.read_bytes(), payload.read_bytes())
                entry["paired_payload"] = identity(payload)
            elif suffix == "ps2":
                entry["contract"] = model(path.read_bytes())
            else:
                entry["contract"] = sprite(path.read_bytes())
                if path.name in gears:
                    seen_gears.add(path.name)
                    expected = gears[path.name]
                    if any(
                        entry["contract"][key] != expected[key]
                        for key in ["width", "height", "pixel_sha256"]
                    ):
                        failures.append(f"gear pixel regression: {name}")
                    entry["meaning"] = expected["meaning"]
            entry["status"] = "supported"
        except (Invalid, FileNotFoundError) as exc:
            entry.update(
                status="unsupported"
                if suffix == "ptg" and path.name not in gears
                else "fail",
                diagnostic=str(exc),
            )
            if entry["status"] == "fail":
                failures.append(f"{name}: {exc}")
        families[target].append(entry)
    for family, count in [("banks", 27), ("models", 56), ("ptg", 548)]:
        if len(families[family]) != count:
            failures.append(
                f"{family}: expected {count}, discovered {len(families[family])}"
            )
    if seen_gears != set(gears):
        failures.append(
            f"missing supported gear sprites: {sorted(set(gears) - seen_gears)}"
        )
    return {
        "provenance": provenance,
        "archive": result,
        "extracted_files": extraction,
        "families": families,
        "counts": {
            **result["counts"],
            **{k: len(v) for k, v in families.items()},
            "discovered_files": len(discovered),
        },
        "ignored_os_metadata": ignored,
        "unsupported_ptg": sum(p["status"] == "unsupported" for p in families["ptg"]),
        "failures": failures,
    }
