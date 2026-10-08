# Adversarial teardown and repairs — 2026-10-08

Local work on `bugfix/inspector-load-recovery`, baseline revision
`1062c2482d5e9d0becf39ef273cf9b9f104d7655`. The starting tree was clean.
Scope: the offline recovered-car inspection/export workflow, the procedural gallery's
selection controls, and the existing recovery verification pipeline. Findings are based on
execution and artifacts; the skeptical-user persona is simulated, not participant research.
No publishing, production changes, tracker writes, or new dependencies were performed.

## Outcomes and original criteria

Assumed audience: a modder or asset researcher with Python and a browser who wants to
inspect three car types, change source geometry/texture candidates, and open the complete
car asset in another glTF consumer. A keyboard user must be able to select gallery cars
and filters. Source fidelity is bounded by the repository's stated candidate interpretations;
pixel-perfect game shading, animated transforms, live LOD and new recovery are separate work.

Budget: about 60 minutes of investigation/implementation with a verification/report reserve.
The useful coverage proxy is the known 35-car corpus, its source material/selector contracts,
all 134 exported selector options, and discriminating negative controls. More downloaded
bytes or more research links are not success measures. This is an asset-inspection project,
so generic retrieval coverage/pagination objectives do not apply.

| Requirement | Acceptance established before/while reproducing | Coverage and evidence |
| --- | --- | --- |
| R1: trustworthy export | Each source textured primitive and variant resolves to its intended texture; Header colours/alpha agree with source contract | All 35 cars, source-linked regression and three semantic mutations; E01/E14 |
| R2: trustworthy preview | Material, texture and image indices remain independent; linear colour factors and opacity survive selection changes | Synthetic reordered-index fixture plus real browser sweep; E01/E09 |
| R3: coherent recovery | Pending/failed selection cannot offer another car's download or overwrite its failure through old controls; retry and latest selection work | 404, malformed GLB, corrupt PNG, 5.5s load, 15s stall, cancellation and cleanup; E02/E03/E06–E08/E11/E12 |
| R4: usable selection | Car/filter controls activate with keyboard; usable 390px layout | Native buttons, Enter/Space execution, search recovery, 390×844 viewport; E04/E10 |
| R5: offline operation | Documented build/server path works with committed assets and no external runtime requests | Clean copied viewer, empty environment, fresh browser context and external network blocked; E15 |
| R6: bounded fidelity improvement | Candidate corpus default follows the bounded captured interval; raw texels remain inspectable | Existing source/capture receipts, Sharp pixels round trip and unchanged PNG payloads; E13/E14 |

## Baseline and environment

Executed the documented `python3 tools/build_showcase.py` and local HTTP server path,
then `tools/check.sh`. Build produced 35 cars and 35 paint samples; regeneration left
`cars.json` unchanged. All 16 baseline check steps passed; no baseline skips or pre-existing
failures. Static overlays, typed export and executable matched their pins. The retained
handler captures and two reference-frame inputs were also available. These available
checks were executed; a green result is limited to their declared scope and tamper controls.

macOS 26.4.1 arm64, Python 3.14.7, Node v26.9.0, ruff 0.16.9 and Chromium 153.0.8010.12 were used. Browser automation reused the configured
Playwright-core/Chromium installation in the existing Jev Browser package. The initial
unaided viewer attempt used Jev Browser; subsequent diagnostics added a read-only snapshot
function through a disposable HTTP response to inspect real THREE materials. Failure/race
probes intercepted local requests; they did not edit canonical inputs. Native browser runs
are complemented by deterministic callback tests with simulated transport/texture decoding;
those tests are not presented as independent browser proof.

Loaded skill packages:

- `~/.agents/skills/adversarial-ux-test/SKILL.md`, version 2.0.0, SHA256
  `c790dcbd617e5481e50fd5aeb432526ef976c14db011b2631ea3f4f73697f157`.
- `~/.agents/skills/jev/SKILL.md`, SHA256
  `7b4e3f55e2b3e813ffe7e97911ef0e9ceb4e576e17332db8f3e1cf8342e84d33`.
- Jev Browser and Conventional Branch instructions were read for their corresponding
  actions; jgrep found the material-update callback by behaviour. Its exit 0 was a match,
  not proof of a defect. Live MCP schemas were read before consequential judgment calls.

## Findings and dispositions

