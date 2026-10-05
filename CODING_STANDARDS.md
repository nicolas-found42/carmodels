# Coding standards

Read during review. Mechanical rules (unused or undefined names, syntax errors) are enforced by
`tools/check.sh` through `ruff`, not repeated here.

## Verifiers and receipts

- A verifier derives its expected result from pinned sources and compares it with its committed
  receipt. It never trusts a value it did not recompute.
- Every verifier has controls: mutated copies of its inputs that must each make the derivation raise.
  A control counts only when its recorded reason names the intended failure, not an unrelated error.
- Re-running a verifier reproduces its receipt byte for byte. A run that changes a committed receipt
  is a finding.
- A new verifier uses `tools/verifier_common.py`, locates executable-derived inputs through
  `tools/static_inputs.py` (never a path constant), exits with one line when an input is missing,
  and gets a line in `tools/check.sh`.

## Claims

- Every receipt carries `claim_limits`, and every note says what its check does not establish.
  A static derivation is not execution evidence; wording stays conditional where only a capture
  could settle it.
- A name for a formula or structure (a reading of the arithmetic) is labelled as a reading.
- A claim moves from candidate to fact only through a check that can fail on unchanged inputs.

## Tools

- A new tool has a test beside it, and the test runs in `tools/check.sh`.
- Open items live in `research/README.md`; update the list when a change closes or opens one.
