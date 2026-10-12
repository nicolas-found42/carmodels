# Editable dealership

## Car generator — WIP

Paused at the owner’s request. Generated cars currently use solid body paint and dark
wheels with no texture maps. The owner found the geometry too bubbly; body quality,
complete blind-review marks and novelty calibration remain unfinished. See the
[WIP investigation and resume notes](../../research/car-generator.md).


The generator learns aligned 64³ body distance grids and separate regressions of wheel layout from body embeddings
from distinct dealership shapes. It provides a linear shape space and a conditional
3D VAE, with their basis, weights, labels and hash manifest in `dealership/generator/`.
Identical canonical body grids are counted once, with duplicate references in the manifest.
The four upward tyre-top coverage rays and a separate exclusion judgment screen open-wheel racers.
Uncertain non-car judgments remain in `review.json` and stay out of training. Labels
do not change the dealership catalog. `GEN_` entries never enter training.

The numerical runtime is separate from stock Python. Provision it from the repository root:

```sh
uv venv --python 3.12 .venv-generator
uv pip install --python .venv-generator/bin/python torch==2.10.0
uv pip install --python .venv-generator/bin/python -r tools/generator-requirements.txt
```

On Linux CPU machines, install torch from `https://download.pytorch.org/whl/cpu`;
CI provisions that pinned runtime. Tests never call a provider. Live preparation
and free text need `OPENROUTER_API_KEY` on the server; credentials never enter the page.

```sh
.venv-generator/bin/python tools/car_generator.py prepare --live
.venv-generator/bin/python tools/car_generator.py train --device mps --epochs 100
.venv-generator/bin/python tools/car_generator.py generate --method 'shape space' --seed 35 --output .scratch/new-car.glb
.venv-generator/bin/python tools/car_generator.py save --input .scratch/new-car.glb --name 'My generated coupe'
python3 tools/serve_library.py
```

Choose `--method network` for the VAE, `--novelty 0..1` to control novelty, or
`--request 'a low, long 70s coupe' --live` for interpretation. A `--constraints`
JSON file can supply recorded readings without another provider call. Generated
GLBs carry their recipe, and their sidecar JSON retains the request for reference.
Replay uses the recorded interpreted constraints and pins the basis/network, wheel model,
labels, calibration, effective training settings, donor GLBs and decoded icon-colour palette.
A changed pinned input is reported rather than silently producing a different model.
A saved catalog entry keeps the executable options at `entry['generator']['recipe']`;
`Generator.generate(**entry['generator']['recipe'])` replays them without interpreting
`entry['generator']['request']`, which is reference text only.
Generation runs every stage and never changes its method based on elapsed time.
Unsupported request parts pause for explicit confirmation. Roll and dropdowns
work without the TypeSafe SDK or credentials.

The page's **Generate a new car** panel runs the same pipeline and previews in the
existing viewer. Saving creates a new `GEN_<hash>` model and appends a catalog row,
then rebuilds display data. It rejects an existing code and never overwrites a model.
Body style and era are marked requested; power, weight, top speed and ratings remain
unknown. The **Generated model** honesty label appears on the saved edition.

The grid cache is ignored and rebuilt with `prepare` using recorded, hash-matched
labels (omit `--live`). A generation after checkout also rebuilds missing grids.
After editing source dealership models, retrain with `prepare --live` and `train`.
Offline checks warn about stale weights, naming the retrain command; stale source
models alone do not fail the generator checks. Corrupt learned artifacts do fail.

```sh
.venv-generator/bin/python tools/generator_review.py create
python3 tools/serve_library.py
# Open /generator-review.html, mark all 70 shuffled models, then Save all 70 marks.
tools/check.sh --only generator_freshness,generator_fixed_seed,test_car_generator,test_generator_runtime,test_generator_http,test_generator_ui
```

The review has 30 outputs per method and 10 real held-out controls. `quality.json`
records held-out reconstruction error, nearest-real distance, symmetry, contact and
end-to-end timings. Complete reviewer marks produce `review-results.json` and set the
novelty default. Recognition rates and automatic-check agreement are measured from
marks, never invented. See [the experiment note](../../research/car-generator.md).

`generator_roundtrip` generates one car by each method, imports and edits it in pinned
Blender, exports it and proves the edit reaches a deterministic dealership rebuild.
Generated GLBs use the same static profile and Blender edit/export route described
below. They carry no original-game rendering or performance claim.

## Working models

This directory owns the dealership's working models and catalog. These regular GLB files
were copied once from recovery; they are not symlinks or hardlinks. Change a file under
`models/` to change that dealership car. Edit `catalog.json` for dealership names, metadata
and colour choices. Dealership-wide rendering/material styling lives in `../dealership.mjs`.

From the repository root, run `python3 tools/build_dealership.py` after an edit. It reads
these working inputs and updates `dealership/public/dealership/cars.json`, preserving edits.
`tools/build_showcase.py` delegates to the same safe build. Source-model recovery and
export do not update this directory.

`origins.json` records where the initial copies came from. It is historical provenance;
edited models are not required to match those hashes. `tools/seed_dealership.py` leaves
an existing dealership intact rather than resetting it from source assets.

Open `/dealership.html` for this edition, and `/recovered.html` for the source-model
showcase. The dealership's download link serves the working GLB copy. The source-model
showcase's download link serves the separately stored recovered original.

Gran Turismo exports are added with `python3 tools/import_gt_dealership.py`, then
`python3 tools/build_dealership.py`. The importer verifies the source index hashes
and static GLB profile before adding independent copies. Repeat imports preserve
existing dealership models and metadata, including user edits. Asset identities
are namespaced as `GT_SIMULATION_<CODE>_<DAY|NIGHT>` or
`GT_ARCADE_PAIR_<ORDINAL>`; simulation day/night and arcade variants remain
separate entries. These are archive identifiers, not decoded retail vehicle names.
Performance values and body styles remain unknown until supported by decoded data.

