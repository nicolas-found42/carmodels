# Modern techniques for visual quality of a low-poly textured car GLB in three.js r182

Read-only web research, primary sources only. Corpus: 35 recovered Ford Racing 2 (PS2, PAL) cars exported as GLB and shown offline in a static three.js r182 viewer. Question: which modern techniques most improve *perceived* quality of a ~10–30k-triangle textured car, and which are safe without misrepresenting recovered data. Every claim carries its source URL; repo facts are cited by file path. Effort/impact figures are **my estimates**, not sourced.

Repo baseline: exporter writes one glTF sampler `magFilter 9728 / minFilter 9728` (NEAREST) and `doubleSided true, metallicFactor 0, roughnessFactor 1` (`tools/export_geometry_candidates.py:46,76-77`). The viewer builds geometry by hand (no GLTFLoader) with `MeshStandardMaterial{roughness:1, metalness:0, side:DoubleSide}`, `magFilter=NearestFilter`, `SRGBColorSpace`, hemisphere + one directional light, no tone mapping, no environment, no ground (`dealership/recovered.html:28,31,45,46`). three.js is vendored at r182 (`dealership/vendor/three.module.js`).

---

## 1. Paint and glass materials (MeshPhysicalMaterial)

- `MeshPhysicalMaterial` adds clearcoat (car paint/lacquer), iridescence, physically-based transmission (glass), thin-specular, sheen and anisotropy to `MeshStandardMaterial`; all off by default, each adds per-pixel cost. "For best results, always specify an environment map." Documented defaults: `clearcoat 0`, `clearcoatRoughness 0`, `transmission 0`, `thickness 0` (0 = thin-walled), `iridescence 0`, `sheen 0`, `ior 1.5`; with `transmission != 0`, `opacity` should stay 1. https://threejs.org/docs/pages/MeshPhysicalMaterial.html
- `KHR_materials_clearcoat` (ratified) persists `clearcoatFactor`/`clearcoatRoughnessFactor` in the GLB, so paint coating survives export rather than being a runtime-only tweak. https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_clearcoat/README.md (registry: https://github.com/KhronosGroup/glTF/blob/main/extensions/README.md)
- Transmission vs alpha: glTF `alphaMode` encodes "alpha as coverage" (does the surface exist?), not light transport; a physically transmissive material should be `OPAQUE` even though it looks transparent. Alpha-0 coverage makes glass vanish, whereas real glass stays visible through reflection; and for `metallicFactor = 1.0` `transmissionFactor` has no effect (metals absorb refracted light). https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_transmission/README.md
- `KHR_materials_ior` (ratified) lets glass carry a real IOR (window glass 1.52) instead of the fixed 1.5. https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_ior/README.md
- three.js r182 `GLTFLoader` supports `KHR_materials_clearcoat`, `_transmission`, `_volume`, `_ior`, `_iridescence`, `_sheen`, `_specular`, `_anisotropy`, `_emissive_strength`, so an enriched GLB renders as authored. https://github.com/mrdoob/three.js/blob/dev/examples/jsm/loaders/GLTFLoader.js
- Official `webgl_materials_car`: body `{metalness 1.0, roughness 0.5, clearcoat 1.0, clearcoatRoughness 0.03}`, glass `{metalness 0.25, roughness 0, transmission 1.0}`, details `MeshStandardMaterial`, `ACESFilmicToneMapping` exposure 0.85, `scene.environment` = a real 1k equirect HDR. It does **not** model paint flakes (the "metallic paint" is clearcoat + envMap + metalness only), loads its envMap directly with `EquirectangularReflectionMapping` (no PMREMGenerator), and its ground shadow is a baked AO PNG on a plane with `MultiplyBlending`, `toneMapped:false`, `premultipliedAlpha:true` — not a shadow map. https://github.com/mrdoob/three.js/blob/dev/examples/webgl_materials_car.html

**Implication for this repo.** Clearcoat/transmission/ior are the biggest cheap win and map onto the glTF the exporter already emits, but the body/glass/trim split is per-part recovered state still unresolved here — apply them as a clearly-labelled *enhanced* material set over the candidate meshes, never as "the original GS shading", and keep the neutral `MeshStandardMaterial` path as the honest baseline. **Effort ~4–8 h; impact high.**

## 2. Environment lighting, tone mapping, ground, anti-aliasing

- `PMREMGenerator.fromScene()` builds a prefiltered, mipmapped radiance environment map from a Scene and can be faster than an image when bandwidth is low (GGX VNDF sampling, Heitz 2018). https://threejs.org/docs/pages/PMREMGenerator.html
- `RoomEnvironment` is a basic room Scene purpose-built as input to `PMREMGenerator.fromScene`; the result goes to `scene.environment` for image-based lighting — offline-friendly, no external asset. https://threejs.org/docs/pages/RoomEnvironment.html
- Alternatively a real HDRI: Poly Haven licenses all HDRIs, textures and models CC0 (public domain), commercial use allowed, no attribution required — safe to vendor. https://polyhaven.com/license
- `renderer.toneMapping` supports `NoToneMapping, LinearToneMapping, ReinhardToneMapping, CineonToneMapping, ACESFilmicToneMapping, CustomToneMapping, AgXToneMapping, NeutralToneMapping`; default `NoToneMapping`. `outputColorSpace` defaults to `SRGBColorSpace` (already correct). https://threejs.org/docs/pages/WebGLRenderer.html
- Khronos PBR Neutral reproduces a product's base colour/hue under PBR and avoids HDR highlight artifacts; it complements ACES, which is more filmic/stylised. three.js exposes it as `NeutralToneMapping`. https://www.khronos.org/news/press/khronos-pbr-neutral-tone-mapper-released-for-true-to-life-color-rendering-of-3d-products
- Contact shadows (`webgl_shadow_contact`) render the scene to a target with a depth override material from an overhead ortho camera, blur it, and paint it on a plane — a flat, non-physical fake that cannot self-shadow. https://github.com/mrdoob/three.js/blob/dev/examples/webgl_shadow_contact.html · `SSAOPass` is a post pass for contact darkening between parts: https://github.com/mrdoob/three.js/blob/dev/examples/webgl_postprocessing_ssao.html
- Anti-aliasing: `antialias:true` selects default MSAA, default `false` (https://threejs.org/docs/pages/WebGLRenderer.html); SMAA runs in linear-sRGB and must precede `OutputPass` (https://github.com/mrdoob/three.js/blob/dev/examples/jsm/postprocessing/SMAAPass.js); FXAA is the cheaper pass for the end of the LDR/sRGB chain (https://github.com/mrdoob/three.js/blob/dev/examples/webgl_postprocessing_fxaa.html).

**Implication for this repo.** An env map plus a tone mapper is the highest perceived-realism-per-effort change, and RoomEnvironment + PMREM keeps the viewer fully offline. Default to `NeutralToneMapping` (colour-faithful, keeps recovered liveries close to source hues) and offer ACES as a labelled "showcase" toggle. **Effort ~4–6 h; impact high.**

## 3. Texture sampling: filtering, mipmaps, anisotropy

- glTF samplers encode `magFilter` (`9728` NEAREST, `9729` LINEAR) and `minFilter` (adds `9984/9985/9986/9987` mipmap variants); minification modes include the nearest/linear-mipmap variants (trilinear). https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/schema/sampler.schema.json
- The spec says implementations **SHOULD** generate mipmaps at runtime, and when they cannot, **SHOULD** downgrade mipmap minification to plain NEAREST/LINEAR. https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc
- three.js `GLTFLoader` sets `generateMipmaps=false` whenever `minFilter` is `NearestFilter` or `LinearFilter`, so the repo's NEAREST/NEAREST sampler disables mipmaps for any spec-compliant consumer. https://github.com/mrdoob/three.js/blob/dev/examples/jsm/loaders/GLTFLoader.js
- `Texture` defaults: `magFilter LinearFilter`, `minFilter LinearMipmapLinearFilter`, `generateMipmaps true`, `anisotropy 1`; higher `anisotropy` is less blurry at grazing angles at the cost of more texture samples; and `generateMipmaps=false` is the documented switch when supplying your own mip chain. https://threejs.org/docs/pages/Texture.html
- Repo nuance: `recovered.html` hand-loads PNGs via `TextureLoader` and sets only `magFilter=NearestFilter`, so `minFilter` stays `LinearMipmapLinearFilter` and mipmaps *are* generated there — the "no mipmaps" effect applies to GLTFLoader consumers of the GLB, not this viewer. `dealership/recovered.html:45`; https://github.com/mrdoob/three.js/blob/dev/examples/jsm/loaders/GLTFLoader.js

**Implication for this repo.** LinearMipmap(Linear) minification plus high `anisotropy` removes the shimmer/aliasing that dominates a moving low-res textured model, and alters no texel. Correction from repo evidence: the captured game draws set `TEX1=0x60` (linear min/mag, MXL=0, no mip levels; `research/packet-continuation.md` lines 17, 29, 119), so the original used **linear** sampling, not point sampling. The viewer's NEAREST magnification is therefore the departure from the original; plain linear (no mips) is the faithful setting, and mips/anisotropy are an enhancement. **Effort ~1–3 h; impact med.**

## 4. Texture upscaling/restoration for 128–256px paletted PS2 textures

- Real-ESRGAN is **BSD 3-Clause** (© 2021 Xintao Wang): https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE · its portable `Real-ESRGAN-ncnn-vulkan` port is **MIT**: https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/blob/master/LICENSE
- Real-ESRGAN targets *general* restoration and also ships anime-specific models (`RealESRGAN_x4plus_anime_6B`), which its own docs compare against waifu2x — the anime model is tuned for flat-colour line art, not photorealism. https://github.com/xinntao/Real-ESRGAN/blob/master/docs/anime_model.md
- waifu2x is **MIT** (© 2015 nagadomi), "Image Super-Resolution for Anime-style art … And it supports photo", with a separate photo model (`-model_dir models/photo`); its README notes the demo image is separately licensed (CC BY-NC). https://github.com/nagadomi/waifu2x/blob/master/README.md
- PS2 community practice: PCSX2 texture replacement identifies each texture by a **hash-derived filename** (base hash, optional CLUT hash, region size), loads user HD replacements, and can dump original textures and mipmaps; the code is **GPL-3.0+** (a tool licence, not an asset licence). https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp (settings labels Load/Dump Textures, Dump Mipmaps, Precache, Search Directory: https://github.com/PCSX2/pcsx2/blob/master/pcsx2-qt/Settings/GraphicsTextureReplacementSettingsTab.ui)
- Artifact caveat: no upscaler repo fetched here documents its failure modes on indexed/paletted low-res art (hallucinated detail, ringed edges, invented texels) in a checkable form; that they invent detail the source never held is my expectation from practice, **not** proven by a primary source fetched here. (searched: https://github.com/xinntao/Real-ESRGAN , https://github.com/nagadomi/waifu2x)

**Implication for this repo.** Upscaled textures are enhancement, never recovery: put them behind the "enhanced" label with tool, model name and version recorded, and never replace the decoded originals in the recovered path. If used, prefer the **photo/general** models, because the source is paletted photographic liveries, not line art. **Effort ~6–12 h (incl. pipeline + labelling); impact med, high honesty risk if careless.**

## 5. Geometry-side quality

- `BufferGeometryUtils.mergeVertices(geometry, tolerance=1e-4)` builds/optimises an index buffer by merging duplicate vertices — directly applicable to the exporter's per-sample vertices. `toCreasedNormals(geometry, creaseAngle=Math.PI/3)` gives smooth normals everywhere except across faces meeting at an angle greater than the crease angle, replacing flat per-face normals without over-smoothing hard panel edges. https://github.com/mrdoob/three.js/blob/dev/examples/jsm/utils/BufferGeometryUtils.js
- glTF: `doubleSided:false` enables back-face culling; `true` renders both sides and negates back-face normals — so double-siding also flips lighting. https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc · three.js `Material.side` defaults to `FrontSide`: https://threejs.org/docs/pages/Material.html
- `KHR_materials_emissive_strength` (ratified) adds a scalar above the core `emissiveFactor` cap of 1.0; values > 1 affect reflections, tonemapping and bloom. https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_emissive_strength/README.md · `THREE.LOD` switches between supplied meshes at distance thresholds: https://threejs.org/docs/pages/LOD.html

**Implication for this repo.** Welding alone changes little (the stored normals are unit-length on 656,687 of 657,139 samples and the current render is smooth), and recomputed creased normals would replace recovered data with invented data, so this is low value here; if done at all keep it opt-in and labelled. (Reviewer correction: an earlier draft claimed it fixes a "faceted" look; nothing in the repo shows one.) Culling turns on only once winding is proven; until then `doubleSided:true` is the honest default. **Effort ~4–6 h (weld+normals), ~2 h (emissive); LOD not needed at this poly count; impact med.**

## 6. Offline path-traced presentation tier (Blender Cycles)

- Cycles is Blender's physically-based path tracer, designed for physically-based results out of the box. https://docs.blender.org/manual/en/latest/render/cycles/index.html · Blender is GPL, and the GPL governs the program, not the images rendered or assets loaded: https://docs.blender.org/manual/en/latest/getting_started/about/license.html
- A GLB is a complete transport container (geometry + materials + images), so Blender imports the same recovered asset the viewer shows, giving a second higher-fidelity rendering of identical source data. https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc

**Implication for this repo.** A Cycles still is the strongest *presentation* layer and needs no change to the offline viewer, but it renders the *candidate/enhanced* asset, so it must be captioned as such and shipped alongside the real-time view, not instead of it. **Effort ~8–16 h; impact high (presentation only).**

---

## Estimate summary (mine)

| # | Technique group | Effort | Visible impact |
| --- | --- | --- | --- |
| 1 | Physical paint/glass materials | 4–8 h | high |
| 2 | Env lighting + tone mapping + ground + AA | 4–6 h | high |
| 3 | Filtering/mipmaps/anisotropy | 2–3 h | med |
| 4 | Texture upscaling (enhanced only) | 6–12 h | med |
| 5 | Weld + creased normals (+ emissive/LOD) | 4–8 h | med |
| 6 | Offline Cycles presentation renders | 8–16 h | high (presentation) |

## Jev trail

- `jev_screen` on the 6 rendering/spec fetch groups → all **pass** (injection ≤0.02, substance ≥0.88, relevance ≥0.85); used them.
- `jev_screen` on the license/pcsx2/blender groups first returned **skip** (relevance 0.24/0.04/0.08) because my purpose said "rendering techniques" while the text is licensing/workflow; re-screened with a licence/provenance purpose → all **pass**; used them. An unrelated probe text → **skip** (0.27); discarded.
- `jev_rerank` on 20 candidate URLs → MeshPhysicalMaterial docs, KHR clearcoat/transmission, PMREM, Texture docs ranked top 5; car example 10th, contact-shadow 19th, PCSX2 *wiki* 20th (0.03). I demoted them and replaced the PCSX2 wiki page with the PCSX2 repo source as the primary source.
- `jev_classify` (22 techniques, 4 classes) → 12 rendering, 5 texture, 4 geometry, 1 tooling. The one `review` item (pcsx2: 0.81 texture / 0.19 tooling) is written up in the texture section with its tool licence also noted.
- `jev_noul` (15 propositions) → clear ones ≥0.86 likely (Blender GPL, Poly Haven CC0, PCSX2 hashing, repo sampler/mipmap fact, anisotropy, honesty framing); every "defaults" proposition came back 0.57–0.84 *uncertain*, so I stopped relying on recall and re-derived each default from the fetched docs.
- `jev_verify` (16 claims vs 13 fetched source documents) → **16 verified, 0 contradicted, 0 unsupported**; no claim dropped. This is why §1's "paint flakes" premise was corrected to "the example does not do flakes", and §2/§3 defaults are cited to docs rather than asserted.
