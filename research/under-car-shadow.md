# Under-car shadow quad in the Recovered inspector

Ticket [#23](https://github.com/nicolas-found42/carmodels/issues/23). Target: `dealership/recovered.html`
(the Recovered inspector reached from the dealership sidebar), Ford Racing 2 only. Receipt:
[`research/evidence/under-car-shadow/table.json`](evidence/under-car-shadow/table.json), produced by
`python3 tools/verify_under_car_shadow.py`.

## What the corpus carries

- All 35 Ford Racing 2 recovered source GLBs carry exactly one under-car shadow record: 33 named
  `UNDER_SHADOW`, one `EX_UNDER_SHADOW2` (EX) and one `GT90_UNDER_SHADOW` (GT90). The name shape is the
  only selector (`isRecoveredUnderShadow` in `dealership/materials.mjs`); no other committed GLB under
  `dealership/public/` carries a material matching it.
- The record is one primitive with POSITION, NORMAL and TEXCOORD_0. GRAN_TORINO and GT90 carry 14 vertices
  / 8 triangles; the other 33 cars carry 37–38 vertices / 24 triangles. In all 35 the primitive is a flat
  plane at Y = 0 (every vertex shares that height, every normal points up along Y) that lies inside the car's
  own footprint — the ground-contact plane the game would draw the shadow with.
- Its texture is 64x64 RGBA8 — the same PNG the per-car manifest already publishes as that texture's
  display PNG (`model_texture_display`, sha256-pinned in `games/ford-racing-2/recovered/cars/<car>/manifest.json`,
  equal to the embedded bytes in all 35). Every texel's RGB is **white**; only the alpha varies (0–254, all
  even), i.e. the exporter's display-alpha conversion `min(255, 2a)` of a stored 0–127 alpha. The
  "alpha/128" scale the recovered glass path already uses is this same stored alpha.
- The exported glTF material records **no blend state**: `alphaMode` is absent (the glTF `OPAQUE` default)
  and no `baseColorFactor` is written. As authored the quad therefore draws as a hard opaque square in its
  own (white) colour, and alpha is ignored.
- Exported scene membership: in all 35 cars the record is reachable only from scene 0, the record layout
  (`doc.scenes[0]`, the per-record leaves). The default scene the viewer opens (`doc.scene`, the low-speed
  tree) does not reference it, and neither does any other exported tree. So before this change the quad was
  not drawn in the default view at all — the "hidden by the preset" of the ticket's three possibilities.
- The repo's captured draws cover one car (COBRA) and contain no draw for this quad, so the game's blend
  function for it, its colour source and its depth behaviour are **not captured**.

### Per-car table

`in the default scene` compares the record against the records reachable from the exported default scene
(`doc.scene`, `Tree 0 — Low-speed wheels, lights off` in all 35). `scenes` lists every exported scene whose
node tree reaches the record. `alpha` is the stored alpha range the display PNG doubles.

