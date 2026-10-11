# Redline conversion and library import

The 2026-10-09 import processed all 129 extracted car configurations. It published
128 static GLBs (19 base-game configurations and 109 add-ons), plus 128 separate,
editable dealership copies. Both catalogs now contain 891 entries. The native
extraction in `redline/cars` remains unchanged.

## Conversion

`tools/redline_mesh.py` reads the native big-endian MDL arrays and indexed triangle
corners, with bounds and finite-value checks. `tools/redline_texture.py` converts
native TXR/DXT3 and conventional image resources into embedded PNGs.
`tools/redline_model.py` assembles body, optional interior, wheels, custom brakes
and graphical add-ons from each car configuration. Wheel placement uses the
native position, tilt, side rotation, width and radius. The neutral preview lowers
each wheel/brake center by half its configured suspension travel; omitted travel
defaults to zero as in the native cleared wheel allocation. Source UV values remain
unchanged; texture-row mapping follows the native upload and GLB loader evidence.
Zero normals use geometric face normals; unusable zero-area triangles are omitted.

The resulting static export contains 598,013 triangles and 169,074,436 GLB bytes.
862 corner normals were derived, and 8,513 unusable triangles were omitted.
Native arrays and source files are retained separately. Every consumed resource
is pinned by size and SHA-256. Package-local resources precede base resources;
ambiguous resources are not borrowed from unrelated plug-ins.

## Rebuilding

Run from the repository root. The system Python has the local Pillow installation
required by the supplied TIFF/PSD images; PICT conversion uses macOS `sips`.

```sh
/usr/bin/python3 tools/export_redline_models.py
/usr/bin/python3 tools/export_redline_models.py --check
python3 tools/build_model_catalog.py
/usr/bin/python3 tools/import_redline_dealership.py --upgrade-unedited
python3 tools/build_dealership.py
python3 tools/build_dealership.py --check
tools/check.sh --evidence-dir .scratch/redline-conversion/final-checks
```

Publication stages and validates the full model directory before replacement.
The importer appends independent editable copies, validates source metadata, and
preserves existing catalog entries. Repeating the import added zero models.
The upgrade flag refreshes only copies whose bytes still match their recorded
source hash; edited models remain untouched. The source viewer and dealership
provide Redline base/add-on filters and visible
per-car conversion limits. Dealership Front/Side controls respect the native
Redline forward-Z axis.

## Exceptions and limits

- Invisivette uses empty native meshes. Its configuration is recorded in the export
  index as non-drawable; no invented model is published.
- Pimped Diablo references `countach_wheel.mdl`, absent from all supplied packages.
  Its available body/interior are retained with missing-wheel warnings.
- An optional APC interior contains non-finite native UV values and is skipped.
- Six texture references are unavailable in the owning/base resources. One has
  conflicting variants in other plug-ins. Neutral materials and warnings preserve
  that uncertainty instead of guessing a texture.
- Wipeout 2 declares zero wheel scales; collapsed wheels are omitted with warnings.
- Runtime steering, spin, animation, paint/reflection/secondary shader composition,
  graphical add-on visibility masks and global plug-in load precedence are not
  reproduced or established. Raw two-slice 3D textures use the native first-slice
  2D fallback. Game-render fidelity remains unverified.

## Verification and judgments

The 48-check suite passed; eight checks covering the affected assembly, exporter,
importer, baker, viewer, freshness and Blender paths passed again after the stance
correction. The published 487 wheel centers and 40 custom-brake centers match
the native preview formula. The exporter regenerated the entire published inventory byte-for-byte with
`--check`. Preservation checks found 8,256 pre-existing native/model files
unchanged, all 763 previous catalog/origin entries unchanged, and 128 new regular
editable copies with bytes equal to their source models and separate inodes.
The stance regression failed with raw configured centers, then passed after the
native half-travel subtraction (Mustang Y 0.35 to 0.25). Both native wheel render
paths use this subtraction. Horizontal position and wheel dimensions retain their
native values; no universal track-width adjustment is invented. Blender 4.5.14 imported and exported four-, three- and six-wheel assemblies,
preserved their triangle counts, propagated a 10% geometry stretch, and rebuilt
schema-2 dealership data without modifying the 256 production Redline GLBs.

All 2,297 source image files (2,159 unique byte payloads) decoded in the full corpus
experiment. Independent comparisons covered native DXT3 and conventional image
pixels. The final PICT optimization was separately checked against all 140 unique
PICT inputs; the original full-corpus receipt identifies its earlier producer.

Jev screened documentation and qualified native-format evidence, reviewed changes,
verified corpus claims and informed the bounded decision to retain cars with
missing original resources and disclose their omissions. Low-confidence reviews
received independent evidence review; original model scores were preserved.
An earlier extension-only PNG warning was withdrawn after content decoding showed
that the affected `.png` file is a valid JPEG.

The server-side semantic filter composes TypeSafe Choice, Noul and Score judgments
for available game/variant filters. It sends bounded queries and filter options,
keeps credentials server-side, and leaves filters unchanged on review/failure.
Sixty labeled experiments compared wording and candidate state. The final
20-case run selected the expected choice in 16 cases; its five accepted answers
were all correct (25% acceptance coverage, a small observed sample). The 40-case
wording comparison used 44,338 input/6,054 output tokens, cost $0.001862196 and
3.523 seconds of wall time with concurrency four. The final 20-case run used
24,799 input/3,026 output tokens, cost $0.001041558 and 2.175 seconds. These costs
exclude MCP documentation/review calls, whose billed cost was not returned.
Four real HTTP requests accepted Redline/base and Gran Turismo/night and returned
review for the add-on request and unsupported all-wheels query; measured latency
was 0.279–0.901 seconds. No acceptance thresholds were relaxed.

Evidence: `.scratch/redline-conversion/export-summary-final.json`, `export-suspension-check.log`,
`preservation-final.json`, `roundtrip-corrected.log`, `final-checks/results.json`,
`stance-final-checks/results.json`,
`live-api-experiments.json`, and the component receipts under `mesh`, `texture`
and `integration`. Browser evidence is in `research/evidence/redline-library`.
Scratch inputs, credentials and native installers are not published by this note.
