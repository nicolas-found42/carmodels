# Visualizing the Ford Racing 2 PS2 car corpus: research findings

Researched 2026-10-04 against primary sources (GitHub repos, official docs, emulator source).
Corpus under study: 35 cars, each with `model/<CAR>.PS2;1` (custom binary: name-offset directory +
part names like `WHEEL_FRONT_LEFT`; per-car containers do not expose float32 vertex arrays), `graphics/liveries/*.ptg;1`
(fixed-size buffers with padding and GIF/GS/DMA-like records; exact pixel upload geometry remains unresolved), `config/*.txt`, `manifest.json`.

---

## (a) Ford Racing 2 / Empire Interactive specific findings

**No GitHub project or tool supports our PS2 car-model container format. None found.**
Method: multiple GitHub code searches (gh-grep over >1M public repos) and web searches over
variation sets of the game title, studio, and part-name strings. What exists is:

1. **widberg/fror-research** — https://github.com/widberg/fror-research
   Research for *Ford Racing: Off Road* (2008, Razorworks, **PC-only** title). Contains
   010 Editor `.hexpat` patterns and a Blender addon (`blender-addon` topic). Formats documented
   (per the README): `3dobjdb.pc`, `3dobjs.pc`, `3dobjsp.pc` (compressed Windows-side databases),
   `pcg`, `pvs`, `spc`, plus DDS/WAV. **1 star, 80 commits, last commit 2026-02-19** (actively
   maintained but tiny). It targets the PC successor's formats — not the PS2 `.PS2;1` containers —
   so patterns do not transfer, but the franchise's overall pipeline (Softimage-style part-based
   car models, part name directories) is the closest prior art in the series.
2. **Ford Racing 3 modding on GameBanana** — https://gamebanana.com/games/8561 (mods/skins only,
   no model-format tooling; linked as "Prior Work" from fror-research).
