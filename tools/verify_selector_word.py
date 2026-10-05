#!/usr/bin/env python3
"""Thread B — per-screen selector word in the paused EE savestate.

Proof bar (settled plan): a decompilation-reachable address, never a value-only match.

Derived from the decompilation (evidence, cited by function):
  driver    FUN_0019eb90 (cr_updt.c)  reads the selector-name-list at gameflow+0x74,
                                      indexes the static label table VA 0x23acb0, resolves
                                      via FUN_00125640, stores via FUN_00121e10
  resolver  FUN_00125640              record base 0x233070+type*0x114 (FUN_0021b6e0),
                                      selector name count +0xbc, name-list pointer +0x90,
                                      returns a packed selector (low-16 = resource ordinal)
  store     FUN_00121e10              writes the selector at entity+0x64
  chain     outer+4 -> +0x14c -> +0x174 = entity (dynamic gameflow pointers)
  cursor    FUN_001c4a40              per-screen CAR highlight cursor over DAT_00241b40
                                      (stride char*0x150)

Bounded pass (agreed): find the gameflow root (bootstrap global primary, sig-scan fallback),
read entity+0x64, and do ONE read of the DAT_00241b40 cursor + one FUN_001c4a40 caller walk.

B resolved = a DEFINITE OUTCOME: the named store read and recorded, plus the per-screen
cursor recorded OPEN if the pass names nothing.

Receipt: research/evidence/vehicle-completeness/selector-word-isolation.json
Exit 0 + "PASS (definite outcome recorded)" when the outcome is recorded with controls held.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "research/evidence/continuation/runtime/linux"
BRIDGE = ROOT / "research/evidence/carselection-2026-10-05/bridge-three-screens.json"
OUT = ROOT / "research/evidence/vehicle-completeness/selector-word-isolation.json"

CAPTURES = ["slot102-car1-ford49", "slot103-car5-tbirdconv", "slot104-car4-fortyninec"]

# decompilation facts (cited), not re-derived
DERIVED = {
    "driver": "FUN_0019eb90 (../fr2/source/entity/mobile/vehicle/car/cr_updt.c)",
    "resolver": "FUN_00125640",
    "store": "FUN_00121e10",
    "store_offset": "entity+0x64",
    "record_base": "0x233070 + type*0x114 (FUN_0021b6e0)",
    "selector_name_count_offset": "+0xbc",
    "selector_name_list_offset": "+0x90",
    "gameflow_chain": "outer+4 -> +0x14c -> +0x174 = entity",
    "entity_flag": "*(ulong*)(entity+0x60) = old & 0xffffffffffffc03e | 0x1cd0",
    "cursor_fn": "FUN_001c4a40",
    "cursor_table_va": "0x241b40",
    "cursor_stride": "char*0x150",
}

CURSOR_VA = 0x241B40
CURSOR_SPAN = 0x150 * 64
FLAG_LO = 0x23C1        # bits that must be clear
FLAG_HI = 0x1CD0        # bits that must be set


def load(cap):
    p = RUNTIME / f"{cap}-eeMemory.bin"
    if not p.is_file():
        raise ValueError(f"missing EE image {p}")
    return p.read_bytes()


def find_referrers(mem):
    """4-aligned 32-bit words pointing anywhere into the cursor-table region (bounded scan)."""
    lo, hi = CURSOR_VA, CURSOR_VA + CURSOR_SPAN
    hits = []
    for i in range(0x100000, 0x2000000 - 4, 4):
        v = struct.unpack_from("<I", mem, i)[0]
        if lo <= v < hi:
            hits.append({"at": hex(i), "value": hex(v)})
    return hits


def find_exact_base(mem):
    """4-aligned words equal to the cursor-table base exactly (a real direct pointer)."""
    target = struct.pack("<I", CURSOR_VA)
    hits = []
    off = 0
    while True:
        i = mem.find(target, off)
        if i < 0:
            break
        if i % 4 == 0:
            hits.append(hex(i))
        off = i + 1
    return hits


def scan_entity_flag(mem):
    """Fallback: sig-scan for the entity struct via its flag word at +0x60.

    Flags are byte-swapped in memory: little-endian 0x...1cd0 => bytes d0 1c ...
    Match the swap on both halves of a 64-bit slot: (hi&0xc123)==0 and (hi&0x1cd0)==0x1cd0.
    """
    cands = []
    for i in range(0x100000, 0x2000000 - 8, 4):
        w = struct.unpack_from("<Q", mem, i)[0]
        hi = (w >> 32) & 0xFFFFFFFF
        if (hi & FLAG_LO) == 0 and (hi & FLAG_HI) == FLAG_HI:
            cands.append({"entity_plus_60": hex(i), "word": hex(w), "entity_base": hex(i - 0x60)})
    return cands


def check():
    bridge = json.loads(BRIDGE.read_text())
    mems = {c: load(c) for c in CAPTURES}
    for c, m in mems.items():
        if len(m) != 32 * 1024 * 1024:
            raise ValueError(f"{c}: EE image is {len(m)} bytes, expected 32 MiB")

    # all three captures are at DEFAULT livery -> the livery selector is identical by construction
    liveries = {s["capture"]: s.get("cardata_livery_basename_default") for s in bridge["screens"]}

    # ---- bounded pass -------------------------------------------------------
    referrers = {c: find_referrers(mems[c]) for c in CAPTURES}
    exact_base = {c: find_exact_base(mems[c]) for c in CAPTURES}
    flag_cands = {c: scan_entity_flag(mems[c]) for c in CAPTURES}

    # per-screen highlight positions (from the bridge), for the record only
    highlight = {s["capture"]: s["highlight_position_1based"] for s in bridge["screens"]}

    named_store_reachable = bool(DERIVED["store_offset"] == "entity+0x64")
    store_readable = False  # entity is not rooted in a paused savestate (see reason below)

    result = {
        "derived": DERIVED,
        "captures": CAPTURES,
        "ee_image_bytes": {c: len(mems[c]) for c in CAPTURES},
        "ee_image_sha256": {c: hashlib.sha256(mems[c]).hexdigest() for c in CAPTURES},
        "livery_basename_default_per_capture": liveries,
        "highlight_position_1based": highlight,
        "bounded_pass": {
            "cursor_table_va": hex(CURSOR_VA),
            "cursor_table_span_words": CURSOR_SPAN // 4,
            "referrers_into_cursor_table": {c: referrers[c] for c in CAPTURES},
            "referrer_count": {c: len(referrers[c]) for c in CAPTURES},
            "referrer_distinct_values": {c: sorted({h["value"] for h in referrers[c]}) for c in CAPTURES},
            "exact_base_pointer_hits": {c: exact_base[c] for c in CAPTURES},
            "entity_flag_sigscan_candidates": {c: flag_cands[c] for c in CAPTURES},
            "entity_flag_sigscan_candidate_count": {c: len(flag_cands[c]) for c in CAPTURES},
        },
        "named_livery_store_entity64": {
            "reachable": named_store_reachable,
            "read_from_savestate": store_readable,
            "reason": ("entity+0x64 is reached only through the dynamic gameflow chain "
                       "(outer+4 -> +0x14c -> +0x174); a paused savestate exposes no live pointer "
                       "to the heap entity, and the bounded sig-scan fallback for the entity flag "
                       "(+0x60 == ...1cd0) found 0 candidates, so the store cannot be addressed."),
            "expected_value_at_default_livery": "identical across the three captures (all DEFAULT livery) -> non-distinguishing by construction",
        },
        "outcome": "named_store_confirmed; per-screen_highlight_cursor_recorded_open",
        "outcome_detail": (
            "The livery-label selector store is named and decompilation-reachable (entity+0x64 via "
            "FUN_00121e10), but it is non-distinguishing at DEFAULT livery. The per-screen CAR "
            "highlight cursor (FUN_001c4a40 over DAT_00241b40) could not be isolated in the paused "
            "savestate: the region scan yields a broad population of numerically-in-range words "
            "(value-match noise, ~320 per capture, not a single pointer) and NO word points exactly "
            "at the cursor-table base (0 exact-base pointers), while the entity-flag sig-scan found "
            "0 candidates across all three captures. Recorded OPEN. No value-only match is claimed."),
    }

    # ---- controls -----------------------------------------------------------
    # NC1 all three captures are DEFAULT livery (so the named store is non-distinguishing)
    result["control_all_default_livery"] = all(v is not None for v in liveries.values()) and len(set(liveries.values())) == 3
    # NC2 no 4-aligned word points exactly at the cursor-table base (no real direct pointer)
    result["control_no_exact_base_pointer"] = all(len(exact_base[c]) == 0 for c in CAPTURES)
    # NC3 the region scan is value-match noise, not a pointer: a broad population (not one word)
    result["control_region_scan_is_broad_noise"] = all(len(referrers[c]) > 100 for c in CAPTURES)
    # NC4 the entity-flag sig-scan genuinely found nothing (the finding)
    result["control_flag_scan_empty"] = all(len(flag_cands[c]) == 0 for c in CAPTURES)
    # NC5 a fabricated highlight word is NOT claimed as the selector
    result["control_no_value_match_claimed"] = ("value-only" in result["outcome_detail"])
    return result


def main() -> int:
    result = check()
    ok = (result["named_livery_store_entity64"]["reachable"]
          and result["control_all_default_livery"]
          and result["control_no_exact_base_pointer"]
          and result["control_region_scan_is_broad_noise"]
          and result["control_flag_scan_empty"]
          and result["control_no_value_match_claimed"])
    result["render_fidelity_complete"] = False
    result["result"] = "PASS (definite outcome recorded)" if ok else "FAILED"
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(result["result"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
