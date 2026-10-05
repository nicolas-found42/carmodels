# Original-recovery evidence index

The current synthesis is [research/original-recovery.md](../../original-recovery.md). The original inputs are in the sibling reverse-engineering repository and copied per-car reference corpus. This folder contains derived evidence and outputs.

| Evidence | Purpose |
|---|---|
| [car-asset-census.json](car-asset-census.json) | Archive/manifest byte identity, parser hashes, textures and geometry spans |
| [texture-gallery.html](texture-gallery.html) and `textures/` | 700 embedded level-zero images, each with raw and display alpha |
| [export-validation.json](export-validation.json) | 700 pinned RGBA hash matches and 1,400 independent PNG pixel roundtrips |
| [per-record-scale-experiment.json](per-record-scale-experiment.json) | All-record extrema comparison, divisor controls |
| [geometry-experiment](geometry-experiment/run_geometry_experiment.py) | Independent reproducible position, float-bias, alternate-scale and palette-zone experiments |
| [geometry-source-byte-check.json](geometry-source-byte-check.json) | 154 original ELF instruction-word checks |
| [packed-attribute-experiment.json](packed-attribute-experiment.json) | Packed vector lengths, UV ranges and texture-index bound checks |
| [four-byte-w-experiment.json](four-byte-w-experiment.json) | W=0/1 corpus measurements and candidate ADC linkage |
| [node-transform-census.json](node-transform-census.json) | Five roots per car, serialized translations and zero last-three fields |
| [geometry-export-index.json](geometry-export-index.json) | GLB hashes, independent records and five trees per car |
| [glb-validation.json](glb-validation.json) | Independent binary/accessor/image/reference/tree integrity checks |
| [inspector-ui-validation.json](inspector-ui-validation.json) | All 35 car selections loaded tree-zero candidates |
| [inspector-controls-validation.json](inspector-controls-validation.json) | Five Gran Torino trees, record and toggle checks; captured console errors |
| [texture-tests-initial-24.log](texture-tests-initial-24.log), [texture-tests.log](texture-tests.log) | Initial 24-test pass and follow-up 25-test pass |
| [full geometry corpus audit](full-geometry-check/20261004T203944Z-f8b8101687f140d0a6260de71e695722/result.json) | 56-file finite/ordered bound and exact-EOF checks |
| [claim-control-fixtures.json](claim-control-fixtures.json) | Seven balanced 12-claim Jev control sets |
| [jev-control-evaluation.json](jev-control-evaluation.json) | 66/84 final-verdict agreement, 75/84 relation agreement, all 28 review actions and mismatch dispositions |
| [Jev receipts](jev/) | Raw parent model outputs, recorded inputs and final review evidence snapshot |
| [jev-usage-summary.json](jev-usage-summary.json) | 21 persisted parent calls: 181,093 input / 11,013 output tokens; community calls separate |
| [jev-final-disposition.md](jev-final-disposition.md) | Escalated final gate and direct-review limits; no favorable retry |
| [historical format notes](format-notes-before-recovery.md) | Preserved incorrect shared-pool/palette-as-topology interpretation, now withdrawn |

Jev receipts include uncertain, unsupported, contradicted and escalated outcomes. Their confidence values are not substitutes for code/byte checks. Screenshots show experimental candidates, including all alternative runtime states and provisional shading; they are not in-game reference captures.

Current continuation evidence also includes [all 12 Jev capability receipts](../continuation/jev-capability-coverage.json), [94 extra mip levels](../../mip-continuation.md), [307 CARS/LIVERY/MATRIX PTGs](../../ptg-continuation.md), [refreshed executable/decompilation identity](../continuation/source-refresh/refresh-identity.json), [texture selector maps](../continuation/source-refresh/texture-variant-contract.json), and [independently validated GLB variants](../continuation/source-refresh/texture-variant-export-validation.json). The current [Khronos](../continuation/khronos-validation.json) and [Blender](../continuation/blender-validation.json) receipts bind the regenerated GLB hashes. Historical inspection receipts above bind earlier exports.
