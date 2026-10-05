# Car PTG loader trace checkpoint

## Result

The PAL executable establishes that a CARS `.PSD` request is explicitly aliased to the disc's `.ptg;1` filename. The CARS callback requests type 2 and queues a file read; on completion `FUN_00111cd0` decompresses the read buffer with `FUN_00101690`, then calls `FUN_0022acc8` on the decompressed PTG. The file-to-parser path is closed. The transformed descriptors, upload behavior, and actual displayed pixels still need validation.

## Primary executable and path strings

The source is the PAL PS2 executable `SLES_517.05` from the extracted game at [`games/ford-racing-2/extracted/SLES_517.05`](/Users/Nicolas/Documents/github/hermes/reverse-engineering/games/ford-racing-2/extracted/SLES_517.05). Its SHA-256 is `216711210898aee296eed73d0776e7f733bac04c334002683bce769c86beea95` (1,662,804 bytes); the same executable identity is recorded in the saved Ghidra decompilation manifest under `reverse-engineering/.scratch/mesh/codex-root/decompile-all-02/manifest.json`.

Direct byte searches and `strings -a -t x` on this executable give:

| File offset | Exact ASCII string | What it establishes |
|---:|---|---|
| `0x151ee0` | `Unable to load a texture graphic from a filename without a .psd extension: %s` | A texture-graphics path validates/mentions `.psd`; the string alone does not identify its caller or codec. |
| `0x15a1d0` | `GRAPHICS\\GAME\\LIVERY\\%s.PSD` | A livery pathname template exists in the executable. |
| `0x15e1c0` | `GRAPHICS\\GAME\\CARS\\%s.PSD` | A car-graphics pathname template exists in the executable. |
| `0x162968` | `No livery %s for %s` | A livery-related error string exists. |

The full executable byte scan finds each pathname string once and no `.ptg` sequence in those templates. The alias is a separate extension table at VA `0x28ef08`, not a `.ptg` filename literal in the templates.

There is one stronger, narrow code-path result for the CARS template. The ELF section map places `.text` at VA `0x100000` / file offset `0x1000`, so VA-to-file offset is `VA - 0xff000`. At VA `0x182224`, the original little-endian MIPS word is `0x3c060026` (`lui a2,0x26`); at `0x182234`, it is `0x24c6d1c0` (`addiu a2,a2,0xd1c0`). Together they form `a2 = 0x25d1c0`, the address of `GRAPHICS\\GAME\\CARS\\%s.PSD`. The surrounding instructions set `a0 = sp`, `a1 = 0x40`, and load the format value into `a3`; `jal` at `0x18223c` targets `0x00101730`. The saved function manifest has no containing function boundary here. A read-only temporary Ghidra project copy recreated the callback boundary at `0x1820f0` from its registration as a callback argument in `FUN_00181f38`; its generated pseudocode shows the CARS case calling `FUN_00101730(auStack_b0,0x40,0x25d1c0,...)`, then `FUN_0022a910(auStack_b0,1,2)`. The latter `jal` at VA `0x1826b0` has bytes `44 aa 08 0c` and targets `0x0022a910`. Treat the function boundary/decompilation as recovered analysis output; the raw executable bytes, string address, and call encoding are primary evidence.

The saved generated pseudocode for [`FUN_00101730`](/Users/Nicolas/Documents/github/hermes/reverse-engineering/.scratch/mesh/codex-root/decompile-all-02/functions/00101730.c) saves variadic arguments, calls `FUN_00212108` with the format argument, then calls `FUN_0020e4d8` with the destination and capacity. The separate LIVERY template has since been tied to a callsite, but not to a texture load: `FUN_00173938` forms VA `0x25a1d0` at `0x17434c/0x17435c` and passes it as the first argument to `FUN_0015b280` at `0x174370`. The recovered body for `FUN_0015b280` saves that argument but does not read it, call the CARS PTG loader, or invoke the PTG parser. See [`livery-and-alpha-source-trace.json`](livery-and-alpha-source-trace.json). Thus the LIVERY string reference is source-proven, while use of the 136 LIVERY PTGs remains unresolved.

## Disc assets and measured PTG boundary

