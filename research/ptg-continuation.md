# PTG icon and livery continuation

This continuation recovers the original car icon and livery image payloads from
the reference-bound `.ptg;1` corpus. It does not claim that these separate
menu assets are model UV textures, or that it has recovered the in-game car
composition. The source archive, checked-in reference copy, and manifest pin
all 171 inputs. PAL traces close the CARS reward-icon parser-to-UI sprite route
conditionally; actual menu output and the LIVERY draw/load route remain open.

## Current result

`tools/recover_car_ptg.py` now validates all 171 manifest-listed CARS and
LIVERY PTGs against their source archive and checked-in reference SHA-256,
then parses every tile descriptor using the PAL executable's dimension and
format-table arithmetic. The source set comprises 171 images and 4,104 tile
descriptors. All descriptors compute to 32×32, format 1, 32 bits per pixel,
and 4,096 payload bytes. The parser checks each record's serialized U/V
extent, each descriptor's measured padding/sentinel profile, its calculated
payload bounds, and the final file end. It emits one image assembled from the
source-ordered tile payloads at the same-index record's raster cell, clipping
edge cells to the header width and height.

Each source has two PNG exports: `.raw-alpha.png` preserves every source
alpha byte, and `.png` scales the source alpha by 2 up to 255 for a conventional
preview. The four-byte order is supported as RGBA: the game loader selects
the 32-bit GS texture path (PSMCT32 code 0), and PCSX2's primary GS renderer
interprets each 32-bit word as `0x00AA00BB00GG00RR`, which corresponds to
RGBA byte order on the little-endian PS2. The source alpha values are all in
the measured 0–128 range; alpha scaling is a preview transform, while raw
bytes remain preserved. This channel interpretation does not establish the
exact menu blend/composite without an observed car-selection render.

The concrete loader trace is documented in
[`evidence/ptg-continuation/loader-trace.md`](evidence/ptg-continuation/loader-trace.md).
The separate LIVERY callsite and GS alpha-state trace is in
[`evidence/ptg-continuation/livery-and-alpha-source-trace.json`](evidence/ptg-continuation/livery-and-alpha-source-trace.json),
with its Jev receipt at
[`evidence/ptg-continuation/jev-livery-alpha-source-trace.json`](evidence/ptg-continuation/jev-livery-alpha-source-trace.json).
Fresh source export review is separately verified in
[`evidence/ptg-continuation/jev-fresh-export-livery-alpha.json`](evidence/ptg-continuation/jev-fresh-export-livery-alpha.json).
The CARS `.PSD` callback aliases to `.ptg;1`; its type-2 asynchronous read is
decompressed by `FUN_00101690`, and `FUN_0022acc8` parses the resulting bytes.
That parser creates same-index record/descriptor links and assigns the
sequential pixel-body pointers. The primary decompilation and instruction
pins are from PAL executable SHA-256
`216711210898aee296eed73d0776e7f733bac04c334002683bce769c86beea95`.
The separate model-texture research already pins PCSX2 GS sources at
revision `81526d4dc7cc70e4ae75abb35a789417456c6d43`; see the
[upload-audit source pins](../../../reverse-engineering/notes/evidence/fr2-texture-upload-audit/source-pins.json).

## MATRIX thumbnail PTGs and CLUT lookup

The archive also contains 136 `GRAPHICS/GAME/MATRIX/*.ptg;1` assets. Their
names join all 136 livery variants, and the primary parser path identifies
format 3 as indexed 8-bit texture data with a 256-entry palette. The recovered
assets comprise six 32×32 tiles in a 3×2 grid covering a 90×64 image; the last
column is clipped to 26 pixels. The decoder keeps original archive PTGs beside
its image exports. Both direct-linear and GS-swizzled palette outputs are
retained for audit.

