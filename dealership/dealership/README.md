# Editable dealership

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

### GT4 material corrections

Both viewers derive material corrections in memory for recognized `gt4-ps2-static-car-v2`
exports. The same corrected document drives factory presets and selected-paint GLB downloads;
original source and dealership files, geometry, PNG bytes and variant mappings are unchanged.
The geometry/studio toggle does not disable these corrections.

Finish-bearing native body surfaces use a one-byte alpha cutoff so partially opaque paint
texels are retained, with native finish alpha replaced by opaque material alpha. All materials of the same factory-variant surface follow that rule,
including black presets with zero native specular input. Alpha-zero cutouts remain open;
window-frame passes without a native finish and authored cutoff/factor values are preserved.

Recognizable green-marker BLEND passes use neutral translucent glass (opacity factor 0.35,
roughness 0.16). Recognition requires the native exporter identity/default material and at
least a quarter of the original PNG pixels carrying the canonical bright green marker with
nonzero alpha. Black window-frame masks keep their existing cutoff and alpha; their black RGB is made explicit to eliminate green transparent-padding fringes under filtering. Ordinary coloured transparent textures and authored finishes are preserved.
This is an explicit preview fallback: native GT4 glass/reflection shading remains unresolved.
The GLB records the source hash, material targets and limits under `gt4MaterialRepair`.

`node tools/test_gt4_materials.mjs` checks the real NSX bumper/glass, original alpha-zero masks,
factory switching/download, reimport, artist edits, format boundaries and mutation controls.
`tools/check.sh --only gt4_materials_corpus` audits every GT4 working model and verifies both
source/working catalog pins, binary/image preservation and material-only document changes.
The corpus audit is opt-in; its counts are not a visual review of every car. Already-corrected
reimports are checked for unchanged bytes and reported separately with zero new corrections.
Their historical repairs cannot be independently re-derived without the pre-repair checkpoint.

### Enhanced Gran Turismo 4 edition

GT4 dealership models are automatically enhanced on load. **Enhanced GT4 edition**
switches between the working model and a modern studio presentation; the comparison
keeps the camera position. The source viewer and all stored source/working GLBs remain
separate and unchanged. A dealership download contains the selected paint, refined
geometry, factory variants, original texture bytes and enhancement provenance.
The studio environment belongs to the viewer; it is not embedded in the download.

The deterministic PN-triangle pass samples supported native-normal curvature at four
segments per edge. Original vertices and render-domain boundaries are anchors;
UV/normal/colour seams and material variants stay separate. Cutout silhouettes,
unsupported attributes, folded candidates and geometry over the budget retain their
original parts. New samples move at most 6 mm from their source barycentric position.
The GLB retains source-face/sample mappings for independent displacement and attribute
checks. These bounds are safeguards, not a measurement of real-car accuracy.

Known native tire parts get a rubber response; materials with native specular input
get a labelled artistic clearcoat translation. Unidentified finishes remain unchanged,
and no chrome or paint mask is guessed from a name or colour difference. Factory
texture pixels are retained, with mip filtering and anisotropy in the enhanced preview.
Exact-car external measurements/reconstructions have not been established for this
batch, so it uses the agreed conservative source-mesh fallback rather than inventing
hidden details or changing dimensions from unmatched references.

Run `tools/check.sh --only test_gt4_refinement,gt4_refinement_corpus` to exercise the
unit/integration checks and every catalog car. `node tools/audit_gt4_refinement.mjs
--output .scratch/new-gt4-audit.json` additionally retains a per-car receipt at a new
path. The audit checks source hashes, original binary/image preservation, factory
variants/transforms, source corners, measured displacement, UV/colour correspondence
and orientation. It does not prove visual identity. Research and reconstruction
limits are in [the fidelity note](../../research/gran-turismo-4-model-fidelity.md).

Gran Turismo exports are added with `python3 tools/import_gt_dealership.py`, then
`python3 tools/build_dealership.py`. The importer verifies the source index hashes
and static GLB profile before adding independent copies. Repeat imports preserve
existing dealership models and metadata, including user edits. Canonical asset identities
are namespaced as `GT_SIMULATION_<CODE>`: one day-derived model per retained vehicle
family, with every native colour set embedded as a material variant. Distinct bodies and racing liveries remain
separate; night editions, exact arcade duplicates and the two special logo/cup families
are excluded from public car entries. Old selection IDs are aliases of canonical cars.
Exact native SPEC-code joins supply retail names and base specifications for 178
families. Other identities and racing specifications remain unassigned; year,
manufacturer, body style, top speed and ratings are not inferred. The native game
power conversion is labelled HP (game), and rotary displacement retains its
chamber/factor representation. Factory colour names use native colour-ID joins;
unmatched sets keep explicit native identifiers.

