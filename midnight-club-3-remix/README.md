# Midnight Club 3: DUB Edition Remix — native vehicle files

Recovered from the supplied NTSC PS2 disc, boot serial `SLUS_213.55`.
Original input remains under `game-files/`; its SHA-256 is
`de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9`.

`cars/` contains **94 source vehicle carriers**, **4,323 unpacked nested members**,
and shared vehicle assets and tuning files. There are **7,283 files** totaling
**569,084,266 bytes**, including original carriers, manifests and provenance.
Vehicle IDs are source codes; this is not a verified playable-car roster.

- `cars/<vp_code>/original/`: decoded original nested DAVE/Dave carrier.
- `cars/<vp_code>/assets/<ordinal>/`: every native member, with source paths.
- `cars/<vp_code>/manifest.json`: offsets, stored/decoded hashes and member ownership.
- `cars/shared/assets/<outer_ordinal>/`: outer vehicle resources, traffic assets,
  tuning, shared textures and physics metadata.
- `cars/provenance/`: boot configuration, ISO/archive inventories and original ASSETS tables.
- `cars/index.json`: corpus index, disc identity, selection policy and claim limits.

Ordinal directories preserve duplicate filenames and payload occurrences.
Shared PPFs include rims, tires, brakes, exhausts, rider textures and decals.
The 164 MB `decal.ppf` and 84 MB `decal_g.ppf` remain locally extracted but are excluded from Git
alongside the original ISO; all are reproducible from the pinned input.

From the repository root:

```sh
python3 tools/extract_mc3_cars.py --check
```

The check regenerates expected bytes from the ISO and rejects changed, missing,
extra or linked output. Initial extraction uses the same command without
`--check`, into a new or empty destination. `--output` can choose another destination.
The tool refuses to overwrite existing content.

Optional `--assess-output <new-file-outside-cars>` sends only bounded inventory
paths, sizes and short headers through screening and the existing server-side
Choice/Noul/Score integration. These labels are advisory; uncertain or unavailable
results do not change extracted files. The current 24-item MC3 sample retained
all labels for review.

PCK/mesh files, PPFs and TEX files remain in their native formats. Static geometry
conversions are stored separately under `recovered-models/`, with an index pinning
each GLB to its selected native resources. Reproduce them with
`python3 tools/export_mc3_models.py`. Existing outputs must match exactly and
are never overwritten. Diffuse textures are decoded into the GLBs; native runtime deformation,
animation, paint colour, shader passes, complete dependency closure and game-render fidelity remain open.

Both catalogs list all 94 source packages under **Midnight Club 3 Remix**.
The source catalog retains native DAT downloads under
`dealership/public/midnight-club-3-remix/native/`. The dealership retains
independent DAT copies under `dealership/dealership/assets/` and displays
separate editable GLB copies under `dealership/dealership/models/MC3_*.glb`.
The DAT packages include nested members; their shared resources remain in the
extraction above. The GLBs contain selected static geometry with decoded diffuse textures and alpha (paint stays neutral, glass keeps its recovered tint), default native rims/tires with their textures, and
source rest frames composed in the executable's XYZ Euler order; ground shadow planes are omitted and listed in the conversion index. Conversion
limits remain attached to the assets and catalog entries.

`python3 tools/import_mc3_previews.py --refresh-unedited` adds or refreshes
independent preview copies after conversion. Edited working models are preserved;
original package provenance remains in `initialSource`. Rebuild with
`python3 tools/build_dealership.py` after editing a working GLB. See the
[preview investigation](../research/midnight-club-3-remix-previews.md).

`python3 tools/import_mc3_catalogs.py` verifies the extraction against the ISO,
publishes source packages, and preserves existing dealership entries on repeat
imports. Rebuild the two catalog outputs with `tools/build_model_catalog.py` and
`tools/build_dealership.py` after an intentional catalog change. See the
[catalog integration record](../research/midnight-club-3-remix-catalogs.md).

See [extraction findings](../research/midnight-club-3-remix-extraction.md) and
[primary-source research](../research/midnight-club-3-remix-formats.md).
