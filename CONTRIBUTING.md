# Contributing

## What this repo is

Recovered Ford Racing 2 car assets, plus the tools that recovered them and the verifiers that
check the result. Two corpora:

- `ford-racing-2/` — the verbatim extraction from the PAL PS2 disc (serial SLES-51705), one folder
  per car, provenance and sha256 per file. Joined on the `CARDATA.DAT` `:CAR_TYPE` code.
- `ford-racing-2/recovered/` — the canonical outputs, each car carrying a hash-verified `manifest.json`.

`research/evidence/` holds the receipts that back the claims in `research/*.md`.

## Prerequisites

- **Repo-owned parsers.** The recovery parsers are in `tools/`. Their corpus regression runs on the
  committed reference models. Full archive and VU checks need private static inputs; provision them
  with `tools/provision_static_inputs.py` (see [the input guide](docs/static-inputs.md)).
- **`python3`.** The basic checks run on the stock interpreter with no third-party
  packages — 3.9.6 and 3.14.7 were the observed runtimes. `tools/check.sh` also runs `ruff` when it
  is installed (`pip install ruff`; CI installs it). Tools that read zstd-compressed savestate members
  (`probe_mark_exhaustive.py`, `scan_slot102_selectors.py`, `trace_car_packets.py`, `gsdump.py`,
  `independent_packet_color_check.py`) need a zstd-capable interpreter, which the stock one is not.
- **Node.js** — for `node tools/test_viewer_scenes.mjs`, which checks Geometry choices against all
  35 exported GLBs. `tools/check.sh` runs it when Node.js is available.
- **Blender 4.5.14** — only for `tools/validate_blender_import.py`. The pinned vendor dmg sits in
  `tools/validation-runtime/` (gitignored; re-download and check it against the pinned sha256).
- **PINE + PCSX2** — only for live capture, under `tools/headless-runtime/` (container).

## Static inputs

Some verifiers read inputs derived from the game executable. They are never committed; the
receipts carry their SHA-256 pins, and a tool refuses an input that differs from its pin. Three
environment variables or the explicitly provisioned `.scratch/input-paths.json` name them. Environment
variables override that config. See [input provisioning and regeneration](docs/static-inputs.md).

| Variable | What it points at | Pinned by |
| --- | --- | --- |
| `CARMODELS_OVERLAY_DIR` | A directory with `overlay-N.bin` (raw VU1 microcode) and `overlay-N.s` (its disassembly) for N = 0–6 | `research/evidence/packet-continuation/vu-overlay-residency.json` |
| `CARMODELS_TYPED_EXPORT` | A directory with `inventory.json` and `decompilation/functions/<entry>.c` (the typed decompilation export) | `research/evidence/continuation/source-refresh/refresh-identity.json` |
| `CARMODELS_EXECUTABLE` | The PAL executable `SLES_517.05` | the same file |

```sh
export CARMODELS_OVERLAY_DIR=… CARMODELS_TYPED_EXPORT=… CARMODELS_EXECUTABLE=…
python3 tools/static_inputs.py      # one line per input: found, and equal to its pin
```

The static-input lookup stops with one line naming a missing variable. Legacy recovery tools also
need the archive data in the local bundle. Checks that
need all three skip by name in `tools/check.sh` when they are absent. Captured inputs (savestates,
GS dumps, unpacked memory under `research/evidence/continuation/runtime/`) are gitignored too and
pinned by receipt; re-capture them live (see `tools/headless-runtime/`).

## Run from the repo root

```sh
cd projects/carmodels
python3 tools/verify_recovered_asset_index.py
```

Scripts resolve paths from their own location (`Path(__file__).resolve().parents[1]`), and import the repo-owned parsers. Run them from the repo root.

## The check to run before a PR

Run `tools/check.sh`: it lints `tools/` with `ruff`, runs the asset-index verifier and basic tests, and runs the
archive/executable checks when the inputs are set. CI runs the same script. The checks and their input requirements are:

| Command | What it covers | Inputs |
| --- | --- | --- |
| `python3 tools/verify_recovered_asset_index.py` | Derives the expected index from producer receipts, re-hashes 2579 artifacts across 35 cars, and requires corrupt manifests, cross-car record swaps and changed declarations each to be rejected | Committed corpus |
| `python3 tools/verify_config_data_sound.py` | 35 cars × config (11 files) + data DAT + sound chain | Private archive/executable bundle |
| `python3 tools/verify_sound_bank_index.py` | Sound bank reconciliation | Private archive/executable bundle |

