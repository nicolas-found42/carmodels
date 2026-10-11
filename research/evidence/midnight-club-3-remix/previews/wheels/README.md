# Native shared wheel probe

The selected rim and tire models are in the recovered `resources/vehicle/rim.ppf` and
`tire.ppf`, indexed through the shared `decal.pck` library. The source customization
index is not the PPF page number. Native library handles resolve the earlier name
probe's Zonda ambiguity without choosing a visually similar model.

`tools/mc3_wheels.py` exposes `read_default_wheels(cars_root, vehicle_id, bike=...)`.
The caller supplies the native vehicle class. The output retains the default
configuration, all duplicate-source hashes, selected library rows, packed handles,
PPF page records, native model header/base, material indices and unscaled meshes.
It applies no placement, wheel rotation, sizing or tire deformation.

## Native selection

Ghidra MCP receipts in the sibling `ghidra` folder pin these static observations:

- `wheels-native-rim-tire-choice.json`, `FUN_002f7310`: rim model index selects the
  library collection at root + 0x28. A car tire's profile selects one of eight
  collections through root + 0x2c; tire model index selects within that collection.
  The bike branch uses root + 0x30 and BikeTireMdlIdx.
- `wheels-scale-and-selection.json`, `FUN_002c66c8`: configuration bytes +0x1c,
  +0x1d and +0x1e populate native rim, tire and bike-tire indices. Profile bytes
  +0x18/+0x19 populate the two profile selections.
- `wheels-library-record-schema.json`, `FUN_003b2d20`: shared model handles preserve
  their packed source selector at +12 while runtime pointers are reset/relocated.
- `wheels-native-resource-select.json` and `wheels-ppf-record-relocation.json`:
  archive class comes from the packed selector's upper bits; the page is its low
  23 bits. PPF sector offset is `(word & 0x7ffff) << 11`; length is
  `(word >> 20) << 11`.
- `wheels-package-names.json` and `wheels-resource-open.json`: class 3 opens tire,
  class 5 opens rim under `resources/vehicle`.

For the default 350Z, RimMdlIdx 136 selects library row 0x2ed90, packed handle
0x0280008f, and rim page 143. Its PPF model begins at 0x82ec20; the native embedded
header starts 32 bytes earlier and records saved base 0x0682d020 and body length
0x75c0. Both car tire profiles are 6 and TireMdlIdx is 0: these select tire page 6.
Direct page 136 would select a different native rim and is rejected as a selection
method by the library evidence.

The parser's in-memory adapter prefixes the exact native body with a standard
128-byte PCK header so the existing bounded packet reader can be reused. This
header is not a recovered file. Original offsets satisfy
`ppf_offset = model_file_offset + adapter_offset - 128`. Native wheel mesh
collections use type 0, class 0x7a2228, a count at +2 and a mesh pointer array at +8.

## Experiments and limits

`decoder-car-branch-corpus.json` records all 94 default configurations decoded with
explicit `bike=False`, zero failures. This tests parser coverage and exact source
handles; it does not classify motorcycles as cars. The bike branch was separately
exercised for Aprilia, Kawasaki cop bike, Ducati Smart and Chingon in
`decoder-bike-branch-examples.json`. These selected tire pages 88, 88, 88 and 93.

Nine adjacent wheel tests pass, including wrong archive, invalid index, conflicting
duplicate configuration, missing/oversized PPF page, and four source-model
corruption controls with their expected failure reasons. Additional controls cover
the source class record, native sizing tables and source symlinks/hardlinks. The
ELF fixture is read from the supplied ISO. Ruff also passes.

`verify.json` and `corpus-verify.json` retain Jev's qualified selection and experiment
checks; all four claims were accepted automatically. Total reported tokens were
3,109 input and 352 output. The MCP responses supplied no cost or timing fields.

## Static rest sizing

The exact executable profile is SLUS_213.55, SHA256
`1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d`.
`read_native_sizing_tables` validates this hash and resolves file-backed ELF
PT_LOAD addresses rather than assuming a constant file offset. Width values are
at VA0x619a18 (9 floats), profile diameters at VA0x669840 (8 floats), and rim
numerators at VA0x669a10 (17 floats). Native read_memory receipts and per-table
hashes retain the actual source bytes. Unknown executable versions are rejected.

`FUN_004af9c8` computes numerator[RimSize-12] / profile[TireProfile].
`FUN_002f85d0` scales the car axle basis by (2*width, ratio, ratio).
`FUN_003042c8` copies that frame for the tire and additionally multiplies the rim
Y/Z basis by the profile diameter. The helper composes these static factors as:

