# Ford Racing 2 car mip recovery

## Result

The 35 archive-matched car containers store **94 extra image levels** after their 700 level-zero textures. This pass exported every mip plane verbatim and decoded all 94 into RGBA PNGs using the existing loader trace and measured static GS address mapping. The binary planes total **75,520 bytes**. The outputs are static source-data reconstructions; they do not establish which level the game selected or what a PS2 displayed during play.

The complete per-level inventory is [mip-index.json](evidence/mip-continuation/mip-index.json). It includes the car and archive paths, model hashes, source byte offsets and sizes, mip-record offsets and words, logical dimensions, CLUT references, upload profile, raw-plane hash, PNG hash, decoder name, and stored-alpha policy. Raw source planes and decoded PNGs are under `research/evidence/mip-continuation/levels/<car>/`. PNGs keep serialized palette/texel alpha unchanged; the existing display-alpha convention is not applied to these files.

## Corpus and decoder profiles

The archive/manifest-bound inventory covers these measured mip routes:

| Route | Logical mip sizes and counts | Total |
|---|---:|---:|
| Format 1, direct RGBA | 16×16: 4; 32×32: 4 | 8 |
| Format 3, direct T8 indices and model CLUT | 16×16: 35; 32×32: 35 | 70 |
| Format 3, packed CT32 upload sampled as T8 | 16×16: 4; 32×32: 4 | 8 |
| Format 4, packed CT16 upload sampled as T4 | 32×16: 4; 64×32: 4 | 8 |
| **Total** |  | **94** |

Format 1 preserves the source RGBA bytes. Direct format 3 preserves the serialized linear index order before CLUT lookup. Packed format 3 uses the loader-selected CT32 upload and PSMT8 address mapping. Packed format 4 uses the CT16 upload and PSMT4 mapping, with the DBW and TBW values read from that level's own 16-byte mip record. Every indexed decode uses the same model palette block referenced by the texture descriptor. The parser-derived dimensions halve per level, and the measured source plane size equals the static upload byte count for every exported level.

The wider 56-model audit found a conditional address-set gap for two packed 8×8 indexed mip profiles under normalized equal upload/sample bases. Neither profile appears in the car subset's 94 mip records. All 16 packed car mips match a separate per-pixel recomputation from the pinned PCSX2 page, block and column tables using each mip's serialized widths. That establishes the static byte/nibble permutation for these profiles under the audited assumptions. It does not prove the actual runtime base allocation or hardware behavior.

## Source evidence

The source identity is PAL `SLES-51705`, corpus ID `e69a2afbd6db606d166e40bae32c436691e134722ad153200859961a5f517dab`. The exporter binds each car model to both its local manifest hash and the `FILES.HDR`/`FILES.DAT` archive output. It pins hashes for `ps2_container.py`, `ps2_texture_indices.py`, `ps2_sections.py`, `format_contracts.py`, and `corpus_binding.py` in the generated index.

Primary loader evidence is the existing static trace of `FUN_0022ba30`, which reads the mip count and descriptor records, lays out the image planes, halves dimensions per level, and fills the runtime source-pointer slot. `FUN_00222358` follows those records for uploads, uses the static format choice and consumes the per-level TBW/DBW fields. The all-56 archive-bound mip upload audit checks instruction bytes against the executable and finds equal source-plane and predicted transfer byte totals. The 16 packed car mappings were also checked against the pinned PCSX2 `GSTables.cpp` revision `81526d4dc7cc70e4ae75abb35a789417456c6d43`, SHA-256 `a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8`. These are source and table calculations, not an execution of the game's uploader.

Reusable primary evidence lives in the sibling reverse-engineering project:

