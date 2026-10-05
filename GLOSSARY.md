# Recovery

Recovered Ford Racing 2 (PAL, SLES-51705) car assets, the tools that recovered them, and the evidence
that backs each claim about how the game draws a car.

## Language

### Corpora

**Reference tree**:
The verbatim extraction from the PAL PS2 disc under `reference/ford/`, one folder per car, with provenance and a sha256 for every file.
_Avoid_: Raw dump, original files

**Recovered corpus**:
The canonical outputs under `recovered/`, each car carrying a hash-verified `manifest.json`.
_Avoid_: Output folder, export

### Evidence

**Verifier**:
A standalone script that derives an expected result from pinned sources, compares it with its receipt, and rejects every one of its controls.
_Avoid_: Self-test, validator

**Receipt**:
The committed JSON a verifier writes under `research/evidence/<area>/`; it backs a claim in a research note, and re-running the verifier reproduces it byte for byte.
_Avoid_: Log, report

**Control**:
A mutated copy of a verifier's inputs that the verifier must reject; a pass means every control failed for the intended reason.
_Avoid_: Negative test, sanity check

**Claim limit**:
A statement in a receipt or note of what its check does not establish.
_Avoid_: Caveat, disclaimer

**Static input**:
A file derived from the game executable (the overlay microcode and its disassembly, the typed decompilation export, the executable itself) that is pinned by sha256 and never committed.
_Avoid_: Dependency, source checkout

**Capture**:
A live emulator run recorded as savestates, unpacked memory files and GS dumps; the files are gitignored and pinned by receipt.
_Avoid_: Recording, snapshot

**Static derivation**:
A result obtained by reading code and data without running anything; it is not evidence of what the game did in a frame.
_Avoid_: Proof, trace

**Candidate**:
An interpretation that fits every measurement but is not proven, such as a strip order, normal, UV or texture selector mapping.
_Avoid_: Result, guess

### Model data

**Header**:
One geometry record's entry in a car model: a vertex count, flags, a texture index and the offsets of its planes.
_Avoid_: Mesh, submesh

**Plane**:
A per-vertex array that a header points to: the six-byte plane (signed 16-bit positions), the four-byte plane (three signed bytes and a fourth byte that is 0 or 1), and an optional UV plane.
_Avoid_: Buffer, attribute

**ADC**:
The bit in a drawn vertex that stops that vertex from completing a triangle in a strip; the four-byte plane's fourth byte feeds it.
_Avoid_: Skip flag, cull flag

### The draw path

**Retained display list**:
The chain of draw descriptors saved in a savestate's EE memory.
_Avoid_: Ring, command buffer

**Draw descriptor**:
One retained draw: its header, vertex count, pass word, flags and colour vector.
_Avoid_: Draw call, packet

**GSDump**:
A one-frame capture of every transfer the game sent to the graphics chip.
_Avoid_: Frame dump, screenshot

**Aligned**:
A draw descriptor matched to a GSDump tag by vertex count and primitive sequence; a content match, not proof that they ran in the same frame.
_Avoid_: Joined, traced

**Pass word**:
The number from 1 to 6 in a draw's packet header that selects, through the jump table, which VU1 handler processes it.
_Avoid_: Pass id, mode

### VU1 microcode

**Overlay**:
One segment of VU1 microcode (2 KiB, or 256 instruction pairs, except the 176-byte overlay 6) resident in micro memory with the others; a program can span overlays.
_Avoid_: Program, module

**Instruction pair**:
The 64-bit VU1 unit of one upper and one lower instruction; addresses and branch offsets count pairs.
_Avoid_: Instruction, word

**MSCAL entry**:
The VU1 start address carried by a VIF MSCAL command; the game uses three: 0, 0x1a and 0x5cc.
_Avoid_: Program entry, start address

**Jump table**:
The seven VU1 addresses overlay 0 writes to VU data memory, indexed by the first lane of the packet header.
_Avoid_: Dispatch table, vector table

**Dispatch**:
The overlay-0 code that reads the pass word from the packet header and jumps through the jump table.
_Avoid_: Scheduler, router

**Handler**:
The VU1 code a jump-table entry points to, run for one pass word.
_Avoid_: Shader, kernel

**TOP**:
The VIF register naming the buffer where the current packet landed; handlers read packet data relative to it.
_Avoid_: Packet base, buffer pointer