**F01 — confirmed defect; substantial export/inspection impact; fixed.**
The exporter inserted untextured materials before texture materials, while textured
primitives and variant mappings continued to use original texture indices as material
indices. In-range references passed integrity checks but referred to another material.
Expected ownership follows the source Header selector and pinned variant contract.
An independent baseline audit found **11,538 incorrect primitive bindings across all 35
cars**. The original material regression failed on a textured primitive with no
`baseColorTexture` (see [red log](evidence/adversarial-2026-10-08/material-red.log)).
The competing explanation, intentionally experimental texture interpretation, does not
explain a material-array offset introduced during export. The falsifying check is source
selector → exported texture identity, which failed before and passes now.
Texture materials now precede Header materials. All GLBs, their indexes and canonical
manifests were regenerated. Geometry/PNG payloads and scene structure remain identical.

**F02 — confirmed defect; substantial preview impact; fixed.**
The viewer used `textures[materialIndex]`; glTF instead uses material → texture → image
references. It also passed an array to `new THREE.Color`, which this pinned implementation
does not accept, then applied an unnecessary sRGB conversion to linear glTF factors.
Gran Torino execution showed **313 map mismatches** against its own GLB declarations;
black Header factors rendered as `[1,1,1]`. The alternative explanation that only F01
caused the appearance fails on a correct synthetic GLB with deliberately distinct index
namespaces. New `materials.mjs` uses explicit references and `Color.fromArray`, applies
variant colour/opacity/blend properties, and reads sampler settings. Gran Torino now has
zero mismatches and four black Header primitives remain black. The full real-browser
corpus/variant sweep also has zero map mismatches. This repairs candidate representation;
it does not prove the RGB lane reading or original GS shading.

**F03 — confirmed recoverable state defect; fixed.**
Small reproduction: load Gran Torino, intercept `COBRA.glb` with HTTP 404, choose COBRA,
then change Geometry. The Car selector says COBRA, but the old Gran Torino remains
visible/downloadable; changing Geometry replaces the failure status with a normal old-car
status. Counterevidence: an alert already identifies the failed COBRA load, and choosing
another valid car recovers. Therefore this is inconsistent failure state, not silence or
data loss. Acceptance: clear geometry/link, disable dependent controls, retain actionable
error and Retry, recover on same-car retry, and prevent stale requests from winning.
The repair meets those checks and bounds network/body reads to 15 seconds. Errors during
embedded-image decoding also clear partial state. E08 separately exposed the interaction
with the five-second startup guard; startup readiness now precedes the independently
bounded car request, so a valid slow load does not leave a stale startup error.

**F04 — confirmed keyboard selection barrier; fixed.**
All 35 gallery car rows and every filter were `div` elements with click handlers, without
focus or keyboard handling. Search was reachable; selecting another car/filter was not.
The expected button interaction follows the [W3C button pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/).
Native buttons now provide focus, Enter/Space activation and pressed-state semantics;
focus styling remains visible. The browser verified car activation with Enter and filter
activation/toggling with Space. This does not establish full canvas or screen-reader
accessibility. The competing explanation that arrow keys on the search field offer car
selection was excluded by the actual handlers; browser-native button activation is the
positive control.

**F05 — confirmed misleading download wording; minor impact; fixed.**
The title promised the same model shown above, although the direct link always downloads
the whole asset with stored default scene/base materials. Selecting another scene or
variant does not change its bytes. The downloaded Gran Torino file was byte-identical to
the export (latest artifact: 1,225,208 bytes; earlier E05 run: 1,225,076 bytes before the explicit filtering limit was added). A complete asset with all scenes is useful; transformed-view
export was not assumed to be required. The wording now describes the full car/all presets
and variants, and explicitly says preview choices are not baked into the file. This is
independent of the stale wrong-car link in F03. Jev compared the two aspects separately:
current-view settings contradict the old promise; presence of the car itself was uncertain
in the passage comparison, then settled by download bytes and parsed car identity.

**F06 — demonstrated small-viewport friction; fixed.**
At 390×844 the Geometry control created **92px horizontal overflow**, clipping its right
edge; 1280px worked. Pixel inspection and `scrollWidth - innerWidth` agree. No explicit
mobile-conformance promise was inferred. Bounding the inline labels/selects and removing
mobile right margins reduces overflow to zero. Vertical scrolling to the 3D stage remains
necessary and was exercised. This is a bounded layout repair, not a general mobile audit.

