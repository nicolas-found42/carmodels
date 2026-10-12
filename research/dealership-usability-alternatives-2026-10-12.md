# Dealership usability alternatives, 2026-10-12

This bounded research supports repairing the demonstrated search and filter friction with native controls and small local functions. It does not establish broad usability preferences, adoption, typo tolerance, legal compliance, or accessibility conformance. The persona is a novice who types ordinary words, presses Enter, and expects available cars to remain discoverable. That persona generates probes; observed behavior and the catalog establish failures.

## Local comparison and decision

Experiment identity: HEAD `6c9cc06a068f2d276bd41820f15eb9922af76e7a`, compiled catalog SHA-256 `17b6f78d9a797b51458ca95fa0b46480f18a05660a991cc02d2573798cc0601b`, local Node `v26.9.0`. The [experiment receipt](evidence/dealership-teardown-2026-10-12/research-experiment.json) retains the exact command, control, output and limits. It read existing files and added no project dependency.

**RE-01 / RD-01 — name and year search.** The existing interface promises “Search name or year”; its implementation searches one contiguous substring of `name + code + year`. A real Node consumer read the current compiled dealership catalog and compared that predicate with case-folded, whitespace-separated tokens, requiring every token to occur in the same searchable record. This was a function experiment over real data, not a browser run or the final implementation.

| Query | Current substring | All-token prototype |
| --- | ---: | ---: |
| `mustang 1968` | 0 | 2 |
| `1968 mustang` | 0 | 2 |
| `MUSTANG   1968` | 0 | 2 |
| `mustang 1967` | 0 | 0 |
| `xxxxxxxx 1968` | 0 | 0 |
| `mustang` | 15 | 15 |
| Empty | 1,715 | 1,715 |

The same consumer counted 730 Gran Turismo 4 records, with zero `night` variants. These are measured catalog facts. They do not prove every empty filter combination is a defect. Keeping a genuinely restrictive name query or body-style intersection empty is useful; automatically erasing all constraints would hide the user's intent. See [the local output receipt](evidence/dealership-teardown-2026-10-12/research-local-probe.json).

The token prototype repairs the representative queries while preserving the two negative cases and single-word/empty controls. It remains exact substring matching: misspellings, missing spaces, punctuation changes, and aliases require separate decisions and tests. Tokens may match different fields, and quoted phrases gain no special syntax. Acceptance: both Mustang word orders and repeated spaces return the two known cars; impossible name/year and nonsense remain empty; existing single-word and empty behavior survives. Jev chose the token option with probability 0.98 and no contradicted requirements; its suggestion that Fuse meets the positive cases is untested model judgment. See [RD-01](evidence/dealership-teardown-2026-10-12/research-decide-search.json).

## Candidate comparison

| Candidate | Mechanism and proposed path | Burden / contrary evidence | Disposition |
| --- | --- | --- | --- |
| Retain current search and document literal matching | No code/dependency change | Leaves measured name-plus-year failures; narrow interpretation of “or” does not help a novice combine fields | Reject for this demonstrated workflow |
| Small local all-token predicate | Existing browser JavaScript over current catalog | Exact matching remains; no typo ranking, aliases or phrase syntax | Recommend, subject to final regression and browser verification |
| Fuse.js | Vendored local full ESM build, fuzzy per-term search and ranking | Threshold tuning, precision benchmark, artifact/license pin and clean accountless operation still needed; no measured gain over token prototype | Research candidate only; keep out of implementation |

Fuse's current [token-search documentation](https://www.fusejs.io/token-search.html) describes fuzzy matching per query term, IDF weighting, and the full-build requirement. It calls the default threshold 0.6 permissive. This could help actual misspellings, but it can also blur a requested numeric year; that is a risk hypothesis requiring negative-query measurements. Its [fuzzy-search guide](https://www.fusejs.io/fuzzy-search.html) explains that default location penalties can exclude matches late in a field; `ignoreLocation` changes that behavior. Neither fact proves a dealership benefit.

