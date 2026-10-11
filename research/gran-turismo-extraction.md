# Gran Turismo native car extraction — 2026-10-09

The supplied raw Mode 2 Form 1 CD image contains the `GRAN_TURISMO` ISO volume
and `SCUS_941.94` boot configuration. Its SHA-256 is
`e1ba7def96b7f213637fa82658b53c34a3a5f6c54df7d7e5ab9c3f53a2d41f03`;
size is 693,668,304 bytes. Original inputs remain in `gran-turismo/game-files/`.

## Established extraction boundary

`CAR.DAT` at LBA 855 contains 1,376 GT-ARC members: 688 alternating GT-CTEX/GT-CAR
pairs. The pinned USA map organizes them into 344 day/night families.
`CARCADE.DAT` at LBA 8,853 contains 80 members, or 40 pairs. All 40 have exact
texture-and-model hash matches in the simulation set, recorded without deduplication.
The compressed `CARINF.DAT` outer stream expands to a GT-ARC with 39 shared
equipment/specification/colour sections, all preserved as native bytes.

The extraction contains 2,228 files totaling 41,574,722 bytes, including the
native assets, manifests, index, boot configuration, compressed/decoded CARINF,
and its sections. Archive offsets and stored/decoded hashes are preserved.
Every expected output can be re-derived from the original disc with
`python3 tools/extract_gt_cars.py --check`; stale, missing, extra, modified or
symlinked output files fail the check.

## Primary format evidence

- [GTExplorer archive reader](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/utils/archive.py):
  content type/count at 0x0C, `<III>` offset/stored/decoded size records at 0x10.
- [GTExplorer GTZIP decoder](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/utils/gtzip.py):
  low-bit-first flags, zero for literal; one for length-plus-three and
  distance-plus-one back-reference, including extended distances.
- [Independent gt2tools archive reader](https://github.com/pez2k/gt2tools/blob/3e4f873f2b989bcb89708973cf9c4ccc05aa0213/GT1ArchiveExtractor/GT1ArchiveExtractor/ArchiveFileList.cs):
  corroborates count/table layout. The production parser routes by content type,
  including compressed streams whose stored and decoded lengths happen to match.
- [USA retail map](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/filelists/filelist_usa_retail.txt):
  all 1,376 CAR assignments reconstructed exactly from the imported compact code
  list. MIT notice retained under `tools/gt1/LICENSE`.
- [Texture parser](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/utils/gttex.py):
  byte 0x10 contains colour IDs; a conflicting optional-short-name comment in
  another helper is not treated as a car identity source.

REA MCP was connected, but `open_binary` returned `target_unavailable` with
`unsupported binary format` for this raw CD. The disc/archive evidence therefore
comes from format-aware code and independent byte checks, not an REA import.

## Checks and evidence

The independently written extractor validates raw sector sync, mode and subheader
copies, ISO endian copies and extents, archive bounds and decoded lengths,
back-reference bounds and pairing signatures. Unsupported streaming Form 2 files
are inventoried without interpreting their payload as ISO user-file data.
Two source hashes around derivation detect a changed disc. Output installation is
staged, checked and limited to a new or empty destination.

The tests use synthetic cooked/raw discs, literals, short/extended/overlapping
matches, compressed equal-length entries, invalid extents/endian copies/sync/Form 2,
wrong pair signatures/order, truncated streams, size overflow, tampered output
with a rewritten manifest, unsafe destinations and a mutated name map.
All 34 top-level repository commands have status `pass` and exit code 0 in
`.scratch/gran-turismo/checks-run-2/results.json`, with no top-level skips.
`test_run_checks.py` deliberately runs failing and skipped nested fixture commands
to test aggregation; their expected failure lines are not suite failures.
The earlier run retained one failing judgment fixture; its probability
was changed without updating the expected confidence. The corrected fixture and
documented confidence checks passed in the final run.

Independent `.scratch/gran-turismo/independent-validation.json` uses its own raw
sector/ISO traversal and the actual pinned GTExplorer decoder. It compares all
1,456 car members, the CARINF outer stream and all 39 sections, output bytes,
all 728 manifests and all 1,376 reconstructed name assignments. This is a
cross-check of extraction; it does not validate meshes, palettes or rendering.

## TypeSafe/Jev use and measured limits

External source and live documentation screening receipts are retained under
`.scratch/gran-turismo/external-research/` and the semantic experiment directory.
Extraction-count claims were verified by Jev automatically at confidence 1.00
and 0.94. Valid review/escalation signals remain recorded for independent review;
they are not cleared by repeated model requests.

The optional inventory helper batches Choice for archive role, Noul for substantive
car-role support and Score for evidence quality. It uses the
[Python SDK](https://docs.typesafe.ai/sdk/python) and documented
[OpenRouter compatibility](https://openrouter.ai/docs/guides/community/typesafe-sdk).
It retains complete distributions, provenance, cost/usage, failure status and
latency. Labels are advisory and cannot change native-file selection or bytes.
The SDK is lazy and optional, and credentials remain in the CLI environment.

Two question wordings were tested on 12 labeled synthetic cases, including car
meshes/textures, metadata, unrelated files, ambiguous generic archives, misleading
names and empty files. Instruction-like inventory strings are covered by offline
input-boundary controls, not by these two live batches. Each wording's top
labels matched 11/12 fixtures. After confidence, support, quality and disagreement
checks, grounded wording accepted one advisory label and brief wording accepted
two; neither accepted a wrong fixture label. Threshold sweeps reuse raw answers.
These small constructed examples are not a general accuracy estimate.

Those two batches plus a filename-only 26-item real-disc batch made 150 primitive
judgments: 25,036 input and 4,031 output tokens, provider cost $0.001051512, with
request latencies 0.39–0.49 seconds. A separate end-to-end extractor run supplied
bounded ASCII headers for the 26-item inventory: 13,808 input and 2,107 output
tokens, cost $0.000579936. All real-disc labels remained review cases under final
composition. The extraction proceeded by strict parsers, not those labels.
These costs exclude development screening/review calls.

Original wire-validation failures are retained. Jev rounds probabilities and
expected scores to hundredths; validation now accounts for analytically bounded
rounding error. Contradictory Choice/Noul signals and malformed answers cannot
be accepted. No unchanged valid model decision was recalled to improve its score.

## Unresolved

- Human display-name and selectable-car identities beyond external asset codes.
- Native geometry/LOD, palette/colour, texture conversion and GLB export.
- Equipment/specification sections' relationships to individual car assets.
- Dealership import and rendered fidelity. No game execution is claimed.
