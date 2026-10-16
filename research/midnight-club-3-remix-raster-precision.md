# MC3 reflection raster precision

The acceptance reference for this investigation is the official PCSX2 **v2.8.2 AVX2 software GS**, commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. The requested comparison is byte-for-byte RGBA output.
This is a software-reference contract, not a claim that PCSX2 reproduces physical PS2 output exactly.

## Measured reference probes

The isolated reference replay runs the pinned official executable without a BIOS or game boot.
The GS receives the submitted packets and original texture bytes. The reconstruction does not supply
its predicted pixels to the reference renderer.

| Probe | Measured RGBA SHA-256 | Result |
| --- | --- | --- |
| Subpixel, constant-Q textured triangle | `24b10b8c49f435c6e26c37c696ca086bbf21d6e470fb7b649acbf3fac426df9a` | All 262,144 bytes equal |
| Same triangle with all STQ multiplied by two | Same as above | All 262,144 bytes equal |
| Varying-Q perspective triangle | `b96045a08e4b8817e22ae59b9cb4fa8b03d48ea26ae87491508c089e26b4e259` | All 262,144 bytes equal |
| Native 256-to-64 specular copy | `ed4da06c0feb166ac9f0aca5d69ba5d317d7c7ea2607ea77bd481f32b5487249` | All 16,384 bytes equal |

The solid right-triangle probe covers 32,896 pixels. The subpixel textured triangle covers 32,521.
These independently executed probes exercise integer sample origins, triangle edges, float32
interpolation, the selected eight-lane stepping sequence, constant-Q optimization, perspective
division and four-bit bilinear filtering. They do not establish the complete original garage frame.
The focused offline regression is `node tools/test_mc3_gs_raster.mjs`.

## Original game boundaries recovered

The source is `SLUS_213.55`, SHA-256
`1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d`.

* The original VU program contains a six-plane clip kernel selected by its uploaded state flags.
  Its XY guardband is four times the visible capture. Original clip/cull control flow selects the kernel during execution;
  the browser does not substitute a fixed host polygon-clipping predicate.
* Source UV0.X retains its least significant bit. The unlit world VU path uses it to generate ADC;
  clearing it or reconstructing it from normalized normals changes the original input.
* The screen offset is added before FTOI4. Removing the large offset algebraically before rounding
  is not an equivalent operation.
* The original GIF header uses packed ST, RGBAQ and **XYZF2** (`0x412`). XYZF2 transport removes the
  four fractional depth bits from the VU output. The capture depth buffer is PSMZ16S with a 65,535
  display depth range; the repeated floor passes use GEQUAL.
* The Euler helper `0x240090` calls the original COP2 polynomial sine/cosine routine `0x41c6d8`.
  Ordinary host sine/cosine is not a source-equivalent substitute. The capture camera uses a
  direction-vector basis routine instead of that Euler helper.

Original VIF carriers and untransformed integer lanes are retained in `native-garage.json`.
This preserves the evidence needed for native execution; retaining those inputs alone does not prove
that the resulting pixels match the reference.

## Fixed garage acceptance

The complete source-bound regeneration executes 15 original EE/VU jobs. Both camera-matrix
backends produce identical words for this fixed pose. Native VU clipping, culling, reciprocal,
ADC and FTOI4 operations execute in the original interpreter; the browser consumes emitted GIF
packets instead of reconstructing those operations with host floating-point geometry.

The final capture and reflection outputs match all RGBA bytes in three independent replay frames:

| Stage | Size | SHA-256 |
| --- | --- | --- |
| Floor base + lightmap + DATE alpha prefill | 256×256 | `9fa63bae26862424b078221da7422ff994093aba857eb800d0e02dc58ec3caba` |
| Capture + panorama, offset 0 | 256×256 | `b24f5b974794bf913a74baaf86d15dad6cbf90384ba92e459bb502f1cc541799` |
| Final specular, offset 0 | 64×64 | `8df682b424767d6a0ecc5325b7cc90e37754d2930dd9377617158177c8553a45` |
| Final specular, offset 7/16 texel | 64×64 | `0f08522eb797d447660e2bf96ab1ea83e79238fc0f32ee987c8ed32ba971e1d5` |

The original full-floor base pass initially differed in 556 bytes, each by one. The pinned binary
uses fused multiply-add instructions, and its GS state flush truncates ST/Q mantissas for
constant-depth textured triangles. Q tracing happens before that truncation and excludes triangles
rejected by the GS screen bounds. Reproducing that sequence closes the mismatch. Exact integer-backed
FMA rounding avoids introducing another host double-rounding assumption.

All 412 other selected world batches remain in the input set and in both conservative culling
controls. Their emitted geometry covers no GS pixels. An independent official-GS control uses
untextured, unblended ALWAYS-depth writes with FBA forcing nonzero alpha for any covered pixel;
both complete streams leave the target untouched. A visible zero-color triangle tests that this
coverage detector can fail. Native sky geometry is retained and fails depth behind the floor.
Hidden material shading is therefore outside the reconstructed subset without being silently
assumed to have no geometry.

The copy target must be mapped into the replay's privileged display readout. Official GSState
intentionally defers VSync flushing for offscreen draws. Mapping readout to the tested 64×64 target
produces all three completed targets without changing any submitted GIF bytes or raster arithmetic.

## Reproduction and limits

Receipts: [source geometry](evidence/midnight-club-3-remix/previews/environment/geometry-native.json),
[executed packets](evidence/midnight-club-3-remix/previews/environment/native-gs-executed.json),
[reference runtime](evidence/midnight-club-3-remix/previews/environment/reference-runtime.json), and
[full RGBA comparisons](evidence/midnight-club-3-remix/previews/environment/raster-reference.json).

Fast checks run by default. `tools/check.sh --game midnight-club-3-remix --full` also rederives the
source disc and executes the optional pinned reference when provisioned. The full reference check
reexecutes the original EE/VU jobs, compares their deterministic fixture, checks hidden geometry,
then compares the production renderer with independent GS replay. A missing reference is an explicit
skip; a wrong executable pin is a failure. It never substitutes predicted pixels into the oracle.

The optional runtime requires the pinned AppImage in `tools/headless-runtime/`, Docker with AVX2/FMA
support, and the original MC3 disc resolved by `tools/static_inputs.py`. Build the existing base image
as `carmodels-mc3-gs-reference:2.8.2`, then build `tools/reference-runtime/Dockerfile` as
`carmodels-mc3-vu-reference:2.8.2`. The adapter checks actual executable bytes before using ABI offsets.
Run `python3 tools/verify_mc3_raster_reference.py` for retained per-run execution evidence.

This closes the precision approximation for the selected static garage reflection capture in both
showcases. The contract fixes the authored camera, 640×448 display origin, zero jitter, static sky,
and recovered floor/material states. It does not certify physical PS2 pixels, other SIMD binaries,
other environments, animated lighting or a complete booted-game frame. The rest of the showcase is
still rendered by its normal WebGL viewer.
