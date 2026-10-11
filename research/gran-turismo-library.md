# Gran Turismo model library

This note records the initial body/texture import. The subsequent
[native wheel recovery](gran-turismo-wheels.md) supersedes its missing-wheel
limitations and generated GLB byte totals. Body polygon counts and original
import evidence below remain historical observations.

This task adds native GT1 car conversions to the source library and imports independent editable copies into the dealership. Source codes, day/night variants and arcade ordinals remain separate; retail names and specifications have not been inferred.

## Library outputs and reproduction

The source catalog contains 728 retained GT archive pairs: 344 simulation day variants, 344 simulation night variants and 40 arcade variants. Each GLB contains three body LOD scenes, totaling 2,184 LODs and 383,027 triangles across all LODs; source GLBs total 132,852,040 bytes. These are asset variants, including possible logo/UI families, not 728 distinct drivable vehicles.

`dealership/public/gran-turismo/index.json` pins every GLB to its native CAR/CTEX hashes. `dealership/public/models.json` combines them with the 35 existing Ford Racing 2 source models. The editable dealership contains 763 entries and independent regular model copies. Importing again adds zero and preserves existing edits. The initial 35 FR2 catalog/origin entries and all pre-task FR2 source/working model hashes remain unchanged.

Reproduction from the repository root:

```sh
python3 tools/export_gt_models.py
python3 tools/build_model_catalog.py
python3 tools/import_gt_dealership.py
python3 tools/build_dealership.py
python3 tools/export_gt_models.py --check
python3 tools/build_dealership.py --check
python3 tools/serve_library.py --port 8081
```

The local server serves `/dealership.html` and `/recovered.html`. Source startup filters accept `?game=gran-turismo&variant=night`; an optional `car` parameter names a complete catalog ID. All model downloads preserve alternative LOD scenes. The dealership displays only the working GLB's default scene, preserving embedded textures and native vertex colours. Unknown GT retail names/performance remain unassigned. Selected-car descriptions explicitly disclose missing wheel assembly and static conversion limits.

## Validation

Full export freshness verification regenerated all 729 indexed output files and required exact byte equality. A separate reviewer parser, without importing the production parser, independently walked all 728 raw CAR files to exact EOF and matched every exported triangle POSITION/index relationship and source LOD offsets. It covered 383,027 triangles across 2,184 LODs, and deliberately excludes normals, textures and original game rendering. A pinned community reference comparison separately matched the ordinary 720 models' 2,160 LODs, positions, vertex/normal ownership, UV bytes and CLUT selectors. Eight native Gouraud models are excluded from that community comparison because its parsers skip actual face groups; independent synthetic packet tests and complete native EOF/geometry audits cover those groups.

The independent editable-copy audit checked all 728 GT copies for equal bytes, distinct source inodes, one link and sourceCode correspondence. Preservation and semantic audits are retained under `.scratch/gt-library/`, alongside check manifests and complete command logs. An initial full run caught a real registry-count failure after adding a sixth Node check; the intended missing-runtime/failed-command fixtures are separate nested controls. The registry expectation was corrected and the failed run retained. The final `tools/check.sh` run (`.scratch/gt-library/full-checks-2/results.json`) completed with exit 0: all 39 checks passed, with no skips. This includes the real Blender 4.5.14 import/edit/export round trip, which preserved all 798 source and working model files. A focused final dealership UI check also passed after the entry-count wording was adjusted. The final browser pass found and fixed startup car IDs being assigned before native select options existed; focused source checks cover this subsequent change, including requested non-first IDs and missing-ID fallback. Browser checks verified representative source and dealership previews through `127.0.0.1:8081`, truthful absent specifications and visible wheel limitations. Live semantic requests selected GT night variants in the dealership and all 40 GT arcade variants in the source library; LOD0/1/2 remained available. A previously open localhost-origin tab retained a stale catalog; the verified loopback tabs use a fresh origin, and the server and source catalog fetch now request no-store caching. Existing localhost-tab cache recovery is not claimed.

## Semantic filters

`tools/library_filter.py` interprets natural language over available game and source-variant filters. One bounded request batches a Choice over existing filters plus `no_match`, a Noul for whether the entire request is supported, and a Score for coverage. Code validates response coverage, status, warnings, distributions, confidence, rubric and finite values, then applies conservative thresholds. Review/error results leave the selected filters unchanged. Unknown vehicle attributes cannot become supported filters.

The optional endpoint lives in `tools/serve_library.py`, bound to loopback. Credentials and SDK requests stay server-side. The UI's **Interpret search** button sends only the entered query and uses catalog game/variant metadata; meshes, textures and other asset bytes are not sent. Exact game, variant and text controls work without the SDK or a provider key.

Current live documentation read: TypeSafe documentation index, Python SDK and question/answer references, confidence guide and function-calling cookbook; OpenRouter's TypeSafe compatibility guide. The Python SDK version available in the task virtual environment is 0.7.4. Requests use `https://openrouter.ai/api`, explicit `OPENROUTER_API_KEY` and `typesafe/jev-1.13`. The fetched SDK quickstart received a Jev screening `review` signal (injection probability .27); inspection found ordinary SDK installation/credential examples, treated as reference data rather than authorization or agent instructions.

## Experiments

Retained raw responses, fixtures, composition and usage are under `.scratch/gt-library/`. Sixteen hand-labeled queries include supported games/variants, synonyms, unavailable color/make/performance filters, conflicting selections, negation, unrelated requests and an instruction-like deletion request. Initial brief questions chose the correct top label for 14/16; initial grounded questions for 13/16. Both accepted four filters and accepted zero incorrect filters. Ambiguous/unsupported winners stayed in review.

Explicit game aliases and clarification that “cars/models” and “both games” are ordinary library requests improved the revised grounded top labels to 16/16. The default composition still accepted four requests with zero incorrect acceptances. Threshold sweeps reused the original responses: .6/.7/.8 accepted five, .85 accepted four, .9 accepted two; none accepted an incorrect result in this small set. The default remains .85 rather than assuming the sample proves a lower threshold safe.

The three batches made 144 primitive judgments, used 24,882 input and 5,981 output tokens and cost $0.001045044 according to provider usage. Their measured end-to-end latencies were .381, .243 and .310 seconds. These costs exclude development MCP screens/reviews and later browser/API requests. This is a small fixture experiment, not a general accuracy or latency guarantee.

## Remaining interpretation limits

The native body/texture conversion is a static reconstruction. Native wheel placement metadata does not by itself establish a complete wheel mesh. Real game rendering, animation, LOD selection, retail display names and specifications require additional evidence. Library labels must describe the asset identity and conversion limits rather than imply these are complete game-render replicas.
