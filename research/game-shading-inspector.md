# Candidate game shading in the Recovered inspector (issues #24 and #26)

`dealership/recovered.html` has a **Game shading (candidate)** control, off by default. When it is on, source
Headers with an established pass-4 assignment take the decoded paraboloid environment lookup and Headers with an
established pass-5 assignment add the decoded specular highlight, both decoded in
[`vu-handler-dump.md`](vu-handler-dump.md) and [`pass-source-join.md`](pass-source-join.md).

Pass 4, per vertex: `V = (position - eye) * position.w`, `d = V·N`, `R = -reflect(V, N)` transformed by
`TOP[12]`-`TOP[14]`, `s = (0.5·x′/(-1-|z′|)+0.5)·Q`, `t = (-0.5·y′/(-1-|z′|)+0.5)·Q`, and
`RGB = ftoi0(paint · min(1+0.95 d, 1))` with the factor in the alpha lane.

Pass 5, per vertex: `L = DM[6]`, `V = (DM[7] - position) * position.w`, `R = 2(N·L)N - L`,
`S = max(0.5·((R+V)·V) - 0.5, 0)`, `s = S·Q`, `t = TOP[1].w·Q`, and the per-draw constant
`RGBA = ftoi0(min(DM[5]·colour, 128))` with `alpha = ftoi0(min(DM[5].w, 128))`. The control is a reading of that
arithmetic, not a captured frame; the capture comparison verifies the per-draw RGBA relation and the `T` lane
(3,387/3,666 vertices exactly, 279 by one ULP) but not `S`.

The page identifies a part by the shipped GLB primitive's `extras.headerOffset`, matched against
`dealership/public/game-shading.json` — the 63 source Headers the pass-source join aligned to a pass-4 or pass-5 draw
(all COBRA, of the six loaded models), of which 37 carry pass 4 and all 63 carry pass 5. `tools/build_game_shading_assignments.py`
derives that table and copies the retained preview from `research/evidence/vu-dispatch/pass-source-join.json`;
`--check` and `tools/test_build_game_shading_assignments.py` fail on a stale or changed input. Any other car, or any
part of a listed car outside those Headers, renders exactly as before and the honesty label says so; the recovered
under-car shadow decal is excluded from both passes.

## Stand-ins and their cost

The receipt has no per-vertex eye, matrix or light, so the inspector substitutes them (ADR
[0004](../docs/adr/0004-inspector-game-shading-stand-ins.md)):

- **Eye**: the inspector camera position. The handlers read `DM[7]`, a game-state position; the vertex position
  is the model's own coordinate, and the model node transform is ignored.
- **Matrix**: the camera's world basis (view-derived), so the lookup is a view-space paraboloid and moves as the
  camera orbits. The game's `TOP[12]`-`TOP[14]` come from its own view state.
- **Position plane w lane**: `w = 1/|position - eye|`, because the exported geometry has no such lane and the
  capture comparison reads the pass-4 factor within [0, 1] on all 2,189 aligned vertices — a cosine, so the
  handler's V is unit length there. The reading also puts the reflection where a grazing surface is
  (factor → 1) and removes it face-on (factor → 0.05), instead of the negative factors a literal `w = 1`
  produced, and it is the same lane the pass-5 view vector is built from (`DM[7] - position`).
- **Pass-5 light**: `DM[5]` (colour, intensity, alpha lane) and `DM[6]` (the direction the specular reflects) come
  from game state. All 63 aligned pass-5 draws carry the *same* retained words, so the control substitutes exactly
  those (`PASS5_LIGHT`, `PASS5_LIGHT_DIRECTION` in the module) as one fixed light; no other light is added.
- **Compositing**: the decoded passes write their RGB and sample textures through the GS texture function, whose
  state is not in the receipt, so both terms are added over the baseline pass-2 colour. With the retained
  `DM[5].w`, the pass-5 alpha lane truncates to 0, so the highlight adds to RGB only.
- **Sampled texture**: the committed preview of `view-render-target-0` (256×128 PSMCT16S). The receipt records it
  as capture-time contents at the sampled address, not the post-render frame the aligned draw sampled.

## Evidence and limits

`tools/test_recovered_game_shading.mjs` (default `tools/check.sh`) asserts the control is off by default in the
markup, that off restores the exact baseline function objects, geometry attributes and material `userData`, that an
unassigned car and an unassigned part of an assigned car are untouched (with controls that reject a leaked term),
that a pass-5-only Header takes the highlight alone, that the under-car shadow decal stays unshaded, that the derived
table joins all 63 Headers to the shipped COBRA primitives with matching flags, that the light stand-ins equal the
retained `DM[5]`/`DM[6]` words of all 63 captured draws, and that the decoded factor, coordinates, specular and
colour relation match hand-computed values.

Where the pinned VU overlays are configured, the same test also runs each decoded handler through the repository's
real numeric executor (`tools/vu_shading_executor.py`: `tools/vu1_exec.py`'s NumDomain machine over the dispatch,
the handler prologue, one four-vertex loop iteration and the tail) on seven pass-4 vectors and six pass-5 vectors —
one pass-4 vector carrying the captured matrix and eye, three pass-5 vectors carrying the captured `DM[5]`/`DM[6]`
/`DM[7]` from `handler-dump-comparison.json` — and requires `factor`, `s`, `t`, `specular` and the colour lanes to
agree with the inspector's implementation (absolute tolerance 1e-6 for the factor and the specular, 1e-5 for `s`
and `t`, colour lanes exact). Without those overlays the comparison prints two skip lines naming the missing input;
the local disc carries only overlay-6 raw, so overlays 0-2 (which hold the pass-4 handler) and overlay 1 (pass 5)
are not reconstructible here.

Open: game-state eye, matrix and light, the pass-5 light's per-draw variation, capture-equivalence of the sampled
texture, the draw's blend equation, per-vertex factor and specular validation against a frame, full pass-5 `S`
reconstruction (its working-plane inputs are not retained), the 279 one-ULP `T` differences, and coverage beyond the
63 aligned COBRA Headers.
