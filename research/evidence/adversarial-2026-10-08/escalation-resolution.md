# Final Jev escalation: focused stronger reasoning review

Recorded 2026-10-08. Jev `typesafe/jev-1.13-20260917` returned `escalate`:
safe-to-apply 0.58, composite 0.7675, test-gap confidence 0.25; all seven claims
verified, none contradicted/unsupported; keyboard/mobile confidence 0.38,
20-check claim confidence 0.59. The unchanged gate was not rerun.

The existing independent standards and specification review agents were asked to resolve
these concerns with actual source and deterministic execution. This is the stronger-reasoner
path required by the installed Jev skill, not an automatic acceptance verdict or independent
proof based on model agreement.

## Standards/test coverage review

The reviewer inspected the actual check runner and retained final log: exactly 20 passing
steps, zero failures/skips. It inspected `tools/test_export_materials.py` (all 35 source
contracts plus three intended-error mutations), `tools/test_viewer_materials.mjs`
(deliberately reordered material/texture/image namespaces, alpha/factor/filter behavior),
`tools/test_model_load.mjs` (real GLB truncations, 404, body stall, timeout, cancellation),
and `tools/test_viewer_loading.mjs` (actual extracted callback, cleanup/retry/race/resource
disposal). It inspected the real browser script and its corresponding logs: all 35 cars
and 134 variant options, request failures, malformed container/image, slow/stalled requests,
stale selections, keyboard activation, search recovery, and no page errors.

It found no concrete material test gap. It noted the original base-map browser metric
used texture indices rather than image indices; synthetic reordered-namespace testing and
source-contract export testing already provided independent coverage. The metric was then
strengthened to use the actual material → texture → image relation and the full browser
sweep rerun; `browser-final.log` records this latest execution. The reviewer correctly
retained Chromium-only and bounded capture-source limitations.

## Specification/keyboard/mobile review

The reviewer independently ran the current gallery in Chromium at 390×844 using the
existing Playwright installation. Direct DOM and execution readback found 35 native,
focusable car BUTTONs, 12 filter BUTTONs, zero document horizontal overflow; Enter selected
a car (`aria-pressed=true`), Space toggled a filter true then false. This corroborates the
specific interaction and viewport claims; it does not establish full accessibility.

It directly inspected current COBRA GLB JSON for the LINEAR/LINEAR sampler and the explicit
limit: candidate default informed by 106 captured COBRA draws, other cars/game states
unverified. It confirmed that limit in all GLBs, README, control tooltip and report R6.
No remaining requirement mismatch or completion blocker was identified.

Disposition: accepted local F01–F07 implementation meets the bounded criteria based on
source-contract regressions, actual browser execution and recorded final checks. Jev's
automatic verdict remains escalated. Scope limits stay explicit; no all-browser,
all-game-state, or assistive-technology completeness claim is made.