Slower but still offline:

- `python3 tools/test_car_mips.py` (~12 s)
- `python3 tools/verify_selector_word.py` (~16 s)
- `python3 tools/verify_vu_dispatch_map.py` (<1 s; static VU1 dispatch map, 14 mutation controls) and `python3 tools/test_vu_dispatch_map.py` (~1 s) — both need the static inputs
- `python3 tools/verify_vu_pass_handlers.py`, `python3 tools/test_vu1_decode.py` and
  `python3 tools/test_vu_pass_handlers.py` — decoded static pass-4/5 handlers, numeric cross-checks
  and mutation controls; need the configured overlays.

Captured-input checks (no live emulator run):

- `python3 tools/verify_vu_handler_dump.py` and `python3 tools/test_vu_handler_dump.py` compare
  100 pass-4/5 draws; need the pinned race94 GSDump and race95 retained EE/VU captures.

- `python3 tools/verify_pass_source_join.py` and `python3 tools/test_pass_source_join.py` join
  all 37 aligned pass-4 and 63 pass-5 draws to source Headers and the pass-4 view render target,
  reproduce its committed capture-time GS PNG, and reject wrong-Header/wrong-texture controls.
  They need the same runtime captures, `race95-GS.bin`, and the configured executable/typed export.
  Use `--write` only to establish/review an intentional new receipt and PNG; normal runs verify both.

Not available offline:

- `tools/validate_blender_import.py` — run through Blender:
  `blender --background --python tools/validate_blender_import.py`
- Anything under `tools/headless-runtime/` — needs the PINE/PCSX2 container and the disc.

## Read a pass correctly

Each verifier is **self-checking**: it mutates copies of the corpus (rehashed manifests, swapped
records, altered declarations) and requires every mutation to be rejected. A pass therefore means
*the corpus is unaltered **and** the tamper controls still fire* — not merely "no exception was
raised". Success prints `VERIFY OK` / `PASS` and exits 0; anything else exits non-zero.

Do not read a green run as covering what the verifier's own `scope` field excludes. Several of them
record `render_fidelity_complete: false` deliberately — geometry, textures, liveries and GLB output
are covered by other verifiers, and full game-render equivalence is still open.

## Receipts

Verifiers write their JSON receipt under `research/evidence/<area>/`. Those receipts are committed:
re-running a verifier should reproduce its receipt and leave the tree otherwise unchanged. A run that
modifies a committed receipt is a finding, not a cleanup.

The `battery_*` scripts are historical model-judgment experiments, not routine check entry points.
Recovery tools use the local input bundle and repo-owned parsers. Historical receipts preserve their
original provenance text; it is a record of an earlier run, not a current dependency.

## Branches and merging

`main` is protected: no direct pushes, no force pushes, no deletion, and the rules apply to admins
too. Every change reaches `main` through a pull request from a feature branch.

- Branch off `main` using Conventional Branch names: `feature/…`, `bugfix/…`, `chore/…`, lowercase,
  hyphenated. Commit headers use `<type>: <description>`.
- Open the PR against `main` with the template filled in. Resolve every review conversation
  before merging. CI runs `tools/check.sh`; when Actions is unavailable, an explicitly authorized
  merge uses the recorded full local run, with the unavailable CI status stated in the PR.
- **Cleanup after merge is part of merging.** GitHub deletes the remote branch automatically when a
  PR merges. Locally, run `tools/git_cleanup.sh` (`--dry-run` to preview). It fast-forwards
  `main`, then deletes each local and remote branch whose merged PR's head commit equals the
  branch tip, and removes its worktree if the worktree is clean. Branches with unmerged work,
  or with commits added after the merge, are left alone.

## Issues and PRs

- File issues through the forms in `.github/ISSUE_TEMPLATE/`. Real evidence, ordered reproducible
  steps, and unchecked acceptance criteria that a developer could verify without the originating chat.
- PRs follow `.github/PULL_REQUEST_TEMPLATE.md`. The Evidence section wants the command you actually
  ran and its observed result, **Before** and **After**; name what you could not verify instead of
  leaving it implied, and keep failed checks visible.
- Triage labels are the five canonical roles — see `docs/agents/triage-labels.md`.
- Agent-facing repo config (issue tracker, labels, domain docs) is in `AGENTS.md` and `docs/agents/`.
- Code review standards are in `CODING_STANDARDS.md`; vocabulary is in `GLOSSARY-MAP.md` and the glossaries it lists.
