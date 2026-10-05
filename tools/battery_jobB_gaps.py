#!/usr/bin/env python3
"""Mark number — GAP-CLOSURE Jev battery (all 12 tools). Evaluates each gap found while
searching for the mark, with the solutions gathered from web/GitHub research.
Receipts: research/evidence/vehicle-completeness/jev-jobB/gap-*.json
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
    print(f"--- {tag:10} {tool:14} action={act}")
    return c


GAPS = (
    "GAPS blocking access to the mark number, and the solutions found by research:\n"
    "G1 (fundamental): the mark is NOT stored in any savestate as a readable integer (exhaustive: every member, "
    "every width, 0 hits). => it is computed, not stored; the only way is a debugger breakpoint on the draw/input "
    "code, or a live value scan.\n"
    "G2 (control): PINE has NO pause/resume opcode (only read/write/save/load/status); the container boots into a "
    "PAUSED savestate. => need a headless way to unpause. Solution: xdotool sends the emulator's ESC key to the "
    "container's own Xvfb display (:99) - headless, no host focus.\n"
    "G3 (headless input): the container image has no X tools (no xdotool/xte/wmctrl). => install xdotool in the "
    "container (apt) and drive :99; this is the standard Xvfb+xdotool Docker pattern. The proven existing path is "
    "the hidden Playwright->noVNC browser, but it cannot drive the debugger UI reliably.\n"
    "G4 (headless debugger): PCSX2's built-in debugger (breakpoints/watchpoints) has no IPC/remote API. Solutions: "
    "(a) pcsx2's DebugServer patch from hkmodd/PCSX2-MCP - a ~1-file GPL patch giving a TCP debug API (breakpoints, "
    "registers, memory diff); the prebuilt release is WINDOWS-ONLY (pcsx2-qt.exe/MSVC), so on Linux it needs a "
    "PCSX2 source build + the patch; (b) drive the built-in debugger GUI headlessly with xdotool; (c) a live value "
    "scan (PINCE/scanmem) against the emulator process.\n"
    "No native PCSX2 GDB stub exists (forum request only).\n"
    "Constraint: headless only, no host focus; read-only preferred; a container image change and a debugger feature "
    "are both policy changes that need user approval.")

run("gap-01-screen", "jev_screen", {"text": GAPS, "purpose": "review the gap/solution evidence before deciding"})
run("gap-02-noul", "jev_noul", {"propositions": [
    "The mark number is computed, not stored, so a saved state can never reveal it.",
    "Installing xdotool in the container is the cleanest headless input path.",
    "A debugger breakpoint is required to find the mark.",
    "hkmodd/PCSX2-MCP can be used as-is on Linux.",
    "A live value scan (PINCE/scanmem) could find the mark without a breakpoint.",
    "Every gap has a solution that needs a policy change the user must approve.",
], "context": GAPS})
run("gap-03-find", "jev_find", {"query": "the single best headless path to the mark number",
    "candidates": [
        {"id": "xdotool_debugger", "text": "Install xdotool in the container and drive PCSX2's built-in debugger on :99 to read the watchpoint that touches the highlight."},
        {"id": "build_debugserver", "text": "Build PCSX2 from source + the DebugServer patch for a headless TCP debug API."},
        {"id": "pince_scan", "text": "Run PINCE/scanmem against the emulator to narrow the value live."},
        {"id": "none", "text": "No headless path exists."},
    ], "top_k": 4})
run("gap-04-rerank", "jev_rerank", {"query": "rank the headless solutions by cost and reliability",
    "candidates": [
        {"id": "xdotool_debugger", "text": "apt install xdotool + drive the debugger UI on :99 (small image change)."},
        {"id": "build_debugserver", "text": "Full PCSX2 Linux build + DebugServer patch (hours; heavy)."},
        {"id": "pince_scan", "text": "Value scan against the process (no breakpoint; may not resolve a computed value)."},
        {"id": "playwright_vnc", "text": "Existing hidden Playwright->noVNC browser (works for keys, awkward for the debugger UI)."},
    ]})
run("gap-05-classify", "jev_classify", {"items": [
        {"id": "g3_xdotool", "text": "Install xdotool in the container; send keys to :99."},
        {"id": "g4_debugserver", "text": "hkmodd/PCSX2-MCP DebugServer patch; Windows prebuilt, Linux needs a source build."},
        {"id": "g2_pine", "text": "PINE pause/resume."},
        {"id": "existing_vnc", "text": "The hidden Playwright->noVNC browser."},
    ],
    "classes": [
        {"id": "viable_solution", "description": "A known, working approach for this Linux/headless setup. Example: xdotool + Xvfb."},
        {"id": "unavailable", "description": "Does not apply to this platform or does not exist. Example: PINE pause, Windows-only release."},
        {"id": "heavy_solution", "description": "Works but needs a large build or fork."},
    ],
    "purpose": "sort the gap solutions by viability",
    "context": "Mark-number gap closure."})
run("gap-06-decide", "jev_decide", {
    "decision": "What is the recommended headless path to the mark number, given the gaps?",
    "evidence": GAPS,
    "priorities": "Headless, no host focus; smallest change first; read-only preferred; a debugger feature and a container image change both need user approval; an honest open is acceptable.",
    "candidates": [
        {"id": "xdotool_debugger", "description": "Approve a container image change (xdotool) and a debugger pass: install xdotool, unpause via ESC on :99, arm a read/write watchpoint in PCSX2's debugger on the highlight path, read the value."},
        {"id": "build_debugserver", "description": "Build PCSX2 + DebugServer for a headless TCP debug API."},
        {"id": "pince_scan", "description": "Live value scan only (no breakpoint)."},
        {"id": "stop", "description": "Record the mark open; no change."},
    ],
    "requirements": ["Runs headless", "Small and reversible", "Needs at most one approval"]})
run("gap-07-compare", "jev_compare", {
    "passage_a": "The container's Xvfb with xdotool (small image change).",
    "passage_b": "A PCSX2 source build + DebugServer patch (large).",
    "aspects": ["setup cost", "reliability", "reversibility"]})
_g8 = run("gap-08-extract", "jev_extract", {"document": GAPS,
    "fields": [
        {"id": "pine_pause", "pattern": "PINE has NO pause/resume opcode", "description": "the PINE pause gap"},
        {"id": "xdotool", "pattern": "install xdotool in the container", "description": "the xdotool solution"},
        {"id": "debugserver", "pattern": "hkmodd/PCSX2-MCP", "description": "the DebugServer project"},
        {"id": "windows", "pattern": "WINDOWS-ONLY", "description": "the platform limit"},
    ]})
_r = []
_f = _g8.get("fields", {}) if isinstance(_g8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("gap-09-audit", "jev_audit", {"source": GAPS, "records": _r or [{"id": "xdotool", "request": "extract xdotool", "value": "install xdotool in the container"}]})
run("gap-10-verify", "jev_verify", {"claims": [
    "The mark is not stored in any savestate (exhaustive, 0 hits).",
    "PINE has no pause/resume opcode.",
    "xdotool on the container's Xvfb is a headless input path that touches no host focus.",
    "hkmodd/PCSX2-MCP's prebuilt release runs on Linux.",
    "A debugger feature and a container image change are both needed.",
], "evidence": GAPS})
run("gap-11-review", "jev_review", {"request": "Recommend the headless path: small image change (xdotool) + a debugger pass.",
    "diff": "+ G1: mark is computed, needs a debugger breakpoint\n+ G2: PINE has no pause; use xdotool ESC on :99\n+ G3: install xdotool in the container (small, reversible)\n+ G4: drive PCSX2's debugger or build DebugServer\n+ both need user approval; nothing done without it",
    "tests": "container stays headless; no host focus"})
run("gap-12-gate", "jev_gate", {"request": "Approve the recommended path and its two needed approvals.",
    "diff": json.dumps({"G2": "xdotool ESC on :99", "G3": "install xdotool", "G4": "debugger/watchpoint", "approvals": 2}, indent=1),
    "claims": [
        "Every gap has a known solution on Linux/headless.",
        "The smallest path needs one image change (xdotool) and one debugger pass.",
        "Neither is done without user approval.",
    ],
    "evidence": GAPS + "\n\nDecide: " + json.dumps(results.get("gap-06-decide", {}))[:1500]})

print("GAP JEV DONE", len(results), "calls")
