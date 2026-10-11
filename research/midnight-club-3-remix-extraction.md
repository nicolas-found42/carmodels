# Midnight Club 3 Remix native vehicle extraction — 2026-10-09

The supplied 8,539,963,392-byte cooked PS2 ISO contains boot serial `SLUS_213.55`.
Its SHA-256 is `de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9`.
The original image remains in `midnight-club-3-remix/game-files/`.

## Recovered files and boundary

The extraction under `midnight-club-3-remix/cars/` contains 94 root `vp_*.dat`
vehicle carriers, all 4,323 nested native member payloads, and the shared outer
vehicle namespaces. The corpus has 7,283 files totaling 569,084,266 bytes,
including carriers, manifests, index and provenance. The index lists 7,282 files
and excludes itself from that list. Counts describe source carriers and native
occurrences, not distinct real-world cars or a verified playable roster.
[Extraction receipt](evidence/midnight-club-3-remix/extraction.json).

ASSETS.DAT at ISO LBA 1,369,534 has 18,416 DAVE/Dave table records. The declared
selection keeps non-directory members under `vehicle/`, `resources/vehicle/`,
`tune/vehicle/`, `tune/phys/`, `tune/traffic/`, `tune/rider/` and `physicslib/`,
root names matching `vp_[a-z0-9_]+.dat`, and `vehiclesexported.txt`. This selects
2,860 outer payloads. Vehicle carriers are retained and unpacked completely;
other selected resources retain their source paths under ordinal directories.
The 94 carriers are part of the outer count, so decoded source outputs total
2,860 + 4,323 = 7,183; generated manifests/provenance/index make up the remaining
100 disk files.

Duplicate names never overwrite one another. The source has 1,525 duplicate-name
occurrences beyond the first across the full ASSETS table. Selected resources
contain 158 duplicated names with 367 additional occurrences; all are retained.
Examples include repeated brake/tire/shared-texture PPF entries. Their runtime
precedence is not inferred. The 350Z carrier expands to 109 native members,
including PCK resources with named bumper, skirt, light and spoiler components.

TEXTURE.DAT at LBA 454,764 has 268 records; BANKS.DAT at LBA 1,343,671 has 283.
They are inventoried, without extracting their city texture/audio payloads.
STREAMS.DAT is identified in the ISO inventory as a separate `Hash` container;
this task does not recover its audio mappings. The static namespace selection
is explicit, and does not establish complete runtime dependency closure.

## Format evidence and checks

