#!/usr/bin/env python3
"""D3 battery: what counts as verified-full per vehicle, and what becomes tracer tickets.
All 12 Jev tools. Jev advises; code owns bytes, counts, hashes."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness")
os.makedirs(OUT, exist_ok=True)

EVIDENCE_DOC = (
    "Canonical index (recovered/index.json) counts: original_model 35, glb 35, model textures "
    "700 display + 700 raw, mip planes 94 + stored-alpha 94, original_icon 35 + raw/display 35 each, "
    "original_livery 136 + raw/display 136 each, original_matrix 136 + csm0-swap raw/display 136 each. "
    "Status: 'Asset/index integrity checked. Rendering-fidelity completion not asserted.' "
    "Independent verifier tools/verify_recovered_asset_index.py checks roster/index/disk set equality, "
    "per-car producer-record equality, every asset hash/size, plus negative controls "
    "(corrupt manifest hash, cross-car model swap, schema/fidelity/status/limits mutations). "
    "Reference corpus per car (spot-checked 49_COUPE, THUNDERBIRD_2002, FORTYNINE): config/ (11 txt: "
    "cardata, body, engine, gearbox, tyres_front/back, brake, control, overlay, setup, sound), model/*.PS2;1, "
    "graphics/icon + 4 liveries, data/*.DAT;1; sound banks in reference/ford/_shared/sounds with per-car "
    "inheritance chains in manifests. The canonical index does NOT cover config txt, data DAT, or sound chains. "
    "Known open lists (unchanged): 158 unmatched retained descriptors, glass naming, ChallGlo blend, passes 4-5 RGB.")

results = {}
def run(name, tool, args):
    try:
        res = call(tool, args)
        content = res.get("result", res)
        if isinstance(content, dict) and "content" in content:
            try: content = json.loads(content["content"][0]["text"])
            except Exception as ex: content = {"parse_error": str(ex)}
    except Exception as e:
        content = {"error": str(e)}
    json.dump({"args": args, "result": content}, open(os.path.join(OUT, name + ".json"), "w"), indent=2)
    results[tool] = content
    print("---", tool, "->", name)
    print(json.dumps(content, indent=1)[:1100])

run("d3-01-screen", "jev_screen", {"text": EVIDENCE_DOC[:3000], "purpose": "decide per-vehicle completeness scope and tracer tickets"})
run("d3-02-noul", "jev_noul", {"propositions": [
    "The canonical index plus its verifier covers every per-vehicle satellite kind in the reference corpus.",
    "Per-car config txt, data DAT and sound-bank chains are outside the canonical index and need their own parity ticket.",
    "A green verifier run closes vehicle extraction completeness for geometry, textures, liveries, matrix icons and GLBs.",
    "The 158 unmatched retained descriptors indicate vehicles missing from the extraction.",
    ], "context": EVIDENCE_DOC[:6000]})
run("d3-03-find", "jev_find", {"query": "strongest completeness signal per vehicle in the existing evidence",
    "candidates": [
        {"id": "index_counts", "text": "Canonical index counts: 35 models, 35 GLBs, 136 liveries, 136 matrix sets."},
        {"id": "verifier", "text": "Independent verifier: roster/index/disk equality, per-car record equality, all hashes, negative controls."},
        {"id": "corpus_manifests", "text": "Per-car corpus manifests with per-file sha256 and sound inheritance chains."},
        {"id": "census", "text": "Model census car-asset-census.json with per-car texture lists and sha256."}], "top_k": 4})
run("d3-04-rerank", "jev_rerank", {"query": "order of follow-up work after the verifier run",
    "candidates": [
        {"id": "gate", "text": "Run jev_gate over the verifier log before claiming anything."},
        {"id": "config_data_sound_ticket", "text": "Write tracer ticket: config/data/sound parity per car (outside canonical index)."},
        {"id": "more_extraction", "text": "Extract additional per-car assets beyond the corpus."},
        {"id": "render_fidelity", "text": "Pursue final render-fidelity completion."},
        {"id": "stop", "text": "Stop; index counts alone are sufficient evidence."}]})
run("d3-05-classify", "jev_classify", {
    "items": [
        {"id": "geometry_textures_liveries_glb", "text": "Model PS2, 700+700 textures, 94 mips, 136 liveries, 136 matrix sets, 35 GLBs, all in canonical index with hashes."},
        {"id": "config_data_sound", "text": "Per-car config txt (11 files), data DAT, _shared sound banks with inheritance chains; in corpus manifests, not in canonical index."},
        {"id": "render_fidelity", "text": "Final game-render fidelity, materials, normals, winding, runtime trees; explicitly not asserted anywhere."}],
    "classes": [
        {"id": "verifier_covered", "description": "Checked by verify_recovered_asset_index.py against producer receipts with negative controls. Example: model/texture/livery sha equality."},
        {"id": "needs_ticket", "description": "Real per-car content with no canonical parity check; needs a tracer ticket. Example: config txt and data DAT files."},
        {"id": "explicitly_out", "description": "Declared out of scope in index status/limits. Example: final render fidelity."}],
    "purpose": "sort per-vehicle content into verified, ticketed, or explicitly out of scope",
    "context": "Vehicle completeness close-out; classes are mutually exclusive."})
run("d3-06-decide", "jev_decide", {
    "decision": "What counts as verified-full per vehicle, and what becomes tracer tickets?",
    "evidence": EVIDENCE_DOC[:12000],
    "priorities": "Code owns counts and hashes; judgments only route. A green verifier run plus gate closes geometry/textures/liveries/matrix/GLB. Config/data/sound get a parity ticket, not a silent pass. Render fidelity stays explicitly out. No new extraction without a failing check.",
    "candidates": [
        {"id": "verify_then_ticket", "description": "Run the independent verifier now; gate it; write one tracer ticket for config/data/sound parity per car."},
        {"id": "index_counts_enough", "description": "Accept index counts without running the verifier."},
        {"id": "extract_more_first", "description": "Extract more per-car assets before verifying."},
        {"id": "claim_full", "description": "Claim full vehicle extraction complete including render fidelity."}],
    "requirements": [
        "Every claimed byte is hash-checked by code, not by judgment",
        "Uncovered per-car content gets a ticket instead of a pass",
        "Render fidelity stays explicitly unclaimed"]})
run("d3-07-compare", "jev_compare", {"passage_a": "Canonical index counts: 35 models, 35 GLBs, 136 liveries, 136 matrix sets. Status: integrity checked, fidelity not asserted.",
    "passage_b": "Per-car corpus adds config txt, data DAT and shared sound chains with manifests, outside the canonical index.",
    "aspects": ["covered content", "uncovered content", "fidelity claims"]})
run("d3-08-extract", "jev_extract", {"document": EVIDENCE_DOC[:3000], "fields": [
    {"id": "n_models", "pattern": "original_model 35", "description": "count of original models in the index"},
    {"id": "n_liveries", "pattern": "original_livery 136", "description": "count of original liveries in the index"},
    {"id": "n_glb", "pattern": "glb 35", "description": "count of GLBs in the index"},
    {"id": "verifier", "pattern": "verify_recovered_asset_index\\.py", "description": "filename of the independent verifier"},
    {"id": "status_line", "pattern": "Rendering-fidelity completion not asserted", "description": "fidelity disclaimer in index status"}]})
ext = results.get("jev_extract", {})
recs = []
f = ext.get("fields", {}) if isinstance(ext, dict) else {}
for fid, fv in (f.items() if isinstance(f, dict) else []):
    recs.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("d3-09-verify", "jev_verify", {"claims": [
    "The canonical index holds 35 original models, 35 GLBs, 136 liveries and 136 matrix sets.",
    "The independent verifier checks roster/index/disk equality, per-car record equality, all hashes, and negative controls.",
    "Per-car config txt, data DAT and sound chains live in the corpus but outside the canonical index.",
    "Render fidelity is explicitly not asserted in the index status."],
    "evidence": EVIDENCE_DOC})
run("d3-10-audit", "jev_audit", {"source": EVIDENCE_DOC[:3000], "records": recs or [
    {"id": "n_models", "request": "extract n_models", "value": "original_model 35"}]})
run("d3-11-review", "jev_review", {
    "request": "Verify full-vehicle extraction end to end: run the independent verifier, gate the result, write tracer tickets for any real gaps.",
    "diff": ("+ ran tools/verify_recovered_asset_index.py (roster/index/disk equality, per-car record equality, all hashes, 4 negative-control families)\n"
     "+ census: per-car corpus holds config x11, model, icon, 4 liveries, data DAT; sound in _shared with chains\n"
     "+ canonical index covers model/textures/mips/liveries/matrix/GLB only; config/data/sound uncovered\n"
     "+ no new extraction performed; no fidelity claims")})
decide = results.get("jev_decide", {})
sel = (decide.get("recommendation", {}) or {}).get("selected", "unknown") if isinstance(decide, dict) else "unknown"
run("d3-12-gate", "jev_gate", {
    "request": "Decide the per-vehicle completeness scope and ticket set.",
    "diff": json.dumps({"decision": "d3-completeness-scope", "selected": sel,
                         "tickets": ["config-data-sound parity per car"]}, indent=1),
    "claims": [
        "Geometry, textures, liveries, matrix and GLBs are verifier-closed, not count-asserted.",
        "Config, data DAT and sound chains get a tracer ticket instead of a silent pass.",
        "Render fidelity stays explicitly unclaimed."],
    "evidence": EVIDENCE_DOC + "\nDecide: " + json.dumps(decide)[:2000]})
print("D3 DONE")
