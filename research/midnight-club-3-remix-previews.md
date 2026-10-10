# Midnight Club 3 Remix: source-bound static previews

The supplied PS2 disc now produces 94 separate static GLB conversions, with native body geometry, stock external components, default rims and tires, decoded diffuse textures and alpha, and no ground-shadow planes: 749,843 triangles and 59,319,640 GLB bytes (the geometry-only conversion had 749,871 triangles and 46,827,416 bytes). Textures are documented in [the texture note](midnight-club-3-remix-textures.md). The final index reports zero omitted stock resources and zero omitted rest-pose components. The dealership uses independent editable copies. The source catalog still describes the original native DAT packages. This advances the earlier [preview-readiness investigation](midnight-club-3-remix-preview-readiness.md); that note records the state before this decoder existed.

## Diagnosis and executable evidence

The initial reproducible symptom was a native package entry with no preview geometry. An [independent replay of the captured baseline](evidence/midnight-club-3-remix/previews/independent-baseline-resolution.json) confirmed that exact 350Z entry lacked a ready descriptor. The retained `.scratch/mc3-preview/repro.py` harness now checks the actual compiled descriptor, not the presence of a catalog label. The original execution count is not a retained-evidence claim.

Ghidra MCP was used against the actual disc executable `SLUS_213.55`, SHA-256 `1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d`. The analyzed program has 15,789 functions. The [Ghidra receipts](evidence/midnight-club-3-remix/previews/ghidra/) retain real MCP tool arguments and responses. REA supplied artifact reconnaissance; its original native provider did not support this R5900 target. The working analysis used the local Ghidra MCP server and its MIPS analysis, with a matching native decompiler build.

The native resource reader validates serialized pointers, collection classes, counts and packet bounds. Three wrapper offset profiles cover the source corpus: 67 original-layout packages, 25 Remix packages, and two Mercedes packages. It selects the exact main PCK basename; an addon can precede that member in the native package.

PS2 VIF interpretation was researched against primary implementations with Firecrawl MCP, gh_grep and Context Awesome. The independently maintained [primary-source research note](midnight-club-3-remix-preview-research.md) records screened sources, limitations and semantic source-selection experiments. Those sources explain VIF; they do not independently validate MC3's retail wrapper. Game-specific packet and skeleton interpretation comes from the supplied executable and falsifiable native corpus checks.

The packet audit covers 805,205 UNPACK planes and found no unsupported skip cycles. Synthetic skip-cycle controls reject destination gaps rather than fabricating a dense array. Strip restarts use the native normal-X ADC bit established by the VU trace; runtime clipping and full native winding behavior remain outside the preview claim.

## Native assembly

Body components use their source skeleton rest positions. The shared `<vehicle>_g.pck` library supplies 42 stock pieces that are absent from the per-car package, across 17 cars. This includes body shells; the converter matches exact stock resource names and retains material ownership. The final corpus reports no unresolved stock resource names.

Wheel selection follows default `.carcfg` indices through `decal.pck` resource handles into `rim.ppf` and `tire.ppf`. A configuration index is not a PPF page number. Each selected source occurrence must match its extraction-index size and SHA-256, and the complete declared occurrence set must be present. The adapter used to read an embedded model retains an explicit mapping back to original PPF offsets and a separate adapter fingerprint.

The 346 physical wheel joints comprise 79 four-wheel cars and 15 two-wheel motorcycles. Ghidra's static sizing chain was checked independently against every joint and the executable's float tables; the largest independent arithmetic difference was `5.55e-17`. See [the independent composition audit](evidence/midnight-club-3-remix/previews/packets/wheel-scale-independent-composition.json). This establishes the implemented static arithmetic, not an emulator capture of runtime physics.

The Kawasaki police motorcycle is `COPBIKE`, native class value 10. An earlier development statement called it `COPCAR`; that statement was wrong. The all-vehicle audit exposed the missing class and retained the rejection control. Its two-wheel source skeleton and native kind byte select motorcycle assets, with the non-CHOPPER rim factor. CHOPPER has a separate native factor. See [the corrected case](evidence/midnight-club-3-remix/previews/wheels/sizing-copbike-correction.json).

The preview frame keeps native coordinates: front is negative Z, side is positive X. The dealership camera tests cover this separately from the established Ford Racing 2 and Redline frames. Working GLBs retain body part and wheel provenance in node extras.

## Materials and remaining limits

