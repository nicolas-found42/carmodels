# Midnight Club 3 Remix catalog integration — 2026-10-10

Both the source catalog and dealership now include the 94 recovered native PS2
vehicle packages. Each catalog has 985 entries: the prior 891 and the added 94.
The new entries have downloadable DAT files and an unavailable 3D preview.
No GLB, thumbnail or synthetic car geometry is substituted for decoded source data.
The [readiness investigation](midnight-club-3-remix-preview-readiness.md) documents
the current PCK/PPF conversion boundary.

## Production behavior and integrity

`tools/import_mc3_catalogs.py` rederives the extraction from the pinned ISO before
publishing the 94 packages under `dealership/public/midnight-club-3-remix/native/`.
The source index preserves each source code, hash, byte size and native member
count. Native entries have `asset_kind: native-package`, profile
`mc3-ps2-native-package-v1`, variant `native`, and no geometry records.

The dealership importer verifies source identity, sizes, hashes, archive table
bounds, member counts and compressed payload termination before installing any
working copy. Independent DAT copies reside under `dealership/dealership/assets/`
with codes beginning `MC3_VP_`. Existing catalog entries and origins remain
unchanged; repeat imports preserve user metadata and working copies. Staging and
rollback protect against partial installation. Corrupt or conflicting inputs fail
before mutation. Source and working paths cannot overlap, escape or use linked files.

The dealership builder compiles a schema-3 download/readiness descriptor for these
entries, with no mesh data. Each viewer clears the previous geometry when selecting
a native package and shows its unavailable preview state. Downloads target the
correct source or dealership copy. Geometry/texture controls are disabled when
there is no decoded model. Native package downloads contain their nested members;
shared external assets remain separately recovered, and runtime closure is unknown.

The production import added 94 source packages and 94 dealership copies. A direct
comparison confirmed all 94 identities equal the source extraction's vehicle set,
and each source/working copy has matching bytes and a distinct inode with one link.
All 891 original catalog entries and origin records are preserved, and none of
9,065 pre-existing asset files changed or disappeared.
[Preservation receipt](evidence/midnight-club-3-remix/catalogs/preservation.json).

## Checks, browser verification and semantic experiments

The new importer tests use a real synthetic ISO/DAVE extraction rather than mock
package bytes. Controls reject rewritten-index source tampering, corrupt hashes,
invalid identities/profiles/paths/member counts, duplicate entries, links,
uncatalogued conflicts and an injected installation failure. Actual source-viewer
callbacks test native selection clearing existing geometry, skipping GLB reads,
disabling unavailable controls and returning to a normal GLB. Dealership callback
tests cover the corresponding cleanup/download behavior. Existing model, editing,
Blender and source-preservation checks continue to run.

An initial full run exposed three affected test assumptions: every dealership copy
was a GLB, the source viewer's isolated callback lacked the new asset-kind helper,
and the JavaScript registry had a fixed count of six. Those tests were extended for
the new behavior. The failed run is retained; the subsequent full run passed all
52 named checks, with final focused checks covering later UI/semantic changes.
Real browser inspection showed 94 MC3 entries in each library with native download
links, unavailable-preview status and unknown performance fields.

The existing server-side Choice/Noul/Score semantic filter now includes the MC3
game and native variant. Two question variants ran against eight labeled queries
covering MC3, native packages, unavailable night/preview restrictions, all games,
Gran Turismo night, a two-game subset and an unsupported retail name. Each selected
seven correct top labels, applied four filters and applied no wrong filter. The
incorrect top label for MC3 night was withheld by support/confidence/coverage
composition. Explicit available-variant wording showed no measured improvement
and was removed. Threshold sweeps reused the answers: 0.75/0.85 accepted four
filters, 0.95 accepted none, with no wrong applications on this sample.

The 16 requests used 25,482 input and 2,964 output tokens with provider-reported
cost $0.001070244. The eight-query runs took 1.835 and 1.542 seconds in total.
This is a small constructed sample, not a general accuracy claim.
[Distributions and metrics](evidence/midnight-club-3-remix/catalogs/semantic-metrics.json).

The earlier jgrep semantic search and Jev decision attempt returned insufficient
credits/HTTP 402. Other MCP screening/verification and the live application SDK
experiments succeeded; availability was route/time dependent. The failed calls
are not approvals. Final raw-patch gates and any independent resolutions are
retained alongside the executed check evidence.

## Limits

Catalog inclusion establishes recovered-package availability, independent copies
and preserved existing data. It does not establish a decoded PS2 PCK/PPF model,
texture/material/part assembly, rendered fidelity, complete runtime dependencies,
verified retail names, playable roster or GLB editing support for MC3. Native
downloads and readiness metadata are the available behavior in both catalogs.
