# GT4-guided upgrades of GT1 cars

Research, 2026-10-16. The target is to bring each GT1 car as close as possible to
its GT4 counterpart without assigning it geometry, equipment or artwork that
belongs to another car. Keep the recovered originals and publish any enhanced
edition separately. This note proposes a pipeline; it does not implement a
cross-game upgrade or establish that a GT4 game model is the physical car's ground
truth.

The key change from the existing trial is to obtain additional shape and artwork
from an evidenced reference, rather than keep increasing the GT1 triangle count.
For a fully verified counterpart, the actual GT4 mesh is already the closest
available representation of that GT4 model. Reconstructing it from the GT1 mesh
adds a correspondence problem. Where the GT1 edition has distinct trim, paint,
wheels or livery, those differences must survive unless a replacement is proved
to belong to the target.

## Current source coverage

The current [GT1 index](../dealership/public/gran-turismo/index.json) has **342**
public families: **178** have verified exact native SPEC identities and **164**
remain unresolved. Of the unresolved source codes, **159 end in `r`**; the other
five are `_a-odn`, `_c-67n`, `_lplan`, `_lplbn` and `_lplin`. These counts come from
the index rows and `native_metadata.identity.status`, not a count of verified
distinct retail cars. A suffix is not an identity proof. The metadata decoder
joins only the exact native code and assigns null specifications to an unmatched
family. It explicitly refuses to infer racing-family relationships.
[Identity join](../tools/gt_metadata.py#L235),
[native metadata limits](../tools/gt_metadata.py#L24).

The current [GT4 index](../dealership/public/gran-turismo-4/index.json) has **730**
distinct model codes with display names and `spec_label` values. Its native SpecDB
decoder supplies names, year, dimensions, tire data and factory-colour records.
Those GT4 codes and the GT1 SPEC codes are separate source identities; a
cross-game correspondence is an additional assertion, not an existing shared key.
[GT4 SpecDB joins and fields](../tools/gt4_specdb.py#L142),
[current GT4 source records](../tools/import_gt4_catalog.py#L175).

GT1's separate year and manufacturer fields remain unresolved even when the native
display name contains a year token. Such a token can support a displayed-name
comparison; it does not silently populate the missing structured field or prove
regional equipment. GT4's catalog converts native backticks in displayed years to
apostrophes without changing the underlying identity.
[GT1 metadata limits](../tools/gt_metadata.py#L24),
[editable catalog's null year](../tools/import_gt_dealership.py#L63),
[GT4 display-name normalization](../tools/import_gt4_catalog.py#L57).

Consequently, the same honest workflow can cover all 342 families, but this
research cannot promise 342 complete GT4-derived models. Unresolved target
identity, no catalog counterpart, uncertain donor compatibility and missing
source detail are different outcomes and should be recorded separately.

## The RX-7 boundary

The existing enhanced pilot's source is **RX-7 FD Type-RB**, GT1
`simulation/_afb7n`. The GT4 catalog contains Type R, Type RZ, Type RS, Type R-S,
Type RS-R, Bathurst R and Spirit R FD entries, but no exact Type-RB label.
`mazd0076` is **Mazda RX-7 Type R (FD, J) '91**, not Type-RB. A full transfer of
its wheels, lamps, trim and artwork would therefore assert compatibility that
these local identities do not establish.
[GT1 native name](../dealership/public/gran-turismo/index.json),
[GT4 FD names](../dealership/public/gran-turismo-4/index.json).

A better first same-label experiment is GT1 `simulation/_afo7n`, **RX-7 FD '91
Type-R**, against GT4 `mazd0076`, **Mazda RX-7 Type R (FD, J) '91**, SpecDB label
`rx7_r_eu_91`. Their printed model, grade and year agree, but GT4's additional
regional qualifier and GT1's incomplete structured identity still need to be
carried as caveats. The earlier [comparison note](gran-turismo-1-vs-4-comparison-2026-10-16.md)
and [source-pinned measurements](../dealership/public/comparisons/gt1-gt4.json)
retain this pair and five other displayed-name matches: NSX '93, FTO GPX '94,
Impreza Sedan WRX STi Version III '96, Corvette Grand Sport '96 and Silvia S13
K's '88. They are seed candidates, not an approved exhaustive interchange list.

For Type-RB, either establish the compatible regions of a particular donor with
additional primary evidence, or keep those regions in their GT1 form. A coarse
GT1 silhouette agreeing with a Type R does not prove that fine Type R details
belong to Type-RB. A clearer label is “GT4-guided Type-RB enhancement; retained
GT1-specific/unresolved parts,” not “exact GT4 Type-RB.”

## Three routes after identity review

| Route | Source of added detail | Fit to the stated goal | Constraint |
| --- | --- | --- | --- |
| Separately attributed GT4 counterpart edition | Actual matched GT4 body, wheels, tires, textures and material variants | Closest to the available GT4 preview when the complete car and equipment match | It is a GT4-sourced edition associated with the GT1 car, not newly recovered GT1 geometry; GT1-specific artwork or equipment cannot be silently discarded |
| GT4-guided GT1 derivative | Verified GT4 surface regions plus retained target-specific GT1 parts/artwork | Useful when the target identity is established but some trim or presentation must remain GT1-specific | Requires reviewed region correspondences and boundaries; unmatched features remain unchanged or explicitly unresolved |
| GT1-preserving refinement | Existing GT1 triangles, interpolated geometry and original artwork | Retains GT1 character while improving limited surface presentation | Cannot recover GT4's fine detail or source textures from subdivision alone |

All three can remain static **GLB / glTF 2.0**. The current viewer supports embedded
static triangle meshes with positions, normals, UVs, colours, PNG artwork and native
material variants; it does not accept arbitrary required mesh extensions,
animations or skins. A concrete generated derivative still needs actual loader
and rebuild checks.
[Static loader contract](../dealership/editable-glb.mjs#L8),
[GT1 exporter](../tools/gt_model.py#L249),
[GT4 exporter](../tools/gt4_glb.py#L56).

The existing refinement's displacement cap is an artistic policy for that trial,
not a source-derived limit on this future work. Repeating bounded subdivision can
produce far more triangles while retaining the same limited GT1 reference and
artwork. The [comparison measurements](../dealership/public/comparisons/gt1-gt4.json)
and [refinement implementation](../tools/refine_gt_model.py) distinguish those
outputs from the GT4 reference. A future GT4-guided displacement policy should be
derived from identity-compatible reference regions, protected target features and
measured error; it must not inherit the old cap automatically.

## Proposed correspondence ledger

Create one record for every GT1 family, retaining its original code, source hashes,
native identity status and exact model/grade spellings. For each GT4 candidate,
retain code, SpecDB label, exact name/year/region tokens, GLB/native-source hashes
and the reason it is a candidate. Do not fuzzy-match “RX-7” and treat the result as
an exact donor.

The proposed outcomes are: fully evidenced counterpart; displayed-name match with
remaining identity questions; related donor with named compatible regions;
unresolved target identity; or no suitable source in the current catalog. These
are proposed workflow states, not classifications already applied to all cars.
Multiple GT4 years/grades should remain alternatives until evidence settles them.

For every permitted donor region, record the evidence for target compatibility,
the source mesh/primitive or native shape range, transformations, excluded parts,
and the retained GT1-specific features. Match body shell, bumpers/aero, lamps,
mirrors, glass/openings, wheels/tires, cabin and livery separately. A valid shell
match does not approve a rim or racing decal. Where local game data is insufficient,
use additional primary model/equipment documentation or leave the region unresolved.

This is especially necessary for racing families: neither a similar suffix nor
a shared sponsor/model name establishes year, aerodynamic package, interior or
livery. GT1 metadata intentionally does not inherit base specifications for those
unmatched identities. [Exact-code ownership policy](../tools/gt_metadata.py#L1),
[null unmatched data](../tools/gt_metadata.py#L235).

## Proposed geometry and artwork pipeline

1. **Clear a pilot identity and edition contract.** Decide whether its output is
   the complete observed GT4 counterpart, or a hybrid preserving named GT1-specific
   features. Keep original GT1 and GT4 source assets unchanged and record the
   derivative's two source identities. Do not label the GT4 source hash as the
   recovered GT1 source.
2. **Compare the actual sources before fitting.** Load referenced default scenes,
   compose node transforms, establish units/axes, and align with reviewed rigid
   landmarks. Measure body and wheels separately. Do not nonuniformly scale away
   a wrong trim or proportions mismatch. Specification dimensions and collision
   bounds are separate data, not substitutes for visible-mesh measurements.
   [Existing transformed measurements](../dealership/public/comparisons/gt1-gt4.json),
   [GT4 wheel/part records](../tools/gt4_glb.py#L337).
3. **Use source geometry directly where the whole counterpart is cleared.**
   Preserve the matched GT4 edition's native textures, UVs and factory variants.
   This is the least ambiguous way to match that preview; it remains limited by
   the current static GT4 conversion. Expose source attribution and retain the
   recovered GT1 edition alongside it.
4. **For a hybrid, restrict transfer to reviewed regions.** Retopology or
   subdivision supplies editable sampling; a region correspondence supplies
   the reference shape. Projection must be restricted by part, surface side,
   distance and normal compatibility, with explicit rejection when ambiguous.
   A global nearest-surface projection can cross openings or hit an adjacent
   panel/interior. Treat that as a failure to resolve correspondence, not a reason
   to fabricate a surface. These are proposed controls, not implemented guarantees.
   Blender 4.5's Shrinkwrap modifier is one concrete implementation option: a
   vertex group can restrict influence, and Project mode offers a distance limit,
   projection-direction selection and front/back face culling. The target should
   be an approved part/region, rather than the complete donor car. Nearest-surface
   mode is merely geometric proximity; the modifier has no knowledge of car
   identity or trim. This option is documented but has not been tested on these
   GT1/GT4 assets. [Official Blender 4.5 Shrinkwrap manual](https://docs.blender.org/manual/en/4.5/modeling/modifiers/deform/shrinkwrap.html).
5. **Preserve feature and artwork ownership.** Keep separate UV/material/hard-normal
   seams. Source-derived GT4 UVs work with the GT4 artwork they describe; they do
   not automatically map GT1 paint or liveries. GT1-specific artwork needs a
   reviewed reprojection/bake and pixel checks, or retention of its original
   surfaces. Do not generate badges, vents, panel lines or interior parts from
   an image model. Do not use a same-named colour as a proven cross-game palette
   mapping. Current paint code deliberately requires source-owned bindings.
   [GT1 face/UV ownership](../tools/gt_model.py#L407),
   [GT4 primitive/variant construction](../tools/gt4_glb.py#L205),
   [paint ownership checks](../dealership/game-paint.mjs#L1).
   Re-baking existing GT1 artwork onto a better supported surface can preserve
   its design, but cannot recover unreadable source pixels or a missing logo.
   Existing low-resolution artwork remains a fidelity limit. Do not paint
   speculative reflections or lighting into a supposedly recovered colour map.
6. **Measure reference agreement and preservation independently.** For cleared
   regions, measure bidirectional surface distance, per-view silhouettes, landmark
   alignment and normal differences. Separately check target wheel placement,
   trim, openings, UV/artwork ownership, material variants and source provenance.
   Set region-specific tolerances from the actual source resolution and intended
   edition; no universal millimetre threshold is established here. Keep a reviewed
   source/region ledger for every accepted deviation.
7. **Review before scaling out.** Use identical camera/light conditions, matched
   paint where independently supported, wireframe, multiple views and separate
   original/enhanced downloads. A high triangle count or low average distance
   cannot override one wrong lamp, wheel or livery. Test negative controls such as
   Type-RB/Type R, different model years and race/road editions. Complete scoped
   extraction/conversion checks when those tools change; derivation work requires
   the full affected-game tier. [Repository verification tiers](../CONTRIBUTING.md#the-check-to-run-before-a-pr).

The current GT4 exporter merges draws into body material/texture primitives and
separate wheel/tire meshes. It retains native source pins and per-part statistics,
but a material primitive is not a semantic “headlamp” or “bumper” label. Fine
transfer masks therefore require additional native-shape tracking or reviewed
segmentation; material names alone are insufficient.
[Body draw merging](../tools/gt4_glb.py#L153),
[body/wheel/tire assembly and records](../tools/gt4_glb.py#L266).

## Reference limits

GT4 here means the repository's **static showroom preview**, not a complete
rendered game frame or an independent scan of the real vehicle. The current
exporter selects LOD0/callback branch 0, uses a documented wheel-placement reading,
omits reflection-like/shadow overlays and flat planes, and does not reproduce
runtime transforms, damage, animation, reflections/specular passes or PS2 blending.
Factory Pat0 material/palette variants are supported in current code; the old
preview note's contrary statement is stale.
[Current GT4 limits](../tools/gt4_glb.py#L22),
[current factory paint application](../tools/gt4_glb.py#L266).

Thus “not invented” can be demonstrated as **traceable to compatible observed game
source geometry**. It cannot, using these local files alone, prove that every
artistic detail of the GT4 asset exists on the physical car. If physical-car
accuracy is required, corresponding primary physical/equipment evidence becomes
an additional acceptance criterion.

## Claim limits and next step

The research phase inspected current local source code, indexes, retained metadata and
the existing comparison artifacts. No model, texture, code or comparison page was
changed during that phase, and no new fit/projection/bake, exhaustive cross-game match, native-game
capture or physical-car validation was performed. Algorithmic stages and distance
metrics above are proposed design controls, not benchmarked implementation results.

The recommended next step is the identity/part correspondence ledger plus a
same-label RX-7 Type R '91 pilot. Compare a separately attributed direct GT4
edition with a narrowly defined GT1/GT4 hybrid only after the target-specific
requirements are explicit. Type-RB remains a related-donor investigation. Apply
the same evidence policy to every other family and report the unresolved cases
instead of manufacturing universal coverage.

## Implementation checkpoint

The first stage is now implemented by [the counterpart builder](../tools/build_gt_counterparts.py),
with a searchable [ledger page](../dealership/gt1-upgrades.html). The generated
[ledger](../dealership/public/gt4-guided/ledger.json) accounts for all 342 GT1
families: 155 have unreviewed lexical suggestions, 23 have no lexical candidate,
and 164 have unresolved native identities. These are deterministic discovery
states, not semantic compatibility judgments or proof that a counterpart is absent.
Every target and donor candidate retains its source identity and hash. No regions
are approved for GT1 transfer.

The [RX-7 Type R '91 study receipt](../dealership/public/gt4-guided/receipt.json)
attributes the GT1 target and GT4 donor separately. Its GLB adds only an attribution
record to the GT4 document: the entire donor binary and all other document fields,
including geometry, UVs, textures, transforms and factory variants, remain unchanged.
The comparison measures 530 original GT1 triangles against 7,830 study triangles.
It is an attributed GT4 edition for inspection, not a reconstructed GT1 model or a
cleared Type-RB upgrade. [Executable preservation and corruption controls](../tools/test_build_gt_counterparts.py).

`python3 tools/build_gt_counterparts.py --check` rederives the generated ledger,
study GLB, receipt and comparison data. The checks are registered for both GT1 and
GT4. Full identity/equipment review, semantic region masks, fitting and artwork
transfer remain future work; this implementation does not claim those stages are
complete.
