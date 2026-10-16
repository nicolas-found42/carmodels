import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { nativeTextureFunction, nativeVehicleFragment } from '../dealership/mc3-vehicle-fragment.mjs';

const proof = JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-fragment.json', import.meta.url)));
assert.equal(proof.reference_commit, 'fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3');
assert.equal(proof.runtime.runtime.binary_sha256, '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a');
const [width, height] = proof.runtime.selected_output.size;
const image = new Uint8Array(width * height * 4);
for (const [index, record] of proof.cases.entries()) {
  const source = nativeTextureFunction({ vertex128: record.vertex.map((v) => v * 128), ...record });
  const output = nativeVehicleFragment({ source, ...record });
  assert.deepEqual(output.rgba, proof.case_rgba[index], record.name + ' native RGBA');
  const depthProbe = nativeVehicleFragment({ source: [11, 239, 37, 91], destination: output.rgba,
    z: 1500, destinationZ: output.z,
    state: { ...record.state, ate: false, date: false, zte: true, ztst: 2, zmsk: false,
        abe: false, pabe: false, fba: false, colclamp: true, fbmask: 0 } });
  assert.deepEqual(depthProbe.rgba, proof.case_depth_probe_rgba[index], record.name + ' native stored depth');
  const x = index % 16 * 16, y = Math.floor(index / 16) * 16;
  for (let dy = 0; dy < 16; dy++) for (let dx = 0; dx < 16; dx++) {
    image.set(dy < 8 ? output.rgba : depthProbe.rgba, ((y + dy) * 256 + x + dx) * 4);
  }
}
assert.equal(createHash('sha256').update(image).digest('hex'), proof.rgba_sha256, 'complete official GS framebuffer');
const state = proof.cases[0].state;
const source = [201, 133, 17, 255], destination = [93, 143, 213, 155];
for (let test = 0; test < 8; test++) for (const a of [0, 112, 113, 114, 127, 128, 255]) {
  const expected = [false, true, a < 113, a <= 113, a === 113, a >= 113, a > 113, a !== 113][test];
  const actual = nativeVehicleFragment({ source: [...source.slice(0, 3), a], destination, z: 2000,
    destinationZ: 1000, state: { ...state, ate: true, atst: test, aref: 113, afail: 0 } });
  assert.equal(actual.framebufferWrite, expected);
}
// A fractional interpolated lane must survive until native TFX multiplication.
assert.deepEqual(nativeTextureFunction({ vertex128: [16447, 16447, 16447, 16447],
  texture: [255, 255, 255, 255], tfx: 0, tcc: true }), [255, 255, 255, 255]);
assert.equal(nativeTextureFunction({ vertex128: [16383, 0, 0, 0], texture: [128, 0, 0, 0], tfx: 0, tcc: true })[0], 127);
assert.throws(() => nativeTextureFunction({ vertex128: [1, 2, 3, 4], tfx: 0 }), /tcc/);
assert.throws(() => nativeVehicleFragment({ source, destination, z: 0, destinationZ: 0,
  state: { ...state, framebuffer: 'PSMCT16' } }), /Unsupported/);
assert.throws(() => nativeVehicleFragment({ source, destination, z: 0, destinationZ: 0,
  state: { ...state, afail: undefined } }), /afail/);
assert.throws(() => nativeTextureFunction({ vertex128: [32768, 0, 0, 0], texture: source, tfx: 0, tcc: true }), /vertex128/);
for (const name of ['aa1', 'fge', 'dthe']) {
  assert.throws(() => nativeVehicleFragment({ source, destination, z: 0, destinationZ: 0,
    state: { ...state, [name]: true } }), /Unsupported/);
}
console.log('PASS 64 official software-GS fragment/depth observations and complete framebuffer bytes');
console.log('PASS fractional TFX lanes, all alpha boundaries and explicit unsupported-state refusal');
