# Gran Turismo shading: why the cars look covered in shadows

Research note, 2026-10-11. Scope: the dark, shadowed look of the Gran Turismo (PS1, GT1) cars in the dealership
viewer, its causes and the fixes. Repo code is cited as `file:line`; external claims link to the source that owns
them. Measurements come from the scripts and JSON in `evidence/gran-turismo-shading-2026-10-11/`. Run each Python
script with `python3 -I <script> <repo root> …`. The second pass (section 5 onward) rebuilt every GT car under
candidate fixes and rendered them in the real viewer; its inputs, outputs and Jev receipts are under
`evidence/gran-turismo-shading-2026-10-11/experiments/`. Items the evidence does not settle are marked **open**.

## Summary

1. **Main cause: most triangles face backwards.** The exporter's index swap inverts winding that was already
   correct for the reflected basis. In 727 of 728 GT cars (344 day, 344 night, 40 arcade), less than half of the
   body area is wound counter-clockwise (the glTF front side) in agreement with the triangles' own stored normals.
   The median is 14%. The materials are double-sided, so three.js negates the normal of every back-facing
   fragment. The outside of the car is therefore lit as though it faced inward. A roof gets the hemisphere's
   near-black ground colour, and the key light brightens the inside.
2. **Second cause: some faces' stored corner normals sum to a direction in the face plane.** A median of 17% of
   each day car's body area has a corner-normal sum within about 9° of the face plane. Individual corner normals
   can cancel in that sum, so this measures faces whose stored normals give no consistent facing direction, not
   necessarily corners that each lie in the plane. Those faces get no reliable winding or Lambert term from their
   normals, so they stay patchy after the winding is fixed. The _ld7vr door panel is the visible example.
3. **The fix is in the exporter, and it is measured.** Orient each face from its stored normals. Where those
   normals lie in the face plane, replace them with the geometric face normal. In the unchanged viewer this
   roughly doubles the mean on-screen luma of the four test cars (39→89, 50→106, 25→48, 40→82) and removes the
   remaining patches (section 5).
4. **Not the cause:** the black flat faces. They are 34% of the surface area but at most 0.23% of visible car
   pixels in the default view. Texture brightness and modulation scale are not the cause either (section 3).
5. **Lighting is optional polish, not a fix.** Once the geometry is repaired, an environment map with neutral tone
   mapping adds about 20–30% luma, and an unlit mode reproduces the PS1 raw-texture look. Neither one corrects
   inverted geometry on its own.

## 1. Winding disagrees with the stored normals (main cause)

**What the exporter does.** `tools/gt_model.py:73-78` reflects native Z for both vertices and normals. It then
writes each face as `[base, base+2, base+1]` (and `[base, base+3, base+2]` for quads). The comment there says
"Z reflection reverses winding" (`tools/gt_model.py:278-282`). Every body material is `doubleSided: true`
(`tools/gt_model.py:264-266`). The node transforms are all identity: 5,096 nodes, no matrix, unit scale, no
rotation.

**What the data shows.** For each body triangle, the scripts compare the geometric CCW normal with the sum of the
triangle's stored corner normals, weighted by area. Wheels are excluded, because the exporter derives their
normals from the emitted winding (`tools/gt_model.py:228-241`). `glb_measure.py` reads the 344 day GLBs the
dealership loads. `experiments/winding_variants.py` rebuilds all 728 native pairs from `games/gran-turismo/cars/`.

| Body area whose CCW front agrees with the stored normal | cars | min | p10 | median | max | cars < 0.5 | cars ≥ 0.99 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| As exported (`current`) | 728 | 0.000 | 0.055 | 0.144 | 0.517 | 727 | 0 |
| Swap removed (`no_swap`) | 728 | 0.356 | 0.632 | 0.842 | 1.000 | 1 | 16 |
| Per-triangle from stored normals (`per_triangle`) | 728 | 0.810 | 0.975 | 1.000 | 1.000 | 0 | 642 |

The variant medians are the same for day, night and arcade (current 0.144/0.144/0.148, no_swap 0.843/0.843/0.828;
`experiments/winding_variants.json`). The night and arcade variants share the defect.

Across LOD0 of all 344 day cars, a median of 86% of faces have stored normals that point away from the car
centroid (`gt_measure.json`). The normals mostly point the right way. It is the winding that is inverted.

The first pass of this note estimated the drop-swap result as 1 − agreement, which gave 86%. The direct rebuild
measures 84.2%. The gap comes from the in-plane normals in section 2, which neither policy orients reliably. A
Jev `jev_compare` of the two passages split between `same_fact` 0.49 and `contradicts` 0.46 (`review`). The
direct measurement is used here.

