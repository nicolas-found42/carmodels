# Visual fidelity: ground truth and PS2 game shading

Read-only web research (primary sources), 2026-10-06. Scope: how to shade a recovered PS2 car so it matches the
original final image in three.js r182, and how to obtain an authoritative reference image. Every claim is followed
by its source URL; items the sources did not settle are marked **open**.

---

## 1. PS2 GS alpha blending, fixed-point alpha, alpha test, stored texture alpha

- The GS blend equation is fixed; only its operands are reconfigurable: `Output = (((A - B) * C) >> 7) + D`, where
  A, B, D are colours and C is an alpha value; the operands come from the ALPHA register spec A/B/C/D (0=source,
  1=framebuffer, 2=FIX, 3=reserved), and `>> 7` is the fixup for the 0..128 alpha scale.
  https://psi-rockin.github.io/ps2tek/#gsalphablending
- **Yes, 0x80 = 1.0.** The right shift by 7 makes C a 0..128 fixed-point alpha; PCSX2 says so in prose, reads the
  framebuffer alpha as `Ad = RT.a / 128.0f`, and clamps `C_clamped = min(C_clamped, 1.0f)`, commenting "alpha is
  in 1/128 increments". https://github.com/PCSX2/pcsx2/blob/master/bin/resources/shaders/opengl/tfx_fs.glsl
- 8-bit alpha values are stored on that same 0..128 scale: PCSX2 de-normalises 8-bit surfaces with
  `uvec4(c * 255.5f)` (32-bit) and `uvec4(round(c * 128.25f))` (16-bit), i.e. alpha 0x80 is one.
  https://github.com/PCSX2/pcsx2/blob/master/bin/resources/shaders/opengl/tfx_fs.glsl
- A = B is a legal case and PCSX2 collapses it to `Color.rgb = D`; software blending otherwise applies
  `trunc((A - B) * C + D)`, matching the hardware expression. https://github.com/PCSX2/pcsx2/blob/master/bin/resources/shaders/opengl/tfx_fs.glsl
- The texture function multiplies vertex colour and texel on the same 128 scale: `FxT = trunc((C * T) / 128.0f)`
  for Modulate (TEX0 colour function 0=Modulate, 1=Decal, 2=Highlight, 3=Highlight2).
  https://github.com/PCSX2/pcsx2/blob/master/bin/resources/shaders/opengl/tfx_fs.glsl ,
  https://psi-rockin.github.io/ps2tek/#gstextures
- Texture alpha in storage is 0..128, not 0..255: TEX0 bit 34 selects "texture is RGB" vs "texture is RGBA"; the
  shader substitutes TEXA TA0 (texel alpha == 0) and TA1 (texel alpha set) instead of scaling by 255.
  https://psi-rockin.github.io/ps2tek/#gstextures ,
  https://github.com/PCSX2/pcsx2/blob/master/bin/resources/shaders/opengl/tfx_fs.glsl
- Alpha **test** is a separate 0..128 comparison: TEST bit 0 enables it, bits 1-3 are the method (NEVER, ALWAYS,
  LESS, LEQUAL, EQUAL, GEQUAL, GREATER, NEQUAL) against AREF (bits 4-11), with per-failure framebuffer/zbuffer
  write options and a destination-alpha test (bit 14). PCSX2 compares `a <= AREF`, `a >= AREF`, `abs(a-AREF) <= 0.5`.
  https://psi-rockin.github.io/ps2tek/#gstestsandpixelcontrol ,
  https://github.com/PCSX2/pcsx2/blob/master/bin/resources/shaders/opengl/tfx_fs.glsl
- Blending is opt-in per primitive: PRIM bit 6 (Alpha blending) must be set. In the repo's captured car interval the
  106 textured geometry tags use PRIM `0x1c` (ABE=0, drawn opaque, TEX1=`0x60` linear min/mag, MXL=0 so no mip levels),
  while the one untextured 7-vertex tag (transfer 5906) uses PRIM `0x4c` (ABE=1) with ALPHA_1 `0x44` =
  `(Cs-Cd)*As+Cd` and RGBA [0,0,0,102], which does blend.
  https://psi-rockin.github.io/ps2tek/#gsprimitives , `research/packet-continuation.md` lines 29, 60, 119
  (corrected by the reviewer: an earlier draft said ABE was off for the whole interval)
