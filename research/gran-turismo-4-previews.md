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
tire model sets. CarInfo `TirePosRelated` holds the front/rear tire diameters in metres; they equal
the last two `CHASSIS` columns (e.g. 0.646/0.699 for the Acura CL). The collision box's minimum Y is 0
(ground).

**MDLS/ModelSet2 shapes**: each shape is a list of VIF packets. Attributes use VU addresses
0x00 (position), 0x40 (UV or normal), 0x80 (normal or colour), 0xC0 (GIF tag). Integer unpacks are
fixed point with 12 fractional bits; one attribute may arrive as contiguous segments of differing
widths (V3_8/V3_16/V3_32), the smallest width that fits. Unsigned 32-bit unpacks (address bit 14)
are floats. Strip lengths are `(b + 6) / 3` from the trailing S_8 unpack. Over the whole sample
(76,000+ packets) every shape's vertex and triangle totals equal its header.

**Render commands**: a static walk takes LOD 0, branch 0 of model callbacks and the first target of
VM branches. Depth-mask and alpha-test commands are tracked per draw. Body callbacks 11–14 load the
right-front, left-front, right-rear and left-rear wheel matrices at runtime (a reading: their brake
shapes sit at ±x around the origin in matching pairs); the preview supplies translations to the
same wheel centres.

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
| Native frame is left-handed; X is mirrored for glTF | Trunk lettering reads "ACURA" left-to-right from behind; the Japanese-market MR2's steering wheel is on the right |
| Cars face −Z | `VARIATION.ModelFront` equals the model's |min Z| (Acura: 2381.8 mm, collision z −2.3817); the dealership front camera shows grilles from −Z |
| Axles at ±wheelbase/2 from the model origin | Wheels sit centred in the arches in side views (Camaro, Acura, AC Cobra, MR2) |
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

`import_gt4_catalog.py --check` (check `gt4_catalog`) re-derives every preview from the committed
extraction and compares geometry and JSON exactly and textures by decoded pixels, so a different
zlib build cannot cause a false failure.

## Not established

- Game-render fidelity: lighting, reflections (kind 2 pass), PS2 blending, shadows and fog.
- Visual artefacts seen in spot checks: light streaks on the NISMO Skyline GT-R R-tune (R34) hood and rear deck; cause not investigated.
- Paint colours other than colour set 0 / the base CLUT; Pat0 colour patches are not applied.
- Runtime wheel matrices, steering, suspension travel, wings and VM-driven animation.
- Wheel placement beyond the readings above; cars with unusual layouts (three-wheelers,
  karts, concept cars) were not inspected individually.
- Race (LOD) models, interiors beyond what the showroom model contains, and the 880 shared wheels.
