# Full game decompilation: staged static bar

The project owner named **full game decompilation** as the goal. "The whole game is reverse engineered" is not a testable finish line, so this bar splits the goal into stages, each with a check that can fail on the unchanged PAL corpus (`e69a2afb…7dab`, executable SHA-256 `2167…ea95`). The bar was chosen with Jev (`jev_decide`, `staged_static_bar` 1.00, no contradicted requirement).

All stages are **static and offline**. No game code, emulator or debugger runs. Behavioral equivalence of recompiled code to the original, and recovery of original source, cannot be tested without an oracle that does not exist locally; they are outside this bar and stay unestablished unless the owner approves an oracle.

Each stage claims only what its check measured, keeps an unresolved list, and records Jev claim checks with deliberate overclaims as unsupported.

## Stages

| Stage | What it establishes | Check (can fail) | Status |
| --- | --- | --- | --- |
| D1 EE byte accounting | Every executable byte is owned by a saved function or classified by structure | `tools/verify_text_denominator.py`: classes sum exactly to the unlisted bytes; function-owned and data controls; exact agreement with the Ghidra coverage export per section | Measured; see below |
| D2 EE function boundaries | Each added function has at least two independent static evidence classes | `tools/verify_text_references.py`, `tools/gap_seeds.py`, `tools/verify_gap_candidates.py` plus the batch guard in `tools/ghidra/experimental/pipeline/` | Batch g1 added 412 functions (tier A); tiers B and C held |
| D3 Decompilation quality | Signatures and call arity are consistent; warnings and failures are counted against controls | `tools/verify_decompilation_quality.py` (counts) with guarded changes: [gp context](../fr2-gp-context/README.md) (13,609 offset names → 0) and [small-data types](../fr2-small-data-types/README.md) (1,023 types, 872 constants). Arity mismatches (3,940) and 23,142 undefined-type tokens remain | Partly measured |
| D4 IOP | Every import and export of the 24 modules is resolved or listed as unresolved with a reason | `tools/ps2_irx_catalog.py` (436 of 748 stubs named; 312 unresolved, mostly SDK minor-version mismatch). The game module STREAM.IRX carries its own symbol tables: [all 71 of its stubs are named](../fr2-iop-game-modules/README.md), 211 procedures cross-checked, 32 of 32 catalog candidates confirmed | Partly measured (2 of 24 modules profiled) |
| D5 VU | Each VU program has an entry map from its MSCAL callers | Eight chunks reassemble byte-exact; entry mapping partial | Open |
| D6 Asset consumers | Each loaded asset type is tied to the code that consumes it | Geometry stage 2 and the open fog areas of issue #1 | Open |

## D1 result (export of 4,718 functions)

Of 1,247,328 executable bytes in the ELF, 1,051,516 are owned by saved functions and 195,812 are not. The unlisted bytes split as zero fill 17,576, code-shaped 164,512, VU microcode 13,584 (the eight DVP overlay sources) and sparse nonzero 140. Every nonzero function-owned word (254,934) passes the structural filter, while 59,330 of 73,180 nonzero words in data sections do (81.1%), so the filter separates code from data only partly. Per-section unlisted bytes agree with the Ghidra coverage export in all 13 executable sections.

References into the 503 code-shaped spans: 62 are anchored (54,536 bytes), 8 are reached only through anchored spans (2,272 bytes) and 433 have no static reference (107,704 bytes). Aligned data words pointing into the executable range outnumber misaligned ones 2,771 to 10, so data pointers into code are real, not noise.

## D2 result (batch g1, 5,130 functions)

Batch [g1](../fr2-ee-next-seeds/batch-g1-candidates/README.md) added 412 gap-fill candidates with a closed control-flow walk, stack-frame consistency and layout or reference evidence. Function-owned executable bytes rose from 1,051,516 (84.3%) to 1,111,328 (89.1%) of 1,247,328. Code-shaped unlisted bytes fell from 164,512 to 103,776 in 354 spans: 58 anchored (52,152 bytes), 7 reached only through anchored spans (1,372 bytes) and 289 with no static reference (50,252 bytes). The export has 5,130 generated functions, 0 failed and 685 warning comments. All candidates lack a known direct caller. The suite passes 327 tests (1 skipped).

## What this bar does not establish

A class, an anchor or a tier is evidence about byte structure and references. It does not establish function identity, original names or types, runtime reachability, VU semantics, IOP runtime linking, or that any code behaves as the original does.

## D3 and D4 results (this pass)

The EE executable's gp value was never set, so 13,609 global-pointer-relative operands in 1,871 functions printed as offset names; one guarded transaction fixed all of them (reconciliation 6 of 6). A second guarded transaction typed 1,023 small-data globals from their access patterns and made 872 literal-pool constants show as numbers (5 of 5). Both records contain failures found along the way, including a check that passed for the wrong reason and a transaction whose first form had no effect. Jev's review gate escalated both changes; the escalations are recorded in their bundles.

The two IOP game modules were profiled: STREAM.IRX is `multi_streamer` v6.2 with intact symbol tables (211 procedure names matched against two independent sources); LGDEV.IRX is a stripped wheel driver. Plate comments were applied to 211 and 114 functions.

Open in D3/D4: 3,940 call-arity mismatches (mostly variadic report calls and wrapper functions), 23,142 undefined-type tokens, 709 integer-or-pointer small-data words, 22 of 24 IOP modules unprofiled, EE-to-IOP name transfer.

## Option B review checkpoint

The bounded jump-table recognizer and table reader are committed in `2aadda6`. Pipeline integration and [its checkpoint](../fr2-ee-next-seeds/jump-table-pipeline-review/README.md) are committed at the user's explicit request to commit and push all pending changes. The checkpoint records 499 tests run with the suite passing (one skipped), four intended live rejections, and a postmutation rollback verified after reopening the project. Jev's pipeline review escalated at `safe_to_apply=0.15`. A synthetic last switch case that jumps to itself also exposes an unresolved terminal-exception scope question. Publication does not clear those issues. Batch g4, export reconciliation and new coverage measurements remain unrun. The saved-function baseline stays 5,454; no gain is claimed.
