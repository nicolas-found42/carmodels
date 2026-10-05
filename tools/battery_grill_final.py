#!/usr/bin/env python3
"""Grill FINAL confirm: the fully-specified plan (Q10a/Q11a locked) through all 12 tools.
Receipts: research/evidence/vehicle-completeness/jev-grill/f-*.json
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
                c = {"parse_error": str(ex), "raw": str(c)[:500]}
    except Exception as e:
        c = {"error": str(e)}
    json.dump({"args": args, "result": c}, open(os.path.join(OUT, tag + ".json"), "w"), indent=2)
    results[tag] = c
    act = c.get("action") or (c.get("recommendation") or {}).get("action") if isinstance(c, dict) else None
    print(f"--- {tag:9} {tool:14} action={act}")
    return c


PLAN = (
    "FINAL PLAN — Ford Racing 2 (SLES_517.05) car-model recovery, workspace R.\n"
    "ORDER: A -> B -> C. Stop only when all three reach a definite outcome (7b); C required.\n"
    "A — RECORDED VERDICT: the executable binds :SOUNDBANK_TYPE by name (config-key table @0x24af68, descriptor "
    "table @0x24afe8, same index 0..7 CAR1..CAR8; FUN_001d7950 -> car struct +0x40; FUN_00165b10 -> carN_snd; "
    "FUN_001408d8 loads carN_snd.msh/.msb; first numeric field is a discarded ordinal). build_reference.py's "
    "name-based CAR_SND_CARn -> carN_snd rule is CONSISTENT, no off-by-one. Record in a sound-index reconciliation "
    "receipt; do NOT change the green T2 verifier.\n"
    "B — SELECTOR: proof bar = a decompilation-reachable address, never a value-only match. Trace FUN_0019eb90 -> "
    "FUN_00125640 -> FUN_00121e10. The livery-label selector is named: FUN_00125640 returns a packed selector "
    "(low-16 resource-list ordinal) from record base 0x233070+type*0x114 (count +0xbc, list +0x90); FUN_00121e10 "
    "stores it at entity+0x64; the chain hangs off dynamic gameflow pointers outer+4 -> +0x14c -> +0x174. DO: read "
    "entity+0x64 via the chain in slots 102/103/104 (expected the same DEFAULT value, non-distinguishing). THEN the "
    "BOUNDED INDIRECTION PASS (Q10a): ONE bounded read of the DAT_00241b40 indexed cursor and one walk of the "
    "FUN_001c4a40 caller chain; if the cursor's selected-index field is not identified, record the per-screen CAR "
    "highlight cursor OPEN and move to C — no further chasing. B resolved = a DEFINITE OUTCOME: entity+0x64 read and "
    "recorded, plus the cursor recorded open if the pass names nothing (broaden_indirect once before recording open).\n"
    "C — DISPLAY NAMES (Q11a): extend tools/resolve_display_names.py keeping BOTH assertions in ONE tool and receipt: "
    "the existing 3-pair check (T3 regression, preserved) AND the full car-keyed TXT_CARS_* table (~35-39 rows). "
    "The three-pair T3 claim survives as a check, not superseded. The '136-entry display-name table' is a misnomer "
    "(136 is livery rows; display names are keyed by car).\n"
    "CEILING: render_fidelity_complete false on every artifact; partial claims only; no completion gate passes; a Jev "
    "gate escalate is an acceptable recorded outcome. CONSTRAINTS: never print credentials; new files in R not S; "
    "close tickets only on real tool output.")

run("f-01-screen", "jev_screen", {"text": PLAN, "purpose": "final confirmation of the fully-specified plan"})
run("f-02-noul", "jev_noul", {"propositions": [
    "The final plan leaves no decision silently assumed on any of the three threads.",
    "The bounded indirection pass (one read + one caller walk) makes 'record open' a terminating outcome.",
    "C's single tool with both assertions preserves the T3 three-pair claim.",
    "The final plan keeps every artifact's render_fidelity_complete false.",
    "The final plan is executable end to end without a positive-find requirement.",
    "The final plan still contains an open branch that would block the session.",
], "context": PLAN})
run("f-03-find", "jev_find", {"query": "any decision still silently assumed in the final plan",
    "candidates": [
        {"id": "bounded_pass", "text": "The indirection pass is defined as one bounded read plus one caller walk."},
        {"id": "c_single_tool", "text": "C keeps both assertions in one tool and receipt."},
        {"id": "b_outcome", "text": "B resolved is a definite outcome, cursor open allowed."},
        {"id": "hidden", "text": "A branch remains that nothing in the plan decides."},
    ], "top_k": 4})
run("f-04-rerank", "jev_rerank", {"query": "how well the final plan answers the capstone warning that a decision was silently assumed",
    "candidates": [
        {"id": "q10_closes", "text": "Q10a defines the indirection pass, closing the B method branch."},
        {"id": "q11_closes", "text": "Q11a defines C's shape, closing the C deliverable branch."},
        {"id": "still_open", "text": "Some branch is still unspecified."},
    ]})
run("f-05-classify", "jev_classify", {"items": [
        {"id": "A", "text": "Sound verdict recorded consistent (two tables + loader chain)."},
        {"id": "B", "text": "Read entity+0x64 via chain; one bounded indirection pass; record definite outcome."},
        {"id": "C", "text": "One tool, 3-pair regression + full car-keyed table (~35-39)."},
        {"id": "ceiling", "text": "render_fidelity_complete false; partial claims; escalate acceptable."},
    ],
    "classes": [
        {"id": "specified", "description": "The plan states exactly what to do and what outcome counts. Example: the bounded indirection pass."},
        {"id": "vague", "description": "Still open to interpretation; could block the session."},
    ],
    "purpose": "confirm every plan step is specified, none vague",
    "context": "Final confirmation."})
run("f-06-decide", "jev_decide", {
    "decision": "Is the final plan ready to act on with no branch silently assumed?",
    "evidence": PLAN,
    "priorities": "No silently-assumed branch; executable end to end; partial claims preserved.",
    "candidates": [
        {"id": "ready", "description": "The plan is complete and ready to execute as written."},
        {"id": "still_open", "description": "A branch remains unspecified."},
        {"id": "investigate", "description": "More evidence is needed before acting."},
    ],
    "requirements": ["Leaves no decision silently assumed", "Executable end to end", "Keeps partial claims"]})
run("f-07-compare", "jev_compare", {
    "passage_a": "Capstone warning: requirement 'leaves no decision silently assumed' was contradicted.",
    "passage_b": "Q10a/Q11a now define the indirection pass and C's shape.",
    "aspects": ["whether the earlier gap is closed", "remaining assumptions", "readiness"]})
_f8 = run("f-08-extract", "jev_extract", {"document": PLAN,
    "fields": [
        {"id": "pass", "pattern": "ONE bounded read of the DAT_00241b40 indexed cursor", "description": "the bounded indirection pass"},
        {"id": "c_shape", "pattern": "BOTH assertions in ONE tool and receipt", "description": "C's shape"},
        {"id": "outcome", "pattern": "a DEFINITE OUTCOME", "description": "the B resolved definition"},
        {"id": "ceiling", "pattern": "render_fidelity_complete false on every artifact", "description": "the ceiling"},
    ]})
_r = []
_f = _f8.get("fields", {}) if isinstance(_f8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("f-09-audit", "jev_audit", {"source": PLAN, "records": _r or [{"id": "outcome", "request": "extract outcome", "value": "a DEFINITE OUTCOME"}]})
run("f-10-verify", "jev_verify", {"claims": [
    "The final plan defines the indirection pass as one bounded read plus one caller walk.",
    "C is delivered by one tool holding both the 3-pair assertion and the full car-keyed table.",
    "B resolved is a definite outcome; a positive car-highlight cursor is not required.",
    "The final plan keeps render_fidelity_complete false on every artifact.",
    "The final plan has no silently-assumed branch remaining.",
], "evidence": PLAN})
run("f-11-review", "jev_review", {"request": "Adopt the final plan for the next session.",
    "diff": "+ A: record consistent sound verdict; no verifier change\n"
            "+ B: read entity+0x64 via chain; one bounded indirection pass; record definite outcome (cursor open allowed)\n"
            "+ C: one tool, 3-pair regression + full car-keyed table\n"
            "+ ceiling: render_fidelity_complete false; stop on three definite outcomes (7b)",
    "tests": "verify_config_data_sound VERIFY OK; resolve_display_names VERIFY OK; test_retained_packet_evidence OK"})
run("f-12-gate", "jev_gate", {"request": "Adopt the final plan: A recorded verdict, B definite outcome with a bounded pass, C one tool with both assertions; all three to a definite outcome (7b); render_fidelity_complete false.",
    "diff": json.dumps({"order": ["A", "B", "C"], "A": "record consistent verdict", "B": "read entity+0x64 + one bounded pass + record open if unnamed", "C": "one tool: 3-pair + car-keyed table", "ceiling": "render_fidelity_complete false"}, indent=1),
    "claims": [
        "The plan defines the indirection pass and C's shape, leaving no silently-assumed branch.",
        "B is deliverable as a definite outcome.",
        "render_fidelity_complete stays false on every artifact.",
    ],
    "evidence": PLAN + "\n\nDecide: " + json.dumps(results.get("f-06-decide", {}))[:1500]})

print("GRILL FINAL DONE", len(results), "calls")
