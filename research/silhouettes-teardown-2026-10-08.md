# Silhouette gallery teardown and repairs — 2026-10-08

Executed against `viewer/index.html` and `tools/build_showcase.py` on
`bugfix/inspector-load-recovery`, revision `1062c2482d5e9d0becf39ef273cf9b9f104d7655`.
The initial tree already held substantial recovered-inspector/export changes and an
earlier teardown. Those are outside this task. A saved initial binary diff was compared
with the final tree: all **79 pre-existing tracked diffs outside this task's files are
unchanged** ([receipt](evidence/silhouettes-2026-10-08/preserved-work.json)).
This work adds local silhouette repairs and verification; it does not publish, merge,
change the tracker, or claim original-game rendering equivalence.

## Task, baseline and original acceptance

Simulated user: someone browsing this project's illustrated car corpus, selecting several
cars, inspecting their profiles and reading the associated game stats. That audience is
inferred from the gallery and its README; no participant preferences or adoption claims
are implied. Keyboard selection and a 390px viewport are practical constraints. Successful
inspection means the illustration is visible, can stay stationary, and remains explicitly
distinct from recovered original geometry. The original recorded illustration families
and handling-driven dimension formulas remain, with corrections to zero-valued ratings.

Working budget: approximately 45 minutes of investigation/implementation plus a 20-minute
verification/report reserve. Baseline snapshot was saved at 11:51 EDT. Normal use was
executed before diagnosis; later probes used source-assisted diagnostic hooks and disposable
HTTP overrides. A selector mismatch in the first diagnostic harness was corrected before
the retained baseline run; it was a harness problem, not a gallery finding.

| Requirement | Acceptance fixed before implementation | Checked coverage |
| --- | --- | --- |
| R1: corpus correctness | Preserve all 35 names, ordering, stats and labels; finite meshes; zero ratings retain their meaning | 35 records/meshes, invalid values, source/pixel pins; E1/E3/E5 |
| R2: sustained browsing | Removed cars release their owned geometry/material resources | Shared-resource disposal and 105 real browser selections; E1/E3/E4 |
| R3: inspection | Details do not cover the canvas; complete model fits; stationary view and keyboard view presets | 320/390/768/1280px, all 35 framed, four presets, motion controls; E2/E4 |
| R4: selection recovery | Empty search explains zero results; clearing restores the list; filtered preview identity is explicit | Empty search, group OR/style AND/year, native keyboard activation; E1/E4/E6 |
| R5: failure recovery | Invalid/failed/stalled corpus has an actionable error and retry; slow valid loads do not prematurely fail | Empty, duplicate, malformed, invalid rating, 404, 5.6s response, 15s stall, file/missing-vendor startup; E1/E4/E6 |
| R6: trustworthy illustration | Names remain literal text; icon sample excludes serialized headers/padding; colour interpretation and limits are explicit | Disposable HTML name, pinned decoded icons, sRGB round trip; E1/E3/E5 |
| R7: operation | Keep current Python/Node/vendored-three.js path; no added service, key, account, signup or charge | Empty-environment build/browser, external requests blocked; E7 |

macOS 26.4.1 arm64, Python 3.14.7, Node v26.9.0, ruff 0.16.9 and Chromium
153.0.8010.12. The documented `python3 tools/build_showcase.py` produced 35 records and
35 samples at baseline; `tools/check.sh` passed all **20** original steps, without skips.
Local browser execution used `python3 -m http.server 8098 --bind 127.0.0.1 --directory viewer`.
The browser package was the already installed Jev Browser package's Playwright-core.
It is diagnostic tooling, not a new required project dependency. The checked-in Node
regression uses the shipped three.js module and native Node HTTP, without npm install.
Skill hashes are retained in [skill-hashes.json](evidence/silhouettes-2026-10-08/skill-hashes.json).

## Findings and dispositions

