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
