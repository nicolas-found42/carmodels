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
| `blur` | 2.5 (three.js's unit: one tap is this over 256 of the plane) | The outermost tap lands 40 texture pixels from the texel at the shipped 1024² (16 for the narrower second pair), which the check asserts from the generated offsets. On the measured footprint that is a soft edge rather than an outline, and on a small object it is wider than the object itself (probe below). |
| `darkness` | 1.6 | Saturates the alpha where a surface meets the floor, so the contact is dark, and lets it fall off with height above the floor. Blurring what the depth pass produces is what makes the edge soft. |
| `opacity` | 0.85 | Keeps the darkest part of the ground slightly alive rather than pure black, so the ground still reads as a surface. |
| `margin` | 0.15 | The shadow plane extends a little past the car's footprint so the blur is not clipped at the plane's own edge. |
| `groundSpan` | 24 × the shadow plane | A large enough floor that its far edge is out of frame at the viewer's fitted camera, so the ground reads as a floor and not as a plate. |
| Ground colour | `#1e2735`, lit by the page's existing lights | A floor only a little lighter than the `#151a22` backdrop; it is a prop, not recovered data. |
| `planeDrop` | 0.0005 of the plane's side | The shadow plane sits a hair *under* the floor the placement chose, and above the ground. That floor is the lower of the framed box's and the drawn recovered under-car shadow quad's own (issue #72): the quad is flat at one height in the export, and the framing box deliberately leaves it out, so the page measures the quad it draws and passes its floor to `follow()`. The plane therefore stands under the quad in every view — 2.1–15.4 mm under it over the 35 cars × both views — and the quad keeps its candidate blend and draws over the shadow. |
| `groundDrop` / `cameraDrop` | 0.002 / 0.01 of the plane's side | The ground sits a hair under the car's lowest point, so the tyres touch the contact plane rather than the floor and the two coplanar surfaces never fight over depth. The depth camera sits a hair under the ground, looking up: the ground and the shadow are the only things between them, and the pass hides the whole group so neither reaches the field. |
| `minimumFootprint` | 0.1 | A degenerate record still gets a usable plane instead of a zero-scale one. |

## What the implementation guarantees

- **Original builds nothing.** No ground, no shadow plane, no render target, and no renderer call at
  all: `createContactShadow` builds on the first Enhanced selection, `setEnabled(scene, false)`
  takes the group out of the scene, and `update()` returns before it touches the renderer.
- **Original renders the pre-change frame.** Measured below: the read-back buffer is byte-identical
  to the same page served from the commit this branch is based on, for both cars and both geometry
  records.
- **Enhanced follows the car.** `follow(box, quadFloor)` are the only inputs; the page passes the visible
  geometry record's bounding box from `showRecord()`, the same box the camera is fitted to, and the floor
  of the recovered under-car shadow quad that view draws. The ground is centred on the box and sits at the
  lower of those two floors; the shadow plane spans the footprint plus its margin; the depth camera covers
  exactly that plane. An empty box (an empty source tree) or a cleared viewer hides both.
- **The plane is never above the recovered under-car shadow quad** (issue #72). That quad is the one
  surface the framing box deliberately leaves out — it is not part of the camera fit — so `showRecord()`
  measures the floor of the quad the selected view actually draws and passes it to `follow()`, whose
  lower floor the placement uses. The quad is flat at a single height in every shipped car, so the plane
  ends up one `planeDrop` below it at least; the check derives this per car and per view from the shipped
  GLBs. Before it, the plane sat *above* the quad in the F150 and F350 default views (measured +1.699 mm
  and +1.331 mm), because those two trees' floors (both +0.00502) are higher than the plane's own drop
  (side × 0.0005 ≈ 3.3–3.7 mm on those cars).
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
- **base** — `origin/main` at the time of the measurement (`782f0cb6`, which already carries issue
  #69's recovered under-car shadow and #70's pass-4 shading control) extracted to `/tmp/rec25-base`:
  the page as shipped without this change. It gives both controls: Original must match it byte for
  byte, and Enhanced-minus-base-Enhanced is the ground and the shadow alone, with the material,
  under-car shadow and shading changes cancelled out.

Cars `ford-racing-2/GRAN_TORINO` and `ford-racing-2/FORD_GT`, at three choices of the geometry
control: the default record ("Assembly 0 — standard wheels, headlights off", GLB scene 6), "Candidate
3 — all states" (scene 4), and the recovered `UNDER_SHADOW` record that issue #23 rebuilds as an
inspector view (record 41 for the Gran Torino, 72 for the Ford GT, read from each GLB). Canvas
1280×650.

**A defect in the first version of this note's numbers.** The blur's tap offsets were generated with
`h` twice (the axis vector already carried `h`), so the outer taps reached a third of a texture pixel
and the field was effectively unblurred; the first version of this note reported 17,787 shadow pixels
and 86.5% of the ground's luminance removed for the Gran Torino at scene 6, and a three-percent
penumbra share. Those figures were measured with the defect and are superseded by the tables below
(the corrected blur spreads the darkening over 40 texture pixels instead of a fraction of one). The
check now parses the generated offsets and asserts both the tap structure and that reach, and fails
for that reason if the defect returns; the review finding is what caught it.

### Original is byte-for-byte the pre-change frame

SHA-256 over the read-back RGBA buffer, head against base, same car and record, fresh load each time:

| Car | Record | Head | Base | Identical |
| --- | --- | --- | --- | --- |
| GRAN_TORINO | scene 6 | `0b77783d257607de` | `0b77783d257607de` | yes |
| GRAN_TORINO | scene 4 | `8d6b52dc4a8b7274` | `8d6b52dc4a8b7274` | yes |
| FORD_GT | scene 6 | `fafc529028512a84` | `fafc529028512a84` | yes |
| FORD_GT | scene 4 | `c97779e1ce211f07` | `c97779e1ce211f07` | yes |

So Original carries no ground and no shadow, and reproduces the shipped page exactly — including the
frames in which issue #69's under-car shadow quad and #70's shading control are present.

### The ground and the shadow, against the base tree's Enhanced frame

"Shadow" is a pixel at least 8/255 darker than the same pixel in the base frame (where the base shows
its backdrop through the ground), "lit ground" is a pixel more than 8/255 brighter. Screen
coordinates, y down.

| Car | Record | Car silhouette box | Lit ground (px, mean luminance) | Shadow (px, box, centre) | Shadow mean luminance | Ground luminance the shadow removes |
| --- | --- | --- | --- | --- | --- | --- |
| GRAN_TORINO | scene 6 | 324,218–887,581 | 713,300, 77.51 | 14,734, 330,332–855,556, centre 550,475 | 22.36 | 71.1% |
| GRAN_TORINO | scene 4 | 326,207–904,516 | 707,176, 77.49 | 7,981, 373,342–865,541, centre 585,467 | 12.31 | 84.1% |
| GRAN_TORINO | record 41 | 328,209–900,580 | 706,498, 77.56 | 14,665, 335,330–864,553, centre 558,473 | 24.20 | 68.8% |
| FORD_GT | scene 6 | 272,220–890,599 | 702,274, 77.62 | 16,744, 300,355–879,568, centre 489,495 | 19.45 | 74.9% |
| FORD_GT | scene 4 | 322,218–895,516 | 714,987, 77.33 | 0 (none darker than the backdrop) | — | — |
| FORD_GT | record 72 | 301,219–892,575 | 714,414, 77.55 | 11,766, 329,350–876,546, centre 478,488 | 19.86 | 74.4% |

Every measured shadow is inside the car's own silhouette box and below its centre, moves with the car
(550,475 → 489,495 between the two cars at scene 6) and re-sizes with the geometry choice (14,734 →
7,981 px for the Gran Torino, 16,744 → 11,766 px for the Ford GT). The Ford GT's candidate-tree-3 row
is the one this comparison cannot see: its shadowed ground never falls below the backdrop's own
luminance (the frame-internal table below measures it at 51% of the ground it falls on), so the
cancelling comparison reports no pixel — a limit of that metric, not an absent shadow.

### The shadow's contrast inside its own frame

The studio ground is not uniformly lit, so this table takes each row's baseline from the ground pixels
*beside* the car in that row (same depth, no shadow) and calls the ground inside the car's own screen
range shadowed when it is at least 15/255 below that baseline. The base frame is used only to mark
which pixels are the car. "Removed" is against the row baseline; "core" is darker than 60% of it,
"fringe" is the penumbra between 60% and the 15/255 threshold; "ground in the car's range" is every
ground pixel the car's screen range contains.

| Car | Record | Rows | Baseline | Shadow (px, box, centre) | Mean | Removed | Core | Fringe | Ground in the car's range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GRAN_TORINO | scene 6 | 346 | 72.0 | 28,534, 324,250–887,562, centre 614,402 | 26.6 | 63% | 21,964 | 6,570 | 99,799 |
| GRAN_TORINO | scene 4 | 310 | 73.3 | 22,472, 349,246–902,516, centre 669,332 | 39.8 | 46% | 9,790 | 12,682 | 101,052 |
| GRAN_TORINO | record 41 | 353 | 72.4 | 11,841, 328,329–877,561, centre 554,474 | 22.3 | 69% | 11,216 | 625 | 111,340 |
| FORD_GT | scene 6 | 356 | 71.7 | 40,918, 294,221–890,573, centre 608,404 | 29.9 | 58% | 31,793 | 9,125 | 95,585 |
| FORD_GT | scene 4 | 299 | 72.9 | 24,935, 322,234–895,516, centre 642,379 | 36.0 | 51% | 16,050 | 8,885 | 84,209 |
| FORD_GT | record 72 | 336 | 72.2 | 8,870, 322,346–883,552, centre 470,490 | 19.2 | 73% | 8,419 | 451 | 104,079 |

So the shadow darkens the ground it falls on by 46–73%, and 23–56% of its area is penumbra in the car
views. In the under-car-shadow record views the depth field is the quad's own flat footprint, so the
field is saturated over the whole quad and only its fringe reaches open ground (5% of the area); the
quad itself draws over the plane, as recorded above.

### The mapping control, and the penumbra on open ground

A probe page builds a scene with a single 0.9 m block at world (+2, 0) or (0, +2) on a plane spanning
9.2 m, enables the shadow, runs the pass, and then **hides the block** so the painted footprint sits
on open ground and can be located directly. If the uv mapping were mirrored, the footprint would
appear on the opposite side of the plane. 640×480, resolution 512², ground luminance 37.05:

| Block | Block silhouette (visible) | Painted footprint (block hidden) | Penumbra |
| --- | --- | --- | --- |
| at +X | 4,423 px, box 417,198–487,265, centre 451,232 | 2,427 px, box 418,215–476,265, centre 447,240, mean 14.88 (60% of the ground removed) | reaches the lit ground 50 px left and 50 px right of the centre row |
| at +Z | 5,059 px, box 285,320–354,394, centre 320,357 | 3,260 px, box 288,333–351,394, centre 320,364, mean 14.87 (60% removed) | 56 px left, 55 px right |

Each footprint lies inside the silhouette of the block that cast it, on both axes, and none appears at
the mirrored position — so `u` runs with world +X and `v` with world +Z as intended. The penumbra is
the softness measurement on open ground: the darkening ramps back to the lit ground over about 50 px
of a ~60 px silhouette, i.e. on a small object the blur is wider than the object itself; on a car it
is about 40 texels of the 1024² field, which at the Gran Torino's 6.26 m plane is roughly 0.24 m of
contact shadow.

### Label

`#presentation-label` is hidden in Original and visible in Enhanced in every run, with the rect
`{x: 24, y: 411.8, width: 960, height: 42}` for the Gran Torino and `{x: 24, y: 451.8, …}` for the
Ford GT — inside the 1280×900 viewport, under the controls it explains. Its text is
`ENHANCED_PRESENTATION.label`, which now names "a ground surface and a soft contact shadow under the
car". The two-car frames for a reader are `<CAR>-page-original.png` and `<CAR>-page-enhanced.png` for
`GRAN_TORINO` and `FORD_GT` — full-document captures so the header label and the whole car are in one
frame — plus `<CAR>-page-enhanced-under-car-shadow-record.png` for the issue #69 interaction, the
canvas-only captures at the measured viewport, and the read-back buffers as `.rgba` beside them.

## Cost

The shadow runs once per placement, not per frame: one depth pass over the visible scene plus four
2-triangle blur passes into two 1024² targets, and a single boolean on every other frame (asserted by
the check).

Three attempts to price one pass are recorded because the first two failed, and the gap the issue names
is still partly open:

- `gl.finish()` inside the probe page returns in 0.0–0.1 ms over ten passes: Chrome hands the work to
  its GPU process, so the call does not wait for it.
- Queueing 20 or 40 placements inside one frame did not move the frame interval off 16.7 ms at either
  512² or 1024², i.e. the interval is scheduler-bound in headless Chrome rather than work-bound.
- The harness's steady-state frame intervals were not usable either: on a machine shared with other
  work the unmodified base tree itself reported p50 intervals from 16.7 to 66.7 ms across runs, and the
  head tree reported the same p50 in Original and Enhanced. A difference that appears between trees but
  not between modes is load, not this change.

The cost is therefore bounded structurally rather than measured in wall-clock time on this machine:
five extra draw calls and two 1024² render targets per placement, and none on a still frame. A GPU-side
measurement (a DevTools performance profile, or an `EXT_disjoint_timer_query` probe on real hardware)
remains open.

## What this does not establish

- The shadow is a **height field**, not occlusion: it cannot self-shadow (a wing over a wheel casts
  nothing), it ignores every light direction, and no object other than the car occludes it. It is a
  labelled presentation effect, not a recovery of the game's own shading or of its blob quad.
- The ground and the shadow are new geometry and new render passes. They are display-only: the download
  path is untouched, and no recovered file changes. The recovered under-car shadow quad keeps its
  candidate blend, draws over the new shadow plane, and is measured as present in the Original frame
  comparison above.
- Coverage is two named Ford Racing 2 cars at three geometry choices, one camera and one software
  rasteriser. Other cars, records, cameras and GPUs were not sampled; the cross-game paths (Gran
  Turismo, Redline, Midnight Club) were not exercised with the shadow at all, and #70's pass-4 shading
  control was left off in every measured frame.
- The penumbra figures come from a 512² probe fixture; the page's own penumbra is read through the
  car, so its frame-internal share (23–56% of the shadow's area) is a lower bound on what the blur
  spreads.
- The shadow's image evidence was measured once with the blur defect described in the measurements
  section; the first figures are superseded rather than adjusted, and the check that now guards the
  offsets is an assertion on the generated shader, not a pixel comparison.
