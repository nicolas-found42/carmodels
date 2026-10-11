# Gran Turismo native wheel assembly

The static source and editable libraries assemble wheels from original executable
templates, native CAR attachment fields and CTEX colour-set-0/CLUT-0 artwork.
These are recovered source meshes with a reconstructed neutral pose. Original
game execution and rendered equivalence are not established.

## Source ownership and packing

GTMAIN.EXE, extracted from the locally supplied disc, has SHA-256
`3fd17ae24e23b9c939d15951d6dafe254fa6611488327c128dfe4637f83d36f8`.
Its PS-X loader expands a backward PSLZ stream to 671,744 bytes at `0x80010000`,
SHA-256 `0d7e00755c0d9234113607daf39ced3728ffe42d4e1984e32eb664f4542f48fd`.
`tools/gt_wheels.py` translates that bounded loader and can rederive the retained
bytes with `--check <original GTMAIN.EXE>`. Normal export needs no private executable:
the compact [native table receipt](evidence/gran-turismo-wheels/native-wheel-tables.json)
retains 2,612 exact table bytes and their 20-byte pointer array. Code-owned pins
check every payload, declaration and pointer before use.

The pointer array at `0x800974b4` selects these native tables. Each begins with
a four-byte quad count, followed by four `<3hH>` vertices per quad. The final
word carries U in its low byte and V in its high byte.

| Native wheel LOD | Address | Quads |
| --- | --- | --- |
| 0 | `0x800970d0` | 31 |
| 1 | `0x80096dec` | 23 |
| 2 | `0x80096c08` | 15 |
| 3 | `0x80096aa4` | 11 |
| 4 | `0x80096a80` | 1 |

Native instruction slices and hashes are retained in
[native-routine-evidence.json](evidence/gran-turismo-wheels/native-routine-evidence.json).
GTMAIN `0x8007144c` loops over the four CAR tuples at `0x10`; its template renderer
`0x8006d2a4` selects the table and emits textured GPU packets. Independent GTMENU
analysis found the same wheel loop at `0x80033860`, differing only in relocated
direct jump/call targets. Earlier six-point ring candidates were discarded after
their input structure and packet writes failed to establish wheel ownership.

## Native fields and static reconstruction

The community GTExplorer/GT2ModelTool names for the four dimension words are
misleading here. Native instructions establish **width, radius, width, radius**
at `0x30..0x36`: the first word feeds width/radius aspect scaling and half-width X
translation, while the second controls radial scale. The first pair applies to
file wheel indices 0/1 and the second to 2/3. Export does not depend on inferred
front/rear naming or retail identities.

For neutral steering and spin, the game applies Y quarter turns of +90 degrees
to even wheel indices and -90 degrees to odd indices. It shifts header X inward
by signed half-width; the header tuple is therefore not the mesh's geometric
centre. The exporter preserves integer aspect division and axial rounding,
then scales to metres. It reflects the entire assembled wheel across Z to match
the existing body export, rather than combining reflected body vertices with
the community helper's unreflected wheel coordinates.

Packet writes put source vertices into GPU quad order `(0,1,3,2)`. The static
triangles are `(0,1,3)` and `(3,1,2)` before the export's Z reflection. Native
wheel packets have no stored normals; export derives flat geometric normals.
Native CTEX upload code in GTMENU `0x80036ca0` transfers the selected 512-byte
palette block at `0x8060 + colourIndex*512` to the allocated base CLUT. The wheel
caller uses that base without a selector offset, establishing CLUT selector 0
within the chosen colour set. Preview colour set 0 remains the existing policy.

The native showroom caller selects wheel template 0 independently of body LOD,
so the three exported body scenes share four template-0 wheel nodes. All five
wheel templates remain retained and verified; the export does not invent a
correspondence between three body LODs and five wheel LODs.

`_0logn`, day/night, has small special bodies in LOD0/1; `_lcupn`, day/night,
has one in LOD0. Their remaining LODs have vehicle-shaped bodies. The application
omits wheels from a scene only when
all four header anchors exceed its lateral/longitudinal body bounds by over
0.1 metre. This is a conservative **display policy**, not a recovered game rule.
The original game's routing for these special assets remains unresolved. Header
data, wheel nodes and source templates are retained even for suppressed scenes.

## Editable upgrades and checks

`tools/import_gt_dealership.py --upgrade-unedited` upgrades a working model only
when its current hash equals its recorded latest source (or initial source for
first upgrades). Edited models remain intact. Source-owned `claimLimits` are refreshed while custom notes and other catalog
fields are retained. Original `initialSource` provenance remains intact; later
hashes are recorded separately
in `latestSource` and `sourceUpgrades`. Tests cover changed sources, explicit
upgrade selection, preserved edits, repeated runs and source corruption.

Wheel tests independently pin XYZ and UV sequences, known vertices, side
transforms and nonexact aspect rounding. Mutation controls reject altered table
bytes, pointers, declarations, missing LODs, invalid base64, source mismatches,
truncated packing and invalid backreferences. Integration tests cover original
UV ordering, four editable wheel meshes, scene ownership and every retained CAR.
The final run and independent export/preservation audits are recorded in the
task's `.scratch/gt-wheels/` evidence directories.

The refreshed source corpus has 728 GLBs totaling 162,320,680 bytes, with 2,912
stored wheel meshes and 180,544 stored wheel triangles. Its 2,184 body LOD scenes
contain 540,144 visible wheel triangles; six special-asset scenes omit wheels.
Two independent audits compared exported positions, UVs, triangle ownership and
source pins; one also decoded all 47,710,208 wheel-texture RGBA pixels
against native CTEX. The working dealership has 728 upgraded GT copies with
distinct source inodes and one link each. All 35 Ford Racing catalog/origin
entries and 2,299 protected native/Ford Racing files remained unchanged.
`tools/check.sh --evidence-dir .scratch/gt-wheels/full-checks-final` passed all
40 checks with no skips, including the existing Ford Racing Gran Torino Blender
edit/export round trip. A GT-specific Blender round trip was not run. The actual
pre-task GT corpus had no edited copies or custom claim notes; preserving those
cases is covered by synthetic importer tests.
The initial integration audit's incorrect `_lcupn` LOD1 suppression expectation
was corrected from native bounds evidence; the failed attempt remains retained.

Jev informed source screening, candidate interpretation, conflicting dimension
names, native ownership verification and completion review. Low-confidence
dimension, coordinate and palette judgments were retained for independent native
review. Final gates escalated and rejected a broad preservation claim; narrower
claims distinguish refreshed source notes, retained catalog fields and fixture-only
customization coverage. Original gate receipts are retained. Exact decoding, hashes, geometry and bounds decisions remain executable
code. This task does not add probabilistic decisions to deterministic mesh decoding.
REA's native opener rejected PS-X EXE as unsupported; its Ghidra provider was
unavailable. The recovery therefore used the source-pinned loader translation,
Capstone MIPS disassembly and independent instruction/byte audits.

Dynamic steering/spin, camera-dependent GTE quantization, PS1 shading and
semi-transparency, runtime LOD selection, additional colour-set display and exact
game-render equivalence remain outside the verified static assembly.