Migrate the older variant catalog with `python3 tools/import_gt_dealership.py
--consolidate --upgrade-unedited`, then rebuild. The migration carries custom day
metadata into the canonical entry and records retired metadata/provenance in
`origins.json`; an edited duplicate aborts before any files change. Edited day models
are retained as canonical working copies. The native extraction is preserved.

Source improvements can be applied with `python3 tools/import_gt_dealership.py
--upgrade-unedited`, followed by the rebuild. A working model is refreshed only
when its hash equals its latest recorded source hash. Edited models and custom
catalog fields are preserved; original import provenance remains in `initialSource`,
with subsequent source hashes recorded in `latestSource` and `sourceUpgrades`.
The Gran Turismo source exports include recovered native wheel templates and
per-car attachment/texture data; their static assembly limits travel with each copy.
Metadata upgrades fill prior generated defaults and keep custom names, values and
notes. `origins.json` retains the latest source metadata independently of owner
overrides. Edited working geometry is preserved. The colour selector reads the
loaded working GLB, so it does not offer source variants absent from an edited copy.

Each enriched source GLB retains complete CAR/CTEX payloads, raw palettes, shadow
records, original normals and face packets, source-to-triangle mappings, native
LOD descriptors, all five wheel templates and neutral attachment pivots. These
records preserve native inputs; they do not implement original GTE effects,
semi-transparency, lighting palette rewrites, shadows or animation.

The Gran Turismo display uses each working GLB's default scene and embedded PNG
textures, rather than compact surface tones. Other LOD scenes remain in the download.
The viewer checks the compiled model hash when loading, so a later GLB edit requires
a rebuild. Game and source-variant selectors work offline. The optional natural
language filter (served by `tools/serve_library.py`) matches exact game/variant phrases
locally and sends other wording to the TypeSafe model; uncertain or unavailable
judgments leave existing filters unchanged and show a status message naming the reason.
The optional form is under **More filters**, submits with Enter, and displays the provider
routing explanation beside the field. Name/year/code search stays offline, accepts words in
either order and keeps unknown names/unsupported spellings as explicit empty results. When
changing games or source variants, incompatible choices are cleared with a visible explanation;
still-available restrictions remain selected.

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

Before importing MC3 GLBs in Blender 4.5.14, run `tools/blender_gltf_compat.py` in
Blender's scripting workspace. Its pinned importer mixes unordered custom-attribute
names with ordered value arrays. The script repairs that ordering for the current
session, checks the importer source hash, and leaves installed files and GLBs intact.
The MC3 roundtrip check uses this repair and verifies exact native attribute values
before importing, editing and exporting three real cars. Unmodified Blender 4.5.14
can reject these models or associate custom attributes incorrectly.

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

Gran Turismo 4 previews are added with `python3 tools/import_gt4_catalog.py`, then
`python3 tools/import_gt4_dealership.py` and `python3 tools/build_dealership.py`. The source
catalog publishes `public/gran-turismo-4/previews/<code>.glb` (static showroom model with decoded
textures, wheels and tires) and `native/<code>.zip` per car (local only, not committed); the dealership owns independent
copies `models/GT4_<CODE>.glb`. Names, model years and masses come from the decoded spec database;
ratings, power and body style stay unknown. Repeat imports preserve edits; `--upgrade-unedited`
refreshes only exact copies of the recorded source. GT4 cars face -Z, so the front camera looks
from -Z. See [the preview note](../../research/gran-turismo-4-previews.md).

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
resources and default rims/tires into `games/midnight-club-3-remix/recovered-models/`. It verifies packet bounds,
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

MC3 tires use the recovered ALWAYS base coverage, native VU alpha and projected-
normal lookup coordinates, and destination-alpha-weighted additive RGB arithmetic.
Both showcases use the shared material adapter and a source-derived San Diego
midnight garage capture, native panorama overlay and 256-to-64 specular copy.
The synthetic highlight lookup and floating capture approximation are removed.
Original EE/VU execution supplies the fixed garage draw packets; the shared
rasterizer and final reflection texture match pinned PCSX2 v2.8.2 AVX2/FMA
software-GS replay byte for byte. Physical PS2 output, alternate environments
and full runtime frame context remain outside this selected contract. See the
[precision investigation](../../research/midnight-club-3-remix-raster-precision.md).
Native rim/tire back-face culling removes the
opposed coplanar-cap stripes without moving or deleting geometry. Original PNGs,
existing geometry and paint variants remain intact; `_MC3_NATIVE_NORMAL` retains
additional source data for lookup generation. Regenerate with
`python3 tools/export_mc3_models.py --output <new-directory>`, publish with the
preserving importers, then rebuild both catalogs and `game-paints.json`. See the
[tire investigation](../../research/midnight-club-3-remix-tire-alpha.md).

