# Improving GT4 models without redesigning the car

Research updated 2026-10-16. Inspected pre-implementation baseline:
`059f8840e1d35e9b313f1407e8bc9f7184c65b75`. This is research and proposed acceptance
criteria; it does not report an implemented or visually validated enhancement.

## Settled scope

The source viewer remains the recovered reference. The dealership becomes a modern
realistic showroom, automatically enhancing all GT4 cars with geometry refinement
included immediately. Prioritize maximum desktop visual quality. Preserve uncertain
materials and retain original geometry for parts that fail refinement. Real-car
references may reconstruct finer shapes and verified dimensions may correct GT4
proportions. Without exact references, use conservative source-based refinement.
The user delegated remaining implementation choices; no interview decision blocks work.

Identity means the same model/year/trim, body, factory equipment, wheel design,
lamps, badges and livery. Better detail does not authorize a different trim, wheel,
body kit or plausible invented feature. Verified corrections and source-derived
refinement must be distinguishable in provenance.

## Inspected baseline

- Every GT4 material receives metallic `0`, roughness `0.7` and double-sided rendering.
  Native material values are retained, but the PBR base factor uses clamped diffuse.
  Reflections, specular passes and PS2 blending remain outside the inspected profile.
  This is a material-response investigation target, not evidence that arbitrary
  shinier values recover an original finish. [Exporter](../tools/gt4_glb.py),
  [shared adapter](../dealership/materials.mjs)
- Native normals, UVs and nontrivial vertex colours already export. Face normals are
  a fallback when packet normals are absent. Kind-2 reflection-like overlays,
  kind-5 shadows and flat shapes are omitted; external texture sentinel `511` is
  excluded from ordinary texture decoding. Investigate these paths against native
  evidence rather than adding duplicate surfaces or imagined reflection inputs.
  [Exporter](../tools/gt4_glb.py)
- Pat0 factory paints already work in the inspected code. `factory_models` patches
  independent MDLS buffers in bounded material/Tex1 regions; `build_car` emits named
  material variants. Direct inspection of committed `acra0001.glb` found its five
  named variants, normals, vertex colours and uniform `(0, 0.7)` material factors.
  The existing test independently applies patch bytes before comparing decoded
  variant pixels; it was inspected, not run for this research.
  [Patch decoder](../tools/gt4_model.py), [exporter](../tools/gt4_glb.py),
  [test](../tools/test_gt4_glb.py),
  [inspected GLB](../dealership/public/gran-turismo-4/previews/acra0001.glb)
- The older preview note says Pat0 is unapplied, contradicting current code and the
  research index. Jev comparison judged that contradiction with probability `0.98`.
  Do not use that stale statement as the improvement backlog.
  [Historical note](gran-turismo-4-previews.md), [index](README.md)
- Both viewers already have hemisphere/directional lighting with different settings.
  The shared textured material path reads base colour/texture, opacity/cutout,
  roughness, metallic and sidedness. Normal maps or richer material extensions need
  explicit loader/adapter support. A sophisticated Blender material will not simply
  become visible by exporting it. [Dealership](../dealership/dealership.html),
  [source viewer](../dealership/recovered.html),
  [editable loader](../dealership/editable-glb.mjs),
  [adapter](../dealership/materials.mjs)

## Topology constrains automatic refinement

The exporter groups native draws by texture, material index, vertex-colour presence
and alpha mode. Welding compares position, normal, UV and colour exactly within
each group. It emits indexed triangles in body/wheel/tire nodes. A display primitive
is consequently a render-state group, not an established semantic car panel.
[Grouping and welding](../tools/gt4_glb.py)

**Implementation implication:** reconstruct geometric adjacency separately from
per-corner rendering attributes. Preserve UV, normal, colour, material and alpha
discontinuities. Coincident positions alone do not establish that vertices may be
welded; an index boundary alone does not establish a real panel seam. Keep independent
parts, attachment transforms and all factory variant mappings. Preserve uncertain
boundaries rather than using a whole-car position weld.

## Geometry methods

