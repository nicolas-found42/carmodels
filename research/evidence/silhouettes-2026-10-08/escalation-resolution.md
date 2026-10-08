# Final review escalation: disposition and limits

The runtime gate's original `safe_to_apply` was 0.15. It marked the final mesh assertion
contradicted at confidence 0.88. Completion was stopped; the assertion was checked against
the actual working-tree module and a new independently logged corpus audit rather than
inferred from a green summary. `mesh-audit.mjs` constructs every current car, records six
finite bounds, floor minimum, transverse-center error and every resource's disposal count,
then asserts each invariant. All 35 pass. The focused runtime gate verifies that exact audit
claim at 0.97 and the actual browser re-attack at 0.95, without contradictions. No claim about
the baseline mesh geometry passing is made. The pre-change red probes remain evidence of
what was wrong, not completion evidence.

The remaining focused runtime gate is `escalate`, `safe_to_apply` 0.45, composite 0.72:
`viewer/index.html` limits on test-gap confidence 0; `viewer/silhouette.mjs` limits on
blast-radius confidence 0. It returns numeric distributions, not an identified failing
line or missing test. The sampling/test review is also `escalate`, composite 0.88475,
with low confidence in test-gap/blast-radius dimensions. Its file correctness scores are
1.88–1.92 out of 2, but these do not override the aggregate escalation.

The host inspected the actual source and final evidence as a separate reasoning review:

- The inline geometry factory is relocated to an imported local module. The same shipped
  THREE URL serves both imports. The dimension formulas and style mapping remain, except
  nullish zero defaults, sRGB input, rear-tailgate axis and pickup/SUV cab-window width.
  All 35 final meshes have finite bounds, nonpenetrating tyres and symmetric transverse bounds.
- Car switching removes the old group then disposes each unique geometry/material exactly
  once. Shared wheel/window resources are covered by event counters. Actual browser renderer
  memory stays bounded through 105 selections, unlike the recorded baseline. The test covers
  resource ownership, not every possible WebGL device or context-loss scenario.
- The list uses native text nodes for car names and metadata. The actual malicious-name
  browser reproduction no longer creates an element or executes. The classic guard's
  remaining HTML strings are fixed local guidance, not corpus input.
- Corpus values are validated before list/mesh construction; HTTP status is checked before
  JSON; abort spans headers and JSON body. Same-page retries for five failure classes work.
  An actual stalled HTTP body is checked with a native local server; the real browser checks
  header stall and slow success. The library-loading guard remains independent.
- Motion controls stop automatic rotation and flush residual damping. Reduced motion,
  persistent pause/resume and keyboard view presets are exercised through actual browser
  controls. All 35 models fit and the four tested viewport layouts have no panel/canvas overlap.
- Sampling verifies the manifest hash before PTG decoding and selects from decoded clipped
  pixels. Every icon's source/pixel hash and counts are checked. A corrupted temporary file
  triggers the intended hash failure. Regeneration is deterministic. All non-paint fields
  and ordering remain identical; generated RGB differs for exactly one record.
- The check-script delta adds two named test commands and updates the missing-Node message.
  The actual final script passes 22 steps with no skips. No external service or new required
  package was introduced. Empty-environment build and fresh browser execution succeed with
  external requests blocked. The 79 unrelated initial tracked diffs remain byte-identical.

These observations justify retaining the implemented local repairs as reviewable changes.
They do not supply an automated Jev patch approval. Remaining coverage gaps are disclosed:
Safari/Firefox, physical touch, screen readers, free-orbit keyboard control, context loss,
GPU-specific failures, large datasets and original-game appearance. No publishing/merge
decision is inferred from this review. No further model retry is warranted with unchanged
code/evidence; future evidence or a concrete reviewer concern can justify another judgment.