The extracted PAL tree contains `GRAPHICS/GAME/CARS/torinod.ptg;1` and other icon assets, and `GRAPHICS/GAME/LIVERY/49coupea.ptg;1`, `49coupeb.ptg;1`, `49coupec.ptg;1`, `49couped.ptg;1`, and other livery assets. The source directory listing is [`games/ford-racing-2/extracted/files/GRAPHICS/GAME`](/Users/Nicolas/Documents/github/hermes/reverse-engineering/games/ford-racing-2/extracted/files/GRAPHICS/GAME); the archive-derived tree is also listed in [`notes/fs-tree.txt`](/Users/Nicolas/Documents/github/hermes/reverse-engineering/notes/fs-tree.txt).

The existing car corpus census reports 171 PTGs, each 100,304 bytes. It measures 35 icon headers at 165×98 with a 6×4 grid, and 136 livery headers at 227×85 with an 8×3 grid. All declare 24 tiles, a 32-pixel cell, stride 32, and final word 1. The checked header relation is `[count, columns, rows, stride, cell, width, height, last]`; this is a tile-grid/header stride field, not evidence of image row pitch. The corpus's implementation explicitly classifies these files as `tiled_header_only`. See [`research/original-ptg-research.md`](/Users/Nicolas/Documents/github/hermes/projects/carmodels/research/original-ptg-research.md), [`ptg_profile.py`](/Users/Nicolas/Documents/github/hermes/reverse-engineering/tools/ptg_profile.py), [`verify_ptg.py`](/Users/Nicolas/Documents/github/hermes/reverse-engineering/tools/verify_ptg.py), and the per-file hashes in [`ptg-profile-carmodels.json`](/Users/Nicolas/Documents/github/hermes/projects/carmodels/research/evidence/ptg-investigation/ptg-profile-carmodels.json).

The known 0xDD-filled multi-tile profile in `ptg_profile.py` is a separate profile from the car assets: the car files end in header word `1`. The single-tile gear-sprite decoder also does not apply because these files have 24 tiles. Consequently, body bytes have not been traced to a decoded car image through that code.

## Jev / TypeSafe check

I used Jev `jev_verify` with the executable strings, the extracted disc paths, and the current measured corpus boundary as separate evidence items. Its full result was:

- Executable identity and both `.PSD` templates: `verified`, `supports=1.00`, `confidence=1.00`.
- Separate CARS and LIVERY `.ptg;1` namespaces: `verified`, `supports=0.98`, `confidence=0.97`.
- Claim that the strings establish a function or pixel format, palette, row stride, swizzle, mips, or alpha: `unsupported` (relation contradicted at 0.99; confidence 0.99).
- The earlier `.PSD`-to-`.ptg;1` check is superseded by the later extension-table trace below; the old check did not include the relevant code or table bytes.
- Separate verification of the CARS MIPS address construction, CARS string mapping, and call to `0x00101730`: `verified`, `supports=1.00`, confidence 0.99. The interpretation of the generated helper pseudocode as string formatting/copying was `verified` at confidence 0.58 with `supports=0.72` and `contradicts=0.26`, so it remains a reviewed inference. The claim that this path trace establishes PTG decoding/upload was `unsupported` (confidence 0.29).

Across these checks, Jev usage was 6,505 input and 1,181 output tokens. This judgment checks the supplied text claims; it does not read or validate executable pixels and is not evidence of runtime behavior.

## Remaining decode questions

1. Map the serialized PTG descriptor fields to effective runtime texture fields. The sequential 80-byte header, 16-byte records, 64-byte descriptors, and body-pointer construction are visible in the parser, but some PTG descriptor words are `0xDD` sentinels and cannot be read as runtime mip pointers/dimensions directly.
2. Verify channel order, alpha behavior, tile arrangement, clipping of padded 32×32 edge cells, and display-space scaling against an in-game car-menu image and/or GS upload capture.
3. Resolve the LIVERY consumer. The template address reaches `FUN_0015b280`, whose recovered body provides no PTG load/parser edge; find the actual string use or a different resource loader and establish how the 136 LIVERY assets are selected, parsed and drawn.

Until those checks pass, the exported PNGs remain source-bound candidate reconstructions, not fully validated recovery.

## Later consumer trace (saved PAL decompilation; asset identity still open)

