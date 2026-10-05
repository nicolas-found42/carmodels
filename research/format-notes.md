# Ford Racing 2 asset-format notes — corrected 2026-10-04

Current synthesis: [original-recovery.md](original-recovery.md). The previous note is preserved as [format-notes-before-recovery.md](evidence/original-recovery/format-notes-before-recovery.md); its topology and shared-pool claims are withdrawn.

## Original car containers

The 35 archive-matched PAL PS2 car `.PS2;1` files contain their own geometry. The current section parser walks their name directory, palettes, textures, `0x34` geometry records, aligned payload planes and later object trees to exact EOF. A fresh census finds 1,872 geometry records, 12,080 headers and 657,139 six-byte samples. Record zero is empty in each file, leaving 1,837 nonempty records.

Geometry group counts are separate u16 fields at record offsets `+0x1c` and `+0x28`. Six-byte planes are signed little-endian int16 triplets. Per-axis local position is:

```
position = raw_signed16 / 16384 * max(abs(stored_min), abs(stored_max))
```

Every nonempty record reproduces all three serialized bound pairs within one quantization step plus `1e-6`. Original executable bytes support the max-absolute scale producer, VIF STROW 768/STMOD 1 preamble and VU subtraction/multiplication path. Qword four is loaded into `vf20`; overlay six continues into stores and `XGKICK`. This establishes a strong static local-position interpretation, with a bounded COBRA UV/texture-to-GS packet join now observed; full vertex-transform equivalence remains open.

The four-byte plane's first three signed bytes have near-unit lengths after division by 127. Its fourth byte is always 0 or 1, and every header starts with two 1 values. A candidate sequential triangle strip suppressing draw on W=1 produces 387,530 triangles. Optional V2-16 data interpreted as signed UV/2048 and the header's third halfword interpreted as texture index give recognizable textured bodies. Every one of 11,538 non-sentinel values fits that car's texture library; 542 headers use 65535. These attribute, topology and material interpretations remain experimental.

Later object trees carry IDs, flags and six floats. Every car has five roots; the last three float fields are zero throughout this corpus. Translating the hierarchy by the first three fields places local wheel geometry beside body geometry. GLBs preserve independent records and all five complete tree scenes, plus ten source-derived low-speed/moving-wheel scenes with lights off. The latter encode explicit state inputs and preserve source transforms. All 2,246 nodes and 2,051 named pairs are source-joined. Runtime captures match six car hierarchies and changing mutable state; distance-root selection is source-traced, while exact executed draws remain a separate check.

The historical G_TORINO/F100/Taurus “strip indices” fall entirely inside parsed palette blocks. Byte equality there cannot establish shared wheel topology. An f32-only scan missed compact signed16 positions. The prior “no positions anywhere,” required shared vertex pool and procedural torus conclusions are withdrawn. `misc.ps2;1` remains a separate generic-asset lead.

## Embedded model textures

The existing loader-derived level-zero decoder handles format 1 linear RGBA and format 3/4 indexed data, including descriptor-bit-8 packed/direct upload differences and bounded CLUT/address handling. The fresh car subset exports 700 textures: 78 format 1, 618 format 3 and 4 format 4. All decoded RGBA hashes match the prior pinned corpus receipt. Raw alpha and display-alpha `min(255, 2*a)` PNGs are both retained: 1,400 files with validated CRCs and pixel roundtrips.

All 94 additional stored mip levels are now decoded and independently validated in the mip continuation, producing 94 stored-alpha PNGs and 94 verbatim binary planes. The GLB preview embeds level zero. A source-derived remapping contract exposes 134 complete numeric texture variants across the 35 GLBs; the stock Taurus base entries are 8×8 placeholders, while its nonzero selectors use full-size textures. Original alpha blending, reflection and shading need further runtime/source validation. See [the original texture research](original-geometry-research.md) and [texture census](evidence/original-recovery/car-asset-census.json).

## Separate PTG files

All 171 original CARS/LIVERY PTGs are decoded and PNG-validated: 35 icons at 165×98 and 136 liveries at 227×85. Their format-1 RGBA tiles and UI grid composition are source-traced. A further 136 MATRIX PTGs at 90×64 are decoded through the source-derived PSMT8/CSM1 palette mapping, with 272 canonical raw/display PNGs and separate palette-order negative controls. CARS loading is source-closed; the inspected LIVERY template call is a UI string property rather than a texture load, so its actual image consumer remains unresolved. See [ptg-continuation.md](ptg-continuation.md).

## Artifacts and next work

- [Recovered geometry inspector](../viewer/recovered.html) and [35-car GLB index](../viewer/public/recovered/index.json).
- [Texture contact sheet](evidence/original-recovery/texture-gallery.html).
- [Research synthesis and experiment ledger](original-recovery.md), including Jev failures and manual dispositions.
- [GitHub/Stack Overflow research](community-github-stackoverflow.md) and [Reddit/YouTube research](community-reddit-youtube.md).

The next fidelity work is to trace runtime part/state selection, close the VIF/VU attribute-to-GIF contract, compare a representative car to an observed game render, and resolve remaining GS material behavior and UI image-consumer links. PTG pixels and stored mip images are recovered. The inspector is a useful recovered-data experiment, not a claim that every car matches the game's final draw.