- **Implication for this repo:** the current `display alpha = min(255, 2*a)` is the correct 8-bit *encoding* of a
  0..128 GS alpha on the same scale, but "2*a" is a scale remap, not a blend law — do not use it as opacity
  without also modelling ABE/TEXA/alpha test.
- **Implication for this repo:** in the viewer, feed opacity as `a/128` (not `a/255`) and set `transparent`/
  `alphaTest` explicitly, because three.js skips blending when `transparent === false` (see §2).

## 2. Reflection/environment passes on VU1 and their WebGL/three.js reproduction

- The pass-4 microcode is a paraboloid environment map: reflect V about N, transform by the retained matrix, then
  `s = 0.5·x′/(−1−|z′|)+0.5` … `t = −0.5·y′/(−1−|z′|)+0.5` scaled by Q; pass 5 is a specular-intensity lookup
  with `s = max(0.5·((R+V)·V) − 0.5, 0)·Q`, `R = 2(N·DM[6])N − DM[6]`. The names ("reflection map", "specular") are
  readings of the arithmetic. `research/packet-continuation.md` §"VU1 pass 4 and pass 5 handlers" ,
  `research/vu-handler-dump.md`
- The 0.5·x/(−1−|z|)+0.5 form is the standard paraboloid (dual-paraboloid) environment-map parameterisation used
  for PS2-era sphere/reflection mapping; the same reflected-view-vector construction appears in OpenGL/three.js
  envmap sampling. https://psi-rockin.github.io/ps2tek/#vu ,
  https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderChunk/envmap_fragment.glsl.js
- three.js already ships both halves: `MeshBasicMaterial`/`MeshStandardMaterial` with `envMap` sample the map by
  `reflectVec = reflect(cameraToFrag, worldNormal)` (mode `ENVMAP_MODE_REFLECTION`), blended by `reflectivity`.
  https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderChunk/envmap_fragment.glsl.js ,
  https://github.com/mrdoob/three.js/blob/dev/src/materials/MeshBasicMaterial.js
- `Scene.environment` applies one environment map to every physical material that has no `envMap` of its own — the
  cheapest way to give all car parts a shared reflection without per-part wiring.
  https://github.com/mrdoob/three.js/blob/dev/src/scenes/Scene.js ,
  https://github.com/mrdoob/three.js/blob/dev/src/materials/MeshStandardMaterial.js
- `MeshMatcapMaterial` is the closest built-in to the pass-4 lookup: it builds a 2D coordinate from the
  **view-space normal** — `vec2 uv = vec2(dot(x, normal), dot(y, normal)) * 0.495 + 0.5` — so an authored
  reflection-map texture is indexed by surface orientation alone.
  https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderLib/meshmatcap.glsl.js
- For the exact formulas use a `ShaderMaterial`, or customise a built-in pass with
  `material.onBeforeCompile(shader, renderer)` (cache key defaults to `onBeforeCompile.toString()`).
  https://github.com/mrdoob/three.js/blob/dev/src/materials/Material.js
- Blending in three.js is GL-style, not GS-style: `NormalBlending` (non-premultiplied) is
  `blendFuncSeparate(SRC_ALPHA, ONE_MINUS_SRC_ALPHA, ONE, ONE_MINUS_SRC_ALPHA)`, i.e. `src·srcAlpha + dst·(1−srcAlpha)`;
  an opaque (`transparent === false`) NormalBlending material is switched to `NoBlending` entirely.
  https://github.com/mrdoob/three.js/blob/dev/src/renderers/webgl/WebGLState.js
- **Implication for this repo:** the viewer's `MeshStandardMaterial(roughness 1, metalness 0, DoubleSide)` has no
  reflection and no specular, so it cannot reproduce pass 4/5; switch reflection parts to a matcap or
  envMap material (or an `onBeforeCompile` shader) and render the two passes as separate materials.
