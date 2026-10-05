#!/usr/bin/env python3
"""Grill COMPLETE confirm: the fully-specified plan (Q1-Q13 + C default) through all 12 tools.
Receipts: research/evidence/vehicle-completeness/jev-grill/z-*.json
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


PLAN = (
    "COMPLETE PLAN — Ford Racing 2 (SLES_517.05) car-model recovery, workspace R. Every decision Q1-Q13 is now "
    "fixed; the residual branches are closed.\n"
    "ORDER A -> B -> C. Stop only when all three reach a definite outcome (7b); C required. Claim ceiling: "
    "render_fidelity_complete false on every artifact; partial claims only; no completion gate passes; a Jev gate "
    "escalate is an acceptable recorded outcome.\n"
    "A — RECORDED VERDICT (no code change): the executable binds :SOUNDBANK_TYPE by name (config-key table @0x24af68, "
    "descriptor table @0x24afe8, same index 0..7 CAR1..CAR8; FUN_001d7950 -> car struct +0x40; FUN_00165b10 -> "
    "carN_snd; FUN_001408d8 loads carN_snd.msh/.msb; the first numeric field is a discarded bank ordinal). "
    "build_reference.py's name-based CAR_SND_CARn -> carN_snd rule is CONSISTENT, no off-by-one. Record in a "
    "sound-index reconciliation receipt; do NOT change the green T2 verifier.\n"
    "B — SELECTOR: proof bar = a decompilation-reachable address, never a value-only match. Trace FUN_0019eb90 -> "
    "FUN_00125640 -> FUN_00121e10. Named: the livery-label selector is stored at entity+0x64 (FUN_00121e10), from the "
    "packed selector FUN_00125640 returns out of record base 0x233070+type*0x114 (count +0xbc, list +0x90). ROOTING "
    "(Q12a): find the bootstrap global that stores the gameflow pointer via decompilation (primary), read it in each "
    "of slots 102/103/104, and follow outer+4 -> +0x14c -> +0x174 to entity; if the global is not cleanly identified, "
    "fall back INSIDE the same bounded pass to scanning for the entity struct via its flags 0x1cd0 at +0x60; then read "
    "entity+0x64 (expected the same DEFAULT value, non-distinguishing). Then the BOUNDED INDIRECTION PASS (Q10a): ONE "
    "bounded read of the DAT_00241b40 indexed cursor and ONE walk of the FUN_001c4a40 caller chain; if the cursor's "
    "selected-index field is not identified, record the per-screen CAR highlight cursor OPEN and move to C. B resolved "
    "= a DEFINITE OUTCOME: entity+0x64 read and recorded, plus the cursor recorded open if the pass names nothing.\n"
    "C — DISPLAY NAMES (Q11a + default): extend tools/resolve_display_names.py keeping BOTH assertions in ONE tool "
    "and receipt: the existing 3-pair check (T3 regression, preserved) AND a full car-keyed table asserting ALL 35 "
    "cars resolve (not just TXT_CARS_* keys), with negative controls (unknown key unresolved; apostrophe byte-exact "
    "from the archive) and a jev_gate. '136-entry display-name table' is a misnomer.\n"
    "CLOSURE (Q13a): one receipt + jev_gate per thread (escalate acceptable) plus a single session completion report "
    "listing the three definite outcomes. CONSTRAINTS: never print credentials; new files in R not S; close tickets "
    "only on real tool output.")

run("z-01-screen", "jev_screen", {"text": PLAN, "purpose": "final confirmation of the complete, branch-closed plan"})
run("z-02-noul", "jev_noul", {"propositions": [
    "The complete plan now leaves no decision silently assumed on any of the three threads.",
    "The gameflow rooting is specified with a primary and a fallback inside one bounded pass.",
    "The closure artifact is specified (receipt + jev_gate per thread plus a completion report).",
    "The plan keeps every artifact's render_fidelity_complete false.",
    "The plan is executable end to end without a positive-find requirement.",
    "A branch still remains that could block the session.",
], "context": PLAN})
run("z-03-find", "jev_find", {"query": "any decision still silently assumed in the complete plan",
    "candidates": [
        {"id": "rooting", "text": "Rooting is specified: bootstrap global primary, sig_scan fallback, in one bounded pass."},
        {"id": "closure", "text": "Closure is specified: receipt + jev_gate per thread plus a completion report."},
        {"id": "c_all35", "text": "C asserts all 35 cars with controls."},
        {"id": "hidden", "text": "A branch nothing in the plan decides."},
    ], "top_k": 4})
run("z-04-rerank", "jev_rerank", {"query": "how well the complete plan answers the residual-branch findings",
    "candidates": [
        {"id": "q12_closes", "text": "Q12a closes the gameflow rooting branch."},
        {"id": "q13_closes", "text": "Q13a closes the closure-artifact branch."},
        {"id": "c_default", "text": "C's all-35 row set with controls closes C's row/control branch."},
        {"id": "still_open", "text": "Some branch is still unspecified."},
    ]})
run("z-05-classify", "jev_classify", {"items": [
        {"id": "A", "text": "Sound verdict recorded consistent; no verifier change."},
        {"id": "B", "text": "Root via bootstrap global (fallback sig_scan), read entity+0x64, one bounded pass, definite outcome."},
        {"id": "C", "text": "One tool: 3-pair regression + all 35 cars + controls + gate."},
        {"id": "closure", "text": "Receipt + jev_gate per thread plus a completion report."},
    ],
    "classes": [
        {"id": "specified", "description": "The plan states exactly what to do and what outcome counts. Example: the rooting primary+fallback."},
        {"id": "vague", "description": "Still open to interpretation; could block the session."},
    ],
    "purpose": "confirm every plan step is now specified, none vague",
    "context": "Final confirmation."})
run("z-06-decide", "jev_decide", {
    "decision": "Is the complete plan ready to act on with no branch silently assumed?",
    "evidence": PLAN,
    "priorities": "No silently-assumed branch; executable end to end; partial claims preserved.",
    "candidates": [
        {"id": "ready", "description": "The plan is complete and ready to execute as written."},
        {"id": "still_open", "description": "A branch remains unspecified."},
        {"id": "gather_more", "description": "More evidence is needed before acting."},
    ],
    "requirements": ["Leaves no decision silently assumed", "Executable end to end", "Keeps partial claims"]})
run("z-07-compare", "jev_compare", {
    "passage_a": "Round-5 finding: the plan omitted how to root the gameflow chain and what proves each thread resolved.",
    "passage_b": "Q12a/Q13a and the C default now specify rooting (primary+fallback), closure (receipt+gate+report), and C's rows/controls.",
    "aspects": ["whether the earlier gaps are closed", "remaining assumptions", "readiness"]})
_z8 = run("z-08-extract", "jev_extract", {"document": PLAN,
    "fields": [
        {"id": "rooting", "pattern": "bootstrap global that stores the gameflow pointer", "description": "the rooting primary"},
        {"id": "fallback", "pattern": "fall back INSIDE the same bounded pass", "description": "the rooting fallback"},
        {"id": "closure", "pattern": "one receipt \\+ jev_gate per thread", "description": "the closure artifact"},
        {"id": "c_rows", "pattern": "ALL 35 cars resolve", "description": "C's row set"},
    ]})
_r = []
_f = _z8.get("fields", {}) if isinstance(_z8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("z-09-audit", "jev_audit", {"source": PLAN, "records": _r or [{"id": "rooting", "request": "extract rooting", "value": "bootstrap global that stores the gameflow pointer"}]})
run("z-10-verify", "jev_verify", {"claims": [
    "The complete plan specifies rooting the gameflow chain via a bootstrap global with a sig_scan fallback in one bounded pass.",
    "The complete plan specifies the closure artifact as one receipt + jev_gate per thread plus a completion report.",
    "C asserts all 35 cars resolve with unknown-key and apostrophe controls.",
    "The complete plan keeps render_fidelity_complete false on every artifact.",
    "The complete plan has no silently-assumed branch remaining.",
], "evidence": PLAN})
run("z-11-review", "jev_review", {"request": "Adopt the complete plan for the next session.",
    "diff": "+ A: record consistent sound verdict; no verifier change\n"
            "+ B: root via bootstrap global (fallback sig_scan); read entity+0x64; one bounded pass; definite outcome\n"
            "+ C: one tool, 3-pair regression + all 35 cars + controls + gate\n"
            "+ closure: receipt + jev_gate per thread + completion report; render_fidelity_complete false",
    "tests": "verify_config_data_sound VERIFY OK; resolve_display_names VERIFY OK; test_retained_packet_evidence OK"})
run("z-12-gate", "jev_gate", {"request": "Adopt the complete plan: A recorded verdict, B rooted definite outcome, C all-35 extension, closure per thread; render_fidelity_complete false.",
    "diff": json.dumps({"order": ["A", "B", "C"], "A": "record consistent verdict", "B": "root bootstrap global + fallback; read entity+0x64; bounded pass", "C": "one tool: 3-pair + all 35 cars + controls", "closure": "receipt+gate per thread + report", "ceiling": "render_fidelity_complete false"}, indent=1),
    "claims": [
        "The plan specifies rooting and closure, leaving no silently-assumed branch.",
        "B is deliverable as a definite outcome.",
        "render_fidelity_complete stays false on every artifact.",
    ],
    "evidence": PLAN + "\n\nDecide: " + json.dumps(results.get("z-06-decide", {}))[:1500]})

print("GRILL COMPLETE DONE", len(results), "calls")