The static preview decodes diffuse images (PCK-embedded, shared `.tex` and rim/tire page textures) and binds them through the material objects; see [the texture note](midnight-club-3-remix-textures.md). Paint surfaces stay neutral gray and glass uses the recovered native tint. Preview normals are derived from faces. Original paint colour, native shader passes, damage, suspension, wheel spin, camber, tire deformation, animation and customization are not emulated.

Ghidra's `FUN_00240090` builds `Rz × Ry × Rx` from local XYZ Euler values. `FUN_0058e740` reads those source joint values and builds local frames; `FUN_0058e8e8` and `FUN_0023e308` compose parent and local frames. The converter now follows that order, including rotated parent frames. This restores five parts omitted by the initial single-axis implementation: the 1968 Corvette hood, the Remix 1963 Corvette hood, the Remix Yukon rear axle, and two Murcielago side vents. The [independent pose audit](evidence/midnight-club-3-remix/previews/packets/native-pose-composition-corpus.json) examined 2,194 assembled or previously omitted records across all 94 vehicles, found those five affected records, and identified rotated ancestors on both Corvette hoods. Six independent scalar matrix controls agreed within `1e-12`. Exact native floating-point rounding and runtime joint updates are not claimed.

## TypeSafe/Jev behavior and experiments

Jev helped select relevant primary sources, screen external payloads, compare conflicting API interpretations, verify native analysis claims, and review bounded patches. Exact source identities, pointers, hashes, arithmetic, file writes and preview readiness remain ordinary code.

The existing semantic catalog filter now receives the active source or dealership catalog. Choice selects a defined game variant; Noul judges whether the game and variant request is expressible; Score describes catalog coverage; a separate Choice identifies ordinary preview requirements or unsupported restrictions. Code validates distributions and failure statuses, applies thresholds, checks actual descriptor readiness, and rejects uncertain restrictions. Credentials stay on the server. A native DAT entry cannot become preview-ready from a model's judgment.

Six changed designs were exercised over a constructed 19-query sample, in two modes: 228 live requests, 516,356 input tokens, 45,169 output tokens, provider-reported cost `$0.021686952`, and 45.870 seconds total experiment wall time. The final stateful composition made 13/19 correct application decisions, with zero incorrect applications in that sample; conservative withholding accounts for the remaining valid-query failures. These are repeated development cases, not 228 independent labels or a general accuracy estimate. See [all experiment measurements](evidence/midnight-club-3-remix/previews/semantic/all-experiment-summary.json).

A broad experiment completion claim was contradicted by Jev and withdrawn. Its replacement reports literal retained test and experiment values. Valid review/escalation results require independent review; they are not erased by repeated calls seeking a different score. Original failures and judgments remain in the evidence directory.

## Final executed validation

The [final check manifest](evidence/midnight-club-3-remix/previews/final-native-frame-checks/results.json) records 62 passes, zero failures and zero skips. It includes exact native regeneration of all 94 conversions, loading all 94 GLBs through the actual dealership renderer, source hash and malformed-input controls, catalog freshness, and the registered checks for the other games. Blender 4.5.14 LTS imported and re-exported the 350Z, Chrysler 300C and Aprilia; the round-trip check also confirmed that a 10% length edit reaches the rebuilt catalog while all 188 canonical and working GLBs remain unchanged. See the [complete Blender command log](evidence/midnight-club-3-remix/previews/final-native-frame-checks/mc3_roundtrip.log).

The [preservation audit](evidence/midnight-club-3-remix/previews/preservation-final.json) checks 8,363 pinned source files, 891 other-game catalog and origin entries, and all 94 original MC3 packages and their initial provenance. Each of the 94 dealership GLBs matches its canonical conversion bytes but is an independent regular file, rather than a link. The compiled dealership has 985 entries. These checks, from before the texture decoder, establish static conversion, integration and editable-file behavior; texture, alpha and artifact handling are covered by the texture note, whose final run recorded 63 passes. Neither establishes runtime rendering fidelity.

## Reproduction

```sh
python3 tools/export_mc3_models.py
python3 tools/import_mc3_previews.py --refresh-unedited
python3 tools/build_model_catalog.py
python3 tools/build_dealership.py
tools/check.sh --evidence-dir <new-empty-evidence-directory>
python3 tools/serve_library.py --port 8081
```

The exporter refuses changed existing conversion output; a changed conversion is staged with `--output`, the previous corpus is preserved, and only then promoted. The importer refreshes only working files that still match their recorded import hash; edited copies are preserved. A repeated native catalog import retains converted previews and their original native package provenance.