| ID | Problem, evidence and strongest counterevidence | Classification, impact and disposition |
| --- | --- | --- |
| S01 / R2 | Cycling cars removed scene nodes without disposing resources. Initial GPU geometry count 13; after three preview selections and a 105-selection loop, 1,387. The active car still worked, so no data loss or crash was demonstrated. Actual renderer counters distinguish it from an invisible scene-node-only concern. | Confirmed defect; sustained-browsing resource burden; **fixed** by disposing each shared geometry/material once. Same 105-selection loop now peaks at 19 and ends at 13, textures stay at 3. |
| S02 / R3 | At 390×844 the 170×294px performance panel overlays a 390×506px stage and hides the car's front/top; desktop also overlaps its front. Horizontal overflow was already zero. The defect is occlusion, not general mobile nonconformance. Pixel inspection corroborates layout rectangles. | Confirmed visibility defect; recoverable inspection burden; **fixed** by separate viewport/details layout and camera fitting. Four tested widths have zero overlap and zero horizontal overflow. Phone details require vertical scrolling, deliberately trading simultaneous display for visibility. |
| S03 / R6 | A disposable name `<img src=x onerror="window.injected=true">` becomes an image and executes in the baseline list. The committed corpus is trusted and contains no such payload; no compromise was observed. Injected response plus the `innerHTML` call establishes the precise condition. | Confirmed literal-text handling defect, conditional on modified data; **fixed** with text nodes. Replay produces literal text, zero image nodes and no execution. |
| S04 / R4 | A nonmatching search hides all rows and leaves a blank list while the previous car remains. Selection itself works. No requirement to auto-select another car was assumed. | Demonstrated friction; minor recoverable burden; **improved** with live result count, retained preview identity, empty explanation and Clear search and filters. |
| S05 / R3 | Rotation and wheel motion start automatically; there is no persistent pause. Holding a pointer only stops the car temporarily, then release resumes it. Continuous motion is not necessary for profile inspection. | Confirmed inspection/control gap; **fixed** with persistent Auto rotate, reduced-motion default, stationary wheels and keyboard Side/Front/Top/Reset. The first re-attack found residual OrbitControls damping after pause; explicit pause now flushes that residual motion. The failed run is preserved. |
| S06 / R6 | Paint text says the texture's exact size is unresolved, although the repo already decodes 165×98 icons. The old sample scans serialized spans as RGBA and includes data outside the clipped image. Repeating the sample on decoded pixels changes only Thunderbird 2002: `[24,8,72]` → `[216,216,200]`. Most old samples were already the same. | Confirmed outdated explanation plus bounded sampling improvement; **fixed** using the existing decoder and manifest pin. Samples carry source/pixel hashes, dimensions and saturated/neutral mode. No car-body segmentation or actual-paint accuracy is claimed. |
| S07 / R5 | A 5.6s valid response receives the generic startup error at 5.1s and then succeeds. Empty/malformed/404 data has a generic error without in-page retry. Counterevidence: slow load ultimately recovers, so permanent blockage would be an overstatement. | Demonstrated transient feedback/retry friction; **improved** by separating module readiness from a 15s header/body timeout, validating the corpus and offering Retry loading cars. |
| S08 / R1/R6 | `value || 0.5` treats zero ratings as 0.5. Baseline zero/.5 speed lengths are both 4.68. A display sample `804020` round trips as `bc8963` because normalized display RGB was treated as linear. | Confirmed geometry/colour interpretation defects; **fixed** using nullish defaults and explicit sRGB input. Independent red probes and new assertions cover both. |
| S09 / R1 | Pickup tailgate uses `-bedL/2` on Z instead of rear X. F150 transverse bounds are `[-1.6029,1.18292]` despite symmetric wheels/cab. This is a coordinate error in the intended generic pickup, not a claim about true Ford dimensions. | Confirmed procedural geometry defect; **fixed** with tailgate at the bed's rear X, centered on Z; pickup windows also use cab width. All 35 final meshes have symmetric transverse bounds and tyres at the floor. |

Simulated reaction, not participant evidence: “I want the car to hold still, and I want the
specs beside it rather than over it.” That sentence generated the inspection probes; the
measured resource, motion and overlap behavior establishes the findings.

## Alternatives, research and decisions

Primary documents were accessed on 2026-10-08. Normal threejs.org manual URLs returned
404 here; the matching **r182** source pages were fetched from its official repository.
The TypeSafe documentation index and current building/citation-check cookbooks were read;
their narrow judgments keep execution and exact invariants in code. Jev is used for this
authorized evaluation, with the existing OpenRouter configuration, not in the gallery runtime.

