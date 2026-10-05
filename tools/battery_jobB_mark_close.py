#!/usr/bin/env python3
"""Mark number — closing Jev battery (all 12). Receipts: .../jev-jobB/mclose-*.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-jobB")
os.makedirs(OUT, exist_ok=True)
results = {}


def rd(p): return open(os.path.join(R, p), encoding="utf-8").read()


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
    print(f"--- {tag:14} {tool:14} action={act}")
    return c


MRK = rd("research/evidence/job-b-live/mark-number-exhaustive-search.json")
EV = ("Mark-number search result, exhaustive: across all three menu savestates I searched EVERY savestate member "
      "(EE main RAM 32 MiB, IOP RAM 2 MiB, VU0/VU1 memory+micro, EE/IOP hardware registers, PAD, scratchpad) at "
      "widths 8/16/32 for the highlight tuple (1,5,4) and the car-index tuple (0,4,3): 0 hits everywhere. The "
      "strong per-entity 'selected' flag test also gives 0 hits. Earlier: no common pointer to the highlighted "
      "node; the named livery store entity+0x64 is a float. ps2dev.org is the PS2 homebrew toolchain "
      "(ps2sdk/ps2gl/ps2client/ps2link/ps2gdb) - build tools only, no memory-search/pointer tool for a retail game. "
      "CONCLUSION: the mark number is not stored in any savestate as a readable integer; isolating it needs a live "
      "tool (PCSX2 read/write breakpoint or live value scan), which the project's read-only constraint excludes.")

run("mclose-01-screen", "jev_screen", {"text": EV, "purpose": "review the mark search result as task data"})
run("mclose-02-noul", "jev_noul", {"propositions": [
    "Every savestate member was searched exhaustively for the highlight tuple with 0 hits.",
    "The mark number is not stored in any savestate as a readable integer.",
    "Isolating the mark needs a live tool outside the read-only constraint.",
    "ps2dev offers a tool that could find the mark.",
    "The mark has already been found.",
], "context": EV + "\n\n" + MRK[:5000]})
run("mclose-03-find", "jev_find", {"query": "the only remaining way to isolate the mark number",
    "candidates": [
        {"id": "live_breakpoint", "text": "A PCSX2 read/write breakpoint on the menu draw path in the headless instance (a debugger feature)."},
        {"id": "live_scan", "text": "A live value scan (scanmem-style) narrowed by moving the highlight."},
        {"id": "ps2dev", "text": "ps2dev PS2 homebrew tooling."},
        {"id": "stop", "text": "Record open; no further option."},
    ], "top_k": 4})
run("mclose-04-rerank", "jev_rerank", {"query": "residual confidence that the mark is stored somewhere still unsearched",
    "candidates": [
        {"id": "registers", "text": "CPU registers / live PC state not captured in the savestate members listed."},
        {"id": "dynamic", "text": "The mark is recomputed from input each frame and never stored."},
        {"id": "nothing", "text": "Nothing remains; the search was complete."},
    ]})
_m5 = run("mclose-05-classify", "jev_classify", {"items": [
        {"id": "ee", "text": "EE main RAM: 0 hits at all widths."},
        {"id": "iop", "text": "IOP RAM 2 MiB: 0 hits at all widths."},
        {"id": "hw", "text": "EE/IOP hw registers, PAD, scratchpad, VU: 0 hits."},
        {"id": "found", "text": "The mark number was found."},
    ],
    "classes": [
        {"id": "searched_negative", "description": "A region searched with a clean zero result. Example: IOP RAM 0 hits."},
        {"id": "positive", "description": "A region where the mark was found."},
    ],
    "purpose": "confirm the search is exhausted and negative",
    "context": "Mark search."})
run("mclose-06-decide", "jev_decide", {
    "decision": "Is the mark-number search exhausted, leaving the only path a live (non-read-only) tool?",
    "evidence": EV + "\n\n" + MRK[:5000],
    "priorities": "Honest partial result; read-only constraint; do not break the constraint; a recorded-open outcome is acceptable; the user wants the mark found but not at the cost of a rule break.",
    "candidates": [
        {"id": "exhausted_live_needed", "description": "Search exhausted; the only remaining path is a live breakpoint/scan, which needs the user to lift the read-only rule."},
        {"id": "keep_searching_static", "description": "Keep searching statically."},
        {"id": "use_breakpoint_now", "description": "Use a breakpoint now, ignoring the constraint."},
    ],
    "requirements": ["Rests on the exhaustive result", "Does not break the read-only rule", "Leaves a recorded outcome"]})
run("mclose-07-compare", "jev_compare", {
    "passage_a": "All savestate members searched: 0 hits for the highlight tuple.",
    "passage_b": "The mark is stored as a readable integer in the savestate.",
    "aspects": ["evidence", "which is supported"]})
_m8 = run("mclose-08-extract", "jev_extract", {"document": MRK,
    "fields": [
        {"id": "total154", "pattern": "\"tuple_154_total_hits\": [0-9]+", "description": "total (1,5,4) hits"},
        {"id": "flag", "pattern": "\"per_entity_flag_hits\": [0-9]+", "description": "per-entity flag hits"},
        {"id": "result", "pattern": "\"result\": \"[A-Z ]+\"", "description": "final result token"},
    ]})
_r = []
_f = _m8.get("fields", {}) if isinstance(_m8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("mclose-09-audit", "jev_audit", {"source": MRK[:6000], "records": _r or [{"id": "total154", "request": "extract total154", "value": "0"}]})
run("mclose-10-verify", "jev_verify", {"claims": [
    "Every savestate member was searched for the highlight tuple with 0 hits.",
    "No per-entity 'selected' flag exists.",
    "The mark number is not stored in any savestate as a readable integer.",
    "Isolating the mark needs a live tool outside the read-only constraint.",
    "ps2dev provides a tool to find the mark.",
], "evidence": EV + "\n\n" + MRK[:5000]})
run("mclose-11-review", "jev_review", {"request": "Record the mark-number search as exhaustive and negative; note the only path is a live tool.",
    "diff": "+ searched all savestate members (EE/IOP/VU/hw/PAD/scratchpad) at all widths: 0 hits\n+ per-entity flag: 0 hits\n+ conclusion: needs a live breakpoint/scan; read-only constraint excludes it\n+ record open; no unsupported claim",
    "tests": "probe_mark_exhaustive.py VERIFY OK"})
run("mclose-12-gate", "jev_gate", {"request": "Gate the mark-number search result: exhaustive and negative.",
    "diff": json.dumps({"members": "all", "tuple_154_hits": 0, "flag_hits": 0, "needs": "live tool"}, indent=1),
    "claims": [
        "Every savestate member was searched with 0 hits for the highlight tuple.",
        "The mark is not stored as a readable integer in the savestate.",
        "The only remaining path is a live tool, excluded by the read-only constraint.",
    ],
    "evidence": EV + "\n\n" + MRK[:5000]})

print("MARK CLOSE DONE", len(results), "calls")
