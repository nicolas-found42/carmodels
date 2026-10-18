# Candidate game shading in the Recovered inspector (issue #24)

`dealership/recovered.html` has a **Game shading (candidate)** control, off by default. When it is on, source
Headers with an established pass-4 assignment take the decoded paraboloid environment lookup in
[`vu-handler-dump.md`](vu-handler-dump.md) and [`pass-source-join.md`](pass-source-join.md): per vertex
`V = (position - eye) * position.w`, `d = V·N`, `R = -reflect(V, N)` transformed by `TOP[12]`-`TOP[14]`,
`s = (0.5·x′/(-1-|z′|)+0.5)·Q`, `t = (-0.5·y′/(-1-|z′|)+0.5)·Q`, and `RGB = ftoi0(paint · min(1+0.95 d, 1))`
with the factor in the alpha lane. The control is a reading of that arithmetic, not a captured frame.

The page identifies a part by the shipped GLB primitive's `extras.headerOffset`, matched against
`dealership/public/game-shading-pass4.json` — the 37 source Headers the pass-source join aligned to pass-4 draws
(all COBRA, of the six loaded models). `tools/build_pass4_assignments.py` derives that table and copies the
retained preview from `research/evidence/vu-dispatch/pass-source-join.json`; `--check` and
`tools/test_build_pass4_assignments.py` fail on a stale or changed input. Any other car, or any part of a listed
car outside those Headers, renders exactly as before and the honesty label says so.

## Stand-ins and their cost

The receipt has no per-vertex eye or matrix, so the inspector substitutes them (ADR
[0004](../docs/adr/0004-inspector-pass4-shading-stand-ins.md)):

- **Eye**: the inspector camera position. The handler reads `DM[7]`, a game-state position; the vertex position
  is the model's own coordinate, and the model node transform is ignored.
- **Matrix**: the camera's world basis (view-derived), so the lookup is a view-space paraboloid and moves as the
  camera orbits. The game's `TOP[12]`-`TOP[14]` come from its own view state.
- **Position plane w lane**: 1, because the exported geometry has no such lane.
- **Compositing**: the decoded pass writes `RGB = paint · factor` and samples the environment texture through the
  GS texture function; the draw's `ALPHA_1` blend equation is not in the receipt, so the term is added over the
  baseline pass-2 colour.
- **Sampled texture**: the committed preview of `view-render-target-0` (256×128 PSMCT16S). The receipt records it
  as capture-time contents at the sampled address, not the post-render frame the aligned draw sampled.

## Evidence and limits

`tools/test_recovered_game_shading.mjs` (default `tools/check.sh`) asserts the control is off by default in the
markup, that off restores the exact baseline function objects, geometry attributes and material `userData`, that
an unassigned car and an unassigned part of an assigned car are untouched, that the derived table joins all 37
Headers to the shipped COBRA primitives with matching flags, and that the decoded factor and coordinates match
hand-computed values.

Where the pinned VU overlays are configured, the same test also runs the decoded handler through the repository's
real numeric executor (`tools/vu_pass4_executor.py`: `tools/vu1_exec.py`'s NumDomain machine over the dispatch,
the pass-4 prologue, one four-vertex loop iteration and the tail) on seven vectors — one carrying the captured
matrix and eye from `handler-dump-comparison.json` — and requires `factor`, `s`, `t` and the colour lanes to agree
with the inspector's implementation within an absolute tolerance of 1e-6 for the factor and 1e-5 for `s`/`t`.
Without those overlays the comparison reports one skip line naming the missing input; the local disc carries only
overlay-6 raw, so overlays 0-2 (which hold the pass-4 handler) are not reconstructible here.

Open: game-state eye and matrix, capture-equivalence of the sampled texture, the draw's blend equation, per-vertex
factor validation against a frame, and coverage beyond the 37 aligned COBRA Headers.