Further inspection of the saved Ghidra export connects a generic `.PSD` texture-resource loader to a parsed texture buffer and to GS packet emission. This closes part of the executable-consumer path, but does **not** establish that the 171 `.ptg;1` files are the bytes returned by that loader.

- `FUN_0022a910` checks that the final path component has a dot extension, allocates a 0x50-byte resource object, copies the filename into its `+0x2c` string, and sets flags including the caller's type. Its type-1 path reaches `FUN_00107ce0(path, ..., 1, ...)`, stores the returned buffer/resource at `+0x40`, then calls `FUN_0022acc8`.
- `FUN_0022acc8` treats `param_1+0x40` as a loaded buffer. It reads word 0, saves words 0 through 10 as runtime header values, and sets the first per-tile structure list to the buffer's word offset `0x14` (80 bytes). It locates the serialized tile descriptors after `count*4` additional words, i.e. 16 bytes per tile, and steps through those descriptors by `0x10` words, i.e. 64 bytes each. It installs runtime body pointers at descriptor `+0x28`. If descriptor byte `+0x34` is 3, it handles a 0x100-byte palette area before assigning tile body pointers; otherwise it advances body pointers using dimension exponents and a format-indexed size table. This count/header/record/descriptor arithmetic is consistent with the measured 80 + 24×16 + 24×64 car-file prefix layout.
- `FUN_00222358` reads a runtime texture object at `+0x28`, `+0x30`, `+0x34`, `+0x35`, and `+0x38`, and calls `FUN_00222110` with `+0x28` as the data pointer. `FUN_00222110` builds GIF/GS packet words and calculates a transfer size from the submitted dimensions and format-size argument. The observed callers of `FUN_00222358` are `FUN_00127470` and `FUN_00228ed8`.
- The format table initialization (`FUN_0022f948`) sets byte `DAT_00232da1` to `0x20`. Since the parser indexes `DAT_00232d92 + format*15`, serialized format byte `1` selects 32 bits per pixel. Its payload-cursor formula multiplies the two descriptor power-of-two dimensions by that bpp and divides by 8, so a 32×32 format-1 tile occupies 4,096 bytes. The corpus has exactly 4,096 bytes per measured tile, agreeing with this part of the source contract; direct dimension-field mapping remains unresolved.
- The direct byte comparison argues against equating the serialized car descriptors with the runtime texture descriptor layout without an intervening conversion. In `torinod.ptg;1`, tile descriptor 0 at file offset 464 has word 10 `0x01c500b0`, word 12 `0xd0410010`, word 13 `0xdddddd01`, word 14 `0xaaaa8c45`; most other words are `0xdddddddd`. If those bytes were treated directly as the runtime object, byte `+0x34` would be 1, `+0x35` would be `0xdd`, the mip-list pointer at `+0x2c` would be `0xdddddddd`, and packed dimension bits at `+0x38` would include `0xdddddddd`. Those values do not supply a valid direct runtime mapping. The 64-byte serialized descriptor boundary is measured; its field semantics and transformation are not.
- The CARS `.PSD` template has one saved reference at `0x00182234` and calls formatting helper `FUN_00101730`; LIVERY `.PSD` has no saved reference. The extension table/code alias below resolves the CARS `.PSD` request to `.ptg;1`; no LIVERY caller sequence has yet been recovered.

Jev `jev_verify` over the earlier pseudocode and inventory excerpts marked the `.PSD` loader call sequence and runtime `FUN_00222358` → `FUN_00222110` edge verified; it marked direct texture-buffer-to-serialized-descriptor field identity unsupported/review. The earlier `.PSD` → `.ptg;1` verdict was based on evidence that omitted the alias table and is superseded by the later verification below. These checks evaluate supplied text excerpts and do not independently decompile the binary or validate pixels. Receipt: `research/evidence/ptg-continuation/jev-loader-consumer.json`.

## Extension alias and exact resolver chain (source follow-up)

The executable contains a direct suffix alias, so the CARS request does reach a filename present on disc:

