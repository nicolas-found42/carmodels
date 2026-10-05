#!/usr/bin/env python3
"""T3 — resolve the three captured VEHICLE labels from the language archive.

Reads each captured car's INGAME_TEXT_ENUM from the reference CARDATA block, then
resolves it through the game's LANGUAGE/tlate_en.dat;1 (UTF-16-LE, keys TXT_CARS_*)
in code, and asserts the resolved string equals the on-screen VEHICLE label.
The apostrophe is taken byte-exact from the archive (raw UTF-16 bytes must appear
verbatim in the archive), never from a vision transcript.

Scope: the three captured pairs only (slot102/103/104). No 136-entry table.

Receipt: research/evidence/vehicle-completeness/t3-display-name-resolution-validation.json
bridge-three-screens.json is updated with the resolved rows ONLY when all three pass.
Exit 0 + "VERIFY OK" only on pass.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_reference as B  # reuse the exact tlate parser + paths

CORPUS = ROOT / "reference/ford"
TLATE = B.SRC / "LANGUAGE/tlate_en.dat;1"
BRIDGE = ROOT / "research/evidence/carselection-2026-10-05/bridge-three-screens.json"
OUT = ROOT / "research/evidence/vehicle-completeness/t3-display-name-resolution-validation.json"
FULL_OUT = ROOT / "research/evidence/vehicle-completeness/full-display-name-table.json"


def parse_tlate(data: bytes) -> dict:
    """Same parse as build_reference.py: UTF-16-LE, TXT_CARS_* lines."""
    text = data.decode("utf-16-le", "replace")
    txt = {}
    for line in text.split("\r\n"):
        line = line.strip("\ufeff").strip()
        if line.startswith("TXT_CARS_") and " " in line:
            k, v = line.split(" ", 1)
            txt[k] = v.strip()
    return txt


def cardata_enum(car_type: str):
    """INGAME_TEXT_ENUM for a car from its extracted reference CARDATA block."""
    path = CORPUS / "cars" / car_type / "config/cardata.txt"
    if not path.is_file():
        raise ValueError(f"missing reference cardata for {car_type}")
    block = path.read_bytes()
    m = re.search(rb"(?m)^:INGAME_TEXT_ENUM[ \t]+(\S+)[ \t]*\r?$", block)
    return m.group(1).decode() if m else None


def check():
    if not TLATE.is_file():
        raise ValueError(f"language archive missing: {TLATE}")
    raw = TLATE.read_bytes()
    txt = parse_tlate(raw)
    bridge = json.loads(BRIDGE.read_text())
    screens = bridge["screens"]

    rows = []
    for s in screens:
        car_type = s["car_type"]
        expected_enum = s["ingame_text_enum"]
        label = s["vehicle"]

        enum = cardata_enum(car_type)
        if enum != expected_enum:
            raise ValueError(f"{car_type}: CARDATA enum {enum!r} != bridge enum {expected_enum!r}")
        resolved = txt.get(enum)
        if resolved is None:
            raise ValueError(f"{car_type}: key {enum} absent from tlate_en archive")
        if resolved != label:
            raise ValueError(f"{car_type}: resolved {resolved!r} != VEHICLE label {label!r}")
        # byte-exact: the raw UTF-16-LE bytes of the resolved string must occur verbatim
        needle = resolved.encode("utf-16-le")
        if needle not in raw:
            raise ValueError(f"{car_type}: resolved string bytes not verbatim in archive")
        rows.append({
            "capture": s["capture"],
            "car_type": car_type,
            "ingame_text_enum": enum,
            "resolved_string": resolved,
            "vehicle_label_on_screen": label,
            "labels_equal": True,
            "utf16le_bytes_hex": needle.hex(),
            "apostrophe_raw_0x27_present": (b"\x27\x00" in needle),
            "archive_verbatim": True,
            "pass": True,
        })

    result = {
        "archive_path": str(TLATE.relative_to(B.SRC)),
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "archive_bytes": len(raw),
        "encoding": "utf-16-le",
        "pairs": len(rows),
        "rows": rows,
        "all_pairs_pass": all(r["pass"] for r in rows),
    }

    # ---- negative controls ----
    # NC1 a label lacking the archive's apostrophe must NOT equal the resolution
    wrong = rows[0]["resolved_string"].replace("'", "")
    if wrong == rows[0]["resolved_string"]:
        raise ValueError("control setup: expected an apostrophe in the resolved string")
    result["control_apostrophe_stripped_label_rejected"] = (wrong != rows[0]["resolved_string"])

    # NC2 a wrong archive key must not resolve to the label
    bogus = txt.get("TXT_CARS_NOT_A_REAL_KEY")
    result["control_unknown_key_unresolved"] = (bogus is None)

    # NC3 CARDATA enum must actually be the bridge enum (guards a silent remap)
    result["control_enum_matches_cardata"] = all(
        cardata_enum(r["car_type"]) == r["ingame_text_enum"] for r in rows)
    return result, bridge, raw


def corpus_enum(car_type: str):
    """INGAME_TEXT_ENUM for a car from its extracted reference CARDATA block."""
    path = CORPUS / "cars" / car_type / "config/cardata.txt"
    if not path.is_file():
        raise ValueError(f"missing reference cardata for {car_type}")
    m = re.search(rb"(?m)^:INGAME_TEXT_ENUM[ \t]+(\S+)[ \t]*\r?$", path.read_bytes())
    return m.group(1).decode() if m else None


def check_full_table(raw: bytes, txt: dict):
    """Every car in the corpus resolves its CARDATA enum through the archive, byte-exact.

    The car-keyed display-name table: all 35 cars, not the three captured pairs.
    """
    cars = sorted(json.loads((CORPUS / "inventory.json").read_text())["cars"])
    rows = []
    for code in cars:
        enum = corpus_enum(code)
        if enum is None:
            raise ValueError(f"{code}: no INGAME_TEXT_ENUM in reference CARDATA")
        s = txt.get(enum)
        if s is None:
            raise ValueError(f"{code}: enum {enum} absent from tlate_en archive")
        if s.encode("utf-16-le") not in raw:
            raise ValueError(f"{code}: resolved string bytes not verbatim in archive")
        rows.append({"car_type": code, "ingame_text_enum": enum, "resolved_string": s,
                     "archive_verbatim": True, "pass": True})
    if len(rows) != 35:
        raise ValueError(f"car-keyed table has {len(rows)} rows, expected 35")
    return {"rows": len(rows), "car_keyed_table": rows,
            "all_35_pass": all(r["pass"] for r in rows)}


def main() -> int:
    result, bridge, raw = check()
    txt = parse_tlate(raw)
    full = check_full_table(raw, txt)
    result["full_car_keyed_table"] = full
    result["control_full_unknown_key_unresolved"] = (txt.get("TXT_CARS_UNKNOWN_KEY_XYZ") is None)
    ap = next((r for r in full["car_keyed_table"] if "'" in r["resolved_string"]), None)
    result["control_full_apostrophe_present_and_byte_exact"] = (
        ap is not None and ap["resolved_string"].replace("'", "") != ap["resolved_string"]
        and ap["resolved_string"].encode("utf-16-le") in raw)

    ok = (result["all_pairs_pass"]
          and result["control_apostrophe_stripped_label_rejected"]
          and result["control_unknown_key_unresolved"]
          and result["control_enum_matches_cardata"]
          and full["all_35_pass"]
          and result["control_full_unknown_key_unresolved"]
          and result["control_full_apostrophe_present_and_byte_exact"])

    if ok:
        # update bridge only on pass; idempotent (replace, not append)
        by_capture = {r["capture"]: r for r in result["rows"]}
        for s in bridge["screens"]:
            r = by_capture[s["capture"]]
            s["display_name_resolution"] = {
                "archive_path": result["archive_path"],
                "archive_sha256": result["archive_sha256"],
                "key": r["ingame_text_enum"],
                "resolved_string": r["resolved_string"],
                "matches_vehicle_label": True,
                "utf16le_bytes_hex": r["utf16le_bytes_hex"],
                "apostrophe_raw_0x27_present": r["apostrophe_raw_0x27_present"],
            }
        bridge["display_name_resolution_summary"] = {
            "method": "LANGUAGE/tlate_en.dat;1 UTF-16-LE keys resolved in code; apostrophe byte-exact from archive",
            "pairs": result["pairs"],
            "all_pass": True,
            "archive_sha256": result["archive_sha256"],
        }
        BRIDGE.write_text(json.dumps(bridge, indent=1) + "\n")
        result["bridge_updated"] = True
    else:
        result["bridge_updated"] = False

    result["result"] = "VERIFY OK" if ok else "VERIFY FAILED"
    result["scope"] = ("three captured pairs (T3 regression) + full car-keyed display-name table (35 cars); "
                       "no 136-entry table")
    result["render_fidelity_complete"] = False
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    FullReceipt = {"archive_path": result["archive_path"], "archive_sha256": result["archive_sha256"],
                   "archive_bytes": result["archive_bytes"], "encoding": result["encoding"],
                   "rows": full["rows"], "car_keyed_table": full["car_keyed_table"],
                   "all_35_pass": full["all_35_pass"], "result": result["result"],
                   "scope": "car-keyed display-name table (all 35 cars); T3 three-pair claim preserved separately",
                   "render_fidelity_complete": False}
    FULL_OUT.write_text(json.dumps(FullReceipt, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(result["result"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
