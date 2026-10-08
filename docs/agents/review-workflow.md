# Patch review and evidence verification

Before implementing a task in a dirty checkout, capture the text files owned by that task.
Include expected new filenames, which are recorded as absent. Leave generated/binary assets
out of model input and verify them with executable checks. The paths are the review scope;
account for changes outside that scope separately.

```sh
python3 tools/review_payload.py snapshot --paths tools/build_dealership.py tools/new_tool.py --output .scratch/review-baseline.json
tools/check.sh --only test_build_dealership,dealership_freshness --evidence-dir .scratch/review-checks
python3 tools/review_payload.py build --baseline .scratch/review-baseline.json --request-file .scratch/request.txt --checks-dir .scratch/review-checks --claim "The listed checks passed." --output-dir .scratch/review-bundle
python3 tools/jev_mcp_call.py --batch .scratch/review-bundle/calls.json
python3 tools/review_payload.py status --bundle .scratch/review-bundle/bundle.json --implementer implementation-agent
```

Write the concrete task in the request file. Review inputs use raw unified diffs relative to
the task baseline, including new files and detected renames. Each patch-review call has at
most 24,000 diff characters by default; whole file diffs stay intact. Oversized files require
a deliberately narrower implementation or separately scoped review, never silent truncation.
Evidence verification uses separate calls with at most two claims each, the executed check
manifest and complete logs. Preparing a bundle does not call Jev. A verifier's approval does
not approve the patch. The request and claims are assertions to check, not evidence.

The status command exits 0 only when every review and claim is accepted. Missing, malformed,
operational-error or contradicted receipts block completion. A valid `review` or `escalate`
result remains `needs_independent_review`; retain its confidence/scores and resolve the
specific uncertainty through the human user or an independently assigned stronger reviewer.
Obtain authorization for agent delegation when the session requires it. The implementing
agent cannot resolve its own escalation by supplying its own reviewer identity.

An independent reviewer records this JSON after reviewing the complete bundle:

```json
{
  "bundle_sha256": "digest from bundle.json",
  "reviewer": "independent-reviewer",
  "verdict": "approve",
  "rationale": "The identified uncertainty and evidence that resolves it."
}
```

Pass the record with `status --resolution <file>`. A resolution cannot approve an operational
failure or contradicted claim. The record documents a decision; it does not authenticate a
person. Preserve the original receipts. Repair malformed inputs/provider errors explicitly;
do not rerun a valid judgment to seek different scores. Changes after review need a new
baseline/bundle. Keep check evidence and review output directories unique to avoid replacing
earlier runs.
