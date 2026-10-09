# carmodels

A recovered **Ford Racing 2 car-asset corpus** — the 35-car reference models,
textures and sounds extracted from the game, with the tools and verifiers used
to recover them. Two static three.js viewers let you inspect the recovered
geometry in a browser, offline.

The interesting part is `dealership/recovered.html`: it renders the **real
recovered original geometry** with the embedded model textures, straight from
the decoded game data. `dealership/index.html` is an earlier procedural silhouette
gallery that stays available for comparison.

## View the car models

From the repository root:

```sh
python3 tools/build_showcase.py
python3 -m http.server 8080 --directory dealership
```

1. `tools/build_showcase.py` regenerates `dealership/public/cars.json` and the shared
   `dealership/public/models.json` catalog.
2. The HTTP server serves the viewer.

Then open the viewers:

- **<http://localhost:8080/recovered.html>** — recommended first stop. The
  recovered-geometry inspector: pick a car, a tree/record and a texture
  variant, flip rows, toggle wireframe, download the GLB.
- <http://localhost:8080/> — the procedural silhouette gallery.

A local HTTP server is required because the viewers load ES modules; opening
the files over `file://` will not work. Everything is offline — three.js r182
(module, core and `OrbitControls`) is **shipped in this repository** under
`dealership/vendor/`, with no build step and no runtime CDN dependency. The 35 GLBs
under `dealership/public/ford-racing-2/` and `dealership/public/cars.json` are committed
too, so the viewer runs from a fresh clone with no manual download.

## What is in here

- `dealership/` — the two static three.js viewers and their data (see
  [`dealership/README.md`](dealership/README.md)).
- `ford-racing-2/recovered/` — the canonical recovered index and per-car manifests.
- `ford-racing-2/` — the per-car reference corpus: models, textures, sounds.
- `research/` — format notes, original-recovery synthesis and evidence receipts.
- `tools/` — recovery, export and **verifier** scripts.

## Adding games

Source assets belong in a root folder named after their game, such as `ford-racing-2/`.
Use lowercase game folder names with hyphens between words.
Keep original models, textures, configuration, sound files and recovery manifests together there.
The shared browser dealership lives in `dealership/`; its exported GLBs and per-game export
index belong under `dealership/public/<game>/`. Each export index uses the same `cars` record
format as Ford Racing 2, including `code`, `file`, `bytes`, `sha256` and `records`.
Run `python3 tools/build_showcase.py` after adding exports to rebuild the shared model catalog.
The recovered inspector lists every game in that catalog and identifies cars by game plus code.
The procedural silhouette gallery currently uses Ford Racing 2 metadata.

Recovery evidence and tooling stay in `research/` and `tools/`.

## Honesty labels

Two things in the viewer are candidates, not proven originals, and are labelled
as such in the interface:

- the **silhouette gallery** (`index.html`) meshes are **procedural
  reconstructions**, not the game models;
- the recovered inspector's triangle-strip, normal, UV and texture-selector
  interpretations are **candidate** mappings, and its per-car colors come from a
  **best-effort paint sample** off the menu-icon buffer.

The recovered geometry bounds, however, are verified: the original-coordinate
mapping reproduces all 1,837 nonempty geometry records' bounds. See
[`research/original-recovery.md`](research/original-recovery.md) and
[`dealership/README.md`](dealership/README.md) for the full fidelity discussion.

## Verify

The repo ships offline verifiers (they do not need the viewer or the game):

```sh
python3 tools/verify_recovered_asset_index.py
python3 tools/verify_config_data_sound.py
python3 tools/verify_sound_bank_index.py
```