Source improvements can be applied with `python3 tools/import_gt_dealership.py
--upgrade-unedited`, followed by the rebuild. A working model is refreshed only
when its hash equals its latest recorded source hash. Edited models and custom
catalog fields are preserved; original import provenance remains in `initialSource`,
with subsequent source hashes recorded in `latestSource` and `sourceUpgrades`.
The Gran Turismo source exports include recovered native wheel templates and
per-car attachment/texture data; their static assembly limits travel with each copy.

The Gran Turismo display uses each working GLB's default scene and embedded PNG
textures, rather than compact surface tones. Other LOD scenes remain in the download.
The viewer checks the compiled model hash when loading, so a later GLB edit requires
a rebuild. Game and source-variant selectors work offline. The optional natural
language filter (served by `tools/serve_library.py`) matches exact game/variant phrases
locally and sends other wording to the TypeSafe model; uncertain or unavailable
judgments leave existing filters unchanged and show a status message naming the reason.

The display baker supports static node translations, quaternion rotations, affine matrices,
nonuniform scale and triangle indices of 8, 16 or 32 bits. Preserve normal attributes and
export embedded non-interlaced RGB8/RGBA8 PNG textures; all five PNG row filters are supported.
JPEG, indexed/interlaced PNG and compressed mesh extensions are outside this profile.
Animated/skinned-model importing is outside this
static display builder's scope. Driver helmets and baked shadow planes are omitted from
the compiled display; source interpretation and surface-tone limits remain documented.

For Blender 4.5.14, import the GLB with scenes as collections, select only the collection
named for the GLB's default scene, then edit that edition. Export GLB with Selected Objects,
Normals and Custom Properties enabled, Animations disabled, and PNG textures. Custom
properties retain source part/wheel names used by the display baker. Keep alternative
state collections out of the export. This route is tested for the Gran Torino with a real
import, geometry edit, image re-encoding, export and rebuild; other cars/exporters need checking.

`python3 tools/build_dealership.py --check` verifies display freshness without writing any
files. It also runs in the normal check suite, so an unrecompiled model or catalog edit fails.
`tools/check.sh --only test_build_dealership,dealership_freshness,dealership_roundtrip` runs
the focused editing checks with complete retained logs.

Redline static exports are added with `python3 tools/import_redline_dealership.py`, then
`python3 tools/build_dealership.py`. The importer verifies every indexed GLB hash, size,
source identity and static profile before changing working files. Repeat imports preserve
existing models and catalog edits; `--upgrade-unedited` refreshes only exact copies of
recorded sources while retaining original import provenance. Editable identifiers begin
with `REDLINE_` and include a digest of the complete source configuration identity.

Redline names are literal native configuration names. Base-game and add-on configurations
remain separate variants. Their performance and body categories remain unknown; conversion
limits travel with each entry. Both viewers use the static GLB scene and embedded textures.
Game, source-variant and literal-name filters work offline. The optional TypeSafe semantic
filter can interpret Redline base-game or add-on requests, with unsupported restrictions and
uncertain/provider-failure answers leaving the current filter unchanged.

Midnight Club 3 Remix has 94 native source packages and separate static GLB
inspection conversions. The source catalog retains the original DAT packages.
The dealership owns independent editable GLBs under `models/MC3_*.glb` and
retains independent native DAT copies under `assets/`. Native source codes remain
the names; retail identities, performance and body categories remain unknown.

The recovery pipeline is:

```sh
python3 tools/import_mc3_catalogs.py
python3 tools/export_mc3_models.py
python3 tools/import_mc3_previews.py --refresh-unedited
python3 tools/build_model_catalog.py
python3 tools/build_dealership.py
```

The exporter reads pinned native PCK geometry, stock-named parts, shared body
resources and default rims/tires into `midnight-club-3-remix/recovered-models/`. It verifies packet bounds,
material indices, source hashes and static GLB validity. An existing conversion
folder must match exactly; differing outputs are never overwritten. Use a separate
`--output` directory for a different conversion profile.

The preview importer preflights all indexed GLBs and retains the native package
provenance. Repeat imports preserve working copies and metadata. Explicit
`--refresh-unedited` replaces a working GLB only when it matches its latest recorded
source hash; an edited model is preserved. `initialSource` remains historical,
while `latestSource` and `previewConversion` record the current conversion. A failed
metadata commit restores previous files. Rebuild after editing a working GLB.

The previews show native static geometry with decoded diffuse textures and
alpha (embedded PNGs with UVs, shown by the same loader as the other textured
games), a neutral paint surface and recovered glass tint. Ground shadow planes are
omitted and runtime-logo decal layers are transparent. Their limitations travel with
each catalog entry. Paint colours and names, shader passes, default customization
parts that sit outside the stock-named set, runtime customization, animation,
damage and full game render fidelity remain unresolved. See the
[texture note](../../research/midnight-club-3-remix-textures.md). Native XYZ Euler frames use the executable's
verified `Rz × Ry × Rx` order and parent composition. The front/side camera
controls follow the MC3 source frame.

Game, native-variant and source-code filters work offline. Optional semantic
filtering uses Choice, Noul and Score judgments over the current catalog, including
preview readiness. A deterministic readiness check prevents native DAT-only rows
from satisfying a preview request; uncertainty or provider failures preserve the
current filters. See [the preview investigation](../../research/midnight-club-3-remix-previews.md)
for native-format evidence, experiments and verification limits.
