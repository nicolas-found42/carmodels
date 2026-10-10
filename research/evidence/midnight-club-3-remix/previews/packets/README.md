# Native MC3 packet and joint evidence

The bounded reader is `tools/mc3_pck.py`; its ten executable tests are in
`tools/test_mc3_pck.py`. This evidence concerns native packet geometry and rest
joint metadata. The root converter and browser checks establish assembled
preview behavior separately.

- `decoder-bones-wheel-corpus-final.json` records 94 main packages and 4,135
  standalone meshes passing the decoder. The main packages contain 7,070 draws,
  20,951 batches and 10,704 joints across all three LOD groups. Geometry counts
  match the preceding reader corpus after adding the scalar wheel header.
- `shared-resource-corpus-final.json` records 94 shared resource groups, with
  5,299 embedded HLOD names. Every main HLOD name and bone index matches its
  shared group, and material table counts agree. The two Eclipse occurrences
  have identical bytes. Resource precedence at runtime is not established.
- `omitted-shared-resource-resolution.json` resolves 42 previously omitted
  stock parts across 17 cars by exact case-sensitive source names.
  `shared-rest-pose-match.json` checks that all 42 relevant main/shared joint
  records have identical names, parents, positions and raw rotation vectors.
- `bone-corpus-probe.json` retains every native joint and its byte offset.
  The source loader at retail ELF `FUN_0058dc18` uses 0x44-byte joints and sums
  local ancestor translations into the global position. All 10,704 source
  joints agree with that calculation within 1e-5.
- `bone-token-source.json` pins the retail ELF's `offset`, `euler` and `scale`
  strings. Its version-104 parser writes the Euler source vector to joint+0x2c.
  `root-euler-review-resolution.json` accepts that qualified metadata claim,
  without asserting native rendering or a three-axis rotation order.
- `inline-bone-rotations.json` records 875 zero, 346 single-axis and three
  multiple-axis raw vectors among 1,224 inline HLOD parts. No such part has an
  ancestor with a nonzero rotation vector (`inline-rotation-ancestry.json`).
- `ghidra/native-rest-pose-source-functions.json` retains complete, exact-entry
  decompiles for `0058e740`, `0058e8e8`, `0058e470` and `00240090`. The first
  initializer sends the serialized joint Euler vector to the local matrix
  constructor; the updater composes local and parent global frames. The native
  Euler basis and the complete affine multiply assembly establish `Rz*Ry*Rx`
  and parent rotation of local translations. `ghidra/pose-vtable-memory.json`
  and the vehicle initializer link those functions to the vehicle skeleton.
  `native-pose-composition-corpus.json` checks six scalar/order controls and
  2,194 previously rendered or omitted stock records. The five multiple-axis
  omissions include both Corvette hoods, the Yukon rear axle and two Murcielago
  vents; the Corvette hood ancestors also rotate. This supersedes the earlier
  inline-only ancestry result for shared/external parts.
- `root-native-frames-independent-comparison.json` compares an independently
  authored matrix calculator with the root converter for all 10,704 joints in
  94 vehicles. The maximum rotation-basis error is 6.661338147750939e-16 and
  translation error is 8.881784197001252e-16. The native coefficients and the
  mathematical calculation establish static frame order, without claiming
  exact native float32 polynomial rounding or runtime animation.
- `wheel-native-profile-probe.json` pins the 350Z rim and first tire meshes
  inside the shared PPF pages. The rim uploads scale/count with S32 UNPACK;
  its other attribute destinations match the main packet profile. Native wheel
  placement, model selection and scale are separate converter responsibilities.
- `normal-lsb-probe.json` records normal-X low bit one on both initial vertices
  in every main batch. The texture agent's retail VU evidence independently
  establishes its ADC meaning; unsigned color W is retained separately.
- `350z-damage-zone-match.json` finds every checked car-coordinate HLOD vertex
  inside the damage-zone AABB indexed by color W. Jev still labels the semantic
  association uncertain at probability 0.55 (`damage-flag-noul.json`), so the
  decoder preserves W as an uninterpreted flag.
