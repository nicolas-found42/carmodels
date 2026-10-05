# Research notes

Start with `original-recovery.md` for the current picture, then the note for your topic. Receipts that back
each claim are under `evidence/<area>/`; a note names its receipts inline. The open items below are the
single list of what is not yet established; update it when a note closes or opens one.

| Note | Holds |
| --- | --- |
| `original-recovery.md` | Synthesis of the original car recovery: what is decoded, what is a candidate |
| `original-geometry-research.md` | Geometry and texture recovery status, superseded notes, evidence route |
| `format-notes.md` | Car container format: name pool, geometry records, planes, embedded textures |
| `original-ptg-research.md`, `ptg-continuation.md` | Menu icon and livery `.ptg;1` images: decoder status and the continuation |
| `mip-continuation.md` | The 94 extra mip levels stored after the level-zero textures |
| `packet-continuation.md` | The draw path: VIF/VU1/GIF/GS packets, the retained display list, the VU1 dispatch map |
| `vu-handler-dump.md` | Static pass-4/5 decode, 100-draw capture comparison, retained matrix inputs and rounding limits |
| `visualization-libraries.md` | Viewer tooling research with primary-source citations |
| `community-github-stackoverflow.md`, `community-reddit-youtube.md` | Community leads for PS2 model and texture recovery; leads, not evidence |

## Open items

- Execution trace of CPU, DMA, VIF and VU1 for the dumped frame.
- ADC-producing pass-1/2 branch and flag-set clip stage; static-kick packet origins.
- Full pass-4 UV/view-normal factor, pass-5 S, and bit-exact arithmetic (279 measured one-ULP T differences); see `vu-handler-dump.md`.
- Glass part naming, and whether header 261 is drawn in other states.
- Numeric selector to human livery label bridge; ordinary car and livery selection capture (cars 1, 5, 4 captured, livery cycling not attempted).
- ChallGlo blend model.
- 158 unmatched retained descriptors, and descriptors outside the six loaded cars.
