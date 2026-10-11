# Midnight Club 3 Remix: textures, alpha and artifact surfaces

Four user screenshots (two byte-identical) showed gray MC3 dealership previews with large flat or irregular light surfaces. This note records the diagnosis, the decoded texture formats, the material-to-texture binding, the display policy and the controls. It extends [the static preview note](midnight-club-3-remix-previews.md), which stated that texture images were undecoded. Retained receipts are under [`evidence/midnight-club-3-remix/previews/textures-fix/`](evidence/midnight-club-3-remix/previews/textures-fix/).

## What the screenshots showed

| Report | Source identification | Cause |
| --- | --- | --- |
| Unlabelled car, large light rectangle under the car | `VP_ESPRIT_04`. The 4-triangle quad `shadow_neon.mesh` (2.92 × 5.27 m, material template `drop_shadow`) is the only large flat primitive; no other vehicle matches the screenshot's wing and tail lamps. | A ground blob-shadow effect plane was exported as opaque neutral geometry. |
| `VP_CORVETTEZ06_03`, bright irregular flat patches near the rear and a loose sliver | The patches are the 56-triangle `car_decal` layer (`composite_material_wrapper` whose sub-shaders are `car_decal` and `car_decal_chrome`), coplanar with the body and z-fighting as opaque gray. The sliver is `masked_chrome` trim at z up to 2.26, beyond the body, which belongs to the rear bumper that is not exported. | Decal surfaces drawn opaque; see "Geometry gap" for the bumper. |
| `VP_D_CHINGON_04`, broad flat plate at the rear hub | `sprocket_h.mesh` (material template `sprocket`): a quad whose trim-atlas alpha cuts out the sprocket disc. | The cut-out texture was missing, so the whole quad was opaque. |

Before/after renders of all three through the real dealership loader are in `renders/before-after/`. The three cars were also checked in the running dealership page at `/dealership.html` by filtering Game to Midnight Club 3 Remix and searching the native ID.

## Texture carriers

Two carriers are decoded; both are in [`tools/mc3_textures.py`](../tools/mc3_textures.py).

- **PCK-embedded image slot.** Class value `0x7A14A0` plus the package profile delta (`0`, `0x200` Mercedes, `0x1308` Remix). A slot is an image when the word at `+0x08` is `0xE7` and the low half of `+0x0C` is `0x100`; its name pointer is at `+0x78`. After the slot's padding comes one 66,560-byte block (256 × 256 PSMT8 indices in GS block order, then a 1,024-byte palette; original and Mercedes profiles), or four levels of 65,536, 16,384, 4,096 and 2,048 bytes with 28-byte level headers between them (Remix; the last block is 32 × 32 indices plus the palette). All 94 packages hold exactly one such slot, and the shared `_g.pck` stock resources carry their own.
- **Shared `.tex`.** A 14-byte header (`u16` width, height, format, level count, ...), a 1,024-byte RGBA palette, then linear 8-bit levels; alpha is already 0–255. 85 shared texture names exist; duplicate occurrences must be byte-identical.
- **`pf05` page slots** (rim and tire pages, Remix profile). A slot's word at `+0x4C` is the page offset of its block; the block header word at `+0x0C` is the block size; image data (`size − 0x100` bytes, square indices then palette) starts 0x90 into the block. Of 108 selected pages, one primary slot (`whl_rm_belaire_57_h`, a 384-byte block) is not a square 8-bit block and stays undecoded. 38 other pages skip only secondary `_b1`/`_b2` mip or layer slots, which are not diffuse images.

Decoder choices were fixed by the images and cross-checked externally:

- GS 8-bit block order uses the repository's existing `ps2_container.unswizzle8`. On the Corvette atlas the mean neighbour step is 50.9 with block order and CSM1 palette, against 60.7 with block order only, and 217–220 without block order. A test requires that ordering to win and to beat the unordered variants by at least a factor of three.
- CSM1 palette order swaps entries 8–15 with 16–23 in every 32. The public PS2 emulator source `jpd002/Play-` (`Source/gs/GSHandler.cpp`, lines 1568 and 1684) uses the same index expression. The fetched snippet was screened by `jev_screen` (injection 0.03, pass; [receipt](evidence/midnight-club-3-remix/previews/textures-fix/screen-clut-snippet.json)).
- PCK palettes use alpha 0–0x80 (scaled ×2, clamped); shared `.tex` palettes are used unscaled. The latter's `vp_shadow` palette reaches 255.
- UVs are the packet integers divided by 4096 with the stored V (no flip). The livery lettering on the Aprilia tank and belly reads upright and unmirrored in the dealership renderer. There is no numeric orientation oracle; the sprocket outline was tried as one and does not discriminate, and this note does not claim one.

