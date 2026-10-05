#!/usr/bin/env python3
"""Job B execution — Jev decision battery (all 12 tools). Decides the remedy to lead with,
the proof bar, the policy class, and whether a live unpause is required.
Receipts: research/evidence/vehicle-completeness/jev-jobB/*.json
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


EVID = (
    "Job B (per-screen selector) is blocked because a PAUSED savestate carries no live pointers "
    "(arXiv 2503.15065; 2307.12060). Named: the livery store is entity+0x64 via FUN_00121e10; resolver "
    "FUN_00125640 over record base 0x233070+type*0x114; chain outer+4 -> +0x14c -> +0x174 = entity. "
    "New decompilation fact: FUN_0019c310 writes the gameflow pointer at outer+4 -> +0x14c, and its caller "
    "FUN_001de3d8 originates it. FUN_001c4540 iterates the car-entity list from a STATIC global "
    "(iRam00290278, EE ~0x290278; +8 = list head, +0xc = next). The cursor fn FUN_001c4a40 indexes "
    "DAT_00241b40 by a per-entity type byte. So at least one stable EE address (0x290278) can be read live. "
    "PCSX2 has: (a) in-emulator read/write BREAKPOINTS (CBreakPoints, BREAKPOINT_EE/IOP; iR5900.cpp "
    "dynarecMemcheck) - a debugger feature; (b) PINE IPC live guest memory read/write (PINE.cpp MsgRead8..64) "
    "exposed by the headless container helper (currently identity/save/load at slot 28193). "
    "Constraint: run EVERYTHING headless (Docker + Xvfb, fr2-recovery-headless); the user is using the host - "
    "no focus stealing on the Mac. Prior constraint from handoff: ordinary controller input + read-only/capture "
    "APIs only, no guest-memory writes/cheats/patches.")

run("jb-01-screen", "jev_screen", {"text": EVID, "purpose": "Job B remedy evidence for the decision battery"})
run("jb-02-noul", "jev_noul", {"propositions": [
    "Extending the headless PINE helper with read-only memory ops (no writes) is within the project's read-only constraint.",
    "A live unpause is required to see the per-screen selector word, because static globals alone do not track the highlight.",
    "PCSX2 read/write breakpoints are a debugger feature distinct from ordinary controller input.",
    "Reading the static entity-list global at ~0x290278 via PINE can locate the car structure without any breakpoint.",
    "The proof bar for Job B should require a live read that varies with the highlight AND is decompilation-reachable.",
    "A value-only match in the live memory is sufficient proof.",
], "context": EVID})
run("jb-03-find", "jev_find", {"query": "the remedy most likely to isolate the per-screen selector headlessly and read-only",
    "candidates": [
        {"id": "pine_live", "text": "Extend the headless PINE helper with read-only reads and read the static entity-list global plus the chain live."},
        {"id": "breakpoint", "text": "Use a PCSX2 read/write breakpoint in the headless instance to catch the writing instruction."},
        {"id": "pointer_scan", "text": "Pointer-scan the guest memory (PINCE/libptrscan)."},
        {"id": "stop", "text": "Record Job B open and stop."},
    ], "top_k": 4})
run("jb-04-rerank", "jev_rerank", {"query": "next concrete headless action to reach the selector word",
    "candidates": [
        {"id": "pine_read32", "text": "Add read32/read64/read_range to the PINE helper and read the entity-list global + candidate chain words in the live state."},
        {"id": "pine_poll", "text": "Unpause via PINE/keys and poll candidate words across three car selections."},
        {"id": "bp", "text": "Arm a read breakpoint on the highlight draw path in the headless instance."},
        {"id": "more_decomp", "text": "Trace FUN_001de3d8 to find the exact static root before any live read."},
    ]})
run("jb-05-classify", "jev_classify", {"items": [
        {"id": "pine_read", "text": "Headless PINE read-only memory read of guest EE RAM."},
        {"id": "breakpoint", "text": "PCSX2 read/write breakpoint (debugger) in the headless instance."},
        {"id": "pointer_scan", "text": "Pointer scan on guest memory."},
        {"id": "keys", "text": "Ordinary controller key delivery via the hidden browser/noVNC."},
    ],
    "classes": [
        {"id": "read_only_ok", "description": "Reads guest state without writing or patching; within the stated read-only constraint. Example: PINE read32."},
        {"id": "debugger_feature", "description": "A debugger facility (breakpoints/watchpoints) that modifies no guest memory but is a new tool class."},
        {"id": "needs_confirm", "description": "Writes guest memory or patches code; needs explicit confirmation."},
    ],
    "purpose": "sort the remedies by the project constraint",
    "context": "Job B headless remedies."})
run("jb-06-decide", "jev_decide", {
    "decision": "Which remedy should the headless Job B execution lead with?",
    "evidence": EVID,
    "priorities": "Headless only (no host focus); read-only is preferred; must be able to name a decompilation-reachable address; a definitive recorded outcome is acceptable if the selector cannot be isolated; the user approved proceeding with the recommendations.",
    "candidates": [
        {"id": "pine_read_then_poll", "description": "Extend PINE with read-only reads, read the static entity-list global + chain live; if that names nothing, unpause and poll across three car selections."},
        {"id": "breakpoint_first", "description": "Lead with a PCSX2 read breakpoint in the headless instance."},
        {"id": "decomp_first", "description": "Trace FUN_001de3d8 fully to the exact static root before any live read."},
        {"id": "stop_record_open", "description": "Record Job B open without a live read."},
    ],
    "requirements": ["Runs headless", "Names a decompilation-reachable address", "Does not write guest memory"]})
run("jb-07-compare", "jev_compare", {
    "passage_a": "PINE read-only live guest-memory read (PINE.cpp MsgRead8..64).",
    "passage_b": "PCSX2 read/write breakpoint (CBreakPoints, memchecks).",
    "aspects": ["writes guest memory", "new tool class", "headless feasibility", "what it names"]})
_j8 = run("jb-08-extract", "jev_extract", {"document": EVID,
    "fields": [
        {"id": "store", "pattern": "entity\\+0x64", "description": "the selector store offset"},
        {"id": "chain", "pattern": "outer\\+4 -> \\+0x14c -> \\+0x174", "description": "the gameflow pointer chain"},
        {"id": "global", "pattern": "0x290278", "description": "the static entity-list global"},
        {"id": "slot", "pattern": "slot 28193", "description": "the PINE slot"},
    ]})
_r = []
_f = _j8.get("fields", {}) if isinstance(_j8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("jb-09-audit", "jev_audit", {"source": EVID, "records": _r or [{"id": "store", "request": "extract store", "value": "entity+0x64"}]})
run("jb-10-verify", "jev_verify", {"claims": [
    "A paused savestate carries no live pointers, which blocks the per-screen selector.",
    "FUN_001c4540 iterates the car-entity list from a static global at about 0x290278.",
    "PCSX2 PINE exposes read-only guest memory access over IPC.",
    "The headless container helper currently exposes only identity/save/load.",
    "A value-only match in live memory is sufficient proof of the selector.",
], "evidence": EVID})
run("jb-11-review", "jev_review", {"request": "Lead the headless Job B execution with read-only PINE live memory reads.",
    "diff": "+ add read8/16/32/64 + read_range to the headless PINE helper (no writes)\n"
            "+ read the static entity-list global (~0x290278) and the gameflow chain in the live instance\n"
            "+ if unnamed, unpause headlessly and poll candidate words across three car selections\n"
            "+ proof bar: live read varies with highlight AND decompilation-reachable; else record open",
    "tests": "existing verifiers stay green; container remains headless"})
run("jb-12-gate", "jev_gate", {"request": "Approve leading Job B with read-only PINE live reads, headless.",
    "diff": "+ PINE read-only ops (no writes); static global + chain read; optional headless unpause + poll\n+ never write guest memory\n+ record open if not isolated",
    "claims": [
        "The plan runs headless and writes no guest memory.",
        "The plan can name a decompilation-reachable address.",
        "The plan keeps a recorded-open outcome available.",
    ],
    "evidence": EVID + "\n\nDecide: " + json.dumps(results.get("jb-06-decide", {}))[:1500]})

print("JOB B JEV DONE", len(results), "calls")