- `notes/evidence/fr2-texture-upload-audit/mip-upload-static-audit/README.md` — uploader byte-count and loader-field trace.
- `notes/evidence/fr2-texture-mip-field-audit/README.md` and `conditional-address-intersections.json` — mip record field measurements and the conditional small-mip address gap.
- `notes/evidence/fr2-gs-mip-sampler-audit/README.md` — public CPU backend sampler discrepancy, explicitly not a Ford Racing 2 runtime or hardware observation.
- `tools/ps2_container.py` and `tools/ps2_texture_indices.py` — archive parser and level-zero source/GS mapping implementation reused as the mip-decoder reference.

## Validation and reproduction

[validation.json](evidence/mip-continuation/validation.json) passes all 35 cars, 94 mip records, 75,520 raw bytes and 94 decoded PNGs. It independently checks archive and manifest identity, source offsets and plane bytes, mip record words, PNG chunk CRCs, decompression and dimensions, palette-decoded pixels, output hashes, and the packed pixel address order against the pinned PCSX2 tables. [negative-controls.json](evidence/mip-continuation/negative-controls.json) records a passing positive corpus plus three rejected mutations: an altered raw-plane hash, a corrupted PNG payload, and a negative source offset.

From the carmodels directory:

```sh
python3 tools/recover_car_mips.py
python3 tools/validate_car_mips.py
python3 tools/test_car_mips.py
```

The final validation receipt is produced by the validator. The mutation checks use temporary copies and do not modify the generated evidence.

## Jev and TypeSafe record

Jev was used to choose the bounded decode policy, retrieve and rank source evidence, classify all eight measured profiles, estimate open runtime claims, compare the small-mip audit to the car subset, verify source/table claims, and review the change. Results are advisory; source bytes and deterministic checks decide exact counts and mapping.

The experiment choice selected decoding supported profiles over raw-only export at 0.79 versus 0.21, with no contradicted requirements. Eight profile classifications were automatic with the expected direct-format1, direct-indexed, packed-CT32/T8, and packed-CT16/T4 routes. Retrieval found only partial candidate coverage (`exists=0.68`); full-evidence reranking ranked the source-field audit 0.88, source parser 0.88, independent validation 0.86, upload audit 0.83, address-gap evidence 0.79, and the public sampler experiment 0.44.

The first broad verifier did not support the PNG mapping claim (support 0.37, contradict 0.51, confidence 0.26) when given summary evidence. After adding the source trace and exact table comparison, Jev verified the 16-packed-level address-order claim at 0.96 confidence and the 94-level static route claim at 0.85. It also contradicted one profile-list claim at 0.81 even though the deterministic profile inventory was supplied; that evaluator result remains retained as a known disagreement. A contextual Noul remained uncertain on full static profile coverage (0.75–0.81), while assigning low probabilities (0.05–0.06) to original-hardware equivalence.

The final patch gate escalated (composite 0.765, safe-to-apply 0.26; three claims verified, one contradicted and four marked for review). The contradicted claim was mistakenly included as a positive completion claim even though it deliberately asserted that the PNGs prove runtime selection and PS2 output; evidence correctly contradicted it. The gate also returned low confidence on several claims despite the supplied validation receipt. I preserve that outcome and do not describe the gate as passed. The earlier gate receipt also escalated. Both full responses are in [jev-receipts.json](evidence/mip-continuation/jev-receipts.json); exact source, table and byte checks remain the basis for this slice's recovery result.

## Remaining fidelity questions

There is no raw-plane or static pixel-address blocker left among these 94 car mips. The following runtime questions remain open:

- Which texture levels the running game actually selects for each draw, and the dynamic VRAM base addresses after allocation.
- How draw-time sampler state, filtering, CLUT setup, alpha tests and blending affect their displayed colors.
- Whether the original PAL executable's behavior agrees with the table model on a real PS2 or a validated emulator capture.

The existing public CPU sampler test returned the TEX0 base plane in authored fixed-LOD cases and disagreed with the manual's specified mip choice, but it bypasses Ford Racing 2's uploader and does not show the game's output. The 94 PNGs therefore close the original stored car-mip extraction and static decoding work; they do not close full rendered texture fidelity.