## Binding a material to its texture

An earlier approach matched strings near the material for names such as `exh_02` or `grill_00`. Those are also bone names, and they bound exhaust textures to paint on the Bel Air and 1969 Charger (a striped checker across the body). The binder now follows the object layout, confirmed in Ghidra on `SLUS_213.55` and against every material in the corpus:

- `+0x10` points to an array of texture-reference pointers, the byte at `+0x20` is its length (at most 8 in the corpus), and `+0x28` points to the shader template name. `FUN_002aff88` constructs this base class, and the template text loader `FUN_002b06b8` fills the same list ([receipts](evidence/midnight-club-3-remix/previews/textures-fix/ghidra/)).
- Each reference is a parameter entry (class `0x7A1260` plus delta: name pointer at `+8`, then an embedded-slot pointer or a name hash) or a slot object.
- A composite wrapper lists sub-materials at `+0x30` (count at `+0x38`), each with its own template name. The corpus has three kinds: `car_decal` + `car_decal_chrome` (75), `carpaint` + `carbon_fiber` (72) and `carpaint_novinyl` + `carbon_fiber` + `chrome` (24).

Across all 2,396 non-wrapper materials the pointer lists parse without error. Every `lit_textured` (291), `default_shiny` (124), `rubber` (90), `carbon_fiber` (29), `drop_shadow` (94) and `emissive_*` material resolves a texture; `carpaint`, `chrome`, `aa_chrome`, `aa_trim`, `car_window`, `colored_glass`, `licenseplate` and wrappers resolve none. Template names read this way are exact; a string scan had produced pooled-suffix fragments such as `chrome_wheemore_chrome_wheel_hi_lod`.

## Display policy

Applied in the converter (`tools/mc3_model.py`, `bind_textures`) from `texture_policy`:

- Textured materials use their image with a white colour factor; `MASK` at 0.5 when the image has transparent texels, otherwise `OPAQUE`; shaders named `*_no_alpha` ignore image alpha.
- `car_decal` wrappers are drawn fully transparent, because their texture is the runtime `__logo__` slot, which is not on the disc. The geometry stays in the GLB.
- `wheel_floating_poly` is drawn transparent. `FUN_003bd4d0` registers a runtime `rimSpeed` parameter with default 0; that this polygon is a speed-driven blur surface is an inference from its name and that parameter, not a traced behaviour.
- Ground shadow quads are omitted. Every draw of such a part uses the `drop_shadow` template (`FUN_003b8e18`: texture `vp_shadow`, parameters `shadowR/G/B/A` defaulting to 1, 0, 0, 1 and `isAdditive` 0). Previously 87 `neonglow.mesh` parts were dropped by name while 7 differently named shadow quads were kept. The rule is now material-based and uniform: 94 effect planes are recorded in the index, and the 7 kept quads account for the total change from 749,871 to 749,843 triangles (four each: CLK GTR, Corvette 1968, Corvette 1963, Eclipse, Esprit, Golf R32, GTO 1970).
- Environment, specular, metal-flake, paint, licence-plate and logo slots are runtime-bound and unresolved. Paint stays a neutral inspection colour.

## Result

