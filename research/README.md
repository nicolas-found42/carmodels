# Research notes

Start with `original-recovery.md` for the current picture, then the note for your topic. Receipts that back
each claim are under `evidence/<area>/`; a note names its receipts inline. The open items below are the
single list of what is not yet established; update it when a note closes or opens one.

| Note | Holds |
| --- | --- |
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