Showcase triangle indices use one unsigned 32-bit representation. The compact display schema is
4; the encoder emits schema 4 and the browser rejects the former 16-bit schema 1, so rebuild showcase data with
`python3 tools/build_dealership.py` after updating. Textured GLBs use 32-bit index arrays in the
renderer too. Imported GLBs can retain their source accessor widths; the loader converts their
indices to 32-bit arrays. This does not change vertex coordinates, triangle order or source files.

Midnight Club: Los Angeles static previews are added with `python3 tools/import_mcla_catalog.py`,
then `python3 tools/import_mcla_dealership.py`, `python3 tools/build_model_catalog.py` and
`python3 tools/build_dealership.py`. The source-model showcase has independent LOD 0 GLBs
and local native ZIP downloads; the dealership owns independent editable `models/MCLA_*.glb`
copies. Repeat imports preserve edits. `--upgrade-unedited` refreshes only exact copies of
recorded sources and retains import history. Names use exact English UI key joins for 47 of
106 source vehicles; the other entries retain source codes. The stock variant identifies the
explicit static assembly convention. Wheel sizing, neutral paint and material simplification
are preview approximations; runtime configuration and original rendering remain unverified.
See [the preview note](../../research/midnight-club-los-angeles-previews.md) and
[the name note](../../research/midnight-club-los-angeles-names.md).

MCLA profile v2 retains native submodel bone bindings, restores joint orientation and composed descendant placement, and corrects shared-wheel and attachment frames. For a source upgrade, use `python3 tools/import_mcla_catalog.py --refresh`, then the `--upgrade-unedited` dealership import and both catalog builds. Source refresh validates the existing edition before installation and preserves checked native ZIPs. Regular exterior parts exclude alternative wide kits; DUB packages without regular exterior slots use their required wide family. Player citybus uses a guarded wheel-only join from its matching ambient family, with donor source hashes retained. Original gameplay configuration and shader fidelity remain outside the static profile.

The S7 preview also carries a source-pinned divider-profile reconstruction in its GLB `preview_geometry_repairs`. Native model/attachment frames stay unchanged; only ten divider components of one skirt primitive are thinned, with before/after measurements recorded. The original native geometry remains in its ZIP. This documented preview cleanup is separate from recovered game deformation or shader behavior.

## Native game colours

Both showcases use recovered native presets and a searchable game-colour library.
The arbitrary colour picker and hex field have been removed. Original presets can
change coordinated native materials and textures. Independently recovered paint
channels can use any verified colour value from that car's game, applied over the
selected preset. Textures, decals, trim and other channels keep their bindings.
Finish controls appear only when a source-backed translation is available.

Game palettes are compiled with `python3 tools/build_game_paints.py` after source
or editable GLB upgrades and catalog builds. The compiler reads the source and
working GLBs, retains each colour's native identity, and pins their carriers.
The default checks reject a stale palette. It never derives paint masks from
material names, menu-icon pixels or differences between native variants.

Current scalar body-paint channels cover direct opaque untextured MC3 carpaint
materials and MCLA AmbientCarPaint materials. Native RGB vectors use the documented
static PBR interpretation; original colour space, shader response and finish formulas
remain unresolved. GT1, Ford, GT4 and Redline retain their recovered material/texture
presets. Cross-car palette correspondence, player-MCLA channels, composite MC3 panels
and additional paint/finish channels stay unavailable until recovered. The controls
state each loaded model's limits; edited GLBs determine which choices are available.

Selections are remembered per car in each showcase on this browser. Reset restores
the loaded GLB's original materials and clears its saved selection. Storage failure
does not prevent painting. Loading, failure and native-package-only states disable
the controls. Changes never write to the working GLB or catalog.

The GLB download opens with the selected preset, channel colours and finishes as its
default materials. It retains original material variants, all scenes, edited geometry,
embedded texture bytes and source metadata. Source-viewer inspection toggles and
geometry-scene choices are not baked into the download. Native package downloads
remain the original game data. Rendering uses viewer lighting rather than the original
game's shaders.
