#!/usr/bin/env python3
"""Mark sweep close-out — Jev battery (all 12). Receipts: .../jev-jobB/msw-*.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-jobB")
os.makedirs(OUT, exist_ok=True)
results = {}


def run(tag, tool, args):
    try:
        res = call(tool, args)
        c = res.get("result", res)
        if isinstance(c, dict) and "content" in c:
            try:
                c = json.loads(c["content"][0]["text"])
            except Exception as ex:
                c = {"parse_error": str(ex), "raw": str(c)[:400]}
    except Exception as e:
        c = {"error": str(e)}
    json.dump({"args": args, "result": c}, open(os.path.join(OUT, tag + ".json"), "w"), indent=2)
    results[tag] = c
    act = c.get("action") or (c.get("recommendation") or {}).get("action") if isinstance(c, dict) else None
    print(f"--- {tag:11} {tool:14} action={act}")
    return c


EV = ("6-position screenshot-verified sweep results (slots 140-145, heap base identical 0x473d70, "
      "pause-control 0 diffs within pairs). Verified positions: 140=pos1 FORD'49, 141=pos2 '68 MUSTANG, "
      "142=pos3 '55 Thunderbird, 143=pos6 FORD GT, 144=pos6 FORD GT, 145=pos5 Thunderbird Convertible. "
      "DECISIVE TEST 1: NO word anywhere in the 32 MiB EE image equals its slot's position in all 6 slots "
      "(0 hits at u32/u16/u8). TEST 2: the DAT-table small words do not track position: 0x241b60 reads "
      "5,5,5,4,3,3 across pos1,2,3,6,6,5; 0x241e00 reads 5,5,5,5,4,4. Notably 143 vs 144 (BOTH pos6) differ "
      "at 0x241b60 (4 vs 3), so these words track something else (animation/other cursor), not the highlight. "
      "Combined with the earlier exhaustive result (no tuple, no flag, no pointer in ANY savestate member), "
      "the mark is definitively NOT a stored integer. Remaining possibilities: recomputed per frame, or an "
      "encoding not tested (float/bitfield). All headless, read-only + savestate saves; container left paused.")

run("msw-01-screen", "jev_screen", {"text": EV, "purpose": "review the sweep result as task data"})
run("msw-02-noul", "jev_noul", {"propositions": [
    "No EE word equals the highlight position across the six verified slots.",
    "The mark is not stored as an integer in EE memory.",
    "The DAT-table words 0x241b60/0x241e00 track the highlight.",
    "The sweep ground truth (screenshot per slot) is trustworthy.",
    "A float or bitfield encoding remains untested and could hold the mark.",
], "context": EV})
run("msw-03-find", "jev_find", {"query": "the strongest single evidence that the mark is not a stored integer",
    "candidates": [
        {"id": "test1", "text": "TEST 1: zero words equal position across all 6 slots at any width."},
        {"id": "tuple", "text": "Exhaustive tuple scan: 0 hits for (1,5,4) at every width in every member."},
        {"id": "flag", "text": "Per-entity selected-flag test: 0 strong hits."},
        {"id": "dat", "text": "DAT words 0x241b60/0x241e00 do not track position."},
    ], "top_k": 4})
run("msw-04-rerank", "jev_rerank", {"query": "what to try next for the mark, if anything",
    "candidates": [
        {"id": "float_scan", "text": "Scan float/fixed-point encodings of 1..6 across the six slots."},
        {"id": "breakpoint", "text": "A PCSX2 read/write breakpoint on the draw path (debugger feature)."},
        {"id": "per_frame", "text": "Accept the mark is recomputed per frame; record open."},
        {"id": "more_int", "text": "More integer scans."},
    ]})
run("msw-05-classify", "jev_classify", {"items": [
        {"id": "test1", "text": "0 words equal position in all 6 slots."},
        {"id": "dat_words", "text": "0x241b60/0x241e00 move with animation, differ even at same position."},
        {"id": "sweep_truth", "text": "Each slot has a vision-verified screenshot."},
    ],
    "classes": [
        {"id": "decisive_negative", "description": "Rules out the stored-integer hypothesis. Example: TEST 1 zero."},
        {"id": "ground_truth", "description": "Verified observation. Example: screenshot per slot."},
        {"id": "inconclusive", "description": "Neither rules in nor out."},
    ],
    "purpose": "sort sweep results by evidential weight",
    "context": "Sweep close-out."})
run("msw-06-decide", "jev_decide", {
    "decision": "Is the stored-integer hypothesis for the mark now closed?",
    "evidence": EV,
    "priorities": "Honest partial result; do not claim what is not shown; a recorded open is acceptable.",
    "candidates": [
        {"id": "closed_negative", "description": "Closed as negative: the mark is not a stored EE integer; record open with float-encoding noted untested."},
        {"id": "float_scan", "description": "Run one float-encoding scan before closing."},
        {"id": "breakpoint", "description": "Go to a debugger breakpoint now."},
    ],
    "requirements": ["Rests on the sweep evidence", "Does not overclaim", "Leaves a next step"]})
run("msw-07-compare", "jev_compare", {
    "passage_a": "TEST 1: no word equals position across six verified slots.",
    "passage_b": "The mark is stored as a small integer in EE.",
    "aspects": ["evidence", "which stands"]})
_m8 = run("msw-08-extract", "jev_extract", {"document": EV,
    "fields": [
        {"id": "test1", "pattern": "0 hits at u32/u16/u8|NO word anywhere|0 words equal", "description": "the TEST 1 result"},
        {"id": "w60", "pattern": "0x241b60 reads [0-9,]+", "description": "the 0x241b60 readings"},
        {"id": "heap", "pattern": "0x473d70", "description": "the heap base"},
    ]})
_r = []
_f = _m8.get("fields", {}) if isinstance(_m8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("msw-09-audit", "jev_audit", {"source": EV, "records": _r or [{"id": "heap", "request": "extract heap", "value": "0x473d70"}]})
run("msw-10-verify", "jev_verify", {"claims": [
    "No EE word equals its slot's highlight position across all six slots.",
    "The DAT words 0x241b60/0x241e00 do not track the highlight position.",
    "143 vs 144 (both pos6) differ at 0x241b60, so it tracks something else.",
    "The mark is stored as an integer in EE memory.",
    "Each sweep slot has a vision-verified screenshot.",
], "evidence": EV})
run("msw-11-review", "jev_review", {"request": "Close the stored-integer hypothesis as negative on the sweep evidence.",
    "diff": "+ 6 screenshot-verified slots (pos1,2,3,6,6,5)\n+ TEST 1: 0 words equal position at any width\n+ DAT words do not track position; differ even at same position\n+ record open; float encoding noted as the one untested form",
    "tests": "pause-control 0 diffs; heap base identical"})
run("msw-12-gate", "jev_gate", {"request": "Gate the sweep close-out.",
    "diff": json.dumps({"test1_hits": 0, "dat_tracks": False, "verdict": "not a stored integer"}, indent=1),
    "claims": [
        "No EE word equals the highlight position across the six slots.",
        "The DAT-table words do not track the highlight.",
        "The stored-integer hypothesis is closed as negative.",
    ],
    "evidence": EV + "\n\nDecide: " + json.dumps(results.get("msw-06-decide", {}))[:1500]})

print("SWEEP CLOSE DONE", len(results), "calls")
