# Research notes

Start with `original-recovery.md` for the current picture, then the note for your topic. Receipts that back
each claim are under `evidence/<area>/`; a note names its receipts inline. The open items below are the
single list of what is not yet established; update it when a note closes or opens one.

| Note | Holds |
| --- | --- |
| `gran-turismo-4-model-fidelity.md` | Automatic modern dealership remaster with unchanged source reference, native-normal/seam-aware geometry, evidence-based real-car corrections, conservative missing-reference refinement and failed-part fallback |
| `gran-turismo-gt4-guided-upgrades-2026-10-16.md` | Evidence-backed GT4 geometry/artwork transfer, identity and part compatibility, RX-7 trim boundaries, proposed pipeline and unresolved coverage |
| `gran-turismo-1-vs-4-comparison-2026-10-16.md` | Six displayed-name counterpart pairs, measured default-scene body/wheel counts and textures, interactive comparison, and the refined RX-7's different-trim caveat |
| `gran-turismo-preserving-model-improvements-2026-10-16.md` | Preservation boundaries and the separate RX-7 GLB refinement trial; bounded curvature, original artwork and scenes retained, visual acceptance still open |
| `gran-turismo-model-data.md` | Native SPEC and colour-ID joins, all palette variants, retained face/shadow/LOD/wheel inputs, catalog upgrades and unresolved identities |
| `check-performance.md` | Freshness and MC3 preview/wheel-page/PNG profiling, equivalent optimizations, optional TypeSafe advice, labeled wording/holdout experiments and calibration limits |
| `dealership-teardown-2026-10-12.md` | Novice-user dealership teardown, search/filter/layout/request recovery improvements, coverage ledger, original reproductions and final verification |
| `dealership-usability-alternatives-2026-10-12.md` | Primary-source comparison of native search/filter/form/disclosure improvements and deferred fuzzy search, with eligibility limits |
| `enhanced-contact-shadow-2026-10-18.md` | Enhanced-mode ground surface and soft contact shadow for the Recovered inspector (issue #25): the three.js depth-from-under-the-floor technique and its values, a byte-identical Original frame, per-car measured shadow placement and contrast, the uv mapping control, frame-time cost and the limits of a height-field fake |
| `enhanced-presentation-2026-10-18.md` | Optional Enhanced presentation for the Recovered inspector (issue #22): Original default with a byte-identical pre-change render, reflections/neutral tone mapping from the existing asset-free studio, the clearcoat values and why, download and offline-request checks, and the mapping's limits |
| `ai-agent-reverse-engineering-workflow-2026-10-11.md` | Primary-source tool comparisons, a bounded agent workflow, reusable prompts, September 27–October 11 releases and videos, and source-quality checks |
| `semantic-filter-teardown-2026-10-11.md` | Natural-language filter teardown: offline phrase routing, fail-closed model composition fixes, availability reporting, frozen labeled before/after measurements and Jev receipts |
| `gran-turismo-shading-2026-10-11.md` | Why GT cars render shadowed: inverted winding and in-plane stored normals under double-sided lighting, all-728-car rebuild of candidate fixes, headless viewer render matrix, rejected modulation/black-face hypotheses, Jev receipts, ranked fixes |
| `jev-review-escalations-2026-10-12.md` | Why `jev_review` escalated the MCLA change: server scoring read from jev-mcp 0.13.0, controlled experiments, per-file review and evidence fixes, line coverage, results by round and the judge's ceiling |
| `midnight-club-los-angeles-catalogs.md` | Source/editable106-car catalogs, uniform32-bit showcase indices, preservation controls, real viewers and semantic experiment outcomes |
| `midnight-club-los-angeles-previews.md` | Static106-car LOD0 GLBs, stock-slot and attachment readings, source wheel identity, sizing/material approximations, controls and limits |
| `midnight-club-los-angeles-names.md` | UTF16LE UI strings, exact key joins,47 names and59 code fallbacks, parser controls and source pins |
| `midnight-club-los-angeles-decoding.md` | MCLA RSC5/LZX decompression of all 15,480 disc resources, model/skeleton, texture (Xenos untiling, packed mips, DXT) and tuning layouts, part names from streaming maps and level variants, joins, controls and limits |
| `midnight-club-los-angeles-extraction.md` | Native MCLA Xbox 360 car files: XDVDFS, basic-packed XEX2, archive key located in the executable, encrypted RPF3 table, disc-string name recovery with collision rules, per-car selection, controls and limits |
| `gran-turismo-4-previews.md` | GT4 CAR4/MDLS/VIF geometry, Tex1/GS texture and SpecDB decoding sources, preview readings (handedness, -Z front, wheel placement, overlay shapes), 730 previews, static body-alpha corrections and neutral glass fallback, limits |
| `gran-turismo-4-extraction.md` | Native GT4 car files from the encrypted GT4.VOL RoFS table: format sources, decoded volume facts, per-car selection, 730 source-catalog packages, controls and limits |
| `gran-turismo-extraction.md` | Native GT1 simulation/arcade models and texture bundles, shared metadata, source provenance, extraction controls and semantic inventory experiments |
| `retro-implementation-2026-10-08.md` | Real dealership Blender edit/export regression, display freshness, retained check evidence, bounded review tooling and explicit CI runtimes |
| `adversarial-teardown-2026-10-08.md` | Executed offline viewer/export teardown, material ownership repairs, failure/keyboard/layout probes, sampling improvement and verification evidence |
| `dealership-split-2026-10-08.md` | Independent editable dealership models/catalog, separate source showcase, rebuild preservation and source hash evidence |
| `silhouette-models-2026-10-08.md` | Source-derived silhouette replacement, all-car geometry checks, browser comparisons and fidelity limits |
| `under-car-shadow.md` | The 35-car `UNDER_SHADOW` record table, its exported scene membership, its texture alpha, the inspector's candidate alpha blend, and its render before/after measurements |
| `silhouettes-teardown-2026-10-08.md` | Silhouette-only teardown, resource/literal-text/layout repairs, stationary inspection, decoded icon samples and browser re-attack |
| `original-recovery.md` | Synthesis of the original car recovery: what is decoded, what is a candidate |
| `original-geometry-research.md` | Geometry and texture recovery status, superseded notes, evidence route |
| `format-notes.md` | Car container format: name pool, geometry records, planes, embedded textures |
| `original-ptg-research.md`, `ptg-continuation.md` | Menu icon and livery `.ptg;1` images: decoder status and the continuation |
| `mip-continuation.md` | The 94 extra mip levels stored after the level-zero textures |
| `packet-continuation.md` | The draw path: VIF/VU1/GIF/GS packets, the retained display list, the VU1 dispatch map |
| `pass-source-join.md` | 100 aligned optional-pass draws joined to source Headers; conditional flags, global pass-4 view render target and retained GS image export |
| `vu-handler-dump.md` | Static pass-4/5 decode, 100-draw capture comparison, retained matrix inputs and rounding limits |
| `game-shading-inspector.md` | The Recovered inspector's candidate game-shading control: the derived Header table, its recorded stand-ins (camera as eye, view-derived matrix, retained pass-5 light), the executor comparison and its tolerance, and what stays open |
| `visualization-libraries.md` | Viewer tooling research with primary-source citations |
| `community-github-stackoverflow.md`, `community-reddit-youtube.md` | Community leads for PS2 model and texture recovery; leads, not evidence |

## Open items

- GT1 enhanced-model trial: the separate RX-7 comparison is implemented; visual acceptance, refinement tuning and broader coverage remain open. See [the preservation research](gran-turismo-preserving-model-improvements-2026-10-16.md).
- GT4-guided GT1 upgrades: the full-family lexical candidate ledger and separately attributed RX-7 Type R '91 counterpart study are implemented. Identity/region/equipment verification, compatible-region approval and hybrid geometry/artwork transfer remain open. See [the upgrade workflow](gran-turismo-gt4-guided-upgrades-2026-10-16.md).

- Check performance: natural-profile advisor accuracy and false-withholding calibration, chunk-utilization measurements, cross-vehicle MC3 page reuse and deeper packet/normal profiling with source-lifetime and bounded-memory controls remain open; bounded PNG output reuse is measured in [the performance note](check-performance.md).

- AI-agent reversing workflow: recommendations and dated resources are documented in [the workflow research](ai-agent-reverse-engineering-workflow-2026-10-11.md); local harness comparisons, PS2-specific provider coverage and restart/resume behavior remain to be measured.

- Jev patch review: the historical score experiments are retained ([jev-review-escalations-2026-10-12.md](jev-review-escalations-2026-10-12.md)). Independent review resolved the MCLA decoding escalations for [PR39](https://github.com/nicolas-found42/carmodels/pull/39). Preview and index-format reviews retain their own scoped judgments and independent resolutions; an accepted patch does not establish original-game fidelity.

- Midnight Club: Los Angeles: native extraction of 106 cars ([midnight-club-los-angeles-extraction.md](midnight-club-los-angeles-extraction.md)), RSC5/LZX decompression of every disc resource, decoding of every car model, texture, tuning file and streaming map, and names for all car-package files are established ([midnight-club-los-angeles-decoding.md](midnight-club-los-angeles-decoding.md)). Static part assembly, GLB conversion and source/dealership catalog import are implemented ([previews](midnight-club-los-angeles-previews.md)); native model-to-bone bindings, restored joint orientation and composed descendant placement, outward shared rims, normalized wheel-root rebasing, steering/scissor/trunk frames, required DUB exterior selection and a guarded player-bus wheel-family join correct the former translation-only assembly. The all-model browser regression and its remaining static-render limits are recorded with the preview checks; exact UI key joins name47 vehicles ([names](midnight-club-los-angeles-names.md)). Tuning field names, runtime stock configuration, wheel-size fields and complete shared tire/brake ownership, the audio-archive car `vp_se_chv_chp_96` and game-render fidelity remain open.

- Gran Turismo 4: native extraction ([gran-turismo-4-extraction.md](gran-turismo-4-extraction.md)) and static previews in both catalogs ([gran-turismo-4-previews.md](gran-turismo-4-previews.md)) are established. Native factory paint presets now apply Pat0 material/CLUT patches with SpecDB names and ordered variants. Raw ColorChip words are retained without inferred finish flags. Derived material corrections address painted-body alpha cutouts and canonical green-marker window passes in both viewers/downloads while preserving the recovered files; neutral glass remains a preview fallback. Cross-car paint-palette correspondence, reflections and game shading, runtime wheel matrices, race LOD conversion, shared wheel ownership and game-render fidelity remain open.

- Redline native extraction is documented in [redline-extraction.md](redline-extraction.md). Static mesh/texture conversion and both library imports are documented in [redline-library.md](redline-library.md); runtime plug-in precedence and game-render fidelity remain open.

- Ford Racing 2 under-car shadow: every recovered car's `UNDER_SHADOW` record, its exported scene membership, its flat ground plane and its graded white-alpha texture are tabulated in [the shadow note](under-car-shadow.md), and the Recovered inspector rebuilds that record in the default view with the texture alpha as a candidate blend. The game's blend function, colour source and depth behaviour for this quad are not captured by any draw in the repo, so the darker ground-contact appearance the retail screenshots show is not reproduced, and which runtime state draws the quad remains open.

- Gran Turismo exact SPEC-code identities/base specifications and all source colour sets are exported, with supported native colour-ID names; original rendering inputs are retained in each canonical GLB ([model data](gran-turismo-model-data.md)). Racing-equipment joins and unresolved identities, dynamic wheels, PS1 rendering fidelity, runtime LOD selection, second-mask paint semantics, connectivity-based normal orientation and game appearance remain open. Native extraction is established in `gran-turismo-extraction.md`; canonical export policy in `gran-turismo-library.md`; neutral wheel assembly in `gran-turismo-wheels.md`; the measured winding/normal repair in `gran-turismo-shading-2026-10-11.md`.

- Natural-language filter: exact phrases are decided offline and measured in [the filter teardown](semantic-filter-teardown-2026-10-11.md). The dealership now has visible provider disclosure, Enter submission, request recovery and a 35 s UI budget for the existing 30 s provider request, verified in [the dealership teardown](dealership-teardown-2026-10-12.md). Model-path option-order stability, the `original` alias outside Redline, and the source viewer's disclosure/20 s timeout remain open.

- Native paint selection in both showcases preserves recovered presets, supports source-backed scalar paint channels and matching GLB downloads, and records per-car browser selections. MC3 direct paint and MCLA ambient paint bindings have bounded native RGB support. Player-MCLA, MC3 composite/secondary channels, cross-car GT1/GT4/Ford/Redline texture-palette correspondence and original finish formulas remain open. Unresolved bindings are unavailable rather than treated as whole-model tints; see `dealership/dealership/README.md`.

- Recovered inspector presentation (issue #25): Enhanced mode also stands the car on a ground surface with a soft contact shadow under it, placed from the visible geometry's box so it follows the selected car and the geometry choice; Original still builds neither and renders the pre-change frame unchanged. The shadow is a blurred height field under the car, so it cannot self-shadow or be occluded by anything but the car, and the ground and the shadow are presentation props rather than recovered data. See [the contact-shadow note](enhanced-contact-shadow-2026-10-18.md).

- Recovered inspector presentation (issue #22): Original remains the default and renders a byte-identical buffer to the pre-change page; Enhanced adds environment reflections, neutral tone mapping and a uniform clearcoat on textured opaque coverage and is labelled as not the original game's look. The gloss covers tyres until parts can be named, and the reflection content is a procedural room rather than the game's pass-4/5 reflection arithmetic. See [the presentation note](enhanced-presentation-2026-10-18.md).

- Execution trace of CPU, DMA, VIF and VU1 for the dumped frame.
- ADC-producing pass-1/2 branch and flag-set clip stage; static-kick packet origins.
- Pass-4 texture identity and the 100 aligned Header joins are established in `pass-source-join.md` (issue #21). The exported PNG is the retained GS target image; its equality to the dump’s post-render sampled pixels remains open. No replay or broader car-state coverage is claimed.
- Full pass-4 UV/view-normal factor, pass-5 S, and bit-exact arithmetic (279 measured one-ULP T differences); see `vu-handler-dump.md`. The inspector can now display the decoded pass-4 reflection over the 37 joined COBRA Headers and the decoded pass-5 specular over all 63 joined Headers as one labelled candidate, with recorded stand-ins for the eye, matrix, w lane, fixed light, blend law and sampled texture; game-state inputs, captured-frame equivalence, full pass-5 S and coverage beyond those Headers remain open ([the inspector note](game-shading-inspector.md)).
- Glass part naming, and whether header 261 is drawn in other states.
- The untextured-Header colour mapping now drawn in the inspector and GLBs is a candidate
  (issue #18): the captured draw's RGB lanes are black, so the RGB-lane reading of coloured
  untextured Headers (0x661a1a1a and 8 similar words, 42 Headers) is evidence-consistent but unproven; opaque-reading
  Headers keep 0x80808080 grey, and per-Header colours may still need a second reading from a wider capture.
- Numeric selector to human livery label bridge; ordinary car and livery selection capture (cars 1, 5, 4 captured, livery cycling not attempted).
- ChallGlo blend model.
- 158 unmatched retained descriptors, and descriptors outside the six loaded cars.
- The GSDump reference frames (`tools/recover_dump_reference_frame.py`) are the
  screenshots PCSX2 embedded at dump-save time; a replayed-frame cross-check of
  those frames is still open (replay needs a GUI session on the pinned builds;
  see the receipt's `claim_limits`), as is the camera/metric work of issue #27.

- [Branch integration and verification, 2026-10-09](main-integration-2026-10-09.md) — independent dealership/source apps, game-folder migration and complete offline/Blender checks.

- [Gran Turismo library](gran-turismo-library.md): body/texture conversions, independent editable imports, semantic-filter experiments and rendering limits.
- [Gran Turismo wheels](gran-turismo-wheels.md): native template recovery, corrected dimension interpretation, wheel textures, neutral assembly and safe editable upgrades.

- [Redline library](redline-library.md): native static mesh/texture conversion, 128 independent editable imports, verification, semantic-filter experiments and source limits.

## Midnight Club 3 Remix

- [Format research](midnight-club-3-remix-formats.md): DAVE/Dave and Hash archive code, Xbox/plain-TEX leads, live TypeSafe contracts and conversion limits.
- [Native extraction](midnight-club-3-remix-extraction.md): 94 retained vehicle carriers, 4,323 nested members, ordinal-preserving shared resources, independent byte/selection checks and advisory experiments.
- Open: runtime deformation/customization and animation, complete runtime dependency closure, retail identities and visual fidelity. Static PCK conversion, editable previews and diffuse texture decoding are documented in the preview follow-up below.

### Catalog follow-up

- [Catalog integration](midnight-club-3-remix-catalogs.md): 94 verified native
  packages added to the source catalog and independent dealership assets;
  records the native-package catalog state before preview conversion; existing entries were preserved.
- [Preview readiness](midnight-club-3-remix-preview-readiness.md): shared traffic
  mesh/plain TEX structural leads do not decode the 94 PS2 vehicle packages.
  This records the initial failed geometry route; later conversion is documented below. PPF textures and source-backed retail identities remain open.

- [Static previews](midnight-club-3-remix-previews.md): native geometry, source rest frames, shared stock resources, separate GLB conversions, editable dealership integration and retained validation.
- [Primary decoder research](midnight-club-3-remix-preview-research.md): PS2 VIF implementation sources, bounded semantic selection experiments and live TypeSafe contracts.
- [Textures, alpha and artifact surfaces](midnight-club-3-remix-textures.md): diagnosis of the reported Esprit, Corvette Z06 and Chingon artifacts, PCK/`.tex`/`pf05` image decoding, exact material-to-texture binding, display policy, controls and receipts.
- [Tire alpha, reflection and wheel culling](midnight-club-3-remix-tire-alpha.md): recovered base/RGBAQ alpha, PRMODE blending, projected-normal/FOV lookup and additive RGB arithmetic in both showcases; original SD midnight garage inputs, floor passes, panorama overlay and native64 copy replace the synthetic illumination lookup. Native wheel culling removes opposed-cap stripes. The [precision investigation](midnight-club-3-remix-raster-precision.md) closes the selected static capture against pinned official PCSX2 software GS bytes, including original EE/VU execution. Full runtime frame context, other raster profiles and neutral wheel-inner tint fidelity remain outside that contract.
- [Vehicle rendering recovery](midnight-club-3-remix-vehicle-rendering.md): generated-paint VIF/VU/GIF/VRAM controls match complete native RGBA; camera/light upload and three skeleton palettes match original EE RAM. Shared renderer activation, production factory packaging, actor/material/visibility joins, vehicle mip binding/activation and gameplay state/rider animation remain open; current production materials still have viewer approximations.
- Open (MC3 geometry): default customization parts (hood, bumpers, skirts, lamp lenses, kit libraries) whose meshes sit in the car's own DAT under names without `_stk_` are not attached, so the Corvette Z06 hood opens onto the engine bay and some trim floats. A rule needs the `default.mccarcustom` indices mapped to each car's bone names; see the textures note.
- Open (MC3 appearance): active-default precedence and preset-index-to-RGB conversion (explicit `m_paintColor1` customization vectors are now retained and selectable on proven direct paint shaders), environment/specular/metal-flake shading, runtime logo, licence-plate and damage textures, the one undecoded Bel Air rim base texture, and numeric UV-orientation evidence.
