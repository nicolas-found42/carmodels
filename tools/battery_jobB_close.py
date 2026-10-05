#!/usr/bin/env python3
"""Job B — closing Jev battery (all 12 tools): gate the recorded-open outcome honestly.
Receipts: research/evidence/vehicle-completeness/jev-jobB/close-*.json
"""
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


JOB = rd("research/evidence/job-b-live/selector-live-findings.json")
EXEC = ("Job B headless execution, read-only: extended the PINE helper with read opcodes (MsgRead8/16/32/64, "
        "no writes); loaded each existing savestate (102/103/104) live in the headless container; traversed the "
        "live entity chain via PINE (static global 0x290278 -> manager 0x473d70 -> 6 car entities at node+0x10); "
        "confirmed the named livery store is a float at entity+0x64; then exhaustively scanned all three 32 MiB "
        "EE images for the highlight tuples. RESULT: (1,5,4) has 0 hits at width 8/16/32; (0,4,3) has 0 u32 hits "
        "and 97 u8 noise hits. The per-screen highlight is NOT stored as a readable EE integer or pointer. "
        "Job B stays a recorded-open definite outcome. The live chain and store are decompilation-reachable and named.")

run("close-01-screen", "jev_screen", {"text": EXEC, "purpose": "review the Job B finding as task data"})
run("close-02-noul", "jev_noul", {"propositions": [
    "The headless live PINE reads reached the car-entity chain without writing any guest memory.",
    "The per-screen highlight is not stored as a readable EE integer or pointer in the three savestates.",
    "Job B reached a definite recorded outcome (named store + recorded-open highlight).",
    "The exhaustive scan proves no EE word holds the highlight.",
    "The result overclaims by asserting the per-screen selector was isolated.",
], "context": EXEC + "\n\n" + JOB[:6000]})
run("close-03-find", "jev_find", {"query": "the strongest evidence supporting the recorded-open outcome",
    "candidates": [
        {"id": "zero154", "text": "The (1,5,4) highlight tuple has 0 hits at width 8, 16 and 32 across all three images."},
        {"id": "noise043", "text": "The (0,4,3) tuple has 0 u32 hits and only 97 u8 hits in VU-packet noise regions."},
        {"id": "chain", "text": "The live chain 0x290278 -> 0x473d70 -> 6 car entities resolves over read-only PINE."},
        {"id": "store", "text": "The named store entity+0x64 is a float (FUN_00121e10), read live."},
    ], "top_k": 4})
run("close-04-rerank", "jev_rerank", {"query": "which next step could still isolate a per-screen selector",
    "candidates": [
        {"id": "live_breakpoint", "text": "A PCSX2 read breakpoint on the highlight draw path (FUN_001c4a40) in the headless instance."},
        {"id": "keys_poll", "text": "Headless key delivery to move the highlight, polling candidate words live."},
        {"id": "menu_struct", "text": "Trace FUN_001c4a40's param_5 byte (puVar9 = entity+0x11) live across selections."},
        {"id": "stop", "text": "Stop; record open with the chain and store named."},
    ]})
run("close-05-classify", "jev_classify", {"items": [
        {"id": "zero154", "text": "0 hits for (1,5,4) at all widths."},
        {"id": "chain", "text": "Live chain resolves over read-only PINE."},
        {"id": "store", "text": "entity+0x64 is a float, read live."},
        {"id": "claim_isolated", "text": "The per-screen selector word was isolated."},
    ],
    "classes": [
        {"id": "supported_fact", "description": "A measured result the code produced. Example: 0 tuple hits."},
        {"id": "unsupported_claim", "description": "Asserts a find the evidence does not support."},
    ],
    "purpose": "separate measured facts from overclaims",
    "context": "Job B closing."})
run("close-06-decide", "jev_decide", {
    "decision": "Is Job B complete as a recorded-open definite outcome, or must more be tried?",
    "evidence": EXEC + "\n\n" + JOB[:6000],
    "priorities": "Honest partial claims; render_fidelity_complete false; do not assert an unsupported find; live read-only evidence is the bar; a recorded-open outcome is acceptable.",
    "candidates": [
        {"id": "record_open", "description": "Job B complete: live chain + store named, highlight recorded open (no EE word holds it)."},
        {"id": "live_breakpoint", "description": "Keep going: arm a headless read breakpoint on the draw path."},
        {"id": "keys_poll", "description": "Keep going: deliver keys headlessly and poll a wider set."},
    ],
    "requirements": ["Rests on measured evidence", "Does not assert an unsupported find", "Keeps partial claims"]})
run("close-07-compare", "jev_compare", {
    "passage_a": "The livery store is named at entity+0x64 (a float) and the live chain resolves via read-only PINE.",
    "passage_b": "The per-screen highlight is stored as an EE integer/pointer.",
    "aspects": ["evidence", "which is supported", "which is not"]})
_c8 = run("close-08-extract", "jev_extract", {"document": JOB,
    "fields": [
        {"id": "u32_154", "pattern": "\"tuple_154_hits\": [0-9]+", "description": "u32 (1,5,4) hit count"},
        {"id": "u32_043", "pattern": "\"tuple_043_hits\": [0-9]+", "description": "u32 (0,4,3) hit count"},
        {"id": "store", "pattern": "entity\\+0x64", "description": "the named store offset"},
        {"id": "manager", "pattern": "0x473d70", "description": "the live manager address"},
    ]})
_r = []
_f = _c8.get("fields", {}) if isinstance(_c8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("close-09-audit", "jev_audit", {"source": JOB[:8000], "records": _r or [{"id": "u32_154", "request": "extract u32_154", "value": "0"}]})
run("close-10-verify", "jev_verify", {"claims": [
    "The headless live PINE reads reached the car-entity chain without writing guest memory.",
    "The (1,5,4) highlight tuple has 0 hits at width 8, 16 and 32.",
    "The (0,4,3) tuple has 0 u32 hits and 97 u8 noise hits.",
    "The per-screen selector word was isolated.",
    "The named livery store entity+0x64 is a float, read live.",
], "evidence": EXEC + "\n\n" + JOB[:6000]})
run("close-11-review", "jev_review", {"request": "Record Job B as a definite outcome: live chain and store named, per-screen highlight recorded open.",
    "diff": "+ headless PINE read-only helper (MsgRead8/16/32/64; no writes)\n+ live chain 0x290278 -> 0x473d70 -> 6 car entities\n+ live store entity+0x64 float\n+ exhaustive scan: (1,5,4) 0 hits all widths; (0,4,3) u8 noise only\n+ record open; no value-only claim",
    "tests": "probe_selector_live.py VERIFY OK; existing verifiers green"})
run("close-12-gate", "jev_gate", {"request": "Gate Job B: recorded-open definite outcome via headless read-only live PINE.",
    "diff": json.dumps({"live_chain": "read-only", "store": "entity+0x64 float", "highlight": "recorded open", "tuple_154_hits": 0}, indent=1),
    "claims": [
        "Headless read-only PINE reached the live car-entity chain.",
        "The (1,5,4) highlight tuple has 0 hits at all widths; (0,4,3) is u8 noise only.",
        "The per-screen selector word was NOT isolated; the outcome is recorded open.",
        "render_fidelity_complete stays false.",
    ],
    "evidence": EXEC + "\n\n" + JOB[:8000]})

print("JOB B CLOSE DONE", len(results), "calls")
