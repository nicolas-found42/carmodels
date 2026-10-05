#!/usr/bin/env python3
"""Grill round-5: the residual unspecified branches Jev flagged (still_open 0.81).
The gameflow pointer root, C's row set + controls, and per-thread closure artifact.
All 12 tools. Receipts: .../jev-grill/r5-*.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-grill")
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
    print(f"--- {tag:9} {tool:14} action={act}")
    return c


BRANCHES = (
    "Residual open branches after the final plan (Jev f-06b: still_open 0.81; 'ready' contradicted on 'leaves no "
    "decision silently assumed'):\n"
    "(1) POINTER ROOT: B says read entity+0x64 via the dynamic gameflow chain outer+4 -> +0x14c -> +0x174, but the "
    "plan never says how to locate the gameflow root 'outer' inside a raw EE savestate. The decompilation "
    "FUN_0019eb90:19 reads ((param_1+4)+0x14c)+0x174 and :37 sets flags at entity+0x60 = (...|0x1cd0); FUN_00121e10 "
    "stores the selector at entity+0x64. The prior tools scanned values/tables, never walked a pointer chain from a "
    "root. Options: (a) find the bootstrap global that stores the gameflow pointer (decompilation-first), then read "
    "that global in the savestate; (b) signature-scan the EE image for the entity struct (e.g. flags 0x...1cd0 at "
    "+0x60) and follow back-pointers; (c) accept a paused savestate may not expose a stable chain and record B's "
    "store read as 'attempted; pointer root unresolved' -> recorded open.\n"
    "(2) C ROW SET + CONTROLS: C extends resolve_display_names.py to the car-keyed set (~35-39). Unspecified: exact "
    "row set (all 35 CARDATA INGAME_TEXT_ENUM values vs only TXT_CARS_* keys present), what happens for cars whose "
    "enum is missing from tlate_en, whether en-only or multi-locale, and what negative controls / gate apply. "
    "Options: (a) assert all 35 cars resolve, negative controls (unknown key unresolved; apostrophe byte-exact), "
    "jev_gate; (b) 35 cars, no new controls; (c) TXT_CARS_* keys only.\n"
    "(3) CLOSURE ARTIFACT: stop condition 7b requires all three threads to reach a definite outcome, but the plan "
    "never says what artifact proves each is 'resolved'. Options: (a) one receipt + jev_gate per thread (escalate "
    "acceptable), plus a single session completion report listing the three definite outcomes; (b) three new tickets "
    "T4/T5/T6; (c) record in the continuation status only.")

run("r5-01-screen", "jev_screen", {"text": BRANCHES, "purpose": "round-5 residual-branch evidence"})
run("r5-02-noul", "jev_noul", {"propositions": [
    "How to locate the gameflow root in a raw EE savestate is a genuine open branch, not an implementation detail.",
    "The bootstrap-global approach (find the global that stores the gameflow pointer) is the decompilation-reachable way to root the chain.",
    "A signature scan for the entity struct (flags 0x1cd0 at +0x60) can locate the chain without a named global.",
    "C must assert all 35 cars resolve, not just the three captured pairs.",
    "One receipt plus a jev_gate per thread is the right closure artifact for 7b.",
    "The plan is ready to act on as written.",
], "context": BRANCHES})
run("r5-03-find", "jev_find", {"query": "the most decision-critical residual branch",
    "candidates": [
        {"id": "pointer_root", "text": "How to locate the gameflow root in the EE savestate to follow the chain to entity+0x64."},
        {"id": "c_rows", "text": "C's exact row set and negative controls."},
        {"id": "closure", "text": "What artifact proves each thread resolved."},
    ], "top_k": 3})
run("r5-04-rerank", "jev_rerank", {"query": "best way to root the gameflow pointer chain for reading entity+0x64",
    "candidates": [
        {"id": "boot_global", "text": "Find the bootstrap global storing the gameflow pointer and read it in the savestate."},
        {"id": "sig_scan", "text": "Signature-scan the EE image for the entity struct via flags 0x1cd0 at +0x60 and follow back-pointers."},
        {"id": "record_open", "text": "Record B's store read as attempted with the pointer root unresolved."},
    ]})
run("r5-05-classify", "jev_classify", {"items": [
        {"id": "pointer_root", "text": "Rooting the gameflow chain in a raw EE savestate to read entity+0x64."},
        {"id": "c_rows", "text": "C: assert all 35 cars resolve with negative controls."},
        {"id": "closure", "text": "One receipt + jev_gate per thread plus a completion report."},
        {"id": "done", "text": "The plan is ready as written."},
    ],
    "classes": [
        {"id": "needs_a_decision", "description": "A genuine design choice that would change what gets built. Example: the pointer-root method."},
        {"id": "implementation_detail", "description": "Mechanical, decided by the code, no design choice. Example: the exact regex."},
    ],
    "purpose": "confirm which residual branches actually need the user",
    "context": "Round-5 residual branches."})
run("r5-06-decide", "jev_decide", {
    "decision": "How should the gameflow pointer chain be rooted to read entity+0x64?",
    "evidence": BRANCHES,
    "priorities": "Decompilation-reachable (the B proof bar); bounded; a definite recorded outcome is acceptable if the root cannot be resolved; do not re-run value-only scanning.",
    "candidates": [
        {"id": "boot_global", "description": "Find the bootstrap global that stores the gameflow pointer (decompilation-first), read it in the savestate, follow the chain."},
        {"id": "sig_scan", "description": "Signature-scan the EE image for the entity struct (flags 0x1cd0 at +0x60) and follow back-pointers."},
        {"id": "record_open", "description": "Record the store read as attempted with the pointer root unresolved."},
    ],
    "requirements": ["Is decompilation-reachable", "Turns the chain into a named address", "Does not rely on value-only matching"]})
run("r5-07-compare", "jev_compare", {
    "passage_a": "B is specified: read entity+0x64 via the chain outer+4 -> +0x14c -> +0x174.",
    "passage_b": "B omits how to locate 'outer' in a raw EE savestate.",
    "aspects": ["completeness", "what is assumed", "what remains"]})
_r8 = run("r5-08-extract", "jev_extract", {"document": BRANCHES,
    "fields": [
        {"id": "chain", "pattern": "outer\\+4 -> \\+0x14c -> \\+0x174", "description": "the gameflow chain"},
        {"id": "store_off", "pattern": "entity\\+0x64", "description": "the selector store offset"},
        {"id": "flags", "pattern": "flags 0x[.0-9a-fx]*1cd0", "description": "the entity flags value"},
        {"id": "rows", "pattern": "~35-39", "description": "the C row estimate"},
    ]})
_r = []
_f = _r8.get("fields", {}) if isinstance(_r8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("r5-09-audit", "jev_audit", {"source": BRANCHES, "records": _r or [{"id": "store_off", "request": "extract store_off", "value": "entity+0x64"}]})
run("r5-10-verify", "jev_verify", {"claims": [
    "The plan specifies the gameflow chain outer+4 -> +0x14c -> +0x174.",
    "The plan specifies how to locate the root outer in a raw EE savestate.",
    "Stop condition 7b requires a closure artifact per thread that the plan does not yet define.",
    "C must resolve all 35 cars, not just the three captured pairs.",
], "evidence": BRANCHES})
run("r5-11-review", "jev_review", {"request": "Close the residual branches: root the gameflow chain, define C's rows/controls, define the closure artifact.",
    "diff": "+ root gameflow chain via the bootstrap global, read it in the savestate, follow to entity+0x64\n"
            "+ C asserts all 35 cars resolve with unknown-key and apostrophe controls, gated\n"
            "+ one receipt + jev_gate per thread; one session completion report for the three definite outcomes",
    "tests": "existing verifiers stay green"})
run("r5-12-gate", "jev_gate", {"request": "Adopt the residual-branch closures.",
    "diff": json.dumps({"pointer_root": "bootstrap global + chain", "c": "35 cars + controls + gate", "closure": "receipt+gate per thread + completion report"}, indent=1),
    "claims": [
        "Rooting the chain via a named bootstrap global is decompilation-reachable.",
        "C asserting all 35 cars with controls is stronger than the three-pair result.",
        "One receipt + jev_gate per thread satisfies 7b's closure requirement.",
    ],
    "evidence": BRANCHES + "\n\nDecide: " + json.dumps(results.get("r5-06-decide", {}))[:1500]})

print("GRILL ROUND-5 DONE", len(results), "calls")
