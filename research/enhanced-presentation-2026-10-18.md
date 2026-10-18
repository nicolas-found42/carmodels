# Optional Enhanced presentation in the Recovered inspector (issue #22)

Scope: an opt-in **Enhanced** presentation for `dealership/recovered.html`, with **Original** as the
default and unchanged; environment reflections, neutral tone mapping and a glossy clearcoat on
textured parts when Enhanced is on; a persistent label saying Enhanced is not the original game's
look; the GLB download unchanged. Static, offline, no build step, three.js at its pinned version.
The ticket's Ford Racing 2 target is `ford-racing-2/GRAN_TORINO` and `ford-racing-2/FORD_GT`.

Code: `dealership/enhanced-presentation.mjs` (mode state machine, finish policy, label),
`dealership/materials.mjs` (`createMaterial(..., {presentation})` picks the clearcoat-capable
material class), `dealership/recovered.html` (control, label, wiring), and
`tools/test_enhanced_presentation.mjs` (the check registered as `test_enhanced_presentation`).

## Vendored helpers: none added

| Dependency | Version | Source | Licence |
| --- | --- | --- | --- |
| three.js (`dealership/vendor/three.module.js`, `three.core.js`, `OrbitControls.js`) | r182, unchanged pin | committed in this repository, shipped from three.js r182 | MIT, © 2010–2025 three.js authors (header in `three.module.js`) |
| Offline studio environment | in-repo, `dealership/gt4-studio.mjs` | this repository (procedural room + `PMREMGenerator.fromScene`) | same repository licence |

The developer note on issue #22 asked for `RoomEnvironment` to be vendored. That is superseded: the
repository already builds an asset-free studio environment for the dealership (`dealership/gt4-studio.mjs`,
merged in `cba5f9c6`), and Enhanced reuses that path. **No three.js example helper, HDRI or other
asset was vendored**, and the vendored three.js pin is untouched. `RoomEnvironment` is an
`examples/jsm` module that this repository does not ship; importing it would have added a vendored
file for no benefit.

Consequence of reuse: the ACES Filmic tone mapper the studio sets is replaced by the neutral mapper
(see below). Everything else — the environment texture, `scene.environment`, the exposure, the
restore-on-disable semantics — comes from the existing studio.

## Chosen values (a judgement call) and why

