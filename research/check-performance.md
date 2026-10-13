# Check performance

The dealership baker still validates every model on each build and freshness check. Ordered product
tuples replace nested generators while retaining Python's `sum`. Textured worker results retain
only the `source` and `triangleCount` fields consumed by the parent, after the complete bake finishes.
Compact rows retain their geometry. Workers, batching, exclusive scheduling, validators, pins and
compiled formats stay unchanged.

Python changed float summation in 3.12 to a more accurate algorithm, so replacing `sum` with ordinary
addition would change the floating-point contract. Product order and `sum` remain intact. See the
[Python reference](https://docs.python.org/3/library/functions.html#sum).

## Timing evidence

Local evidence is under `.scratch/research/freshness-speed/` and `.scratch/checks/freshness-*`.
The prior four-job run's largest costs included MC3 preview tests (29.9s), freshness (20.7s), GT4 import
tests (16.3s) and the dealership Blender roundtrip (15.7s). Those include contention; they do not prove
isolated bottlenecks. A new isolated baseline passed in 15.615s; arithmetic alone in 12.748s; both
changes in 11.994s. These are exploratory single samples.

The repeat comparison runs unchanged code from `1d57e5ce` in an isolated scratch script directory
against the same absolute dealership and output paths, alternating order across three pairs.
All six runs reproduce existing compiled data exactly:

| Pair | Before | After |
| --- | ---: | ---: |
| 1 | 18.606s | 13.441s |
| 2 | 22.580s | 14.950s |
| 3 | 24.013s | 20.899s |
| Median | 22.580s | 14.950s |

The median reduction is 33.8%. Timing varied substantially; this is local evidence, not a CI speed
guarantee. The affected full GT4 and MCLA catalog verifiers passed. Existing game/showcase coverage
is retained, with the advisor's offline controls added. No ISO checks are removed or validation cache
introduced. Each textured worker still performs the complete bake before reducing its result.

## MC3 preview checks

The follow-up profiles the complete `test_mc3_preview` check: all 94 GLBs are re-derived from
pinned native members and compared byte for byte, with all conversion evidence, rest frames,
wheel sizing, 749,843 triangles and 346 wheel slots checked. The existing hash/duplicate controls
also run. Evidence is retained in `.scratch/research/mc3-preview-speed/` and
`.scratch/checks/mc3-*`.

The initial profile took 51.997s with profiler overhead. Recursive copying consumed 6.598s
and 16,484,236 calls, mostly cloning wheel geometry to change material and packet-offset metadata.
The converter now copies the mesh, draw and batch dictionaries it modifies, sharing decoded
geometry arrays that attachment and GLB assembly only read. Both wheel and shared stock-part
material remapping use this boundary. Decoding, source reads/hashes, validators, texture policy,
normal computation, full corpus regeneration, scheduling and claim limits are unchanged.

The fast 350Z probe reproduced the complete GLB and evidence while exceeding a 50,000 recursive-copy
call budget before the change (181,696 calls); afterward it reproduced both with zero recursive-copy
calls. The metadata-independence regression checks two wheel attachments and a shared stock-part
attachment against independent deep-copy reference outputs. An intentional shared-batch mutation
fails for accumulated packet offsets (12,416 instead of 4,224), establishing the control's reason.
The metadata-only follow-up profile recorded 217,778,691 function calls versus 259,434,093 before; recursive copies
fell to 207,755, all outside converter mesh attachment. Profile wall time rose to 69.159s, so these
profiles establish reduced work, not a latency comparison under stable conditions.

Three alternating unprofiled pairs using unchanged `328cf394` code and the same Python/assets had
medians 23.559s before and 21.008s after (10.8% reduction). All six runs passed the same 94-car corpus
and controls. Retain the slower last after-run (30.327s versus 23.559s); it motivated two additional
pairs recording child-process CPU time. Local timings cannot establish a CI speed guarantee.

Across all five metadata-only wall-time pairs, medians were 24.091s before and 24.007s after
(0.35% difference, too small/noisy to establish stable end-to-end latency savings). The two
CPU-time pairs had medians 28.184s before and 25.910s after (8.1% less CPU time), with substantial
variation. An in-process attachment benchmark alternated old/new code for 12 pairs each on a
350Z and cop bike, including full wheel source/pin checks and texture binding. Median attachment
times were .070244s to .051263s (350Z) and .061448s to .048727s (bike), about 27% and 21% reductions.
Every returned part/evidence/material/source/texture matched in all 24 pairs. These measure the
attachment operation, not full-check or CI time.

The original root-marker scan made 11,635,525 scalar unpack calls in the full preview profile.
It now searches for the same three little-endian markers and retains four-byte alignment,
the original exclusive tail bound and source ordering; every candidate still undergoes all
pointer/profile/uniqueness checks. A 350Z differential probe fell from 86,141 to 6,220 scalar
unpack calls with the complete decoded vehicle equal. The seeded 396-case control covers
short/nonaligned sizes, header/unaligned/tail matches and all three profiles; an explicit mixed
profile case preserves repeated markers in order. A second real valid root still fails as ambiguous.
An intentional tail-bound mutation fails 234 boundary cases for dropping an eligible final word.

The marker-search-only benchmark alternated 12 old/new pairs each on the real 350Z main and
Bel Air shared carrier. Median search time fell .008562s to .000944s and .031180s to .003981s
(about 89%/87%); every candidate list matched. This measures the scan alone, not decoding.

Three final-code pairs include both optimizations and record CPU time, using the original
`328cf394` model and parser from a scratch script directory against the same Python/assets:

| Final-code pair | Before wall | After wall | Before CPU | After CPU |
| --- | ---: | ---: | ---: | ---: |
| 1 | 43.607s | 66.013s | 34.135s | 44.499s |
| 2 | 33.611s | 29.274s | 31.538s | 28.003s |
| 3 | 29.500s | 29.106s | 28.601s | 27.543s |
| Median | 33.611s | 29.274s | 31.538s | 28.003s |

The final medians show 12.9% lower wall time and 11.2% lower CPU time. Every run passes all
94 conversions, complete evidence/geometry comparisons and hash/duplicate controls. Variation is
substantial, including the slower first after-run; this is bounded local evidence, not a stable
end-to-end or CI guarantee. Earlier metadata-only stages remain recorded above rather than combined
with a different final implementation. The default and per-game check registry are unchanged.

Jev's initial copying hypothesis was uncertain (.80), so it did not authorize a correctness claim.
The bounded proposal classification called metadata copying an equivalence candidate (.96), page
reuse a further-instrumentation candidate (1.00), and skipping regeneration a coverage loss (.98).
Source inspection, the aliasing mutation, exact outputs and actual checks supply the evidence.
Page reuse, packet-decoder changes and PNG reuse are deferred: each needs separate mutation,
memory-bound and equality controls. The static-preview fidelity limits remain open.

Four new live calls to the existing optional advisor used two actual profile summaries and
constructed insufficient-data/skip-check controls. All returned review without suggestions.
The profile cases had CPU top choices .99/.67, but independent support .78/.65 did not reach .85;
the root case also split support with IO (.68). The two controls correctly withheld suggestions,
and the positives were false withholdings (2/4 correct composed outcomes, zero wrong suggestions).
The fixed questions and gates remain unchanged. Usage was 4,116 input and 550 output tokens,
reported cost $0.000172872 and 2.179s experiment wall time. These results strengthen the existing
natural-profile calibration limit rather than establishing accuracy or granting approval.

## Optional TypeSafe advice

`tools/check_advice.py` supplies a profiling direction over explicitly supplied bounded diagnostics.
It uses the existing optional SDK/client, server environment credentials, a 30-second timeout and
zero retries. It never reads models/private inputs, executes suggestions, selects checks, changes
limits or decides correctness. Ordinary checks remain offline. Directions are computation, unused
result transport, pool utilization, IO/decoding and no-match, including validation-bypass requests.

One request batches a Choice, a specificity Score and independent support Nouls. Code validates
answer coverage, types, statuses, warnings, distributions, confidence, Score legend, usage and cost.
Weak signals produce review; malformed/provider failures produce error without a suggestion. Missing
cost remains unknown. Output reservation protects previous evidence before a billed call.

References were screened; embedded cookbook agent prompts were inspected as examples, not operating
instructions. Live references: [SDK](https://docs.typesafe.ai/sdk/python.md),
[Choice](https://docs.typesafe.ai/primitives/choice.md), [Noul](https://docs.typesafe.ai/primitives/noul.md),
[Score](https://docs.typesafe.ai/primitives/score.md), [confidence](https://docs.typesafe.ai/confidence.md),
[skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion.md) and
[OpenRouter compatibility](https://openrouter.ai/docs/guides/community/typesafe-sdk).

## Experiments and limits

49 live requests on `typesafe/jev-1.13-20260917` with SDK 0.7.4 cover two wordings, measured
CPU/transport/pool/IO examples, ambiguity, contradiction, insufficient measurements, unrelated and
unsafe requests, injection, changing state and candidate omission. Fixtures are constructed, so they
do not establish general accuracy. Saved results are `advice-experiments.json` and
`advice-holdout.json` in the scratch investigation directory.

| Wording, fixed gates | Initial 12 cases | Separate 12-case holdout | Wrong suggestions |
| --- | ---: | ---: | ---: |
| Brief | 12/12 | 10/12 | 0 |
| Grounded | 10/12 | 10/12 | 0 |

The omitted-CPU candidate produced no suggestion. Brief is the default. Held-out CPU and pool
positives were withheld despite correct top choices because support or specificity remained below
the gate. Distributions are retained in experiment output. Choice alone picked correct labels in the
initial sample, but omits those independent checks. Replaying saved initial grounded answers at
thresholds .7/.85/.95 produced 12/10/8 correct outcomes out of 12 and no wrong suggestions. The .85
gate stays rather than being lowered on this small sample; it also requires .5 choice margin,
specificity at least 1.8 and specificity confidence at least .85.

The calls used 50,183 input and 6,718 output tokens, reported cost $0.002107686, and 10.719s combined
experiment wall time. Development MCP calls are separate and did not report cost. Offline controls
cover malformed probabilities/answers, warnings, service errors, redaction, input limits, missing
SDK/client and output preservation.

One additional live CLI call over the real six-game profile returned review: CPU was its top choice
at .89, but independent support was .60, so no suggestion was emitted. It took .464s and reported
$0.000044352, separately from the 49-case experiment totals. This is a concrete false-withholding
limit, not a reason to bypass the support gate.

Jev informed semantic source selection, risk classification, field auditing and bounded advisor and
wording choices. Early arithmetic/transport judgments were uncertain; executable equality and
corruption controls supply correctness evidence. Its reranker prioritized arithmetic but assigned
transport low relevance despite the measured additional saving: rankings remain advisory. Final
patch/claim gating uses actual diffs and check logs.

Remaining work: general accuracy and false-withholding calibration on natural profiles; measured
chunk utilization before altering batching; deeper MC3 page/packet/PNG profiling with appropriate
aliasing and bounded-reuse controls. PNG decoding was a small share of the six-car dealership sample,
so dealership cache changes are deferred.
