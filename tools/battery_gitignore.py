#!/usr/bin/env python3
"""Populate .gitignore via Jev: classify every candidate file group as keep or ignore.
Receipts: research/evidence/vehicle-completeness/jev-gitignore/gi-*.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/vehicle-completeness/jev-gitignore")
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
                c = {"parse_error": str(ex), "raw": str(c)[:400]}
    except Exception as e:
        c = {"error": str(e)}
    json.dump({"args": args, "result": c}, open(os.path.join(OUT, tag + ".json"), "w"), indent=2)
    results[tag] = c
    act = c.get("action") or (c.get("recommendation") or {}).get("action") if isinstance(c, dict) else None
    print(f"--- {tag:11} {tool:14} action={act}")
    return c


GROUPS = (
    "Candidate file groups in the carmodels repo (Ford Racing 2 recovery), with sizes:\n"
    "G1 tools/validation-runtime 1.1G: Blender dmg + mounted Blender.app (third-party, re-downloadable). "
    "Scripts validate GLBs through Blender.\n"
    "G2 tools/headless-runtime AppImage 57M: PCSX2 v2.8.2 AppImage, pinned emulator dependency for the container.\n"
    "G3 research/evidence/continuation/runtime 960M: 40 savestates (.p2s ~11MB each) + unpacked EE/IOP/VU/hw-reg "
    "dumps + 13M F8 screenshots. Receipts record sha256 of these files.\n"
    "G4 research/evidence/job-b-live 704M: pairs/*-eeMemory.bin + members/ extracted dumps (experiment working "
    "sets, rebuilt by the probe tools).\n"
    "G5 viewer 57M: web viewer incl. vendor three.js + 35 recovered .glb files.\n"
    "G6 reference 65M: the per-car reference corpus (models, textures, sounds) — the deliverable.\n"
    "G7 recovered 972K: canonical index + per-car manifests.\n"
    "G8 receipts JSON (~5M total): validation receipts, Jev receipts, tickets, reports.\n"
    "G9 tools/*.py + batteries: all scripts.\n"
    "G10 869 .pyc / __pycache__: bytecode regenerable.\n"
    "Context: user cancelled a 2.6GB push; wants a lean repo. GitHub rejects files >100MB (only the Blender "
    "files exceed it). Tools read the unpacked runtime dumps at fixed paths (e.g. verify_selector_word reads "
    "RUNTIME eeMemory.bin); excluding them means a fresh clone cannot re-run those tools without re-capturing.")

run("gi-01-screen", "jev_screen", {"text": GROUPS, "purpose": "review the file-group evidence before classifying"})
run("gi-02-noul", "jev_noul", {"propositions": [
    "The Blender vendor files (G1) should be ignored (re-downloadable, exceed GitHub limits).",
    "The PCSX2 AppImage (G2) should be kept (pinned dependency, under limits).",
    "The savestates and unpacked dumps (G3) should be ignored (regenerable via re-capture).",
    "The job-b-live working sets (G4) should be ignored (rebuilt by probe tools).",
    "The reference corpus (G6) must be kept (the deliverable).",
    "The F8 screenshots (13M, ground-truth evidence) should be kept.",
    "Excluding files that tools read at fixed paths is acceptable if documented.",
], "context": GROUPS})
run("gi-03-find", "jev_find", {"query": "the file group most important to keep in git",
    "candidates": [
        {"id": "corpus", "text": "G6 reference corpus 65M: the per-car deliverable everything joins against."},
        {"id": "receipts", "text": "G8 receipts JSON: sha256-pinned validation evidence and tickets."},
        {"id": "tools", "text": "G9 tools and verifier scripts."},
        {"id": "dumps", "text": "G3 savestates and unpacked memory dumps (960M)."},
    ], "top_k": 4})
run("gi-04-rerank", "jev_rerank", {"query": "rank groups by value of keeping in git versus size cost",
    "candidates": [
        {"id": "tools_receipts", "text": "Scripts + receipts + tickets + reports (small, the proof)."},
        {"id": "corpus", "text": "Reference corpus + recovered index (66M, the deliverable)."},
        {"id": "viewer", "text": "Viewer incl. vendor three.js + GLBs (57M)."},
        {"id": "appimage", "text": "PCSX2 AppImage (57M pinned dependency)."},
        {"id": "screenshots", "text": "F8 ground-truth screenshots (13M)."},
        {"id": "dumps", "text": "Savestates + unpacked dumps + working sets (1.6G, regenerable)."},
        {"id": "blender", "text": "Blender vendor files (1.1G, re-downloadable, over GitHub limits)."},
    ]})
run("gi-05-classify", "jev_classify", {"items": [
        {"id": "G1", "text": "Blender dmg + mounted app 1.1G, third-party, re-downloadable, exceeds GitHub 100MB limit."},
        {"id": "G2", "text": "PCSX2 AppImage 57M, pinned emulator dependency for the container."},
        {"id": "G3", "text": "Savestates + unpacked EE/IOP/VU dumps 960M, regenerable by re-capture; tools read them at fixed paths."},
        {"id": "G4", "text": "job-b-live pairs/members 704M, rebuilt by probe tools."},
        {"id": "G5", "text": "Viewer 57M incl. vendor three.js + recovered GLBs."},
        {"id": "G6", "text": "Reference corpus 65M, the deliverable."},
        {"id": "G10", "text": "869 .pyc bytecode files, regenerable."},
    ],
    "classes": [
        {"id": "keep", "description": "Belongs in git: deliverable, proof, or a pinned dependency under size limits. Example: the reference corpus."},
        {"id": "ignore", "description": "Belongs in .gitignore: regenerable, re-downloadable, over host limits, or machine-local. Example: bytecode caches."},
    ],
    "purpose": "decide keep vs ignore per file group",
    "context": "Lean repo after a cancelled 2.6GB push; GitHub 100MB file limit."})
run("gi-06-decide", "jev_decide", {
    "decision": "What is the keep/ignore split for the .gitignore?",
    "evidence": GROUPS,
    "priorities": "Lean repo; keep everything needed to understand and re-verify the work; never ignore the deliverable or the proof; document what a fresh clone cannot re-run.",
    "candidates": [
        {"id": "lean", "description": "Keep tools+receipts+corpus+viewer+AppImage+screenshots; ignore Blender vendor, savestates/dumps, working sets, bytecode."},
        {"id": "keep_dumps", "description": "Keep the savestates/dumps too (full reproducibility, ~2.6GB push)."},
        {"id": "minimal", "description": "Keep only tools+receipts; ignore corpus, viewer, AppImage as well."},
    ],
    "requirements": ["Fits GitHub limits", "Keeps the deliverable and the proof", "Smallest push that preserves the work"]})
run("gi-07-compare", "jev_compare", {
    "passage_a": "Ignore savestates/dumps: fresh clone re-captures; receipts keep sha256 pins.",
    "passage_b": "Keep savestates/dumps: tools read them at fixed paths; fresh clone re-runs everything.",
    "aspects": ["reproducibility", "push size", "what breaks on a fresh clone"]})
_g8 = run("gi-08-extract", "jev_extract", {"document": GROUPS,
    "fields": [
        {"id": "g1", "pattern": "1\\.1G", "description": "Blender vendor size"},
        {"id": "g3", "pattern": "960M", "description": "runtime dumps size"},
        {"id": "limit", "pattern": "100MB", "description": "the GitHub file limit"},
    ]})
_r = []
_f = _g8.get("fields", {}) if isinstance(_g8, dict) else {}
for fid, fv in (_f.items() if isinstance(_f, dict) else []):
    _r.append({"id": fid, "request": "extract " + fid, "value": fv.get("value", "") if isinstance(fv, dict) else ""})
run("gi-09-audit", "jev_audit", {"source": GROUPS, "records": _r or [{"id": "limit", "request": "extract limit", "value": "100MB"}]})
run("gi-10-verify", "jev_verify", {"claims": [
    "Only the Blender files exceed GitHub's 100MB file limit.",
    "The reference corpus is the deliverable and must be kept.",
    "Savestates and unpacked dumps are regenerable by re-capture.",
    "A fresh clone without the dumps cannot re-run the tools that read them at fixed paths.",
], "evidence": GROUPS})
run("gi-11-review", "jev_review", {"request": "Adopt the lean .gitignore split.",
    "diff": "+ ignore: Blender vendor, *.p2s, unpacked memory dumps, job-b-live working sets, bytecode, OS cruft\n+ keep: tools, receipts, reference corpus, viewer, AppImage, screenshots\n+ document what a fresh clone cannot re-run",
    "tests": "git status shows only intended files tracked"})
run("gi-12-gate", "jev_gate", {"request": "Gate the lean .gitignore split.",
    "diff": json.dumps({"keep": ["tools", "receipts", "reference", "viewer", "AppImage", "screenshots"],
                        "ignore": ["blender", "sstates/dumps", "working-sets", "bytecode"]}, indent=1),
    "claims": [
        "Everything over GitHub limits is ignored.",
        "The deliverable and the proof are kept.",
        "A fresh clone can rebuild everything except re-capturing live emulator state.",
    ],
    "evidence": GROUPS + "\n\nDecide: " + json.dumps(results.get("gi-06-decide", {}))[:1500]})

print("GITIGNORE JEV DONE", len(results), "calls")