1. The recovered CARS callback at inferred VA `0x1820f0` formats the template at `0x25d1c0` through `FUN_00101730`, then calls `FUN_0022a910(path,1,2)`. The call instruction at VA `0x1826b0` is `44 aa 08 0c` (little-endian word `0x0c08aa44`), a JAL to `0x0022a910`. The saved manifest does not contain the callback boundary; it was recreated in a temporary Ghidra project copy from the callback pointer passed by saved function `FUN_00181f38`. The decompilation is therefore generated analysis output, while the executable call bytes and referenced template address are primary evidence.
2. `FUN_0022a910` finds the final dot and passes the extension to case-insensitive `FUN_0020db20` for comparison with string VA `0x28ef08`. At VA `0x28ef08` / file offset `0x18ff08`, the exact bytes begin `70 73 64 00 00 00 00 00 70 74 67 00 00 00 00 00 42 75 67 00`: `psd`, padding, `ptg`, padding, `Bug`. When `psd` matches, `FUN_0022a910` calls `FUN_0020d9e0(extension,0x28ef10)`. `FUN_0020d9e0` formats/copies the NUL-terminated `ptg` string over the existing extension and terminates it. This is a replacement, not merely an extension check.
3. `FUN_0022a910` passes the rewritten path into `FUN_00107628`. In PS2 mode, `FUN_00107628` calls `FUN_001077f0(...,2)`, which applies format string VA `0x250348`, `cdrom0:\\%s;1`, then uppercases the path after its seven-byte prefix. `FUN_00107c20(...,2,...)` calls `FUN_00107268`; that routine skips `cdrom0:\\`, splits on backslashes, and uses case-insensitive exact component matching (`FUN_0020db20`) against the directory/file table at `0x295000`. The resolver returns the matched tree node; the suffix mapping happened before it.
4. The extracted disc tree contains `GRAPHICS/GAME/CARS/torinod.ptg;1` and `GRAPHICS/GAME/LIVERY/49coupea.ptg;1`, confirming the resolved CARS name shape and the separate LIVERY namespace. The LIVERY `.PSD` template is referenced by the `FUN_00173938` call to `FUN_0015b280`, but that call has no demonstrated PTG load/parser edge; a LIVERY asset consumer path is still unverified.

The CARS callback passes resource type 2. In `FUN_0022abf8`, type 2 gets the file size through `FUN_001076a0`, aligns/allocates a buffer, and queues a request through `FUN_00105480`, setting state 2. On completion, `FUN_00111cd0` checks the request state, obtains the compressed byte count with `FUN_001076a0(path)`, and calls `FUN_00101690(input_buffer, compressed_bytes, path)`. It frees the compressed input, stores the returned output at object `+0x40`, calls `FUN_0022acc8`, and advances the object state. `FUN_00101690` allocates the uncompressed length from the input's first word, inflates the zlib stream beginning at input offset 4, and finalizes the output. This matches the archive's size-prefixed zlib wrapper; the parser receives the decompressed PTG bytes. Type 1 instead calls `FUN_00107ce0(path,0,1,...)` and parses its returned buffer immediately.

`FUN_0022acc8` is structured parsing and pointer setup, not the file reader or decompressor. It reads header words from the populated object buffer, constructs 16-byte runtime entry links and 64-byte descriptor pointers, optionally assigns a 0x100-byte palette area for format 3, and computes payload pointers from descriptor dimensions and format size. On the CARS type-2 path that populated buffer is produced by `FUN_00101690` during async completion.

Jev `jev_verify` was rerun with the callback pseudocode, raw extension-table bytes, path-normalizer and resolver pseudocode, disc-tree entries, and resource-type branch pseudocode. It verified the `psd`→`ptg` replacement (supports 0.97, confidence 0.96), normalized `cdrom0:\\...ptg;1` construction (supports 0.99, confidence 0.98), and exact table resolution (supports 0.90, confidence 0.85). A second verification of the async completion edge, `FUN_00101690` zlib wrapper, and archive's size-prefix-plus-zlib profile returned all three `verified` (confidence 0.81/0.97/0.96). A third call verified format code 1's 32-bpp table entry and the four-byte-per-pixel size calculation while marking direct 32×32 dimension field identity unsupported. Receipt: `research/evidence/ptg-continuation/jev-async-completion.json` and `research/evidence/ptg-continuation/jev-format-size.json`. Jev marked callback call attribution for manual review (confidence 0.65) because the recovered callback boundary was reconstructed, not present in the saved manifest. Jev checks supplied evidence text; raw bytes and saved pseudocode remain the underlying evidence.

