# Gran Turismo source assets

The local `game-files/gran-turismo.bin` is a raw PlayStation CD image. Its boot
configuration identifies `SCUS_941.94`, and its ISO volume is `GRAN_TURISMO`.
The input image and accompanying user-supplied files are preserved.

Native car files have been extracted to `cars/`:

```text
cars/
  index.json
  simulation/<asset-code>/day/{model.car,textures.tex,manifest.json}
  simulation/<asset-code>/night/{model.car,textures.tex,manifest.json}
  arcade/pair-0000/{model.car,textures.tex,manifest.json}
  ...
  _metadata/CARINF.DAT
  _metadata/CARINF.decoded.arc
  _metadata/sections/00.bin ... 38.bin
  _metadata/manifest.json
  _metadata/SYSTEM.CNF
```

There are 344 simulation asset families, each with day and night pairs, plus
40 arcade pairs: 728 models and 728 texture bundles in total. Every arcade pair
has an exact model-and-texture hash match recorded in the simulation set. All
variants remain separate. These counts do not establish how many distinct cars
are selectable in the game.

Every asset manifest records archive ordinal, archive-relative offset, stored
and decoded byte counts, compressed and decoded SHA-256, and extraction limits.
`index.json` records the disc hash and ISO archive LBAs. The external USA name
map supplies asset codes; see `tools/gt1/README.md` for provenance and its license.
No human car names are guessed from colour IDs or binary fragments.

The repeatable offline extractor is `tools/extract_gt_cars.py`. From the repository:

```sh
python3 tools/extract_gt_cars.py --check
```

`--check` re-derives every output from the disc and checks exact bytes and the
file inventory. Normal extraction refuses a nonempty output directory. A fresh
destination can be supplied with `--output`; the original disc is never edited.

Optional `--semantic-report <new-report-file>` assesses bounded inventory names,
sizes and ASCII headers through the TypeSafe Python SDK on OpenRouter. The helper
keeps uncertain answers for review, never changes asset selection or offsets,
and needs an explicit live request plus a server-side `OPENROUTER_API_KEY`.
The offline extraction and tests have no SDK, network or API-key dependency.

These are the game's native `GT-CAR` model and `GT-CTEX` texture payloads.
Static body LODs and the first source colour set are now converted to GLB in
`dealership/public/gran-turismo/`, indexed by the shared source library. All 728
retained pairs also have independent editable copies in the dealership. Wheels
use shared native templates recovered from the packed game executable, each car's
attachment data and its colour-set-0 wheel texture. Retail names, equipment
and performance joins remain unresolved. Neither extraction nor conversion
establishes game-render equivalence.

See [the library conversion note](../research/gran-turismo-library.md) for exact
counts, checks, limitations and reproduction commands. Add newly extracted pairs
by running `tools/export_gt_models.py`, `tools/build_model_catalog.py`,
`tools/import_gt_dealership.py` and `tools/build_dealership.py` from the repo root.
Reimporting preserves existing working models and edits.
After improving source exports, use `tools/import_gt_dealership.py --upgrade-unedited`
to refresh only copies that still match their recorded source. This preserves edited
models, custom catalog fields and original import provenance. See the
[wheel recovery note](../research/gran-turismo-wheels.md) for source pins, native
dimensions, special-asset display policy and remaining rendering limits.
