# carmodels

Recovered Ford Racing 2 assets and two independent static three.js apps. The dealership is the default app, with 35 editable display models. The source inspector displays the recovered original geometry and embedded textures. The earlier procedural silhouette gallery has been removed.

## Open the apps

From the repository root:

```sh
python3 tools/build_dealership.py
python3 tools/build_model_catalog.py
python3 -m http.server 8080 --directory dealership
```

- [Dealership](http://localhost:8080/) redirects to `dealership.html`. Edit its independent GLBs and metadata, then rebuild its display data.
- [Source models](http://localhost:8080/recovered.html) lets you select a game and car, inspect geometry and texture variants, toggle filtering and wireframe, and download the source GLB.

All model data and three.js r182 are committed, so a fresh clone runs offline without npm installation. A local HTTP server is required for ES modules.

## Repository layout

- `dealership/` — both app entry points, shared vendor libraries and compiled browser data. See [the app guide](dealership/README.md).
- `dealership/dealership/` — independent editable GLBs, catalog and initial-fork provenance. See [the editing guide](dealership/dealership/README.md).
- `ford-racing-2/` — original models, textures, sounds and configuration; `recovered/` beneath it holds canonical manifests.
- `dealership/public/ford-racing-2/` — exported source GLBs and their per-game index.
- `research/` — recovery notes and evidence receipts.
- `tools/` — recovery, export, build and verifier scripts.

`tools/build_dealership.py` reads the editable dealership inputs and preserves edits. `tools/build_showcase.py` remains a compatibility entry point for that build. Recovery/export commands update source outputs without replacing dealership models.

## Adding games

Put source assets in a root folder named for the game, using lowercase words separated by hyphens. Keep original models, textures, configuration, sounds and recovery manifests together. Put exported source GLBs and an `index.json` under `dealership/public/<game>/`. Each index has `cars` records with `code`, `file`, `bytes`, `sha256` and `records`.

Run `python3 tools/build_model_catalog.py` to rebuild `dealership/public/models.json`. The source inspector identifies models by game plus code, so different games can share a car code. The dealership remains an independently edited edition; source catalog updates do not replace it.

## Fidelity and verification

The original-coordinate mapping reproduces all 1,837 nonempty geometry records' bounds. Triangle-strip, normal, UV and texture-selector interpretations retain their documented candidate limits. The dealership's baked display geometry and illustrative body tint do not establish original game shading. Full game-render equivalence remains open. See [the recovery report](research/original-recovery.md) and [the app guide](dealership/README.md).

Run `tools/check.sh` before a PR. It retains complete logs and pass/fail/skip states, verifies corpus integrity using tamper controls, checks app load recovery and dealership independence, and runs the Blender edit/export regression when its runtime is available. Read [CONTRIBUTING.md](CONTRIBUTING.md) for inputs and the scope of each check.
