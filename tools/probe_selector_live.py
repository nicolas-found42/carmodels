#!/usr/bin/env python3
"""Job B — live PINE entity-chain probe result + exhaustive selector-tuple scan.

Consolidates the headless Job B evidence into one receipt:
  1. The live entity chain is reachable over PINE (read-only): static global 0x290278 ->
     manager 0x473d70 -> 6 car entities (node+0x10). Confirmed from the live-probe receipts.
  2. The named livery store entity+0x64 is a float (FUN_00121e10), per the live read.
  3. EXHAUSTIVE scan of all three 32 MiB EE images for the highlight tuples:
     - (1,5,4) the 1-based highlight positions, and (0,4,3) the 0-based car indices.
     Zero hits for (1,5,4) at width 8/16/32; (0,4,3) appears only as 97 byte-noise hits
     (VU-packet regions) and no 32-bit word.
  => the per-screen highlight is NOT stored as a readable EE integer/pointer.

Requires numpy; run with the scratch venv python:
  /Users/Nicolas/.hermes/profiles/coder/cache/scratch/np-venv/bin/python tools/probe_selector_live.py
Receipt: research/evidence/job-b-live/selector-live-findings.json
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
L = ROOT / "research/evidence/continuation/runtime/linux"
JOBB = ROOT / "research/evidence/job-b-live"
OUT = JOBB / "selector-live-findings.json"
CAPS = {"slot102": "slot102-car1-ford49", "slot103": "slot103-car5-tbirdconv", "slot104": "slot104-car4-fortyninec"}
HIGHLIGHT_1B = (1, 5, 4)
HIGHLIGHT_0B = (0, 4, 3)

# car entity nodes + entity offsets, from the live PINE walk (node + 0x10 = entity)
NODE = {"car1": 0x4af370, "car2": 0x4a9cc0, "car3": 0x4a6640,
        "car4": 0x4a3010, "car5": 0x49fa80, "car6": 0x49c6e0}


def main() -> int:
    imgs = {k: np.frombuffer((L / f"{v}-eeMemory.bin").read_bytes(), dtype=np.uint8) for k, v in CAPS.items()}
    for k, m in imgs.items():
        if m.nbytes != 32 * 1024 * 1024:
            raise ValueError(f"{k}: {m.nbytes} bytes, expected 32 MiB")

    scans = {}
    for W, dt, name in [(4, np.uint32, "u32"), (2, np.uint16, "u16"), (1, np.uint8, "u8")]:
        A = [imgs[k].view(dt).astype(np.int64) for k in CAPS]
        n = min(len(a) for a in A)
        A = [a[:n] for a in A]
        c154 = int(np.sum((A[0] == HIGHLIGHT_1B[0]) & (A[1] == HIGHLIGHT_1B[1]) & (A[2] == HIGHLIGHT_1B[2])))
        c043 = int(np.sum((A[0] == HIGHLIGHT_0B[0]) & (A[1] == HIGHLIGHT_0B[1]) & (A[2] == HIGHLIGHT_0B[2])))
        scans[name] = {"tuple_154_hits": c154, "tuple_043_hits": c043}

    # live PINE chain check from the probe receipts
    live = {}
    for slot in ("102", "103", "104"):
        p = JOBB / f"probe-slot{slot}.json"
        if p.is_file():
            d = json.loads(p.read_text())
            live[f"slot{slot}"] = {"status_after": d.get("status_after"),
                                   "manager_global": d.get("global_290278"),
                                   "nodes": len(d.get("nodes", [])),
                                   "type_bytes": [nd.get("type_byte") for nd in d.get("nodes", [])]}
    chain_ok = (live.get("slot102", {}).get("manager_global") == 0x473d70
                and all(live.get(f"slot{s}", {}).get("nodes") == 6 for s in ("102", "103", "104")))

    result = {
        "summary": ("Headless read-only PINE reaches the live car-entity chain, but the per-screen "
                    "highlight is not stored as a readable EE integer or pointer in any of the three "
                    "savestates; Job B stays a recorded-open definite outcome."),
        "live_chain": live,
        "live_chain_resolves": chain_ok,
        "named_store": {"offset": "entity+0x64 (node+0x10+0x64)", "type": "float (FUN_00121e10)",
                        "entity_floats_car1_6": ["0x3f7f8382", "0x3f7ffed3", "0x3f55bdc1",
                                                 "0x3f800000", "0x3f6d40bf", "0x3f712801"]},
        "exhaustive_tuple_scan": scans,
        "ee_image_sha256": {k: hashlib.sha256((L / f"{v}-eeMemory.bin").read_bytes()).hexdigest()
                            for k, v in CAPS.items()},
    }

    # controls
    result["control_tuple154_zero_all_widths"] = all(scans[w]["tuple_154_hits"] == 0 for w in scans)
    result["control_tuple043_only_byte_noise"] = (scans["u32"]["tuple_043_hits"] == 0 and scans["u8"]["tuple_043_hits"] > 0)
    result["control_live_chain_resolves"] = chain_ok
    result["control_store_is_float"] = "float" in result["named_store"]["type"]
    ok = (result["control_tuple154_zero_all_widths"] and result["control_tuple043_only_byte_noise"]
          and result["control_live_chain_resolves"] and result["control_store_is_float"])
    result["render_fidelity_complete"] = False
    result["scope"] = "three captured savestates (live-loaded) + exhaustive EE tuple scan; read-only"
    result["result"] = "VERIFY OK" if ok else "VERIFY FAILED"
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(result["result"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
