# Redline native car recovery

The supplied Redline DMG and add-on collection have been inspected as native
archives. The extraction preserves base resources and car add-on carriers, records
each native car configuration variant separately, and decodes the retained named
members with a bounded reconstruction of the shipped i386 decoder. The index is
`redline/cars/index.json`. Retained compact receipts are in
[`evidence/redline-extraction/`](evidence/redline-extraction/), including the
extraction summary, independent output audit, native corpus comparison, check
manifests, source preservation and semantic experiment measurements. Full source
inventories, native instruction spans and raw Jev/API receipts remain in the local
`.scratch/redline/` working set.

## Source identities and staging

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `redline/game-files/Redline.dmg` | 191577525 | `5a13296c7d7f861eb6927e2d3407d82606f71663985be0b1d623d911d03c42da` |
| `redline/game-files/redline_addons.sit` | 480219651 | `1f729115120016d0053076297a9fbf61a9adab1f627990fc01137e6bf527c6f2` |
| Base `data.redplug` | 214022786 | `ecd95f91ec9ecdee45de2af44a5f79650c1d32e35f9260effc41ed8d282a5379` |
| Shipped FAT executable | 5376560 | `7af974e1431ce875ed8729d41354073ac453998a1df26764db6c92d1c5aff7be` |
| Extracted i386 slice | 1149488 | `b2ac41a4335a1a75f71f9e88a4867c08cc514a74426576733e58aa6a05547e22` |

The original DMG REA inventory attempt stopped at the macOS license prompt. No
license was accepted and the game was not executed. `hdiutil imageinfo` identified
an unencrypted UDZO/HFS+ image. `hdiutil convert -format UDTO` produced a raw image,
which was mounted read-only for access to the native package and executable.
The FAT file contains PPC and i386 slices; static native analysis used the
byte-identical i386 slice, since neither slice is host arm64.

`bsdtar` exposed an embedded ZIP containing one Wipeout plug-in, an incomplete
view of the 480 MB StuffIt collection. That result was rejected. The installed
XADMaster framework reported StuffIt 5, 147 entries (three directories and
144 regular files), and no archive corruption. All 82 original files beneath
the archive's `cars/` directory are retained as car envelopes. Nested archives
were unwrapped without executing their contents. One Honda S2000 ZIP required
Python `zipfile`; its eight regular members passed CRC checks.

An independent outer-archive audit matched 142 regular payloads directly to
stored source slices and CRC16 values. Two Arsenic-compressed payloads rely on
XADMaster's decoder. The final 48 source bytes remain in the original archive;
their semantic role was not independently established. Resource forks are not
separately reconstructed by the data-fork staging helper; original carriers and
embedded metadata sidecars are preserved.

## Native format and decoder experiments

The 24-byte header contains `R3Dl1n3\0` at offset 0 and a big-endian member count
at offset 8; 268-byte table entries begin at offset 24. Each entry contains an offset, decoded size, stored
size and 256-byte MacRoman name. Four-byte member flags select raw storage or
LZRW3-A compression. Payload coverage must be exact; unsafe names, overlapping
ranges, unexplained gaps, truncated tokens and excessive sizes fail.

The first single-entry LZRW3 candidate reproduced declared lengths but introduced
dictionary-seed digits into car names. It was rejected. Static instructions at
i386 address `0x716ec` established the depth-eight dictionary: 512 hash buckets,
eight entries per bucket, and a shared replacement cursor advancing on every
insertion, including deferred literal insertions. The initial seed is
`123456789012345678`.

An independent C decoder translated from bounded native instruction spans
agreed with the Python producer on decoded hashes and lengths for 3485 members
across 81 unique native packages. The producer survey contained 82 package
instances and 3495 member instances because one Wipeout package appeared twice.
This survey includes base, car, track and miscellaneous packages; those totals
are not car-only extraction counts. Incorrect hash, length, missing-member and
wrong-package controls were each rejected. A metadata sidecar that is not a native
package is explicitly excluded from this comparison.

The base package contains 1623 retained named resources, totaling 617921798 decoded
bytes, and 19 `.car` files. Its header contains 2671 slots; 1048 empty slots
remain in the original package. Other packages contain 15 nonempty slots with
unreadable offsets. The retained named members still partition their full payloads.
The native loader does not establish that unreadable slots are deleted or inactive;
their runtime meaning remains open. Named empty Finder icon resources are retained.

Static car-parser evidence routes model, interior, shadow, wheel and brake model
fields through resource lookup. Lookup tries the supplied name with `.txr`, then
`.ima`, then the exact name, with ASCII case folding. The extraction records all
candidate local/base matches without claiming the game's plug-in precedence.