**Native-normal triangle refinement is the recommended conservative starting point.**
The original Curved PN Triangles paper constructs cubic triangular Bézier patches
from the three positions and vertex normals of an existing triangle. It matches
corner position/normal data, forwarding other attributes mostly by linear
interpolation. It targets existing game triangle art and explicitly does not
promise tangent continuity everywhere. [Authors' paper](https://alex.vlachos.com/graphics/CurvedPNTriangles.pdf)

Proposed application: keep source corners, sample curved geometry only where native
normals and local topology support a smooth patch, and use consistent shared-edge
positions. Retain separate UV/colour/normal domains across rendering seams; do not
average hard normals to manufacture curvature. Pin protected boundaries, cap local
displacement, and preserve original parts when checks fail. Those restrictions are
project design choices, not guarantees supplied by PN triangles. Native normals
are shading data, so their usefulness as shape constraints still needs measurement.

Loop subdivision is another triangle-compatible method. OpenSubdiv requires purely
triangulated meshes for Loop and describes Catmull–Clark as suited to quad-dominant
meshes. Its edge/vertex sharpness and face-varying interpolation controls distinguish
geometry from UV discontinuities. Boundary modes describe smooth boundary curves
and corner behavior; they do not promise to freeze every source boundary position.
[OpenSubdiv rules](https://opensubdiv.com/docs/subdivision_surfaces.html)

Catmull–Clark is therefore an alternative requiring deliberate topology/crease
control, not a safe global modifier for exported render groups. Blender documents
its edge rounding and the use of creases/support loops. Simple subdivision generally
does not smooth coplanar surfaces. More triangles on the same planar surface are
not recovered curvature. [Blender subdivision](https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/subdivision_surface.html)

Weighted normals and bump-only detail change shading rather than the mesh surface;
true displacement changes the surface. Shading improvements alone do not fulfill
the selected geometry-refinement scope.
[Weighted normals](https://docs.blender.org/manual/en/4.2/modeling/modifiers/normals/weighted_normal.html),
[bump versus displacement](https://docs.blender.org/manual/en/4.2/render/materials/components/displacement.html)

## Reference-assisted reconstruction

COLMAP reconstructs structure and camera intrinsics/extrinsics from overlapping
views of the same object. Known camera calibration can be supplied. Dense stereo
fuses depth/normal maps into a point cloud and can reconstruct a surface. Its
tutorial recommends good texture, high overlap, different viewpoints and similar
illumination, and warns against specularities on shiny surfaces.
[COLMAP tutorial](https://colmap.github.io/tutorial.html)

**Project policy:** accept reference-based shape corrections only with established
same-year/trim/parts identity and reliable image alignment or verified physical
dimensions. Record reference provenance, scale, affected landmarks and uncertainty.
Measurements may correct GT4 proportions when verified; aesthetic plausibility may
not. Glossy paint, glass and unobserved areas need particular caution. A successful
photogrammetry run does not by itself verify identity or every hidden surface.
No actual real-car corrections were found or applied by this research.

TripoSR describes a learned transformer/LRM-based system producing a mesh from a
single image and evaluates it on public datasets.
[Primary technical report](https://arxiv.org/abs/2403.02151)

**Inference:** a generated mesh is a candidate, not measured evidence of unseen
car surfaces or correct trim. Multiple generated views of one photograph are not
independent observations. Without exact references, retain source-derived shape
constraints and use conservative refinement; do not publish generative inventions
as recovered detail.

The analogous texture concern is supported by the perception–distortion distinction
in image-restoration research. A sharper-looking AI texture is not evidence that
its grille, badge or lettering is historically correct. Preserve UV placement,
factory palette variants, alpha and identity-bearing graphics; use evidence-backed
restoration for those details. This is a project inference, not a measured GT4
error rate. [Primary paper](https://openaccess.thecvf.com/content_cvpr_2018/html/Blau_The_Perception-Distortion_Tradeoff_CVPR_2018_paper.html)

## Proposed automatic pipeline and acceptance

The selected implementation architecture is deterministic enhancement on dealership
load, with the same enhanced GLB used for its downloadable paint buffer. A Node
catalog audit should exercise every car and retain source/fallback records. This
avoids rewriting the full source corpus. These are implementation decisions, not
completed behavior reported by this research note.

1. Record each car's identity, source hash, preset variants and part transforms.
   Assemble exact references where available; mark missing coverage explicitly.
2. Run independent material, texture and geometry stages across the catalog.
   Translate supported paint/glass/rubber/chrome/lamp responses; keep uncertain
   materials unchanged. Evaluate a controlled showroom environment without
   confusing lighting changes with material correctness.
3. Refine eligible geometry from retained positions/normals. Where reliable external
   evidence exists, apply separately documented local reconstruction or dimension
   corrections. Do not require manual tuning of every car.
4. Validate protected landmarks, silhouette/dimension changes, seam continuity,
   finite nondegenerate triangles, orientation, attribute domains, wheel placement,
   variant bindings and texture readability. Reject folds, cracks, uncontrolled
   bulges, changed features and lost paint variants. Keep original geometry for the
   failed part and record the reason. These are proposed checks to implement.
5. Rebuild affected dealership metadata and verify source assets unchanged. Inspect representative
   fixed-camera full-car and close-up renders as part of catalog validation; a
   one-car-first manual pilot is not a prerequisite selected by the user.

The dealership owns independent editable GLB copies. GT4's preserving importer skips
existing models by default; `--upgrade-unedited` updates only a working hash equal
to its recorded source. A dedicated enhancement path must preserve existing user
edits, provenance and the unchanged source reference. [Editing contract](../dealership/dealership/README.md),
[GT4 importer](../tools/import_gt4_dealership.py)

Maximum desktop quality remains bounded by measured load time, memory and rendering
behavior. Existing static-loader triangle/attribute/resource checks do not establish
car-design fidelity. Refinement tolerances, feature segmentation and budgets are
implementation parameters to measure and report, not missing user authorization.
[Static loader](../dealership/editable-glb.mjs)

## Evidence limits

Primary-source excerpts were screened and factual claims verified with Jev. The
baseline includes code inspection and one committed GLB JSON inspection. No visual
comparison, performance benchmark, reconstruction, mesh refinement or test run was
performed by this research subtask. In-game fidelity and original-PS2 reinsertion
are outside the selected scope; neither source reconstruction nor a plausible
remaster is a blanket guarantee of exact real-car geometry.
