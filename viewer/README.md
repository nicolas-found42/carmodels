# Ford Racing 2 — Car Model Explorer

Static three.js viewers for the 35-car reference corpus. `recovered.html` now displays original-coordinate candidates with embedded model textures and serialized translation trees. `index.html` retains the earlier procedural silhouette gallery.

## Run

From the `carmodels/` directory:

```sh
python3 tools/build_showcase.py
python3 -m http.server 8080 --directory viewer
```

Open <http://localhost:8080/>. The viewer uses the vendored three.js r182 module, core, and `OrbitControls`; it has no build step or runtime CDN dependency. A local HTTP server is required for browser ES-module loading.

Open <http://localhost:8080/recovered.html> for original-data experiments. The 35 GLBs are already generated under `public/recovered/`. Each retains independent geometry records and five translated tree candidates. The inspector starts with tree zero and includes car, tree/record, texture, wireframe and row-flip controls, plus a GLB download.

To regenerate original-data exports from the existing sibling `reverse-engineering` corpus:

```sh
python3 tools/recover_original_assets.py
python3 tools/export_geometry_candidates.py
python3 tools/validate_geometry_candidates.py
```

The original-coordinate mapping reproduces all 1,837 nonempty geometry records' bounds. Triangle strip, normals, UVs and texture assignments are candidate interpretations. Sixteen scenes retain all alternative wheel/light states and add explicit low-speed/moving-wheel presets derived from the original visibility routines. The low-speed first tree is the default; live animation and executed LOD remain separate checks. Numeric texture selectors are available in the inspector and as KHR_materials_variants. Original material header words and lane recipes are preserved in primitive metadata. The exporter uses display alpha and opaque, double-sided glTF materials, so glass, reflections and GS shading do not yet match the game. Separate PTG menu icons/liveries, 136 newly discovered MATRIX thumbnails and 94 additional mip levels are decoded into evidence folders. This GLB export uses level-zero model textures. The main recovery report distinguishes source decoding from original draw fidelity.

## What the silhouette gallery shows

- Manifest data: name, year, group, in-game BHP, mass, top speed, handling ratings, liveries, sound bank.
- Body-style filters from a batched Jev classification, with the two low-confidence cases resolved from their model names (Explorer Sport Trac → SUV, FR500 → coupe silhouette).
- Procedural 3D silhouettes shaped by the real handling values and colored with a best-effort dominant opaque-color sample from each menu-icon `.ptg;1` buffer.

**The index.html meshes are procedural reconstructions.** The recovered.html inspector uses original car geometry inputs and decoded embedded model textures, with its remaining fidelity limits displayed explicitly.

## Research

- `../research/visualization-libraries.md` — primary-source tooling research and citations.
- `../research/format-notes.md` — verified file structure, experiments, confidence, and remaining reverse-engineering tasks.
- `../research/original-recovery.md` — current synthesis, validation receipts, Jev experiments and research leads.
