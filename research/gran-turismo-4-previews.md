# Gran Turismo 4 static previews

Date: 2026-10-12. Scope: decode the extracted GT4 car files into textured static GLB previews
and list them in both the source catalog (`recovered.html`) and the editable dealership.
Extraction itself is covered by [gran-turismo-4-extraction.md](gran-turismo-4-extraction.md).

## Sources

Format reference; the repo's Python decoders are written from these, with attribution:

| Source | Commit | Licence | Used for |
| --- | --- | --- | --- |
| [Nenkai/PDTools](https://github.com/Nenkai/PDTools) `PDTools.Files/Models/PS2` (ModelSet2, PGLUshape, VIF*, RenderCommands, PGLUmaterial) | `ffe0bb26` | MIT | MDLS header, shape/VIF packet layout, render-command operand sizes |
| PDTools `PDTools.Files/Textures/PS2` (TextureSet1, GSMemory, GSPixelFormats) | `ffe0bb26` | MIT | Tex1 layout, GS block/column tables, CLUT tiling |
| PDTools `PDTools.SpecDB` (DBT/IDI/SDB readers, Huffman rows, GT4 column maps) | `ffe0bb26` | MIT | Spec database decoding |
| [Nenkai/GT-File-Specifications-Documentation](https://github.com/Nenkai/GT-File-Specifications-Documentation) `GT4_CAR4_CarInfo.bt` | `05e52347` | MIT | CAR4 header slots and CarInfo fields |
| [GT Modding Hub](https://github.com/Nenkai/gt-modding-hub) specdb, DBT/IDI/SDB pages | `b312010b` | — | Table semantics |

PDTools' README states GT4 model support is incomplete; every GT4-specific rule below was
checked against the disc data (counts, totals, rendered output), not taken on trust.

## What is decoded

**CAR4** (`tools/gt4_model.py`): header slots for car info, collision box, body, wheel and the two
tire model sets. The collision box's minimum Y is 0; that is not the ground (see the ride-height reading). CarInfo `TirePosRelated` (two floats,
equal to the last two `CHASSIS` columns) was first read as front/rear tire diameters; that reading
was wrong. The second value matches neither tire (Taurus SHO '98: 0.658/0.777 m with 225/55R16,
about 0.654 m, at both ends), and over 730 cars it is within 10 mm of the rear tire in only 170.
Its meaning is open; tire sizes now come from TIRESIZE.

**MDLS/ModelSet2 shapes**: each shape is a list of VIF packets. Attributes use VU addresses
0x00 (position), 0x40 (UV or normal), 0x80 (normal or colour), 0xC0 (GIF tag). Integer unpacks are
fixed point with 12 fractional bits; one attribute may arrive as contiguous segments of differing
widths (V3_8/V3_16/V3_32), the smallest width that fits. Unsigned 32-bit unpacks (address bit 14)
are floats. Strip lengths are `(b + 6) / 3` from the trailing S_8 unpack. Over the whole sample
(76,000+ packets) every shape's vertex and triangle totals equal its header.

**Render commands**: a static walk takes LOD 0, branch 0 of model callbacks and the first target of
VM branches. Depth-mask and alpha-test commands are tracked per draw. Body callbacks 11–14 load the
left-front, right-front, left-rear and right-rear wheel matrices at runtime; the preview supplies
translations to the same wheel centres. Over 725 cars with all four, the parts of 11/13 sit at local
+x and 12/14 at local −x, inboard only if 11/13 are on −x (the left side). 11/12 carry the
larger discs in 411 cars against 63 the other way (front).

**Tex1**: transfers are always PSMCT32-swizzled uploads; cars use PSMT4 and PSMT8 textures with
PSMCT32 CLUTs (CSA offsets in units of eight words; PSMT8 CLUTs in 8×2 tiles). GS alpha 0–0x80 is
rescaled to 0–255. Size-0 Tex1 entries are placeholders for unused texture LODs. Decoded textures
show legible badges and decals (for example "ACURA" and "3.2CL-S").

**SpecDB** (`tools/gt4_specdb.py`): GENERIC_CAR (730 rows) joins to CAR_VARIATION → VARIATION
(model code), CAR_NAME (retail name), DEFAULT_PARTS → CHASSIS, FRONTTIRE/REARTIRE → TIRESIZE.
Joins use table ids, because GT4's DEFAULT_PARTS key order differs from later games. All 730 model
codes join exactly once, all with names.

## Readings used to assemble a preview

These are labelled readings, verified visually but not by game execution:

| Reading | Evidence |
| --- | --- |
| Native coordinates are used unchanged in glTF (no X mirror) | Compared with in-game GT4 photo-mode shots ("Cars of Gran Turismo" blog): with the X mirror the earlier previews were mirror images. The NISMO 270R's exhaust and "270R" badge sat on the wrong side, and its "nismo" plate, side decal and the Hyundai Coupe FX's "Coupe" plate read backwards. Unmirrored, all of these match the game, and the Acura CL's "ACURA" trunk lettering reads correctly. The earlier mirror reading (trunk lettering, MR2 steering wheel) was wrong |
| Cars face −Z | `VARIATION.ModelFront` equals the model's |min Z| (Acura: 2381.8 mm, collision z −2.3817); the dealership front camera shows grilles from −Z |
| The car's right side is +X; front axle at −wheelbase/2, rear at +wheelbase/2; body callbacks 11–14 are the left-front, right-front, left-rear and right-rear wheels | Follows from the two rows above and the brake-callback statistics. The first previews put the front axle at +Z; with equal axles this looked right, but on the Taurus SHO the wrong tire size clipped the body (review of PR #36) |
| Axles are centred on the model origin | Body arch openings, with brake parts moved away, centre at about ±1.36 m for the Taurus SHO (wheelbase 2756 mm) and the Acura CL (2715 mm) |
| Tire diameter = rim + 2 × aspect × width (TIRESIZE) | 215/50R17 → 0.647 m; front and rear use their own rows |
| The ground lies the default SUSPENSION ride height below the model origin (wheel centre y = tire radius − ride height) | With the ground at y=0 (the collision floor), the Taurus SHO's tires rose 5–10 cm through the arch lips. The Taurus's lowest body point is 0.029 m and its ride height is 155 mm. Over 44 sampled cars, the 17 with measurable clipping under y=0 have none under this rule; the cars that appeared to get worse are triangle-sampling artefacts, and the Camaro and RX-7 (FC) checked by eye sit in their arches. An in-game Taurus screenshot shows the same small gap above the tires |
| Wheel centre track = tread − tire width | Acura: 1769 − 215 = 1554 mm against a published 1555 mm track |
| Wheel/tire meshes are normalised (tire width 0..1, bead radius 1, tread ~1.317) | Measured bounds of every sampled wheel/tire model set |
| TIRESIZE bytes: aspect/5, category, rim inches × 10, width/5 mm | 215/50R17 decodes to (10, 0, 170, 43) |
| Shape kind 2 is a reflection-like overlay, kind 5 a shadow | Kind 2 duplicates body shapes untextured with vertex colours (dark blotches when drawn); kind 5 shapes are flat or shadow volumes |
| Texture alpha is opacity only where depth writes are off (glass) | Body paint texels carry alpha ≤ 0x40, used by the reflection pass; the game's default alpha test (GEQUAL 0x20) is kept as MASK |

## Visual verification

Spot-checked in `recovered.html` (local `serve_library.py`): Acura CL 3.2 Type-S '01, AC Cars 427 S/C
'66, Toyota MR2 V Edition (J) '02, Chevrolet Camaro Z28 302 '69, NISMO Skyline GT-R R-tune (R34)
'99, Ford GT '05 and Volkswagen Beetle 1100 Standard '49 render with textures, wheels in the
arches and no console errors. In `dealership.html` the Camaro shows its decoded year and mass,
and the side and front cameras frame the side profile and the grille.

## Outputs

`python3 tools/import_gt4_catalog.py` writes, under `dealership/public/gran-turismo-4/`, one
`previews/<code>.glb` (showroom model, decoded textures, four wheels and tires) and one
`native/<code>.zip` per car, with an `index.json`. Rows carry the retail name, the native package
and the claim limits. `python3 tools/import_gt4_dealership.py` adds independent editable copies
as `dealership/dealership/models/GT4_<CODE>.glb` with names, model years and masses from the spec
database. Rebuild with `tools/build_model_catalog.py` and `tools/build_dealership.py`.

`import_gt4_catalog.py --check` (check `gt4_catalog`) re-derives every preview from the local
extraction and compares geometry and JSON exactly and textures by decoded pixels, so a different
zlib build cannot cause a false failure. The extraction (except `index.json`, `provenance/` and the
fixture car `acra0001`) and the native ZIPs are not committed, so the check is skipped where they
are absent; the catalog build then validates each committed preview against its pinned hash.

## Not established

- Game-render fidelity: lighting, reflections (kind 2 pass), PS2 blending, shadows and fog.
- Visual artefacts seen in spot checks: light streaks on the NISMO Skyline GT-R R-tune (R34) hood and rear deck; cause not investigated.
- Paint colours other than colour set 0 / the base CLUT; Pat0 colour patches are not applied.
- Runtime wheel matrices, steering, suspension travel, wings and VM-driven animation.
- The meaning of CarInfo `TirePosRelated` and the last two `CHASSIS` columns.
- Wheel placement beyond the readings above; cars with unusual layouts (three-wheelers,
  karts, concept cars) were not inspected individually.
- Race (LOD) models, interiors beyond what the showroom model contains, and the 880 shared wheels.

## Material correction follow-up (2026-10-16)

The original static MASK interpretation cuts holes through painted bodywork: the NSX '91
bumper has existing triangles sampling alpha 31/255 against the exported cutoff 63/255.
The NSX Coupe '97, Honda NSX '90 and BMW M3 '04 show related defects. A controlled cutoff
override closes the seams without moving vertices. This invalidates the earlier assumption
that retaining the default native alpha-test threshold alone gives a usable static preview.
Native PS2 pass ordering/blend behavior is still unverified.

The viewers now derive the material corrections documented in
[the dealership guide](../dealership/dealership/README.md#gt4-material-corrections), retaining
recovered files and geometry. Finish-bearing body surfaces keep nonzero paint alpha while
preserving alpha-zero cutouts; unrelated masks and authored material changes are retained.
Canonical green-marker BLEND window passes receive neutral translucent glass; black frame masks retain alpha while neutral RGB removes green transparent-padding filter fringes. Glass is explicitly a
preview fallback rather than recovered native glass shading. The source hash and correction
indices travel in the derived GLB and selected-paint downloads. Unit tests and an opt-in
730-car material audit check the bounded interpretation and preservation properties; they
do not establish original-game shader fidelity or a full visual review of the collection.

[Before/after screenshots and validation receipt](evidence/gt4-material-fix/validation.json)
record representative comparisons; the corpus counts remain executable material checks.
