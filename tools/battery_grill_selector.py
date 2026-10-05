#!/usr/bin/env python3
"""Grill round 2 Jev battery: the selector word's existence/storage form and the
fallback if the decompiled label chain names no per-screen selector field.

Receipts: research/evidence/vehicle-completeness/jev-grill/n-*.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-grill")
os.makedirs(OUT, exist_ok=True)
results = {}


def R_(tag):
    return json.load(open(os.path.join(OUT, tag + ".json")))["result"]


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


SELECTOR_EV = (
    "carselection bridge: no FORD'49 / TXT_CARS_* label bytes in slot102 EE (labels via text archive + glyphs). "
    "Static leads: FUN_0019eb90 reads the livery label via static table VA 0x23acb0 (packed strings INVALID/WHEELS/"
    "FUEL), resolves via FUN_00125640, stores via FUN_00121e10; VA_0x23acb0 = 0x0028f7c8 stable across captures. "
    "jgrep hits: 0017cb80 (initials cycler, discarded), 00184430 (1..3 cursor on uRam0028fd74, reads 0 in all "
    "three), 001c4a40 (indexed cursor over DAT_00241b40, caller open). VA_0x241b60 = 5,4,4 (does not track "
    "highlight). Three-way triangulation: (1,5,4) 0 hits; (0,4,3) words 0 hits; (0,4,3) bytes 97 hits in VU "
    "regions, no menu-struct candidate; scratchpad 121 changed words all float VU noise. Screens: highlight 1/5/4 "
    "-> 49_COUPE / THUNDERBIRD_2002 / FORTYNINE, all DEFAULT livery. Jev round-1 noul: 'an isolated EE word that "
    "tracks the highlight exists' = 0.13 unlikely; 'deriving the store address from the FUN_0019eb90 chain will "
    "name it' = 0.29 uncertain; 'value-only match sufficient' = 0.09 unlikely. Round-1 decide chose trace_store 0.96.")

run("n-01-screen", "jev_screen", {"text": SELECTOR_EV, "purpose": "selector design evidence for the fallback decision"})
run("n-02-noul", "jev_noul", {"propositions": [
    "The per-screen menu highlight is stored as a plain 16/32-bit integer word in EE main RAM.",
    "The highlight/selector value is reached only via pointer indirection or a heap struct, so a direct byte diff will not reveal it.",
    "The decompiled cursor code (001c4a40 over DAT_00241b40) has already narrowed the highlight to a small candidate set.",
    "If the trace of FUN_0019eb90/FUN_00125640/FUN_00121e10 names no per-screen selector field, the thread should be recorded open rather than chased further.",
    "Capturing more screens will eventually reveal the selector word by diff.",
    "The three-pair bridge is a sufficient delivered result for the selector thread even if the word is never isolated.",
], "context": SELECTOR_EV})
run("n-03-find", "jev_find", {"query": "best fallback if the label chain names no per-screen selector field",
    "candidates": [
        {"id": "broaden_indirect", "text": "Trace indirect/pointer structures reached from the label chain and the menu draw path."},
        {"id": "record_open", "text": "Record the selector thread open, with the three-pair bridge as the delivered result."},
        {"id": "more_screens", "text": "Capture more screens with varied highlight and livery and diff."},
        {"id": "drop", "text": "Drop the selector thread entirely."},
    ], "top_k": 4})
run("n-04-rerank", "jev_rerank", {"query": "next concrete act after tracing the label chain",
    "candidates": [
        {"id": "read_store", "text": "Read the store address from FUN_00121e10 in the three EE images."},
        {"id": "resolve_caller", "text": "Resolve the 001c4a40 caller and read DAT_00241b40's selected index."},
        {"id": "menu_struct", "text": "Locate the menu cursor struct from the highlight-draw code."},
        {"id": "record_open", "text": "Record the thread open and stop."},
    ]})
run("n-05-classify", "jev_classify", {"items": [
        {"id": "plain_word", "text": "Highlight stored as a plain integer word in EE RAM."},
        {"id": "indirect", "text": "Selection reached only via pointer/heap struct."},
        {"id": "no_bytes", "text": "No label strings in EE; labels via archive + glyphs."},
        {"id": "no_word_hit", "text": "0 word hits for the highlight tuple; 97 noisy byte hits."},
    ],
    "classes": [
        {"id": "supports_direct_word", "description": "Evidence that a plain integer word holds the highlight. Example: a small-int cursor in RAM."},
        {"id": "supports_indirection", "description": "Evidence the value is behind a pointer/struct so direct diffs miss it. Example: label bytes absent and draw code indirection."},
        {"id": "neutral", "description": "Consistent with both storage forms."},
    ],
    "purpose": "sort selector evidence by storage form",
    "context": "Selector thread design."})
run("n-06-decide", "jev_decide", {
    "decision": "If tracing the label chain names no per-screen selector field, what is the fallback for the selector thread?",
    "evidence": SELECTOR_EV,
    "priorities": "Prefer a named address or a definite recorded outcome over unbounded searching; keep the three-pair bridge as the delivered result; do not re-run value-only triangulation; keep render fidelity unclaimed.",
    "candidates": [
        {"id": "broaden_indirect", "description": "Trace indirect/pointer structures reached from the label chain and menu draw path."},
        {"id": "record_open", "description": "Record the selector thread open with the three-pair bridge as delivered."},
        {"id": "more_screens", "description": "Capture more screens and diff."},
        {"id": "drop", "description": "Drop the thread."},
    ],
    "requirements": ["Produces a named address or a definite recorded outcome", "Does not rely on value-only matching", "Keeps the bridge as the floor"]})
run("n-07-compare", "jev_compare", {
    "passage_a": "The selector is a plain integer word in EE main RAM, findable by diff.",
    "passage_b": "The selector is behind a pointer/struct reached from the menu draw path, so a direct diff misses it.",
    "aspects": ["what a diff would show", "how the label chain relates", "plausibility given the failed triangulation"]})
_n8 = run("n-08-extract", "jev_extract", {"document": SELECTOR_EV,
    "fields": [
        {"id": "cursor", "pattern": "DAT_00241b40", "description": "the indexed cursor table address"},
        {"id": "store_fn", "pattern": "FUN_00121e10", "description": "the store function"},
        {"id": "word_hits", "pattern": "words [0-9]+ hits", "description": "word-level triangulation count"},
        {"id": "unlikely_p", "pattern": "= 0.13 unlikely", "description": "the noul probability that an isolated word exists"},
    ]})
_r = []
_f = _n8.get("fields", {}) if isinstance(_n8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("n-09-audit", "jev_audit", {"source": SELECTOR_EV, "records": _r or [{"id": "store_fn", "request": "extract store_fn", "value": "FUN_00121e10"}]})
run("n-10-verify", "jev_verify", {"claims": [
    "No label bytes exist in the slot102 EE image.",
    "0 word hits and 97 byte hits were found for the highlight tuple.",
    "The highlight is stored as a plain integer word in EE main RAM.",
    "The three-pair bridge pairs highlight 1/5/4 to the three cars.",
], "evidence": SELECTOR_EV})
run("n-11-review", "jev_review", {"request": "Define the fallback for the selector thread when the decompiled label chain names no per-screen selector field.",
    "diff": "+ primary: read FUN_0019eb90/FUN_00125640/FUN_00121e10 store address, read it in slots 102/103/104\n"
            "+ fallback: trace indirect structures from the label/draw path, OR record the thread open with the three-pair bridge floor\n"
            "+ never count a value-only match as proof",
    "tests": "existing verifiers stay green"})
run("n-12-gate", "jev_gate", {"request": "Adopt the selector plan with a named-address-or-recorded-open fallback.",
    "diff": "+ trace the store; if unnamed, broaden to indirection or record open\n+ bridge remains the floor; no value-only proof",
    "claims": [
        "The plan's floor is the three-pair bridge.",
        "The plan does not rely on value-only matching.",
        "The plan produces either a named address or a recorded open outcome.",
    ],
    "evidence": SELECTOR_EV + "\n\nDecide: " + json.dumps(results.get("n-06-decide", {}))[:1500]})

print("GRILL ROUND-2 DONE", len(results), "calls")