3. **32bits.substack.com, "Under the microscope: Ford Racing 3 (PS2, Xbox)"** (Jan 9, 2026) —
   https://32bits.substack.com/p/under-the-microscope-ford-racing-7a4
   Ghidra reverse engineering of the PS2/Xbox executables for cheat codes only. Demonstrates the
   workflow (Ghidra + `ghidra-emotionengine-reloaded` ELF loader on the game's SLUS ELF); contains
   no model/texture format info for FR2/FR3.
4. **PCSX2 compatibility artifacts**: shadow-rendering bug for Ford Racing 2 PAL
   https://github.com/PCSX2/pcsx2/issues/1982 and patch files for SLES-51705 / SLUS-20788 in
   community patch packs (e.g.
   https://github.com/Gabominated/PCSX2/blob/main/PCSX2%20Patches/SLES-51705_37F695CD.pnach).
   Confirms the game is emulated well enough to run; nothing about asset extraction.
5. GitHub-wide code greps for the exact part-name strings visible in our containers
   (`WHEEL_FRONT_LEFT`, `HUB_BACK_RIGHT`, `BRAKE_LIGHTS_ON`) matched only unrelated projects
   (GTA decompilations, robotics controllers). No FR2 tooling exists anywhere in public code.

**Conclusion for (a):** we are format-first discoverers; no 80% shortcut exists in public code.

---

## (b) Generic PS2 binary/texture/model tools

| Tool | URL | What format | Fit for our `.PS2;1`/`.ptg;1` container |
| --- | --- | --- | --- |
| **PCSX2** (GS texture dumping/replacement) | https://github.com/PCSX2/pcsx2 (feature: GS: Add texture dumping and replacement system #5547, requested as issue #5046 https://github.com/PCSX2/pcsx2/issues/5046) | Dumps live GS textures in VRAM while the game renders (PNG/DDS) | **Best livery shortcut.** Play FR2 in-game (livery select screen) with dumping on; recover the exact decoded textures incl. any non-obvious formats. Cannot dump geometry. |
| **vutrace** (chaoticgd) | https://github.com/chaoticgd/vutrace | Tracing debugger for PS2 VPU1 in PCSX2 (37★, last commit 2024-06) | **Best geometry-discovery tool.** Patch PCSX2, record VU1 traces (register/memory snapshots + load/store events), replay the game's own frame construction and see exactly how our container's VIF/VU1 data maps to vertices. |
| **ghidra-emotionengine-reloaded** (chaoticgd) | https://github.com/chaoticgd/ghidra-emotionengine-reloaded | Ghidra loader/processor for EE ELF binaries | To disassemble FR2's SLUS ELF and recover the loader/consumer code that walks our container (names→offsets→DMA). Same workflow as the FR3 writeup above. |
| **Noesis** (Rich Whitehouse) | https://richwhitehouse.com/index.php?postid=73 (glTF import/export support), plugin ecosystem incl. https://github.com/alphazolam/fmt_RE_MESH-Noesis-Plugin | Hundreds of model/texture formats via plugins; exports glTF | Can be an export-verification target (load .ptg-decoded PNG + .PS2-decoded OBJ) but has **no FR2 format plugin** (checked plugins lists). |
| **QuickBMS** (aluigi) | https://quickbms.altervista.org/ ; per-game PS2 scripts indexed at https://aluigi.altervista.org/quickbms.htm (e.g. `nfsps2_tpk.bms` for Need for Speed PS2 `.TPK` texture archives) | Archive/container extraction via BMS scripts | Model: write our own `.bms` scripts for the `.PS2;1` directory and `.ptg;1` streams once offsets are known. No existing script for FR2 (library searched). |
| **Rainbow** (marco-calautti) | https://github.com/marco-calautti/Rainbow | Texture format converter for console graphics formats | Useful for validating swizzle/CLUT interpretation of `.ptg;1` texture payloads. |
| **TIM2 toolkit** (PS2HomeDeveloper/ps2-tim2-tool) | https://github.com/PS2HomeDeveloper/ps2-tim2-tool | TIM2 (.tm2) ⇄ PNG | If `.ptg;1` payload turns out to be TIM2-like, this validates decoding. |
| **vincent-tim** (myst6re) | https://github.com/myst6re/vincent-tim | PS1-era TIM ⇄ PNG | Reference for TIM layout if we treat `.ptg;1` data as TIM-like. |
| **xtc** (aap) | https://github.com/aap/xtc | A PS2 3D rendering library (VU1 microcode, DMA/GIF chains, OBJ-based model pipeline with `tools/xstrip`); 38★, still active (2026-09) | **Reference-quality open source for VIF→VU1→GIF geometry generation.** Not a FR2 parser, but its VU1 pipelines mirror the microcode constructs our containers likely embed. |
| **DobieStation** (PSI-Rockin) + its "From Bits to Pixels" wiki | https://github.com/PSI-Rockin/DobieStation/wiki/Making-a-PS2-Emulator%3A-From-Bits-to-Pixels | Tutorial on EE→VIF→GIF→GS renderer dataflow | Best concise read to understand what our containers are compiled into. |
| **PCSX2 `Vif_Unpack.cpp`** | https://github.com/PCSX2/pcsx2/blob/master/pcsx2/Vif_Unpack.cpp | The canonical open-source implementation of VIF UNPACK semantics (writeXYZW, masks, modes, cycle/wl skip logic) | Directly reusable as a Python reference implementation for our per-part geometry unpacking. |
| **PCSX2 GS texture dumping guide (community)** | https://reshax.com/forum/5-3d2d-models.xml (forum tutorial threads on ripping PS2 models/textures via emulators; the "scurest PCSX2 3D Screenshot Build" workflow referenced from https://www.reddit.com/r/ps2/comments/1nu0466/how_to_rip_3d_models_with_materials_and_textures/) | In-emulator geometry/text dump → OBJ | Manual last-ditch route for one or two cars if static analysis stalls; not automatable for 35 cars. |

Nothing in the table parses our specific container — they are all *infrastructure* around VIF/GIF/TIM
semantics that we will reuse when writing our own parser.

---

## (c) Web viewer recommendation

### Primary: three.js — current stable is `0.182.0` (major.minor `0.182`)

- Repository: https://github.com/mrdoob/three.js — releases are tagged `rXXX`/`0.182.0`.
- GLTFLoader lives in `examples/jsm/loaders/GLTFLoader.js`, importable via
  `three/addons/loaders/GLTFLoader.js` and documented at
  https://threejs.org/docs/#examples/en/loaders/GLTFLoader.
- Official example (importmap + GLTFLoader):
  https://github.com/mrdoob/three.js/blob/dev/examples/webgl_loader_gltf.html
- Official installation guidance (npm vs CDN vs importmap):
  https://threejs.org/docs/index.html#manual/en/introduction/Installation

**Offline vendoring (recommended for this project — no runtime CDN; serve the static files from a local HTTP server):**

1. Download the matching release from e.g. `https://unpkg.com/three@0.182.0/build/`.
   Three.js r182 splits core into `three.core.js`; the viewer vendors `three.module.js`, `three.core.js`,
   and `examples/jsm/controls/OrbitControls.js`. Add `examples/jsm/loaders/GLTFLoader.js` only when
   loading future GLB exports. `three.module.js` imports `./three.core.js` relatively.
2. In the HTML, use an importmap for the bare `three` import used by OrbitControls:

```html
<script type="importmap">
{ "imports": { "three": "./vendor/three.module.js" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
</script>
```

The current viewer builds silhouettes directly with three.js and OrbitControls; GLTFLoader is the
future path once verified per-car geometry can be exported. A static server is required for module
loading in browsers; do not promise direct `file://` execution.

- Reference for the importmap pattern with local vendored three.js:
  https://discourse.threejs.org/t/possible-to-write-offline-3js-after-version-128/86649
  ("If you have the threejs library code in the same directory as your html … redirect the required
  references via importmap"; also explains why post-r128 no single non-module file exists to just
  `<script src>`.)

**Lighter alternative: `<model-viewer>`** (Google web component wrapping three.js)
- Repo: https://github.com/google/model-viewer — docs/quickstart at https://modelviewer.dev/
  (as of the research date, the Google Ajax CDN hosts version **4.3.1**:
  `https://ajax.googleapis.com/ajax/libs/model-viewer/4.3.1/model-viewer.min.js`).
- Pro: one HTML element, built-in orbit/environment/shadow/AR. Con: heavier default bundle for our
  simple 35-model catalog, harder to vendor the full dependency graph offline, and less control over
  the render loop (we want per-part visibility, livery swapping, and a camera fit per part). Use it
  only if we want a fast demo page; **recommend three.js directly** for the final gallery.

**Python exporter path for the meshes we extract ourselves**
- Recommended: `trimesh` (https://trimesh.org/), current docs version 5.1.x.
  `pip install trimesh`; export either OBJ or GLB:
  `trimesh.exchange.obj.export_obj(...)` (https://trimesh.org/trimesh.exchange.obj.html),
  `trimesh.exchange.gltf.export_gltf/export_glb(...)` (https://trimesh.org/trimesh.exchange.gltf.html).
  This is the shortest path from our Python-parsed VIF/GIF geometry to a `.glb` that the vendored
  three.js GLTFLoader displays. `trimesh.exchange.gltf` handles material/texture attachment for the
  livery (`*.ptg;1`-decoded PNG) → per-car GLB.

---

## (d) PS2 VIF/VU1/GIF spec references

Authoritative, open, and machine-readable. All four are actively maintained public resources.

1. **ps2tek** — nocash-style comprehensive PS2 hardware docs, includes:
   - GIFtag format and GIF paths — https://psi-rockin.github.io/ps2tek/#gif
   - VIF UNPACK commands and cycles — https://psi-rockin.github.io/ps2tek/#vif
   - VU architecture and registers — https://psi-rockin.github.io/ps2tek/#vu
   - DMA controller — https://psi-rockin.github.io/ps2tek/#dmac
2. **PCSX2 source (vif/GIF semantics, GPL-3.0+)**
   - VIF UNPACK interpretation (writeXYZW, mask, modes, cycle/wl skip):
     https://github.com/PCSX2/pcsx2/blob/master/pcsx2/Vif_Unpack.cpp (see also
     https://github.com/PCSX2/pcsx2/issues/3024 for VIF1-DMA-to-VU1 semantics)
   - GS context / SCISSOR / TEX0 handling:
     https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/GSState.cpp
   - GIF packet plumbing: https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/GSState.cpp
3. **DobieStation "From Bits to Pixels" wiki** — end-to-end EE→VIF→GIF→GS renderer dataflow
   tutorial that explains what a game's model blob compiles into:
   https://github.com/PSI-Rockin/DobieStation/wiki/Making-a-PS2-Emulator%3A-From-Bits-to-Pixels
4. **aap/xtc** (38★, actively developed) — working open-source PS2 3D renderer with VU1 microcode
   (`xtc/vu1/*.vcl`), DMA/GIF chains, and a toolchain that converts OBJ → PS2 display lists:
   https://github.com/aap/xtc — the inverse direction (PS2 display list → geometry) uses the same
   building blocks; its `tools/xstrip` and `common/tristrip.cpp` show how PS2 triangle strips are
   constructed and deconstructable.
5. **Chaotic's VU trace** (chaoticgd/vutrace) — tracer plugin for PCSX2, with VU memory/register
   snapshots, useful for watching the exact VIF/VU1 data flow of a real PS2 frame:
   https://github.com/chaoticgd/vutrace

---

## (e) Recommendation

**No existing parser exists — we build our own (Python).**

Justification:
1. GitHub-wide code search for the exact part-name strings in our container returned zero FR2 tooling;
   the only Ford Racing RE project in public code targets the *PC* sequel's different file formats.
2. Our container is a *custom* format — a name directory + part-name strings, not a standard PS2
   container format (no `IMD/PMD`, no `TM2` magic, no `RWS` chunk id, no `SLES-51705` marker). Any
   generic "PS2 model converter" would still need our custom container layer first. Generic PS2
   tools target *standard* formats or *specific games*; neither exists for this game.
3. However, we are not parsing blind — the generic layer is documented and reusable as reference code:
   - `.ptg;1` is confirmed to contain fixed-size padded upload buffers and pointer-like GIF/GS/DMA
     structures, but exact texture upload bounds and mips are **not decoded yet**. Exploratory pixel
     renders show partial car imagery at guessed pitches, not faithful complete textures. Do not treat
     the current color sample as a finished texture decoder. PCSX2 texture dumping remains the right
     ground-truth cross-check once the game is running in an emulator.
   - `.PS2;1` has a custom name/part directory, u16 strip-like topology and transforms, but no
     per-car float32 vertex arrays. Current evidence suggests a shared geometry pool/object-ID path;
     exact mesh recovery still requires ELF loader RE and a VU trace. PCSX2 `Vif_Unpack.cpp` and
     `vutrace` are references/validation aids, not a completed parser.

**Tool that gets us closest to 80%:** *none for parsing the container* (that work is ours), but for
*validation* two tools give useful leverage when installed:
- **PCSX2 texture dumping** (https://github.com/PCSX2/pcsx2/issues/5046, PR
  https://github.com/PCSX2/pcsx2/pull/5547) — ground truth for validating a future livery decoder.
- **chaoticgd/vutrace** (https://github.com/chaoticgd/vutrace) — ground truth for tracing the
  geometry loader on a sample car, complementing the static reference at
  https://github.com/PCSX2/pcsx2/blob/master/pcsx2/Vif_Unpack.cpp.

**Current implementation and remaining plan:**
1. **Format reconnaissance:** name directory, livery codes, paint samples, u16 topology and part transforms have been mapped; exact `.ptg;1` mip extents and the shared geometry pool remain open.
2. **Viewer shipped:** static HTML + locally-vendored three.js 0.182.0 + OrbitControls; manifests drive performance panels, Jev body-style classifications drive procedural silhouettes, and paint color samples come from each icon payload. The UI explicitly labels the bodies as reconstructions; no partial texture is presented as a decoded car image.
3. **To replace the reconstructions with original meshes:** trace the shared geometry lookup in the ELF, use PCSX2/vutrace for a ground-truth capture, and export verified per-car GLB via `trimesh` + future `GLTFLoader`.

---

## Summary of sources

| Claim | URL |
| --- | --- |
| widberg/fror-research (FR PC-sequel RE, 1★) | https://github.com/widberg/fror-research |
| FR3 Ghidra RE writeup (cheats only, no formats) | https://32bits.substack.com/p/under-the-microscope-ford-racing-7a4 |
| PCSX2 texture dump/replace issue | https://github.com/PCSX2/pcsx2/issues/5046 |
| PCSX2 VIF UNPACK reference implementation | https://github.com/PCSX2/pcsx2/blob/master/pcsx2/Vif_Unpack.cpp |
| PS2 hardware docs (GIFtag, VIF, VU, DMA) | https://psi-rockin.github.io/ps2tek/ |
| DobieStation "From Bits to Pixels" wiki | https://github.com/PSI-Rockin/DobieStation/wiki/Making-a-PS2-Emulator%3A-From-Bits-to-Pixels |
| vutrace (VU1 tracer) | https://github.com/chaoticgd/vutrace |
| ghidra-emotionengine-reloaded (EE ELF loader) | https://github.com/chaoticgd/ghidra-emotionengine-reloaded |
| aap/xtc (open PS2 3D renderer + OBJ pipeline) | https://github.com/aap/xtc |
| QuickBMS + PS2 script index | https://aluigi.altervista.org/quickbms.htm |
| Noesis glTF export support | https://richwhitehouse.com/index.php?postid=73 |
| Rainbow texture converter | https://github.com/marco-calautti/Rainbow |
| TIM2 toolkit | https://github.com/PS2HomeDeveloper/ps2-tim2-tool |
| vincent-tim | https://github.com/myst6re/vincent-tim |
| three.js repo + GLTFLoader example | https://github.com/mrdoob/three.js |
| three.js offline/importmap discussion | https://discourse.threejs.org/t/possible-to-write-offline-3js-after-version-128/86649 |
| three.js r0.182 importmap pattern | https://discourse.threejs.org/t/how-to-build-a-simple-libre-3d-glb-gltf-viewer/89393 |
| model-viewer quickstart + CDN version 4.3.1 | https://modelviewer.dev/ |
| trimesh GLB exporter docs | https://trimesh.org/trimesh.exchange.gltf.html |