- `wheel-joint-independent-corpus.json` resolves complete source wheel sets for
  all 94 vehicles: 79 cars and 15 motorcycles, with 346 physical wheel joints.
  The bounded aliases, parent references, source positions and all-zero wheel
  ancestry rotations are retained. Nineteen inline wheel-bound meshes are named
  brake, sprocket or spindle components; `wheel-components-classify.json`
  independently classifies them as mechanical attachments. The Jev verification
  in `wheel-joint-verify.json` accepts the source binding and axle claims.
- `wheel-scale-source-review-resolution.json` independently accepts the
  qualified static wheel scale chain against the native decompile. The first
  independent experiment caught the unhandled COPBIKE class for Kawasaki;
  `wheel-scale-missing-class-control.json` retains that rejection. After the
  wheel helper author added the source-exact COPBIKE case, the independent
  calculator matches all 346 physical wheels across 94 vehicles within 1e-12
  (`wheel-scale-independent-composition.json`). The maximum absolute
  discrepancy is 5.551115123125783e-17; Jev accepts this bounded arithmetic
  claim in `wheel-scale-independent-verify.json`. It does not prove native
  animation, runtime float rounding or full scene fidelity.
- `vif-cycle-audit.json` and `vif-cycle-audit-after-fix.json` audit 805,205
  UNPACK planes before and after rejecting unsupported CL>WL destination skip
  cycles. Both runs have identical source records and cycle counts, with zero
  skip planes in 94 main packages, 95 shared occurrences, 4,135 standalone
  meshes, 183 accepted rim pages and 98 tire pages. Ten rim pages fail the known
  native wheel body profile and are explicitly listed. The independent reviewer
  caught the synthetic skip-cycle defect; `skip-cycle-fix.diff` rejects it
  before interpreting headers or attributes. Supported fill cycles remain
  covered, and an unused trailing state command is accepted.
- `wheel-runtime-forwarding-independent-review.json` independently checks the
  pinned source-package, wrapper relocation, model acquisition, instance and
  renderer pointer chain. It accepts the bounded static link between source
  wrapper+0xe4 and the renderer's kind predicate; it does not assert runtime
  emulation or absence of every possible later mutation.

`root-frames-and-export-independent-tests.txt` records thirteen passing tests:
five converter controls and the latest eight exporter boundary controls. The
latest exporter tests add missing declared and undeclared wheel-source
occurrence cases. `export-boundary-eight-independent-gate.json` retains the
model's review and its initially unsupported fixture claim; the additional
complete test-source evidence is checked in
`export-boundary-eight-fixture-verify.json`. The independent reviewer resolves
this narrow test-file uncertainty in
`export-boundary-eight-independent-review-resolution.json`. The earlier
six-test receipt remains historical, not the latest review.

`root-native-frames-independent-gate.json` retains a verified arithmetic claim
and a low-confidence source-chain claim, with patch review escalation. The
independent resolution in
`root-native-frames-independent-review-resolution.json` accepts only the native
frame functions and their application against the full native source trace,
independent matrix corpus and executable controls. Other converter behavior and
the complete dealership feature require their separately assigned reviews.
The exact latest input hashes and intact raw diffs are retained in
`independent-final-review-input-pins.json`; malformed initial evidence-object
inputs were preserved separately as input errors and then repaired using the
live schema.

`packet-tests.txt` and `packet-lint.txt` retain the earlier nine-test and lint
outputs. The Jev claims gates retain their full distributions and escalation
statuses. The final scoped parser gate automatically verifies the test and
raw-rotation scope claims, while requesting independent review for the shared
corpus claim and patch test-gap confidence. It is not automatic approval of the
parser or the finished dealership integration.

`skip-cycle-tests.txt` and `skip-cycle-lint.txt` retain the current ten-test and
lint results. `skip-cycle-fix-receipt.json` compares both actual corpus runs and
records the synthetic defect. The scoped `skip-cycle-gate.json` verifies all
three supplied claims but escalates patch blast-radius confidence and claim
confidence for independent review; it does not automatically approve the patch.
