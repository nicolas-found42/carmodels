# Agent guide

Repo configuration for the engineering skills.

## Working in this repo

The repo is a showcase of recovered car models; the per-game extraction and recovery tooling exists to
produce those models, which are committed. `tools/check.sh` (and CI) verifies the models and the showcase.
After changing extraction, conversion, import or recovery tooling, run `tools/check.sh --game <slug>`
for each affected game; use `--games` for shared tooling. Add `--full` when changing derivation logic
or regenerating receipts, or use `--only` for the affected verifiers. `--full` without `--game` runs
all disc, corpus and private-input checks.

Verify before done: run the real checks first; a pass means corpus unaltered **and** tamper controls
fired. Review path is `docs/agents/review-workflow.md` — bundle every change, never resolve your own
escalation, never script a reviewer's verdict.

Read `CONTRIBUTING.md` before changing or verifying anything: it lists the checks and their tiers,
the static inputs some verifiers need, and how to read a verifier's pass (self-checking against tamper
controls, not merely "no exception"). Review against `CODING_STANDARDS.md`. Research notes and their open
items are indexed in `research/README.md`.

For dealership model or catalog edits, read `dealership/dealership/README.md`.

## Branches and merging

`main` is protected; change it only through a PR from a `feature/`, `bugfix/` or `chore/` branch.
After a PR merges, run `tools/git_cleanup.sh` so no merged branch or worktree is left behind,
locally or on `origin`. Never push to `main` or force-push.

## Delegation and sessions (defaults: no restating needed)

Sessions run multi-agent by default. Use subagents with distinct scopes; you own evidence review,
integration, and verification. Tell the user only when you deliberately work solo.
Propagate repo tool policy to every subagent (`find` first for unknown locations, `read` ranges,
`edit` for surgical changes, run `tools/check.sh` per the tiers below) — brief them, don't assume it.

End-of-work sweep runs unprompted before you report done: land open PRs, scan `gh` draft PRs and
`git worktree list` for unfinished work (merge or delete), run `tools/git_cleanup.sh`. Report what
still needs the user.

## Jev tools

When the `jev_*` MCP tools are not listed, call them with `tools/jev_mcp_call.py` (`--batch` runs several
calls in one process); argument names are in `docs/agents/jev-tools.md`.

Before work in a dirty checkout, or Jev review/escalation, read `docs/agents/review-workflow.md`.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues on `nicolas-found42/carmodels`, driven with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Handoff

Handoff files are briefing context, never itineraries; handoffs go to `$TMPDIR`. See `docs/agents/handoff.md`.

### Domain docs

Multi-context: `GLOSSARY-MAP.md` lists `GLOSSARY.md` (recovery) and `dealership/GLOSSARY.md`; decisions are in `docs/adr/`. See `docs/agents/domain.md`.