**Why that darkens the car.**
- glTF: with a positive-determinant transform, "front-facing triangles use the counterclockwise order". For
  `doubleSided: true`, "the normal vectors of the back-facing triangles are negated".
  https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc (lines 2138-2140,
  2729-2731 at commit `b43260ee1291`)
- three.js r182, as vendored in the repo (`dealership/vendor/three.core.js` `REVISION = '182'`), does exactly
  that. `normal_fragment_begin` sets `faceDirection = gl_FrontFacing ? 1.0 : -1.0` and, under `DOUBLE_SIDED`,
  multiplies `normal *= faceDirection` (`dealership/vendor/three.module.js:438`). The loader honours the GLB's
  material side (`dealership/materials.mjs:25`).
- The hemisphere term is `mix(groundColor, skyColor, 0.5*dot(normal, up) + 0.5)`
  (`dealership/vendor/three.module.js:386`), and the dealership's ground colour is `0x1a1c20`
  (`dealership/dealership.html:487`). Once the roof normal is flipped downward, the roof takes the near-black
  ground colour. Directional light uses the same flipped normal, so the key light (`dealership/dealership.html:488-490`)
  falls mostly on the inner side.

**Wheels are not affected.** The wheel CCW fronts point toward the wheel centroid on all 724 wheeled cars. Their
normals are computed from that same winding, so the double-sided flip still yields outward normals. They render
correctly.

