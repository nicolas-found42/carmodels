# Dealership editing and agent environment improvements

Implemented all five candidates from the session retrospective. Production dealership/source
models were preserved; the changes are editing compatibility, checks, evidence and review tooling.

## Real editing roundtrip

`tools/test_dealership_roundtrip.py` runs in pinned Blender 4.5.14. It imports the Gran Torino's
default-scene collection, retains normals/custom properties, re-encodes images, exports a baseline,
lengthens mesh vertices by 20% along the longitudinal axis and exports again. The display builder
preserves 4,072 triangles and wheel metadata, receives the geometry edit, reproduces compiled output
on another build and leaves all 70 production dealership/source GLBs unchanged. All editing happens
in temporary copies. Blender's `--python-exit-code 1` makes a failed assertion fail the command.

Editable-model PNG decoding now lives in `tools/model_png.py`, with RGB8/RGBA8 and row filters 0–4.
Tests cover independently calculated filter residuals, RGB conversion, corrupted CRC, truncated
chunks, invalid filters and payload size. The pinned source-mode recovery decoder is unchanged.
The tested export settings are in `viewer/dealership/README.md`. The Blender options were checked
against the vendor's [export operator documentation](https://docs.blender.org/api/dev/bpy.ops.export_scene.html)
and, decisively, exercised in the pinned local runtime.

## Freshness and executed check evidence

`python3 tools/build_dealership.py --check` recomputes display data from current dealership models
and catalog and compares it with compiled JSON without writing anything. Geometry-only edits,
catalog edits and absent output make the comparison fail. It runs as `dealership_freshness` in
the normal suite. A normal build continues to preserve editable inputs.

`tools/check.sh` delegates to `tools/run_checks.py`. It supports `--list`, repeatable/comma-separated
`--only` and `--evidence-dir`. Default runs use unique `.scratch/checks/run-*` directories. Each
command has a complete retained log, exit code, duration and pass/fail/skip state in `results.json`.
Failures accumulate across later successes. Unknown names fail and existing evidence is preserved.
Controls exercise masked-failure prevention and all five actual JavaScript registry entries with
Node absent in CI. Optional private input availability remains explicit and distinct from a pass.

The final local run recorded 29 passing checks, no skips and exit code 0. Full evidence is
`evidence/retro-implementation-2026-10-08/final-checks/`. A hash comparison against this task's
starting state verified all 827 source/recovery files and 35 dealership GLBs unchanged; other
pre-existing work remained unchanged outside the explicit task scope. See `preservation.json`.

## Review tooling and CI

`tools/review_payload.py` captures an explicit text-file task baseline, including expected new
files, then builds raw unified diffs with rename detection. Review calls use bounded whole-file
diff groups without clipping hunks. Verification calls are separate, with at most two claims
and full check logs. Oversized inputs fail before submission. Existing review outputs survive.

Receipt status checks bind arguments to the submitted bundle. Missing/malformed/stale receipts,
unknown actions, invalid confidence, operational failures and contradicted claims block acceptance.
Valid review/escalation verdicts need an independent reviewer record tied to the bundle digest.
The implementer cannot supply its own reviewer identity, and a resolution cannot override missing
receipts or contradicted claims. These are workflow records, not reviewer identity authentication.
Executable controls and the procedure are in `tools/test_review_payload.py` and
`docs/agents/review-workflow.md`. A four-call bounded bundle was generated from the actual task
baseline and final check logs under `review-bundle/`; preparation itself is not judgment approval.

CI explicitly provisions Node 22 and pinned Linux Blender 4.5.14, verifies the vendor archive hash,
runs the common check command and uploads complete evidence on success or failure. Missing mandatory
runtimes fail in CI. The Linux archive URL returned HTTP 200 during this task. The revised GitHub
Actions workflow has not been executed remotely in this uncommitted local session.

## Jev judgment

The final core gate reviewed raw logic, changed tests and CI diff with the complete executed logs
and preservation receipt. It escalated: safe-to-apply 0.43, composite 0.70025, correctness confidence
0.40 and test-gap confidence 0.03. The combined check/preservation claim was verified at confidence
0.59, requiring review; none was contradicted. The original result is retained as `jev-gate.json`.
It was not rerun to obtain different scores. The explicitly invoked Jev escalation policy routed
this uncertainty to an independently assigned reviewer; the reviewer outcome is stored separately.

The independent reviewer `/root/retro_escalation_review` approved after examining the patch and
evidence and reported no concrete blocker in the five improvements. This resolves the patch and
claim uncertainty through the documented independent-review route; it does not alter Jev's original
verdict. `independent-review.json` binds the review to the raw task/core diff hashes and preserves
its scope limits. Gate usage was 22,480 input tokens and 118 output tokens. The prepared smaller
review/verification calls were not submitted again to seek different model scores.

## Limits

The Blender exercise covers one static representative car and the documented export profile, not
all modeling tools, cars, compressed mesh extensions or animation. JPEG, indexed/interlaced PNG
and skinned importing remain outside the profile. Static display geometry does not establish
original game shading fidelity. The source hashes compare with this task's starting state, not
clean Git HEAD; earlier local recovery/model work remains in the checkout.
