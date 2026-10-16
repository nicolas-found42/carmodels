# MC3 vehicle rendering recovery

This investigation extends the fixed-garage reflection work to the vehicle itself.
The requested scope includes the static showroom appearance and gameplay effects:
damage, animated lights, moving wheels and rider animation. The investigation is
in progress; the existing static GLBs do not implement those systems.

## Questions and acceptance evidence

| Area | Required evidence | State |
| --- | --- | --- |
| Native material families and ordered passes | Original shader resources, compiled material objects and scalar binders | Graph retained; selected binders independently executed; renderer pending |
| Vertex lighting and generated coordinates | Original VU instructions and independently executed raw-word probes | Thirteen registered programs and selected builtin controls match interpreter memory/register/GIF/cycle output; actual actor uniform joins pending |
| Garage and gameplay light inputs | Original environment/tuning resources joined to native state writers | Original garage light binder independently executed with explicit parked-car frames; city/gameplay state joins pending |
| Source attribute preservation | Every selected native batch joined to exported original lanes | All94 models published to both showcases with raw lanes, skeleton, material tables and texture bytes; original DATs retained |
| Shared vehicle renderer | Both showcases consume recovered material programs and source attributes | Pending |
| Damage and deformation | Native state transitions, geometry update code and original damage inputs | Original carpaint preprocessing and EE palette helpers verified; collision/state joins pending |
| Lights and time-dependent effects | Native animation/state code, resources and executed controls | Pending |
| Wheel and rider animation | Native skeleton/animation dependency closure, transforms and executed controls | Wheel lookup/frame helpers verified; rider skinning/controller joins pending |
| Output equivalence | Independent pinned software-GS comparisons with failure controls | Selected fragment/raster/color/depth controls verified; whole vehicle output pending |

The prior byte-exact contract remains limited to the selected static garage
reflection texture. It does not establish vehicle shading or gameplay fidelity.
New conclusions must distinguish source derivation, isolated kernel execution,
complete draw execution and whole-frame comparison.

## Working evidence

Local investigation output is retained under
`.scratch/research/mc3-vehicle-rendering-20261015/`,
`.scratch/research/mc3-vehicle-material-20261015/`,
`.scratch/research/mc3-vehicle-vu-20261015/` and
`.scratch/research/mc3-vehicle-renderer-audit-20261015/`.

The selected original executable remains `SLUS_213.55`, SHA-256
`1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d`.
The existing fixed-garage comparison is described in
[the raster precision investigation](midnight-club-3-remix-raster-precision.md).

## Current implementation boundary

The shared browser VU interpreter is being checked against complete original
program jobs, including emitted GIF bytes, final data memory, vector registers
and cycle counts. Its separate synthetic ISA controls cover pair conflicts,
old-VI forwarding, delayed clipping/Q, integer conversion, memory wrapping and
end delay. These controls are retained in
`evidence/midnight-club-3-remix/previews/vu-interpreter-controls.json`.
Whole-program tests currently use explicit controlled uniforms. Reusing a source
batch with another microprogram is a cross-program control, not evidence that
the car's authored material selects that program.

The resource loader uses retained native RGBA bytes, including original alpha,
rather than reconstructing alpha from display PNGs. It verifies each embedded
payload hash and material-table/texture-reference identity. Runtime images and
undecoded texture profiles remain explicit unresolved resources. Both showcase
loaders can attach this data without putting it into editable scene serialization.

The published exports also retain the original VIF packet bytes and relative
batch offsets. An independent audit compared all 7,163 packet intervals against
their original source carriers and preserved the earlier candidate's geometry,
scene, records and 696 display PNG payloads. Geometry provenance is separate from
material provenance: an attachment can inherit a PCK material while its mesh
comes from a PPF. Executing these original packets still requires the exact VIF
unpacker; the older Python plane reconstruction is not that equivalence claim.

The program pack derives custom registry indices from original registration
instructions, including their branch delay slots, and retains both builtin
variants. The browser decoder requires an explicit native builtin selector.
This establishes the program resource boundary; it does not construct a car's
camera, light, texture or animation state.

The new state-packing stage matches 32 executions of original `002ad228`,
including literal GS blend/test/write registers and VU control/color words.
Its contract is an explicit complete dirty-state update for a 32-bit color and
16-bit depth target. Texture binding, engine cache transitions and draw epilogues
remain separate. The bounded fragment and raster stages have independent
software-GS color/depth controls; unsupported formats and state are rejected.
These modules are not yet the active vehicle renderer.

