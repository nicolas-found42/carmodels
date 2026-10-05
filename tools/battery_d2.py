#!/usr/bin/env python3
"""D2 battery: what the three ordinary-capture screens establish for the
numeric-livery-selector -> human-label bridge. All 12 Jev tools. Jev advises;
code owns bytes, counts, hashes."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/carselection-2026-10-05")
os.makedirs(OUT, exist_ok=True)

T102 = ("Ground-truth emulator screenshot slot102: Living Legends, thumbnail 1 highlighted "
        "(pale green Ford), VEHICLE: FORD '49, TRACK: ROUTE 50, TYPE: DRIVING SKILLS, STATUS UNLOCKED, "
        "ROOKIE 0%, BACK/OK prompts.")
T103 = ("Ground-truth emulator screenshot slot103: Living Legends, thumbnail 5 highlighted (white car), "
        "VEHICLE: THUNDERBIRD CONVERTIBLE, TRACK: DEER CREEK, TYPE: DRAFTING, STATUS UNLOCKED.")
T104 = ("Ground-truth emulator screenshot slot104 (vision transcript, model-generated): Living Legends, "
        "thumbnail 4 highlighted, VEHICLE: FORTYNINE CONCEPT, TRACK: PORT SIDE, TYPE: RACING LINE, STATUS UNLOCKED.")
EE = ("EE scans (code-measured): six static 12-name livery tables present in slot102 at "
      "0x0143b736,0x0157e365,0x016b7934,0x017ec5aa,0x0192f915,0x01a5856e; record bases "
      "0x233070+type*0x114 with count 12 for types 2..7, all words unchanged between slot102 and slot103. "
      "No FORD'49/ROUTE 50/label strings in EE (labels come from text archive + glyphs). "
      "Three-way word triangulation for highlight tuples (0,4,3)/(1,5,4): 0 hits. "
      "Byte-level (0,4,3): 97 hits, clustered in VU-packet regions; (1,5,4): 0 hits. "
      "Scratchpad diffs are float-scale VU noise. L key moved highlight leftward (5->4 single step; "
      "1->5 via wrap under hold), contrary to the assumed L=Right mapping.")
EVIDENCE_DOC = ("Screens:\n- " + T102 + "\n- " + T103 + "\n- " + T104 + "\nEE:\n" + EE + "\n"
      "Captures: slot102 sha 6e39717778e9887c2fe65a370098c391ab974a0d109d60d74d6c0b3afa47f1e7, "
      "slot103 sha b5e569fcc561fa3a5408f6eb0a7a6497594e52bdb26f5cdb2dbfeed31dc56c3e, "
      "slot104 sha 74acb509d464d9def05f5a233a5b79142ff12534ac9c21415ecb44d821940694. "
      "19 key presses used of 30 budget. Slot 100 untouched; slot 101 backs up the pre-experiment live state.")

results = {}
def run(name, tool, args):
    try:
        res = call(tool, args)
        content = res.get("result", res)
        if isinstance(content, dict) and "content" in content:
            try: content = json.loads(content["content"][0]["text"])
            except Exception as ex: content = {"parse_error": str(ex), "raw": str(content)[:500]}
    except Exception as e:
        content = {"error": str(e)}
    json.dump({"args": args, "result": content}, open(os.path.join(OUT, name + ".json"), "w"), indent=2)
    results[tool] = content
    print("---", tool, "->", name)
    print(json.dumps(content, indent=1)[:1200])

run("d2-01-screen", "jev_screen", {"text": T104, "purpose": "bridge label transcription for livery-selector join"})
run("d2-02-noul", "jev_noul", {
    "propositions": [
        "Thumbnail 1 (FORD '49) is the 49_COUPE car type whose MATRIX icon is 49couped.ptg.",
        "Thumbnail 5 (THUNDERBIRD CONVERTIBLE) is the THUNDERBIRD_2002 car type whose icon is tbird22d.ptg.",
        "Thumbnail 4 (FORTYNINE CONCEPT) is the FORTYNINE car type whose icon is fortyd.ptg.",
        "The EE livery-name tables stayed identical because the tables are static and selection lives elsewhere.",
        "A single isolated highlight-index word exists in EE memory for these menu screens.",
    ], "context": EVIDENCE_DOC[:6000]})
run("d2-03-find", "jev_find", {
    "query": "strongest EE anchor tying a captured screen to its numeric livery selector",
    "candidates": [
        {"id": "six_tables", "text": "Six static 12-name livery tables at fixed EE addresses, unchanged across captures."},
        {"id": "record_abi", "text": "Record layout 0x233070+type*0x114 with count 12 and list pointers matching the six tables."},
        {"id": "fun_19eb90", "text": "FUN_0019eb90 reads the gameflow livery label from static table VA 0x23acb0 and resolves it via FUN_00125640."},
        {"id": "triangulation", "text": "Three-way byte/word diff hits for highlight tuples (97 noisy byte hits, 0 word hits)."},
    ], "top_k": 4})
run("d2-04-rerank", "jev_rerank", {
    "query": "next analysis step to close the numeric-selector to human-label bridge",
    "candidates": [
        {"id": "read_19eb90_addrs", "text": "Read FUN_0019eb90/FUN_00125640 disassembly for the selector-store address, then read that word in all three EE images."},
        {"id": "menu_state_struct", "text": "Find the menu cursor struct via the highlight-draw code and read the selected car/type field per capture."},
        {"id": "more_screens", "text": "Capture more thumbnail screens (cars 2, 3, 6) for a bigger label set."},
        {"id": "text_archive", "text": "Resolve TXT_CARS_COUPE_1949/TXT_CARS_FORTYNINE through the language archive to the rendered strings."},
        {"id": "stop_claim", "text": "Stop and report the three pairs as a partial bridge without an isolated selector word."},
    ]})
run("d2-05-classify", "jev_classify", {
    "items": [
        {"id": "slot102", "text": T102},
        {"id": "slot103", "text": T103},
        {"id": "slot104", "text": T104},
    ],
    "classes": [
        {"id": "labeled_vehicle", "description": "Screen shows a highlighted car plus a readable VEHICLE label naming it. Example: VEHICLE: FORD '49 with thumbnail 1 highlighted."},
        {"id": "unlabeled_strip", "description": "Car strip visible but no VEHICLE detail text for the highlight. Example: theme screen before pressing Cross."},
        {"id": "manual_review", "description": "Label/highlight relationship ambiguous; needs a human look at the screenshot."},
    ],
    "purpose": "confirm each capture carries a usable human label for the bridge",
    "context": "Three ordinary-capture screens; classes are mutually exclusive."})
run("d2-06-decide", "jev_decide", {
    "decision": "What does the three-screen evidence establish for the numeric-selector to human-label bridge?",
    "evidence": EVIDENCE_DOC[:12000],
    "priorities": "Claim only what two-to-three screens support; never a 136-entry table. Keep render_fidelity_complete false. Counts, hashes and addresses come from code, not from judgments. Preserve negative results (failed triangulation, contradicted mapping).",
    "candidates": [
        {"id": "partial_pairs", "description": "Three observed (highlighted car, VEHICLE label, track/type) pairs plus static-table presence form a real but partial bridge; the isolated per-screen selector word is still open."},
        {"id": "closed", "description": "The bridge is closed: labels fully joined to numeric selector words per screen."},
        {"id": "no_bridge", "description": "No bridge: the screens contribute nothing beyond what static analysis already had."},
        {"id": "need_selector_word", "description": "Do not write the bridge yet; first read the FUN_0019eb90 selector-store address in all three images."},
    ],
    "requirements": [
        "Stays within what three observed screens can support",
        "Does not invent EE addresses or selector-word values",
        "Keeps negative results (failed isolation) visible",
    ]})
run("d2-07-compare", "jev_compare", {
    "passage_a": T102, "passage_b": T104,
    "aspects": ["highlighted car", "vehicle label", "track and type", "status"]})
run("d2-08-extract", "jev_extract", {
    "document": ("slot102 sha 6e39717778e9887c2fe65a370098c391ab974a0d109d60d74d6c0b3afa47f1e7 "
      "slot103 sha b5e569fcc561fa3a5408f6eb0a7a6497594e52bdb26f5cdb2dbfeed31dc56c3e "
      "slot104 sha 74acb509d464d9def05f5a233a5b79142ff12534ac9c21415ecb44d821940694 "
      "labels VEHICLE: FORD '49; VEHICLE: THUNDERBIRD CONVERTIBLE; VEHICLE: FORTYNINE CONCEPT. "
      "slots 101,102,103,104; record base 0x233070; tables 0x0143b736 0x0157e365."),
    "fields": [
        {"id": "slot102_sha", "pattern": "slot102 sha [0-9a-f]{64}", "description": "full hex sha256 of the slot102 savestate"},
        {"id": "slot104_sha", "pattern": "slot104 sha [0-9a-f]{64}", "description": "full hex sha256 of the slot104 savestate"},
        {"id": "label_ford49", "pattern": "VEHICLE: FORD '49", "description": "vehicle label shown on the car-1 screen"},
        {"id": "label_tbird", "pattern": "VEHICLE: THUNDERBIRD CONVERTIBLE", "description": "vehicle label shown on the car-5 screen"},
        {"id": "label_49concept", "pattern": "VEHICLE: FORTYNINE CONCEPT", "description": "vehicle label shown on the car-4 screen"},
        {"id": "rec_base", "pattern": "0x233070", "description": "EE base of the selector-record array"},
        {"id": "table1", "pattern": "0x0143b736", "description": "EE address of the first livery-name table in slot102"},
    ]})
ext = results.get("jev_extract", {})
recs = []
f = ext.get("fields", {}) if isinstance(ext, dict) else {}
for fid, fv in (f.items() if isinstance(f, dict) else []):
    recs.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("d2-09-verify", "jev_verify", {
    "claims": [
        "Slot102 shows thumbnail 1 with VEHICLE: FORD '49, TRACK: ROUTE 50, TYPE: DRIVING SKILLS.",
        "Slot103 shows thumbnail 5 with VEHICLE: THUNDERBIRD CONVERTIBLE, TRACK: DEER CREEK, TYPE: DRAFTING.",
        "Slot104 shows thumbnail 4 with VEHICLE: FORTYNINE CONCEPT, TRACK: PORT SIDE, TYPE: RACING LINE.",
        "The six 12-name EE livery tables are unchanged between slot102 and slot103.",
        "No isolated highlight-index word was found by three-way triangulation.",
    ],
    "evidence": EVIDENCE_DOC})
run("d2-10-audit", "jev_audit", {
    "source": "slot102 sha 6e39717778e9887c2fe65a370098c391ab974a0d109d60d74d6c0b3afa47f1e7 labels VEHICLE: FORD '49; VEHICLE: THUNDERBIRD CONVERTIBLE; VEHICLE: FORTYNINE CONCEPT. record base 0x233070, table 0x0143b736.",
    "records": recs or [{"id": "label_ford49", "request": "extract label_ford49", "value": "VEHICLE: FORD '49"}]})
run("d2-11-review", "jev_review", {
    "request": "Reach a real car-selection screen by ordinary controller input headless; save new slots with extracted members and hashes; join on-screen labels to the numeric livery selector without claiming a full table.",
    "diff": ("+ connected hidden browser to noVNC, proved Space delivery (status 1->0)\n"
      "+ loaded slot 98, unpaused to Living Legends theme screen\n"
      "+ Cross on highlighted car opened the VEHICLE/TRACK/TYPE/STATUS detail panel\n"
      "+ captured 3 labeled screens (cars 1, 5, 4) into slots 102, 103, 104 with unpacked members\n"
      "+ L key moved highlight leftward (5->4 step; 1->5 wrap under hold), against assumed L=Right\n"
      "+ EE: six static 12-name tables unchanged; triangulation found no isolated highlight word\n"
      "+ slot 100 untouched; slot 101 backs up pre-experiment live state")})
decide = results.get("jev_decide", {})
sel = (decide.get("recommendation", {}) or {}).get("selected", "unknown") if isinstance(decide, dict) else "unknown"
run("d2-12-gate", "jev_gate", {
    "request": "Decide what the three ordinary-capture screens establish for the numeric-selector to human-label bridge.",
    "diff": json.dumps({"decision": "d2-bridge-interpretation", "selected": sel,
                         "screens": ["slot102/car1/FORD'49", "slot103/car5/THUNDERBIRD-CONVERTIBLE",
                                     "slot104/car4/FORTYNINE-CONCEPT"]}, indent=1),
    "claims": [
        "Three ordinary-capture screens pair highlighted cars with human VEHICLE labels.",
        "The six EE livery-name tables are static across captures; selection state lives elsewhere.",
        "No isolated highlight/selector word is claimed; the full-table bridge stays open.",
    ],
    "evidence": EVIDENCE_DOC + "\nDecide: " + json.dumps(decide)[:2500]})
print("D2 DONE")