**Why the game never showed this.** The PS1 GPU does no culling. Facing is decided in software from the sign of
GTE `NCLIP`, which "indicates whether the polygon coordinates are arranged clockwise or anticlockwise (ie.
whether the front side or backside is visible)" (https://psx-spx.consoledev.net/geometrytransformationenginegte/).
Textured car faces are drawn raw (section 3), so the stored normals never darken them in the game. The community
GTExplorer renderer does not cull either: when a triangle's screen-space area is negative it swaps two vertices
and draws it anyway ([`gtcar_render.py` L84-L88](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/utils/gtcar_render.py#L84-L88)). It shades with `abs(dot(n, light))`, a two-sided
term that hides inverted normals ([L294-L299](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/utils/gtcar_render.py#L294-L299)).

## 2. Corner-normal sums that lie in the face plane (second cause)

On _ld7vr, 25% of body area has a corner-normal sum whose cosine with the face normal is about 0. Across the 344
day cars (`experiments/normal_quality.json`, threshold |cos| < 0.15):

- Per-car share of body area: median 16.8%, p90 39.5%, max 44.3%. 289 of 344 cars exceed 5%.
- By material: 43% of black flat area, 66% of other flat colours, 6.1% of textured area and 1.1% of Gouraud
  area. Black flat faces make up 75% of all in-plane area.

"In-plane area" in this note means this summed-corner-normal measure (`experiments/normal_quality.py`). The
viewer shades interpolated corner normals, so it is a proxy for faces without a consistent stored direction; the
rendered effect is measured separately in section 5.

These normals do not affect the game, because the textured faces are drawn raw. In a lit viewer, though, they
give an arbitrary Lambert term, and the winding chosen from them is arbitrary. With `per_triangle`, the _ld7vr door
panel still renders blue and dark (`experiments/contact_sheet.png`, bottom row).

**Repair** (`experiments/repaired_variant.py`). Per face, take the Newell normal of the polygon. If the stored
corner-normal sum has |cos| ≥ 0.15 with it, keep the stored normals and wind the face to agree with them.
Otherwise, write the geometric normal to every corner, oriented away from the LOD centroid. Zero-area faces keep
their stored normals, because the viewer rejects zero normals (`GLB normal is zero`, found when the first
repaired build of _ccrvn failed to load). After the repair, in-plane area is at most 1.3% per car, with a median of
0% (`experiments/normal_quality_repaired.json`). Winding/normal disagreement is at most 0.12% of body area.

The centroid orientation is a heuristic for a non-convex shape. It covers the faces whose normals carry no
direction, but **open:** a mesh-connectivity orientation (weld positions, then propagate consistent winding)
would not depend on the centroid.

## 3. Rejected: texture modulation scale

- The PS1 polygon command byte has bit 24 "Texture Color Mode (0=Shaded/Modulated, 1=Raw)". In modulated mode,
  "8bit values of 80h are brightest (values 81h..FFh are 'brighter than bright' …about twice as bright)".
  https://psx-spx.consoledev.net/graphicsprocessingunitgpu/
- Textured GT faces store colour `FFFFFF` (59,761 of 59,785 LOD0 textured faces; `gt_measure.json`). In
  modulated mode that would double brightness.
- But the command bytes are `0x25`/`0x2D` (29,495 and 30,116 faces), plus semi-transparent `0x27`/`0x2F` (52 and
  98). All of these have bit 0 set, which means raw. Only 24 faces use `0x2C`, which is modulated
  (`gt_types.json`). So the hardware ignores the colour, and the export's 1× texels (`tools/gt_model.py:146-161`,
  5-bit channels `<<3`) match the static packets. **Open:** whether the game rewrites these bits or colours at
  run time.
- The vertex colours on the four Gouraud materials (0.9% of area) are converted sRGB→linear
  (`tools/gt_model.py:163-164`, `:274-275`). That matches glTF, where `COLOR_0` "acts as an additional linear
  multiplier to base color" (Specification.adoc line 2605). There is no double-gamma error.

## 4. Flat black faces: not part of the look

Flat untextured faces with colour `000000` cover 34.2% of GT body surface area (`glb_measure.json`). The test
removed every one of those primitives and rendered again (`per_triangle_noblack`). In the default viewer camera
this changed 0.23%, 0.23%, 0.00% and 0.12% of car pixels on the four test cars. The faces are almost entirely
hidden behind textured surfaces or underneath the car. The dark NSX roof is texture, not black faces: it stays
dark when they are removed. That matches the real car, which has a black roof.

GTExplorer's renderer skips any untextured face whose colour is 0 (`if fc == 0: return`, [`gtcar_render.py` L316-L318](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/utils/gtcar_render.py#L316-L318)). It
is a community choice, not evidence of game behaviour. Jev's `jev_noul` without context put "GT1 draws flat
000000 polygons as visible black geometry" at 0.28 (uncertain). **Open:** in-game appearance. It does not affect
the shadowed look.

## 5. Render experiments

**Harness.** `experiments/variant_server.py` serves the repo's `dealership/` read-only. It swaps in GT day GLBs
from a variant directory and rewrites the matching `cars.json` hashes, so the viewer's integrity check
(`dealership/editable-glb.mjs:89-90`) still applies. It patches `dealership.html` only in memory: it selects
`?car=`, turns off auto-rotation, optionally applies a lighting variant, and exposes a capture hook.
`experiments/capture.mjs` drives headless Chromium (Playwright 1.63, SwiftShader WebGL) at 1400×900. It renders
at the viewer's reset camera and reads statistics only from pixels the car covers. The car mask comes from a
second render of the car alone over magenta. Luma uses Rec. 709 weights, and "dark" means luma < 40 of 255.

**Lighting variants.** `base` is the unchanged viewer. `env` adds a PMREM environment from a simple lit-room
scene at intensity 0.9, `NeutralToneMapping` at exposure 1.0, and a hemisphere ground colour of `0x55565a`. `unlit`
replaces each car material with `MeshBasicMaterial` (same map, colour, side and alpha), which is how raw-mode
PS1 polygons look.

| Car | current/base | no_swap/base | per_triangle/base | **repaired/base** | repaired/env | per_triangle/unlit |
| --- | --- | --- | --- | --- | --- | --- |
| _hnsxn mean luma (dark share) | 38.9 (57%) | 89.5 (34%) | 89.5 (34%) | **89.5 (34%)** | 110.0 (32%) | 101.8 (39%) |
| _nr33n | 50.5 (44%) | 105.4 (25%) | 105.6 (25%) | **105.6 (25%)** | 135.5 (24%) | 127.1 (25%) |
| _ccrvn | 24.7 (91%) | 48.5 (55%) | 47.6 (57%) | **48.2 (56%)** | 52.4 (57%) | 47.3 (71%) |
| _ld7vr | 40.4 (53%) | 78.1 (22%) | 78.7 (22%) | **81.9 (20%)** | 106.2 (23%) | 97.6 (19%) |

Source: `experiments/matrix.log` and `experiments/captures/*.json`. Log rows 29-30 (_ccrvn repaired, 0 car
pixels) are the failed first load described in section 2 and are superseded by rows 37-38; the capture script now
rejects a failed load, a zero-pixel capture or an unsaved result. The images are in
`experiments/contact_sheet.png` and `experiments/contact_sheet_repaired.png`.

What the renders show:
- **The geometry fix removes the shadowed look on all four cars**, with no lighting change. Before it, the bodies
  are blue-black silhouettes lit from inside. After it, the NSX and R33 are silver and the Corvette is blue with
  white stripes.
- **The normal repair is what clears the remaining patches.** On _ld7vr it brightens the door panel from blue to
  silver. The other three cars barely change (±0.6 luma).
- **The remaining darkness on _ccrvn is its texture.** Unlit gives the same mean (47.3 against 48.2). Jev's
  `jev_noul` with this evidence put that proposition at 0.85.
- **Lighting is a choice of look.** `env` brightens by about 20–30% on three cars and 9% on _ccrvn. `unlit`
  gives flat, PS1-like texels. Jev's `jev_noul` put "environment lighting is necessary once the winding is
  repaired" at 0.11.

## Implementation update (2026-10-13)

The measured per-face repair is now implemented in `tools/gt_model.py` as
`body_face_frame`: stored normals orient ordinary faces; near-perpendicular or
cancelling sums use a geometric normal oriented away from the LOD centroid.
Zero-area faces keep their stored normals. The canonical public exports and working
copies use day sources and colour set 0. Texture pixels, UVs, materials and viewer
lighting are retained. The corpus regression independently measures winding/normal
agreement from emitted GLB accessors, with a deliberately reversed-winding control.

The centroid fallback remains a heuristic for non-convex shapes; connectivity-based
orientation and original PS1 rendering fidelity remain open. The archived experiment
scripts below describe the pre-repair exporter and are historical reproductions.

## Recommended fixes, in order

1. **Repair the exporter's winding and normals** (`tools/gt_model.py:278-282`). Port the per-face logic from
   `experiments/repaired_variant.py`: wind each face to agree with its stored normals, and give faces with
   in-plane normals their geometric normal. Keep `doubleSided`, because PS1 culling is software. Add a test that
   fails on the current exporter, for example the area agreement on a fixture car being ≥ 0.99. Regenerate
   `dealership/public/gran-turismo` (`tools/export_gt_models.py`), then upgrade the unedited dealership copies with
   `tools/import_gt_dealership.py`, whose `upgrade_unedited` path preserves edited cars. Catalog hashes will
   change, so rebuild the dealership data and run the GT freshness checks in `tools/check.sh`. Verify with
   `glb_measure.py`, expecting median ≥ 0.99 and no car below 0.95, and with the capture harness above.
   Jev's `jev_decide` over the measured candidates selected this fix with probability 0.91. Drop-swap got 0.08:
   its requirement check "leaves no faces shaded by arbitrary in-plane normals" came back contradicted.
2. **Optional: a native/unlit display mode** for GT (`dealership/materials.mjs`). It could be a viewer toggle that
   uses `MeshBasicMaterial`, or exporter-written `KHR_materials_unlit`, which the extension defines as
   "color = <baseColorTerm>", independent of lighting
   (https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_unlit/README.md). The
   editable loader currently rejects primitives with extensions (`dealership/editable-glb.mjs:37`), so a viewer
   toggle is the smaller change.
3. **Optional: showroom lighting for all games** (`dealership/dealership.html:468-500`). Add an environment map
   (`RoomEnvironment` or a PMREM scene), `NeutralToneMapping` (present in r182, `three.core.js:479`) and a
   brighter ground colour. Tune it after fix 1 on a reference car from each game, so it does not hide geometry
   defects.

## How Jev was used, and what it did not decide

- `jev_screen` passed all four fetched source excerpts: glTF spec, KHR_materials_unlit, psx-spx GPU and GTE
  (injection ≤ 0.02).
- `jev_verify` checked 12 claims (spec facts, corpus measurements and render numbers) against the excerpts and
  JSON. All 12 were verified with `auto`. The two render claims scored 0.98 and 0.94. The first attempt used
  plain-string evidence items and a decide call with four requirements, which the schema rejects. Those calls
  returned input-validation errors and were resubmitted in the documented `{id, text}` and ≤ 3-requirement form
  (`*.r2.json`).
- `jev_compare` flagged the earlier 86% drop-swap figure as `review` (section 1), and `jev_decide` chose fix 1
  (0.91). `jev_noul` gave the three probabilities quoted in sections 4 and 5. Every measurement itself comes from
  executable scripts, not from Jev. Receipts are in `experiments/jev/`.
- **Within the application:** the dealership already routes free-text library filtering through a server-side Jev
  judgment (`tools/serve_library.py`, `tools/library_filter.py`). For shading, no runtime judgment was found that
  would help. Winding, normals and lighting are deterministic geometry and rendering. Jev reads text, not
  pixels, so it cannot judge whether a render "looks shadowed" without a vision transcript. Such a transcript
  would only be a weaker signal than the pixel statistics above.

## Open items

- Mesh-connectivity orientation for faces whose stored normals carry no direction, instead of the centroid
  heuristic (section 2).
- Runtime rewrites of polygon colour or raw bits in GT1 (would change section 3).
- In-game appearance of the black flat faces (section 4). It does not affect the shadowed look.
- The renders cover four day cars from the reset camera. The night and arcade variants were measured
  geometrically but not rendered.
- No GT1 emulator reference frame has been compared, so game-render fidelity remains open.