The actual compiled pass indices must be joined to complete actor draw state
before activation. Template names alone do not select native microprograms.
Generated paint is also more than a single radial lookup: native gradient,
highlight and nearby-light composition belongs to the recovered command stream.
The existing display materials still supply the active vehicle appearance;
this investigation has not yet removed their approximations.

## Further executed boundaries

The generated-paint transport now has a complete two-context regression in
`evidence/midnight-club-3-remix/previews/vehicle-paint-pipeline.json`.
The original factory and paint function produced the retained raw VIF bytes.
The browser executes their uploaded VU programs, literal GIF IMAGE transfers,
CLUT loads, sprites and triangles against explicit private VRAM. The complete
256-square positive and flat RGBA buffers match the pinned original software GS.
The full-sized comparison uses the next replay's first alpha-only prefill:
RGB is masked and the completed image already has alpha 128 everywhere. It does
not assemble a reference image from cropped primitive rectangles.

This paint stage rejects depth reads, unsupported TEX2/HWREG writes and uploads
that span an otherwise unchanged draw group. General overlap-aware GS flushing,
framebuffer feedback and vehicle depth ownership remain separate work. The
VRAM receipt covers CT32, PSMT8 and PSMT4 addressing and host uploads, including
packed32 aliases, odd buffer width and nibble padding. Its conditional CLUT
cache controls beyond CLD1 are source-derived unit controls rather than executed
native draw goldens.

Original camera/frame/light upload routines now have four explicit caller
contexts in `evidence/midnight-club-3-remix/previews/vehicle-uniforms.json`.
Both source matrix backends produce identical 704-byte DMA payloads. Independently
executed browser and original EE results agree across all 32 MiB RAM. These
contexts specify projection, pose, actor frame, light words and a 256-square
display; they do not choose live actor lights or initialize a whole game scene.

The original skeleton constructor, local Euler-frame initializer and world
palette update also have twelve source contexts in
`evidence/midnight-club-3-remix/previews/vehicle-skeleton.json`: 350Z 250 joints,
FX45 111 joints and Ducati 24 joints, two root poses and both matrix backends.
The browser and original EE match all 32 MiB RAM in every context. Serialized
mesh bonebyte+6 agrees with the source group bone table. This establishes rest
palette generation with an explicit actor frame; gameplay animation, damage,
IK, weighted skinning and final stock-part visibility are not established by it.

Private full-ELF browser probes also reproduce both whole factory sequences
across all 32 MiB RAM, including native camera/image/texture construction, radial
and palette generation and the paint function. Their private carrier has not
been published: a sparse instruction/data pack now reproduces both contexts after an explicit
projection of unused ELF bytes. Runtime actor joins and production packaging
remain in progress. The bounded EE instruction increments have separate
original execution controls for masks, aliases, finite arithmetic, raw lane
rotation and packed 128 copies. A working isolated factory is not evidence that
either showcase has activated the native vehicle renderer.

## Published data and precision controls

The reviewed 94-model edition is installed in canonical recovery, public source
previews and independent dealership working copies. Publication validated the
previous source edition, retained all 94 original DAT packages and used the
importer's hash guard for working edits. No MC3 working copy differed from its
recorded import at this checkpoint. Both catalogs and the paint library were
rebuilt; the six publication checks, including the complete MC3 preview corpus
and both freshness checks, passed. The retained publication audit is
`.scratch/research/mc3-vehicle-rendering-20261015/publication-1/after-audit.json`.
This publishes source inputs for the new renderer; the existing display
materials remain active.

The unsigned-depth stage has 26 original software-GS controls in
`evidence/midnight-club-3-remix/previews/vehicle-high-z.json`. Independent native
reexecution matched the complete receipt and all 156 RGBA/Z32 exports. It retains
the selected software GS's literal bitwise depth-equality correction and biased
double-to-integer conversion. Integration must also preserve the original GS
source-vertex buffer lifetime: skipped or culled vertices affect depth tracing
differently from indexed raster primitives. Thirteen original multi-triangle,
ADC, culling and textured controls now verify that bounded shared-consumer
boundary, including STQ rounding under corrected depth equality. Whole-vehicle
activation remains separate.

The varying-Q mip stage has 18 original software-GS controls in
`evidence/midnight-club-3-remix/previews/vehicle-variable-mip.json`. Independent
reexecution matched all 108 RGBA/Z16 exports. It preserves the separate unfused
trace polynomial and fused scanline polynomial, fixed-point LOD rounding and
per-pixel trilinear fractions. This bounded stage is independently reviewed;
authored material binding and showcase activation remain separate work.
