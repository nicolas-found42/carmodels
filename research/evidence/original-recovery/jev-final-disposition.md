# Final Jev review disposition

The original call and complete result are retained in [jev/final-gate.json](jev/final-gate.json). The evidence snapshot submitted is preserved separately in [jev/final-gate-args.json](jev/final-gate-args.json). No second call was made to seek automatic acceptance.

The gate **escalated** overall: review composite 0.7305, minimum safe-to-apply 0.39, with low rubric confidence and test-gap/blast-radius scores. Claim verification returned nine verified, zero contradicted and one unsupported; three claim actions require review. This is an advisory judgment outcome, not proof of automatic acceptance, and no final report describes it as passed.

Manual review inspected the exact generated artifacts, bounded exporter behavior and unresolved claims:

- The independent file validator reads actual binary chunks and attributes without importing exporter code. It verifies all 35 GLBs and their hashes, index bounds, stored extrema, normalized normals, embedded image CRCs, references and scene hierarchies. These checks do not settle original draw fidelity.
- The browser receipt contains successful tree-zero status for all 35 car selections with empty displayed errors. Gran Torino's five trees, an individual record and texture/wireframe controls were exercised. Captured console errors were empty. This is bounded browser coverage, not a claim of every possible interaction.
- Export tools write only derived files below this project by default. Archive/manifest and source hashes are retained. The existing procedural gallery remains available, with the new original-data inspector and explicit limits documented separately. Original input assets were not intentionally edited.
- Claim seven (independent records plus five trees with state selection unresolved) is directly inspectable in the exporter, generated index and six-scene GLB checks. No state-selection completeness claim is made.
- Claim eight (PTG/mip/glass/GS work left unresolved) is stated explicitly in the report, README, inspector and GLB extras. Those limits remain required work for faithful cars.
- Claim ten (24 texture tests passed) received `unsupported` at confidence 0.78. The submitted `tests` field contains the real initial 24-test log, but it was not also duplicated into the `evidence` array. The assertion is supported by [texture-tests-initial-24.log](texture-tests-initial-24.log), copied from the immutable submitted call snapshot. A follow-up run passed 25 tests, preserved in [texture-tests.log](texture-tests.log); the shared source project gained a test during the session. These counts describe separate runs, not model-generated estimates.

The source/byte/PNG/GLB/browser checks justify delivering the research and **experimental** artifacts within the user's requested scope. They do not justify declaring faithful in-game rendering or all reverse-engineering work complete. The gate's escalated state and all control errors remain preserved for future review.
