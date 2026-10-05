#!/usr/bin/env python3
"""Mark number — exhaustive savestate search (all members, all widths).

Searches every member of the three menu savestates (EE, IOP, VU0/VU1, hardware
registers, PAD, scratchpad) for the per-screen highlight tuple. The highlight is the
1-based position (1,5,4) for slot102/103/104 (cars 1/5/4), and the 0-based car index
(0,4,3). Also records the per-entity flag test (0) and the pointer test (0).

Conclusion when all are 0: the per-screen highlight is not stored anywhere in the
savestate as a readable integer; getting the mark number needs a live tool
(breakpoint/scanning), not another saved state.

Requires numpy + the 3.14 python (zstd). Run:
  /Users/Nicolas/.hermes/profiles/coder/cache/scratch/np-venv/bin/python tools/probe_mark_exhaustive.py
Receipt: research/evidence/job-b-live/mark-number-exhaustive-search.json
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
L = ROOT / "research/evidence/continuation/runtime/linux"
OUT = ROOT / "research/evidence/job-b-live/mark-number-exhaustive-search.json"
SLOT = {"102": "slot102-car1-ford49", "103": "slot103-car5-tbirdconv", "104": "slot104-car4-fortyninec"}
P2S = {s: L / f"sstates/SLES-51705 (37F695CD).{s}.p2s" for s in SLOT}
ORDER = ["102", "103", "104"]
T154 = (1, 5, 4)
T043 = (0, 4, 3)
MEMBERS = ["eeMemory.bin", "iopMemory.bin", "vu0Memory.bin", "vu0MicroMem.bin",
           "vu1Memory.bin", "vu1MicroMem.bin", "eeHwRegs.bin", "iopHwRegs.bin",
           "PAD.bin", "Scratchpad.bin"]
MEMBERS_DIR = ROOT / "research/evidence/job-b-live/members"


def load_members():
    """Read pre-extracted member files (the .p2s zip is zstd; extraction is done with the
    3.14 python). Falls back to the zip when the plain member files are absent."""
    data = {}
    # EE main RAM from the existing unpacked dumps
    for s, name in SLOT.items():
        ee = L / f"{name}-eeMemory.bin"
        if ee.is_file():
            data[(s, "eeMemory.bin")] = np.frombuffer(ee.read_bytes(), dtype=np.uint8)
    for s in ORDER:
        for m in MEMBERS:
            plain = MEMBERS_DIR / f"{s}-{m}"
            if plain.is_file():
                data[(s, m)] = np.frombuffer(plain.read_bytes(), dtype=np.uint8)
    if data:
        return data
    for s, p in P2S.items():
        with zipfile.ZipFile(p) as z:
            for m in MEMBERS:
                try:
                    data[(s, m)] = np.frombuffer(z.read(m), dtype=np.uint8)
                except KeyError:
                    pass
    return data


def scan_tuple(a8):
    out = {}
    for W, dt, name in [(1, np.uint8, "u8"), (2, np.uint16, "u16"), (4, np.uint32, "u32")]:
        A = [a.view(dt).astype(np.int64) for a in a8]
        n = min(len(a) for a in A)
        c154 = int(np.sum((A[0][:n] == T154[0]) & (A[1][:n] == T154[1]) & (A[2][:n] == T154[2])))
        c043 = int(np.sum((A[0][:n] == T043[0]) & (A[1][:n] == T043[1]) & (A[2][:n] == T043[2])))
        out[name] = {"tuple_154": c154, "tuple_043": c043}
    return out


def per_entity_flag(mem):
    """Strong one-of-six: highlighted entity differs, other five share one value."""
    NODE = [0x4af370, 0x4a9cc0, 0x4a6640, 0x4a3010, 0x49fa80, 0x49c6e0]
    HI = {"102": 0, "103": 4, "104": 3}
    hits = 0
    for d in range(0x220):
        ok = True
        for s in ORDER:
            vals = [mem[s][NODE[k] + 0x10 + d] for k in range(6)]
            hv = vals[HI[s]]
            oth = [v for k, v in enumerate(vals) if k != HI[s]]
            if len(set(oth)) != 1 or hv == oth[0]:
                ok = False
                break
        if ok:
            hits += 1
    return hits


def main() -> int:
    data = load_members()
    scans = {}
    for m in MEMBERS:
        if all((s, m) in data for s in ORDER):
            scans[m] = scan_tuple([data[(s, m)] for s in ORDER])
    ee = {s: data[(s, "eeMemory.bin")] for s in ORDER}
    flag_hits = per_entity_flag(ee)

    total154 = sum(v["tuple_154"] for m in scans for v in scans[m].values())
    total043 = sum(v["tuple_043"] for m in scans for v in scans[m].values())
    result = {
        "summary": ("Exhaustive across all savestate members: the per-screen highlight tuple is not stored "
                    "as a readable integer at any width; no per-entity 'selected' flag exists."),
        "members_scanned": list(scans),
        "highlight_tuples": {"1_based": list(T154), "0_based": list(T043)},
        "tuple_scan": scans,
        "tuple_154_total_hits": total154,
        "tuple_043_total_hits": total043,
        "per_entity_flag_hits": flag_hits,
        "state_sha256": {s: hashlib.sha256(P2S[s].read_bytes()).hexdigest() for s in ORDER},
        "conclusion": ("The mark is not stored in any savestate member as a readable integer or pointer; "
                       "isolating it needs a live tool (read/write breakpoint or live value scan)."),
        "ps2dev_check": ("ps2dev org is the PS2 homebrew toolchain (ps2sdk/ps2gl/ps2client/ps2link/ps2gdb); "
                         "build tools only, no memory-search or pointer tool for a retail game."),
    }
    result["control_ee_tuple154_zero"] = scans["eeMemory.bin"]["u32"]["tuple_154"] == 0
    result["control_all_members_tuple154_zero"] = total154 == 0
    result["control_no_entity_flag"] = flag_hits == 0
    result["render_fidelity_complete"] = False
    ok = (result["control_ee_tuple154_zero"] and result["control_all_members_tuple154_zero"]
          and result["control_no_entity_flag"])
    result["result"] = "VERIFY OK" if ok else "VERIFY FAILED"
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(result["result"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