The palette order is now source-derived. In `FUN_0022f948`, format ID 3 selects
the table row at `DAT_00232dbe`: indexed flag 1, PSM selector `0x13` (PSMT8),
and CPSM selector 0 (PSMCT32). `FUN_00220fe0` uploads tile bytes as PSMT8 at
8 bpp, and uploads the palette as an unpermuted 16×16 PSMCT32 image at 32 bpp.
The literal `0x20` in that palette call is the 32-bit depth argument, while
the transfer's DPSM argument is 0. `FUN_00220d60` sets TEX0 CSM=0, CSA=0, and
CLD=1. PCSX2's pinned CSM=0 path calls this CSM1 and its PSMT8/CT32 lookup
swaps CLUT address bits 3 and 4. Thus each indexed pixel `i` reads palette
entry `(i & ~0x18) | ((i & 8) << 1) | ((i & 16) >> 1)`. The official
[PCSX2 v2.8.2 GSClut.cpp](https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSClut.cpp)
and [GSTables.cpp](https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSTables.cpp)
provide the independent GS implementation trace. All 136 archive-matched
thumbnail comparisons also favor the bit-swap export, but their substituted
JPEG tables make that only corroboration, not the basis of the mapping.

The ELF-bound call sites, export and executable hashes, exact transfer/TEX0
fields, reproduction limits, and focused Jev receipts are recorded in
[`matrix-gs-csm1-contract.json`](evidence/ptg-continuation/matrix-gs-csm1-contract.json).
The MATRIX recovery receipt is
[`recovered-matrix-ptgs.json`](evidence/matrix-continuation/recovered-matrix-ptgs.json);
it retains 136 original PTGs and 544 independently validated preview files.
The thumbnails are associated menu/livery images; this recovery does not
identify them as car-model UV textures or establish a live menu render.

## Reproduction and validation

Run from this directory:

```sh
python3 tools/recover_car_ptg.py --verify-only
python3 tools/recover_car_ptg.py
```

The first command rechecks archive, reference, manifest and all source
descriptor/body bounds without rewriting images. The second regenerates the
PNGs and independently checks PNG chunk CRCs, image dimensions, zlib payloads,
and decoded image bytes against the assembled source bytes. The saved
[`archive layout receipt`](evidence/ptg-continuation/archive-layout-validation.json)
records 171/171 archive-bound inputs and 4,104 source-computed descriptors.
The
[`recovery receipt`](evidence/ptg-continuation/recovered-car-ptgs.json)
records all output hashes and per-descriptor calculations. A separate
macOS `sips` image-reader pass recognized all 342 PNGs and their expected
dimensions with no failures; see
[`independent PNG reader receipt`](evidence/ptg-continuation/png-independent-reader-validation.json).
The earlier 4,104-chunk scan of the loading-stage memory dumps found no exact
4,096-byte tile matches; it is explicitly a pre-car-menu negative control,
not evidence against these assets. A second state-specific scan searched all
171 exact, decompressed serialized files in the 32 MB EE memory capture from
the red Mustang quick-race checkpoint `.94`; none matched in full. Its receipt
[`race94 EE scan`](evidence/ptg-continuation/race94-ee-ptg-scan.json) is
limited to whole-file linear residency in that race state and says nothing
about a menu capture or transformed tile data.

Jev / TypeSafe receipts are preserved beside the corresponding evidence.
[`jev-descriptor-consumer-decision.json`](evidence/ptg-continuation/jev-descriptor-consumer-decision.json)
verifies the descriptor-byte facts and decoder limits, and records Jev's
bounded next-experiment recommendation. These judgments are supporting
signals; the input bytes, source code and deterministic checks establish the
technical measurements.

## Open validation gap

The serialized descriptors contain `0xDDDDDDDD` at `+0x2c` and `0xDD` at
`+0x35`. `FUN_00222358`, a texture upload routine, treats runtime fields at
those offsets as an additional-mip pointer and count. The sentinel issue is
route-dependent. For CARS reward buttons, the source join now connects the
dynamic handle to `BUTTON1` / `BUTTON2` class 3; the button renderer reaches
`FUN_0015e2e0` → `FUN_00220678` → `FUN_0021fd50` → `FUN_00220fe0`, whose upload
reads `+0x28`, `+0x34`, and `+0x38` but not `+0x2c/+0x35`. The path is still
conditional on asynchronous completion and does not establish output pixels
in the captured runtime state.

