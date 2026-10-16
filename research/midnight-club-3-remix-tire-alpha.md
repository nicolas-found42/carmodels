# Midnight Club tire alpha, reflection and wheel culling

Both showcases now translate the recovered MC3 tire alpha, projected-normal
lookup and additive reflection arithmetic. Native wheel back-face culling fixes
the striped surfaces behind the rims. Original texture pixels, triangle topology,
positions, existing normals/UVs and paint variants remain intact.

The reflection illumination input now comes from the original San Diego midnight
clear garage. Both showcases translate its environment capture, native floor
passes, garage panorama overlay and 256×256 → 64×64 `__specular__` copy. The
synthetic viewer highlight lookup has been removed. This is a portable rendering
translation of a selected original environment, not a captured game frame or
cycle-exact PS2 emulation.

## Native environment generation

`tools/mc3_environment.py` reads the original disc's city PCK, garage props PCK,
`fx_static_envmap_garage.tex` and `garage.garageshared`. It publishes
`dealership/public/midnight-club-3-remix/environment/native-garage.json`;
`--verify` compares every published byte with a fresh disc derivation. The full
native tire verifier also checks this pack. The pack retains all selected prop
triangles, rather than deleting objects based on their names.

The native capture at `562530` looks down from the authored car position plus
one metre in Y, with garage FOV 100°, near .25 and far 1000. Native viewport Y
is negative (`530f38`); with camera up −Z, image row zero faces world −Z.
Among selected garage props, only floor material 8 survives clipping here. The original
sky is decoded and drawn, but the floor covers every output pixel. The source
regression checks full coverage; the renderer rejects newly visible unsupported materials.

The floor's two original passes use source UV pairs, the city palette's entry
127 and source textures. Pass one modulates RGB by `[75,69,65]/128` and keeps
texture alpha. Pass two applies the material blend register `0x81`:
`clamp(floor((destinationRGB − lightmapRGB) × lightmapAlpha / 128))`, writing
RGB only. The pre-sky fullscreen write sets capture alpha to 48 without
darkening RGB. The later tire blend uses destination alpha from the tire's base
pass, independently of the environment lookup's alpha.

The garage panorama uses its original BGRA palette converted to RGBA, with
native alpha `floor(fileAlpha × 128/255)`. Its RGB is bilinearly sampled with
four fractional bits, tinted by `127/128`, then added to the capture; alpha is
preserved. The source panorama wraps. The subsequent 256→64 source target
**clamps** at its edges, while the resulting 64×64 tire lookup repeats. The copy
performs a further `127/128` RGB modulation, not an additive copy. These separate
sampler states are checked against the original executable.

The panorama offset comes from the active camera pose's first vector, its right
axis (`515790` → `39e7c8` → `39d610` → `39d770` → `257ac8` → city+`19c`).
The showcase maps its camera right axis into the authored garage frame using
`CarAnglesd`. Native code writes this value directly into the car's Euler Y and
uses radians in the Y rotation (`325d78`, `244f70`). The scalar continued-fraction
atan2 and nearest-even sixteenth-texel UV rounding are translated separately
from the portable camera transform arithmetic.

Evidence is retained in the
[specular generation receipt](evidence/midnight-club-3-remix/previews/tire-alpha-native/specular-generation.json),
[environment GS receipt](evidence/midnight-club-3-remix/previews/tire-alpha-native/environment-gs.json),
[garage input receipt](evidence/midnight-club-3-remix/previews/tire-alpha-native/garage-environment.json),
[shared texture receipt](evidence/midnight-club-3-remix/previews/environment/shared-texture-native.json)
and [sky input fragments](evidence/midnight-club-3-remix/previews/environment/sky-fragments.json).
The [native scene receipt](evidence/midnight-club-3-remix/previews/environment/native-scene.json)
pins the camera, VU colors, palette and FX source joins.
The five authored ordinary garage glows use queue flag `0x80`; the reflection
queue requires `0x40` (`255f30` → `251af8`). This static environment therefore
has no additional active vehicle/headlight reflection FX actors.

The scalar copy and blend arithmetic are source-derived. Original EE/VU execution
now supplies emitted GIF packets; the shared rasterizer matches the pinned official
PCSX2 v2.8.2 AVX2/FMA software GS byte for byte for this fixed capture and final
64×64 texture. See the [precision investigation](midnight-club-3-remix-raster-precision.md).
Runtime sky/weather animation, temporal jitter and full original frame context
remain outside this selected static environment; no complete booted-game frame
or physical PS2 equivalence is claimed.

