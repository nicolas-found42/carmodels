# Contributing

## What this repo is

Recovered Ford Racing 2 car assets, plus the tools that recovered them and the verifiers that
check the result. Two corpora:

- `reference/ford/` — the verbatim extraction from the PAL PS2 disc (serial SLES-51705), one folder
  per car, provenance and sha256 per file. Joined on the `CARDATA.DAT` `:CAR_TYPE` code.
- `recovered/` — the canonical outputs, each car carrying a hash-verified `manifest.json`.

`research/evidence/` holds the receipts that back the claims in `research/*.md`.

## Prerequisites

- **A sibling checkout of the extraction tree at `../../reverse-engineering`.** Five shared parser
  modules live in its `tools/` — `ps2_sections.py`, `corpus_binding.py`, `format_contracts.py`,
  `ps2_container.py`, `ps2_texture_indices.py` — and the scripts here import them from that path.
  Without it, everything past `build_reference.py` fails at import.
- **`python3`.** The three verifiers below run on the stock interpreter with no third-party
  packages — 3.9.6 was the observed runtime. Tools that read zstd-compressed savestate members
  (`probe_mark_exhaustive.py`, `scan_slot102_selectors.py`, `trace_car_packets.py`, `gsdump.py`,
  `independent_packet_color_check.py`) need a zstd-capable interpreter, which the stock one is not.
- **Blender 4.5.14** — only for `tools/validate_blender_import.py`. The pinned vendor dmg sits in
  `tools/validation-runtime/` (gitignored; re-download and check it against the pinned sha256).
- **PINE + PCSX2** — only for live capture, under `tools/headless-runtime/` (container).

## Run from the repo root

```sh
cd projects/carmodels
python3 tools/verify_recovered_asset_index.py
```

Scripts resolve paths from their own location (`Path(__file__).resolve().parents[1]`), and the
import path for the shared parsers assumes this layout. Run them from the repo root.

## The check to run before a PR

Minimum, offline, no Blender or PINE — about 3.5 seconds in total:

| Command | What it covers | Observed |
| --- | --- | --- |
| `python3 tools/verify_recovered_asset_index.py` | Derives the expected index from producer receipts, re-hashes 2579 artifacts across 35 cars, and requires corrupt manifests, cross-car record swaps and changed declarations each to be rejected | ~3 s |
| `python3 tools/verify_config_data_sound.py` | 35 cars × config (11 files) + data DAT + sound chain | <1 s |
| `python3 tools/verify_sound_bank_index.py` | Sound bank reconciliation | <1 s |

Slower but still offline:

- `python3 tools/test_car_mips.py` (~12 s)
- `python3 tools/verify_selector_word.py` (~16 s)
- `python3 tools/verify_vu_dispatch_map.py` (<1 s; static VU1 dispatch map, 14 mutation controls) and `python3 tools/test_vu_dispatch_map.py` (~1 s)

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

Some tool scripts are exploratory one-offs kept as provenance rather than as entry points — the
`battery_*` series, and scripts whose non-stdlib imports point at a research checkout outside this
repo. They are not expected to run here.

## Branches and merging

`main` is protected: no direct pushes, no force pushes, no deletion, and the rules apply to admins
too. Every change reaches `main` through a pull request from a feature branch.

- Branch off `main` using Conventional Branch names: `feature/…`, `bugfix/…`, `chore/…`, lowercase,
  hyphenated. Commit headers use `<type>: <description>`.
- Open the PR against `main` with the template filled in. Resolve every review conversation
  before merging; there is no CI to wait on, so the Evidence section is the review.
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
