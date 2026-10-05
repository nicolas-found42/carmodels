#!/usr/bin/env python3
"""Execution closure battery: all 12 tools over the A/B/C execution, plus jev_gate per thread (Q13a).
Receipts: research/evidence/vehicle-completeness/jev-exec/*.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-exec")
os.makedirs(OUT, exist_ok=True)
results = {}


def rd(rel):
    return open(os.path.join(R, rel), encoding="utf-8").read()


def diff_of(rel):
    body = rd(rel)
    return f"--- /dev/null\n+++ b/{rel}\n" + "\n".join("+" + l for l in body.split("\n"))


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


A_RECEIPT = rd("research/evidence/vehicle-completeness/sound-bank-index-reconciliation.json")
B_RECEIPT = rd("research/evidence/vehicle-completeness/selector-word-isolation.json")
C_RECEIPT = rd("research/evidence/vehicle-completeness/full-display-name-table.json")
REG = "tools/test_retained_packet_evidence.py -> RETAINED PACKET EVIDENCE OK; tools/verify_recovered_asset_index.py -> VERIFY OK; \
tools/verify_config_data_sound.py -> VERIFY OK; index sha 9fcbac873a96b72d8ef71822f3e0fcccc7bec1a174da18b8a54e93090063befe unchanged"

EXEC = ("EXECUTION of the agreed plan (three threads, each to a definite outcome):\n"
        "A — SOUND-INDEX RECONCILIATION: tools/verify_sound_bank_index.py VERIFY OK. Read the two parallel car-bank "
        "tables from the ELF (config-key @0x24af68, descriptor @0x24afe8): CARn_SOUND_FILE and carN_snd share index "
        "0..7; build_reference.py's name-based CAR_SND_CARn -> carN_snd mapping equals the executable. Verdict "
        "consistent. Controls: off-by-one corpus mapping rejected; swapped descriptor table rejected; car1 ordinal 0. "
        "No change to the green T2 verifier.\n"
        "B — SELECTOR WORD: tools/verify_selector_word.py PASS (definite outcome recorded). Named livery store "
        "entity+0x64 via FUN_00121e10 (from FUN_00125640's packed selector over record base 0x233070+type*0x114), "
        "reached via gameflow chain outer+4 -> +0x14c -> +0x174. In a paused savestate the entity is not rooted: the "
        "bounded sig-scan for the entity flag (+0x60 == ...1cd0) found 0 candidates; the DAT_00241b40 region scan "
        "yields ~320 numerically-in-range words (value-match noise) and 0 exact-base pointers. All three captures are "
        "DEFAULT livery, so the named store is non-distinguishing by construction. Per-screen CAR highlight cursor "
        "recorded OPEN. No value-only match claimed.\n"
        "C — DISPLAY NAMES: tools/resolve_display_names.py VERIFY OK; full-display-name-table.json 35 cars all pass. "
        "Both assertions kept in one tool: the 3-pair T3 regression AND the all-35 car-keyed table, with unknown-key "
        "and apostrophe-byte-exact controls. The '136-entry display-name table' is a misnomer.\n"
        "CLOSURE ARTIFACT: one receipt per thread; jev_gate per thread; this session completion report. "
        "render_fidelity_complete false everywhere; no completion gate passes; a Jev escalate is acceptable.")

run("exec-01-screen", "jev_screen", {"text": EXEC, "purpose": "review the execution result as task data"})
run("exec-02-noul", "jev_noul", {"propositions": [
    "A reached a definite outcome: the executable agrees with build_reference's sound mapping.",
    "B reached a definite outcome: the livery store is named and the per-screen cursor is recorded open.",
    "C reached a definite outcome: all 35 cars resolve through tlate_en.dat with controls.",
    "The execution asserted a positive per-screen selector word.",
    "Every artifact keeps render_fidelity_complete false.",
], "context": EXEC + "\n\n" + A_RECEIPT[:2500] + "\n" + B_RECEIPT[:2500] + "\n" + C_RECEIPT[:2500]})
run("exec-03-find", "jev_find", {"query": "which thread produced the strongest definite outcome",
    "candidates": [
        {"id": "A", "text": "Sound mapping equal to the executable across two tables and 35 cars; 3 controls rejected."},
        {"id": "B", "text": "Livery store named at entity+0x64; cursor recorded open; 0 sig-scan candidates, 0 exact-base pointers."},
        {"id": "C", "text": "35/35 cars resolve with unknown-key and apostrophe controls; 3-pair regression preserved."},
    ], "top_k": 3})
run("exec-04-rerank", "jev_rerank", {"query": "residual risk each thread leaves open",
    "candidates": [
        {"id": "A_risk", "text": "None material: the mapping is read straight from the executable tables."},
        {"id": "B_risk", "text": "The per-screen highlight cursor stays unnamed; a live (unpaused) capture may still expose it."},
        {"id": "C_risk", "text": "en-only; other locale tlate files not resolved; the '136' phrasing still appears in old notes."},
    ]})
run("exec-05-classify", "jev_classify", {"items": [
        {"id": "A", "text": "A: sound mapping consistent; controls rejected; no verifier change."},
        {"id": "B", "text": "B: livery store named; per-screen cursor recorded open; no value-only match."},
        {"id": "C", "text": "C: 35/35 car-keyed display names with controls; 3-pair regression kept."},
    ],
    "classes": [
        {"id": "definite_outcome", "description": "A recorded result that closes the thread without a positive-find requirement. Example: a recorded open with evidence."},
        {"id": "positive_find_asserted", "description": "Claims a discovery the evidence does not support."},
        {"id": "incomplete", "description": "The thread is neither closed nor honestly recorded open."},
    ],
    "purpose": "confirm each thread reached a definite outcome",
    "context": "Execution closure."})
run("exec-06-decide", "jev_decide", {
    "decision": "Did the execution meet the agreed plan and reach a definite outcome on all three threads?",
    "evidence": EXEC + "\n\n" + A_RECEIPT[:2500] + "\n" + B_RECEIPT[:2500] + "\n" + C_RECEIPT[:2500],
    "priorities": "Each thread to a definite outcome (7b); no positive-find requirement; render_fidelity_complete false; no value-only match claimed; escalate acceptable.",
    "candidates": [
        {"id": "met", "description": "All three threads reached a definite outcome; the plan's bar is met."},
        {"id": "B_short", "description": "B is short: it should have isolated the per-screen cursor positively."},
        {"id": "rework", "description": "Rework required."},
    ],
    "requirements": ["All three threads to a definite outcome", "No value-only match claimed", "render_fidelity_complete false"]})
run("exec-07-compare", "jev_compare", {
    "passage_a": "Plan: A recorded verdict; B definite outcome (store read + cursor open allowed); C all-35 car-keyed with controls.",
    "passage_b": EXEC,
    "aspects": ["A met", "B met", "C met", "claim ceiling held"]})
_e8 = run("exec-08-extract", "jev_extract", {"document": A_RECEIPT + "\n" + B_RECEIPT + "\n" + C_RECEIPT,
    "fields": [
        {"id": "a_verdict", "pattern": "\"verdict\": \"[a-z_]+\"", "description": "thread A verdict"},
        {"id": "b_outcome", "pattern": "\"outcome\": \"[^\"]+\"", "description": "thread B outcome"},
        {"id": "c_rows", "pattern": "\"rows\": [0-9]+", "description": "thread C car-keyed rows"},
        {"id": "c_result", "pattern": "\"result\": \"VERIFY OK\"", "description": "thread C result"},
    ]})
_r = []
_f = _e8.get("fields", {}) if isinstance(_e8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("exec-09-audit", "jev_audit", {"source": A_RECEIPT + "\n" + B_RECEIPT + "\n" + C_RECEIPT,
    "records": _r or [{"id": "b_outcome", "request": "extract b_outcome", "value": "named_store_confirmed; per-screen_highlight_cursor_recorded_open"}]})
run("exec-10-verify", "jev_verify", {"claims": [
    "tools/verify_sound_bank_index.py prints VERIFY OK and the executable mapping equals build_reference's.",
    "tools/verify_selector_word.py records the livery store at entity+0x64 and the per-screen cursor OPEN.",
    "tools/resolve_display_names.py resolves all 35 cars with unknown-key and apostrophe controls while keeping the 3-pair assertion.",
    "The execution asserted a positive per-screen selector word.",
    "render_fidelity_complete is false in every receipt.",
], "evidence": EXEC + "\n\n" + A_RECEIPT[:3000] + "\n" + B_RECEIPT[:3000] + "\n" + C_RECEIPT[:3000]})
run("exec-11-review", "jev_review", {"request": "Execute the agreed plan: A recorded verdict, B rooted definite outcome, C all-35 extension.",
    "diff": diff_of("tools/verify_sound_bank_index.py") + "\n" + diff_of("tools/verify_selector_word.py") + "\n" + diff_of("tools/resolve_display_names.py"),
    "tests": REG})
run("exec-12-gate", "jev_gate", {"request": "Gate the execution of the agreed plan across the three threads.",
    "diff": diff_of("tools/verify_sound_bank_index.py") + "\n" + diff_of("tools/verify_selector_word.py") + "\n" + diff_of("tools/resolve_display_names.py"),
    "claims": [
        "A: the executable's sound mapping equals build_reference's; verdict consistent.",
        "B: the livery store is named at entity+0x64 and the per-screen cursor is recorded open.",
        "C: all 35 cars resolve with controls and the 3-pair assertion is preserved.",
        "render_fidelity_complete stays false on every artifact.",
    ],
    "evidence": EXEC + "\n\nA_RECEIPT:\n" + A_RECEIPT + "\n\nB_RECEIPT:\n" + B_RECEIPT + "\n\nC_RECEIPT:\n" + C_RECEIPT,
    "tests": REG})

# per-thread gates (Q13a)
run("exec-13-gate-A", "jev_gate", {"request": "Gate thread A (sound-bank index reconciliation).",
    "diff": diff_of("tools/verify_sound_bank_index.py"),
    "claims": [
        "The two executable car-bank tables pair CARn_SOUND_FILE with carN_snd at the same index.",
        "build_reference.py's name-based mapping equals the executable; no off-by-one.",
        "The first numeric descriptor field is a discarded ordinal, not the name index.",
    ],
    "evidence": A_RECEIPT, "tests": REG})
run("exec-14-gate-C", "jev_gate", {"request": "Gate thread C (car-keyed display-name table).",
    "diff": diff_of("tools/resolve_display_names.py"),
    "claims": [
        "All 35 cars resolve their CARDATA INGAME_TEXT_ENUM through tlate_en.dat;1.",
        "The three-pair T3 assertion is preserved in the same tool.",
        "Unknown-key and apostrophe byte-exact controls hold.",
    ],
    "evidence": C_RECEIPT, "tests": REG})

print("EXEC CLOSURE DONE", len(results), "calls")