## Branch conflict resolution from pinned ELF bytes

A conflicting earlier summary said the type-2 completion branch bypassed
`FUN_0022acc8`. That is incorrect. The saved `FUN_00111cd0` pseudocode and
the pinned ELF both place the decompressor and parser calls inside the
resource-type-2 completion path. The CARS callback's call at VA `0x1826b0`
is `44 aa 08 0c` (`jal 0x0022a910`); its delay-slot instruction at
`0x1826b4` is `02 00 06 24` (`addiu a2,zero,2`). The preceding callback
instructions set `a0` to the filename and `a1=1`. `FUN_0022a910` stores
`param_3` into object `+0x34` and `param_2` into `+0x30`. In
`FUN_00111cd0`, raw bytes at `0x111d8c` (`02 00 13 24`), `0x111d90`
(`34 00 22 8e`), and `0x111d98` (`1f 00 53 54`) set type 2, load the
object's `+0x34` type, and branch to the next resource if it differs.

In the selected type-2 completion path, `FUN_001076a0` is called at
`0x111de0` (`a8 1d 04 0c`), `FUN_00101690` at `0x111df0`
(`a4 05 04 0c`), `FUN_0010d100` frees the compressed input at `0x111dfc`
(`40 34 04 0c`), and `0x111e04` (`40 00 30 ae`) stores the decompressed
pointer at object `+0x40`. The call at `0x111e08` is
`32 ab 08 0c` (`jal 0x0022acc8`), followed by the state-4 store at
`0x111e10` (`4c 00 32 ae`). The raw bytes use VA-to-file mapping `VA -
0xff000` for `.text` in executable SHA-256
`216711210898aee296eed73d0776e7f733bac04c334002683bce769c86beea95`.
Constructor and completion decompilation identities plus the exact callsite
bytes are saved in
[`async-bridge-static-evidence.json`](async-bridge-static-evidence.json).

This closes the conditional CARS `.PSD`→`.ptg;1`→async read→decompression→
structured parser chain. `FUN_0022a910` starts async work only when its global
async gate is set and the resource flags overlap the active request mask.
`FUN_00111cd0` also requires an active-mask match, a pending state (not 4), a
nonzero request handle, and a successful completion poll. The saved static
caller chain places `FUN_00111cd0` in `FUN_0015fbe0`'s loop, but static code
does not prove those runtime global conditions held in any particular state.
It does not connect the parsed car PTG descriptors to `FUN_00222358` or prove
that an actual menu draw consumes the assembled image. In particular, the
serialized `+0x2c` / `+0x35` mismatch is now route-dependent. A following
source trace joins the dynamic CARS request to reward buttons of class 3; this
button renderer reaches the base-image sprite uploader when its asynchronous
request completes. A particular runtime draw, final alpha blend and output
pixels are not proved here.

## UI draw table, cell geometry, and route-dependent mip sentinels

The archived `files/UI/REWRD.UI;1` is the original serialized layout for the reward screen. It identifies `GLOW` as `UI_TYPE_GRAPHIC`, with texture `GRAPHICS\\GAME\\CARGLOW.PSD`, position `(0.35, 0.32)`, and size `(0.35, 0.25)`. It identifies `BUTTON1` and `BUTTON2` as `UI_TYPE_BUTTON` at x positions 0.35 and 0.65. UI type table indices map class 1 to `UI_TYPE_AREA`, 3 to `UI_TYPE_BUTTON`, and 4 to `UI_TYPE_GRAPHIC`.

The class-selected renderer table has base-image routes for all three relevant UI classes. `FUN_0014d568(1)` installs setter `FUN_0014d728` and `FUN_0014d1d8` installs class-1 renderer `FUN_0014ca80`. Button initialization `FUN_00159610(3)` initializes class 3's setter through `FUN_0014d568(3)`, and `FUN_001595f0` installs renderer `FUN_00159080`. `FUN_00156e28(4)` installs graphic setter `FUN_00156f70` and `FUN_00156c40` installs renderer `FUN_001566b0`. Each of these renderer bodies resolves a ready texture resource, reads its dimensions with `FUN_002209a0`, computes a UI rectangle, and calls `FUN_0015e2e0`; this wrapper calls `FUN_00220678`, which enters `FUN_0021fd50`.

