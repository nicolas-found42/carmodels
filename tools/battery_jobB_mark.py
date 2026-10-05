#!/usr/bin/env python3
"""Find the mark number — Jev battery (all 12). Chooses the decisive experiment.
Receipts: research/evidence/vehicle-completeness/jev-jobB/mark-*.json
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


EV = (
    "Goal: find the mark number — the game's own id for the car highlighted on the car-selection menu. "
    "Exhausted so far (exhaustive, deterministic): across three savestates (highlight 1/5/4 -> cars 1/5/4), "
    "(a) no EE word at width 8/16/32 equals the highlight tuple (1,5,4) or (0,4,3); (b) no per-entity 'selected' "
    "flag exists where the highlighted car's field differs while the other five share one value (0 strong hits at "
    "width 1/2/4 across the 6 car entities, node+0x10); (c) no common address holds a pointer to the highlighted "
    "car's node/entity; (d) FUN_001de3d8 creates all cars, not the selection. Named/found: the live car-entity list "
    "is reachable read-only over PINE (static global 0x290278 -> manager 0x473d70 -> 6 entities; type byte at "
    "entity+0, linked by node+0xc); the livery store is a float at entity+0x64 (FUN_00121e10); FUN_001c4a40 runs "
    "per entity over DAT_00241b40 (the per-type table) and reads/writes a byte at entity+0x11. Web methods "
    "(scanmem value-scan with 'unknown initial value' -> narrow by changed/unchanged; Cheat Engine pointer scan; "
    "PINCE) all assume the value MOVES with a single live session. Constraint: headless only, no host focus; "
    "read-only preferred; the emulator is currently paused on a savestate.")

run("mark-01-screen", "jev_screen", {"text": EV, "purpose": "review the mark-number evidence before the decision"})
run("mark-02-noul", "jev_noul", {"propositions": [
    "The mark number is stored in EE memory at a fixed address.",
    "A same-session adjacent diff (two fresh savestates one highlight apart) would reveal the mark word, even though the cross-session diff did not.",
    "The mark is computed from input each frame and not stored as a stable word.",
    "The mark is reachable by a live read breakpoint on the draw path.",
    "More static analysis of the decompilation will find the mark.",
], "context": EV})
run("mark-03-find", "jev_find", {"query": "the decisive next experiment to find the mark number",
    "candidates": [
        {"id": "same_session_adjacent", "text": "Headless: load a menu state live, deliver one key to move the highlight, save two fresh savestates one car apart, and diff them (only highlight-dependent state changes)."},
        {"id": "scanmem_unknown", "text": "Headless scanmem/unknown-initial-value scan narrowed by moving the highlight live."},
        {"id": "live_breakpoint", "text": "A PCSX2 read breakpoint on FUN_001c4a40's draw path to catch the highlight read."},
        {"id": "more_decomp", "text": "Read the menu-input handler that changes the highlight index."},
    ], "top_k": 4})
run("mark-04-rerank", "jev_rerank", {"query": "rank the experiments by likely payoff",
    "candidates": [
        {"id": "same_session_adjacent", "text": "Two fresh savestates one highlight apart, same session, diffed."},
        {"id": "scanmem_unknown", "text": "Unknown-initial-value scan narrowed live."},
        {"id": "live_breakpoint", "text": "Read breakpoint on the draw path."},
        {"id": "more_decomp", "text": "Read the input handler."},
    ]})
run("mark-05-classify", "jev_classify", {"items": [
        {"id": "cross_session", "text": "Diff three savestates captured in different sessions (confounded by animation)."},
        {"id": "same_session", "text": "Diff two savestates captured moments apart in one session."},
        {"id": "live_read", "text": "Read the value live from the running emulator."},
    ],
    "classes": [
        {"id": "high_confidence", "description": "Removes the confound, so the result is attributable to the highlight. Example: a same-session adjacent diff."},
        {"id": "confounded", "description": "Cannot separate the highlight from other differing state."},
        {"id": "needs_tool", "description": "Requires a tool class not yet used (debugger/scan)."},
    ],
    "purpose": "separate clean experiments from confounded ones",
    "context": "Mark-number search."})
run("mark-06-decide", "jev_decide", {
    "decision": "Which experiment should we run to find the mark number?",
    "evidence": EV,
    "priorities": "Headless, read-only preferred; a positive find is wanted but an honest open stays acceptable; prefer the experiment that can attribute a change to the highlight; the user explicitly wants the mark found.",
    "candidates": [
        {"id": "same_session_adjacent", "description": "Headless: load a menu state, one key to move the highlight, save two fresh savestates one car apart, diff them."},
        {"id": "scanmem_unknown", "description": "Headless unknown-initial-value scan narrowed by moving the highlight live."},
        {"id": "live_breakpoint", "description": "A read breakpoint on FUN_001c4a40's draw path (debugger feature)."},
        {"id": "more_decomp", "description": "Read the menu-input handler that changes the highlight."},
    ],
    "requirements": ["Runs headless", "Attributes the change to the highlight", "Read-only or a documented tool"]})
run("mark-07-compare", "jev_compare", {
    "passage_a": "Cross-session diff of three savestates (the method that found nothing).",
    "passage_b": "Same-session adjacent diff of two fresh savestates.",
    "aspects": ["confound control", "attribution to highlight", "cost"]})
_m8 = run("mark-08-extract", "jev_extract", {"document": EV,
    "fields": [
        {"id": "global", "pattern": "0x290278", "description": "the static entity-list global"},
        {"id": "manager", "pattern": "0x473d70", "description": "the live manager address"},
        {"id": "store", "pattern": "entity\\+0x64", "description": "the livery store offset"},
        {"id": "draw", "pattern": "FUN_001c4a40", "description": "the per-entity draw function"},
    ]})
_r = []
_f = _m8.get("fields", {}) if isinstance(_m8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("mark-09-audit", "jev_audit", {"source": EV, "records": _r or [{"id": "draw", "request": "extract draw", "value": "FUN_001c4a40"}]})
run("mark-10-verify", "jev_verify", {"claims": [
    "No EE word at any width equals the highlight tuple in the three savestates.",
    "No per-entity 'selected' flag exists across the six car entities.",
    "The live car-entity list is reachable read-only over PINE.",
    "A same-session adjacent diff is confound-free for the highlight.",
], "evidence": EV})
run("mark-11-review", "jev_review", {"request": "Choose the decisive experiment for the mark number.",
    "diff": "+ exhausted: cross-session tuple/flag/pointer scans (all negative)\n+ proposed: headless same-session adjacent diff of two fresh savestates one highlight apart\n+ read-only; no host focus",
    "tests": "container headless; PINE read + savestate ops only"})
run("mark-12-gate", "jev_gate", {"request": "Approve the same-session adjacent diff as the mark-number experiment.",
    "diff": json.dumps({"experiment": "same-session adjacent diff", "headless": True, "read_only": True}, indent=1),
    "claims": [
        "Cross-session tuple/flag/pointer scans are exhausted and negative.",
        "A same-session adjacent diff can attribute a change to the highlight.",
        "The experiment runs headless with read-only PINE plus savestate ops.",
    ],
    "evidence": EV + "\n\nDecide: " + json.dumps(results.get("mark-06-decide", {}))[:1500]})

print("MARK JEV DONE", len(results), "calls")