The LIVERY template VA `0x25a1d0` is passed by `FUN_00173938` to
`FUN_0015b280` at `0x174370`. Raw ELF instructions correct the older
pseudocode-based claim that the first argument is unused: `FUN_0015b280` stores
`a0` at `sp+0x170`, reloads it at `0x15b4d8`, and copies it into the property
pack at `sp+0x98` after key `0x6d`. Type 1 is registered to `FUN_0014bed0`,
which sends properties to `FUN_00145b08`; its key-`0x6d` setter
`FUN_0014e298` stores the supplied string in the type-1 UI object's dynamic
string buffer at `+0x140`. This closes this particular call as UI string
initialization, not as a LIVERY PTG load/parse/upload route. The actual
consumer route for the 136 LIVERY PTGs remains unresolved. Raw ABI offsets and
source identities are in [`livery-ui-string-contract.json`](evidence/ptg-continuation/livery-ui-string-contract.json); Jev's raw-string check is in [`jev-livery-ui-string-contract.json`](evidence/ptg-continuation/jev-livery-ui-string-contract.json).

For alpha, the earlier trace mislabeled the `FUN_00220d60` register `0x3f`
packet as TEST state and said the sprite path had no `ALPHA_1` activity. The
pinned GS register definitions identify `0x3f` as TEXFLUSH, while `0x47` is
TEST_1 and `0x42` is ALPHA_1. Fresh raw instructions for
`FUN_0021fd50` show it queues tokens for `0x47`, `0x4e`, `0x44`, and `0x42`
with packed words between them; `FUN_00220d60` separately emits TEXFLUSH and
texture setup. The presence of an `0x42` token proves ALPHA_1-related packet
activity, but the complete data/address packing and effective draw state are
not yet closed, so this is not a final blend equation or a verified output
alpha conversion.

The wrapper's raw MIPS setup is now recorded rather than treating its six-item
decompiler call as a C ABI. At `0x220678`, it stores incoming `a1` at its
stack offset 0, sets `a1=1`, moves incoming `a0` into `a3`, sets `a0=a2=0`,
masks the saved `a1` to 16 bits into `t0`, then calls `FUN_0021fd50` with delay
slot `t1=1`; it also clears `f16` and copies zero to `f17/f18`. The exact UI
renderer-provided `a1` and surrounding FPU inputs still need to be traced at
each class-3 caller. `FUN_0021fd50` halves its packed vertex-color channels
with `(component+1)>>1`. `.raw-alpha.png` preserves source bytes; `.png`
doubles alpha only as a conventional preview, not as a proved game-exact
composite.

The current indexed menu checkpoint at
[`menu-state-identity.json`](evidence/continuation/runtime/menu-state-identity.json)
is post-profile and has no in-race car. The earlier `.94` screenshot shows an
in-race red Mustang. Neither verifies recovered CARS or LIVERY menu pixels.

### Menu98 GS upload trace

The finalized PCSX2 2.8.2 GS dump for menu98 was parsed as a bounded GSDump
event stream, including packed GIF tags and their A+D register writes. The
parser consumed all 10,747 Transfer events and ended exactly at byte
16,023,665. It found 1,562 IMAGE tags, of which 150 carry 4,096-byte
32x32 PSMCT32 host-to-local transfers. The target packet begins at dump event
offset `0x96a84b` (9,873,483): its 256-QWC IMAGE payload starts at
`0x96a861` (9,873,505). Its state has `BITBLTBUF=0x129dd00000000`,
`TRXPOS=0`, `TRXREG=0x2000000020`, and `TRXDIR=0`, which decodes to base
block `0x29dd`, DBW 1, PSMCT32, destination `(0,0)`, and a `32x32` host-to-local
transfer.

