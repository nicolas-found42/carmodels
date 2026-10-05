#!/usr/bin/env python3
"""Grill capstone: the FULL consolidated plan through all 12 Jev tools.
Receipts: research/evidence/vehicle-completeness/jev-grill/c-*.json
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
    print(f"--- {tag:10} {tool:14} action={act}")
    return c


PLAN = (
    "CONSOLIDATED PLAN for the next session on the Ford Racing 2 (SLES_517.05) car-model recovery, workspace R "
    "(projects/carmodels).\n"
    "ORDER: A (sound index) -> B (selector) -> C (display names). Stop only when all three reach a definite outcome "
    "(stop condition 7b); C is required.\n"
    "A: RECORDED VERDICT. The executable binds :SOUNDBANK_TYPE by name: config-key table @0x24af68 (CAR1..CAR8_SOUND_FILE "
    "then CAR_GENERIC/UI_SOUNDS) and descriptor table @0x24afe8 (sounds\\car1_snd:0:0:5 .. car8_snd:7:35:5), same index "
    "0..7; FUN_001d7950 resolves the token to car struct +0x40; FUN_00165b10 indexes carN_snd by +0x40; FUN_001408d8 "
    "loads carN_snd.msh/.msb from the literal stem; the first numeric field is a discarded bank ordinal. Verdict: "
    "build_reference.py's name-based rule is CONSISTENT, no off-by-one. Action: record this verdict in a sound-index "
    "reconciliation receipt; do NOT change the green T2 verifier.\n"
    "B: PROOF BAR = a decompilation-reachable address, never a value-only match (value triangulation already returned 0 "
    "word hits and 97 noisy byte hits). METHOD: trace FUN_0019eb90 -> FUN_00125640 -> FUN_00121e10. The livery-label "
    "selector is named: FUN_00125640 returns a packed selector (low-16 resource-list ordinal) from record base "
    "0x233070+type*0x114 (count +0xbc, list +0x90); FUN_00121e10 stores it at entity+0x64; the chain hangs off the "
    "dynamic gameflow pointers outer+4 -> +0x14c -> +0x174. DO: read entity+0x64 via the chain in the three existing EE "
    "images (slots 102/103/104), expected the same DEFAULT value in all three (non-distinguishing by construction at "
    "DEFAULT livery). Then ONE time-boxed indirection pass for the per-screen CAR highlight cursor (FUN_001c4a40 over "
    "DAT_00241b40, caller open). 'B resolved' = a DEFINITE OUTCOME: the named livery store read AND recorded, plus the "
    "car-highlight cursor recorded open if the indirection pass names nothing. FALLBACK: broaden_indirect once before "
    "recording open.\n"
    "C: extend tools/resolve_display_names.py to the full car-keyed TXT_CARS_* set (~35-39 rows), delivered as its own "
    "receipt under vehicle-completeness/; the three-pair T3 claim stays intact and separate. The '136-entry display-name "
    "table' is a misnomer (136 is livery rows; display names are keyed by car).\n"
    "CEILING: render_fidelity_complete stays false on every artifact; partial claims only; no completion gate passes; a "
    "Jev gate escalate is an acceptable recorded outcome. CONSTRAINTS: never print credentials; new files in R not S; "
    "close tickets only on real tool output.")

run("c-01-screen", "jev_screen", {"text": PLAN, "purpose": "capstone review of the consolidated plan"})
run("c-02-noul", "jev_noul", {"propositions": [
    "The consolidated plan visits every open decision on the three threads.",
    "The plan keeps every artifact's render_fidelity_complete false.",
    "The plan can complete without re-running value-only triangulation.",
    "The plan's B is deliverable as a definite outcome even if the car-highlight cursor stays unnamed.",
    "The plan is internally consistent with the project's partial-claims-only policy.",
    "The plan asserts a positive selector find that the evidence does not support.",
], "context": PLAN})
run("c-03-find", "jev_find", {"query": "any remaining assumption in the plan that is not backed by evidence",
    "candidates": [
        {"id": "sound", "text": "The sound mapping is consistent, backed by two executable tables and the loader chain."},
        {"id": "store", "text": "The livery selector store at entity+0x64 is backed by FUN_00121e10."},
        {"id": "cursor", "text": "The per-screen car-highlight cursor is reachable by one indirection pass."},
        {"id": "c_rows", "text": "The car-keyed display-name set is ~35-39 rows; not 136."},
    ], "top_k": 4})
run("c-04-rerank", "jev_rerank", {"query": "rank the plan's work items by how well each is backed by existing evidence",
    "candidates": [
        {"id": "A_record", "text": "Record the sound-index consistent verdict."},
        {"id": "B_read_store", "text": "Read entity+0x64 via the chain in the three EE images."},
        {"id": "B_cursor", "text": "One indirection pass for the car-highlight cursor."},
        {"id": "C_extend", "text": "Extend the resolver to the car-keyed display names."},
    ]})
run("c-05-classify", "jev_classify", {"items": [
        {"id": "A", "text": "Record the sound verdict: consistent, no off-by-one, first numeric field discarded."},
        {"id": "B", "text": "Read the named livery store entity+0x64; record the car cursor open if unnamed."},
        {"id": "C", "text": "Extend the resolver to car-keyed display names (~35-39)."},
    ],
    "classes": [
        {"id": "evidence_backed", "description": "The plan step rests on named decompilation or measured evidence. Example: the two sound tables."},
        {"id": "bounded_probe", "description": "A bounded runtime read whose result is recorded whether or not it is positive. Example: reading entity+0x64."},
        {"id": "unsupported", "description": "Asserts a result the evidence does not yet support."},
    ],
    "purpose": "confirm each plan step is evidence-backed or a bounded probe",
    "context": "Capstone."})
run("c-06-decide", "jev_decide", {
    "decision": "Is the consolidated plan complete and ready to act on, or does a decision remain open?",
    "evidence": PLAN,
    "priorities": "No silently-assumed branch; every artifact keeps partial claims; the plan must be executable end to end without a positive-find requirement.",
    "candidates": [
        {"id": "ready", "description": "The plan is complete and can be executed as written."},
        {"id": "reopen_b", "description": "Reopen B: require the car-highlight cursor to be named before acting."},
        {"id": "cut_c", "description": "Cut C to shrink scope."},
        {"id": "investigate_more", "description": "Gather more evidence before acting."},
    ],
    "requirements": ["Leaves no decision silently assumed", "Executable end to end", "Keeps partial claims"]})
run("c-07-compare", "jev_compare", {
    "passage_a": "Stop condition 7b: all three threads to a definite outcome, C required.",
    "passage_b": "Plan: B resolved = definite outcome (store read + cursor open if unnamed); C = car-keyed extension.",
    "aspects": ["whether all three threads can reach a definite outcome", "whether C is defined", "internal consistency"]})
_c8 = run("c-08-extract", "jev_extract", {"document": PLAN,
    "fields": [
        {"id": "order", "pattern": "ORDER: A \\(sound index\\) -> B \\(selector\\) -> C", "description": "the work order"},
        {"id": "proof_bar", "pattern": "a decompilation-reachable address, never a value-only match", "description": "the B proof bar"},
        {"id": "verdict", "pattern": "CONSISTENT, no off-by-one", "description": "the sound verdict"},
        {"id": "ceiling", "pattern": "render_fidelity_complete stays false", "description": "the claim ceiling"},
        {"id": "c_rows", "pattern": "~35-39 rows", "description": "the C row count"},
    ]})
_r = []
_f = _c8.get("fields", {}) if isinstance(_c8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("c-09-audit", "jev_audit", {"source": PLAN, "records": _r or [{"id": "verdict", "request": "extract verdict", "value": "CONSISTENT, no off-by-one"}]})
run("c-10-verify", "jev_verify", {"claims": [
    "The plan orders A -> B -> C and requires all three to reach a definite outcome.",
    "The sound verdict is consistent with no off-by-one.",
    "The livery-label selector store is entity+0x64 reached via the gameflow pointer chain.",
    "B resolved requires a positive isolated car-highlight cursor.",
    "C is a car-keyed display-name set of about 35-39 rows, not a 136-entry table.",
    "render_fidelity_complete stays false on every artifact.",
], "evidence": PLAN})
run("c-11-review", "jev_review", {"request": "Adopt the consolidated plan for the next session.",
    "diff": "+ A: record sound verdict consistent (two tables @0x24af68/@0x24afe8 + loader chain); no verifier change\n"
            "+ B: trace FUN_0019eb90->FUN_00125640->FUN_00121e10; read entity+0x64 via chain in slots 102/103/104; one indirection pass; record definite outcome\n"
            "+ C: extend resolve_display_names.py to car-keyed TXT_CARS_* (~35-39 rows), own receipt\n"
            "+ ceiling: render_fidelity_complete false; stop only on three definite outcomes (7b)",
    "tests": "verify_config_data_sound VERIFY OK; resolve_display_names VERIFY OK; test_retained_packet_evidence OK"})
run("c-12-gate", "jev_gate", {"request": "Adopt the consolidated plan: A recorded verdict, B definite outcome, C car-keyed extension; all three to a definite outcome (7b); render_fidelity_complete false.",
    "diff": json.dumps({"order": ["A", "B", "C"], "A": "record consistent sound verdict", "B": "read entity+0x64 + record car cursor open", "C": "extend resolver to car-keyed names", "ceiling": "render_fidelity_complete false"}, indent=1),
    "claims": [
        "A is backed by two executable tables and a loader chain; no off-by-one.",
        "B's proof bar is decompilation-reachability, and B is deliverable as a definite outcome.",
        "C is car-keyed (~35-39 rows); the 136-entry display-name table is a misnomer.",
        "render_fidelity_complete stays false on every artifact.",
    ],
    "evidence": PLAN + "\n\nDecide: " + json.dumps(results.get("c-06-decide", {}))[:1500]})

print("GRILL CAPSTONE DONE", len(results), "calls")