- **Implication for this repo:** since GS `Modulate` is `trunc((C*T)/128)` and three.js `map` multiplies the
  texel by `diffuse` in the same normalised space, texture×vertex-colour is already equivalent — the missing
  fidelity is the environment/specular terms, not the base modulation.

## 3. Ground-truth reference: PCSX2 headless replay, screenshots, GS dumps, texture dumping

- PCSX2 boots headless and unattended: `-nogui` "Hides main window while running (implies batch mode)",
  `-batch` exits after shutting down, `-statefile <filename>` loads a savestate, `-datapath <path>` relocates data,
  and a bare `[boot filename]` runs a game.
  https://pcsx2.net/docs/advanced/cli
- PCSX2 boots a `.gs` dump **directly** as a replay: `VMManager` tests `IsGSDumpFileName(filename)` and calls
  `GSDumpReplayer::Initialize`; replay needs no BIOS and no disc, MTUV is forced off, and the replayer supports a
  frame range and a loop count. https://github.com/PCSX2/pcsx2/blob/master/pcsx2/VMManager.cpp ,
  https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GSDumpReplayer.cpp
- The dump header carries `state_version, state_size, serial, crc, screenshot_width/height/offset/size`, preceded by
  the `0xFFFFFFFF` marker and a header-size word; PCSX2 writes it in `GSDumpBase::AddHeader`.
  https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/GSDump.h ,
  https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/GSDump.cpp
- Screenshots are produced by the same path in GUI and headless runs: `GSQueueSnapshot(path, 0)` saves a PNG and
  `GSQueueSnapshot(path, 1 / max)` saves a single- or multi-frame GS dump; these back the Screenshot,
  "Save Single Frame GS Dump" and "Save Multi Frame GS Dump" hotkeys.
  https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/GS.cpp
- For scripted N× captures, the `pcsx2-gsrunner` target is the supported automation: it accepts `-dumpdir`,
  `-renderer`, `-upscale`, `-dump`, `-dumprange`/`-dumprangef` and `-loop`, and writes one PNG per frame as
  `{prefix}_frame{N}.png` via `GSQueueSnapshot`; `test_run_dumps.py -runner … -dumpdir … -gsdir … -renderer …`
  drives it per dump. https://github.com/PCSX2/pcsx2/blob/master/pcsx2-gsrunner/Main.cpp ,
  https://github.com/PCSX2/pcsx2/blob/master/pcsx2-gsrunner/test_run_dumps.py ,
  https://pcsx2.net/docs/advanced/gsdumprunner
- Texture dumping/replacement is in-tree and separate from screenshots: `DumpTexture` writes into a `dumps`
  subdirectory when `DumpReplaceableTextures`/`LoadTextureReplacements` are set, with a PNG loader and
  `SavePNGImage`. https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/Renderers/HW/GSTextureReplacements.cpp
- The repo already holds two replayable dumps: `research/evidence/continuation/runtime/snaps/*.gs.zst` (and a
  linux copy) parse as `marker 0xffffffff, header_size 1228846, state_version 9, serial SLES-51705,
  disc_crc 0x37f695cd, screenshot 640×480` — the current dump format of §3 above. `research/evidence/packet-continuation/race94-trace.json`
- The three PNG screenshots in `research/evidence/continuation/runtime/` (`race94-Screenshot.png`,
  `menu93-original-screenshot.png`, `loading-Screenshot.png`) measure 640×480, i.e. native display size.
- Replay and capture render through the normal GS pipeline, so a replayed dump at native resolution is an
  authoritative reference needing no disc; whether an N× upscale stays faithful is **open** (Jev noul: upscaled
  replay faithful 0.77, 640×480 is native 0.42).
- **Implication for this repo:** the missing ground truth is one command away —
  `pcsx2-qt -nogui -batch -datapath <dir> -- "<…>.gs"` (or `pcsx2-gsrunner -dumpdir … -upscale 1`) on the existing
  dumps, giving per-frame PNGs of the exact car state already captured.
- **Implication for this repo:** capture at native resolution for fidelity comparisons; treat upscaled output as a
  readability aid only, and use `dumps/` texture replacement to confirm the decoded car textures against the GS.

