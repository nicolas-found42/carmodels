# Gran Turismo 4 — native car files

Extracted from the supplied PAL PS2 DVD image (boot `SCES_517.19`, ISO volume
`GRANTURISMO4`). The original input remains under `game-files/` and is never
committed or edited; its SHA-256 is
`efcb2ac8428be5f4c67f3d5e97f941f4c267015ab92ea0cc1c624d75cb830ef5`.

Almost all game data sits in `GT4.VOL`, a 3.08 GB RoFS 3.1 volume. Its real file
table is encrypted and compressed behind a decoy GT3-style table. The repo-owned
reader `tools/gt4_volume.py` decodes the table (21,188 files in 432 directories)
and the PS2Zip payloads. Every selected file inflates to exactly its table size.

`cars/` holds **730 cars** (one per eight-character model code in `car/lod/`) and
**6,591 files** totaling **942,613,925 bytes**. Only `index.json` (every file's SHA-256),
`provenance/` and the fixture car `acra0001/` are committed; the rest is local and
re-derived from the disc (see `.gitignore`):

```text
cars/
  index.json                       disc/volume identity, selection rules, every file hash
  <code>/manifest.json             per-file volume path, offsets, stored and decoded SHA-256, timestamp, role
  <code>/car/lod/<code>            race model (CAR4)
  <code>/car/lod/<code>.pat        colour patch (Pat0)
  <code>/car/menu/<code>           menu/showroom model (CAR4)
  <code>/car/open/<code>[.pat]     open-top model and its patch (57 cars)
  <code>/wheel/{lod,menu,open}/<code>  wheels whose file name equals the car code (MDLS)
  shared/wheel|tire|wing/...       880 wheels, 179 tires and 42 wings with no exact car code
  provenance/SYSTEM.CNF
  provenance/GT4.VOL.inventory.json  the complete decoded volume table
  provenance/specdb/GT4_EU2560/...   the native car spec database (race tables excluded)
```

Car IDs are model codes such as `acra0001`; they are not decoded retail names.
The 880 shared wheels include aftermarket sets (for example `bbs_001w`) and wheel
codes without a matching body model; their owners are not inferred.

From the repository root:

```sh
python3 tools/extract_gt4_cars.py --check
```

The check reads the ISO again and rejects changed, missing, extra or linked
output. Initial extraction uses the same command without `--check`, into a new
or empty destination (`--output` chooses another one). It never overwrites.

## Catalogs and previews

Both catalogs list all 730 cars under **Gran Turismo 4**, by retail name from the game's spec
database (for example "Chevrolet Camaro Z28 302 '69"):

- Source catalog (`recovered.html`): `dealership/public/gran-turismo-4/previews/<code>.glb` is a
  static textured preview of the showroom model with four wheels and tires;
  `native/<code>.zip` holds the car's native files and manifest (the "Native files (.zip)" link).
  The ZIPs are local: after extracting, `import_gt4_catalog.py` restores any missing ZIP whose
  rebuilt bytes equal the SHA-256 pinned in the committed `index.json`.
- Dealership (`dealership.html`): independent editable copies `GT4_<CODE>.glb` with the decoded
  model year and mass.

```sh
python3 tools/extract_gt4_cars.py            # local extraction from the ISO (needs an empty destination)
python3 tools/import_gt4_catalog.py          # previews + native ZIPs; restores missing pinned ZIPs
python3 tools/import_gt4_catalog.py --check  # offline: re-derive every preview and ZIP and compare
python3 tools/import_gt4_dealership.py       # editable copies; existing edits are preserved
python3 tools/build_model_catalog.py
python3 tools/build_dealership.py
```

See [the preview note](../research/gran-turismo-4-previews.md) for decoding sources and readings.

## Not established

Previews are static: colour set 0 only (Pat0 colour patches are not applied), no reflections,
lighting, animation or runtime wheel matrices; wheel placement is a reading of spec values.
Race (LOD) models are extracted but not converted. Game-render fidelity is unverified.
See [the extraction note](../research/gran-turismo-4-extraction.md) for format
sources, verification and open items.