## Original inputs and reproduction

Normalized private input: `games/source-data/PS2/midnight-club-3-remix/`, containing
`midnight-club-3-remix.7z` and `midnight-club-3-remix.iso`. The ISO is
8,539,963,392 bytes, SHA-256
`de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9`.
`CARMODELS_MC3_DISC` overrides this location. `SLUS_213.55`, ISO LBA 544,
5,264,872 bytes, has SHA-256
`1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d`.

The [native evidence](evidence/midnight-club-3-remix/previews/tire-alpha-native/)
contains the original small `tire.shadert`, bounded scalar analysis, the original
base-state receipt and the expanded `vu-reflection.json` receipt. The full VU
packet and executable remain private; the new receipt retains selected
instruction evidence and interval hashes rather than the complete microprogram.
`tools/mc3_tire_vu.py` derives the VU/GS contract, and
`tools/verify_mc3_tire_alpha.py --disc` checks it against the original executable
and original ASSETS.DAT `tire.ppf`, as well as rederiving the shader.

Run `tools/check.sh --game midnight-club-3-remix --full`. Offline fixture and
renderer tests run without the private ISO. Controls reject changed VU operands,
alpha arithmetic, lookup matrices, source intervals, GS state and source pages.
The original `native-alpha.json` retains its narrower historical scope; the new
VU and texture-page evidence closes the formerly excluded alpha/lookup path.

## Base coverage and framebuffer alpha

Original ASSETS.DAT ordinal 6745 is `shaderlib/tire.shadert`, offset 1433744384:
523 compressed / 1162 unpacked bytes, unpacked SHA-256
`a5054894ed8236a356fade03730a82bde3bfc3b7fdc70e584105d4a177b0f2ad`.
Only the active PS2 branch is used; semicolon comments include an obsolete
reference pass and are not active behavior.

The active shader declares ALWAYS alpha testing and `ps2blend 0 0 As Cs 0`.
Tire preparation `003beb40` emits `ALPHA_1` register `0x42` with value `0x0a`
for texture 0 and `0x58` for texture 1. The base blend is
`(0 - 0) * As + Cs = Cs`: alpha cannot make the rubber disappear.

The five MPG uploads bound to `specular2_dc` are registered by scalar code at
`003b59a8` from the original packet at `005fe010`. In the base vertex path,
VU instructions `00a7`–`00b9` accumulate lighting, clamp it and multiply by
material RGBA. Scalar `002ae224` uploads light-vector W lanes `[0,0,0,1]` to
VU slots 28–31. Material alpha is 128, so base RGBAQ alpha is always 128.

All 98 original tire pages and 294 embedded image slots have TEX0 PSM=19
(PSMT8), TCC=1, TFX=0 (modulate), CPSM=0 (32-bit CLUT). Thus framebuffer
alpha is `(palette_alpha * 128) >> 7`, i.e. the palette alpha itself. TEXA
expansion does not replace 32-bit CLUT alpha. The observed raw palette maximum
is 84. Original PNG alpha doubles that byte; the viewer reconstructs native
alpha per texel before filtering, also handling saturated PNG 255 as native 128.
It does not treat PNG alpha as coverage or undo scaling after interpolation.

The original initialization packet at `0061c3c0`, enqueued by `005295f4`, writes
PRMODECONT=0. The vehicle/wheel draw state enables PRMODE alpha blending;
`002ad228` packs it into bit 6. The VU GIF tag's ABE bit alone therefore does
not determine blending. This resolves the earlier ABE uncertainty.

## Reflection color and generated coordinates

The second VU pass (`03c0`–`03e6`) replaces texture coordinates and emits RGBAQ
`[127,127,127,0]`. Its source alpha is irrelevant to blend `0x58`:

```
Cs = floor(lookup_RGB_byte * 127 / 128)
RGB_out = clamp(RGB_base + floor(Cs * framebuffer_alpha / 128), 0, 255)
```

