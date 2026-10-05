#!/usr/bin/env python3
"""Mark-number sweep design — Jev battery (all 12). Decides the 6-position ground-truth
sweep and the candidate-ranking criteria. Receipts: .../jev-jobB/sweep-*.json
"""
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
    print(f"--- {tag:12} {tool:14} action={act}")
    return c


EV = ("Breakthrough: headless F8 screenshots work (PCSX2 writes PNGs to /data/snaps). Current screen verified "
      "by vision: 6 thumbnails, 3rd highlighted, VEHICLE '55 Thunderbird. Paused-pair method: pause via RFB Space, "
      "save pair (pause-control = 0 differing words), unpause, one L key, re-pause, save pair. A=pos3, B=pos5 "
      "(screenshot-verified Thunderbird Convertible). Diff A->B re-finds the DAT-table candidates: 0x241b60 4->5, "
      "0x241e00 4->3, 0x2420a0 4->5. But 0x241b60 reads 5,4,4 across slots 102/103/104 (highlights 1/5/4), so it is "
      "NOT the per-car id by value. FUN_001c4a40 indexes DAT_00241b40 by the per-entity type byte with stride 0x150, "
      "so these words are fields inside per-type menu records. Proposed: a 6-position sweep - move the highlight to "
      "each of the 6 thumbnails with a screenshot + paused savestate pair at each; the true mark word must equal "
      "(or map 1:1 to) the 1..6 position across all six samples. All headless, read-only + savestate saves.")

run("sweep-01-screen", "jev_screen", {"text": EV, "purpose": "review the sweep evidence before deciding"})
run("sweep-02-noul", "jev_noul", {"propositions": [
    "A 6-position screenshot-verified sweep will identify the mark word.",
    "F8 screenshots plus paused savestate pairs give attributable ground truth.",
    "0x241b60 (reads 5,4,4 for highlights 1/5/4) is the per-car highlight id.",
    "The mark word must equal or map 1:1 to the 1..6 highlight position.",
    "The sweep needs no new tool class beyond keys, screenshots, and savestates.",
], "context": EV})
run("sweep-03-find", "jev_find", {"query": "the best next step to identify the mark word",
    "candidates": [
        {"id": "six_sweep", "text": "Screenshot + savestate pair at each of the 6 highlight positions; the mark must map 1:1 to position."},
        {"id": "chase_241b60", "text": "Assume 0x241b60-family words and verify by repeated moves."},
        {"id": "breakpoint", "text": "A PCSX2 read breakpoint on the draw path."},
        {"id": "stop", "text": "Record open; stop."},
    ], "top_k": 4})
run("sweep-04-rerank", "jev_rerank", {"query": "rank candidate-selection criteria for the sweep",
    "candidates": [
        {"id": "one_to_one", "text": "The word's six values map 1:1 to the six highlight positions."},
        {"id": "equals_pos", "text": "The word literally equals the 1..6 position."},
        {"id": "decomp_reach", "text": "The word is decompilation-reachable (DAT_00241b40 record / menu struct)."},
        {"id": "small_int", "text": "The word is a small integer that changes with moves."},
    ]})
run("sweep-05-classify", "jev_classify", {"items": [
        {"id": "w_241b60", "text": "0x241b60 reads 5,4,4 for highlights 1/5/4; 4->5 in the A->B move."},
        {"id": "f8", "text": "F8 screenshots land in /data/snaps headlessly."},
        {"id": "pairs", "text": "Paused savestate pairs have 0 pause-control diffs."},
    ],
    "classes": [
        {"id": "ground_truth", "description": "Verified observation tying a screen to a state. Example: a screenshot showing the highlighted thumbnail."},
        {"id": "candidate", "description": "A word that moves with the highlight but is not yet attributed."},
        {"id": "disproven", "description": "A word shown not to be the per-car id by value."},
    ],
    "purpose": "sort sweep facts by evidential status",
    "context": "Mark sweep."})
run("sweep-06-decide", "jev_decide", {
    "decision": "Should we run the 6-position screenshot-verified sweep?",
    "evidence": EV,
    "priorities": "Headless, read-only; ground truth before attribution; a positive find is wanted; an honest open stays acceptable.",
    "candidates": [
        {"id": "run_sweep", "description": "Run the sweep: screenshot + paused pair at each of 6 highlight positions; rank words by 1:1 mapping to position."},
        {"id": "breakpoint", "description": "Skip the sweep; go straight to a debugger breakpoint."},
        {"id": "stop", "description": "Record open without the sweep."},
    ],
    "requirements": ["Runs headless", "Ground-truths every sample", "Can attribute a word to the highlight"]})
run("sweep-07-compare", "jev_compare", {
    "passage_a": "Two known positions (A=3, B=5): a word must read (3,5)-consistent values.",
    "passage_b": "Six known positions: a word must map 1:1 to 1..6.",
    "aspects": ["attribution strength", "cost", "false-positive risk"]})
_s8 = run("sweep-08-extract", "jev_extract", {"document": EV,
    "fields": [
        {"id": "w60", "pattern": "0x241b60 4->5", "description": "the 0x241b60 move"},
        {"id": "w00", "pattern": "0x241e00 4->3", "description": "the 0x241e00 move"},
        {"id": "ctrl", "pattern": "pause-control = 0 differing words", "description": "the pause control result"},
        {"id": "screen", "pattern": "3rd highlighted", "description": "the verified screen state"},
    ]})
_r = []
_f8 = _s8.get("fields", {}) if isinstance(_s8, dict) else {}
for fid, fv in (_f8.items() if isinstance(_f8, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("sweep-09-audit", "jev_audit", {"source": EV, "records": _r or [{"id": "ctrl", "request": "extract ctrl", "value": "pause-control = 0 differing words"}]})
run("sweep-10-verify", "jev_verify", {"claims": [
    "Headless F8 screenshots work and land in /data/snaps.",
    "Paused savestate pairs have 0 differing words within a pair.",
    "The A->B move re-finds 0x241b60/0x241e00/0x2420a0 as changed.",
    "0x241b60 reads 5,4,4 for highlights 1/5/4, so it is not the per-car id by value.",
    "The mark word has been found.",
], "evidence": EV})
run("sweep-11-review", "jev_review", {"request": "Approve the 6-position screenshot-verified sweep.",
    "diff": "+ F8 screenshot + paused savestate pair at each of 6 highlight positions\n+ rank words by 1:1 mapping to position; require decompilation reachability\n+ headless, read-only, no new tool class",
    "tests": "F8 works; pause-control 0 diffs; PINE reads green"})
run("sweep-12-gate", "jev_gate", {"request": "Approve the sweep as the mark-identification experiment.",
    "diff": json.dumps({"sweep": "6 positions x screenshot + pair", "criterion": "1:1 map to position"}, indent=1),
    "claims": [
        "Screenshots plus paused pairs give attributable ground truth.",
        "A 1:1 position mapping identifies the mark word.",
        "The sweep runs headless with read-only PINE plus savestate saves.",
    ],
    "evidence": EV + "\n\nDecide: " + json.dumps(results.get("sweep-06-decide", {}))[:1500]})

print("SWEEP JEV DONE", len(results), "calls")