- Car tire: (2*width, numerator/profile, numerator/profile).
- Car rim: (2*width, numerator, numerator).

The clamped 0.0254 path in that renderer feeds brake geometry. It is not used as
an alternative rim sizing rule. Native table values are used literally; the
helper does not reinterpret their relation to modern physical wheel sizes.

For bikes, `FUN_002f6c48` captures twice each rest wheel matrix's Y translation.
`FUN_002f85d0` places this in the local Y/Z wheel basis, retaining X=1.
`FUN_003042c8` scales rim/tire X by 0.89*4*joint constraint transmaxX and
additionally scales rim Y/Z by 0.85 for class 5, otherwise0.7. The0.89/0.85/0.7
values are exact native float32 defaults in `FUN_002c55f0`.
The wheel joint's auxiliary pointer is at +0x40; transmaxX is auxiliary+0x24.
This is a degrees-of-freedom constraint block, not a guessed bounding box.

The supplied vehicle.lst selects literal classes. Kawasaki cop bike has COPBIKE,
so the class label alone cannot choose the car/bike branch. The native source
byte at file0x1b4, corroborated by its wrapper skeleton pointer at file0x1ac and
the two/four wheel-joint layout, chooses that branch in the preview caller. Native
`FUN_004b1480` builds the class enum from table0x619a40;
`FUN_004b2318` parses Class into vehicle metadata+8;
`FUN_004b2220` tests that field for5. Index5 is chopper, index6 is sportbike, and index10 is copbike.
The helper permits explicit bike classes CHOPPER, SPORTBIKE and COPBIKE; the
COPBIKE bike uses the native non-CHOPPER0.7factor. It rejects missing,
nonfinite or nonpositive source joint dimensions.

`read_wheel_sizing(executable_bytes_or_path, config_fields, axle=..., bike=...,
vehicle_class=..., wheel_max_x=..., wheel_rest_y=...)` returns separate rim and
tire static scale vectors plus all native table/source pins.
`read_vehicle_class(root,id)` preserves the exact source record and duplicate
copy fingerprints. Placement, spin, camber, runtime deformation and physics are
separate from these scale vectors and are not emulated by this helper.

Nine adjacent tests pass; Ruff passes. `sizing-verify.json` retains Jev's first
combined native trace check. Both composition claims had a verified verdict but
were flagged for review (confidence0.43/0.23). An independent packet/root audit
was requested; this receipt is not automatic completion evidence.

`sizing-corpus.json` records all 94 vehicles and 346 physical wheel joints,
79 four-wheel vehicles and 15 two-wheel vehicles. This combines the 93 unchanged
successful rows from the full source run with the corrected Kawasaki COPBIKE
case; it does not mislabel that combination as a fresh full replay. The original
missing-COPBIKE failure is retained in `sizing-corpus-copbike-rejection.json`.
The independent packet audit freshly checks all 94/346 against the final helper
in `../packets/wheel-scale-independent-composition.json`: maximum arithmetic
discrepancy is 5.551115123125783e-17. This double arithmetic check does not model
the console's floating-point rounding or animation.

## Serialized model and render argument

The native PCK loader reads a 128-byte header and returns the following payload.
Vehicle resource relocation updates payload-root+8 and passes that object to
`FUN_00307400`. Instance construction passes this relocated pointer into
`FUN_002f6c48`, which stores it at instance+0x14. The render caller
`FUN_002fd868` sets its saved pointer to instance+8, then passes the saved
pointer's +0xc slot to `FUN_003042c8`: this is the same instance+0x14 field.
The renderer tests its model argument+0xe4 for the wheel branch.

`runtime-render-object-proof.json` records the complete loader receipts and
exact forwarding excerpts. `runtime-object-link-corpus.json` pins all 94 source
objects at file0xd0, so their +0xe4 field is file0x1b4 and skeleton+0xdc is
file0x1ac. This establishes a static field correspondence; it does not prove
that all later runtime code preserves that field. The original combined Jev
verification requested review, and its expanded combined claim was unsupported
with review. Those receipts are retained. Narrower verification provides the
actual 94-row corpus and separates the decompiled call relation from the source
offset claim; independent review remains the completion authority.

No runtime execution, authentic wheel texture decode, visual fidelity, full
customization behavior or dealership attachment is established by this probe.
