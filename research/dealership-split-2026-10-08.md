# Dealership and source-model showcase separation

The editable gallery is now called **Dealership**. It lives at `viewer/dealership.html`,
with the recovered source-model showcase at `viewer/recovered.html`. `viewer/index.html`
redirects to the dealership. Each page links to the other and downloads its own GLB.

## Model ownership and editing

`viewer/dealership/models/` contains 35 independent regular GLB files, initially copied
from recovered assets. They are neither symbolic links nor hard links.
`viewer/dealership/catalog.json` owns dealership names, metadata and presentation choices.
`viewer/dealership.mjs` owns dealership rendering/material styling.
`viewer/dealership/origins.json` records historical seed provenance, not a requirement
for an edited model to keep matching the original.

Run `python3 tools/build_dealership.py` after editing a working model or catalog entry.
This reads only the dealership inputs and atomically replaces its compiled
`viewer/public/dealership/cars.json`. The compatibility command `tools/build_showcase.py`
delegates to the same build. Neither command reseeds the dealership or exports recovery
assets. An explicit `tools/seed_dealership.py` invocation preserves an existing dealership
before reading any source data. The original metadata reader now lives in
`tools/showcase_metadata.py` and is used for initial seeding and source metadata checks.

The original source corpus remains under `reference/`, `recovered/` and
`viewer/public/recovered/`. The source-model page retains its recovery presets, texture
variants and inspection behaviour; its changes here are labels and navigation only.

## Verification

- All 24 steps in `tools/check.sh` passed without skips on the final code. Actual output:
  `evidence/dealership-split-2026-10-08/check.log`.
- All 827 source/recovery files match their SHA-256 values captured at the start of this
  split. Previously modified, unrelated working files also remain unchanged relative to
  that start. Receipt: `evidence/dealership-split-2026-10-08/preservation.json`.
- The 35 editable models have separate file identities from their source GLBs. Initial
  catalog metadata matches the previous gallery, excluding its generated geometry.
- In an isolated temporary fixture, a Gran Torino working GLB was lengthened by 20% and
  renamed in the catalog. Compiled geometry reflected that change, repeated builds were
  identical, the edited GLB hash survived, a seed attempt preserved the existing fork,
  and all source GLB hashes remained unchanged. Source-reading helpers were made to throw
  during the build to expose an accidental reseed dependency. The production Gran Torino
  copy was not lengthened by this test.
- A static replacement fixture without recovery extras/material names exercised 16-bit
  indices, quaternion rotation, reflected nonuniform scale, normalized inverse-transpose
  normals and an equivalent column-major affine matrix. A singular transform was rejected.
- Tamper controls reject model symlinks, hard links, duplicate/path-traversal catalog codes,
  generated geometry in the editable catalog and output paths inside protected inputs.
  Test source: `tools/test_build_dealership.py`; output: `edit-isolation.log`.
- The dealership renderer checks compact geometry, floor placement, disposal, malformed
  meshes and transport failures. A model with removed wheel geometry is accepted, so
  editable dealership geometry need not preserve the original four-wheel metadata.
  Original source geometry comparisons remain in `tools/test_bake_models.py`.
- The actual browser showed the Dealership title and independent model download path;
  navigation reached Source models and its original download path, then returned. The
  Ford GT displayed successfully. At a 390-pixel viewport the document width remained
  390 pixels and the new download link fit its wrapped controls. The viewport override
  was reset. Preview: `evidence/dealership-split-2026-10-08/dealership.jpg`.

## Judgment and limits

Jev reviewed a 49,354-character raw core patch and actual check/preservation evidence.
It verified the combined 24-check/827-source-file claim with confidence 0.82. The patch
gate escalated because its test-gap judgment had confidence 0.30; safe-to-apply was 0.58,
composite 0.77725. This is not automatic patch approval. The host's subsequent review
checked the ownership boundary, explicit seed behaviour, edited-model rebuild fixture,
tamper controls and browser paths against the code and receipts. No contradicted claim
was returned. Gate receipt: `evidence/dealership-split-2026-10-08/jev-gate.json`.

The core gate input is `gate.diff`; the broader task diff is `task.diff`. Generated model
copies and compiled JSON were checked by their file identities, source hashes, catalog
comparison and executable tests rather than sending binary/generated geometry to the judge.

The source hashes compare with this split's starting state, not the repository's clean
HEAD: earlier recovery work remains in the checkout. Static display support does not
establish original game shader fidelity or animation support. Keep normal attributes and
the existing embedded texture encoding when editing these GLBs. The compact display
continues to use illustrative vertex tones/icon tint and omits driver helmets and shadow
planes. This work introduces independent editing inputs, not an in-browser modeling editor.
