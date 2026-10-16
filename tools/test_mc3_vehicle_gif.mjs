import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { decodeNativeVehicleGIF, renderNativeVehicleGIF } from '../dealership/mc3-vehicle-gif.mjs';

const proof = JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-gif.json', import.meta.url)));
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const chunks = (list) => list.map((s) => new Uint8Array(Buffer.from(s, 'base64')));
function vertexBytes(vertices) {
  const bytes = new Uint8Array(vertices.length * 32), view = new DataView(bytes.buffer);
  for (const [i, v] of vertices.entries()) {
    const o = i * 32;
    view.setUint16(o, v.xy[0], true); view.setUint16(o + 2, v.xy[1], true);
    view.setUint32(o + 4, v.z, true); bytes.set(v.rgba, o + 8);
    for (let k = 0; k < 3; k++) view.setUint32(o + 12 + k * 4, v.rawStqWords[k], true);
    view.setUint16(o + 24, v.uv?.[0] ?? 65535, true); view.setUint16(o + 26, v.uv?.[1] ?? 65535, true);
    bytes[o + 28] = v.fog; bytes[o + 29] = Number(v.adc);
  }
  return bytes;
}
for (const row of proof.native_transports) {
  const raw = chunks(row.chunks), prefix = createHash('sha256');
  for (const chunk of raw) {
    const len = Buffer.alloc(4); len.writeUInt32LE(chunk.length); prefix.update(len).update(chunk);
  }
  assert.equal(prefix.digest('hex'), row.source_sha256, row.program + ' original observer transport');
  const decoded = decodeNativeVehicleGIF(raw, { initialRegisters: new Map([[0x1a, 1n]]) });
  assert.equal(decoded.vertices.length, row.vertices);
  assert.equal(sha(vertexBytes(decoded.vertices)), row.vertex_words_sha256, row.program + ' every decoded native vertex word');
  // Observer boundaries can split tags/payloads. They never reset GS latches.
  const oddChunks = [decoded.bytes.subarray(0, 7), decoded.bytes.subarray(7, 37), decoded.bytes.subarray(37)];
  const odd = decodeNativeVehicleGIF(oddChunks, { initialRegisters: new Map([[0x1a, 1n]]) });
  assert.equal(sha(vertexBytes(odd.vertices)), row.vertex_words_sha256);
  assert.ok(decoded.draws.every((d) => d.primitives.length > 0));
  console.log('PASS original ' + row.program + ' GIF vertex words: ' + row.vertices);
}
assert.equal(proof.native_transports.length, 13);
const expectedDraws = [1, 1, 3, 1, 1, 1, 1, 2], expectedTriangles = [1, 1, 3, 2, 1, 1, 1, 3];
for (const [i, record] of proof.records.entries()) {
  const input = record.case;
  assert.equal(record.runtime.binary_sha256, '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a');
  const decoded = decodeNativeVehicleGIF(chunks(input.chunks), { initialRegisters: new Map(input.initial.map(([a, v]) => [a, BigInt(v)])) });
  const target = { fbp: 0, fbw: 4, zbp: 128, width: 256, height: 256,
    rgba: new Uint8Array(256 * 256 * 4), depth: new Uint16Array(256 * 256) };
  const lookups = [];
  const stats = renderNativeVehicleGIF(decoded, { target, resolveTexture(tex0) {
    const key = '0x' + (tex0 & 0x3fffn).toString(16), image = input.images[key];
    lookups.push(key); assert.ok(image, 'only actual supplied native texture bindings');
    return { ...image, data: new Uint8Array(image.data), readOnly: true };
  } });
  assert.equal(stats.draws, expectedDraws[i], input.name + ' native draw boundaries');
  assert.equal(stats.triangles, expectedTriangles[i]);
  for (const [field, stride] of [['frames', 4], ['depth_frames', 2]]) {
    const [width, height] = record[field][0].size;
    const bytes = new Uint8Array(width * height * stride), view = new DataView(bytes.buffer);
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      if (stride === 4) bytes.set(target.rgba.subarray((y * 256 + x) * 4, (y * 256 + x) * 4 + 4), (y * width + x) * 4);
      else view.setUint16((y * width + x) * 2, target.depth[y * 256 + x], true);
    }
    assert.ok(record[field].every((f) => f.sha256 === sha(bytes)), input.name + ' all original ' + field + ' bytes');
    assert.equal(record[field].length, 3);
  }
  if (input.name === 'multipass-bindings') assert.deepEqual(lookups, ['0x2000', '0x2400', '0x2000']);
  if (input.name === 'prmode-dynamic-toggle') assert.deepEqual(decoded.draws.map((d) => d.primitive), [11, 539],
    'selected GS AC toggles keep effective flags; AC1 PRMODE writes are ignored');
  console.log('PASS original GS end-to-end ' + input.name + ' RGBA/Z16, three frames');
}
assert.throws(() => decodeNativeVehicleGIF(new Uint8Array(16)), /Explicit initial/);
assert.throws(() => decodeNativeVehicleGIF(new Uint8Array(15), { initialRegisters: new Map([[0x1a, 1n]]) }), /Truncated/);
const input = proof.records[0].case;
const raw = chunks(input.chunks);
assert.throws(() => decodeNativeVehicleGIF(raw[0].subarray(0, 16), { initialRegisters: new Map([[0x1a, 1n]]) }), /Truncated/);
const changed = new Uint8Array(raw[0]); changed[7] |= 8; // IMAGE format bit59.
assert.throws(() => decodeNativeVehicleGIF(changed, { initialRegisters: new Map([[0x1a, 1n]]) }), /IMAGE/);
function packedTag(regs, values) {
  const b = Buffer.alloc(16 + regs.length * 16);
  b.writeBigUInt64LE(1n | BigInt(regs.length) << 60n, 0);
  b.writeBigUInt64LE(regs.reduce((n, r, i) => n | BigInt(r) << BigInt(i * 4), 0n), 8);
  for (let i = 0; i < values.length; i++) for (let j = 0; j < 4; j++) b.writeUInt32LE(values[i][j], 16 + i * 16 + j * 4);
  return b;
}
const st = [0x3f000000, 0x3e800000, 0x40000000, 0], color = [11, 22, 33, 44], xyz = [16, 32, 160, 0];
const pointInitial = new Map([[0x1a, 1n], [0, 0n]]);
let point = decodeNativeVehicleGIF([packedTag([2], [st]), packedTag([1], [color]), packedTag([4], [xyz])],
  { initialRegisters: pointInitial });