This uses destination alpha, not source opacity. The GS texture/blend arithmetic
is corroborated by the [PCSX2 renderer](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/Renderers/HW/GSRendererHW.cpp)
and [register definitions](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/GSRegs.h).
The shared material hook applies the byte arithmetic in display RGB, separately
from Three.js viewer lighting and transfer functions.

The lookup is **not** a textbook reflected environment ray. For native local
position `p` and unnormalized signed VIF normal `n = normal_byte / 128`:

```
P = MVP * vec4(p, 1)
N = MVP * vec4(n, 0)
f = 0.175 + 0.325 * ((vertical_FOV_degrees - 25) / 40)
ST = (f * (N.xy + 0.1 * P.xy) + vec2(0.5)) / P.w
Q = 1 / P.w
lookup_uv = ST / Q
```

GLSL perspective interpolation of the numerator reproduces this ST/Q coordinate
construction. VU instructions preserve the normal X low bit used separately for
ADC; the normal is neither normalized nor masked for lookup generation.

The tire material has a nonzero animated texture-transform pointer, so the
generic reflected-texture matrix is not its active path. All 98 source pages
retain the actual cached matrix with positive XY half scales, half offsets and
Q=1. Scalar `003b5fa0` updates the scales by camera FOV before preparation;
`005311f8` stores that FOV in degrees at camera `+0x19c` before applying the
half-angle tangent projection. The cached scale 0.5 is used for the viewer's
orthographic diagnostic camera. Original native normals travel in the custom
`_MC3_NATIVE_NORMAL` GLB attribute, distinct from existing preview shading normals.

## Striped surfaces behind the rims

A deterministic browser harness renders the real loaded 350Z at a fixed camera,
changing only depth-buffer range. The original full car changed 20,230 pixels
by more than 20 RGB levels. A minimized rim/tire pair changed 20,560 pixels;
the rim alone was stable. Flat opaque materials preserved the defect, while
front-face rendering of the competing native wheel surfaces removed it.

The source geometry contains opposed coplanar axial caps in 316 wheel pairs
across 79 cars. The exporter had made all surfaces double-sided. The native
wheel caller selects cull state 2; tire and selected rim states do not override
it. The VU common draw path tests signed screen area and suppresses back-facing
triangles with ADC. The same culling path is present in the selected rim
microprograms and both builtin programs. This establishes a culling translation,
not a reason to offset, delete or reshape the caps.

All physical rim/tire materials now render front faces. Unrelated body materials
retain their existing policy. The final full-car depth comparison has 4 edge
pixels changed; the minimized pair has zero. Both render substantial foreground
coverage and report no WebGL shader errors, preventing an empty frame from
passing. Source and dealership share the same material and native-normal loader
path. A further neutral-gray `wheel_inner` color remains an inspection choice:
compiled black state alone has not yet closed its runtime class/override path,
so that color was not guessed into a new native claim.

## Preservation and remaining limits

The 94 new conversions retain every original position, existing shading normal,
UV and triangle-index value, all original embedded PNG bytes, node transforms,
paint metadata and variants. New native-normal attributes add source data;
wheel culling and tire reflection provenance change material behavior. Original
DAT downloads remain intact. Publication refreshes only unchanged dealership
imports and preserves independent edits. Models lacking retained native normals
cannot claim an exact native projected-normal lookup.

This combines static source derivation, original EE/VU interpreter execution and
independent official software-GS replay for the selected garage reflection texture.
Original frame-dependent lighting, temporal context, alternate environments and
alternate framebuffer modes remain outside that bounded reference contract. REA rejected
the unmodified R5900 ELF; ordinary Ghidra 12.1.4 with standard MIPS decoding and
repo VU decoding were used, with unsupported R5900 instructions retained as
explicit boundaries. Scalar conclusions use bounded decoded instructions and
source byte checks rather than treating truncated pseudocode as a complete run.

MCLA's 106 source and 106 dealership GLBs were previously audited: included tire
materials are already opaque with exported alpha 255. No equivalent exported
alpha-discard defect was found; native MCLA shader fidelity remains separate.

Local repros, controlled screenshots, full source probes and preservation audits
are under `.scratch/research/mc3-rim-reflection-20261015/` and
`.scratch/research/mc3-vu-reflection-20261015/`. The earlier missing-input search
and opaque inspection workaround are historical stages; restored original shader,
VU and scalar evidence now replace their unresolved MC3 visibility/alpha claims.
