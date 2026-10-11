# Research notes

Start with `original-recovery.md` for the current picture, then the note for your topic. Receipts that back
each claim are under `evidence/<area>/`; a note names its receipts inline. The open items below are the
single list of what is not yet established; update it when a note closes or opens one.

| Note | Holds |
| --- | --- |
| `gran-turismo-extraction.md` | Native GT1 simulation/arcade models and texture bundles, shared metadata, source provenance, extraction controls and semantic inventory experiments |
| `retro-implementation-2026-10-08.md` | Real dealership Blender edit/export regression, display freshness, retained check evidence, bounded review tooling and explicit CI runtimes |
| `adversarial-teardown-2026-10-08.md` | Executed offline viewer/export teardown, material ownership repairs, failure/keyboard/layout probes, sampling improvement and verification evidence |
| `dealership-split-2026-10-08.md` | Independent editable dealership models/catalog, separate source showcase, rebuild preservation and source hash evidence |
| `silhouette-models-2026-10-08.md` | Source-derived silhouette replacement, all-car geometry checks, browser comparisons and fidelity limits |
| `silhouettes-teardown-2026-10-08.md` | Silhouette-only teardown, resource/literal-text/layout repairs, stationary inspection, decoded icon samples and browser re-attack |
| `original-recovery.md` | Synthesis of the original car recovery: what is decoded, what is a candidate |
| `original-geometry-research.md` | Geometry and texture recovery status, superseded notes, evidence route |
| `format-notes.md` | Car container format: name pool, geometry records, planes, embedded textures |
| `original-ptg-research.md`, `ptg-continuation.md` | Menu icon and livery `.ptg;1` images: decoder status and the continuation |
| `mip-continuation.md` | The 94 extra mip levels stored after the level-zero textures |
| `packet-continuation.md` | The draw path: VIF/VU1/GIF/GS packets, the retained display list, the VU1 dispatch map |
| `pass-source-join.md` | 100 aligned optional-pass draws joined to source Headers; conditional flags, global pass-4 view render target and retained GS image export |
| `vu-handler-dump.md` | Static pass-4/5 decode, 100-draw capture comparison, retained matrix inputs and rounding limits |
| `visualization-libraries.md` | Viewer tooling research with primary-source citations |
| `community-github-stackoverflow.md`, `community-reddit-youtube.md` | Community leads for PS2 model and texture recovery; leads, not evidence |

## Open items

- Redline native extraction is documented in [redline-extraction.md](redline-extraction.md). Static mesh/texture conversion and both library imports are documented in [redline-library.md](redline-library.md); runtime plug-in precedence and game-render fidelity remain open.

- Gran Turismo dynamic wheel behavior, additional colour sets, PS1 rendering fidelity, runtime LOD selection, per-car metadata joins and retail identities remain open. Native extraction is established in `gran-turismo-extraction.md`; static body/first-colour conversion and dealership import are established in `gran-turismo-library.md`; native wheel templates and neutral assembly are established in `gran-turismo-wheels.md`.

- Dealership surface tones use vertex sampling rather than semantic glass/paint segmentation; residual decals and dark details are approximate. Full game-render fidelity remains open.

- Execution trace of CPU, DMA, VIF and VU1 for the dumped frame.
- ADC-producing pass-1/2 branch and flag-set clip stage; static-kick packet origins.
- Pass-4 texture identity and the 100 aligned Header joins are established in `pass-source-join.md` (issue #21). The exported PNG is the retained GS target image; its equality to the dump’s post-render sampled pixels remains open. No replay or broader car-state coverage is claimed.
- Full pass-4 UV/view-normal factor, pass-5 S, and bit-exact arithmetic (279 measured one-ULP T differences); see `vu-handler-dump.md`.
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
- Open (MC3 geometry): default customization parts (hood, bumpers, skirts, lamp lenses, kit libraries) whose meshes sit in the car's own DAT under names without `_stk_` are not attached, so the Corvette Z06 hood opens onto the engine bay and some trim floats. A rule needs the `default.mccarcustom` indices mapped to each car's bone names; see the textures note.
- Open (MC3 appearance): default paint colour (`m_paintColor1` in `default.mccarcustom`), environment/specular/metal-flake shading, runtime logo, licence-plate and damage textures, the one undecoded Bel Air rim base texture, and numeric UV-orientation evidence.
