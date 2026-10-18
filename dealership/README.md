# Ford Racing 2 — Car Model Explorer

Local three.js viewers for Ford Racing 2, Gran Turismo, Redline, Midnight Club 3 Remix and Gran Turismo 4. Two independent showcases: `recovered.html` displays the recovered source models; `dealership.html` displays an editable dealership edition. `index.html` redirects to the dealership. Ford Racing 2 retains the 35-car reference corpus; the other games have separate catalogs and documented decoding limits.

## Run

From the `carmodels/` directory:

```sh
python3 tools/build_dealership.py
python3 -m http.server 8080 --directory dealership
```

Open the dealership at <http://localhost:8080/dealership.html>, or the source-model showcase at <http://localhost:8080/recovered.html>. The source showcase renders the recovered original geometry: pick a car, a tree/record and a texture variant, and download the complete GLB. The download contains every geometry preset and texture variant; it opens with its stored default scene and base materials. Inspector choices, wireframe and row-flip settings affect the preview and are not baked into the file. The 35 GLBs are already generated under `public/ford-racing-2/`; each retains independent geometry records and five translated tree candidates. Empty source trees (including tree 4 in the current corpus) are retained in the GLBs but disabled and labelled “no geometry” in the Geometry chooser. The inspector starts with tree zero and includes car, tree/record, texture, wireframe and row-flip controls.

The source inspector reads the shared `public/models.json` catalog, built from hash-verified per-game indexes by `tools/build_model_catalog.py`. Model IDs combine game and car code.

**Presentation** offers `Original` (the default, which renders exactly as before) and `Enhanced`: environment reflections, neutral tone mapping and a glossy clearcoat on textured parts, built from the same in-repo asset-free studio environment the dealership uses — no HDRI, no vendored example helper and no network request. Enhanced is a deliberate departure from the game's look, carries a visible label saying so, and never changes the downloaded model. See [the presentation research](../research/enhanced-presentation-2026-10-18.md).

The dealership has its own editing inputs:

- `dealership/dealership/models/<CAR>.glb`: independent regular GLB files for each converted car. Edit geometry here.
- `dealership/dealership/catalog.json`: editable dealership names, metadata and icon colour samples.
- `dealership/dealership.mjs`: dealership rendering and material styling.
- `dealership/public/dealership/cars.json`: compiled display data; rebuild this from the editing inputs.
- `dealership/dealership/origins.json`: historical provenance of the initial fork, not a current-model hash constraint.

`python3 tools/build_dealership.py` reads only the dealership catalog and working GLBs, and writes only compiled dealership data. It preserves model/catalog edits. Source recovery and export commands write `games/ford-racing-2/`, `games/ford-racing-2/recovered/` and `dealership/public/ford-racing-2/`; they do not update dealership copies. Shared vendor library code is not shared model storage.

The working GLBs were explicitly forked once with `python3 tools/seed_dealership.py`. Running that command again preserves an existing dealership without reading source assets or replacing edits. New source recovery output is not silently pulled into the dealership. The old `tools/build_showcase.py` command remains a compatibility entry point for the safe dealership build.

The baker supports static node translation, quaternion rotation, affine matrices, nonuniform scale and 8/16/32-bit triangle indices. The tested Blender export settings and supported texture profile are in [the dealership editing guide](dealership/README.md). This is a static display importer.

The viewer uses three.js r182 — the module, core and `OrbitControls` are **shipped in this repository** under `dealership/vendor/`, so it has no build step or runtime CDN dependency. A local HTTP server is required for browser ES-module loading (`file://` will not load the modules).

To regenerate original-data exports from the provisioned local input bundle:

```sh
python3 tools/recover_original_assets.py
python3 tools/export_geometry_candidates.py
python3 tools/build_model_catalog.py
python3 tools/validate_geometry_candidates.py
```