Three 64-byte raw prefixes from LIVERY source tiles occur inside this IMAGE
payload at byte offsets `+1824` and `+1952`. None has a matching 4,096-byte
continuation, and no complete source tile matched the raw dump or the earlier
aligned-origin PSMCT32 VRAM scan. These prefixes are not tile identifications.
The offsets are pixel-aligned at `(x=8,y=14)` and `(x=8,y=15)` in the
32x32 payload (128 bytes per row), rather than at a tile origin. Across all
3,136 unique source tile bodies, a bounded candidate search tested all 24
component permutations and raw, doubled/clamped, opaque, and zero alpha
options. It found 66 repeated/displaced 64-byte prefix positions across the
same three tile candidates; the six RGB permutations preserve the same prefix
because their alpha bytes remain unchanged. No tile prefix matches payload
origin under this transform set. For the source-origin crops implied by the
two original prefix positions, all 18 matching candidate transformations
diverge immediately after the first 16 pixels; none completes the 24x18 or
24x17 in-bounds crop. This is a stronger bounded negative, but does not cover
arbitrary alpha/color arithmetic or an arbitrary source crop origin. The
pixel coordinates, transformation inventory, and crop check are detailed in
[`menu98-gif-transfer-trace.json`](evidence/ptg-continuation/menu98-gif-transfer-trace.json).
The same bounded search was then run across all 150 32x32 PSMCT32 uploads.
It found 14,220 transformed 64-byte prefix candidates in 44 payloads and
tested the full remaining in-bounds source-origin crop for each. None matched
through the payload edge; the longest initial run before a mismatch was 27
pixels. These repetitive short hits remain ambiguous. This broader search
still excludes arbitrary transforms and crops whose source-tile origin lies
outside the upload. Jev/TypeSafe verified the candidate counts and zero full
crop matches, but gave a low-confidence review verdict on whether enumeration
covered all packets; the local parser did build windows for all 150 before
matching prefixes. It rejected any claim of global PTG absence from this
single state. The complete raw dispositions are in
[`jev-menu98-gif-transfer-verification.json`](evidence/ptg-continuation/jev-menu98-gif-transfer-verification.json).
The new trace establishes packet semantics and one GS destination, but does
not join this upload to a source PTG descriptor, a full decoded tile, or one
of the six visible thumbnails. Color/alpha remapping and alternate transfer
coordinates/pitches remain outside the exact-byte tests. The stream counts,
register values, source offsets, PCSX2 source references, and explicit limits
are preserved in
[`menu98-gif-transfer-trace.json`](evidence/ptg-continuation/menu98-gif-transfer-trace.json),
linked from the earlier
[`menu98-ptg-gs-scan.json`](evidence/ptg-continuation/menu98-ptg-gs-scan.json).
Jev/TypeSafe verified the exact packet dimensions and register interpretation
against the trace, corroborated the bounded transformed-candidate counts,
and contradicted the proposed claim that this transfer is already joined to
a visible thumbnail. Its focused receipt is
[`jev-menu98-gif-transfer-verification.json`](evidence/ptg-continuation/jev-menu98-gif-transfer-verification.json).

### Menu98 sprite, upload and PTG join (2026-10-05)

The earlier negative above searched only the 171 car/livery PTGs (and transformed variants). Searching **all 548 `.ptg;1` files** of the PAL image for every menu98 IMAGE payload of at least 512 bytes finds untransformed exact substrings: 56 of the 150 PSMCT32 32×32 uploads are exact 4,096-byte tile bodies of the seven `GRAPHICS/GAME/CHALL/{living,movie,svt,concept,offroad,custom,stock}.ptg;1` files (four tiles each at file offsets 400, 4,496, 8,592 and 12,688; a 2×2 grid, 56×56 image, every tile uploaded twice in the dump), 264 of 276 PSMT8 32×32 uploads are tile bodies of `GRAPHICS/GAME/` PTGs (72 of them the six `MATRIX` files below), and 446 of 668 16×16 PSMCT32 uploads (palettes) are exact PTG substrings. The previously studied target upload (event offset `0x96a84b`, DBP `0x29dd`) is `living.ptg` tile 0 at file offset 400. Tile bodies begin at `80 + 80·count + 4,096·i` for count 4, i.e. the descriptor data order that `0022acc8`/`00220fe0` set up. The remaining 94 PSMCT32 32×32 uploads and every upload of 64×64 or larger are not matched and no claim is made about them.

