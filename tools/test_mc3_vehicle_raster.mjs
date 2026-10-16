import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { rasterizeNativeVehicleTriangle } from '../dealership/mc3-vehicle-raster.mjs';
import { nativeTextureFunction, nativeVehicleFragment } from '../dealership/mc3-vehicle-fragment.mjs';
import { sampleGSFixedRGBA } from '../dealership/mc3-gs-raster.mjs';

const proof = JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-raster.json', import.meta.url)));
const state = { framebuffer: 'PSMCT32', depthFormat: 'PSMZ16S', fbmask: 0,
  ate: false, atst: 1, aref: 128, afail: 0, date: false, datm: 0,
  zte: true, ztst: 2, zmsk: false, abe: false, pabe: false, fba: false,
  colclamp: true, aa1: false, fge: false, dthe: false, blend: [0, 1, 0, 1, 128] };
for (const record of proof.records) {
  assert.equal(record.runtime.binary_sha256, '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a');
  assert.equal(record.frames.length, 3);
  const { case: input, mode } = record;
  const [width, height] = record.frames[0].size;
  const rgba = new Uint8Array(width * height * 4), depth = new Uint16Array(width * height);
  let covered = 0, fractional = 0;
  rasterizeNativeVehicleTriangle(input.vertices, { xyOffset: input.xyOffset, scissor: input.scissor,
    textureSize: [8, 8], constantQ: input.vertices.every((v) => v.stq[2] === input.vertices[0].stq[2]),
    gouraud: input.gouraud, onPixel: (x, y, pixel) => {
      assert.ok(x >= 0 && x < width && y >= 0 && y < height);
      covered++;
      fractional += Number(pixel.vertex128.some((v) => (v & 127) !== 0));
      const source = nativeTextureFunction({ vertex128: pixel.vertex128,
        texture: input.textured ? sampleGSFixedRGBA(input.texture, pixel.u, pixel.v) : null,
        tfx: input.textured ? 0 : 4, tcc: true });
      const index = y * width + x;
      const out = nativeVehicleFragment({ source, destination: Array.from(rgba.slice(index * 4, index * 4 + 4)),
        z: pixel.z, destinationZ: depth[index], state });
      rgba.set(out.rgba, index * 4);
      depth[index] = out.z;
    } });
  if (mode === 'depth') {
    for (let i = 0; i < depth.length; i++) {
      const out = nativeVehicleFragment({ source: [31, 227, 59, 173],
        destination: Array.from(rgba.slice(i * 4, i * 4 + 4)), z: 24000, destinationZ: depth[i], state });
      rgba.set(out.rgba, i * 4);
      depth[i] = out.z;
    }
  }
  assert.ok(covered > 10000, 'nontrivial triangle coverage');
  assert.equal(fractional > 1000, input.gouraud, 'fractional Gouraud colors retained');
  const digest = createHash('sha256').update(rgba).digest('hex');
  assert.ok(record.frames.every((frame) => frame.sha256 === digest), record.name + ' every original GS framebuffer byte');
  const [zw, zh] = record.depth_frames[0].size;
  const zbytes = new Uint8Array(zw * zh * 2), view = new DataView(zbytes.buffer);
  for (let y = 0; y < zh; y++) for (let x = 0; x < zw; x++) view.setUint16((y * zw + x) * 2, depth[y * width + x], true);
  const zdigest = createHash('sha256').update(zbytes).digest('hex');
  assert.ok(record.depth_frames.every((frame) => frame.sha256 === zdigest), record.name + ' every original stored16bit depth word');
  console.log('PASS ' + record.name + ' native RGBA ' + digest + ' Z16 ' + zdigest);
}
assert.equal(proof.records.length, 10);
const input = proof.records[0].case;
assert.throws(() => rasterizeNativeVehicleTriangle(input.vertices, {}), /Explicit/);
assert.throws(() => rasterizeNativeVehicleTriangle(input.vertices.map((v, i) => i ? v : { ...v, rgba: [-1, 0, 0, 0] }),
  { gouraud: true, xyOffset: [0, 0], onPixel() {} }), /RGBAQ/);
console.log('PASS flat provoking vertex, Gouraud fractional lanes, textured/projective triangles and stored-depth controls');