| Value | Chosen | Why |
| --- | --- | --- |
| Tone mapping | `THREE.NeutralToneMapping` (Khronos PBR Neutral) | The merged pipeline research recommends it as the default: it reproduces a product's base colour and hue under PBR and avoids HDR highlight artefacts, which keeps recovered liveries close to their source colours. ACES Filmic (the studio's own default) is more filmic/stylised. Sources: `research/visual-fidelity-modern-pipeline-options.md` §2, and the Khronos PBR Neutral release it cites (https://www.khronos.org/news/press/khronos-pbr-neutral-tone-mapper-released-for-true-to-life-color-rendering-of-3d-products). |
| Exposure | `1.0` | three.js's default and the value the studio already sets. PBR Neutral is already colour-faithful, so no exposure compensation is claimed or applied. |
| Environment intensity | `0.8` | The studio's own value; unchanged so Enhanced differs from Original only by what the ticket asks for. The existing hemisphere and directional lights stay on in both modes, so the base lighting is shared. |
| `roughness` | `0.35` | Glossy but broad. The paint is a 128–512 px PS2 texture stretched over large panels; a near-mirror value (the three.js car example's `0.5` body roughness is paired with `metalness 1`) would show the procedural room's boxes instead of paint. |
| `metalness` | `0` | The recovered albedo stays the diffuse pigment. `metalness 1` would discard the recovered texture colour and misrepresent the source; the lacquer is carried by the clearcoat layer instead. |
| `clearcoat` | `1` | Full-coverage lacquer over the textured surface. |
| `clearcoatRoughness` | `0.06` | Soft reflections rather than a mirror: the environment is a small procedural room, so the three.js car example's `0.03` reads as a hard artificial highlight. |

Scope of the finish: **textured, non-blended coverage only** (`baseColorTexture` present and
`alphaMode !== 'BLEND'`), and only where the material carries no authored clearcoat. Untextured
header-coloured parts and blended windows keep their recovered finish; `MASK` cutouts count as opaque
coverage; a corrected GT4 surface with its own `KHR_materials_clearcoat` finish is left alone. Tyres
are textured, so they are glossier than they should be until parts can be told apart — the gap issue
#22 records, unchanged by scope decisions here.

## What the implementation guarantees

- `createPresentation(renderer, scene)` snapshots the renderer/scene state at construction and starts
  in `original`. Selecting Original when already Original touches nothing.
- Selecting Original after Enhanced restores the snapshot exactly: tone mapping, exposure,
  `scene.environment` (null) and `environmentIntensity` (1). The displayed materials are rebuilt
  through the unchanged `createMaterial`/`applyMaterial`/`applyPaintMaterial` path, and the finish is
  a no-op outside Enhanced.
- The finish runs after every paint update because the paint pipeline rewrites roughness and metalness
  from recovered factors and clears clearcoat. Setting `clearcoat` across zero bumps the material
  version, which is what makes three.js rebuild the shader program; no extra `needsUpdate` is used.
- A material that already carries an authored `KHR_materials_clearcoat` finish keeps it, so a
  corrected GT4 surface is not overwritten by the uniform gloss; Enhanced adds a coating where the
  recovered material has none.
- Presentation is display-only. The download link is the inspector's existing paint re-export of the
  loaded source buffer and the mode never touches that buffer.

## Measurements

Harness: this machine, Chrome (headless, `--enable-unsafe-swiftshader --use-angle=swiftshader`),
viewport 1280×900, `python3 -m http.server` over `dealership/`. Cars
`ford-racing-2/GRAN_TORINO` and `ford-racing-2/FORD_GT`, geometry record "Assembly 0 — standard
wheels, headlights off", default camera. The stage canvas is 2400×1020 device pixels at
`devicePixelRatio 2`.

WebGL buffer identity was read with `gl.readPixels` on `#stage canvas` inside a
`requestAnimationFrame` callback (SHA-256 over the RGBA bytes), which is the rendering itself rather
than a resampled screenshot:

| Car | Mode | Buffer SHA-256 (first 16) | Non-zero bytes |
| --- | --- | --- | --- |
| GRAN_TORINO | Original, fresh load | `5ac32201c3adcf24` | 9,790,902 |
| GRAN_TORINO | Enhanced | `3b0a3771d60e49a7` | 9,791,789 |
| GRAN_TORINO | Original after Enhanced | `5ac32201c3adcf24` | 9,790,902 |
| FORD_GT | Original, fresh load | `d5783f9d1ec67c2a` | — |
| FORD_GT | Enhanced | `28fcd9433f35051d` | — |

Pre-change control: the same two URLs were served from a pre-change tree
(`git archive origin/main dealership | tar -x -C /tmp/rec22-base`) on a second port, so the
comparison is against the code as it is on `main`, not against a branch-internal baseline. Both cars
produced the **identical** buffer hash in Original mode (`5ac32201c3adcf24…` for GRAN_TORINO,
`d5783f9d1ec67c2a…` for FORD_GT), stable across repeated fresh loads on both pages. So Original does
not merely look like today: the rendered buffer is byte-identical, and Original reproduces it again
after a round trip through Enhanced.

Visual statistics from PNG captures of `#stage` (element screenshots, 2400×1020), Original → Enhanced,
same page and camera:

| Car | Mean luminance (0–255) | Pixels above 0.72 luminance | Mean channel delta | Pixels changed by >8/255 |
| --- | --- | --- | --- | --- |
| GRAN_TORINO | 33.97 → 35.86 | 10,670 → 23,165 | 3.04/255 | 8.5% |
| FORD_GT | 32.45 → 33.84 | 24,916 → 35,485 | 3.07/255 | 8.3% |

Round trip at screenshot level: Original before any mode change and Original after
Enhanced → Original had the same PNG bytes (SHA-256 `4c13e207020e2aa7…`), consistent with the
buffer-level result above.

Real-environment check (temporary probe page, not committed): with the actual studio (no stub),
Enhanced sets `renderer.toneMapping = 7 (NeutralToneMapping)`, `toneMappingExposure = 1`,
`scene.environment` = a render-target `Texture` with `CubeUVReflectionMapping` and image size
1536×2048 (the PMREM atlas of the studio's 512 environment), `scene.environmentIntensity = 0.8`;
Original restores NoToneMapping, exposure 1, `environment = null`, intensity 1.

Download: the `#download` link is a `blob:` URL produced by the existing paint export. Its SHA-256 is
**identical in both modes** — `997c27260dc1c9c400e0152817203b35f687ab23095a5c3354a1ac309d615863`,
1,224,868 bytes for GRAN_TORINO (source file `d01fc358428c244c…`, 1,225,208 bytes) — and its glTF
materials keep `roughnessFactor 1`, `metallicFactor 0` and no `KHR_materials_clearcoat` extension.

Network: 32 requests after the car loaded in Original mode, 32 after switching to Enhanced, **0 added
by the switch**, every URL on `127.0.0.1:8231` (page, modules, `models.json`, GLB, blob URLs). No
external host appears in either mode. The check also asserts statically that the presentation module,
the reused studio and the material path contain no `fetch`, `XMLHttpRequest` or URL.

## What this does not establish

- Enhanced is a chosen presentation, not the game's shading. It does not reproduce the original
  VU1/GS pass-4/5 reflection and specular arithmetic described in `research/packet-continuation.md`
  and `research/visual-fidelity-ground-truth-and-game-shading.md` §2; the environment is a
  procedural room, so reflection content is invented by construction.
- The gloss is uniform over textured opaque coverage, so tyres are glossier than the original; part
  naming (paint/trim/tyre separation) is out of scope.
- The measurements cover the two Ford Racing 2 cars above at one geometry record, one camera and one
  software rasteriser. Other cars, records, cameras and GPUs were not sampled.
- Originating breakpoints or per-pixel match against the game's own render is not attempted here;
  the claim is only "Original is unchanged; Enhanced is a labelled departure".
- Screenshots are not committed: `research/evidence/` is allowlist-only and no verifier writes or
  reads images for this change.