Tracking GS state through the dump (`tools/join_menu98_sprites_to_ptg.py`, [`menu98-sprite-ptg-join.json`](evidence/ptg-continuation/menu98-sprite-ptg-join.json)) decodes 1,034 sprite draws (PRIM type 6, packed UV/RGBAQ/XYZ2). 902 sample a texture whose latest earlier upload at that TBP0 is an exact PTG tile body. All have TEX0 TFX=0 (modulate), TCC=1, FRAME_1 `0xa0050`, ALPHA_1 `0x44`, ABE=1 and XYOFFSET_1 `0x700000006c00` (OFX 1728, OFY 1792). A CHALL tile sprite uses UV (0,0)–(512,512) in 1/16-texel units over about 35.2 screen pixels for 32 texels; the clipped right and bottom tiles use UV 384 (24 texels), matching the 56×56 image. The framebuffer-to-screenshot mapping is **fitted, not assumed**: `x_s = x + 1`, `y_s = 0.9375·y + 1` (480/512 line scaling), chosen by grid search on the even-indexed CHALL PSMCT32 sprites only (mean absolute RGB error 15.95 over opaque texels, predicted as texel × vertex RGB / 128). The rows below score every family with that single mapping.

| Family (not used for fitting unless stated) | Sprites | Mean abs RGB error | Shifted ±8 px controls | Swapped-tile control |
| --- | --- | --- | --- | --- |
| CHALL PSMCT32 (fit used even half) | 56 | 16.9 | 67.2–73.7 | 75.2 |
| MATRIX PSMT8 + CLUT (independent family and format) | 72 | 17.6 | 40.3–56.2 | 50.4 |
| Other `GRAPHICS/GAME` PSMCT32 | 412 | 23.9 | 46.5–70.7 | 48.1 |
| Other `GRAPHICS/GAME` PSMT8 | 312 | 21.9 | 23.4–28.1 | 28.4 |
| `ChallGlo` PSMT8 glow | 50 | 119.6 | 117.0–118.8 | 117.8 |

**What the screenshot shows.** The seven round **theme icons** along the top (star, camera, SVT, thought bubble, rocks, wrench, chequered flag) are the seven CHALL PTGs, left to right, at screenshot x 94–537, y about 121–177. The **six car thumbnails** in the “Living Legends” strip are the six `GRAPHICS/GAME/MATRIX` PTGs `49couped`, `must68d`, `tbirdd`, `fortyd`, `tbird22d` and `fordgtd`, left to right at x 114–528, y about 249–299 (six 32×32 PSMT8 tiles each, drawn twice). For all six the uploaded 16×16 PSMCT32 palette is byte-equal to the PTG's 1,024-byte palette at offset 576, the lookup uses the source-derived bit-3/4 swapped index (CSM1), and mean RGB error is 13.1–19.9 against 40–56 for shifted mappings. The earlier prose that called the six visible car thumbnails unmatched was looking in the wrong PTG family: these thumbnails are MATRIX, not CARS/LIVERY. The lock overlays are `Locked.ptg`/`Unlocked.ptg`. `ChallGlo` (a glow) is **not** explained by the opaque-modulate model (error equals the controls), so its blend remains unresolved; the weaker two generic `GRAPHICS/GAME` rows have smaller margins because many are flat bars, scaled or alpha-blended.

Limits: this is one menu state; the colour model ignores filtering and alpha blending (only opaque texels are scored); the join identifies PTG tile bytes and where they are drawn but not the human labels of the thumbnails or any numeric→livery-label bridge (MATRIX stems join the 136 livery variants by filename only); the car (CARS/LIVERY) PTG consumer is still not observed in this capture. Jev verified the six-MATRIX statement at 0.89 and judged the ChallGlo explanation unsupported (0.80); see [`jev-retained/08-verify-continuation-claims.json`](evidence/packet-continuation/jev-retained/08-verify-continuation-claims.json).

### Generic texture registry consumer does not close the car-PTG edge

