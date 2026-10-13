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

Remaining work: general accuracy and false-withholding calibration on natural profiles; isolated MC3
preview profiling; measured chunk utilization before altering batching. PNG decoding was a small
share of the six-car sample, so cache changes are deferred.
