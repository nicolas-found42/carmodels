#!/usr/bin/env python3
"""T2 + T3 Jev batteries: all 12 Jev tools over each ticket's real diff, run log and
acceptance criteria. Jev advises; code owns bytes, counts, hashes.

Receipts: research/evidence/vehicle-completeness/jev/{t2,t3}-NN-<tool>.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev")
os.makedirs(OUT, exist_ok=True)


def rd(rel):
    return open(os.path.join(R, rel), encoding="utf-8").read()


def diff_of(rel):
    body = rd(rel)
    lines = body.split("\n")
    return f"--- /dev/null\n+++ b/{rel}\n" + "\n".join("+" + l for l in lines)


T2_LOG = rd("research/evidence/vehicle-completeness/t2-verify-log.txt")
T3_LOG = rd("research/evidence/vehicle-completeness/t3-verify-log.txt")
REG = rd("research/evidence/vehicle-completeness/t2-t3-regression.log")

T2_REQ = ("Implement tools/verify_config_data_sound.py: per-car config x11 txt set equality vs corpus "
          "manifests, every file sha256 vs manifest, data DAT present per car, sound inheritance chain per car "
          "resolves to an existing bank in reference/ford/_shared/sounds; plus at least two negative controls "
          "(mutated hash accepted nowhere; cross-car config swap rejected).")
T2_DIFF = diff_of("tools/verify_config_data_sound.py")
T2_EVID = ("Ticket T2 acceptance: " + T2_REQ + "\n\nVerifier run log:\n" + T2_LOG +
           "\n\nRegression log:\n" + REG +
           "\n\nThe checker reuses build_reference.py parsing primitives (block_spans/clean_block/field) rather than "
           "re-deriving formats. Canonical index sha256 9fcbac873a96b72d8ef71822f3e0fcccc7bec1a174da18b8a54e93090063befe "
           "unchanged. render_fidelity_complete stays false.")

T3_REQ = ("Implement tools/resolve_display_names.py: read each captured car's INGAME_TEXT_ENUM from reference CARDATA, "
          "resolve through LANGUAGE/tlate_en.dat;1 (UTF-16-LE, keys TXT_CARS_*) in code, assert resolved strings equal "
          "the screens' VEHICLE labels; apostrophe byte-exact from the archive, not vision; receipt records archive path, "
          "sha256, key->string rows, pass/fail per pair; update bridge-three-screens.json only on pass.")
T3_DIFF = diff_of("tools/resolve_display_names.py")
T3_EVID = ("Ticket T3 acceptance: " + T3_REQ + "\n\nVerifier run log:\n" + T3_LOG +
           "\n\nRegression log:\n" + REG +
           "\n\nLabels come from the archive (UTF-16-LE bytes), not from vision transcripts; scope is the three captured "
           "pairs only, no 136-entry table. render_fidelity_complete stays false.")

results = {}


def run(tag, tool, args):
    try:
        res = call(tool, args)
        content = res.get("result", res)
        if isinstance(content, dict) and "content" in content:
            try:
                content = json.loads(content["content"][0]["text"])
            except Exception as ex:
                content = {"parse_error": str(ex), "raw": str(content)[:500]}
    except Exception as e:
        content = {"error": str(e)}
    json.dump({"args": args, "result": content}, open(os.path.join(OUT, f"{tag}.json"), "w"), indent=2)
    results[tool] = content
    act = content.get("action") or (content.get("recommendation") or {}).get("action") if isinstance(content, dict) else None
    print(f"--- {tag} ({tool}) action={act}")
    return content


# ======================================================================= T2 ======
run("t2-01-screen", "jev_screen", {
    "text": ("Decompilation-derived config keyword strings from the shared source checkout: CAR_TYPE, CAR_SOUND_TYPE, "
             "CAR_BODY_TYPE, CAR_ENGINE_TYPE, CAR_SETUP_TYPE, CAR_GROUP_TYPE, CAR_PERFORMANCE, CAR_MODEL_YEAR, "
             "VALID_LIVERY, ICON_FILENAME; plus sound bank descriptors 'sounds\\car1_snd:0:0:5' ... 'car8_snd:7:35:5' "
             "and the bank templates '%s.msh' / '%s.msb'."),
    "purpose": "confirm the config/sound keyword evidence used by the parity verifier is task data"})
run("t2-02-noul", "jev_noul", {
    "propositions": [
        "Every one of the 35 cars carries exactly the 11 named config txt files in its config/ folder.",
        "Each config txt file equals the block that build_reference.py derives from the shared source config.",
        "Each car's sound.txt :INHERIT_TYPE resolves in one hop to a base bank whose carN_snd.msb/.msh exist in _shared/sounds.",
        "Each car has exactly one data DAT matching its OWN_GAMEPLAY name.",
        "The four negative controls (mutated config, cross-car swap, missing shared bank, manifest sha tamper) are each rejected.",
        "The config/data/sound verifier proves render fidelity.",
    ],
    "context": T2_EVID[:40000]})
run("t2-03-find", "jev_find", {
    "query": "strongest evidence that the per-car config/data/sound parity verifier actually checks parity",
    "candidates": [
        {"id": "s_derived", "text": "Config txt content is compared to bytes derived from the source config via build_reference parsers, not just against the manifest."},
        {"id": "sha256", "text": "Every file's sha256 is recomputed on disk and matched to the manifest record."},
        {"id": "sound_chain", "text": "Each car's :INHERIT_TYPE resolves to a base bank and the carN_snd.msb/.msh files are asserted present."},
        {"id": "controls", "text": "Four negative controls each raise the expected rejection."},
    ], "top_k": 4})
run("t2-04-rerank", "jev_rerank", {
    "query": "next step after the T2 config/data/sound verifier is green",
    "candidates": [
        {"id": "close_t2", "text": "Gate the verifier and close T2."},
        {"id": "widen", "text": "Extend parity to _shared gameplay files and shared config contents."},
        {"id": "runtime", "text": "Prove the runtime loads the same bytes as the corpus."},
        {"id": "stop", "text": "Stop; record T2 as verified parity only."},
    ]})
run("t2-05-classify", "jev_classify", {
    "items": [
        {"id": "main", "text": "config x11 set equality + S-derived content equality + sha256 over 385 files; result VERIFY OK"},
        {"id": "nc_hash", "text": "mutated_config_hash_rejected: true"},
        {"id": "nc_swap", "text": "cross_car_config_swap_rejected: true"},
        {"id": "nc_bank", "text": "missing_shared_banks_rejected: true"},
        {"id": "nc_manifest", "text": "manifest_sha_tamper_rejected: true"},
    ],
    "classes": [
        {"id": "passed_check", "description": "A positive parity assertion that held over the real corpus. Example: 385 config files equal to S-derived bytes."},
        {"id": "rejected_control", "description": "A deliberate mutation that the checker rejected, with the expected rejection reason."},
        {"id": "inconclusive", "description": "Result reported neither as a clean pass nor as a clean rejection."},
    ],
    "purpose": "confirm the T2 result is all positive passes plus four cleanly rejected controls",
    "context": "T2 verifier receipt; classes are mutually exclusive."})
run("t2-06-decide", "jev_decide", {
    "decision": "Is T2 (per-car config / data-DAT / sound parity) complete enough to close?",
    "evidence": T2_EVID[:12000],
    "priorities": ("Close only on real tool output; never overclaim; render_fidelity_complete stays false; negative controls "
                   "must reject; do not re-derive config formats already parsed by build_reference.py."),
    "candidates": [
        {"id": "close_t2", "description": "Close T2: parity verified over 35 cars with four rejected negative controls."},
        {"id": "keep_open", "description": "Keep T2 open until runtime proves it loads the same bytes."},
        {"id": "widen_first", "description": "Extend to shared gameplay/config before closing."},
    ],
    "requirements": [
        "Rests on real checker output",
        "Includes at least two rejected negative controls",
        "Does not assert render fidelity",
    ]})
run("t2-07-compare", "jev_compare", {
    "passage_a": T2_REQ,
    "passage_b": T2_LOG,
    "aspects": ["config x11 set equality", "sha256 vs manifest", "data DAT per car", "sound chain resolution", "negative controls"]})
_t2ext = run("t2-08-extract", "jev_extract", {
    "document": T2_LOG,
    "fields": [
        {"id": "cars", "pattern": "\"cars\": [0-9]+", "description": "number of cars the verifier covered"},
        {"id": "config_files", "pattern": "\"config_files_checked\": [0-9]+", "description": "config files checked"},
        {"id": "data_files", "pattern": "\"data_files_checked\": [0-9]+", "description": "data DAT files checked"},
        {"id": "sound_chains", "pattern": "\"sound_chains_resolved\": [0-9]+", "description": "resolved sound chains"},
        {"id": "manifest_files", "pattern": "\"manifest_files_checked\": [0-9]+", "description": "manifest files checked"},
        {"id": "result", "pattern": "\"result\": \"[A-Z ]+\"", "description": "final verifier result token"},
    ]})
_recs = []
_f = _t2ext.get("fields", {}) if isinstance(_t2ext, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _recs.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("t2-09-audit", "jev_audit", {
    "source": T2_LOG,
    "records": _recs or [{"id": "result", "request": "extract result", "value": "VERIFY OK"}]})
run("t2-10-verify", "jev_verify", {
    "claims": [
        "tools/verify_config_data_sound.py prints VERIFY OK.",
        "The verifier checked 385 config files, 35 data DAT files and 35 sound chains over 35 cars.",
        "Each config txt file equals the block derived from the shared source config via build_reference parsers.",
        "Each car's sound chain resolves to a carN_snd bank present in _shared/sounds.",
        "Four negative controls (mutated config, cross-car swap, missing shared bank, manifest sha tamper) are rejected.",
        "The verifier asserts render fidelity.",
    ],
    "evidence": T2_EVID})
run("t2-11-review", "jev_review", {
    "request": T2_REQ,
    "diff": T2_DIFF,
    "tests": REG})
_gate2 = run("t2-12-gate", "jev_gate", {
    "request": T2_REQ,
    "diff": T2_DIFF,
    "claims": [
        "tools/verify_config_data_sound.py passes and prints VERIFY OK.",
        "Config x11 txt set equality holds for all 35 cars.",
        "Every file sha256 is verified against the manifest.",
        "Each car has a data DAT and a sound chain resolving to an existing shared bank.",
        "At least two negative controls are rejected.",
    ],
    "evidence": T2_EVID,
    "tests": REG})

# ======================================================================= T3 ======
run("t3-01-screen", "jev_screen", {
    "text": ("Vision-derived VEHICLE labels from the emulator screenshots to be asserted against the archive: "
             "slot102 'FORD '49', slot103 'THUNDERBIRD CONVERTIBLE', slot104 'FORTYNINE CONCEPT'. These are transcripts, "
             "not authoritative."),
    "purpose": "confirm the untrusted vision label strings are task data before asserting equality"})
run("t3-02-noul", "jev_noul", {
    "propositions": [
        "TXT_CARS_COUPE_1949 resolves to FORD '49 through tlate_en.dat;1.",
        "TXT_CARS_THUNDERBIRD_2002 resolves to THUNDERBIRD CONVERTIBLE.",
        "TXT_CARS_FORTYNINE resolves to FORTYNINE CONCEPT.",
        "The apostrophe in FORD '49 is byte-exact (0x27) from the archive rather than from a vision transcript.",
        "Each captured car's INGAME_TEXT_ENUM in the reference CARDATA equals the bridge enum.",
        "T3 resolves the full 136-entry display-name table.",
    ],
    "context": T3_EVID[:40000]})
run("t3-03-find", "jev_find", {
    "query": "strongest evidence the three captured VEHICLE labels resolve through the language archive",
    "candidates": [
        {"id": "cardata_enum", "text": "Each car's INGAME_TEXT_ENUM is read from the reference CARDATA block and equals the bridge enum."},
        {"id": "tlate_lookup", "text": "Each enum key resolves in tlate_en.dat;1 to a string equal to the on-screen label."},
        {"id": "byte_exact", "text": "The resolved string's raw UTF-16-LE bytes occur verbatim in the archive, including the 0x27 apostrophe."},
        {"id": "bridge_update", "text": "bridge-three-screens.json is updated with the resolved rows only when all three pass."},
    ], "top_k": 4})
run("t3-04-rerank", "jev_rerank", {
    "query": "next step after the three captured labels resolve through the archive",
    "candidates": [
        {"id": "close_t3", "text": "Gate the resolver and close T3."},
        {"id": "full_table", "text": "Resolve the full 136-entry TXT_CARS_* table."},
        {"id": "selector", "text": "Isolate the EE per-screen numeric selector word."},
        {"id": "stop", "text": "Stop; keep the three-pair result as the delivered scope."},
    ]})
run("t3-05-classify", "jev_classify", {
    "items": [
        {"id": "slot102", "text": "car 49_COUPE enum TXT_CARS_COUPE_1949 resolved 'FORD '49' == screen label 'FORD '49'"},
        {"id": "slot103", "text": "car THUNDERBIRD_2002 enum TXT_CARS_THUNDERBIRD_2002 resolved 'THUNDERBIRD CONVERTIBLE' == label"},
        {"id": "slot104", "text": "car FORTYNINE enum TXT_CARS_FORTYNINE resolved 'FORTYNINE CONCEPT' == label"},
    ],
    "classes": [
        {"id": "resolved_match", "description": "The archive key resolved and the string equals the screen VEHICLE label. Example: TXT_CARS_FORTYNINE -> FORTYNINE CONCEPT."},
        {"id": "resolved_mismatch", "description": "The key resolved to a different string than the screen label."},
        {"id": "unresolved", "description": "The key was absent from the archive, so no string resolved."},
        {"id": "manual_review", "description": "Ambiguous; needs a human check."},
    ],
    "purpose": "confirm each captured pair is a resolved match",
    "context": "Three captured pairs only; classes are mutually exclusive."})
run("t3-06-decide", "jev_decide", {
    "decision": "Is T3 (resolve the three captured VEHICLE labels via tlate_en.dat) complete enough to close?",
    "evidence": T3_EVID[:12000],
    "priorities": ("Scope is the three captured pairs only, never a 136-entry table; the apostrophe must be byte-exact "
                   "from the archive; update the bridge only on pass; render_fidelity_complete stays false."),
    "candidates": [
        {"id": "close_t3", "description": "Close T3: all three pairs resolve and equal the screen labels, apostrophe byte-exact from the archive."},
        {"id": "keep_open", "description": "Keep T3 open pending the full table or an isolated selector word."},
        {"id": "widen", "description": "Extend to all 136 TXT_CARS_* entries before closing."},
    ],
    "requirements": [
        "Covers exactly the three captured pairs",
        "Takes the apostrophe byte-exact from the archive",
        "Does not claim a 136-entry table",
    ]})
run("t3-07-compare", "jev_compare", {
    "passage_a": T3_REQ,
    "passage_b": T3_LOG,
    "aspects": ["enum from CARDATA", "tlate_en resolution", "apostrophe byte-exactness", "bridge update on pass", "scope of pairs"]})
_t3ext = run("t3-08-extract", "jev_extract", {
    "document": T3_LOG,
    "fields": [
        {"id": "archive_sha", "pattern": "\"archive_sha256\": \"[0-9a-f]{64}\"", "description": "sha256 of tlate_en.dat;1"},
        {"id": "pairs", "pattern": "\"pairs\": [0-9]+", "description": "number of captured pairs resolved"},
        {"id": "ford_bytes", "pattern": "\"utf16le_bytes_hex\": \"46004f00520044002000270034003900\"", "description": "UTF-16-LE bytes of FORD '49"},
        {"id": "result", "pattern": "\"result\": \"[A-Z ]+\"", "description": "final resolver result token"},
    ]})
_recs3 = []
_f3 = _t3ext.get("fields", {}) if isinstance(_t3ext, dict) else {}
for fid, fv in (_f3.items() if isinstance(_f3, dict) else []):
    _recs3.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("t3-09-audit", "jev_audit", {
    "source": T3_LOG,
    "records": _recs3 or [{"id": "result", "request": "extract result", "value": "VERIFY OK"}]})
run("t3-10-verify", "jev_verify", {
    "claims": [
        "tools/resolve_display_names.py prints VERIFY OK.",
        "TXT_CARS_COUPE_1949 resolves to FORD '49 and equals the slot102 VEHICLE label.",
        "TXT_CARS_THUNDERBIRD_2002 resolves to THUNDERBIRD CONVERTIBLE and equals the slot103 label.",
        "TXT_CARS_FORTYNINE resolves to FORTYNINE CONCEPT and equals the slot104 label.",
        "The apostrophe in FORD '49 is byte-exact from the archive.",
        "bridge-three-screens.json is updated with the resolved rows only when all three pairs pass.",
        "T3 resolves a 136-entry display-name table.",
    ],
    "evidence": T3_EVID})
run("t3-11-review", "jev_review", {
    "request": T3_REQ,
    "diff": T3_DIFF,
    "tests": REG})
run("t3-12-gate", "jev_gate", {
    "request": T3_REQ,
    "diff": T3_DIFF,
    "claims": [
        "tools/resolve_display_names.py passes and prints VERIFY OK.",
        "The three captured pairs resolve through tlate_en.dat;1 and equal the screens' VEHICLE labels.",
        "The FORD '49 apostrophe is byte-exact from the archive.",
        "bridge-three-screens.json is updated only on pass.",
        "No 136-entry table is claimed.",
    ],
    "evidence": T3_EVID,
    "tests": REG})

for tag, content in results.items():
    pass
print("T2+T3 BATTERY DONE")