## 4. Existing projects that render PS2 VU1/GS-style car shading

- `mholeys/roadtrip-choroq-tools` (Road Trip Adventure / ChoroQ HG2/HG3, PS2) exports PS2 car meshes, but its OBJ
  writer emits only `usemtl` and geometry (`s off`), with no specular, environment-map, matcap or glass handling;
  the only alpha logic found is a palette round-trip mapping a full alpha byte 255 back to `0x80` (1.0 on the GS
  scale). It splits cars into named meshes (body, front/rear lights for night rendering) and concedes the mapping
  is not exact ("HG2's palette alpha is not just simple values, might have a map").
  https://github.com/mholeys/roadtrip-choroq-tools/blob/master/choroq/egame/car.py ,
  https://github.com/mholeys/roadtrip-choroq-tools/blob/master/choroq/texture_utils.py ,
  https://github.com/mholeys/roadtrip-choroq-tools/blob/master/docs/HG2_HG3.MD
- `aap/xtc` is a working open-source PS2 VU1/DMA/GIF renderer with VU1 microcode sources — the closest reference
  for reproducing VU-generated passes in a custom renderer; `chaoticgd/vutrace` traces the live VU1 in PCSX2 for
  verifying the decoded handler path. https://github.com/aap/xtc , https://github.com/chaoticgd/vutrace ,
  `research/visualization-libraries.md` §(b)/(d)
- No project found renders this corpus's VU1 pass-4/5 shading in three.js/Blender/WebGL; the community tools stop
  at model+texture extraction. `research/visualization-libraries.md` §(a), "no FR2 tooling exists anywhere in
  public code". **open** for any tool that reproduces GS reflection/specular specifically.
- **Implication for this repo:** there is no off-the-shelf shading reference to copy — the pass-4/5 microcode in
  `research/packet-continuation.md` is our own source of truth, and community prior art only informs glass/alpha.
- **Implication for this repo:** borrow the two practical conventions from choroq-tools — split parts into separate
  named materials, and treat alpha 0x80 as opaque one — but do not inherit its OBJ-only, shading-free output.

---

## Jev trail

- `jev_rerank` #1 (10 PCSX2 CLI/dump candidates) → top: official CLI docs 0.92, Debian manpage 0.78, GSdx wiki 0.72.
  Opened the reachable winners; dropped the wiki (Cloudflare 403).
- `jev_rerank` #2 (10 shading/env-map candidates) → top: MeshMatcapMaterial docs 0.86, ps2tek 0.85, matcap source
  0.82; guided the three.js source reads.
- `jev_screen` GS ALPHA/TEST/TEX0 → pass (injection 0.02, substance 0.99, relevance 0.98). Used as data only.
- `jev_screen` PCSX2 CLI option list → pass (injection 0.02, relevance 0.97). Used as data only.
- `jev_screen` PCSX2 GS Dump Runner → pass (injection 0.01, relevance 0.98). Used as data only.
- `jev_verify` 10 key claims vs ps2tek + PCSX2 tfx/GS shader + three.js sources → verified 10/10, no review,
  nothing changed.
- `jev_verify` 3 claims vs three.js WebGLState + gsrunner Main.cpp → verified 3, needs_review 1 (gsrunner
  `_frame{N}.png`, 0.76); kept, attributed to the exact source line.
- `jev_verify` 2 claims vs choroq-tools OBJ writer/texture_utils → verified 2/2 (0.81, 0.90); kept.
- `jev_noul` 5 propositions → all "uncertain": "640×480 PNGs are native resolution" 0.42, "upscaled replay is
  faithful" 0.77, "`min(255, 2*a)` faithfully reconstructs GS display" 0.19, "matcap/env-map ≈ pass-4 UV" 0.70,
  "gsrunner writes comparable per-dump screenshots" 0.60. Kept the source-backed 0..128 scale from §1, flagged the
  alpha proposition as an unresolved disagreement, and stated the resolution/upscale items as **open**.
- One `mcp__jev__*` tool_call failed argument validation (bracketed text broke the JSON) and one batch returned an
  incomplete result → switched to the repo's `tools/jev_mcp_call.py --batch`; every later call succeeded.
