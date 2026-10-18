# Ground surface and soft contact shadow in Enhanced mode (issue #25)

Scope: the **Enhanced** presentation of `dealership/recovered.html` gains a ground surface under the
car and a soft contact shadow on it, placed from the visible geometry so it follows the selected car
and the geometry choice; **Original** stays the default and is unchanged. Static, offline, no build
step, three.js at its pinned revision. In: ground surface and contact shadow, Enhanced only. Out:
ambient occlusion, further lights, any change to Original, real-time shadow maps, and the game's own
blob quad (issue #23 owns that path).

Code: `dealership/contact-shadow.mjs` (the ground, the shadow plane and the passes),
`dealership/enhanced-presentation.mjs` (`follow`/`prepare` and the label),
`dealership/recovered.html` (wiring), `tools/test_enhanced_presentation.mjs` (the check registered as
`test_enhanced_presentation`).

## The technique, and why this one

The issue points at three.js's contact-shadow example (`examples/webgl_shadow_contact.html`), and
that is what this is: an orthographic camera under the car's floor renders the car with a
`MeshDepthMaterial` override into a render target, the result is blurred by a two-pass 9-sample
Gaussian, and the blurred field is painted on a plane that sits on the ground. It is a **flat,
non-physical fake**: it cannot self-shadow, it does not respond to the light directions, and nothing
but the car occludes it.

Two alternatives are ruled out by the issue itself: the game's own blob quad is the
original-materials option (#23, a different ticket), and shadow maps are "costlier and unnecessary
for a single object". Nothing new is vendored: `dealership/contact-shadow.mjs` imports only
`./vendor/three.module.js`, and the test asserts that. The two blur shaders are the 9 weights of
three.js's `HorizontalBlurShader`/`VerticalBlurShader` (MIT, three.js authors) inlined as GLSL built
from one weight table, so the pin gains no file; the attribution is in the module.

Deviations from the example, each deliberate:

| Example | Here | Why |
| --- | --- | --- |
| `depthTest = false`, `depthWrite = false` on the depth material | both left on | the depth test is what makes the *nearest* surface win each texel; without it the last-drawn triangle wins, which on a car shell is draw-order dependent |
| `side` left at the material default | `DoubleSide` everywhere | the recovered corpus has no proven winding (the viewer is double-sided for the same reason), and a one-sided depth pass would leave holes in the field |
| the plane is placed exactly at the camera's far plane | the camera sits under the floor and the ground and shadow group are hidden for the depth pass | explicit, and it also keeps a 24× ground out of the field |
| depth and blur every frame | once per placement (`dirty`) | the cars are static in this viewer, so the field only changes when the car or the geometry choice does; a still frame costs one boolean |
| the uv comes from a rotated `PlaneGeometry` plus a `scale.y = -1` flip | the quad's uv is written as the shadow camera's own mapping of it (0.5 + x, 0.5 + z over a unit quad) | no axis flip has to be guessed; the mapping is checked by a probe (below) |
| the example's ACES/white look | the ground is a `MeshStandardMaterial` under the page's existing lights and the Enhanced environment | the ground belongs to the labelled Enhanced presentation, not to a second look |

The one three.js internal it depends on is the `MeshDepthMaterial` fragment line it rewrites
(`gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );`, worth a black core instead of grey
where a surface meets the floor). The check asserts the vendored source still contains that exact
line, and calls the rewrite, so a three.js bump fails the check instead of silently painting a solid
plane.

## Chosen values (a judgement call) and why

| Value | Chosen | Why |
| --- | --- | --- |
| Resolution | 1024², two targets | Square and independent of the canvas and the car; the blur step is expressed in uv, so the cost is fixed rather than car-dependent. 1024 keeps the field's own texels smaller than the visible penumbra. |
| `blur` | 2.5 (three.js's unit: one tap is this over 256 of the plane) | On the measured footprint this puts the penumbra at roughly a third of a small object's silhouette (probe below), which reads as a soft edge rather than an outline. |
| `darkness` | 1.6 | Saturates the alpha where a surface meets the floor, so the contact is dark, and lets it fall off with height above the floor. Blurring what the depth pass produces is what makes the edge soft. |
| `opacity` | 0.85 | Keeps the darkest part of the ground slightly alive rather than pure black, so the ground still reads as a surface. |
| `margin` | 0.15 | The shadow plane extends a little past the car's footprint so the blur is not clipped at the plane's own edge. |
| `groundSpan` | 24 × the shadow plane | A large enough floor that its far edge is out of frame at the viewer's fitted camera, so the ground reads as a floor and not as a plate. |
| Ground colour | `#1e2735`, lit by the page's existing lights | A floor only a little lighter than the `#151a22` backdrop; it is a prop, not recovered data. |
| `groundDrop` / `cameraDrop` | 0.002 / 0.01 of the plane's side | The ground sits a hair under the car's lowest point, so the tyres touch the contact plane rather than the floor and the two coplanar surfaces never fight over depth. The depth camera sits a hair under the ground, looking up: the ground and the shadow are the only things between them, and the pass hides the whole group so neither reaches the field. |
| `minimumFootprint` | 0.1 | A degenerate record still gets a usable plane instead of a zero-scale one. |

## What the implementation guarantees

- **Original builds nothing.** No ground, no shadow plane, no render target, and no renderer call at
  all: `createContactShadow` builds on the first Enhanced selection, `setEnabled(scene, false)`
  takes the group out of the scene, and `update()` returns before it touches the renderer.
- **Original renders the pre-change frame.** Measured below: the read-back buffer is byte-identical
  to the same page served from the commit this branch is based on, for both cars and both geometry
  records.
- **Enhanced follows the car.** `follow(box)` is the only input; the page passes the visible
  geometry record's bounding box from `showRecord()`, the same box the camera is fitted to. The
  ground is centred on the box and sits at its lowest point; the shadow plane spans the footprint
  plus its margin; the depth camera covers exactly that plane. An empty box (an empty source tree) or
  a cleared viewer hides both.
- **Enhanced draws once per placement.** `prepare()` is the page's per-frame hook and returns
  immediately unless the placement changed; the test asserts that the frame sequence is one depth
  pass plus two two-pass blurs, that the plane samples the target the last pass writes, and that a
  second frame does no work.
- **The passes leave the page alone.** `scene.overrideMaterial`, `scene.background` and the renderer's
  clear alpha are restored before the page's own render, and the render target is unbound.
- **The label says so.** Enhanced's label now names the ground surface and the contact shadow as part
  of "not the original game's look"; it is hidden in Original as before.

## Measurements

Harness: this machine, Chrome (headless, `--enable-unsafe-swiftshader --use-angle=swiftshader`),
viewport 1280×900, `python3 -m http.server` over each tree, `Page.captureScreenshot` for the PNGs and
`gl.readPixels` **on the page's own canvas** for every number below (the rendering itself, not a
resampled screenshot). Two trees are served at once:

- **head** — this branch.
- **base** — `4a8d2f65` (the commit this branch is based on) extracted to `/tmp/rec25-base`, i.e. the
  page as shipped without this change. It gives both controls: Original must match it byte for byte,
  and Enhanced-minus-base-Enhanced is the ground and the shadow alone, with the material change
  (issue #22) cancelled out.

Cars `ford-racing-2/GRAN_TORINO` and `ford-racing-2/FORD_GT`, at the default geometry record
("Assembly 0 — standard wheels, headlights off", GLB scene 6) and at "Candidate 3 — all states"
(scene 4). Canvas 1280×650.

### Original is byte-for-byte the pre-change frame

SHA-256 over the read-back RGBA buffer, head against base, same car and record, fresh load each time:

| Car | Record | Head | Base | Identical |
| --- | --- | --- | --- | --- |
| GRAN_TORINO | scene 6 | `deda20dee3f95522` | `deda20dee3f95522` | yes |
| GRAN_TORINO | scene 4 | `8d6b52dc4a8b7274` | `8d6b52dc4a8b7274` | yes |
| FORD_GT | scene 6 | `d968ec5d61c203cd` | `d968ec5d61c203cd` | yes |
| FORD_GT | scene 4 | `c97779e1ce211f07` | `c97779e1ce211f07` | yes |

### The ground and the shadow, measured against the base tree's Enhanced frame

"Shadow" is a pixel at least 8/255 darker than the same pixel in the base frame (where the base shows
the backdrop through the ground), "lit ground" is a pixel more than 8/255 brighter. Screen
coordinates, y down.

| Car | Record | Car silhouette box | Lit ground (px, mean luminance) | Shadow (px, box, centre) | Shadow mean luminance | Ground luminance the shadow removes |
| --- | --- | --- | --- | --- | --- | --- |
| GRAN_TORINO | scene 6 | 329,218–887,511 | 715,391, 77.87 | 17,787, 338,330–880,559, centre 583,467 | 10.50 | 86.5% |
| GRAN_TORINO | scene 4 | 326,207–904,516 | 704,940, 77.92 | 16,511, 338,334–895,563, centre 582,471 | 10.24 | 86.9% |
| FORD_GT | scene 6 | 331,220–890,509 | 710,918, 77.91 | 14,467, 340,339–877,545, centre 562,476 | 10.27 | 86.8% |
| FORD_GT | scene 4 | 322,218–895,516 | 710,677, 77.82 | 8,882, 330,334–884,553, centre 530,484 | 10.68 | 86.3% |

The shadow is where it should be: its centre sits inside the car's own silhouette box and below its
centre (583,467 against 594,359 for the Gran Torino), it moves with the car (583,467 → 562,476), and
it re-sizes with the geometry choice (17,787 → 16,511 px of area with the Gran Torino's centre moving
0.5 px and its box widening 15 px; 14,467 → 8,882 px for the Ford GT, whose candidate tree carries a
different body assembly). Every measured shadow lies inside the car's footprint in the frame, none of it appears
away from the car.

Softness, from the same frames (shadow pixels as a share of the lit ground's luminance):
96.5% of the Gran Torino's shadow (scene 6) is below 20% of the lit ground, 3.3% between 20% and 50%,
0.2% between 50% and 80% and 0.04% above 80%. The core is what is directly under the car; the visible
penumbra is the thin band at the car's own silhouette edge, where most of the blur is hidden behind
the car. The controlled probe below measures that ramp on open ground.

### The mapping control: the field lands under the object that cast it

A probe page builds a scene with a single 0.9 m block at world (+2, 0) or (0, +2) on a plane spanning
9.2 m, enables the shadow, runs the pass, and then **hides the block** so the painted footprint sits
on open ground and can be located directly. If the uv mapping were mirrored, the footprint would
appear on the opposite side of the plane. 640×480, resolution 512²:

| Block | Block silhouette (visible) | Painted footprint (block hidden) | Lit ground mean | Penumbra |
| --- | --- | --- | --- | --- |
| at +X | 4,420 px, box 417,198–487,265, centre 451,232 | 2,940 px, box 417,215–479,265, centre 447,240, mean 6.39 | 37.10 | 30 px left and right of the centre row |
| at +Z | 5,059 px, box 285,320–354,394, centre 320,357 | 3,933 px, box 288,333–352,394, centre 320,364, mean 6.29 | 37.10 | 33 px left, 32 px right |

Each footprint lies inside the silhouette of the block that cast it, on both axes, and none appears at
the mirrored position — so `u` runs with world +X and `v` with world +Z as intended. The penumbra
numbers are the softness measurement on open ground: the darkening ramps back to the lit ground over
about 30 px for a silhouette about 62 px wide, i.e. the blurred edge is about half the object's width,
and the sub-20-luminance core (2,940 px) is smaller than the silhouette (4,420 px).

### Label

`#presentation-label` is hidden in Original and visible in Enhanced in every run, with the rect
`{x: 24, y: 411.8, width: 960, height: 42}` for the Gran Torino and `{x: 24, y: 451.8, …}` for the
Ford GT — inside the 1280×900 viewport, under the controls it explains. Its text is
`ENHANCED_PRESENTATION.label`, which now names "a ground surface and a soft contact shadow under the
car". The two-car frames for a reader are `<CAR>-page-original.png` and `<CAR>-page-enhanced.png` for
`GRAN_TORINO` and `FORD_GT` — full-document captures (1280×1161 and 1280×1201) so the header label
and the whole car are in one frame — plus `<tree>-<car>-tree<record>-{original,enhanced}-canvas.png`
for the canvas alone at the measured viewport, and the read-back buffers as `.rgba` beside them.

## What this does not establish

- The shadow is a **height field**, not occlusion: it cannot self-shadow (a wing over a wheel casts
  nothing), it ignores every light direction, and no object other than the car occludes it. It is a
  labelled presentation effect, not a recovery of the game's own shading or of its blob quad.
- The ground and the shadow are new geometry and new render passes. They are display-only: the
  download path is untouched, and no recovered file changes.
- Coverage is the two named Ford Racing 2 cars at two geometry records, one camera and one software
  rasteriser. Other cars, records, cameras and GPUs were not sampled; the cross-game paths
  (Gran Turismo, Redline, Midnight Club) were not exercised with the shadow at all.
- The penumbra measurement is a 512² probe fixture, and the frame-area softness numbers are read from
  the page at 1024²; both are the software rasteriser's own output.
- The perf numbers were taken on a shared machine while other work ran; they bound the cost, they are
  not a benchmarking-grade figure (see below).

## Cost

The shadow runs once per placement, not per frame: one depth pass over the visible scene plus four
2-triangle blur passes into two 1024² targets, and a single boolean on every other frame (asserted by
the check). Steady-state frame intervals from the harness (90 frames per mode per tree): in the quiet
passes both trees held a p50 of 16.7–16.8 ms with Original and Enhanced identical; a later pass, run
while other work occupied the machine, reported a p50 of 50–133 ms for *every* tree and mode,
including the unmodified base, so those numbers are load rather than cost.

Two attempts to price one pass are recorded because they failed, and the gap the issue names is still
partly open:

- `gl.finish()` inside the probe page returns in 0.0–0.1 ms over ten passes: Chrome hands the work to
  its GPU process, so the call does not wait for it.
- Queueing 20 or 40 placements inside one frame did not move the frame interval off 16.7 ms at either
  512² or 1024², i.e. the interval is scheduler-bound in headless Chrome rather than work-bound.

The cost is therefore bounded structurally rather than measured in wall-clock time on this machine:
five extra draw calls and two 1024² render targets per placement, and none on a still frame. A
GPU-side measurement (a DevTools performance profile, or an `EXT_disjoint_timer_query` probe on real
hardware) remains open.