The original-coordinate mapping reproduces all 1,837 nonempty geometry records' bounds. Triangle strip, normals, UVs and texture assignments are candidate interpretations. Sixteen scenes retain all alternative wheel/light states and add explicit low-speed/moving-wheel presets derived from the original visibility routines. The low-speed first tree is the default; live animation and executed LOD remain separate checks. Numeric texture selectors are available in the inspector and as KHR_materials_variants. Original material header words and lane recipes are preserved in primitive metadata. The exporter keeps textured surfaces opaque and double-sided, and applies stored header alpha to untextured surfaces; so glass, reflections and GS shading do not yet match the game. Separate PTG menu icons/liveries, 136 newly discovered MATRIX thumbnails and 94 additional mip levels are decoded into evidence folders. This GLB export uses level-zero model textures. The main recovery report distinguishes source decoding from original draw fidelity.

Failed car loads clear the previous preview and download link, disable geometry/material controls, and offer **Retry this car**. Switching cars cancels obsolete requests; a stalled geometry request fails after 15 seconds. Missing or undecodable embedded textures are reported as load failures. Textures default to linear min/mag filtering without mip levels, matching the bounded 106-draw capture described in `../research/packet-continuation.md`; filtering for every game state is not established. **Sharp pixels** restores nearest filtering for texel inspection. **Game shading (candidate)** is off by default; while it is on, the honesty label reports what it did, and source Headers with an established pass-4 assignment take the decoded paraboloid environment lookup of the game's VU1 handler. It is a candidate: the eye is the inspector camera, the reflection matrix is view-derived, and the sampled texture is the retained preview of the pass-4 view render target, so game-state shading is not reproduced. Any car or part without that assignment renders exactly as before. The derived Header table and the stand-ins are recorded in [`../research/game-shading-inspector.md`](../research/game-shading-inspector.md) and [ADR 0004](../docs/adr/0004-inspector-pass4-shading-stand-ins.md). The dealership car and filter buttons support keyboard activation with Enter and Space.

## What the dealership shows

- Manifest data: name, year, group, in-game BHP, mass, top speed, handling ratings, liveries, sound bank.
- Illustration-family filters from a recorded batched Jev classification, with the two low-confidence cases resolved from their model names (Explorer Sport Trac → SUV, FR500 → coupe family).
- Car-specific 3D display models baked from the dealership’s editable GLBs. The initial copies came from the recovered first-tree low-speed assembly. Driver helmets and baked shadow planes are omitted. Identical vertices are welded; geometry is not decimated or stretched by handling ratings.
- Ford Racing 2: up to three meshes per car, no runtime texture or full GLB loading. Desaturated vertex tones approximate dark surface details; icon colour provides an illustrative body tint. Other converted games load their independent working GLBs and embedded textures, checking the compiled source hash. Native-only entries offer the native download with an explicit unavailable-preview message. These previews do not establish original game shading.

The dealership viewport has its own space beside the performance panel on wide screens,
with details below it on smaller screens. **Side**, **Front**, **Top**, and **Reset view**
frame the complete illustration. **Auto rotate** can be turned off persistently; reduced
motion preferences start it off, and dragging also stops it. Wheels stay stationary.
These native controls support keyboard activation. Drag/zoom still require a pointer.

Search and filters show the result count and identify the retained preview. A zero-result
search has an explanation and **Clear search and filters** restores the list. Group choices
combine with OR, style choices with OR, and the two categories combine with AND.
Name/year/code search accepts words in either order and ignores punctuation between words,
for example `mustang 1968` or `1968 mustang`. Multiword terms match word prefixes; a single
literal term also retains substring lookup. It does not correct spelling or infer undecoded names.
Game and variant selectors disable unavailable choices. Changing either selector clears
incompatible variant/group/style choices and announces which were cleared; available restrictions
and the name query are preserved. Body-style filtering excludes entries whose style is unknown.
**More filters** contains catalog groups, body styles and optional natural-language filtering,
with the active chip count visible when collapsed. The sidebar can scroll at short heights.
Vehicle data failures offer **Retry loading cars**. HTTP failures, empty/duplicate records,
invalid values, and a 15-second header/body timeout are reported before building the list.
Missing library files and direct `file://` use have separate startup guidance.