The corpus is 59,319,640 bytes (was 46,827,416), 749,843 triangles, with 2,488 textured meshes in the working copies; the renderer test counts 2,082 alpha-tested meshes and 386 blended meshes (glass, transparent decals and rim polygons). Triangle counts differ from the previous conversion only for the seven shadow cars. All 94 conversions reload bit-identically through `tools/export_mc3_models.py`; the dealership working copies were refreshed with `import_mc3_previews.py --refresh-unedited`, none having been edited. The 891 other-game entries in each of the four catalogs, the 94 native packages and every MC3 `initialSource` are unchanged; 21,689 of the 21,691 entries pinned before promotion (other games' files, native extraction, native packages, other-game working models, the ISO size) match, and the other two are catalog digests whose filter mishandled `origins.json`, compared directly instead ([receipt](evidence/midnight-club-3-remix/previews/textures-fix/preservation/catalog-preservation.json)). The previous canonical corpus and dealership copies are hashed in `preservation/previous-canonical-and-dealership-copies.sha256.json`.

All 94 models were rendered from front, rear and side (and top for the shipped copies) through the real `loadCar` code and reviewed on 19 contact sheets in `renders/audit-sheets/`, covering original, Remix and Mercedes profiles, 79 cars and 15 motorcycles.

Controls ([`tools/test_mc3_textures.py`](../tools/test_mc3_textures.py), 26 tests):

- Synthetic fixtures for every profile and level layout, each corruption rejected for its own reason (short or long block, missing padding, bad name pointer, duplicate names, wrong profile, non-image slots, a first pixel equal to the padding byte).
- Shared `.tex`: malformed size, dimensions, level count; divergent duplicate occurrences.
- Material objects: oversized list, a list entry that is neither parameter nor slot, bad template pointer, unreadable name, bad wrapper counts; node-name strings beside a material that must not bind.
- Corpus checks: every package decodes one slot; swizzle and palette order win on the real image; binding coverage is exact; every template name is in the known set; every selected wheel page binds and effect polygons keep no texture.
- GLB transport: texture, `TEXCOORD_0`, alpha cut-off and embedded PNG; missing texture key and malformed UVs rejected.
- Seven injected defects (identity palette, no unswizzle, unscaled alpha, shadow keeps its texture, wrapper textured, ignored list length, any block size accepted) each fail at least one test.
- `tools/test_mc3_preview_ui.mjs` loads all 94 working copies in the dealership renderer with a strict PNG decoder and checks UVs, white colour factors, alpha tests and blends, and a corrupt-texture rejection. `tools/test_mc3_roundtrip.py` now requires Blender 4.5.14 to keep embedded images, texture bindings, UVs and alpha modes through import, edit and export.

The final run of `tools/check.sh` recorded 63 passes, no failures and no skips ([manifest](evidence/midnight-club-3-remix/previews/textures-fix/checks/results.json)).

## Geometry gap (separate from textures)

Many mesh-less parts in each package are filled from `.mesh.pck` members of the car's own DAT, but the converter only attaches parts whose names contain `_stk_`. Across the corpus 3,488 mesh-less parts have an external file but no `_stk_` name, against 317 that do. 43 cars hold eight or fewer such parts. For `VP_CORVETTEZ06_03` the hood (`hd_hd_h`), front and rear bumpers, tail-lamp lens, side skirts and headlights are absent, so the hood opening shows the engine bay, the rear panel is black, and the masked-chrome sliver floats. Larger packages are kit libraries (20–110 parts) whose default part is chosen by `default.mccarcustom` indices (for the Z06 all `0`). A safe selection rule needs that table mapped to bone names, which vary by car (`bmpf`, `bumf`, `f_bumpers`); it is not guessed here and remains open ([research index](README.md)).

## Jev and TypeSafe

`jev_screen` passed the one external snippet used. A bounded `jev_classify` experiment judged 47 distinct (shader template, binding facts) combinations into diffuse-texture, neutral-surface and effect-plane classes: 45 agree with the code policy and 43 of 47 were auto decisions, all correct. The two disagreements (`drop_shadow`, `car_decal` wrapper) were both flagged `review` (confidence 0.52 and 0.25). Usage was 6,094 input and 1,920 output tokens in one request; provider cost is not reported by the tool and is unknown. The experiment shows that effect surfaces are not reliably identified from names and facts alone, so the policy stays deterministic, keyed on the exact template names read from the objects.

## Not established

Native paint colours (the default customization data holds `m_paintColor1`), paint names, environment, specular and metal-flake shading, the runtime logo, licence-plate and damage textures, native GS blending and 4-bit or non-square page blocks. UV orientation is verified by rendered lettering, not numerically. Hiding the rim-blur polygon and the decal layer are display decisions. Texture evidence is static decoding checked against rendered output, not an emulator capture.
