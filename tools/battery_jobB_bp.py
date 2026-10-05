#!/usr/bin/env python3
"""Breakpoint-road decision — Jev battery (all 12). No GDB stub in this build, debugger
has no headless API, DebugServer patch is Windows-only. Decides the feasible path.
Receipts: research/evidence/vehicle-completeness/jev-jobB/bp-*.json
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
    print(f"--- {tag:9} {tool:14} action={act}")
    return c


EV = ("Breakpoint-road feasibility findings (all verified in the headless container): "
      "PCSX2 v2.8.2 AppImage binary contains ZERO gdb strings: no GDB stub. The debugger GUI has no remote/IPC API "
      "(only a forum request exists upstream). hkmodd/PCSX2-MCP DebugServer patch is Windows-only (pcsx2-qt.exe/MSVC); "
      "Linux needs a full PCSX2 source build + patch (hours, GBs, risky inside the running container). Driving the "
      "debugger GUI blind via RFB keys is infeasible: F8 screenshots capture only the emulated game screen, never "
      "the Qt debugger window, so there is zero visibility into debugger state. What REMAINS feasible headlessly: "
      "(a) static analysis of the menu INPUT handler in the decompilation - find which variable the d-pad handler "
      "increments when moving the highlight (read-only, headless, no new tool); then verify the variable live via "
      "read-only PINE across the six screenshot-verified slots; (b) full PCSX2 source build + DebugServer patch; "
      "(c) stop and record open. NOTE: the sweep proved no EE word equals position 1..6, so the handler more likely "
      "writes an index into a table, a pointer, or a per-frame recomputation - the variable may still be found and "
      "read even if it is not position-valued.")

run("bp-01-screen", "jev_screen", {"text": EV, "purpose": "review breakpoint-road feasibility"})
run("bp-02-noul", "jev_noul", {"propositions": [
    "No GDB stub exists in this PCSX2 build.",
    "The debugger GUI cannot be driven headlessly with any verification.",
    "Static analysis of the menu input handler can find the highlight variable.",
    "A PCSX2 source build inside the container is too risky to attempt.",
    "The highlight variable, once named, can be verified by read-only PINE.",
], "context": EV})
run("bp-03-find", "jev_find", {"query": "the feasible headless path to the highlight variable",
    "candidates": [
        {"id": "input_handler", "text": "Static analysis: find the d-pad menu input handler and the variable it updates; verify live via PINE reads."},
        {"id": "source_build", "text": "Full PCSX2 source build + DebugServer patch for a TCP debug API."},
        {"id": "blind_gui", "text": "Drive the debugger GUI blind via RFB keys."},
        {"id": "stop", "text": "Record open; stop."},
    ], "top_k": 4})
run("bp-04-rerank", "jev_rerank", {"query": "rank the breakpoint-road options by feasibility headlessly",
    "candidates": [
        {"id": "input_handler", "text": "Static input-handler analysis + PINE verification (read-only, no build)."},
        {"id": "source_build", "text": "PCSX2 source build + DebugServer (hours, risky)."},
        {"id": "blind_gui", "text": "Blind debugger-GUI driving (no visibility)."},
        {"id": "stop", "text": "Record open."},
    ]})
run("bp-05-classify", "jev_classify", {"items": [
        {"id": "no_gdb", "text": "Zero gdb strings in the pcsx2-qt binary."},
        {"id": "no_visibility", "text": "F8 captures only the emulated screen, never Qt windows."},
        {"id": "win_only", "text": "PCSX2-MCP prebuilt is Windows-only."},
        {"id": "input_static", "text": "The input handler can be read in the decompilation export we already have."},
    ],
    "classes": [
        {"id": "hard_blocker", "description": "Rules the option out entirely. Example: no GDB stub in the binary."},
        {"id": "feasible", "description": "Can be done headlessly with tools present. Example: static analysis + PINE reads."},
        {"id": "heavy", "description": "Possible but costly/risky."},
    ],
    "purpose": "sort feasibility facts",
    "context": "Breakpoint road."})
run("bp-06-decide", "jev_decide", {
    "decision": "Which breakpoint-road option should we execute?",
    "evidence": EV,
    "priorities": "Headless, verifiable, smallest risk; read-only preferred; user approved proceeding; an honest open stays acceptable.",
    "candidates": [
        {"id": "input_handler", "description": "Static analysis of the menu input handler to name the highlight variable; verify live via read-only PINE across the six verified slots."},
        {"id": "source_build", "description": "Full PCSX2 source build + DebugServer patch inside the container."},
        {"id": "blind_gui", "description": "Drive the debugger GUI blind via RFB."},
        {"id": "stop", "description": "Record open without further attempts."},
    ],
    "requirements": ["Headless and verifiable", "Low risk to the running container", "Read-only unless approved"]})
run("bp-07-compare", "jev_compare", {
    "passage_a": "Static input-handler analysis + PINE verification (no build, no GUI).",
    "passage_b": "Full PCSX2 source build + DebugServer patch.",
    "aspects": ["risk", "verifiability", "cost"]})
_b8 = run("bp-08-extract", "jev_extract", {"document": EV,
    "fields": [
        {"id": "nogdb", "pattern": "ZERO gdb strings|no GDB stub", "description": "the GDB finding"},
        {"id": "f8", "pattern": "F8 screenshots capture only the emulated game screen", "description": "the visibility limit"},
        {"id": "winonly", "pattern": "Windows-only", "description": "the DebugServer limit"},
        {"id": "path", "pattern": "input handler.*PINE|PINE.*input handler", "description": "the feasible path"},
    ]})
_r = []
_f = _b8.get("fields", {}) if isinstance(_b8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("bp-09-audit", "jev_audit", {"source": EV, "records": _r or [{"id": "nogdb", "request": "extract nogdb", "value": "no GDB stub"}]})
run("bp-10-verify", "jev_verify", {"claims": [
    "This PCSX2 build contains no GDB stub.",
    "The debugger GUI cannot be verified headlessly (F8 sees only the game screen).",
    "The DebugServer prebuilt release is Windows-only.",
    "Static analysis of the input handler plus PINE verification is headless and read-only.",
], "evidence": EV})
run("bp-11-review", "jev_review", {"request": "Approve the input-handler static-analysis path.",
    "diff": "+ find the d-pad menu input handler in the decompilation export\n+ name the highlight variable it updates\n+ verify live via read-only PINE across six verified slots\n+ no build, no GUI driving, no guest writes",
    "tests": "PINE reads green; container paused and intact"})
run("bp-12-gate", "jev_gate", {"request": "Approve executing the input-handler path.",
    "diff": json.dumps({"path": "input-handler static analysis + PINE verify", "no_build": True, "read_only": True}, indent=1),
    "claims": [
        "No GDB stub or headless debugger API exists in this setup.",
        "The input-handler path is headless, verifiable, and read-only.",
        "A Linux DebugServer needs a full source build (deferred unless this fails).",
    ],
    "evidence": EV + "\n\nDecide: " + json.dumps(results.get("bp-06-decide", {}))[:1500]})

print("BP JEV DONE", len(results), "calls")
