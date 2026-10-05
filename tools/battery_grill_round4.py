#!/usr/bin/env python3
"""Grill round 4: with the sound verdict evidence-backed and the selector store named,
define 'B resolved' and C's true shape. All 12 Jev tools. Receipts: .../jev-grill/r4-*.json
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


SOUND = (
    "Sound index verdict (evidence): two parallel tables in SLES_517.05, both ascending index 0..7 = CAR1..CAR8: "
    "config-key table @0x24af68 (CAR1_SOUND_FILE..CAR8_SOUND_FILE, then CAR_GENERIC_SOUND_FILE, UI_SOUNDS_FILE) and "
    "descriptor table @0x24afe8 (sounds\\car1_snd:0:0:5 .. car8_snd:7:35:5, then car_gen:8:40:51, ui_snds:9:91:9). "
    "FUN_001d7950 (db_crsnd.c) resolves the :SOUNDBANK_TYPE token by name via table 0x24af68 and stores the index "
    "into car struct +0x40; FUN_00165b10 (mfile.c) indexes the carN_snd descriptor table by that +0x40; FUN_001408d8 "
    "parses 'sounds\\carN_snd:B:O:C' and builds carN_snd.msh/.msb with the literal stem. The first numeric field (0 "
    "for car1) is a bank/stream ordinal that is discarded in the filename path. Verdict: build_reference.py's "
    "name-based rule (CAR_SND_CARn + CARn_SOUND_FILE -> carN_snd) is CONSISTENT with the executable; no off-by-one.")
SELECTOR = (
    "Selector path (evidence): FUN_0019eb90 driver reads the selector-name-list at gameflow+0x74 and a label string "
    "from the static pointer table VA 0x23acb0 (12 pointers -> INVALID, A, A1..D1), resolves via FUN_00125640, stores "
    "via FUN_00121e10. FUN_00125640: record base 0x233070+type*0x114 (via FUN_0021b6e0), selector name count at "
    "+0xbc, name-list pointer at +0x90, returns a packed selector whose low 16 bits are the matched resource-list "
    "ordinal. FUN_00121e10 stores that selector at entity+0x64 (100 dec). The whole path hangs off the dynamic "
    "gameflow pointer chain outer+4 -> +0x14c -> +0x174, not a fixed VA. All three captured cars are at DEFAULT "
    "livery, so the livery selector is expected to be the same value (0) across all three. The per-screen CAR "
    "highlight cursor (FUN_001c4a40 over DAT_00241b40) remains caller-open.")
CREFRAME = (
    "C scope: the '136-entry display-name table' is a conflation. 136 is the count of :VALID_LIVERY rows across 35 "
    "cars; display names are keyed by car. There are 35 cars and 39 TXT_CARS_* keys in tlate_en.dat;1. The only "
    "resolver, tools/resolve_display_names.py, asserts exactly 3 pairs. No artifact defines a 136-row display-name "
    "table. A car-keyed display-name table has ~35-39 rows, not 136.")
EVID = SOUND + "\n\n" + SELECTOR + "\n\n" + CREFRAME

run("r4-01-screen", "jev_screen", {"text": EVID, "purpose": "round-4 decision evidence for B-resolved and C shape"})
run("r4-02-noul", "jev_noul", {"propositions": [
    "build_reference.py's CAR_SND_CARn -> carN_snd mapping is consistent with the executable (no off-by-one).",
    "The livery-label selector is stored at entity+0x64, reachable via the gameflow pointer chain.",
    "The per-screen CAR highlight cursor is the same field as entity+0x64.",
    "Reading entity+0x64 in the three captures will distinguish the three screens.",
    "C (the display-name table) is car-keyed (about 35-39 rows), not 136 rows.",
    "The '136-entry display-name table' is a well-defined artifact.",
], "context": EVID})
run("r4-03-find", "jev_find", {"query": "best definition of 'B resolved' given the named livery store and the open car cursor",
    "candidates": [
        {"id": "read_store_record_cursor", "text": "Read entity+0x64 via the pointer chain in all three EE images and record its value; record the car-highlight cursor open."},
        {"id": "require_car_cursor", "text": "B resolved only if the per-screen car-highlight cursor itself is named and read."},
        {"id": "declare_open_now", "text": "Record B open immediately without any read."},
        {"id": "drop_b", "text": "Drop thread B."},
    ], "top_k": 4})
run("r4-04-rerank", "jev_rerank", {"query": "correct shape for C (the display-name deliverable)",
    "candidates": [
        {"id": "car_keys", "text": "Extend resolve_display_names.py to all TXT_CARS_* car-name keys (~35-39), new receipt; do not call it a 136-entry table."},
        {"id": "force_136", "text": "Force a 136-row table over the livery rows."},
        {"id": "new_t4", "text": "Build a separate tool and ticket T4 for C."},
        {"id": "skip", "text": "Skip C."},
    ]})
run("r4-05-classify", "jev_classify", {"items": [
        {"id": "sound_verdict", "text": "build_reference mapping consistent with the executable; first numeric field is a discarded ordinal."},
        {"id": "livery_store", "text": "selector stored at entity+0x64 via dynamic chain; same value expected across three DEFAULT captures."},
        {"id": "car_cursor", "text": "FUN_001c4a40 indexed cursor over DAT_00241b40, caller open."},
        {"id": "c_136", "text": "'136-entry display-name table': 136 is livery rows; display names keyed by car (~35-39)."},
    ],
    "classes": [
        {"id": "definite_named", "description": "A concrete, decompilation-reachable address or a proven verdict. Example: entity+0x64; the consistent sound mapping."},
        {"id": "non_distinguishing", "description": "Named but the same value across the three captures, so it cannot separate screens. Example: the DEFAULT livery selector."},
        {"id": "still_open", "description": "Not yet resolved; caller or definition unknown. Example: the car-highlight cursor; the 136-row table."},
    ],
    "purpose": "sort the round-4 items by resolution status",
    "context": "Round-4 reframe."})
run("r4-06-decide", "jev_decide", {
    "decision": "What must 'B (selector) resolved' require, given the named livery store and the open car cursor?",
    "evidence": EVID,
    "priorities": "Accept a definite recorded outcome short of a forced positive; keep partial claims and render_fidelity_complete false; do not claim the car cursor is found when it is not; record what a read actually shows.",
    "candidates": [
        {"id": "read_store_record_cursor", "description": "Read entity+0x64 via the chain in the three EE images, record its value (expected DEFAULT), and record the car-highlight cursor as still open -> definite outcome."},
        {"id": "require_car_cursor", "description": "Require the car-highlight cursor itself to be named and read before B is resolved."},
        {"id": "declare_open_now", "description": "Record B open with no read."},
        {"id": "drop_b", "description": "Drop B from scope."},
    ],
    "requirements": ["Produces a definite recorded outcome", "Does not assert an unread find", "Keeps render_fidelity_complete false"]})
run("r4-07-compare", "jev_compare", {
    "passage_a": "B resolved = read the named livery store (entity+0x64) and record the car-highlight cursor open.",
    "passage_b": "B resolved = the per-screen CAR highlight cursor must itself be isolated.",
    "aspects": ["what a read can show", "risk of an open-ended hunt", "consistency with partial claims"]})
_r8 = run("r4-08-extract", "jev_extract", {"document": EVID,
    "fields": [
        {"id": "store_off", "pattern": "entity\\+0x64", "description": "the selector store offset"},
        {"id": "record_base", "pattern": "0x233070\\+type\\*0x114", "description": "the record base formula"},
        {"id": "car_keys", "pattern": "39 TXT_CARS_\\* keys", "description": "the car-name key count"},
        {"id": "verdict", "pattern": "CONSISTENT", "description": "the sound mapping verdict"},
    ]})
_r = []
_f = _r8.get("fields", {}) if isinstance(_r8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("r4-09-audit", "jev_audit", {"source": EVID, "records": _r or [{"id": "store_off", "request": "extract store_off", "value": "entity+0x64"}]})
run("r4-10-verify", "jev_verify", {"claims": [
    "build_reference.py's CAR_SND_CARn -> carN_snd mapping is consistent with the executable, with no off-by-one.",
    "The executable resolves :SOUNDBANK_TYPE by name via a table at 0x24af68 into car struct +0x40.",
    "The livery-label selector is stored at entity+0x64 reached via the gameflow pointer chain.",
    "The '136-entry display-name table' has 136 distinct display names.",
    "Display names are keyed by car, so a car-keyed table has about 35-39 rows.",
], "evidence": EVID})
run("r4-11-review", "jev_review", {"request": "Adopt round-4: record the sound verdict; define B resolved as a definite outcome; shape C as car-keyed.",
    "diff": "+ record sound verdict: consistent (no off-by-one), evidence-backed\n"
            "+ B resolved := read entity+0x64 via chain + record car cursor open\n"
            "+ C := car-keyed display names (~35-39), not a 136-entry table\n"
            "+ render_fidelity_complete stays false",
    "tests": "verify_config_data_sound VERIFY OK; resolve_display_names VERIFY OK; test_retained_packet_evidence OK"})
run("r4-12-gate", "jev_gate", {"request": "Adopt: sound verdict consistent; B resolved = definite outcome; C = car-keyed display names.",
    "diff": json.dumps({"sound": "consistent", "B_resolved": "read entity+0x64 + record car cursor open", "C": "car-keyed ~35-39 rows"}, indent=1),
    "claims": [
        "The sound mapping is consistent with the executable; the first numeric field is a discarded ordinal.",
        "The livery selector store is entity+0x64, reached via a dynamic chain.",
        "The 136-entry display-name table is not a well-defined artifact.",
    ],
    "evidence": EVID + "\n\nDecide: " + json.dumps(results.get("r4-06-decide", {}))[:1500]})

print("GRILL ROUND-4 DONE", len(results), "calls")