**F07 — evidence-backed capability/fidelity improvement (existing issue #19); implemented locally.**
The retained COBRA interval has 106 actual textured geometry tags with TEX1 `0x60`, selecting
linear min/mag and MXL=0. The old GLB sampler was NEAREST/NEAREST; the inspector hardcoded
nearest magnification and left minification at its mipmapped default. This is a demonstrated
departure from that interval, not proof about every car/game state. GLBs now declare
LINEAR/LINEAR (9729), and the inspector reads them without generating mip levels.
**Sharp pixels** restores nearest filtering and returns to linear when unticked. Applying that default across the corpus is an inference, explicitly labelled as a candidate in the exported claim limits and the control tooltip; filtering for other cars/states remains unverified. All source
texels remain unchanged. See [bounded packet evidence](packet-continuation.md) and
[existing request](https://github.com/nicolas-found42/carmodels/issues/19).

Existing issue #18 establishes the Header-colour expectation and #7 supplies related
startup-failure history. They do not erase these independently observed regressions.
No issues were reopened, created, commented on or closed. Broader reflection/specular,
shadow and viewer-versus-game work remains in the existing tracker/research index.

## Experiments, evidence and decisions

All paths below are retained under [the evidence directory](evidence/adversarial-2026-10-08/).

| ID | Hypothesis/control and result | Evidence / decision |
| --- | --- | --- |
| E01 | Source texture ownership and renderer map ownership fail independently; corrected checks pass | `source-baseline.json`, `probe-baseline.log`, `material-red.log`; D1 repair both exporter and renderer |
| E02/E03 | Failed car request leaves contradictory state; same-car retry should recover | `browser-final.log`, before/after failure screenshots; D2 explicit empty/error state + Retry |
| E04 | Gallery click-only controls cannot serve keyboard selection | `browser-final.log`, gallery viewport; D3 native buttons |
| E05 | Full-file download cannot encode current preview state | Byte comparison in browser log; D4 truthful full-asset label |
| E06 | Delayed old request can race latest selection | Delayed FOCUS WRC then F350 remains F350; browser log and actual callback regression |
| E07/E12 | Malformed container or invalid embedded PNG must not retain/download a partial model | Three-byte GLB and corrupted PNG signature; actionable errors and link cleared |
| E08/E11 | Startup timeout and car request timeout must represent distinct states | 5.5s valid load passes; stalled request fails at 15s with Retry |
| E09 | Corpus-wide ownership fix must cover selector variants too | 35 cars + 134 variant options, zero base/variant map mismatches |
| E10 | Existing layout clips Geometry at 390px | 92px before, zero after; matched viewport screenshots |
| E13 | Source-backed linear/no-mip default can preserve texel inspection | Real THREE sampler readback, Sharp pixels round trip; D5 include existing #19 improvement |
| E14 | Material/sampler repair must not change source geometry, pixels or scene structure | `export-invariants.json`; all 35 BIN payloads and selected metadata equal HEAD |
| E15 | Updated viewer remains offline/accountless from a clean consumer state | `clean-browser.log`; empty env, fresh context, local copied viewer, external requests blocked |

Negative controls include three source-semantic mutations (in-range wrong material,
changed colour, changed alpha), reordered material/texture/image fixtures, GLB truncations,
HTTP errors, stalled bodies and cancellation. The existing self-checking asset verifiers
also retained their tamper controls. Test coverage was strengthened rather than replacing
real integration checks with mocks: synthetic transport cases coexist with browser probes.

Two harness mistakes were corrected during investigation: an old diagnostic function
assumed a loaded model after the new empty failure state; a temporary diagnostic string
had a quoting error. Neither was attributed to the product or counted as a pass. An early
variant-loop placeholder was replaced by actual material-map readback before any corpus
completion claim. A baseline server's first port was occupied; another local port was used
without disturbing that process.

## Alternatives and tool eligibility

Research used web search/primary pages, awesome-list discovery, GitHub code/issues and
Reddit/Stack Overflow leads. Community posts were discovery only. Plugin discovery was
screened as off-target and excluded. Relevant installed skills/tools were sufficient.
This was a bounded investigation, not an exhaustive market survey or repository audit.

| Candidate, source/version | Gap, mechanism and decision | Eligibility / burden / limitations |
| --- | --- | --- |
| Retain current code | Lowest change cost but preserves reproduced ownership failures; rejected | Existing offline footprint, but no correction |
| Internal material/load correction (chosen) | Explicit source bindings, timeout/cancellation and real material tests; preserves custom geometry presets | Uses existing three.js r182 and browser/Python/Node primitives; no install, services, accounts, keys or licence fees added. Clean consumer run proven |
| [three.js GLTFLoader r182](https://github.com/mrdoob/three.js/blob/r182/examples/jsm/loaders/GLTFLoader.js) | Standard material parsing and broader glTF support; credible future seam, not integrated | MIT three.js ecosystem; adds utility import, requires adaptation of research-specific scene/record controls and external variant plugin. Official source warns about bitmap disposal. Not installation/prototype-tested here, so no new required tool admitted |
| [PlayCanvas model-viewer](https://github.com/playcanvas/model-viewer), reviewed 2026-10-08 | General inspector, discovered through awesome lists; no demonstrated advantage for the source-record workflow | Independent renderer/build footprint; complete keyless/offline execution path and transitive dependencies not tested. Licence/maintenance/integration fit not established sufficiently for adoption; excluded |
| [Google model-viewer](https://github.com/google/model-viewer), reviewed 2026-10-08 | Reusable 3D component; broader presentation opportunity | Custom record/preset controls still need adaptation. Complete eligibility not tested, so excluded from implementation |

The chosen material rules are supported by the [Khronos PBR schema](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/schema/material.pbrMetallicRoughness.schema.json)
and pinned THREE source, including separate indices and linear factors. Loader failure/
disposal tradeoffs were checked against [the maintainers' bitmap issue](https://github.com/mrdoob/three.js/issues/23953).
No required development/test library was added. Browser diagnostics reuse the existing
Playwright-core installation; the project checks need no npm install. Existing Jev is a
configured research/judgment service, not a new project runtime dependency. Full replacement
candidates remain excluded until their complete credentialless installation and operation
are proven, regardless of an open-source label.

## Judgment log, verification and limits

Jev uses `typesafe/jev-1.13-20260917` through the configured provider. Screened external
research and issue data passed; off-target plugin results were skipped. Risk reranking put
viewer recovery/material inspection ahead of corpus checks and gallery work, and ranked
pixel-perfect demands lowest because the docs exclude them. Hypothesis scores guided probes;
they were not defect evidence. F01/F02 classifications were automatic. F03/F04 initially
needed review; deterministic failure-state/keyboard evidence and explicit scope qualified
the claims. Claim verification supported all four; F03 severity remained a review judgment,
so the report uses only the measured contradiction and calls it recoverable. F05 was an
automatic defect classification; F06's defect-vs-friction split was unresolved (0.47/0.50),
so the conservative measured-friction label is retained.

The architecture decision selected internal repair (0.98) with no contradictory requirements;
the filtering decision selected linear + Sharp pixels (0.99). The first per-file patch
review escalated (`safe_to_apply=0.49`, composite 0.769), primarily on test-gap/blast-radius
uncertainty. Its full unfavorable result is retained in `jev-review.json`. Corpus-wide real
runtime tests, export invariants, clean execution and stronger semantic mutation controls
were added before final review. The final gate result is retained separately; it must be
read alongside these logs, not treated as independent proof.

Verification commands and current outcomes are recorded in `final-check.log`,
`browser-final.log`, `clean-browser.log` and `khronos.log`. Required `tools/check.sh`
includes four new meaningful regressions (export semantics, material properties, network/
container handling, and actual viewer load lifecycle); all available static/captured inputs
are exercised. Khronos checks run through the existing repository validator and include
its malformed-file negative control. Renderer/format checks do not establish game-render
equivalence. Browser evidence covers Chromium, 1280×900 and 390×844; other browser engines,
Blender import, live emulator capture, full assistive-technology testing, and the private
input provisioning path on another machine are untested. Search with no results recovers
when cleared; a richer empty-state message remains an optional usability opportunity.


## Independent standards and specification review

Standards: one deliverable issue was raised while evidence copies were in progress: logs
were still in scratch instead of the linked evidence directory. They are now retained with
the report; Markdown link existence and the evidence manifest are checked locally. No code
standards violation or actionable smell was identified.

Spec: one scope concern was raised for the corpus-wide linear default versus the bounded
COBRA filtering evidence. The GLB claim limits, control tooltip and R6 now explicitly label
that default as a candidate inference. No other material mismatch was identified for F01–F06.
These reviews inform the patch; agreement between models is not proof of correctness.

Exact verification entry points:

```sh
python3 tools/build_showcase.py
python3 tools/test_export_materials.py
node tools/test_viewer_materials.mjs
node tools/test_model_load.mjs
node tools/test_viewer_loading.mjs
node tools/test_viewer_scenes.mjs
python3 tools/validate_geometry_candidates.py
node tools/validate_gltf_khronos.cjs
tools/check.sh
git diff --check
```

The [required check log](evidence/adversarial-2026-10-08/final-check.log) records **20 passed
steps, no skips and no failures**. The [Khronos log](evidence/adversarial-2026-10-08/khronos.log)
records **35 models, zero errors and zero warnings**; its existing receipt records malformed
input rejection. The [browser sweep](evidence/adversarial-2026-10-08/browser-final.log)
records **35 cars and 134 variant options**, no map mismatch and no page error, with all
requests local. The sweep was repeated on the latest artifacts; [final smoke](evidence/adversarial-2026-10-08/final-smoke.log)
checks the latest download, candidate limit, sampler and mobile layout. The [clean-browser
log](evidence/adversarial-2026-10-08/clean-browser.log) records the credentialless consumer
run. The final project checks were repeated after the text/metadata correction. No new
library, account, API key or paid backend was added.

Matched desktop viewports: [before](evidence/adversarial-2026-10-08/before-desktop.png) /
[after](evidence/adversarial-2026-10-08/after-desktop.png). Mobile: [before](evidence/adversarial-2026-10-08/before-mobile.png) /
[after](evidence/adversarial-2026-10-08/after-mobile.png), plus [scrolled 3D stage](evidence/adversarial-2026-10-08/after-mobile-stage.png).

Remaining limits are research/coverage limits, not waived failures: candidate normals,
triangle/texture interpretation, RGB lanes outside the captured material example,
all-state filtering, reflections/specular/live animation/LOD, and the omitted platforms
and assistive-technology tests above. The accepted local changes F01–F07 are implemented.

## Final judgment and escalation resolution

The [final Jev gate](evidence/adversarial-2026-10-08/jev-final-gate.json) returned
**escalate**, not auto-accept: `safe_to_apply=0.58`, composite `0.7675`, test-gap
confidence `0.25`. It verified all seven supplied claims, with zero contradicted or
unsupported claims; keyboard/mobile evidence had confidence `0.38` and the 20-check
claim `0.59`. The input was not truncated. Raw implementation/test diffs and actual
logs were supplied; generated binaries were represented by source-contract checks and
before/after payload invariants. The raw check-runner diff was supplied as evidence;
documentation was covered by the separate standards/spec review. The earlier review
and low-confidence broad metadata wording are also retained, rather than discarded.

Following the Jev skill's instruction, “Low confidence on a consequential judgment goes
to the human or to a stronger reasoner, with the numbers attached,” the two independent
full reasoning reviews examined the specific concerns and execution evidence. Their
[resolution record](evidence/adversarial-2026-10-08/escalation-resolution.md) identifies
the source/test paths and a fresh keyboard/mobile browser run. No concrete remaining
test gap or requirement mismatch was found. A browser metric that originally compared
texture-array indices with texture indices was strengthened to traverse the actual
material → texture → image relation; the whole sweep was rerun on the latest artifacts.
The gate was not rerun to obtain a preferred verdict. These reasoning reviews resolve
the confidence escalation for the bounded acceptance criteria; the automatic gate
remains escalated, and broader platform/accessibility/game-fidelity claims remain unmade.

For reproducibility, the evidence directory retains the exact browser experiment scripts:
[corpus/failure probes](evidence/adversarial-2026-10-08/retest.cjs),
[final smoke](evidence/adversarial-2026-10-08/final-smoke.cjs),
[credentialless consumer probe](evidence/adversarial-2026-10-08/clean-browser.cjs), and
the baseline scripts. They are optional experiment snapshots, not new required project
dependencies; they use the already installed Playwright-core path recorded above and
task-owned local HTTP servers on ports 8087/8088 (baseline 8097). The retained scripts
include disposable response instrumentation and deliberate request failures. Evidence
integrity is indexed in [SHA256SUMS](evidence/adversarial-2026-10-08/SHA256SUMS).
