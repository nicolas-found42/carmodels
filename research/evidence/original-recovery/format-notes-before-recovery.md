# Ford Racing 2 asset-format notes

Source corpus: PAL PS2 `SLES-51705`, 35 per-car `.PS2;1` model containers, `.ptg;1` icon/livery buffers, extracted ELF and 3DDATA files.

## Findings verified from on-disk assets

### Model containers (`cars/<code>/model/*.PS2;1`)
- Initial directory contains a string-blob length, groups of u32 offsets into the blob, part names (`WHEEL_*`, `HUB_*`, `BRAKE_LIGHTS_*`, `EXHAUST`, etc.), texture names (`*_512/256/128/64`, `UNDER_SHADOW`), and livery tokens.
- Files are qword-aligned. **Verified:** u16 LE triangle-strip topology zones (G_TORINO `0x6d4..0x190a`): strips end at `0xffff`; `0x80ff` (low half of `0xffffff80`) pads to qword alignment; other low values (0x4, 0x0b..0x11) are genuine reused vertex indices, not separators.
- **Verified cross-car:** the wheel/hub strip topology is byte-identical across different cars — GT[1748:3802] == F100[1876:3930] == TAU[2196:4250] (2052 B, 1016 tris, max index 200). Body strips are car-specific (G_TORINO body: 3 strips, 917 tris, max index 154). Max index 200 (GT/F100) and 236 (TAURUS) ⇒ ~201–237 vertices per part.
- Per-part color data: 114 qwords RGBA(dd,dd,dd,0x6f) flat-color zone + `(R,G,B,0x80)` ramp qwords; body paint rgb(39,16,15) sits in the G_TORINO ramp at zone byte 6944. These are palettes/ramps, **not** coordinates (92% of ramp entries have R=G=B; values wrap 0x00→0xfe).
- Byte zones contain 4bpp/8bpp indexed texture texels with headers carrying a f32 world-size (e.g. 3.62). Tail holds per-part f32 transform records (u32 id, 1, f32×3 — e.g. Taurus wheel mount (±0.817, 0.331, −1.283)) plus 12-byte-periodic 7-f32 records with id tags (G_TORINO `0x3f000`, F100 905032) = per-part transforms/hull params.
- **No per-vertex position arrays anywhere** (exhaustive f32-plausibility scan of all three reference files + dword histogram). Current best explanation: the containers store topology, materials/palettes, and part transforms; geometry positions come from a shared geometry pool indexed by object-3D ids and are built into VU1 vertex buffers at load time by the ELF loader (`3dscene.c`/`3dobjbuf.c`/`vu1pack.c`/`vu1rend.c` module names + `object_3d_id_number invalid - geometry index out of range` string at ELFOFF 0x153a40 + `GENERIC_CAR` enum names). Wheels are consistent with procedural torus generation from strip topology + radius/width params (0.7485/0.3231).
- `3DDATA/misc.ps2;1` (236,944 B, name blob includes `GENERIC_CAR`) and the ELF's shared pool are the unverified-but-likely sources of the positions; recovery requires full loader disassembly or a VU trace. Reconstruction story: **medium confidence**; the topology/palette/texture layout findings: **high confidence**.

### `.ptg;1` texture buffers
- Every observed icon/livery `.ptg;1` is exactly 100,304 bytes; `0xdd` runs are padding, and repeated structures include EE-RAM-looking addresses. A sequence of 24 pointer-shaped qwords begins at offset `0x1f8` in the Torino icon. The pointer deltas vary (including large jumps); the earlier simple fixed-stride interpretation was wrong.
- Cross-file byte comparisons locate car-dependent payload spans. Rendering selected spans as linear RGBA can reveal a red Gran Torino body fragment, but guessed row widths produce repeated/cropped strips, not a validated complete icon. Exact TRXREG dimensions, payload starts, mip boundaries and palette mapping remain **unresolved**.
- A PSMT4/PSMT8 swizzle experiment produced lower neighbour-difference metrics than a linear control for some pages, but contact sheets were not coherent. **Swizzling is not confirmed**; do not publish the experimental PNGs as faithful textures.
- The viewer therefore shows only an **icon paint sample** (a dominant opaque/saturated colour estimate), the original livery codes, and the explicitly reconstructed 3D silhouette. It does not claim to display decoded textures.
- `tools/gifparse.py` was an unsuccessful packet-parsing probe and was removed; a correct GIF walker still needs to locate valid packet boundaries and interpret each A+D/IMAGE upload.

## Decision experiments with Jev (TypeSafe/Jev 1.13)
- Batched `jev_classify` of manifest car descriptions for broad gallery groups: 28/35 auto, 7 sent for review. A second body-silhouette classification returned 33 auto and 2 review (Explorer Sport Trac, FR500); resolved from exact model names as SUV and Mustang coupe silhouette.
- Texture-page question on programmatic measurements returned a weak preference for `linear` (0.77), while an earlier SDK question preferred atlas tiles (0.71). Treat this disagreement as evidence that texture dimensions are not settled; visuals also show incomplete strips.
- `jev_decide` for the viewer scope selected `manifest_3d` (p=0.86): build a usable interactive gallery now, keep real data visible, mark generated shapes as reconstructions, and defer exact mesh recovery.
- `jev_decide` for thumbnail handling weakly preferred replacing broken partial textures with a paint swatch + exact livery codes (0.52 vs partial thumbnail 0.48). We followed the more truthful option; both satisfied the explicit requirements.

## Research deliverables
- `research/visualization-libraries.md` — primary-source research on related tools, PS2 references, three.js and exporter options.
- `viewer/index.html` — offline three.js viewer; its procedural shapes use Jev-classified body styles and manifest performance values.
- `tools/build_showcase.py` — regenerates `viewer/public/cars.json`, including the best-effort icon paint sample.

## Next technical work
1. Decode valid GIF packet boundaries and A+D register writes; use BITBLTBUF/TRXPOS/TRXREG/TRXDIR/HWREG to obtain exact pixel upload extents.
2. Recover the shared geometry pool: disassemble the ELF loaders around the located strings/enum tables (no capstone on this box yet) or trace VU1 in PCSX2; `misc.ps2;1` is the likely pool file. With per-part transforms (tail f32 trios) + shared topology, per-car meshes become reconstructable once positions exist.
3. Only after those are verified, generate GLB per car and replace the procedural silhouette.

References used: ps2tek GIF/VIF/VU/DMAC (`https://psi-rockin.github.io/ps2tek/`); PCSX2 `GSLocalMemory.h/.cpp`, `GSTables.cpp`, `GSBlock.h`, `Gif_Unit.h`; viewer-library citations are in `research/visualization-libraries.md`.