The saved PAL source export resolves the producer and context of one
`FUN_00222358` upload loop. `FUN_001d3468` looks up named resources including
`SMOKEANDDUST`, `TYRE_SKID`, `SUN_FLARE`, `HEADLIGHT_FLARE`, `TYRE_SMOKE`,
`EXHAUST`, `GRASS`, `SPARK`, `SPRAY`, and `FIRE`, then registers selected
objects in eight slots through `FUN_00228df0`. `FUN_00228ed8` iterates the
resulting unique-object list and calls `FUN_00222358` for each descriptor.
These names and the producer/consumer relation are backed by raw PAL
executable strings and saved function exports. Jev verified the registry
producer relation (0.87 confidence) and upload-loop relation (0.98); it marked
the proposed inference that this proves CARS PTGs reach the loop unsupported,
with the supplied trace explicitly showing no connecting edge (0.96
confidence). The full receipt and source hashes are in
[`race-texture-registry-trace.json`](evidence/ptg-continuation/race-texture-registry-trace.json).

This narrows the source-side gap: it shows the uploader operating on a
specific named set of effect resources, but does not show those resources are
CARS PTG descriptors or that this loop draws the car selector. The CARS
reward-button parser-to-upload edge is established separately below; actual
menu pixels and the LIVERY texture route remain unvalidated.

The saved exports expose a separate path that does initialize mip records:
`FUN_0011ed90` formats a `%s.ps2` resource and calls `FUN_0022ba30`, whose
body builds `+0x2c` mip pointers using `+0x35` counts. Exact-call search of
the saved export set found no other caller, and this path is the parser for a
different `.ps2` container. Jev verified that call path and contradicted the
claim that it processes CARS PTGs (0.98 confidence). The other direct parser
caller `FUN_0022aed8` is reached from `FUN_001d3a78` with an inline buffer and
resource type 9; its saved caller path draws a generic texture object. Neither
branch establishes an intermediate CARS PTG transformation. See
[`mip-construction-path-comparison.json`](evidence/ptg-continuation/mip-construction-path-comparison.json).

The canonical recovered-asset index verifier has since been strengthened.
The current check derives exact expected records per car from producer
receipts and enforces schema, status, fidelity flag, and the three declared
limits for both index and manifests. Its in-memory rehashed cross-car model
swap and declaration mutations are rejected, as is a corrupted manifest
hash. `python3 tools/verify_recovered_asset_index.py` currently passes for 35
cars and 2,579 assets. Jev/TypeSafe's review escalated because the
blast-radius rubric had low confidence; its bounded claim check verified the
per-car ownership and declaration-control paths but did not support any
game-render-equivalence claim. Code execution and direct inspection remain
the basis for the integrity result. The current tool hash and Jev disposition
are recorded in
[`independent-continuation-review.json`](evidence/ptg-continuation/independent-continuation-review.json)
and [`jev-index-verifier-recheck.json`](evidence/ptg-continuation/jev-index-verifier-recheck.json).

The canonical recovered-asset index verifier has since been strengthened.
The current check derives exact expected records per car from producer
receipts and enforces schema, status, fidelity flag, and the three declared
limits for both index and manifests. Its in-memory rehashed cross-car model
swap and declaration mutations are rejected, as is a corrupted manifest
hash. `python3 tools/verify_recovered_asset_index.py` currently passes for 35
cars and 2,579 assets. Jev/TypeSafe's review escalated because the
blast-radius rubric had low confidence; its bounded claim check verified the
per-car ownership and declaration-control paths but did not support any
game-render-equivalence claim. Code execution and direct inspection remain
the basis for the integrity result. The current tool hash and Jev disposition
are recorded in
[`independent-continuation-review.json`](evidence/ptg-continuation/independent-continuation-review.json)
and [`jev-index-verifier-recheck.json`](evidence/ptg-continuation/jev-index-verifier-recheck.json).