For optional natural-language filtering, serve with `python3 tools/serve_library.py` and open
the printed local address. The form accepts Enter and explains provider routing before submission:
exact game/variant phrases work locally; other wording needs the existing configured TypeSafe
provider. Manual filters and text edits cancel obsolete requests and clear their pending status.
The UI allows 35 seconds, including the provider's 30-second request budget and local processing;
timeouts and provider/server failures retain the current filters. Canceling in the browser does
not guarantee cancellation of server-side provider work; the server's existing concurrency limit
may temporarily return a busy response. The ordinary static server supports name search/selectors
and shows guidance if the optional API is requested.

Icon samples now come only from the decoded, clipped 165×98 reference icon pixels,
checked against each manifest's SHA-256. Opaque saturated pixels are preferred, with a
neutral sample for icons without eligible saturated pixels. Headers and padded tile edges
are excluded. The data records the source/pixel hashes, dimensions and selection mode.
Samples use display RGB in the UI and are converted from sRGB for three.js lighting.
This remains a colour heuristic, not segmentation or a measurement of the vehicle's paint.
The recorded styles are illustration families: `concept` and `racecar` are not physical
body-style measurements. Handling ratings are displayed as metadata and no longer change the mesh. The source coordinate/triangle/normal/UV interpretations remain candidates; dealership models do not establish full game-render fidelity.

Rebuild dealership display data with `python3 tools/build_dealership.py`. Recovery pins are checked during the explicit initial fork; edited dealership GLBs are accepted on their own current content, without requiring equality with source models.

Offline regressions run with `node tools/test_dealership.mjs`, `python3 tools/test_build_dealership.py`, `python3 tools/test_build_showcase.py` and `python3 tools/test_bake_models.py`, all included in `tools/check.sh`. Dealership tests edit a copied GLB and catalog, rebuild twice, and require the edit to survive while source hashes stay unchanged. Source-bake checks validate the recovery-to-copy producer separately, without constraining edited dealership models to their source geometry.
The executed teardown and browser evidence are in
[`../research/silhouettes-teardown-2026-10-08.md`](../research/silhouettes-teardown-2026-10-08.md).

**The dealership models are independent editable display editions.** The recovered.html inspector provides the full exported GLBs, original-coordinate candidate scenes and decoded embedded model textures. Both retain the recovery’s fidelity limits. The earlier replacement and browser checks are recorded in [`../research/silhouette-models-2026-10-08.md`](../research/silhouette-models-2026-10-08.md).

The dealership separation and verification are recorded in [`../research/dealership-split-2026-10-08.md`](../research/dealership-split-2026-10-08.md).

## Research

- `../research/visualization-libraries.md` — primary-source tooling research and citations.
- `../research/format-notes.md` — verified file structure, experiments, confidence, and remaining reverse-engineering tasks.
- `../research/original-recovery.md` — current synthesis, validation receipts, Jev experiments and research leads.

## Preview colours

Both showcases offer recovered factory colour variants where the loaded GLB
contains them, plus a custom colour picker and a `#RRGGBB` field for any 3D preview.
A factory selection clears the custom tint; **Reset colour** restores the stored
default materials. Changing cars clears the custom tint. Colour controls disable
while loading, after failures, and for native packages without a 3D preview.

Custom colours multiply the opaque materials in linear RGB after converting the
picker's sRGB colour. They retain texture detail and vertex shading, but can also
tint trim or wheels when native paint regions are unavailable. Transparent glass
keeps its stored colour. Compact dealership models have a separate body material,
so their known wheel/detail materials are excluded. This is a preview adjustment;
it does not establish native paint semantics or modify catalogs, GLBs, downloads
or saved settings.
