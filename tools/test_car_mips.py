#!/usr/bin/env python3
"""Positive, negative and boundary checks for the car mip recovery artifacts."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools/validate_car_mips.py"
EVIDENCE = ROOT / "research/evidence/mip-continuation"


def run_validator(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), "--output-dir", str(output_dir)],
                          text=True, capture_output=True, check=False)


def prepare(target: Path) -> None:
    shutil.copytree(EVIDENCE, target)


def main() -> None:
    cases = []
    with tempfile.TemporaryDirectory(prefix="fr2-car-mips-check-") as tmp:
        root = Path(tmp)
        good = root / "positive"
        prepare(good)
        result = run_validator(good)
        if result.returncode != 0:
            raise AssertionError(f"positive corpus failed: {result.stderr}")
        positive = json.loads((good / "validation.json").read_text())
        if positive["checked_extra_mip_levels"] != 94 or positive["independently_decoded_pngs"] != 94:
            raise AssertionError("positive corpus counts differ")
        cases.append({"case": "unaltered complete corpus", "result": "accepted"})

        bad_hash = root / "bad-hash"
        prepare(bad_hash)
        index_path = bad_hash / "mip-index.json"
        index = json.loads(index_path.read_text())
        index["cars"][0]["extra_mip_levels"][0]["source_sha256"] = "0" * 64
        index_path.write_text(json.dumps(index))
        result = run_validator(bad_hash)
        if result.returncode == 0 or "exported plane differs" not in result.stderr:
            raise AssertionError("source-hash corruption was not rejected")
        cases.append({"case": "mutated source-plane hash", "result": "rejected"})

        bad_png = root / "bad-png"
        prepare(bad_png)
        index = json.loads((bad_png / "mip-index.json").read_text())
        first_png = bad_png / index["cars"][0]["extra_mip_levels"][0]["png"]
        png = bytearray(first_png.read_bytes())
        cursor = 8
        while cursor < len(png):
            size = int.from_bytes(png[cursor:cursor + 4], "big")
            kind = bytes(png[cursor + 4:cursor + 8])
            if kind == b"IDAT":
                png[cursor + 8 + size // 2] ^= 0x01
                break
            cursor += 12 + size
        else:
            raise AssertionError("generated PNG has no IDAT chunk")
        first_png.write_bytes(png)
        result = run_validator(bad_png)
        if result.returncode == 0 or "PNG CRC mismatch" not in result.stderr:
            raise AssertionError("PNG CRC corruption was not rejected")
        cases.append({"case": "mutated PNG payload", "result": "rejected"})

        bad_offset = root / "bad-offset"
        prepare(bad_offset)
        index = json.loads((bad_offset / "mip-index.json").read_text())
        index["cars"][0]["extra_mip_levels"][0]["source_file_offset"] = -1
        (bad_offset / "mip-index.json").write_text(json.dumps(index))
        result = run_validator(bad_offset)
        if result.returncode == 0 or "source span mismatch" not in result.stderr:
            raise AssertionError("negative source boundary was not rejected")
        cases.append({"case": "negative source-file offset", "result": "rejected"})

        result_doc = {"schema_version": 1, "status": "pass", "cases": cases,
                      "test_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "scope": "The unaltered corpus passes; three copied-artifact mutations are rejected by the validator.",
                      "note": "Negative controls ran in temporary copies and did not modify the exported evidence."}
        (EVIDENCE / "negative-controls.json").write_text(json.dumps(result_doc, indent=2) + "\n")
        print(json.dumps(result_doc, indent=2))


if __name__ == "__main__":
    main()
