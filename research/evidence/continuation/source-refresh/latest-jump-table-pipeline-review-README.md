# Option B pipeline review checkpoint, 2026-10-04

Status: **Jev review escalated; batch g4 unrun; pipeline source and evidence committed at the user's explicit request**. The user authorized resuming after the first-slice escalation and subsequently requested committing and pushing all pending changes. Commit `2aadda6` saved the corrected recognizer and table reader. This checkpoint records the subsequent walker, config, independent checker, Java guard, and hold-out work. Publication preserves the unresolved review and terminal-rule issue; it does not clear them or authorize running g4. The baseline remains 5,454 saved functions; no successful production batch or coverage gain is claimed.

## Proposed implementation

The shared walker recognizes a bounded SLTIU/BEQ/SLL/table-load/JR profile, reads the ordered table words from one allocated non-executable ELF section, and accepts only targets within the seed limit and outside saved functions. It pins the dispatch, bound site, table address, count, ordered targets and table SHA-256. A reached ordinary bound, a fully reached bound-to-dispatch region, and absence of branch/switch entry into that region are required. Definitions supplying the table base must follow the bound. Targets already owned by saved functions remain rejected, including saved entries.

Schema 2 carries these pins. The independent checker performs its own forward symbolic replay from raw words; it imports neither the generator recognizer nor the walker. Schema 1 refuses switch candidates. The V5 Java guard verifies pinned words against both ELF and program memory, inserts missing COMPUTED_JUMP references before function-body discovery, preserves existing sources, and retains exact reference-delta checks. Outside references into case interiors are allowed only for the exact corresponding pinned table DATA word; those baseline records must remain unchanged.

Switch candidates may finish lexically in an in-span jump to a shared return. They still require a reached return or pinned tail, exact closed reachability and complete span accounting. The specification reviewer found that the exception also accepts a last case that jumps to itself, while another case returns. `terminal-loop-control.json` reproduces that acceptance in the walker, generator and independent checker; the Java predicate has the same relaxation but was not run on this synthetic case. The shared-return regression is the intended reason for the exception. Whether a looping last case qualifies under the glossary's terminal requirement remains an unresolved scope question; this is not review clearance.

## Checks and measured limits

- `full-tests.log`: **499 tests, OK, one skipped**, on the source hashes in `manifest.json`.
- `prospective-root-check.json`: independent checker passes on a prospective 41-candidate config, checking 7,948 reached instruction words and two incoming direct-call sites. Eleven candidates contain 18 pinned switch sites. This is config verification, not Java batch acceptance.
- `negative-controls.json`: four live Ghidra controls reject changed count, table hash, ordered targets, and missing dispatch pin for their intended reasons. Each starts from a byte-identical project copy and leaves the source project unchanged.
- The fifth live control deliberately fails after switch references have been added. `rollback-verified.json` is from reopening that project read-only after the failed headless script. Functions, instructions, data, references and initialized memory all match the saved pretransaction digests; function count remains 5,454. `VerifyCandidateRollback.java` and `live-controls.py` preserve the own-source verification procedure. The helper is the exact successful v4 driver, with its scratch paths and fresh-project requirement intact.
- `failed-controls.json` preserves two unusable rollback attempts. v2 stopped before mutation on a pre-existing table DATA reference. v3 checked too early, while Ghidra's enclosing transaction remained open, and reported `NEGATIVE_CONTROL_ROLLBACK_FAILED`. Neither is counted as rollback proof. The corrected check reopens the project only after script termination.
- `walker-measurement.json`: 181 clean seeds without switches and 16 clean switch seeds in the 408-seed scan. Seeds may overlap; these are not distinct functions or batch admissions. `residual-recognizer-measurement.json` covers only 15 remaining rejected computed-JR sites, 10 locally recognized; it must not be substituted for the original 29-site scan recorded in the first-slice bundle.

The skipped preguard-LUI control exposed a real path flaw: a prefix branch could skip the base definition but enter the bound. The recognizer and independent checker now require address definitions within the protected interval. Walker and forged-config regressions failed before the fix and pass after it; the latter rejects specifically because the instruction profile cannot be rederived. Earlier GPR0/JR0 and reserved-field controls are recorded in the first-slice bundle.

## Hold-out measurements

`holdout-summary.json` pools three deterministic seeds per population; the six complete result receipts are included. Saved functions are provisional structural ground truth, and only contiguous bodies are eligible. Runs overlap, so pooled totals are observations across runs, not distinct original functions.

| Population | Exact recovered / held out | Exact / candidates in held spans | Recall | Precision |
| --- | --- | --- | --- | --- |
| Supported local switch profile, six eligible saved functions; five held out per run | 12 / 15 | 12 / 12 | 80.0% | 100.0% |
| General contiguous functions without saved callers; 330 held out per run | 844 / 990 | 844 / 845 | 85.25% | 99.88% |

The historical pooled benchmark was 85.4% recall and 99.7% precision. It used a different saved-function population; these numbers do not establish an improvement attributable to switch support. The switch sample is small and excludes unsupported switch forms and split bodies. None of the measurements proves original boundaries or behavior.

## Review and disposition

The standards reviewer found no hard standards breach and suggested naming the long terminal-transfer predicate. The specification review found the preguard-definition defect described above; its fix has direct regressions. The last-case self-loop acceptance was reproduced separately after review and remains unresolved.

`jev-review.json` records a single final per-file review of the changed pipeline, with real suite, config, hold-out and live-negative evidence. It returned **escalate**, composite **0.7349772727272726**, whole-change `safe_to_apply` **0.15**. For the Java guard, test-gap confidence was **0.22**, correctness confidence **0.32**, and per-file composite **0.6695**. The default review threshold was **0.5**. Other files also had low confidence. The tool did not identify a concrete defect in its receipt; passing checks do not override this recorded escalation under the handoff policy.

The handoff says: “Read distributions, not only verdicts. `escalate` means stop and tell the user with the numbers.” The successful g4 batch, export reconciliation, new byte-accounting/reference/quality measurements, and final gate therefore remain undone. The user separately authorized committing and pushing this incomplete checkpoint. No unchanged Jev review was repeated to seek a different answer. All twelve capabilities were already used in the first-slice record; this checkpoint adds the meaningful pipeline review.

No original routine, game, generated guest or host runner, emulator, debugger, display or audio was run. No PR, merge or external message was performed. Projects and generated original-code artifacts remain ignored. This bundle contains own source, hashes, bounded address metadata and measurements.

To resume after the escalation is resolved: retain these receipts; resolve the terminal-exception review disposition; run g4 on a fresh byte-identical gp-g2 project copy with program decompiler options; drop only documented guard-rejected seeds; reconcile and measure the resulting export; save a `batch-g4-candidates` bundle; update the staged bar; obtain the final claim gate; then commit the final corrections and results. Re-review only a materially changed decision.
