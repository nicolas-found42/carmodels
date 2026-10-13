---
status: accepted
---
# Game source trees live under `games/<game>/`

Each game's source tree (its reference extraction, recovered corpus, local disc inputs and README) lives
under `games/<game>/`, named by the same game ID the catalogs, `dealership/public/<game>/` and evidence
areas use. The dealership owns the general catalog: `dealership/dealership/catalog.json`, one entry per
source variant, with no cross-game merging, because retail identities are mostly undecoded. Compiled and
served files stay under `dealership/public/<game>/`, where the viewer loads them; recovered sources are
not mixed with build output.

Tools, research notes and receipts stay in their shared folders (`tools/`, `research/`). Each
`games/<game>/README.md` indexes that game's tools, notes, evidence and published files instead of
holding them, so tool imports and served paths are unchanged.

Paths that a tool reads, or a check reproduces, were rewritten when the trees moved. Historical records
(review bundles, reviewed diffs, gate results, logs) keep the paths they recorded, as CONTRIBUTING's
receipt rules require. No compatibility links exist at the old root paths.
