# Branch integration, 2026-10-09

The integration merges the independent editable dealership branch `fbb055b` and optional-pass source join branch `8bf9b66`, preserves the game-folder organization and corrected material assignments, and removes the legacy procedural gallery. The default entry redirects to the dealership. The source inspector uses a hash-verified multi-game catalog with game-qualified model IDs and encoded model URLs.

Source inputs and canonical manifests live under `ford-racing-2/`; exported source GLBs live under `dealership/public/ford-racing-2/`. Editable dealership models remain independent under `dealership/dealership/models/`. The compatibility showcase builder rebuilds only the dealership; `tools/build_model_catalog.py` rebuilds only the source catalog.

## Executed evidence

[Evidence folder](evidence/main-integration-2026-10-09/):

- `checks-1` and `checks-2` preserve the failed integration runs: stale protected-path/catalog references, then a stale source-index assertion. These were corrected; they are not claimed as passes.
- `checks-3/results.json` records 32 passes, no skips, exit zero. It includes original asset integrity and tamper controls, material/texture ownership across 35 GLBs, multi-game identity/path controls, load recovery, editable dealership preservation/freshness, actual Blender 4.5.14 import/edit/export, static executable verifiers and captured optional-pass controls. Complete command logs are retained alongside the manifest.
- `browser.json` records the default redirect, 35 dealership cars, independent editable GLB download path, separate original source GLB download path and no uncaught browser errors. `dealership.png` records the rendered updated app.
- `export-preservation.json` compares the rebuilt source GLBs to material-fix commit `89ffd39`: all 35 binary chunks (geometry and embedded texture payloads) are unchanged. All source samplers are linear min/mag without mipmaps.
- `evidence/continuation/khronos-validation.json` records 35 source GLBs, zero errors and zero warnings, plus malformed-input rejection.

These checks establish the bounded behavior above, not complete original game shading, live animation or fidelity for uncaptured game states. Issue 21 covers 100 aligned optional-pass draws, all from COBRA, within six loaded models; it does not establish optional-pass assignment for the other cars. Linear filtering is informed by 106 captured draws; the inspector retains that candidate qualification and its reversible Sharp pixels control.

Independent Standards and Spec review against main `1062c24` found no blocking findings. The Standards review noted nonblocking duplication of catalog fixtures between recovery-input and dedicated catalog tests. Bounded Jev integration reviews use raw file diffs against the completed dealership branch remapped to the new paths; full-main comparisons were reviewed separately by those independent reviewers.