| Candidate | Mechanism, source and prerequisites | Eligibility, limits and decision |
| --- | --- | --- |
| Retain shipped three.js r182 and repair internally | Local procedural mesh creation, OrbitControls and explicit owned-resource disposal. Official [cleanup source](https://github.com/mrdoob/three.js/blob/r182/manual/en/cleanup.html) and [colour management](https://github.com/mrdoob/three.js/blob/r182/manual/en/color-management.html). Already vendored; Python/Node/browser on existing hardware. | Existing accountless/keyless path; no new license/service cost or dependency. Real empty-environment build/browser verified. Preserves illustration behavior and fixes measured gaps; **selected**. |
| Google model-viewer | Model-loading web component; official [README](https://github.com/google/model-viewer/blob/master/packages/model-viewer/README.md) requires coordinated three.js peer version. Would require serializing procedural meshes and adding a component build/vendor surface. | No isolated installation/operation or full transitive eligibility validation performed; **excluded from implementation**. Its model-loading convenience does not solve the procedural resource/data defects by itself. License/authentication eligibility is not asserted. |
| Babylon Viewer | Official [viewer documentation](https://github.com/BabylonJS/Documentation/blob/master/content/features/featuresDeepDive/babylonViewer.v1.md) presents model-source loading and identifies V1 as deprecated. Replacement would require an engine/component transition and mesh adaptation. | No added dependency. Current V2 installation/offline operation and transitive eligibility remain untested; **excluded**. Do not carry a legacy CDN example into an offline project. |
| Existing `recover_car_ptg.decode_file` | Parse pinned reference icon descriptors, assemble source pixels and clip to header dimensions; [repo PTG continuation](ptg-continuation.md). Python standard library only. | Reuse, not a new backend. Tested all 35 icons from committed reference files with cleared environment. **Selected** for sampling; menu render/compositing and painted-body segmentation remain unestablished. |

Broader search discovered component viewers, car-viewing examples, community reports about
mobile overlays and local-viewer external assets. They were leads, not evidence of this
gallery's behavior or verified eligibility. No optional hosted/account execution path was
added. Replacing procedural silhouettes with original models, adding an AI runtime classifier,
photorealistic shading, or reclassifying all physical body shapes would change the gallery's
purpose; those opportunities were declined for this task. `concept`/`racecar` remain explicit
illustration families rather than asserted measurements. No user preference was inferred
to justify a wholesale renderer replacement.

Motion controls follow the relevant principle in [W3C Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).
This is a bounded keyboard/motion improvement, not an accessibility conformance claim.
Existing tracker [#9](https://github.com/nicolas-found42/carmodels/issues/9) is the historical
teardown index, and closed [#7](https://github.com/nicolas-found42/carmodels/issues/7) concerns
indefinite/silent load failure. Our transient slow-load behavior and retry gap were measured
independently; no ticket was reopened, commented on, created or closed.

## Evidence and experiments

All retained evidence is under [evidence/silhouettes-2026-10-08/](evidence/silhouettes-2026-10-08/).
Diagnostic scripts reuse the installed browser path; they are receipts, not required CI tools.
Baseline scripts require the saved pre-change HTML under `.scratch/silhouettes-2026-10-08/`.

| ID | Hypothesis/control → result | Artifacts |
| --- | --- | --- |
| E1 | Core browser workflow then repeated switches, empty search, invalid corpus and disposable HTML name → observed counterexamples | `probe-baseline.cjs`, `baseline-browser.log`, before screenshots |
| E2 | 390px details overlay obscures preview despite no overflow → confirmed by viewport pixels/rectangles; four-width final measurements show no overlap | `before-mobile.png`, `after-mobile.png`, `after-mobile-full.png`, `browser-final.log` |
| E3 | Zero defaults, colour transfer and pickup rear coordinate are incorrect → independent red probes fail before, final corpus regressions pass | `geometry-red.log`, `tools/test_silhouette.mjs`, `final-check.log` |
| E4 | Repairs survive real interaction, complete framing, repeated selection, motion and failures → 105 selections max19/end13 geometry; final pause stationary; five error/retry cases recover; stall15.195s; malicious name literal | `retest.cjs`, `browser-first-retest.log` (failed pause assertion), `browser-final.log`, final screenshots |
| E5 | Decode/clipping changes sample coverage without changing source stats → all35 pinned; one RGB changes; non-paint fields identical | `paint-baseline.json`, `data-invariants.json`, `tools/test_build_showcase.py`, `final-check.log` |
| E6 | Slow-load error is transient; missing libraries/file protocol still need guidance; filter composition must remain correct | `slow-before.cjs`, `slow-before.log`, `edge-smoke.cjs`, `edge-smoke.log` |
| E7 | Existing local runtime works without inherited credentials/account session → empty-environment build and fresh browser context succeed with external requests blocked | `clean-build.log`, `clean-browser.cjs`, `clean-browser.log` |

## Jev judgments and resolutions

The [judgment log](evidence/silhouettes-2026-10-08/jev-log.json) records material outcomes,
uncertainty and host resolutions. Screen the evidence as data, not tool-use authority.
The user-provided workflow was flagged `block` (injection0.78/substance0.98/relevance0.80).
That result was disclosed before continued use; the human's explicit instruction to follow
the attachment established its task authority. Primary-document screening requested review
(injection0.27); inspection found ordinary documentation/example instructions, which were
treated only as source data. Tracker screening passed (injection0.02).

Plan judgments supported measurable criteria and keyboard/phone constraints (0.93/0.91);
audience fit was uncertain (0.74), so the report labels that audience as inferred.
Classification accepted S01/S02 as defects; five other items required review. The explicit
host rule was existing wrong output/control → defect, avoidable feedback/effort → friction;
the table preserves conditional security impact and transient recovery counterevidence.
The architecture decision selected internal repairs at1.0 with no contradicted requirements.

An intermediate verifier gave three low-confidence supports and one unsupported slow-load
claim (confidence0.16). No green completion was inferred. The dedicated 5.1s baseline probe
was added to supply the missing observation; source inspection and exact disposal/corpus
tests resolve the other narrow facts. Tracker comparison remained review: related recovery
requirements but different failure conditions. The final patch gate uses raw per-file diffs
relative to the saved initial state plus the actual current check/browser logs.

The first full gate request exceeded the provider's token budget; it was an operational
failure, not a pass. A narrower runtime gate escalated (`safe_to_apply`0.15) and contradicted
the mesh claim at confidence0.88 while its evidence included the pre-change red controls.
That claim was stopped and checked with a new **final-only** [35-mesh audit](evidence/silhouettes-2026-10-08/mesh-audit.log).
The focused runtime gate then verified both the mesh and browser completion claims at
confidence **0.97/0.95**, with no contradictions or unsupported claims.

Automated patch approval was **not** obtained: the focused runtime gate still escalates
on test-gap/blast-radius confidence (`safe_to_apply`0.45, composite0.72). The sampling/tests
review also escalates on confidence (composite0.88475); an earlier accompanying review was
truncated, so a narrower nontruncated review replaced its coverage. No thresholds were
relaxed and no unchanged judgment was repeated to obtain approval. The host's source and
coverage review is recorded in [escalation-resolution.md](evidence/silhouettes-2026-10-08/escalation-resolution.md).
It resolves the concrete contradictory assertion with executed evidence and records the
broader coverage uncertainty; it does not represent a Jev `auto` verdict. The tool's final
automated-review status remains visible as an explicit limitation of this workflow.

## Verification and remaining coverage

`tools/check.sh` passes all **22** steps, including both added silhouette tests, with no
skips. The available pinned static inputs, handler captures and dump checks ran as well.
See [final check log](evidence/silhouettes-2026-10-08/final-check.log) and the baseline log.
`node research/evidence/silhouettes-2026-10-08/retest.cjs` and `edge-smoke.cjs` pass the
real browser re-attack. `env -i PATH="$PATH" python3 tools/build_showcase.py` and the fresh
browser diagnostic pass; `git diff --check` passes. Re-running the showcase builder is
deterministic. The existing verifiers' success includes their tamper controls and only
their declared scope; it does not prove full game render fidelity.

Coverage excludes Safari/Firefox, physical touch hardware, screen readers, manual free-orbit
keyboard control, WebGL context-loss recovery, GPU-specific behavior and large non-corpus
datasets. The phone viewport and full-page screenshots were both inspected; vertical scrolling
to details/controls is intentional. Model pixel-perfect appearance, correct physical body
dimensions, faithful menu compositing, and accurate car-paint segmentation remain outside
these procedural illustrations. All accepted in-scope findings above have an implemented
change and a check; these stated exclusions are not claimed passes.
