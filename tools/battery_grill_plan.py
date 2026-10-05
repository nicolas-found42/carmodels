#!/usr/bin/env python3
"""Grill-session Jev battery: all 12 tools over the plan and each open thread.

Threads: A sound bank index (CAR_SND_CARn -> carN_snd), B EE selector word,
P the plan itself (ordering, claim ceiling, proof bar). Jev advises; code owns facts.

Receipts: research/evidence/vehicle-completeness/jev-grill/<tag>.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-grill")
os.makedirs(OUT, exist_ok=True)


def rd(rel):
    return open(os.path.join(R, rel), encoding="utf-8").read()


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
    print(f"--- {tag:12} {tool:14} action={act}")
    return c


# ============================================================== shared evidence =
SOUND_EV = (
    "build_reference.py (line ~261) builds base_bank with a NAME-based rule: for each CAR_SND_CARn block in "
    "CARSOUND.DAT it reads :SOUNDBANK_TYPE CARn_SOUND_FILE and sets base_bank['CAR_SND_CARn'] = 'car' + "
    "SOUNDBANK_TYPE[3] + '_snd', i.e. CAR_SND_CAR6 + CAR6_SOUND_FILE -> 'car6_snd' (the digit is taken from the "
    "bank file name, not from the CAR_SND_CARn number). CARSOUND.DAT binds CAR_SND_CAR1..CAR_SND_CAR8 -> "
    "CAR1_SOUND_FILE..CAR8_SOUND_FILE (verified: 8 base blocks). The executable's static strings are "
    "'sounds\\car1_snd:0:0:5' ... 'sounds\\car8_snd:7:35:5' (addresses 0x288e40..0x288f18) with templates "
    "'%s.msh' (0x28f508) and '%s.msb' (0x28f510); the trailing fields are base:offset:count with base 0..7, "
    "suggesting an index. Corroboration: 49_COUPE's sound type CAR_SND_49_COUPE inherits CAR_SND_CAR6 and its "
    "sample names are literally MASTER_SOUND_SAMPLE_CAR6_TICKOVER / ..._LOW_UNLOADED / ..._HIGH_LOADED, so the "
    "'CAR6' identity appears in the sample data itself. All 35 cars resolve a chain; the 8 distinct inherit "
    "targets are CAR_SND_CAR1..CAR_SND_CAR8.")

SELECTOR_EV = (
    "carselection-2026-10-05/bridge-three-screens.json ee_findings: no FORD'49 / ROUTE 50 / TXT_CARS_* label bytes "
    "exist in the slot102 EE image (labels arrive via the text archive + glyph path). Static leads: FUN_0019eb90 "
    "reads the gameflow livery label via a static table at VA 0x23acb0 (packed strings INVALID/WHEELS/FUEL/...) and "
    "resolves it via FUN_00125640, storing via FUN_00121e10; VA_0x23acb0 holds 0x0028f7c8 stable across all three "
    "captures. jgrep highlight hits: 0017cb80 (initials-entry cycler, discarded), 00184430 (1..3 bounded cursor on "
    "uRam0028fd74, reads 0 in all three, not the car cursor), 001c4a40 (indexed cursor over DAT_00241b40 table, "
    "caller context open). VA_0x241b60 is 5,4,4 across slots 102/103/104 (does not track highlight; open). "
    "Three-way triangulation for highlight tuples: one-based (1,5,4) 0 hits; zero-based (0,4,3) words 0 hits; "
    "byte-level (0,4,3) 97 hits clustered in VU-packet regions (0x21xxxx, 0x81xxxx-0x84xxxx) with no menu-struct "
    "candidate; scratchpad 121 changed words all float-scale VU noise (0x352c-0x354c 102==104!=103, not a small-int "
    "cursor). Screens pair highlight positions 1/5/4 to cars 49_COUPE / THUNDERBIRD_2002 / FORTYNINE at DEFAULT livery.")

PLAN_EV = (
    "Adopted plan: (1) ordering = do the sound-index reconciliation (A) first, then the EE selector word (B), with "
    "the display-name table (C) optional. (2) proof bar for the selector word = an isolated EE word that tracks the "
    "highlight AND is reachable from the decompiled menu/label draw path (not a bare value match, because value-only "
    "triangulation already produced 97 noisy byte hits and 0 word hits). (3) claim ceiling = render_fidelity_complete "
    "stays false on every artifact, partial claims only, no completion gate passes. (4) method for the selector = "
    "decompilation-first: read the FUN_0019eb90 -> FUN_00125640 -> store chain to derive the exact struct offset, "
    "then read that address in the three existing EE images. Standing constraints: never print credentials; new files "
    "in R not S; close tickets only on real tool output; a Jev gate escalate is an acceptable recorded outcome.")


# ================================================================== battery P ====
run("p-01-screen", "jev_screen", {"text": PLAN_EV, "purpose": "review the adopted grill-session plan as task data"})
run("p-02-noul", "jev_noul", {"propositions": [
    "Doing the sound-index reconciliation before the selector work is the right ordering.",
    "Requiring decompilation-reachability is a stronger and more appropriate proof bar for the selector word than a value match.",
    "Keeping render_fidelity_complete false on every artifact is the correct standing policy for this project.",
    "A decompilation-first approach is more likely to isolate the selector word than capturing more screens.",
    "The project can reach a fully closed state within the next one or two sessions.",
    "The display-name table is the highest-value of the three open threads.",
], "context": PLAN_EV + "\n\n" + SOUND_EV[:2000] + "\n\n" + SELECTOR_EV[:2000]})
run("p-03-find", "jev_find", {"query": "most important reason to do the sound-index reconciliation first",
    "candidates": [
        {"id": "correctness", "text": "If build_reference's name-based rule disagrees with the executable's index table, the just-closed T2 sound assertion is wrong."},
        {"id": "cheap", "text": "It is a small, bounded investigation with a definite verdict."},
        {"id": "unblocks", "text": "It unblocks nothing downstream."},
        {"id": "documents", "text": "It documents the soundman table for the corpus README."},
    ], "top_k": 4})
run("p-04-rerank", "jev_rerank", {"query": "best next action for the coming session",
    "candidates": [
        {"id": "reconcile_sound_index", "text": "Read the soundman table consumption in the decompilation and decide consistent/off-by-one; fix T2 if needed."},
        {"id": "trace_label_chain", "text": "Read FUN_0019eb90/FUN_00125640/FUN_00121e10 and read the derived store address in the three EE images."},
        {"id": "build_display_table", "text": "Build the full display-name table from tlate_en.dat."},
        {"id": "more_screens", "text": "Capture more car-selection screens and diff again."},
        {"id": "stop_report", "text": "Stop and report the three closed tickets as the delivered state."},
    ]})
run("p-05-classify", "jev_classify", {"items": [
        {"id": "A", "text": "Sound bank index: does build_reference's CAR_SND_CARn->carN_snd name rule agree with the executable's carN_snd:base:offset table? Decidable by reading soundman decompilation."},
        {"id": "B", "text": "EE selector word: find the per-screen highlight/selector value and tie it to a decompiled field. Prior value-only triangulation found nothing discriminating."},
        {"id": "C", "text": "Display-name table: resolve all TXT_CARS_* keys through tlate_en.dat; breadth work, no unknown."},
    ],
    "classes": [
        {"id": "decidable_now", "description": "Answerable from existing static/decompilation material with a definite verdict. Example: reading a table's consumption."},
        {"id": "needs_new_evidence", "description": "Requires a new capture, runtime read, or artefact before it can be decided."},
        {"id": "breadth_only", "description": "Mechanical expansion over known material; no unknown to resolve."},
    ],
    "purpose": "triage the three open threads by tractability",
    "context": "Three open threads from the T2/T3 close-out."})
run("p-06-decide", "jev_decide", {
    "decision": "What should the next session commit to as its primary objective?",
    "evidence": PLAN_EV + "\n\n" + SOUND_EV + "\n\n" + SELECTOR_EV,
    "priorities": "Protect the just-closed verifiers; prefer the thread that turns an unnamed address into a named one; keep render fidelity unclaimed; do not re-do value-only triangulation that already returned noise.",
    "candidates": [
        {"id": "reconcile_then_selector", "description": "Reconcile the sound index first (bounded), then decompilation-first selector hunt."},
        {"id": "selector_only", "description": "Spend the whole session on the selector word."},
        {"id": "display_table_only", "description": "Build the full display-name table."},
        {"id": "verify_only", "description": "Harden and re-gate the existing verifiers without new investigation."},
    ],
    "requirements": [
        "Protects the closed verifiers",
        "Produces a named address or a definite verdict",
        "Does not rely on value-only matching",
    ]})
run("p-07-compare", "jev_compare", {
    "passage_a": "Method for the selector: decompilation-first. Read FUN_0019eb90 -> FUN_00125640 -> FUN_00121e10 to derive the exact struct offset, then read that address in the three existing EE images.",
    "passage_b": "Method for the selector: runtime-first. Capture more car-selection screens with varied highlight and livery positions and diff the EE images.",
    "aspects": ["what it can name", "cost", "risk of noise", "relies on existing evidence"]})
_p8 = run("p-08-extract", "jev_extract", {"document": PLAN_EV + " " + SELECTOR_EV,
    "fields": [
        {"id": "label_chain", "pattern": "FUN_0019eb90 -> FUN_00125640 -> [A-Za-z0-9_]+", "description": "the decompiled label-resolution chain"},
        {"id": "byte_hits", "pattern": "byte-level \\(0,4,3\\) [0-9]+ hits", "description": "byte-level triangulation hit count"},
        {"id": "word_hits", "pattern": "zero-based \\(0,4,3\\) words [0-9]+ hits", "description": "word-level triangulation hit count"},
        {"id": "va", "pattern": "VA 0x[0-9a-f]+", "description": "a virtual address named in the evidence"},
    ]})
_recs = []
_f = _p8.get("fields", {}) if isinstance(_p8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _recs.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("p-09-audit", "jev_audit", {"source": PLAN_EV + " " + SELECTOR_EV, "records": _recs or [{"id": "va", "request": "extract va", "value": "VA 0x23acb0"}]})
run("p-10-verify", "jev_verify", {"claims": [
    "The adopted plan orders the sound-index reconciliation before the selector word.",
    "The proof bar for the selector word requires decompilation-reachability, not a value match.",
    "The claim ceiling keeps render_fidelity_complete false on every artifact.",
    "Value-only triangulation already produced 97 byte hits and 0 word hits, so a value match is not discriminating.",
], "evidence": PLAN_EV + "\n\n" + SELECTOR_EV})
run("p-11-review", "jev_review", {"request": "Adopt this plan for the next session on the Ford Racing 2 car-model recovery.",
    "diff": "+ ordering: sound-index reconciliation, then decompilation-first selector hunt, display-name table optional\n"
            "+ proof bar: selector word must be decompilation-reachable, not a bare value match\n"
            "+ claim ceiling: render_fidelity_complete false on every artifact\n"
            "+ selector method: read FUN_0019eb90/FUN_00125640/FUN_00121e10, then read the derived address in the three EE images\n"
            "+ no re-run of value-only triangulation",
    "tests": "existing verifiers stay green: tools/verify_config_data_sound.py VERIFY OK; tools/resolve_display_names.py VERIFY OK; tools/test_retained_packet_evidence.py OK"})
run("p-12-gate", "jev_gate", {"request": "Adopt the plan: sound-index reconciliation first, decompilation-first selector hunt, display-name table optional, render fidelity unclaimed.",
    "diff": json.dumps({"plan": "p-06-decide selection", "order": ["A", "B", "C?"], "proof_bar": "decompilation-reachable selector word", "claim_ceiling": "render_fidelity_complete false"}, indent=1),
    "claims": [
        "The plan does not require re-running value-only triangulation.",
        "Every artifact keeps render_fidelity_complete false.",
        "The selector thread's success criterion is a named, decompilation-reachable address.",
    ],
    "evidence": PLAN_EV + "\n\n" + SELECTOR_EV + "\n\nPlan decide: " + json.dumps(results.get("p-06-decide", {}))[:1500]})

# ================================================================== battery A ====
run("a-01-screen", "jev_screen", {"text": SOUND_EV, "purpose": "sound bank mapping evidence for the off-by-one question"})
run("a-02-noul", "jev_noul", {"propositions": [
    "build_reference.py's name-based rule (CAR_SND_CARn + CARn_SOUND_FILE -> carN_snd) agrees with the executable's sounds\\carN_snd table.",
    "The build_reference mapping is off by one.",
    "The MASTER_SOUND_SAMPLE_CAR6_* sample names corroborate CAR_SND_CAR6 -> car6_snd.",
    "A name-based mapping makes an index off-by-one impossible for this corpus.",
    "T2's sound-chain assertion could be wrong even though every chain resolves to an existing bank file.",
], "context": SOUND_EV})
run("a-03-find", "jev_find", {"query": "strongest evidence that CAR_SND_CARn -> carN_snd is not off by one",
    "candidates": [
        {"id": "sample_names", "text": "49_COUPE inherits CAR_SND_CAR6 and its samples are literally MASTER_SOUND_SAMPLE_CAR6_*."},
        {"id": "bank_file", "text": "The digit comes from the CARn_SOUND_FILE token, not from the CAR_SND_CARn number."},
        {"id": "table_index", "text": "The executable table 'carN_snd:B:O:C' carries a 0..7 base index that could disagree with the name."},
    ], "top_k": 3})
run("a-04-rerank", "jev_rerank", {"query": "next step to settle the sound-index question",
    "candidates": [
        {"id": "read_soundman", "text": "Read the soundman function that consumes sounds\\carN_snd:B:O:C and state what B indexes."},
        {"id": "fix_t2", "text": "Pre-emptively change build_reference to an index rule."},
        {"id": "accept_name", "text": "Accept the name-based mapping as sufficient because samples say CAR6."},
        {"id": "runtime_probe", "text": "Probe the bank loads at runtime."},
    ]})
run("a-05-classify", "jev_classify", {"items": [
        {"id": "rule", "text": "build_reference: base_bank['CAR_SND_CARn'] = 'car' + SOUNDBANK_TYPE[3] + '_snd'"},
        {"id": "samples", "text": "MASTER_SOUND_SAMPLE_CAR6_TICKOVER for a car inheriting CAR_SND_CAR6"},
        {"id": "exe_table", "text": "sounds\\car1_snd:0:0:5 ... car8_snd:7:35:5 with base 0..7"},
    ],
    "classes": [
        {"id": "supports_name_mapping", "description": "Evidence that the CAR-number identity is carried by the name/data. Example: sample names saying CAR6."},
        {"id": "supports_index_mapping", "description": "Evidence that a separate 0..7 index is the authority. Example: a base field consumed positionally."},
        {"id": "neutral", "description": "Consistent with both mappings."},
    ],
    "purpose": "sort the sound evidence by which mapping it supports",
    "context": "Off-by-one question for T2."})
run("a-06-decide", "jev_decide", {
    "decision": "How should the sound-index question be settled?",
    "evidence": SOUND_EV,
    "priorities": "Do not change a verified T2 unless the executable proves a disagreement; prefer a definite verdict from the decompilation; keep the corpus building.",
    "candidates": [
        {"id": "read_then_decide", "description": "Read the soundman consumer to state what the base field indexes, then fix or confirm."},
        {"id": "change_preemptively", "description": "Switch build_reference to an index rule now."},
        {"id": "declare_name_based", "description": "Record the mapping as name-based and add the sample-name corroboration as evidence."},
    ],
    "requirements": ["Rest on executable evidence", "Avoid changing a green verifier without proof", "Leave a definite recorded verdict"]})
run("a-07-compare", "jev_compare", {
    "passage_a": "build_reference.py rule: base_bank['CAR_SND_CAR6'] = 'car6_snd' derived from the token CAR6_SOUND_FILE.",
    "passage_b": "Executable table: 'sounds\\car6_snd:5:25:5' where the middle fields are base:offset:count with base = 5.",
    "aspects": ["authority for the digit", "name vs index", "agreement"]})
_a8 = run("a-08-extract", "jev_extract", {"document": SOUND_EV,
    "fields": [
        {"id": "rule_code", "pattern": "'car' \\+ SOUNDBANK_TYPE\\[3\\] \\+ '_snd'", "description": "the build_reference mapping expression"},
        {"id": "exe_first", "pattern": "car1_snd:[0-9]+:[0-9]+:[0-9]+", "description": "first executable bank descriptor"},
        {"id": "exe_last", "pattern": "car8_snd:[0-9]+:[0-9]+:[0-9]+", "description": "last executable bank descriptor"},
        {"id": "inherit", "pattern": "inherits CAR_SND_CAR[0-9]", "description": "an inheritance target"},
    ]})
_ra = []
_fa = _a8.get("fields", {}) if isinstance(_a8, dict) else {}
for fid, fv in (_fa.items() if isinstance(_fa, dict) else []):
    _ra.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("a-09-audit", "jev_audit", {"source": SOUND_EV, "records": _ra or [{"id": "rule_code", "request": "extract rule_code", "value": "'car' + SOUNDBANK_TYPE[3] + '_snd'"}]})
run("a-10-verify", "jev_verify", {"claims": [
    "build_reference sets base_bank['CAR_SND_CAR6'] = 'car6_snd' from the token CAR6_SOUND_FILE.",
    "CARSOUND.DAT binds CAR_SND_CAR1..CAR_SND_CAR8 to CAR1_SOUND_FILE..CAR8_SOUND_FILE.",
    "The executable contains sounds\\car1_snd:0:0:5 through car8_snd:7:35:5 plus %s.msh / %s.msb templates.",
    "49_COUPE's samples are named MASTER_SOUND_SAMPLE_CAR6_*.",
    "The build_reference mapping is proven off by one.",
], "evidence": SOUND_EV})
run("a-11-review", "jev_review", {"request": "Settle whether build_reference's CAR_SND_CARn -> carN_snd sound mapping agrees with the executable.",
    "diff": "+ read the executable soundman consumer of sounds\\carN_snd:B:O:C and state what B indexes\n"
            "+ corroborate with MASTER_SOUND_SAMPLE_CAR6_* sample names\n"
            "+ record verdict: consistent | off_by_one | undecidable\n"
            "+ change build_reference only if the verdict is off_by_one",
    "tests": "tools/verify_config_data_sound.py VERIFY OK (35/35 sound chains)"})
run("a-12-gate", "jev_gate", {"request": "Record a definite verdict on the CAR_SND_CARn -> carN_snd mapping.",
    "diff": "+ verdict to be recorded from the decompilation, not asserted\n+ no change to build_reference unless off_by_one is proven",
    "claims": [
        "T2's sound-chain assertion resolves every car to an existing bank file.",
        "The name-based mapping is corroborated by CAR6 sample names.",
        "No off-by-one has yet been proven from the executable.",
    ],
    "evidence": SOUND_EV + "\n\nDecide: " + json.dumps(results.get("a-06-decide", {}))[:1500]})

# ================================================================== battery B ====
run("b-01-screen", "jev_screen", {"text": SELECTOR_EV, "purpose": "EE selector evidence for the decompilation-first plan"})
run("b-02-noul", "jev_noul", {"propositions": [
    "An isolated EE word that tracks the menu highlight exists.",
    "Deriving the selector store address from the FUN_0019eb90 / FUN_00125640 chain will name the address to read.",
    "A value-only match across three screens would be sufficient proof of the selector word.",
    "The 97 byte-level hits contain the selector as a byte.",
    "VA_0x241b60 (5,4,4) is the per-screen selector.",
], "context": SELECTOR_EV})
run("b-03-find", "jev_find", {"query": "best anchor for deriving the selector address",
    "candidates": [
        {"id": "fun19eb90", "text": "FUN_0019eb90 reads the livery label via static table VA 0x23acb0 and resolves via FUN_00125640, storing via FUN_00121e10."},
        {"id": "fun1c4a40", "text": "001c4a40 indexed cursor over DAT_00241b40 table, caller context open."},
        {"id": "va241b60", "text": "VA_0x241b60 = 5,4,4 across the three captures."},
        {"id": "scratchpad", "text": "121 changed scratchpad words, all float-scale VU noise."},
    ], "top_k": 4})
run("b-04-rerank", "jev_rerank", {"query": "which decompiled function most likely stores the per-screen car/livery selector",
    "candidates": [
        {"id": "fun121e10", "text": "FUN_00121e10 stores the resolved label (the write side of FUN_0019eb90)."},
        {"id": "fun1c4a40", "text": "001c4a40 indexed cursor over DAT_00241b40, caller context open."},
        {"id": "fun184430", "text": "00184430 1..3 bounded cursor on uRam0028fd74 (read 0 in all three)."},
        {"id": "fun17cb80", "text": "0017cb80 initials-entry cycler (discarded)."},
    ]})
run("b-05-classify", "jev_classify", {"items": [
        {"id": "fun121e10", "text": "FUN_00121e10 stores the resolved livery label."},
        {"id": "fun1c4a40", "text": "001c4a40 indexed cursor over a table, caller unknown."},
        {"id": "va241b60", "text": "VA_0x241b60 holds 5,4,4 that does not track the highlight."},
    ],
    "classes": [
        {"id": "reads_or_writes_selection", "description": "Code that plausibly reads or writes the selected car/livery for the menu. Example: the store of the resolved label."},
        {"id": "indexed_table_cursor", "description": "A cursor walking an indexed table whose caller is unknown; could be the selector."},
        {"id": "disqualified", "description": "Already shown not to track the highlight."},
    ],
    "purpose": "sort the selector leads by role",
    "context": "Decompilation-first selector hunt."})
run("b-06-decide", "jev_decide", {
    "decision": "What is the first concrete read to perform for the selector word?",
    "evidence": SELECTOR_EV,
    "priorities": "Prefer a named address derived from the decompilation over another value diff; keep the deliverable a named field; do not re-run value-only triangulation.",
    "candidates": [
        {"id": "trace_store", "description": "Read FUN_0019eb90/FUN_00125640/FUN_00121e10, extract the store address, read that word in slots 102/103/104."},
        {"id": "open_caller", "description": "Resolve the 001c4a40 caller context first, then read its table index."},
        {"id": "capture_more", "description": "Capture more screens and diff again."},
        {"id": "stop", "description": "Stop the selector thread; keep the three-pair bridge."},
    ],
    "requirements": ["Produces a named address", "Uses existing evidence", "Avoids value-only matching"]})
run("b-07-compare", "jev_compare", {
    "passage_a": "Prior method: three-way value triangulation across slot102/103/104 (0 word hits, 97 noisy byte hits).",
    "passage_b": "Proposed method: read the decompiled label/store chain to derive the address, then read that address in the same three images.",
    "aspects": ["what names the address", "evidence used", "false-positive risk"]})
_b8 = run("b-08-extract", "jev_extract", {"document": SELECTOR_EV,
    "fields": [
        {"id": "chain", "pattern": "FUN_0019eb90 reads[^.]*FUN_00125640", "description": "the label read/resolve chain"},
        {"id": "va_table", "pattern": "VA 0x23acb0", "description": "the static label table address"},
        {"id": "word_hits", "pattern": "words [0-9]+ hits", "description": "word-level hit count"},
        {"id": "byte_hits", "pattern": "byte-level \\(0,4,3\\) [0-9]+ hits", "description": "byte-level hit count"},
    ]})
_rb = []
_fb = _b8.get("fields", {}) if isinstance(_b8, dict) else {}
for fid, fv in (_fb.items() if isinstance(_fb, dict) else []):
    _rb.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("b-09-audit", "jev_audit", {"source": SELECTOR_EV, "records": _rb or [{"id": "va_table", "request": "extract va_table", "value": "VA 0x23acb0"}]})
run("b-10-verify", "jev_verify", {"claims": [
    "No FORD'49 / TXT_CARS_* label bytes exist in the slot102 EE image.",
    "Three-way triangulation produced 0 word hits and 97 byte hits for the highlight tuples.",
    "FUN_0019eb90 reads a livery label via VA 0x23acb0 and resolves it via FUN_00125640.",
    "An isolated per-screen selector word has already been found.",
], "evidence": SELECTOR_EV})
run("b-11-review", "jev_review", {"request": "Isolate the per-screen car/livery selector word by decompilation-first reading of the label/store chain.",
    "diff": "+ read FUN_0019eb90 -> FUN_00125640 -> FUN_00121e10, extract the store address\n"
            "+ read that word in the three existing EE images (slots 102/103/104)\n"
            "+ require the value to track positions 1/5/4 and be decompilation-reachable\n"
            "+ do not count a value-only match as proof",
    "tests": "three captures already unpacked: slot102 sha 6e3971..., slot103 sha b5e569..., slot104 sha 74acb5..."})
run("b-12-gate", "jev_gate", {"request": "Plan the decompilation-first isolation of the per-screen selector word.",
    "diff": "+ derive the store address from the label chain, read it in the three EE images\n+ require decompilation-reachability, not a value match\n+ deliver a named field or a recorded open",
    "claims": [
        "The plan avoids re-running value-only triangulation.",
        "The success criterion is a named, decompilation-reachable address.",
        "The three EE images are already available.",
    ],
    "evidence": SELECTOR_EV + "\n\nDecide: " + json.dumps(results.get("b-06-decide", {}))[:1500]})

print("GRILL BATTERY DONE", len(results), "calls")
