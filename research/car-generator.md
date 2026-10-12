# Learned car generation — WIP

**Paused at the owner’s request on 2026-10-11.** The owner reported weird projected textures and bubbly body geometry during the blind review. Generated outputs now use solid body paint and dark wheels, with no texture maps. Geometry quality remains unresolved; this branch is a development checkpoint, not an accepted completion of issue #35.


Issue [#35](https://github.com/nicolas-found42/carmodels/issues/35) adds an editable static-car generator to the dealership. Its public Python boundary is `Generator.prepare/train/generate/save/rebuild`; numerical geometry stays in the project-local generator environment. The existing stock-Python server runs one cancellable worker and applies its localhost Host, Origin and request-size guards to generation, confirmation and add-only saving.

## Dataset and representation

Preparation considered the 985 editable dealership rows without changing their catalog or source GLBs. The final manifest accepts **316 distinct canonical body grids**: 146 Gran Turismo, 83 Redline, 69 Midnight Club 3 Remix and 18 Ford Racing 2. It keeps **64 uncertain candidates** outside training and records **605 exclusions**: 552 duplicate shapes, 45 failed four-wheel checks, four bodies outside the aligned domain and four TypeSafe class exclusions. The latter are the APC, AlluBus, Bugatti Type 35C GT and Formula 1 model. Every retained entry carries its GLB SHA-256, canonical SDF hash and measured wheel parameters.

Bodies use +X forward, +Y up and +Z lateral, ground Y=0 and wheelbase 2.5. The native +Z-front games and MC3's -Z-front frame are rotated into this convention. GT/Redline/MC3 wheel groups come from native part metadata/names; FR2 groups use circular, thin, low, outboard geometry and centre clustering. The default scene supplies GT's first LOD and FR2's tree zero. Canonical bodies are symmetrized into 64³ signed distance grids; this cache is ignored and regenerated from editable GLBs. Exact duplicate canonical grids count once, including differently named archive/paint copies. This definition cannot distinguish sub-voxel shape differences, and it is not a proof that every pair of visually similar cars is a duplicate.

The initial name-only class question accepted an open-wheel Bugatti. Visual inspection exposed that error. Four upward rays from tyre tops now measure body coverage, and a separate Noul asks about excluded classes, explicitly including vintage open-wheel racers. Eligibility is the minimum of car-class probability and one minus excluded-class probability. This excludes the identified racer while retaining four-wheel road-car fixtures. Coverage alone is not a vehicle-class proof. The uncertain band remains available for owner decisions rather than silently accepting or deleting candidates.

## Learning and output

Both methods use the same accepted corpus and held-out split. A rank-16 linear basis supplies the baseline. The conditional 3D VAE uses 16 latent dimensions, three measured proportions and one-hot body-style/era readings; low-probability readings condition on “no match”. Its surface-weighted reconstruction objective and small KL penalty are selected by held-out reconstruction MSE. The training script chooses the best held-out checkpoint, with patience 12 and a requested maximum of 100 epochs. CI only performs fixed-seed inference against committed weights.

Separate ridge regressions learn wheelbase, track width and wheel radius from each method's body embedding. Wheelbase is constant in the canonical frame; the other targets vary with the corpus. The nearest real wheel set supplies mesh/UV/material detail, and its geometry is scaled and placed from the learned layout with all four tyre bottoms at ground level.

Marching cubes rebuilds the sampled grid. A shared radial section template supplies 10,102 body vertices, UVs and end caps. The duplicated UV seam is exactly coincident geometrically; validation welds that seam and requires a closed surface with consistent winding, bilateral symmetry, four ground contacts and the existing embedded static GLB profile. The initial implementation projected nearest-triangle barycentric texture detail below the measured texture-distance threshold and used a classified glass/light atlas above it. The owner found those textures weird, so generation now exports solid material factors with no body or wheel texture maps. Body paint still comes from decoded FR2 menu-icon RGB samples; the projection helper and template classification remain as WIP code/data for future development. These samples do not establish retail paint names. This template fits an enclosing body and can smooth wheel arches, separated details or deep concavities; visual quality requires the blind review.

Novelty measures RMS movement from a method's reconstructed anchor along a seeded learned direction. The UI also reports the separate distance to the nearest actual corpus grid. Recipes retain method, seed, explicit novelty and interpreted constraints; original request text is reference only. Pins cover learned weights, labels, calibration, effective selection/texture settings, source GLBs and the decoded palette. Changed pins stop replay. Source staleness alone emits a retrain warning from offline checks; artifact corruption fails with named mutation controls.

## TypeSafe experiments

The adapter uses Choice for body style/era, Score for ordered shape-word levels and Noul for presence, vehicle eligibility and unsupported parts. Corpus deciles/median map the ordered proportion levels to measured length, height, width and boxiness; that map is geometric calibration, not human validation of word meanings. Request and name strings are bounded data, never instructions. Model bytes, private packages, credentials and raw catalog records are not sent.

The corrected benchmark contains 18 ordinary decoded FR2 cars and four literal excluded-class examples (drag racer, APC, bus and open-wheel Bugatti). Both wording variants classified **22/22** at threshold .85. At that threshold, both variants decided nine compatible decoded body styles and nine eras, with 9/9 agreement in each field. Uncertain readings are omitted from selective accuracy, and those small, name-grounded samples do not establish accuracy on unknown native codes or rendered generated bodies.

| Wording | Input tokens | Output tokens | Reported cost USD | Sum of call latency seconds |
| --- | ---: | ---: | ---: | ---: |
| Brief | 16,576 | 5,648 | 0.000696192 | 1.24185 |
| Grounded | 18,600 | 5,645 | 0.000781200 | 1.08837 |

Threshold sweeps .7/.8/.85/.9/.95, complete distributions and compatible decoded-label comparisons are in `dealership/generator/class-experiments.json`. At .95, grounded class coverage falls to 11/22; .85 retains all 22. Grounded wording remains the production choice because it explicitly limits native identity inference. The .85 positive and .15 negative thresholds leave an uncertain band; the benchmark supports this conservative choice but does not prove a universal operating point. Unsupported-part Noul uses .5 and requests explicit user confirmation before sampling.

The production preparation retained 25 calls (24 car batches plus template classification), 325,912 input tokens, 98,503 output tokens, reported cost $0.013688304 and 9.72347 seconds summed call latency. Identical state/question receipts can be resumed without re-asking the provider. A floating-point tie in Choice probabilities initially failed the parser; a 1e-8 tie tolerance fixes that input error while still rejecting a selected choice with a materially lower probability.

Requests tested include a low/long/boxy 70s coupe, a six-wheeled 70s coupe, an electric motorcycle and vague wording. Their readings, uncertainty, unsupported parts and raw envelopes are retained. The final request suite records the explicit supported-era range; actual corpus coverage is checked in code. A “long” reading below threshold is displayed as set aside instead of forced into a proportion target.

Primary API references: [TypeSafe documentation index](https://docs.typesafe.ai/llms.txt) and [PyTorch modules](https://docs.pytorch.org/docs/stable/nn.html). Score levels are ordinal descriptions; the adapter checks the response legend and weighted score against its probability distribution rather than treating a level score as a probability.

## Measurement and blind calibration

The final CPU training ran 100 epochs in 551.38 seconds and selected the best held-out checkpoint. The texture threshold is 0.0177161 normalized SDF RMS, the 75th percentile of ten held-out nearest-training distances. `quality.json` records the complete per-output measurements:

| Method | Mean held-out SDF MSE | Mean nearest-real distance | Mean generation seconds | Maximum generation seconds | Mean template-fit distance |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shape space | 0.0000567544 | 0.00635914 | 3.24004 | 8.52314 | 0.0256565 |
| Network | 0.000152806 | 0.0113135 | 2.70045 | 11.89753 | 0.0254171 |

The baseline reconstructs these held-out grids more accurately. That result alone does not establish which generated cars look better. All 60 generated review outputs pass bilateral symmetry (maximum 8.01e-16), wheel contact (maximum 5.56e-17), closed welded topology and winding checks. Timings include concurrent local checks and are measurements of this run, not latency guarantees.

Owner review exposed zero normals on unused wheel vertices. The exporter now compacts every vertex attribute through the triangle index map before computing normals. All referenced triangles, UVs and materials are preserved. The review retains its session, order and existing owner mark; its key records old/new geometry hashes and the repair. All 70 exact files pass the real viewer parser. An optional `KHR_materials_variants` mapping on a control model now uses its existing default material; unsupported geometry extensions still fail. These are executable structural/loading checks, not a visual-quality verdict. The blind review contains 30 outputs per method (10 seeded outputs at each of novelty 0/.35/.7) and ten real held-out controls, shuffled with a recorded session and model hashes. No source/method labels appear in the review page. It accepts only all 70 owner marks, retains the complete shuffled key and computes method recognition, automatic-check agreement and TypeSafe selective agreement across thresholds.

The novelty default is the highest tested level where both method groups reach at least .8 recognition and remain within .1 of this reviewer's real-control rate. Before complete owner marks exist, .35 is provisional. The owner started but paused the review; no complete marks or calibrated recognition rates were recorded. The existing local review session shows the earlier textured outputs and must be replaced for the new untextured appearance before finishing calibration. Human rates and a review-calibrated default are **pending**, and are not implied by symmetry or reconstruction scores.

## Limits and remaining work

This is learned static geometry, not a source recovery or original-game render. Labels do not decode retail identity, performance, animation, interiors or damage, and generated catalog rows leave those fields unknown. The basis/network/wheel weights and quality measurements are retained. The initial full check run completed with two UI/check-registry failures, which were repaired in focused checks. A later full run was interrupted at the owner’s pause after 56 checks passed; it is not a green completed suite. Separate generator export/replay checks and Blender checks passed before the final untextured appearance change. A focused smoke run validates both current untextured methods, renderer parsing and byte-identical replay. Complete owner blind-review marks, geometry quality improvements, refreshed appearance review and the final full suite remain unfinished. The research index tracks the unresolved owner recognition and texture-projection assessment. MPS and CPU training can differ numerically; fixed artifacts plus stored recipes, not retraining, support byte-identical replay on the same environment.

## Resume from this checkpoint

- Improve the rounded/bubbly body result, particularly the SDF-to-radial-template fit and preservation of roof, bonnet and wheel-arch features. The owner’s visual judgment takes precedence over the passing symmetry/contact checks.
- Keep the current solid-material appearance unless the owner asks to restore texture projection. Existing quality timing and review assets describe the earlier textured pipeline.
- Recreate a fresh 70-item review after appearance/geometry changes; complete owner marks and derive the novelty default and TypeSafe agreement from those marks. The old local session and browser marks were preserved, but were not accepted as final results.
- Reconcile this note and the research index with new evidence, finish the independent patch/evidence review, and run the complete offline checks before calling #35 done.