| car | material | record | vertices | triangles | in the default scene | scenes | alpha (stored) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 49_COUPE | UNDER_SHADOW | 37 | 37 | 24 | no | 0 | 0–127 |
| 49_COUPE_MOVIE | UNDER_SHADOW | 33 | 37 | 24 | no | 0 | 0–127 |
| COBRA | UNDER_SHADOW | 48 | 37 | 24 | no | 0 | 0–127 |
| CROWN_VICTORIA | UNDER_SHADOW | 66 | 37 | 24 | no | 0 | 0–127 |
| EX | EX_UNDER_SHADOW2 | 60 | 37 | 24 | no | 0 | 0–126 |
| EXPLORER | UNDER_SHADOW | 48 | 37 | 24 | no | 0 | 0–127 |
| F100_1956 | UNDER_SHADOW | 40 | 37 | 24 | no | 0 | 0–127 |
| F100_1965 | UNDER_SHADOW | 34 | 38 | 24 | no | 0 | 0–127 |
| F150 | UNDER_SHADOW | 50 | 37 | 24 | no | 0 | 0–127 |
| F150_2004 | UNDER_SHADOW | 44 | 37 | 24 | no | 0 | 0–127 |
| F350 | UNDER_SHADOW | 47 | 37 | 24 | no | 0 | 0–127 |
| FOCUS_FR200 | UNDER_SHADOW | 64 | 37 | 24 | no | 0 | 0–127 |
| FOCUS_SVT | UNDER_SHADOW | 56 | 37 | 24 | no | 0 | 0–127 |
| FOCUS_WRC | UNDER_SHADOW | 64 | 37 | 24 | no | 0 | 0–127 |
| FORD_GT | UNDER_SHADOW | 72 | 37 | 24 | no | 0 | 0–127 |
| FORTYNINE | UNDER_SHADOW | 39 | 37 | 24 | no | 0 | 0–127 |
| FR500 | UNDER_SHADOW | 52 | 37 | 24 | no | 0 | 0–127 |
| GRAN_TORINO | UNDER_SHADOW | 41 | 14 | 8 | no | 0 | 0–127 |
| GT90 | GT90_UNDER_SHADOW | 71 | 14 | 8 | no | 0 | 0–127 |
| INDIGO | UNDER_SHADOW | 94 | 37 | 24 | no | 0 | 0–127 |
| LIGHTNING_SVT | UNDER_SHADOW | 56 | 37 | 24 | no | 0 | 0–127 |
| MACH1_AGENT | UNDER_SHADOW | 27 | 37 | 24 | no | 0 | 0–127 |
| MACH1_SIXTY | UNDER_SHADOW | 27 | 37 | 24 | no | 0 | 0–127 |
| MACH3 | UNDER_SHADOW | 58 | 37 | 24 | no | 0 | 0–127 |
| MUSTANG_68 | UNDER_SHADOW | 58 | 37 | 24 | no | 0 | 0–127 |
| MUSTANG_68B | UNDER_SHADOW | 59 | 37 | 24 | no | 0 | 0–127 |
| MUSTANG_CONCEPT | UNDER_SHADOW | 48 | 37 | 24 | no | 0 | 0–127 |
| POWERSTROKE | UNDER_SHADOW | 39 | 37 | 24 | no | 0 | 0–127 |
| TAURUS_STOCK_A | UNDER_SHADOW | 51 | 37 | 24 | no | 0 | 0–127 |
| TAURUS_STOCK_B | UNDER_SHADOW | 51 | 37 | 24 | no | 0 | 0–127 |
| TAURUS_STOCK_C | UNDER_SHADOW | 51 | 37 | 24 | no | 0 | 0–127 |
| TAURUS_STOCK_D | UNDER_SHADOW | 51 | 37 | 24 | no | 0 | 0–127 |
| THUNDERBIRD | UNDER_SHADOW | 36 | 37 | 24 | no | 0 | 0–127 |
| THUNDERBIRD_2002 | UNDER_SHADOW | 65 | 37 | 24 | no | 0 | 0–127 |
| THUNDERBIRD_MOVIE | UNDER_SHADOW | 65 | 37 | 24 | no | 0 | 0–127 |

Counts: 35 cars, 35 shadow records, 0 in the default scene, 35 in the record layout only, 35 flat planes at
Y = 0 with upright normals, 35 textures with the doubled display alpha, 35 all-white textures, 35 embedded
PNGs equal to their manifest display PNG.

## The seam: load-time reconstruction, not bake-time retention