REA decoder evidence identifier:
`ev_8d9b62befd12f0c87c73be02274a55bb76d52fd9e01d349265c1e1d039e25148`.
An independent reviewer checked source identities, correctly aligned instruction
boundaries and the dictionary arithmetic; initial lower-confidence semantic
assembly interpretations are retained with their stronger review resolution.

## Extraction behavior and verification

`tools/redline_archive.py` implements the bounded native reader.
`tools/extract_redline_cars.py` verifies staged source hashes, enumerates the
complete staged car-envelope set, checks packed and loose configuration coverage,
preserves source carriers, and builds a deterministic namespaced tree. Duplicate
package declarations, duplicate loose car ownership and case/Unicode path
collisions fail. A nonempty output cannot be overwritten.

The extractor keeps all base resources, 77 packed add-on native packages and
five loose native resource namespaces. It indexes 129 configuration variants:
19 base and 110 add-on configurations (105 packed and five loose). Multiple
variants, duplicate source envelopes and fictional cars remain distinct.
The Lotus Exige SketchUp file is retained separately and is not counted as a
native car configuration. The produced tree contains 3709 files totaling 2202028393 bytes, including the
index. Full byte regeneration and output comparison succeeded. All 4554 existing
source/library files checked against the pre-task snapshot remained unchanged.
The 42 named repository checks passed, including Blender import/edit/export;
focused Redline checks were rerun after the metadata corrections.

Adjacent tests exercise native decoding and extraction preservation, source
tampering, missing/extra/linked output, traversal, incomplete declarations,
duplicate ownership, CR/LF/CRLF metadata line numbers, resource suffix ordering,
and screening outcomes. The repository's named offline checks include both new
test modules. The full extraction check derives the expected tree again from
the source packages, rather than trusting the generated index.

## TypeSafe/Jev and remaining limits

Live TypeSafe documentation for the SDK, Choice, confidence and hierarchical
classification cookbook was read and screened. The SDK and cookbook screens
required review; manual examination found ordinary API instructions and example
strings used as documentation, with no request to expose credentials or override
the task. The OpenRouter compatibility documentation fetch returned HTTP 403;
the existing reviewed provider configuration and installed SDK were used.

Jev screened external documentation and bounded source excerpts, checked static
format and corpus claims, compared native interpretations, and reviewed the
decoder patch. Initial broad claims that mixed unique packages and instances, or
overstated archive scope, were corrected and checked against qualified evidence.
Their original receipts remain available. Independent native and parser reviews
resolved low-confidence semantic interpretations against executable bytes and
concrete tests.

The optional application behavior reuses the existing server-side inventory
judgment module. Each item receives a Choice over car assets, car metadata,
other and unknown; a Noul for substantive car support; and a Score for evidence
quality. Code combines their distributions and confidence with explicit thresholds.
Bounded headers are screened first, warnings and malformed responses fail closed,
and uncertain labels remain advisory. No judgment chooses archive offsets or
changes native content. Experiments compare brief and grounded questions on
16 actual metadata headers plus 12 labeled relevant, unrelated, ambiguous and
conflicting controls, then compare thresholds against the same responses.
On the 28-item labeled sample, brief wording selected 26 correct labels and
accepted 12, all correct; grounded wording selected 27 correct labels and kept
all 28 for review. Neither accepted an incorrect label. A bounded decision call
suggested active source-field excerpts instead of comment-heavy prefixes, at
0.75 probability and 0.71 confidence. Testing that changed evidence with grounded
wording again selected 27 correct labels and kept all 28 for review, providing no
measured gain. The application retains its existing grounded wording, thresholds
and prefix adapter. The 16-item production sample selected car metadata for all
16 but kept every label for review because quality confidence was insufficient.
These results do not establish accuracy outside this small sample.

Three experiment requests plus the production inventory request used 51300 input
tokens and 8169 output tokens; exact totals and SDK latencies are recorded in the evidence receipt.
The SDK calls cost $0.002154600 in provider-reported charges and took
approximately 0.328–0.644 seconds each, including request validation, the provider request and
response composition. Whole-CLI latency including screening was not separately
instrumented. Screening and MCP overhead are additional; MCP calls
report tokens without monetary cost. The live API returned no usable labels
for automatic application under the conservative grounded threshold.

Mesh topology, native texture interpretation, plug-in precedence, transitive
dependency closure, runtime behavior and visual fidelity remain unverified.
Browser conversion, library registration and editable dealership imports are
subsequent work. Monetary cost is reported only if supplied by the provider;
MCP receipts that report token counts alone do not establish billed cost.