The parser follows the public [Edness DAVE/Dave implementation](https://github.com/EdnessP/scripts/blob/main/midnight-club/dave.py),
retained with source SHA-256 `d8ce48672e1af5ac44e8a901cac57b5bc2f99ddd12ea9deedd9949a2c14f1303`.
It validates cooked ISO endian copies, extents and names, bounded archive tables,
packed-name prefix bounds and character symbols, safe output paths, member sizes,
raw-DEFLATE termination and exact decoded lengths. Source hashes before and after
derivation reject changed input. Output installation uses a temporary tree and
requires a new or empty destination. Every extracted native payload carries stored/decoded provenance.

`python3 tools/extract_mc3_cars.py --check` successfully rederived every expected
output from the original disc and compared all files. Expectations come from
source bytes, not the existing output index. Tampered payloads with a rewritten
index, missing/extra output, linked files/directories, changed source and malformed
name/table/DEFLATE controls each fail for their intended reason. All 50 repository
checks passed, including the two new suites and existing Blender checks. Final
focused lint/archive/extraction checks also passed after the advisory experiment.
[Check manifest](evidence/midnight-club-3-remix/checks.json),
[focused checks](evidence/midnight-club-3-remix/focused-checks.json).

An independently written ISO traversal and adapter executed the screened upstream
`read_dave` implementation using read-only source regions and hash-only sinks.
It matched all 18,416 outer table records, all 2,860 selected outer payloads and
all 4,323 nested members across 94 carriers. Comparisons included names, ordinals,
name offsets, payload offsets, full/stored sizes, stored hashes, decoded hashes
and actual output-file hashes. It rehashed all 7,282 indexed files and checked the
7,283-file disk set. Wrong-name and wrong-decoded-hash controls were rejected.
The main audit took 20.92 seconds. It independently validates ASSETS/nested
extraction; TEXTURE/BANKS inventory files were rehashed, not independently parsed.
[Independent output audit](evidence/midnight-club-3-remix/independent-output-audit.json).

A supplemental independent source-name decode applied the declared selection
rules without taking ordinals from the index, and matched the complete 2,860-member
selection and 94-carrier map. A dropped-selected-ordinal control was rejected.
This closes the earlier selection-policy gap while retaining the runtime-closure
limit. It took 3.831 seconds.
[Selection audit](evidence/midnight-club-3-remix/independent-selection-audit.json).

The preservation audit rehashed 13,280 pre-existing tracked files, excluding the
three declared shared text files owned by this task. None changed or disappeared.
It checks working-file bytes/sizes; it does not claim a Git index identity check.
[Preservation receipt](evidence/midnight-club-3-remix/preservation.json).

REA MCP was available, but opening the extracted game executable returned
`target_unavailable` with `unsupported ELF architecture`. Native MIPS decompilation
was unavailable in that session; no REA analysis database was opened. Archive
claims rest on format-aware byte extraction and independent checks.
[REA result](evidence/midnight-club-3-remix/rea-open.json).

## TypeSafe/Jev experiments and limits

The [format research](midnight-club-3-remix-formats.md) retains Firecrawl,
gh_grep, context-awesome, external-content screening, semantic source selection,
source classification, bounded source-value extraction/audit, comparison and
claim verification. Live TypeSafe SDK/API, provider and cookbook references were
read before the integration experiments. A low-confidence numerical audit claim
was retained for independent review; executable equality results remain its evidence.

The extractor adds optional screened advisory inventory assessment through the
existing server-side Choice/Noul/Score module. Choice selects asset/metadata/other/
unknown roles, Noul estimates substantive car support, and Score grades evidence
quality. Code combines distributions, confidence, margin and support thresholds.
No label changes native bytes, selects offsets or removes resources. Non-pass
screening or provider errors accept no advisory labels; credentials stay in the
CLI environment and only bounded metadata is sent.

Two wording variants were evaluated on 20 explicitly labeled constructed cases:
car geometry/textures/packages, car metadata, unrelated city/audio/UI/code,
ambiguous containers, missing evidence and conflicting filenames/headers. Each
variant selected 20 correct top labels. Brief wording accepted seven advisory
labels and grounded wording four; neither accepted a wrong label. Threshold
sweeps reused the same answers: brief accepted 8/7/3 and grounded 6/4/0 at the
three retained settings, with zero wrongly accepted labels on this sample.
These are small constructed-case results, not general accuracy estimates.

The 24 actual MC3 samples all remained under review; they have no independently
verified semantic role labels, so real-corpus accuracy is not claimed. An alternate
descriptor supplied known unpacked-member counts for four carriers. It still
accepted zero advisory labels and was not retained in the application. The
original bounded byte/header adapter and conservative grounded thresholds remain.
[Experiment metrics](evidence/midnight-club-3-remix/semantic-metrics.json),
[alternative descriptor experiment](evidence/midnight-club-3-remix/semantic-enhanced.json).

The four SDK requests used 46,259 input and 7,159 output tokens, with provider-reported
cost $0.001942878. SDK request latency ranged from 0.330 to 0.592 seconds. The actual
inventory request took 1.312 seconds including screening; the alternate descriptor
request took 1.396 seconds. MCP research/review/screening costs are additional and
not established by those SDK charges. Full distributions, statuses and usage are
retained in the experiment receipts.

## Remaining work

Native car files are recovered within the declared extraction boundary. PS2 PCK
geometry, PPF/native TEX decoding, material/wheel/part assembly, GLB export,
viewer/dealership integration, runtime dependency closure and visual fidelity
remain unverified. Xbox XBCK and mixed-platform plain-TEX readers are research
leads; they are not treated as established PS2 PCK converters.