The fetched [main package manifest](https://raw.githubusercontent.com/krisk/Fuse/main/package.json) reports **7.6.0-beta.0 / Apache-2.0**, and the [main LICENSE](https://raw.githubusercontent.com/krisk/Fuse/main/LICENSE) agrees. Do not reuse a remembered MIT license for another version. The [installation guide](https://www.fusejs.io/getting-started.html) documents ESM and CDN paths and estimates an 8.6 kB gzip full build; that is an upstream estimate, not a measured project footprint. CDN runtime would add a network dependency to an offline viewer. The inspected manifest shows development tooling and no runtime dependency field; complete source, lifecycle-script and transitive installation review were not performed. No Fuse package was installed or executed. Accountless, credentialless operation and license compatibility are therefore **not established for an integration**, and the candidate is not approved by this note. Reconsider only after a pinned artifact/source review, isolated no-credential execution, and precision/recall comparison on known positive, typo, numeric-year and nonsense queries.

## Native control improvements

**RD-02 — contextual variants.** Derive available source variants from catalog rows for the selected game, including the existing special arcade rule. On a game change, preserve a still-valid variant, clear an impossible one, and explain the reset in visible status. This is a proposed product behavior justified by the measured zero GT4 night records and the parent's live game-switch reproduction. It is not mandated by a web standard. Test GT night → GT4, all-games switching, preserved valid variants, and genuine empty name/body filters. A game with only one available variant may still expose the selector for consistency; disable it clearly rather than implying choice.

**RD-03 — semantic Enter.** Use a native form with an explicit submit button and one submission handler shared by click and keyboard activation. The [HTML Standard's implicit-submission section](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#implicit-submission) specifies default-button activation when a user agent supports implicit submission, including Enter on some platforms. This is conditional documentation support, not proof that the project's browser path works. Assert one request on Enter/click, no accidental page navigation, stale-response preservation, and failure recovery against the final implementation.

**RD-04 — constrained-height discoverability.** Put optional advanced filters in a clearly named native `details` disclosure and allow the sidebar/filter area to scroll without starving the car list. Keep name, game, current result count and reset discoverable. [MDN's details documentation](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details) describes summary-only collapsed presentation and Space activation; the [W3C disclosure pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) describes Enter/Space activation for its button pattern. These sources explain a mechanism, not a proven layout fix. Closing optional controls may hide useful capabilities; test opening them at 900×500 and a narrow viewport, keyboard focus, usable list height, and visible recovery.

**RD-05 — visible routing explanation.** Show concise text beside the semantic submission control explaining that exact game/variant phrases stay local and other wording can go through the configured TypeSafe/OpenRouter provider. Associate it with the field using `aria-describedby`, and retain deterministic selectors as an obvious local alternative. The [W3C forms tutorial](https://www.w3.org/WAI/tutorials/forms/instructions/) supports visible instructions associated with controls and explains why disappearing placeholders cannot substitute for labels. The [privacy principles](https://www.w3.org/TR/privacy-principles/#transparency) call for contextual data-use explanation and state that transparency alone is insufficient for consent. This supports disclosure placement, not a legal conclusion or an additional authorization grant. Do not imply that text always stays offline, that all semantic queries leave the machine, or that a hover tooltip reaches every user.

Jev selected the combined native approach with probability 1 and no contradicted requirements. That result ranks the stated alternatives; it does not establish actual usability or implementation success. See [RD-02–05 judgment](evidence/dealership-teardown-2026-10-12/research-decide-native.json).

## Evidence limits and research gaps

- Four fetched-content screens returned `pass`; injection probabilities were 0.07, 0.04, 0.03 and 0.06. Sources remained evidence rather than operating instructions. Raw fetched results and distributions are in `research-sources-1.json` through `research-sources-4.json` and matching `research-screen-*.json` under the [teardown evidence directory](evidence/dealership-teardown-2026-10-12/).
- The legacy Fuse options URL returned HTTP 404. Search located current first-party guides. Search results included unrelated and community material; consequential technical claims use the linked primary sources. No competitor installation, issue-history audit, community frequency estimate, mobile device run, or assistive-technology session was performed in this bounded research.
- One overlarge Jev verification call failed with OpenRouter `400 (max_tokens_exceeded)`; [the failure is retained](evidence/dealership-teardown-2026-10-12/research-verify-error.json). The corrected bounded call verified license/version, permissive fuzzy matching and privacy claims with support 1. Its compound HTML claim received support 0.71, confidence 0.56 and `review`: [raw result](evidence/dealership-teardown-2026-10-12/research-verify.json). Independent review or final live Enter verification must resolve that concern; this note does not report Jev-reviewed completion.
- Product changes, final browser measurements, full repository checks and accepted-finding dispositions are owned by the main teardown. This note recommends alternatives; it does not claim they were implemented or that all required project work is complete.