1. The inspector renders the committed, sha256-pinned recovered GLB (`dealership/public/ford-racing-2/<car>.glb`,
   pinned in each car's manifest and in `dealership/public/models.json`). The repo never replaces a recovered
   original, so the record cannot be exported into a tree at bake time without changing those bytes.
2. The only bake seam, `tools/bake_models.py`, feeds the *derived* dealership catalogue, and its output is
   per-vertex tone bytes with no texture map (`texture_tone`). A retained shadow plane there could not carry
   the texture alpha this ticket asks for, and retaining it would silently change 35 `triangleCount` rows of
   `dealership/public/dealership/cars.json` for a view the ticket does not target.
3. Load-time reconstruction is therefore the smallest seam that can satisfy the acceptance criteria, and it
   keeps the recovered corpus byte-identical.

`dealership/editable-glb.mjs` (the derived dealership viewer) keeps omitting the quad: that path is a separate
derived view, its bake and catalogue agree on the omission, and this ticket's target is the inspector.

## What changed

- `dealership/materials.mjs`: `isRecoveredUnderShadow(source)` (name-shape selector) and
  `applyRecoveredUnderShadow(material, source)`, called at the end of `applyMaterial`. For that material the
  quad is drawn with `transparent = true` and `depthWrite = false` (the dev note's depth/sort concern) and the
  texture's own alpha is the blend factor; `opacity` stays 1 so the blend factor is the alpha channel alone,
  `alphaTest` stays 0 so the graded coverage is kept, and the map stays bound. Every other material is
  untouched, including the glass/Header-colour path from the untextured-parts ticket.
- `dealership/recovered.html`: `meshNode` is split into `meshFor(primitive)` + `meshNode(node)` (no behaviour
  change) so one primitive can be rebuilt on its own; `underCarShadowPrimitive(doc)` selects that record,
  `sourceSceneRecords(doc, scene)` reports which records a view draws, and `underCarShadowNote(...)` prints
  the honesty label. When the exported default scene does not reference the record, the inspector rebuilds
  that one original primitive as an overlay of the default view (`userData.overlay`), taking part in the same
  visibility switch as the group it belongs to but never used for camera framing. The status line records the
  record number, the material, the triangle count, whether the source default scene draws it, the reason when
  it does not, and that the drawn blend is a candidate because the blend state is not captured.
- `dealership/enhanced-presentation.mjs`: `isTexturedOpaque` no longer claims the under-car shadow, so the
  optional Enhanced presentation (issue #22) does not gloss the quad. **The shadow quad is not affected by
  Enhanced mode.** Enhanced deliberately departs from the recovered look by adding a clearcoat to *textured
  opaque coverage*; the shadow's texture is an alpha coverage decal and not an opaque surface, so a clearcoat
  would replace its soft patch with a reflective sheet. Its candidate blend (transparency, no depth write, the
  texture alpha at the alpha/128 scale, opacity 1, no cutout) is applied by `applyMaterial` in both modes, and
  `presentation.finish` leaves its roughness, metalness and clearcoat exactly as the recovered material set
  them. What Enhanced does change for the quad is shared with every surface: the scene environment and the
  neutral tone mapping. `tools/test_under_car_shadow.mjs` builds the shadow material through both presentation
  modes and asserts the blend and the unglossed finish, and `tools/test_enhanced_presentation.mjs` covers the
  predicate and the real Gran Torino materials.
- `tools/verify_under_car_shadow.py`: the new self-checking verifier behind the table above.
- `tools/test_under_car_shadow.mjs`: the offline viewer-side test (authored facts, candidate blend, every
  other material unchanged, selector behaviour).
- `tools/test_viewer_scenes.mjs`: keeps exercising `showRecord` through the shipped page, now including the
  shadow label and the overlay/framing guard.
- `tools/run_checks.py` (+ `tools/test_run_checks.py`, `.gitignore`): registers the two new checks; the
  receipt-writing verifier is audited as an exclusive check.

## Additive/derived work unchanged

Nothing regenerates the corpus: the recovered GLBs, the dealership GLBs, `cars.json`, the catalogs and every
other model file are byte-identical to `main`. The only `dealership` files this change touches are
`recovered.html`, `materials.mjs` and one predicate in `enhanced-presentation.mjs`; the rest of the
difference against `main` is the verifier, the two tests, the receipt and this note.

## Evidence

### 1. Static table and its tamper controls

```
python3 tools/verify_under_car_shadow.py          # VERIFY OK, receipt reproduces byte for byte
python3 tools/verify_under_car_shadow.py --write  # only to establish a reviewed new receipt
```

Controls (mutated copies of the corpus, each rejected; the receipt records the reason):

| mutation | rejected by |
| --- | --- |
| shadow record added to the default scene tree | receipt differs from the clean derivation |
| second under-car shadow record added | derivation error: more than one under-car shadow record |
| shadow material renamed away from its shape | derivation error: no under-car shadow material in this car |
| shadow record loses its UVs | derivation error: the record needs its own UVs to sample the texture alpha |
| two cars carry each other's GLB | derivation error: GLB differs from its manifest pin |
| one GLB pin replaced | derivation error: GLB differs from its manifest pin |

### 2. Offline viewer-side test

```
node tools/test_under_car_shadow.mjs
PASS test_under_car_shadow: 35 cars, 35 shadow records outside the exported default scene, 35 rebuilt at
load, 665 other textured/detail materials and 80 Header-colour parts unchanged, candidate alpha blend kept
in both presentation modes
```

It pins, per car: the material is authored opaque with no colour factor, the texture is 64x64 with a doubled
all-white-alpha gradient, the UVs sample more than one alpha value (so the patch cannot be a flat square),
and `applyMaterial` yields `transparent`, `depthWrite === false`, `NormalBlending`, `opacity === 1`,
`alphaTest === 0` with the shadow texture still bound — while every other material keeps its authored
transparency, depth write, cutout, blend mode, stored colour, stored alpha and texture binding.

### 3. Render before/after (headless Chrome, SwiftShader; local, not part of `tools/check.sh`)

Method (session scripts under `.scratch/research/ticket-23/`, not committed): serve the worktree with a
static server; capture with
`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu
--enable-unsafe-swiftshader --use-angle=swiftshader --hide-scrollbars --window-size=1200,800
--virtual-time-budget=30000 --screenshot=<out.png> "http://127.0.0.1:<port>/recovered.html?game=ford-racing-2&car=<id>"`;
a capture is accepted when more than 5,000 pixels below y = 400 differ from the page background `#151a22`
(the shipped page renders in runs and the screenshot is retried until it does). The "before" state is the
same tree with `recovered.html`, `materials.mjs` and `enhanced-presentation.mjs` taken from `origin/main`
(which now carries the Enhanced presentation control), so both states share one layout. The record view
drives the shipped Geometry control over CDP (`Page.captureScreenshot` after setting `#record` and
dispatching `change`). Measurement: the count of pixels whose largest per-channel difference exceeds one
level, and the peak channel difference, over 1200x800. Re-measured after the rebase: the added presentation
row moves the stage, so framing — and therefore these counts — differ from the pre-rebase run.

| car | view | before | after | pixels changed | peak channel delta |
| --- | --- | --- | --- | --- | --- |
| GRAN_TORINO | default (low-speed tree) | no shadow record drawn | the record is drawn and blended | 2,415 | 233 |
| GT90 | default (low-speed tree) | no shadow record drawn | the record is drawn and blended | 797 | 229 |
| GRAN_TORINO | assembly part 41 (the record) | hard-edged opaque white quad | soft graded patch, no hard square | 1,031 | 234 |
| GT90 | assembly part 71 (the record) | hard-edged opaque white quad | soft graded patch, no hard square | 17 | 228 |

Readings:

- The default view now draws the original record (open the Geometry list's default entry; the changed region
  is the ground plane under the car, below the rockers and between the wheels). The car body occludes most of
  that plane from the inspector's elevated default camera, so the visible change is the part of the plane that
  is not covered by the body. Both cars change, so the acceptance evidence covers at least two cars.
- The record view is the clearest before/after for GRAN_TORINO: with the same selection, the quad changes from
  a hard opaque rectangle in its own colour to a soft graded patch — the acceptance criterion "texture alpha
  as a blend (alpha/128) and no hard opaque square".
- The record view is a weak view for most cars, and the measurement says so: GT90 changes on 17 pixels only,
  and COBRA (part 48), 49_COUPE (37), TAURUS_STOCK_A (51), MUSTANG_68 (58), F150 (50) and FORD_GT (72) change
  on **none** — in those records the quad lies behind the record's own glass and body geometry from the framed
  camera, so the same opaque-versus-blended change is simply not visible there. Record-view evidence is
  therefore quoted for one car, and the two-car acceptance evidence is the default view's.
- The quad's stored colour is white in every car, so what the candidate blend adds where the plane is visible
  over the inspector's dark studio background is **lighter**, not darker. The retail screenshots show it
  darkening the road, which needs the game's own blend function; see the open item below. The inspector label
  states the candidate blend and the white stored colour.
- The alternative reading — attenuating what is behind by `1 - alpha` (the multiply treatment the official
  three.js car example uses for its baked ground shadow, cited in
  [`visual-fidelity-modern-pipeline-options.md`](visual-fidelity-modern-pipeline-options.md)) — was implemented
  first and measured the same way (in the earlier, smaller page header, before the presentation control moved
  the stage): it changed at most 612 of 960,000 pixels by **one** level in the default view and nothing at all
  in the record view, because the inspector draws no ground to darken and the quad is drawn against the page's
  dark background. It left the ticket's own visible outcome unreachable, so the shipped reading is the alpha
  blend of the quad's stored colour: same blend factor (the texture alpha at the alpha/128 scale), but
  observable in the inspector. Both readings are candidates; the game's is not captured.

## What this check does not establish

- The verifier is a static derivation: it establishes the record, its scene membership and its texture alpha,
  not the game's blend function, colour source or depth behaviour for this quad. No capture covers the quad.
- The candidate blend is a reading of the texture alpha at the recovered alpha/128 scale; it is labelled
  candidate everywhere the inspector prints it.
- The render figures are one headless software-rendered frame per state on this machine, not a game-render
  comparison and not part of `tools/check.sh`.
- Whether the game draws this quad at all in the low-speed state (the record layout is not a runtime state) is
  not established; the exported trees record states, not the runtime draw list.

## Open items (also listed in `research/README.md`)

- The game's blend function, colour source and depth behaviour for the under-car shadow quad are not captured;
  the inspector's candidate blend therefore lightens the studio background instead of reproducing the darker
  ground-contact appearance, and the true appearance stays open.
- Which runtime state (if any) draws the quad in game is unresolved; the record sits outside every exported
  state tree.
