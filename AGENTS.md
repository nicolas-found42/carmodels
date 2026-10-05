# Agent guide

Repo configuration for the engineering skills.

## Working in this repo

Read `CONTRIBUTING.md` before changing or verifying anything: it lists the prerequisite sibling
checkout (`../../reverse-engineering`), the offline verifiers to run before a PR, and how to read a
verifier's pass (self-checking against tamper controls, not merely "no exception").

## Branches and merging

`main` is protected; change it only through a PR from a `feature/`, `bugfix/` or `chore/` branch.
After a PR merges, run `tools/git_cleanup.sh` so no merged branch or worktree is left behind,
locally or on `origin`. Never push to `main` or force-push.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues on `nicolas-found42/carmodels`, driven with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