The CARS callback's UI object join is now source-proven. `FUN_00181f38`
formats `BUTTON1` and `BUTTON2` from the `BUTTON%d` template, looks them up
under root resource `UIREWRD.UI`, and stores their pointers at `gp-0x5370`
indexes 0 and 1. The `FUN_001820f0` callback walks reward items, calculates
the same index as `s7 = item_index * 4`, and uses it both for the button-node
pointer and the returned-resource-handle slot. Its one-based type-1 jump-table
entry at `0x25d2f0` selects the `CARS\%s.PSD` case at `0x182220`. That case
starts the type-2 texture load. On completion, the callback loads the
same-index button object and resource handle, then dispatches through the
button object's class-indexed setter. The archived `REWRD.UI;1` declares both
buttons as class 3 (`UI_TYPE_BUTTON`), while `GLOW` is a separate class-4
graphic with static `GRAPHICS\GAME\CARGLOW.PSD`.

For class 3, `FUN_00159610` installs setter `FUN_0014d728` at node `+0x154`
and renderer `FUN_00159080`. That renderer calls `FUN_0015e2e0` →
`FUN_00220678` → `FUN_0021fd50` → `FUN_00220fe0`. The source sprite loop
uses the parsed cell table and descriptors; `FUN_00220fe0` uploads base
pixels from descriptor `+0x28`, format `+0x34`, and dimensions `+0x38`, without
reading `+0x2c/+0x35`. Thus the serialized mip sentinels do not block the
CARS reward-icon base-image route, provided the asynchronous request and
completion conditions succeed. The same-index cell/descriptor relationship,
row-major draw steps, and partial edge-cell extents also match the decoder's
source-checked composition. This static wiring does not prove runtime
reachability in a particular emulator state, actual output pixels, or alpha
blending. The source hashes, class/object fields, and full paths are recorded in
[`reward-ui-graphic-path-trace.json`](evidence/ptg-continuation/reward-ui-graphic-path-trace.json),
with a separate Jev verification receipt at
[`jev-reward-ui-graphic-path-verification.json`](evidence/ptg-continuation/jev-reward-ui-graphic-path-verification.json).
The earlier handle receipt
[`reward-ui-handle-linkage.json`](evidence/ptg-continuation/reward-ui-handle-linkage.json)
records the callback-to-setter handoff and its limitations.

## Ordinary car-selection capture (2026-10-05)

Drove the headless game with ordinary controller input through the hidden
browser → noVNC canvas (key delivery proven: Space toggled PINE status 1→0).
Loaded slot 98, unpaused to the Living Legends theme screen; Cross on the
highlighted car opened the VEHICLE/TRACK/TYPE/STATUS detail panel. Three
labeled screens were saved to new slots with unpacked, hashed members:

- slot 102 (`6e3971…fa47`): car 1, VEHICLE: FORD '49, TRACK: ROUTE 50,
  TYPE: DRIVING SKILLS — thumbnail `MATRIX/49couped.ptg;1` = 49_COUPE.
- slot 103 (`b5e569…1dc5`): car 5, VEHICLE: THUNDERBIRD CONVERTIBLE,
  TRACK: DEER CREEK, TYPE: DRAFTING — `MATRIX/tbird22d.ptg;1` =
  THUNDERBIRD_2002.
- slot 104 (`74acb5…4069`): car 4, VEHICLE: FORTYNINE CONCEPT, TRACK: PORT
  SIDE, TYPE: RACING LINE — `MATRIX/fortyd.ptg;1` = FORTYNINE.

Thumbnail left-to-right order is code-measured from the prior sprite join
(x 113 → 458 across the six MATRIX PTGs); car joins via CARDATA
`VALID_LIVERY` basenames (49COUPED / TBIRD22D / FORTYD). All three cars show
their DEFAULT livery. The six 12-name EE selector tables are static across
captures (record bases `0x233070+type*0x114` unchanged); no isolated
highlight/selector word was found (three-way triangulation negative, jgrep
leads weak), so the full-table bridge stays open and
`render_fidelity_complete` stays false. Observed: the L key moves the
highlight leftward (against the assumed L=Right mapping), and paused loads
present no new frame until unpause. Slot 100 untouched; live race restored
from slot 101 and left paused (~21 observed key presses of a 30 budget).
Receipt:
[`bridge-three-screens.json`](evidence/carselection-2026-10-05/bridge-three-screens.json).
