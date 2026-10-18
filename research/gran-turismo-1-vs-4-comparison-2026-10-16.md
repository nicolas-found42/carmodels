# GT1 models and their GT4 counterparts

2026-10-16. This compares the repository's recovered GT1 default LOD0 scenes with
GT4 static showroom previews. It does not compare native gameplay frames, establish
real-car accuracy or claim every GT1 car has a GT4 counterpart. No model was changed.

## Matched sample

Six pairs were selected by matching displayed model, grade and year labels in the
two source indexes. They are name-level counterparts, not proven identical regional
or equipment specifications. GT1 names are retained from verified native SPEC joins;
GT4 names come from its spec database.
[GT1 source index](../dealership/public/gran-turismo/index.json),
[GT4 source index](../dealership/public/gran-turismo-4/index.json).

Counts below include all default-scene body, wheel and tire instances. Hidden LOD
scenes are excluded. These are triangles, not counts of native quad packets.

| Counterpart labels | GT1 whole car | GT4 whole car | GT4 / GT1 | GT1 body | GT4 body |
| --- | ---: | ---: | ---: | ---: | ---: |
| RX-7 FD Type R ’91 | 530 | 7,830 | 14.77× | 282 | 4,230 |
| NSX ’93 | 480 | 7,668 | 15.98× | 232 | 3,436 |
| FTO GPX ’94 | 535 | 10,396 | 19.43× | 287 | 3,508 |
| Impreza Sedan WRX STI Version III ’96 | 514 | 6,457 | 12.56× | 266 | 3,097 |
| Corvette Grand Sport ’96 | 525 | 7,109 | 13.54× | 277 | 3,449 |
| Silvia S13 K’s ’88 | 504 | 6,792 | 13.48× | 256 | 3,696 |

Exact source pairs are `simulation/_afo7n` / `mazd0076`, `_hnsrn` / `hond0074`,
`_mfton` / `mits0030`, `_sipbn` / `subr0025`, `_ccrvn` / `chev0006`, and
`_ns13n` / `niss0005`. The [comparison measurements](../dealership/public/comparisons/gt1-gt4.json)
record each complete source path and SHA-256, default scene, per-node triangle
counts, texture dimensions, material counts, native paint counts and transformed
visible bounds.

GT4 has approximately **12.6–19.4 times** the whole-car triangles in this sample.
Body-only ratios are approximately **11.6–15.0 times**. Keeping those separate
matters: wheel/tire detail contributes substantially to whole-car counts. The RX-7
pair, for example, has 248 GT1 wheel triangles versus 3,600 GT4 wheel/tire triangles.
[Measured parts](../dealership/public/comparisons/gt1-gt4.json).

## The refined RX-7 is a related-trim comparison

The GT1 trial is **RX-7 FD Type-RB**, source `simulation/_afb7n`. No exact Type-RB
label exists in the current GT4 catalog. The comparison therefore uses GT4's
**RX-7 Type R (FD, J) ’91** as an explicitly related FD reference. The GT1 Type-RB
year remains unresolved. Do not interpret this as an exact grade/year match.
[GT1 native identity](../dealership/public/gran-turismo/index.json),
[GT4 catalog names](../dealership/public/gran-turismo-4/index.json).

| GT1 Type-RB edition | Triangles | Relative to the related GT4 FD (7,830) |
| --- | ---: | ---: |
| Recovered | 520 | 0.07× |
| First refinement | 2,080 | 0.27× |
| Eightfold further | 16,640 | 2.13× |
| Latest refinement | 133,120 | 17.00× |

The latest GT1 refinement has about seventeen times this GT4 preview's triangles,
but retains GT1 artwork and limits all inserted geometry to the bounded recovered
reference envelope. It does not recover GT4's source geometry or new texture detail.
That distinction follows from the refinement construction, not from an assumption
that triangle count measures visual fidelity.
[Refinement implementation](../tools/refine_gt_model.py),
[refinement limits and evidence](gran-turismo-preserving-model-improvements-2026-10-16.md).

## Textures, materials and presentation

All default texture sheets observed in these six GT1 scenes are 256×256. GT4 uses
multiple separate sizes, including 512×128 and smaller sheets. A 512×128 image has
the same pixel count as 256×256, so width alone is not evidence of greater texture
detail. Texture allocation, image contents, geometry and materials must be inspected
together. The measurements enumerate only image sources referenced by the default
visible materials; other paint-variant images are retained but not counted as
default textures. No guessed texture-resolution multiplier is asserted.
[Image dimensions](../dealership/public/comparisons/gt1-gt4.json),
[GT1 indexed artwork expansion](../tools/gt_model.py),
[GT4 model/material/texture construction](../tools/gt4_glb.py).

The [interactive comparison](../dealership/gt1-gt4-compare.html) shares a camera and
identical light rigs, centres/grounds both models without rescaling, and offers
wireframe, fixed views, independent native paint selectors and model downloads.
It initially selects an identical normalized paint name when both games offer
one; matching names do not guarantee matching RGB values. For the related Type-RB
comparison, its GT1 edition selector exposes all four refinement levels.

GT1 and GT4 material parameters and native artwork remain their exported values.
This makes the page a controlled comparison of these static exports, not a claim
of identical shading inputs or recovered game-render equivalence. GT4 reflections,
shadows and runtime wheel/branch behavior remain outside the static profile.
GT4 factory Pat0 paint variants are supported in the current exporter; the older
preview note's claim that they are not applied is stale.
[Current GT4 limits and paint construction](../tools/gt4_glb.py),
[current dealership conventions](../dealership/dealership/README.md),
[GT1 rendering limits](../tools/gt_model.py).

## Measurement and claim limits

Measurements read the actual GLB default scenes, traverse node transforms, count
indexed triangle instances and compute bounds from referenced positions. Model
SHA-256 values are checked against source indexes or refinement receipts. Counts
are independently cross-checked against producer scene totals, GT1 body/wheel
records and GT4 retained body-part receipts. The local analysis and validation log
are under `.scratch/gt1-gt4-compare/`; the published JSON carries source hashes.

The six-pair sample is not an exhaustive mapping of the two catalogs. Name/grade/year
agreement does not prove identical equipment or region. Exported bounds are measured
meshes, not vehicle specification dimensions or proof of correct placement. GT4's
static showroom scene and GT1's highest exported body LOD are different source
representations. Neither this table nor the browser comparison establishes PS1/PS2
render fidelity, real-car shape accuracy, or subjective preference.
