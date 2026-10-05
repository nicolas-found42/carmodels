#!/usr/bin/env python3
"""Grill round 3: under stop-condition 7b (all three threads resolved), what 'B
resolved' means given the selector is likely un-isolatable; the C deliverable shape;
and sequencing. All 12 Jev tools. Receipts: .../jev-grill/r3-*.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-grill")
os.makedirs(OUT, exist_ok=True)
results = {}


def rd(rel):
    return open(os.path.join(R, rel), encoding="utf-8").read()


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
    print(f"--- {tag:10} {tool:14} action={act}")
    return c


SETTLED = (
    "Settled for the next session: order A (sound index) -> B (selector) -> C (display-name table). B proof bar = a "
    "decompilation-reachable address, not a value match. Claim ceiling = render_fidelity_complete false on every "
    "artifact, partial claims only. B method = decompilation-first trace of FUN_0019eb90 -> FUN_00125640 -> "
    "FUN_00121e10, then ONE time-boxed indirection pass before recording the thread open. A method = settle with a "
    "definite verdict (consistent | off_by_one | undecidable) from the soundman consumer. Stop condition 7b = do NOT "
    "stop until all three threads are resolved (C now required, not optional).")
CONFLICT = (
    "Tension: Jev rounds 1-2 put 'an isolated EE word that tracks the highlight exists' at 0.13 likely-false and "
    "contradicted 'the highlight is stored as a plain integer word in EE main RAM' (0.88); the fallback allows "
    "recording the selector thread open. But stop-condition 7b says do not stop until all three threads are resolved. "
    "If B yields no positive find, 'resolved' must mean a definite outcome (named address OR evidenced open) or the "
    "session cannot end.")
CFACTS = (
    "C target: Jev round-1 classify labeled C breadth_only, auto. The '136' figure refers either to the 35 cars or to "
    "the 136 liveries (exact meaning pending a fact check). LANGUAGE/tlate_en.dat;1 holds TXT_CARS_* keys that "
    "build_reference.py already parses; T3 already resolved three pairs (COUPE_1949/THUNDERBIRD_2002/FORTYNINE).")

EVID = SETTLED + "\n\n" + CONFLICT + "\n\n" + CFACTS

run("r3-01-screen", "jev_screen", {"text": EVID, "purpose": "round-3 decision evidence for the resolved-definition question"})
run("r3-02-noul", "jev_noul", {"propositions": [
    "Under stop-condition 7b, 'B resolved' must mean a definite outcome (named address OR evidenced open), not necessarily a positive find.",
    "If B requires a positive find, the session can be blocked indefinitely given the selector's low likelihood.",
    "C (the display-name table) deserves its own new ticket and tool rather than reopening the closed T3.",
    "The order A -> B -> C is better than A -> C -> B.",
    "All three threads can be brought to a definite outcome within one session.",
    "Reopening T3 is the cleanest way to deliver C.",
], "context": EVID})
run("r3-03-find", "jev_find", {"query": "the correct meaning of 'resolved' for the selector thread under stop-condition 7b",
    "candidates": [
        {"id": "definite_outcome", "text": "Resolved = a named decompilation-reachable address OR an evidenced recorded-open outcome."},
        {"id": "positive_find", "text": "Resolved = the selector word was positively isolated."},
        {"id": "blocked", "text": "If no positive find, the session is blocked and the decision escalates."},
        {"id": "drop_thread", "text": "Resolved = the selector thread is dropped from scope."},
    ], "top_k": 4})
run("r3-04-rerank", "jev_rerank", {"query": "best deliverable shape for C (the full display-name table)",
    "candidates": [
        {"id": "new_tool_t4", "text": "A new tool resolve_all_display_names.py and a new ticket T4, mirroring T2/T3, with its own receipt and negative controls."},
        {"id": "extend_t3", "text": "Extend the existing resolve_display_names.py to the full table."},
        {"id": "reopen_t3", "text": "Reopen the closed T3 ticket and widen its scope."},
        {"id": "skip_c", "text": "Do not build C; keep the three-pair result."},
    ]})
run("r3-05-classify", "jev_classify", {"items": [
        {"id": "definite_outcome", "text": "'Resolved' = named address OR evidenced open for the selector thread."},
        {"id": "positive_find", "text": "'Resolved' = the selector word positively isolated."},
        {"id": "new_t4", "text": "C delivered as a new tool + ticket T4."},
        {"id": "extend_t3", "text": "C delivered by extending the T3 tool."},
    ],
    "classes": [
        {"id": "fits_partial_claims", "description": "Consistent with the project's partial-claims-only, render-fidelity-false policy. Example: recording an evidenced open."},
        {"id": "overclaims_or_blocks", "description": "Either asserts a positive result that may not exist or blocks the session on it."},
        {"id": "neutral", "description": "Consistent with both."},
    ],
    "purpose": "test the round-3 options against the claim ceiling",
    "context": "Round-3 decisions under 7b."})
run("r3-06-decide", "jev_decide", {
    "decision": "Under stop-condition 7b, what does 'B (selector) resolved' mean?",
    "evidence": EVID,
    "priorities": "Keep partial-claims-only and render_fidelity_complete false; never assert a find that evidence does not support; allow the session to end on a definite recorded outcome; a Jev gate escalate is acceptable.",
    "candidates": [
        {"id": "definite_outcome", "description": "'Resolved' = a named decompilation-reachable address, OR an evidenced recorded-open outcome after the time-boxed indirection pass."},
        {"id": "positive_find", "description": "'Resolved' = the selector word was positively isolated; block otherwise."},
        {"id": "escalate_if_no_find", "description": "If no positive find, stop the session and escalate the open to the human."},
    ],
    "requirements": [
        "Lets the session end on a definite recorded outcome",
        "Does not assert an unsupported find",
        "Keeps render_fidelity_complete false",
    ]})
run("r3-07-compare", "jev_compare", {
    "passage_a": "Stop-condition 7b: do not stop until all three threads are resolved.",
    "passage_b": "Fallback: if the trace and one indirection pass name nothing, record the selector thread open.",
    "aspects": ["what 'resolved' means", "whether the two conflict", "effect on session end"]})
_r8 = run("r3-08-extract", "jev_extract", {"document": EVID,
    "fields": [
        {"id": "order", "pattern": "order A[^.]*\\.", "description": "the settled thread order"},
        {"id": "proof_bar", "pattern": "decompilation-reachable address, not a value match", "description": "the B proof bar"},
        {"id": "ceiling", "pattern": "render_fidelity_complete false", "description": "the claim ceiling phrase"},
        {"id": "stop", "pattern": "do NOT stop until all three threads are resolved", "description": "the stop condition"},
    ]})
_r = []
_f = _r8.get("fields", {}) if isinstance(_r8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("r3-09-audit", "jev_audit", {"source": EVID, "records": _r or [{"id": "stop", "request": "extract stop", "value": "do NOT stop until all three threads are resolved"}]})
run("r3-10-verify", "jev_verify", {"claims": [
    "The settled order is A -> B -> C.",
    "The B proof bar is decompilation-reachability, not a value match.",
    "The claim ceiling keeps render_fidelity_complete false on every artifact.",
    "Stop-condition 7b requires all three threads resolved before stopping.",
    "Under 7b, 'B resolved' currently means a positive isolated selector word.",
], "evidence": EVID})
run("r3-11-review", "jev_review", {"request": "Adopt round-3 decisions: define 'resolved' for B, shape C, keep the ceiling.",
    "diff": "+ B resolved := named decompilation-reachable address OR evidenced recorded-open\n"
            "+ C delivered as a new tool + ticket T4 (mirrors T2/T3)\n"
            "+ order A -> B -> C; render_fidelity_complete stays false throughout",
    "tests": "existing verifiers stay green: verify_config_data_sound VERIFY OK; resolve_display_names VERIFY OK; test_retained_packet_evidence OK"})
run("r3-12-gate", "jev_gate", {"request": "Adopt: B resolved = definite outcome; C = new tool + T4; order A->B->C.",
    "diff": json.dumps({"B_resolved": "definite outcome (named address OR evidenced open)", "C": "new tool resolve_all_display_names.py + ticket T4", "order": ["A", "B", "C"]}, indent=1),
    "claims": [
        "B resolved is defined as a definite outcome, not a required positive find.",
        "C is delivered as a new tool and ticket.",
        "render_fidelity_complete stays false throughout.",
    ],
    "evidence": EVID + "\n\nDecide: " + json.dumps(results.get("r3-06-decide", {}))[:1500]})

print("GRILL ROUND-3 DONE", len(results), "calls")