assert.equal(point.vertices[0].rawStqWords[2], 0x3f800000, 'new tag Q latch reset');
point = decodeNativeVehicleGIF([packedTag([2, 1], [[...st.slice(0, 2), 0, 0], color]), packedTag([4], [xyz])],
  { initialRegisters: pointInitial });
assert.equal(point.vertices[0].rawStqWords[2], 0, 'original zero Q retained');
assert.equal(point.vertices[0].stq[2], 2 ** -126, 'selected software GS packed zero-Q rule');
const texturedInput = proof.records[1].case;
const init = new Map(texturedInput.initial.map(([a, v]) => [a, BigInt(v)]));
const decoded = decodeNativeVehicleGIF(chunks(texturedInput.chunks), { initialRegisters: init });
const target = { fbp: 0, fbw: 4, zbp: 128, width: 256, height: 256,
  rgba: new Uint8Array(256 * 256 * 4), depth: new Uint16Array(256 * 256) };
assert.throws(() => renderNativeVehicleGIF(decoded, { target }), /resolver/);
assert.throws(() => renderNativeVehicleGIF(decoded, { target, resolveTexture() { return null; } }), /Unresolved native texture/);
assert.throws(() => renderNativeVehicleGIF(decoded, { target: { ...target, fbp: 1 } }), /binding differs/);
const unsupported = decodeNativeVehicleGIF(chunks(texturedInput.chunks), { initialRegisters: new Map([...init, [0x15, 100n]]) });
assert.throws(() => renderNativeVehicleGIF(unsupported, { target }), /mip\/nearest/);
assert.equal(proof.records.length, 8);
console.log('PASS source words, observer splits, PRE/ADC/REGLIST/Q/context/multipass and explicit profile boundaries');
