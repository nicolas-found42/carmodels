# Why Jev escalated the MCLA review, and what fixed it

Date: 2026-10-12. Question: why did every `jev_review` call on the Midnight Club: Los Angeles change
([PR #38](https://github.com/nicolas-found42/carmodels/pull/38)) escalate, and what code changes raise the
judgments toward 0.95? Receipts: [`evidence/jev-review-escalations-2026-10-12/`](evidence/jev-review-escalations-2026-10-12/)
(experiment and round results with SHA-256 digests of the exact arguments; full arguments for round 3).

## Primary source: how `jev_review` decides

Read from the installed server, `@jkudish/jev-mcp` 0.13.0, `dist/server.js` and `dist/lib.js`:

- Each review asks five questions over the state `{request, diff | files, tests}` (`reviewQuestions`,
  server.js ~1189): four 0–2 scores (`correctness`, `spec_match`, `test_gap`, `blast_radius`), each with
  the model's own confidence, and `safe_to_apply`, a yes/no probability for "Is it safe for the host coding
  agent to apply this change without a human first?".
- `reviewAction` (lib.js ~290): `escalate` when the lowest rubric confidence or `safe_to_apply` is below
  `review_at` (0.5); `auto` only when `safe_to_apply` and every confidence reach `auto_accept` (0.8) and
  the weighted composite (0.4/0.3/0.15/0.15, gap and radius inverted) reaches 0.7.
- Per-file mode (`files: [{path, diff}]`, server.js ~1218): the same questions per file, each scoped
  "Judge only files[i], not the change as a whole", with every file visible in the state. Limits
  (lib.js ~208): 16 files, 200,000 characters in total, 50,000 per document.
- No rationale is returned, so causes have to be found by controlled comparison.

## Experiments

Same slice (`tools/xex2.py`), one variable changed at a time (receipts `experiments/A`–`F`):

| Run | Input | safe_to_apply | correctness (score/conf) | spec_match | Reading |
| --- | --- | ---: | --- | --- | --- |
| A | original bundle call (24,000-char slice, manifest JSON as `tests`) | 0.29 | 0.68 / 0.31 | 0.68 / 0.49 | reproduces the escalation (0.28 originally) |
| B | slice + its test file + its test output | 0.41 | 0.68 / 0.23 | 0.63 / 0.43 | test pairing alone barely helps |
| C | B in per-file mode | 0.44 | 1.10 / 0.17 | 0.62 / 0.08 | mode alone does not help a lone slice |
| D | request states why XEX decryption is needed | 0.51 | 1.55 / 0.31 | 0.97 / 0.83 | missing plan context depressed spec and correctness |
| E | real-disc observations in `tests` | 0.37 | 1.33 / 0.23 | 0.92 / 0.79 | evidence helps correctness |
| F | D + E | 0.54 | 1.80 / 0.70 | 1.02 / 0.82 | both together; spec stays "partial" for a lone file |
| G | the whole 16-file change in one per-file call, with D + E | 0.56–0.81 per file | ~1.8 / 0.6–0.8 | 1.45–1.77 | the whole change in view lifts spec_match on every file |

Causes, in order of effect:

1. **Slicing.** `tools/review_payload.py` cut the change into 24,000-character whole-diff calls. Each slice was
   judged against the whole request, so it read as a partial solution (`spec_match` ≈ 0.6–1.0).
2. **No plan context.** The request said "extract the car models"; nothing explained why an AES decryptor or an
   executable loader belongs to that, so those files looked like extra work.
3. **Weak test evidence.** `tests` carried the 78-row check manifest, not the output of the tests that exercise
   the change. Logs said only `OK`, without naming tests.
4. **Untested branches.** Measured with stdlib `trace`, most fail-closed rejection branches had no control
   (`xdvdfs` 89%, `xex2` 91%, `review_payload` 90% of executable lines), and two lines were unreachable.
5. **Counting in verification.** The "78 checks passed" claim held at 0.72 support because the verifier had to
   count manifest rows.

## Fixes (in code)

- `tools/review_payload.py`: one per-file call when the scope fits the server limits (grouped calls otherwise,
  or with `--grouped`); `tests` carries computed scope facts (added/modified/deleted files, same-directory
  importers), a computed check summary and the full logs of checks naming an in-scope file; verification
  evidence starts with the computed summary and carries only the logs of checks a claim names; status validates
  every per-file result, and an `auto` aggregate cannot hide an unresolved file. A 90,000-character per-call
  budget fails closed: round 2's ~105,000-character calls failed upstream with `max_tokens_exceeded`, while a
  ~99,000-character call had succeeded.
- `tools/line_coverage.py` (new, stdlib `trace`) and the `line_coverage` check: 100% of executable lines for the
  five MCLA modules and `review_payload.py`, gated at 95%.
- New controls for every rejection branch (XGD2 partition offset on a sparse image, multi-sector directories,
  resource size words, colliding names, missing disc members, destination rules, budget and receipt
  tampering). An unreachable parent-path fallback and an unreachable "input inside destination" check
  were removed. `extract_mcla_cars.derive` was split into smaller steps with streamed name harvesting; the
  real-disc `--check` still matches every byte.
- The new test modules run with `verbosity=2`, so check logs name every test.
- `docs/agents/review-workflow.md` documents per-file mode, the evidence rules, the budget and splitting by concern.

## Results

| Round | Scope | safe_to_apply (per file) | Lowest rubric confidence | Claims |
| --- | --- | --- | --- | --- |
| 0 (original) | 5 grouped slices | 0.24–0.47 | 0.00 | 0.70 support (review) |
| 1 | 16 files per-file + 2 tooling files | 0.52–0.88 | 0.00 (blast radius) | 0.72, 0.52 |
| 2 | tooling only (MCLA and both verify calls failed: `max_tokens_exceeded`) | 0.60–0.85 | 0.00 | operational error |
| 3 | 4 bundles split by concern | 0.59–0.89 | 0.00–0.37 | **0.98–1.00, all `auto`** |

Every verification claim now passes at ≥ 0.98. Correctness reaches 1.77–1.95 at 0.64–0.93 confidence. No review
reaches `auto`, and `safe_to_apply` stays below 0.95.

## Ceiling

A one-word typo fix in a README, through the same tool, scores `safe_to_apply` 0.96–0.97 with every rubric
at confidence 1.0 (receipts `experiments/H`, `I`). So 0.95 sits near this judge's ceiling for trivially safe
changes. For this change the remaining holds are judgments, not defects found:

- `review_payload.py` is the repo's shared review gate. Jev rates its blast radius 1.92 at confidence 0.88,
  which is accurate.
- New decryptor and archive-reader modules get blast-radius scores between "tiny" and "moderate" at
  confidence ≤ 0.43, despite computed import facts.
- After splitting by concern (needed to stay under the provider's input limit), the readers bundle's
  `spec_match` fell to 1.41–1.57 even though the request names the sibling bundles.

Further reruns with reworded inputs would be score-seeking, which `docs/agents/review-workflow.md` rules out.
The remaining escalations need the independent review that workflow defines.

## Verifying this note

`jev_verify` checked seven claims against a digest of the receipts (`verify-note-1.json`, `verify-note-2.json`)
and two again against round-3-only evidence (`verify-note-3.json`). Five verified. One stands contradicted:
"per-file `safe_to_apply` ranged from 0.59 to 0.89 with no file `auto`" (contradicts 0.87). Recomputed directly from the
round-3 receipts, the extremes are exactly 0.59 (`review_payload.py`, escalate) and 0.89 (`CONTRIBUTING.md`, escalate),
and the actions are only `escalate` and `review`. The claim is kept on that mechanical check, and the
contradiction is recorded as a judge error, not resolved by rerunning.

## Not established

- Calibration of Jev's confidences against real defect rates; the ceiling probe is one trivial change.
- The provider's exact input limit; 90,000 characters is a margin under one observed success and two failures.
- Whether a stronger reviewer would agree with any of these scores.
