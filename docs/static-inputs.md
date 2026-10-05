# Private static inputs

Parser code lives in `tools/`. Game data, executable-derived exports and captures are separate inputs. A fresh clone can run the asset-index verifier, input-lookup tests and parser corpus regression with the committed reference models. Full checks need the private inputs below.

## Provision an independent local bundle

`python3 tools/provision_static_inputs.py --from-bundle /path/to/input-bundle`

The command verifies the PAL archive identity, typed inventory and overlay pins before copying. It makes independent file copies under `.scratch/inputs/`, verifies them again, and writes `.scratch/input-paths.json`. Neither location is tracked. It rejects symlinks and refuses to replace existing local files with different bytes. After provisioning, the source bundle can be disconnected.

The source bundle contains these paths:

| Input | Path inside the supplied bundle |
| --- | --- |
| Disc and extracted archive | `games/ford-racing-2/`: `ford-racing-2.bin`, `ford-racing-2.cue`, `extracted/SLES_517.05`, `extracted/FILES.HDR`, `extracted/FILES.DAT`, `extracted/files/` |
| VU overlays | `.scratch/evidence/vu/private-work-016dac24781c4c9ea7c99aa0fa79c310/overlay-N.bin` and `.s` |
| Typed export | `.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po/`: `inventory.json`, `decompilation/manifest.json`, `decompilation/functions/` |
| Historical export | `.scratch/evidence/static-export.json`, `.scratch/mesh/codex-root/decompile-all-02/` |
| Historical dispatch functions | `.scratch/mesh/codex-root/decompile-dispatch-all-3837-02/` |
| Pinned graphics contracts | `.scratch/mesh/codex-root/github-raw-Vif_Unpack.cpp` and `github-raw-GSTables.cpp` |
| Optional historical research | `notes/evidence/fr2-*/` |

The nested paths preserve existing export identities; they describe data layout, not a required repository layout. No input bundle needs `.git` or parser code to run recovery tools. Parser SHA-256 values remain equal to the producer receipts.

## Configure other locations

`tools/static_inputs.py` reads `.scratch/input-paths.json`. Set `CARMODELS_INPUT_CONFIG` to select another JSON file. The keys are `CARMODELS_BUNDLE`, `CARMODELS_OVERLAY_DIR`, `CARMODELS_TYPED_EXPORT` and `CARMODELS_EXECUTABLE`. Environment variables override the JSON values. The three per-input values support the VU verifiers; the bundle root supports older recovery tools. CLI `--source` or `--input-bundle` options override the default data root for the tools that expose them.

Run `python3 tools/static_inputs.py` to check pins, then `tools/check.sh`. A full run includes the VU checks. With no configuration, these skip by name; the asset-index and parser checks still run. The new parser regression uses committed reference models and needs no private inputs.

## Re-create missing inputs

- Start with the pinned PAL disc/archive files. `tools/corpus_contract.py` lists the expected lengths and hashes. An extraction must match `tools/format_contracts.py`'s independent archive parser; copying a differently extracted corpus is rejected.
- Obtain the typed export with the exact inventory and pseudocode identity recorded in `research/evidence/continuation/source-refresh/refresh-identity.json`. A new decompiler export can differ even for the same executable; it needs an explicit evidence refresh rather than silently changing a pin. This repo consumes the pinned export and does not supply a complete decompiler export driver.
- Restore overlay binaries and disassembly matching `research/evidence/packet-continuation/vu-overlay-residency.json` and the dispatch receipt. The handler decoder checks instruction words against the pinned disassembly. Reconstructing overlay bytes from an executable does not by itself reproduce a typed export.
- Runtime savestates and GSDumps are captured with `tools/headless-runtime/` and unpacked with `tools/unpack_runtime_state.py`. Their receipts record hashes. Do not substitute another frame merely because its car list looks the same.

Provisioning copies and verifies existing pinned artifacts; it does not claim to regenerate every artifact from the disc automatically. No game execution is implied by a static pin check.
