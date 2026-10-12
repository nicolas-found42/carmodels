# MCLA catalogs and 32-bit showcase indices

The source-model showcase and dealership each contain 1,821 entries: the previous 1,715 plus
106 Midnight Club: Los Angeles source vehicles. The source export has 106 LOD0 GLBs totaling
265,655,196 bytes and 6,851,647 visible mesh-instance triangles. The dealership has independent
editable copies. Local native ZIP downloads retain each car's extracted files and manifest;
shared rims, tires and brakes remain separately recorded source dependencies. The ZIPs and game
inputs are local and gitignored. Generated previews and catalog data are committed.

Names use exact English UI-key joins for 47 vehicles; 59 retain source codes. The corpus contains
41 ambient, 49 player and 16 DLC namespace entries. A namespace is not proof of a playable roster.
Retail year/manufacturer/performance remain unknown, even when a literal display name contains a year.
See the [name parser](midnight-club-los-angeles-names.md) and
[assembly readings and limits](midnight-club-los-angeles-previews.md).

## One index representation

Project-owned showcase triangle indices are unsigned 32-bit little-endian integers. The producer
packs `<I`, the compact decoder uses `getUint32` and `Uint32Array`, and both GLB viewer paths
normalize imported integer accessors to `Uint32Array` before rendering. Imported game/GLB files
retain their actual encoded source widths; the application has no 16-bit output mode or old compact
fallback. Compact showcase schema 4 rejects former schema 1 data explicitly. Textured and native
package descriptors remain separate display kinds, not alternate index encodings.

The temporary validation-only `compact=False` path was removed. Every dealership GLB uses the
same producer validation; textured displays continue loading their actual GLB. A 65,538-vertex
producer test and browser mesh test preserve index 65537. Corrupt indices and stale schema 1 data
are rejected. A comparison of all 35 existing compact cars against the preceding committed data
found identical vertex bytes, triangle order, bounds, source metadata and triangle counts. Raw
index bytes increased from 913,968 to 1,827,936. This is an index-width change, not a geometry edit.

## Import and viewer controls

Source exports preflight native hashes, member coverage, ordinary file modes, static GLB identity
and declared instance triangle counts. Existing exports must equal a re-derivation; missing ZIPs
are restored only after complete preflight, including rebuilt length and hash. Native restoration
and editable import roll back on commit failures. Duplicate IDs, unsafe paths, symlinked indexes,
rehashed wrong GLB identity, invented source names and wrong declarations fail. Repeat dealership
imports retain edits and metadata. Explicit `--upgrade-unedited` refreshes only copies matching
recorded sources and preserves original and latest provenance.

The real 106-car viewer check loads every independent editable GLB through the application loader:
6,851,647 triangles and 6,244 textured mesh instances, with source material factors, decoded pixels,
UVs, normals, 32-bit indices, transforms, centering/floor placement, downloads and resource disposal.
Changed-model and corrupt-texture controls fail. Materials are opaque inspection approximations;
zero blended/alpha-tested meshes is intentional and does not prove original shading.

Actual desktop browser captures show the GT-R in the
[source-model showcase](evidence/midnight-club-los-angeles/preview-source.png) and
[dealership](evidence/midnight-club-los-angeles/preview-dealership.png). The source page exposes 106
entries plus separate GLB/native ZIP downloads. The dealership stock filter exposes 106 entries,
loads its independent GT-R copy, and its Front control follows the source's negative-Z direction.
These captures prove the displayed states, not runtime geometry or shader equivalence.

## Semantic experiments

The optional filter composes Choice selection, Noul support and Score coverage, with an independent
restriction Choice and deterministic catalog/readiness checks. Unavailable/uncertain responses
preserve the current filters. Exact game/variant words stay local. The ambiguous Midnight Club
family name requests clarification when both MC3 and MCLA exist. Known game abbreviations are
expanded in model state without removing any other query word; the original query is retained.
Every independent question receives the same whitelisted game aliases and current catalog facts.

Three experiments compare 28 labeled cases in each of two wordings. They cover both real catalogs,
partial-preview controls, aliases, stock requests, unsupported makes/statistics/fidelity/variants,
mixed games, cross-catalog requests and instruction-like queries. All receipts preserve model
answers, distributions, cost, latency, input pins and fail-closed statuses:

| Experiment | Grounded correct actions | Stateful correct actions | Operational errors |
|---|---:|---:|---:|
| Initial state |18/28|21/28|0|
| Shared alias state |19/28|19/28|0|
| Known abbreviation expansion |22/28|21/23 valid|1; stopped after 24 stateful attempts|

Top-choice accuracy differs from action accuracy: code can correctly withhold a chosen filter
when preview availability or another restriction cannot be satisfied. The normalized stateful
experiment applied eight requests with zero wrong applications among its 23 valid answers; it
stopped on an unusable response to the mixed-game request. The remaining four cases were not
attempted in that run. Grounded wording wrongly applied one cross-catalog request and is not the
production model route. Production uses stateful wording plus the earlier deterministic catalog
check. An alias-state addition alone did not improve this sample; abbreviation expansion improved
observed valid-action accuracy but the stopped run is not a complete benchmark.

Across the three runs, 164 requests were attempted and 163 produced valid experiment judgments.
The provider-reported cost for valid judgments totaled $0.020532288. Input/output usage and end-to-end
latency are retained per experiment; failed-response cost is unknown, not zero. These are small
constructed samples, not general accuracy guarantees or threshold certification. The real failure
is retained and causes no applied filter. Exact words and manual controls remain usable.

## Remaining evidence gaps

Runtime XCC selection, rotational part transforms, decoded tire sizing and complete shared tire/brake
ownership, faithful glass/paint/reflection passes and game-render equivalence remain open. Static
coverage, source preservation and successful display do not establish those stronger claims.
