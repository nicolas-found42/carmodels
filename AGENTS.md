# Agent guide

Repo configuration for the engineering skills.

## Working in this repo

Read `CONTRIBUTING.md` before changing or verifying anything: it lists the offline checks (`tools/check.sh`),
the static inputs some verifiers need, and how to read a verifier's pass (self-checking against tamper
controls, not merely "no exception"). Review against `CODING_STANDARDS.md`. Research notes and their open
items are indexed in `research/README.md`.

## Branches and merging

`main` is protected; change it only through a PR from a `feature/`, `bugfix/` or `chore/` branch.
After a PR merges, run `tools/git_cleanup.sh` so no merged branch or worktree is left behind,
locally or on `origin`. Never push to `main` or force-push.

## Jev tools

When the `jev_*` MCP tools are not listed, call them with `tools/jev_mcp_call.py` (`--batch` runs several
calls in one process); argument names are in `docs/agents/jev-tools.md`.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues on `nicolas-found42/carmodels`, driven with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context: `GLOSSARY-MAP.md` lists `GLOSSARY.md` (recovery) and `dealership/GLOSSARY.md`; decisions are in `docs/adr/`. See `docs/agents/domain.md`.
