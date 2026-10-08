# Pass-4/5 source Headers and the pass-4 texture (issue #21)

The committed receipt [pass-source-join.json](evidence/vu-dispatch/pass-source-join.json)
covers all **37 aligned pass-4 draws and 63 aligned pass-5 draws**. Each row records
its retained descriptor index/address, GS transfer, car, Header index/offset/raw
bytes, flag word, source-plane offsets/hashes, and active GS binding. Pass-4 rows
also identify the sampled texture. These are content joins between race95 retained
EE memory and the race94 GSDump, **not proof of same-frame execution** (ADR 0001).

Six models are loaded: COBRA, CROWN_VICTORIA, FOCUS_SVT, LIGHTNING_SVT,
POWERSTROKE and THUNDERBIRD_MOVIE. All 100 target draws join to **COBRA**. The
other five loaded cars do not acquire optional-pass coverage from this receipt.
The verifier independently locates model bases in pinned EE bytes, reparses the
committed source models, requires a unique positional Header match for both REF
planes/count, checks all referenced six-/four-byte/UV-plane bytes, and checks the
saved Header declaration against that match. The existing handler comparison
also checks retained descriptor fields and inherited geometry content against the
aligned dump draws. It does not rename parts or resolve unmatched descriptors.

## Conditional Header rule

`FUN_0021bf28` maps source Header bit `0x10` to effective bit `0x80`, and source
bit `0x08` to effective bit `0x40`. In `FUN_0021c3e0` the normal-row arm emits:

- Pass 4 when `(effective_flags & 0x88) == 0x80` and its per-draw global enable is set.
- Pass 5 when `(effective_flags & 0x48) == 0x40` and its per-draw global enable is set.

Both required source bits and effective predicates hold on **100/100** target
draws. This establishes eligibility, not sufficiency from Header flags alone.
Runtime context can suppress optional passes; a paused global is not the enable
value at an earlier retained draw. The receipt pins the typed inventory, executable
and five relevant function exports, and checks their inventory instructions against
ELF load segments. Function names remain address labels. Reflection/specular are
readings of the handler arithmetic, as in `vu-handler-dump.md`.

## Texture identity and origin

All 37 pass-4 draws bind `TEX0_1 = 0x5e0a129c0`: **TBP0 `0x29c0`, TBW 4,
PSMCT16S (`0x0a`), 256×128**. Their texture has no car texture index or source
library name; the receipt calls it `view-render-target-0` as a descriptive label.

The retained global at EE `0x28f1b0` points to texture object `0x3b9bf0`, also
found in the first view-table slot at `0x2907b0`. The TEX0 emission in
`FUN_0021b850` reconstructs the same binding from that object's fields. The
object lies outside all six loaded model byte ranges; none of their parsed car
texture libraries has a 256×128 image. The view-slot lookup (`FUN_00127738`)
and global setter (`FUN_00127730`) are separate from a Header's car texture
index lookup. These facts establish **not a car texture**; they do not identify
an archive filename by guessing texture names.

In the dump itself, **905 geometry tags**, transfers 127 through 5444, precede
the first pass-4 sample at transfer 5456 while `FRAME_1` binds the same memory:
FBP `0x14e` × 32 blocks = TBP0 `0x29c0`, FBW 4, PSMCT16S, and SCISSOR
x=0..255, y=0..127. The first/last tags and raw registers are retained in the
receipt. This is evidence of a view render target being drawn before it is
sampled. This verifier does not rasterize those tags.

## Image export and its boundary

[pass4-retained-target.png](evidence/vu-dispatch/pass4-retained-target.png) is a
committed **opaque RGB preview of that address in race95's captured GS memory**.
Its SHA-256, row-major packed-pixel hash, RGBA hash, GS input pin and origin path
are in the receipt. The decoder extracts VRAM from GS freeze version 9, applies
PSMCT16S addressing, and expands five-bit RGB with shifts. Alpha is set to 255
for inspection; it is not a TEXA/GS-blend calculation.

The layout and addressing follow PCSX2 v2.8.2's
[GSState::Freeze](https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSState.cpp),
[GSTables](https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSTables.cpp), and
[Expand16To32](https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSLocalMemory.h)
(GPL-3.0+). A sparse-pixel fixture independently checks the decoder's block,
column and RGB expansion. The PNG's striped/noisy appearance is retained as
captured; it is not cleaned up or presented as a panorama. **It does not establish
the target's post-render pixel contents when race94 transfer 5456 samples it.**
That requires replay or further execution evidence outside this issue's no-rendering,
no-new-capture scope. Texture identity and memory origin are established separately
from final sampled pixel fidelity.

## Reproduction and controls

```sh
python3 tools/verify_pass_source_join.py
python3 tools/test_pass_source_join.py
tools/check.sh
```

Normal verification reproduces the JSON byte for byte and requires the committed
PNG to equal the derived export. The wrong-Header control assigns another valid
COBRA Header to an aligned draw. The wrong-texture control changes its actual
preceding GS TEX0 write to the pass-5 texture (`0x5dc00a800`), preserving geometry.
Both must fail derivation with their intended Header/texture reason. The regression
also checks Header eligibility, the independent sparse GS-pixel fixture, and rejection
of a changed captured GS file by its hash pin.

No rendering, new states, 29-car extension, bit-exact pass-4 UV/pass-5 S, glass
part naming, ChallGlo blend model or 158 unmatched-descriptor closure is claimed.
