import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createNativeVehicleSampler } from '../dealership/mc3-vehicle-sampler.mjs';
import { rasterizeNativeVehicleTriangle } from '../dealership/mc3-vehicle-raster.mjs';
import { nativeTextureFunction, nativeVehicleFragment } from '../dealership/mc3-vehicle-fragment.mjs';

const proof = JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-sampler.json', import.meta.url)));
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const state = { framebuffer: 'PSMCT32', depthFormat: 'PSMZ16S', fbmask: 0,
  ate: false, atst: 1, aref: 128, afail: 0, date: false, datm: 0,
  zte: true, ztst: 2, zmsk: false, abe: false, pabe: false, fba: false,
  colclamp: true, aa1: false, fge: false, dthe: false, blend: [0, 1, 0, 1, 128] };
const carbon = [];
for (const record of proof.records) {
  const input = record.case, texture = { ...input.texture, data: new Uint8Array(input.texture.data), readOnly: true };
  assert.equal(hash(texture.data), texture.rgba_sha256, 'original decoded native texels');
  assert.equal(record.execution.runtime.binary_sha256, '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a');
  const sample = createNativeVehicleSampler({ image: texture, tex1: BigInt(input.tex1), clamp: BigInt(input.clamp) });
  const rgba = new Uint8Array(256 * 256 * 4), depth = new Uint16Array(256 * 256);
  rasterizeNativeVehicleTriangle(input.vertices, { xyOffset: [0, 0], scissor: [0, 0, 256, 256],
    textureSize: [texture.width, texture.height], constantQ: true, gouraud: false,
    onPixel(x, y, pixel) {
      const source = nativeTextureFunction({ vertex128: pixel.vertex128, texture: sample(pixel.u, pixel.v), tfx: 0, tcc: true });
      const i = y * 256 + x;
      const result = nativeVehicleFragment({ source, destination: Array.from(rgba.subarray(i * 4, i * 4 + 4)),
        z: pixel.z, destinationZ: depth[i], state });
      rgba.set(result.rgba, i * 4); depth[i] = result.z;
    } });
  for (const [field, stride] of [['frames', 4], ['depth_frames', 2]]) {
    const [w, h] = record[field][0].size, bytes = new Uint8Array(w * h * stride), view = new DataView(bytes.buffer);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (stride === 4) bytes.set(rgba.subarray((y * 256 + x) * 4, (y * 256 + x) * 4 + 4), (y * w + x) * 4);
      else view.setUint16((y * w + x) * 2, depth[y * 256 + x], true);
    }
    assert.equal(record[field].length, 3);
    assert.ok(record[field].every((f) => f.sha256 === hash(bytes)), input.name + ' all original ' + field + ' bytes');
  }
  if (input.name.startsWith('carbon-mmin')) carbon.push(hash(rgba));
  console.log('PASS original sampler ' + input.name + ' whole RGBA and Z16, three frames');
}
assert.equal(proof.records.length, 9);
assert.equal(new Set(carbon).size, 1, 'MXL0 ignores all tested MMIN selectors');
const image = { ...proof.records[0].case.texture, data: new Uint8Array(proof.records[0].case.texture.data), readOnly: true };
assert.throws(() => createNativeVehicleSampler(), /Explicit/);
assert.throws(() => createNativeVehicleSampler({ image, tex1: 4n | 32n, clamp: 0n }), /mip\/nearest/);
assert.deepEqual(createNativeVehicleSampler({ image, tex1: 0n, clamp: 0n })(0, 0), Array.from(image.data.subarray(0, 4)));
assert.throws(() => createNativeVehicleSampler({ image, tex1: 32n, clamp: 2n | 1023n << 14n }), /VRAM/);
assert.throws(() => createNativeVehicleSampler({ image: { ...image, readOnly: false }, tex1: 32n, clamp: 0n }), /read-only/);
assert.throws(() => createNativeVehicleSampler({ image, tex1: 32n, clamp: 0n })(0.5, 0), /signed16/);
console.log('PASS native MXL0/MMAG1 source-window filters, region modes and explicit unsupported profile boundaries');
