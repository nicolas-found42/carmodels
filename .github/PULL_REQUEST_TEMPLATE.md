<!--
Fill every section. Scale the detail to the change: a one-line verifier tweak does not need a
table. If something could not be verified, say so in Evidence rather than leaving it implied.
-->

## Summary

<!--
The problem and why it matters, the resulting behavior, and a link to the issue/spec (`Closes #N`).
Then the smallest view that makes the important change clear — a `diff` block for code or
artifact-tree changes, a table or diagram when structure or behavior is what matters.
Close with relevant tradeoffs, limitations, or migration steps.
-->

## Evidence

<!--
Match each important behavior claim to what you actually ran. This repo's idiom is standalone
verifiers — `python3 tools/verify_*.py`, `python3 tools/validate_*.py`, a Blender/PINE run — plus
sha256 pins and receipts under `research/evidence/`. Name the command, the conditions, and the
observed result. Keep failed checks visible.
-->

- **<behavior checked>**: <command or scenario, with conditions>
  - **Before:** <observed result>
  - **After:** <observed result>

<!--
If anything is unverified, state what remains unverified, why evidence could not be obtained,
and the check that is still needed. An after-only result must be labelled as such.
-->

## Merge Danger

**Door:** <!-- one-way or two-way, with the reason. Reverting a commit cannot un-publish a corpus. -->

**Blast Radius:** <!-- Affected consumers: the ford-racing-2/recovered/ corpus and its manifests, dealership/public
GLBs, the per-game extraction folders, downstream research notes. What could go wrong if this
merges and is wrong. Keep a small reversible change's risk statement brief. -->
