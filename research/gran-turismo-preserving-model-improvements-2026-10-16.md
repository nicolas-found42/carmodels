# Improving GT1 appearance while preserving the car

Research and one-car pilot, 2026-10-16. The user approved increased polygon count,
conservative rounding of curved panels and wheel outlines, preservation of
proportions, panel edges, paint and details, and a separate enhanced model keeping
the recovered original. Normals, shading and filtering may change, while the
result should retain GT1's low-poly character.

The current format is **GLB, binary glTF 2.0**. Both the recovered source exporter
and the new enhancement writer use version-2 GLB containers. No format migration
is needed. [Source writer](../tools/gt_model.py#L475),
[enhancement writer](../tools/refine_gt_model.py#L48).

## Initial implemented pilot

The pilot is **RX-7 FD Type-RB**, native source `simulation/_afb7n`. Its exact name
and verified native SPEC identity are retained by the original GLB's metadata.
The source path and SHA-256 are pinned by the enhancement CLI; a changed input is
rejected before regeneration. [Pilot input](../tools/refine_gt_model.py#L17),
[source pin check](../tools/refine_gt_model.py#L287).

The [enhanced GLB](../dealership/public/gran-turismo-enhanced/rx7-fd-type-rb-enhanced.glb)
is separate from the [recovered original](../dealership/public/gran-turismo/simulation/_afb7n.glb).
The [receipt](../dealership/public/gran-turismo-enhanced/receipt.json) records
**520 → 2,080 triangles** in the default displayed scene: body 272 → 1,088,
and four wheels each 62 → 248. This is an actual generated count, not a target
multiplier for every GT1 car. Fourfold triangles does not mean fourfold recovered
detail.

## Eight times further

The user subsequently requested “8x further”, interpreted as eight times the
2,080-triangle pilot, giving **16,640 displayed triangles** (32 times the recovered
520-triangle model). The separate [higher-density GLB](../dealership/public/gran-turismo-enhanced/rx7-fd-type-rb-enhanced-8x.glb)
and [receipt](../dealership/public/gran-turismo-enhanced/receipt-8x.json) retain
the earlier file as their pinned input. The earlier enhanced GLB's SHA-256 remains
`6a367cd2c59ce2c642e740dfabcead9f0c77c4828d3a5aac0d1d480da2b9df99`.
The new default is scene 4; scenes 0–3 and their existing nodes, meshes, accessors,
buffer views and complete binary ranges remain unchanged.
[Further-stage construction](../tools/refine_gt_model.py),
[earlier-version and loader assertions](../tools/test_refine_gt_model.py).

Each earlier triangle receives a shared four-child edge refinement. Two children
then receive interior centroid splits, replacing each selected triangle with
three: `2 + 3 + 3 = 8` children per earlier triangle. The interior splits add no
boundary samples, so this reaches the exact count without unmatched edge splits.
New interior points use bounded tangent-plane projections; an unsafe or
degenerate case keeps its arithmetic centroid. This deliberately uses mixed
triangle sizes rather than claiming a uniform subdivision level.
[Eightfold tessellation](../tools/refine_gt_model.py).

Further refinement does not accumulate a fresh displacement allowance at every
stage. The tool reconstructs linear positions and native vertex lineage from
the first pilot's retained recovered accessors. New edge and interior samples
carry corresponding recovered reference positions. Their displacement is bounded
by the same **0.2% of each original part's longest dimension**, and original part
bounds remain fixed. The body stays within about **8.6 mm** of these references;
float32 encoding introduces sub-micrometre rounding. All earlier samples are
retained. This envelope bounds geometric change; it does not prove an unchanged
intermediate silhouette or better visual quality.
[Reference reconstruction and clamp](../tools/refine_gt_model.py),
[per-sample envelope, winding and shared-edge assertions](../tools/test_refine_gt_model.py).

Protected source edges are re-evaluated using retained original normals,
attributes and native identities, then inherited by their first-pass edge
segments. This prevents a later pass from smoothing an originally authored
crease merely because first-pass geometric normals now fall below the angle
threshold. The wheel-ring exception remains explicit.
[Inherited edge protection](../tools/refine_gt_model.py),
[authored-crease regression](../tools/test_refine_gt_model.py).

At that stage, the comparison defaulted to earlier enhancement versus the new version. A
reference selector can show the recovered original on the left instead. All
three downloads remain available, with shared paint, camera and wireframe
controls. The original files and library catalogs remain unchanged.
[Comparison page](../dealership/gt1-enhanced.html).

## Another eightfold step: 133,120 triangles

The next requested eightfold increase produces a separate
[133,120-triangle GLB](../dealership/public/gran-turismo-enhanced/rx7-fd-type-rb-enhanced-133120.glb),
with its own [receipt](../dealership/public/gran-turismo-enhanced/receipt-133120.json).
It has 8 times the previous 16,640 displayed triangles and 256 times the recovered
520. The two earlier enhanced files remain byte-identical. The new default scene
is scene 5, retaining all earlier scenes, source binary ranges and position/UV/colour
samples. Materials, native artwork and all four paints are unchanged.
[Stage construction and publication](../tools/refine_gt_model.py),
[successive-generation preservation and loader checks](../tools/test_refine_gt_model.py).

The same eight-child scheme is reused. Stored recovered reference positions are
carried forward; protected edge segments are reconstructed recursively through
exact original accessor/index joins to retained earlier meshes. Protection is
propagated to each descendant half-edge, and newly detected boundaries are retained
too. New lineage descriptions use SHA-256 digests to bound metadata growth.
The displacement allowance remains the original 0.2% per-part extent, with
coordinate-scale float32 rounding; it is not reset and accumulated at every stage.
[Ancestry, lineage and reference handling](../tools/refine_gt_model.py).

At this density, opposing interpolated normals and float32 winding changes occur
on extremely thin triangles. Zero-length interpolated normals use the parent
geometric normal, or a retained endpoint normal for a zero-area parent. Both this
fallback count and final float32 winding repairs are recorded per mesh. Final
child winding is checked after float32 encoding. Reorientation is allowed only
when the parent area falls within a coordinate/edge-scale roundoff bound; a
resolvable inverted parent or a collapsed nondegenerate child is rejected.
[Numerical controls](../tools/refine_gt_model.py),
[unit-normal and rejected-inversion controls](../tools/test_refine_gt_model.py).

The comparison defaults to 16,640 versus 133,120. The left selector also offers
2,080 and the recovered 520 triangles; all four editions have downloads. Functional
browser and regression results for this generation are recorded separately from
the earlier runs below. Higher tessellation does not increase texture resolution
or establish real-car or original-game detail.

For this generation, `.scratch/gt1-133120-checks/test_refine_gt_model.log`
records **23 tests**, followed by `OK`. The suite covers both repeated eightfold
stages, byte-identical earlier artifacts, descendant support/bounds, shared edges,
positive encoded child winding, normal fallback/unit length, ambiguous ancestry,
production GLB loading and stale outputs. The broader check invocation was still
running when this section was written; no complete-run claim is made here.

The full GT1 run in `.scratch/gt1-8x-checks/` preceded the final authored-crease
regression: its refinement log records **14 tests**, followed by `OK`. After the
inherited-edge safeguard and its regression were finalized, the focused run in
`.scratch/gt1-8x-final-checks/` recorded **15 refinement tests**, followed by `OK`.
That later run also checks final artifact freshness, lint and check selection.
The final suite covers preservation, exact count, source-envelope, inherited
creases, shared-edge continuity, winding, production loading and stale outputs.
These are distinct executions; the earlier full run does not establish that the
later fifteen-test version ran in that earlier invocation. Original-disc and
Blender checks remain skipped in this session.

The initial enhanced file appends a new default scene, scene 3, with separate refined body
and wheel meshes. The original LOD0/LOD1/LOD2 scenes, nodes, meshes, accessors,
buffer views and original binary ranges remain available in the same download.
The original recovered file remains separately downloadable. This avoids silently
replacing the recovered original. [Scene construction and retained binary prefix](../tools/refine_gt_model.py#L242),
[preservation assertions](../tools/test_refine_gt_model.py#L55).

Materials, embedded artwork, samplers, native colour-variant mappings and complete
CAR/CTEX payloads are retained. The original position, UV and colour samples remain
at the beginning of each enhanced primitive's attribute arrays; inserted samples
are appended. Derived normals may change. The pilot retains four native paints:
CHASTE WHITE, SILVER STONE METALLIC, BRILLIANT BLACK and VINTAGE RED.
[Attribute construction](../tools/refine_gt_model.py#L190),
[artwork/native-data/variant assertions](../tools/test_refine_gt_model.py#L68).

## What the refinement does

One edge split produces four children for every source triangle. For a triangle
A, B, C with midpoints AB, BC, CA, the children are `(A,AB,CA)`, `(AB,B,BC)`,
`(CA,BC,C)` and `(AB,BC,CA)`. If these new points stay at the arithmetic midpoints,
the children partition the same original piecewise planar surface. This geometric
derivation explains why extra triangles alone cannot round a silhouette. The
pilot instead allows bounded movement of selected inserted points while fixing
all original position samples. [Four-child construction](../tools/refine_gt_model.py#L197).

For body curvature, the implementation checks edge incidence, material primitive,
opposite directed use, geometric face angle, endpoint normals, UV/colour continuity and native vertex
identity before linking local normal fans. Open/nonmanifold edges, material
boundaries, attribute seams and sufficiently sharp normal changes do not receive
this body's smooth-edge displacement. Normals are recomputed from angle-weighted
local faces; protected attribute duplicates remain independent. Geometrically
identical edge positions share a midpoint decision rather than being welded into
one output vertex. [Edge records and guards](../tools/refine_gt_model.py#L75),
[local normal averaging](../tools/refine_gt_model.py#L142).

The wheel route has a separate rule around the native X-axis pivot: short,
constant-X, approximately equal-radius segments may receive radial midpoint
rounding. It is distinct from the body guard and is not a claim of general
manifold smoothing. Axial or unequal-radius edges do not qualify for that wheel
ring rule. [Native-pivot wheel rule](../tools/refine_gt_model.py#L171).

Every new midpoint is limited to **0.2% of its mesh's longest dimension** from the
arithmetic midpoint, then clamped to that mesh's original axis-aligned bounds.
The generated receipt records a maximum body displacement of about **8.6 mm**;
wheel limits are about **1.3 mm**. This bounds local modification; it does not prove
all intermediate silhouettes are unchanged. [Displacement cap and bounds clamp](../tools/refine_gt_model.py#L104),
[per-mesh measured values](../dealership/public/gran-turismo-enhanced/receipt.json).

Children of a nondegenerate parent must keep positive geometric-normal alignment
with that parent or generation fails. Original degenerate triangles are recorded
rather than presented as repaired geometry. Native face triangle ranges are
multiplied by four, and enhancement metadata retains original attribute/index
references while explicitly distinguishing source normal IDs from derived display
normals. [Winding control and mappings](../tools/refine_gt_model.py#L213).

These are conservative geometric rules, not a semantic understanding of every
panel, lamp or authored crease. No new texture detail, wheel design or native game
geometry is recovered. A visual comparison remains necessary before broad rollout.

## Reviewable comparison

The [comparison page](../dealership/gt1-enhanced.html) presents the chosen reference
and latest enhanced model side by side under a shared camera and matching light rigs.
All loads use receipt hashes. Paint changes apply to all four loaded editions; wireframe and fixed
three-quarter, side, end and above views support inspection. Separate download
links expose both GLBs. [Comparison implementation](../dealership/gt1-enhanced.html#L22).

The page is separate from the source and dealership catalogs. Its existence does
not imply the enhanced car has replaced an existing library entry or that other
GT1 cars have been regenerated. The enhancement CLI writes only its designated
model and receipt outputs. [Output scope and freshness mode](../tools/refine_gt_model.py#L287).

## Validation status and limits

The tool invokes the production Python baker before returning a derivative.
Its tests define checks for source/hash identity, deterministic output, retained
original scenes and binary ranges, artwork/native payload/variant preservation,
original samples and part bounds, child winding, seam/crease/nonmanifold and
same-direction overlapping-sheet controls, wheel-ring
rounding, planar preservation, invalid inputs, the production JavaScript loader,
and stale model/receipt rejection. [Production baker invocation](../tools/refine_gt_model.py#L279),
[test definitions](../tools/test_refine_gt_model.py).

Executed `tools/check.sh --game gran-turismo --full`: **129 passed, 4 skipped,
zero failures**. The skips were source-disc extraction (pinned input unavailable)
and three Blender roundtrips (runtime unavailable). Canonical GT1 export
rederivation and enhanced-pilot freshness passed. A final focused run of `ruff`,
`test_refine_gt_model`, `gt_enhanced_pilot` and `test_run_checks` passed all four;
the refinement suite executed ten tests. Logs and manifests are retained locally
in `.scratch/gt1-refinement-checks/` and `.scratch/gt1-refinement-final-checks/`.

The browser comparison loaded both models; native-paint selection, wireframe and
side-camera controls were exercised. This is a functional A/B check, **not user
visual acceptance**. Review all four paints and multiple viewpoints before a
broader rollout. Source-disc and Blender checks remain unexecuted in this session.

The current enhancement is artistic derived geometry. Original samples and part
bounds are fixed, but intermediate silhouette and shading can change. Texture
resolution is unchanged. Original-game lighting, transparency, palette rewrites,
shadows, animation and complete render equivalence remain outside its claim.
The existing GT1 exporter documents those native rendering limits, and the new
receipt adds its enhancement-specific limits. [Native export limits](../tools/gt_model.py#L17),
[enhancement limits](../tools/refine_gt_model.py#L266).

## Further work

Use the original/enhanced A/B to decide whether the approved low-poly character,
proportions, panel edges, rim details and paint remain acceptable. Measure
silhouette differences across views rather than relying on unchanged bounding
boxes alone. If acceptable, keep a separate enhanced identity and preserve the
recovered originals for later trials; do not apply repeated global subdivision
merely to raise the count.

Native-render recovery remains a separate investigation. The existing
[native-data note](gran-turismo-model-data.md) records unresolved palette-processing
and extra-pass leads; they are not evidence that generic gloss, transparent glass
or invented highlights belong on this pilot. The [earlier shading research](gran-turismo-shading-2026-10-11.md)
also distinguishes measured winding/normal repair from unproven game appearance.