For a parsed tiled texture, `FUN_0022acc8` copies header width and height to texture-object offsets `+0x14/+0x18`, stride and tile cell size to `+0x0c/+0x10`, columns and rows to `+0x04/+0x08`, and sets `+0x44` to the same-index cell-record list. It writes each same-index descriptor pointer to cell record `+8`. `FUN_0021fd50` iterates rows and columns, reads each record's normalized U/V extents at `+0/+4`, and uploads the referenced descriptor through `FUN_00220fe0`. Its x step is `(right-left)*stride/imageWidth`; its y step is `(bottom-top)*cellSize/imageHeight`. The cell quad extent multiplies each step by the record's U/V values. In the source data those are 1.0 for complete 32-pixel cells and the clipped remainder/32 at the last column or row. This supports the decoder's same-index row-major placement and edge clipping as the texture object's source draw-grid semantics.

The base uploader `FUN_00220fe0` reads the descriptor base data pointer at `+0x28`, format at `+0x34`, and dimension bits at `+0x38`, then calls the GS-transfer helper. It does not read `+0x2c` or `+0x35`; those fields matter only on routes such as mip-aware `FUN_00222358`. The CARS callback's UI object join is now source-proven: its item index selects the same `BUTTON1`/`BUTTON2` pointer and resource-handle slots, and the archived buttons are class 3. Class 3's renderer reaches the base-image sprite uploader, so the dynamic CARS button route conditionally avoids the mip fields when the asynchronous load completes. Source identities and the class/draw trace are in [`reward-ui-graphic-path-trace.json`](reward-ui-graphic-path-trace.json).

### Sprite alpha state and LIVERY boundary

Correction to the earlier register labels: the pinned GS register map assigns
`0x3f` to TEXFLUSH, `0x47` to TEST_1, and `0x42` to ALPHA_1. In raw
`FUN_0021fd50` instructions, at `0x22000c` it places token `0x47`; at
`0x220080` it builds a data word from `DAT_002324ec` and
`DAT_002324fa`; at `0x220094` and `0x22009c` it places tokens `0x4e` and
`0x44`; after computing a packed data word at `0x2200c0`, it places token
`0x42` at `0x2200c4`, then calls `FUN_00110148` and `FUN_00110688`.
These instructions establish TEST_1- and ALPHA_1-related packet activity,
but the complete packet pairing/data interpretation is still unresolved.
`FUN_00220d60` independently emits TEXFLUSH and format-selected texture
setup; the old `0x3f` selector-as-TEST description was wrong.

The raw wrapper at `0x220678` stores incoming `a1` at stack offset 0,
sets `a1=1`, moves incoming `a0` to `a3`, sets `a0=a2=0`, masks saved `a1`
to 16 bits in `t0`, and calls `FUN_0021fd50` with delay-slot `t1=1`. It
clears FPU `f16` and copies zero to `f17/f18`; it leaves `f12`–`f15` intact.
The decompiler's six-argument rendering of that call is not a safe mapping to
the callee's thirteen-parameter prototype. The sprite routine halves supplied
vertex-color channels as `(channel+1)>>1`; its primitive bit `0x40` branch is
conditional on `param_9==1`, whose original incoming wrapper `a1` value must
be traced through the UI renderer. The decoder keeps source alpha unchanged
in `.raw-alpha.png`; `.png` doubles it only as a conventional preview. Final
blend state and observed menu output remain open. The source excerpts, hashes,
and Jev review receipt are in
[`livery-and-alpha-source-trace.json`](livery-and-alpha-source-trace.json)
and [`jev-livery-alpha-source-trace.json`](jev-livery-alpha-source-trace.json);
the earlier Jev receipts contain the superseded `0x3f`/ALPHA statements and
are retained as historical records.

The separate LIVERY string at `0x25a1d0` is referenced at `0x17435c` and passed
to `FUN_0015b280` at `0x174370`. Its recovered body saves the first argument
but does not consume it or call the CARS loader/parser. This establishes the
template reference, not a LIVERY PTG loading/draw route. That unresolved path
is documented in [`livery-and-alpha-source-trace.json`](livery-and-alpha-source-trace.json).
