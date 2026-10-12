# Midnight Club: Los Angeles display strings

`tools/mcla_names.py` decodes the pinned localization member of the supplied
Complete Edition disc and joins vehicle identifiers to its original ASCII keys.
The resulting [display-name receipt](evidence/midnight-club-los-angeles/display-names.json)
has one row for each of the 106 extracted vehicles: 47 exact English UI strings
and 59 explicit archive-code fallbacks. All 47 resolved rows are `vp_` vehicles;
the two remaining `vp_` codes are `vp_citybus_07` and `vp_nsn_gtr_08`.

The receipt establishes the shipped display text, not a complete retail identity.
For example, `vp_aud_rs4_07` joins the string `2008 RS4`. The year suffix of the
archive code therefore cannot safely supply the displayed model year. Manufacturer
and retail year remain `Unknown` and `null`; the parser does not expand abbreviations
or choose a similar vehicle's string. Runtime playable-roster membership is also
unresolved.

## Source and layout

Source archive: `xarchive_cache.rpf`, loose member hash `0xa4c1e8fa`, 2,157,137 bytes,
SHA-256 `c01f84edf4563d21084140839b9ead10405f97ae01949ad4abc90b5fb8a3965d`.
The handoff identifies entries 21936 and 21938 as identical copies; the reader
selects by hash, requires all matching loose payloads to agree, and checks the
complete digest before using either. It derives the archive key from the disc's
own executable in memory; neither the key nor the full localization blob is saved
in the repository. The source-disc identity is pinned by the extraction index.

The following is a static layout reading, tested for complete section consumption
and key/record consistency. The layout has **little-endian UTF-16 text**, correcting
the handoff's UTF-16BE description. `53 00 49 00 44 00 45 00` starts `SIDE` in the
English text, and strict UTF-16LE parsing consumes all six language sections exactly.

| Field | Layout |
| --- | --- |
| Header | Version `11` as a little-endian u32; eleven u32 section offsets; u32 `512` of unknown meaning; u32 key count `4018` |
| Keys | 4,018 records: u32 ASCII byte length, that many key bytes, one NUL terminator |
| Language | u32 record count, equal to the key count |
| Text record | u32 name hash; u16 `1`; u32 font byte length; ASCII font bytes; u32 UTF-16 unit count; little-endian UTF-16 text including NUL; floats `1.0, 1.0`; u16 `0` |

The key section ends at `0x18097`. Distinct language sections occupy
`[0x18097,0x6a5b9)`, `[0x6a5b9,0xc3585)`, `[0xc3585,0x11e1d7)`,
`[0x11e1d7,0x176f21)`, `[0x176f21,0x1d002f)`, and `[0x1d002f,0x20ea51)`.
Repeated offsets describe absent language positions. Only language position 0
is used for English display identity. Each of the six populated sections has
4,018 records, and every record joins exactly one original ASCII key through
the lowercased RAGE Jenkins hash. Duplicate keys, hash collisions, unknown hashes,
duplicate records and unconsumed bytes are errors.

Display identity additionally requires the original key to equal the complete
requested vehicle code. A hash alone, a `_shrt` key or a `pinkslip_` key is insufficient.
Surrounding UI whitespace is removed from the display name; the original text,
key, hash, language position and byte offset remain in the receipt. An empty
string or missing exact key yields the code itself. No prefix guessing is needed
because the original key catalog is present.

## Reproduction and controls

From the repository root:

```sh
python3 tools/test_mcla_names.py
python3 tools/line_coverage.py --minimum 95 --modules tools/mcla_names.py --tests tools/test_mcla_names.py
python3 tools/mcla_names.py
```

The source derivation runs from the local disc without writing a receipt by default;
`--write` establishes an intentional receipt. `--table` accepts a local copy of the
same pinned payload. Both paths reproduced the 106-row receipt in this investigation.
Synthetic tests cover source digest rejection, short/pinkslip exclusions, a hash-only
collision, empty display text, Unicode and supplementary characters, malformed
lengths/offsets/terminators, duplicate keys/records, source-member ambiguity and
disc closure on failure. The CLI also corrupts the real version, language offset
and key count and requires rejection for the intended reason before it accepts
the receipt. The parser's synthetic test suite executed 100% of its executable lines.

## Judgment experiments

Live TypeSafe Choice and source-value-extraction documentation informed the candidate
boundary: models can select only supplied values, and a no-match path is necessary.
The docs were screened before use; Jev recommended review (`injection: 0.38`,
`substance: 0.99`, `relevance: 0.71`). Inspection found documentation navigation and
example instructions, with no request to access credentials or override operating
rules. These instructions were treated as documentation data.

Jev compared the handoff's encoding claim with byte/parser evidence and judged
them contradictory (`0.96` overall, `0.98` for encoding). Noul assigned `0.93`
to the risk of deriving the wrong retail year or trim from the archive code.
Its broader proposition about exact-string/fallback preservation was uncertain
at `0.80`; the implementation therefore depends on explicit executable joins,
not that probabilistic assurance. A preliminary evidence verification marked the
encoding and coverage claims verified but requested review (`supports: 0.79/0.76`),
which is retained as an unresolved model review signal for independent assessment.

A six-case classification experiment included exact text with a conflicting code
year, exact normal text, a missing GT-R with a similar Skyline candidate, short-only
and pinkslip-only candidates, and conflicting unpinned source records. Against the
explicit evidence rules, Jev labeled all six as expected: two exact-display, three
no-exact-display and one manual-review case. Top probabilities were `0.93–1.0`;
the call used 1,162 input and 243 output tokens and took 375 ms end to end. This
small authored sample establishes behavior on those cases, not general accuracy.
The tool did not report dollar cost. The unresolved conflicting-source case was
correctly identified as requiring review, not accepted as a vehicle name.

Identity recovery uses deterministic parsing and source joins. The experiments
support the evidence boundary and failure behavior; they do not authorize missing
retail identities. Other localization members, manufacturer-to-vehicle joins,
GT-R/city-bus identity and game runtime presentation remain open.
