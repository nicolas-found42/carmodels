// Native vehicle GIF transport and a bounded explicit-state software-GS draw
// consumer. Original VRAM/image ownership stays with the supplied resolver.
import { intersectsGSScissor, roundGSSTQ } from './mc3-gs-raster.mjs';
import { rasterizeNativeVehicleTriangle } from './mc3-vehicle-raster.mjs';
import { rasterizeNativeVehicleSprite } from './mc3-vehicle-sprite.mjs';
import { createNativeVehicleSampler } from './mc3-vehicle-sampler.mjs';
import { createNativeVehicleConstantMipSampler } from './mc3-vehicle-mip.mjs';
import { createNativeVehicleVariableMipSampler } from './mc3-vehicle-variable-mip.mjs';
import { nativeTextureFunction, nativeVehicleFragment } from './mc3-vehicle-fragment.mjs';

const bits = new DataView(new ArrayBuffer(4));
const float = (word) => { bits.setUint32(0, word, true); return bits.getFloat32(0, true); };
const field = (value, shift, width) => Number((value >> BigInt(shift)) & ((1n << BigInt(width)) - 1n));
const mask = (shift, width) => ((1n << BigInt(width)) - 1n) << BigInt(shift);
const primClass = (p) => [0, 1, 1, 2, 2, 2, 3, 4][p & 7];
const contextRegisters = (p) => {
  const c = (p >> 9) & 1;
  return { tex0: 6 + c, clamp: 8 + c, tex1: 0x14 + c, xy: 0x18 + c,
    scissor: 0x40 + c, alpha: 0x42 + c, test: 0x47 + c,
    fba: 0x4a + c, frame: 0x4c + c, zbuf: 0x4e + c, mip1: 0x34 + c, mip2: 0x36 + c };
};
const masks = new Map([[0x18, mask(0, 16) | mask(32, 16)], [0x40, mask(0, 11) | mask(16, 11) | mask(32, 11) | mask(48, 11)],
  [0x42, mask(0, 8) | mask(32, 8)], [0x47, mask(0, 19)], [0x4c, mask(0, 9) | mask(16, 6) | mask(24, 6) | mask(32, 32)],
  [0x4e, mask(0, 9) | mask(24, 4) | mask(32, 1)], [0x08, mask(0, 44)],
  [0x14, mask(0, 1) | mask(2, 8) | mask(19, 2) | mask(32, 12)],
  [0x22, 3n], [0x45, 1n], [0x46, 1n], [0x49, 1n], [0x4a, 1n],
  [0x3b, 0xff000080ffn], [0x3d, 0xffffffn], [0x44, 0x7777777777777777n],
  [0x34, mask(0, 60)], [0x36, mask(0, 60)]]);
function sameRegister(a, b, address, canonical = address) {
  const x = a.get(address), y = b.get(address), m = masks.get(canonical);
  return x === undefined || y === undefined ? x === y : m === undefined ? x === y : (x & m) === (y & m);
}

// GSState::TestDrawChanged, fd9d310. Ignore unused state changes rather than
// splitting a draw and accidentally changing constant-Q dispatch/rounding.
function drawChanged(a, p, b, q) {
  if (primClass(p) !== primClass(q) || ((p ^ q) & ~7)) return true;
  const r = contextRegisters(p);
  for (const [address, canonical] of [[r.test, 0x47], [r.scissor, 0x40], [r.xy, 0x18], [0x22, 0x22], [0x45, 0x45]]) {
    if (!sameRegister(a, b, address, canonical)) return true;
  }
  if (((a.get(0x45) ?? 0n) & 1n) && !sameRegister(a, b, 0x44)) return true;
  if ((p & 64) && (!sameRegister(a, b, r.alpha, 0x42) || !sameRegister(a, b, 0x49))) return true;
  if ((p & 32) && !sameRegister(a, b, 0x3d)) return true;
  const test = a.get(r.test), never = test !== undefined && field(test, 0, 1) && field(test, 1, 3) === 0;
  const fail = test === undefined ? 0 : field(test, 12, 2), date = test === undefined ? false : field(test, 14, 1);
  if ((!never || (fail & 1) || date) && (!sameRegister(a, b, r.frame, 0x4c)
    || !sameRegister(a, b, 0x46) || !sameRegister(a, b, r.fba, 0x4a))) return true;
  if ((!never || fail === 2) && !sameRegister(a, b, r.zbuf, 0x4e)) return true;
  if (p & 16) {
    for (const [address, canonical] of [[r.tex0, 6], [r.tex1, 0x14], [r.clamp, 8], [0x3b, 0x3b]]) {
      if (!sameRegister(a, b, address, canonical)) return true;
    }
    const tex1 = a.get(r.tex1);
    if (tex1 !== undefined && field(tex1, 2, 3) > 0
      && (!sameRegister(a, b, r.mip1, 0x34) || !sameRegister(a, b, r.mip2, 0x36))) return true;
  }
  return false;
}

function concatenate(chunks) {
  if (chunks instanceof Uint8Array) return chunks;
  if (!Array.isArray(chunks) || chunks.some((c) => !(c instanceof Uint8Array))) throw new Error('Invalid native GIF chunks');
  const bytes = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}

// Keep original words in events/rawStqWords. The separate effective Q follows
// the selected pinned software GS's explicit zero/NaN transport handling.
function qWord(word, packed) {
  if (word === 0) return packed ? 0x00800000 : 0x3f800000;
  return (word & 0x7f800000) === 0x7f800000 && (word & 0x7fffff) ? 0x7f7fffff : word;
}

export function decodeNativeVehicleGIF(chunks, { initialRegisters, allowImages = false } = {}) {
  if (typeof allowImages !== 'boolean') throw new Error('Explicit native IMAGE transport mode must be boolean');
  if (!(initialRegisters instanceof Map) || !initialRegisters.has(0x1a)) {
    throw new Error('Explicit initial GS registers including PRMODECONT are required');
  }
  const registers = new Map(initialRegisters);
  for (const [address, value] of registers) {
    if (!Number.isInteger(address) || address < 0 || address > 127 || typeof value !== 'bigint' || value < 0n || value > 0xffffffffffffffffn) {
      throw new Error('Invalid native GS initial register');
    }
  }
  const bytes = concatenate(chunks);
  if (bytes.length % 16) throw new Error('Truncated native GIF stream');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const events = [], vertices = [], draws = [], operations = [];
  let offset = 0, primitive = registers.has(0) ? field(registers.get(0), 0, 11) : undefined;
  let history = [], draw, imageBoundary, stWords, rgba, rawQ, effectiveQ, uv, fog, latchQ = 0x3f800000;
  // GSState::VertexKick keeps a separate native source buffer. Indexed bounds
  // omit culled/ADC primitives, but CorrectDepthTrace scans this compacted
  // buffer, including unused trailing vertices until ApplyPRIM trims them.
  let sourceBuffer = [], sourceHead = 0, sourceNext = 0;
  function traceSource() { if (draw) draw.sourceVertexIndices = [...sourceBuffer]; }
  function flushSource() {
    traceSource();
    const type = primitive & 7, tail = sourceBuffer.length;
    const unused = tail > sourceHead ? ([1, 2, 6].includes(type) ? 1
      : [3, 4].includes(type) ? Math.min(tail - sourceHead, 2) : type === 5 ? Math.min(tail - sourceHead, 2) : 0) : 0;
    sourceBuffer = !unused ? [] : type === 5 ? [sourceBuffer[sourceHead], ...(unused > 1 ? [sourceBuffer.at(-1)] : [])]
      : sourceBuffer.slice(-unused);
    sourceNext = unused && sourceNext > sourceHead ? sourceNext - sourceHead : 0;
    sourceHead = 0;
  }
  function nativeCull(indices) {
    const type = primitive & 7, r = contextRegisters(primitive), xy = registers.get(r.xy), sc = registers.get(r.scissor);
    // Missing render state is rejected by the renderer; transport decoding can
    // still expose raw vertices without inventing a culling context.
    if (xy === undefined || sc === undefined || ![3, 4, 5, 6].includes(type)) return false;
    const xyOffset = [field(xy, 0, 16), field(xy, 32, 16)];
    const scissor = [field(sc, 0, 11), field(sc, 32, 11), field(sc, 16, 11) + 1, field(sc, 48, 11) + 1];
    if (scissor[0] >= scissor[2] || scissor[1] >= scissor[3]) return true;
    const points = indices.map((i) => vertices[i]);
    if (type !== 6) return !intersectsGSScissor(points, { xyOffset, scissor });
    const xs = points.map((v) => v.xy[0] - xyOffset[0]), ys = points.map((v) => v.xy[1] - xyOffset[1]);
    const box = [(Math.min(...xs) + 15) & ~15, (Math.min(...ys) + 15) & ~15,
      ((Math.max(...xs) - 1) & ~15) + 1, ((Math.max(...ys) - 1) & ~15) + 1];
    return box[0] >= box[2] || box[1] >= box[3] || box[0] >= (scissor[2] - 1) * 16 + 8
      || box[1] >= (scissor[3] - 1) * 16 + 8 || box[2] + 1 <= scissor[0] * 16 - 8 || box[3] + 1 <= scissor[1] * 16 - 8;
  }
  if (!(registers.get(0x1a) & 1n) && primitive === undefined) throw new Error('Explicit initial effective PRIM is required in PRMODE');
  if (registers.has(1)) {
    const word = registers.get(1);
    rgba = [0, 8, 16, 24].map((n) => field(word, n, 8));
    rawQ = field(word, 32, 32); effectiveQ = qWord(rawQ, false);
  }
  if (registers.has(2)) stWords = [field(registers.get(2), 0, 32), field(registers.get(2), 32, 32)];
  if (registers.has(3)) uv = [field(registers.get(3), 0, 14), field(registers.get(3), 16, 14)];
  if (registers.has(10)) fog = field(registers.get(10), 56, 8);
  function applyPrim(value) {
    const ac = registers.get(0x1a) & 1n;
    primitive = ac ? field(value, 0, 11) : ((primitive ?? 0) & ~7) | field(value, 0, 3);
    sourceBuffer.length = sourceNext;
    sourceHead = sourceNext;
    traceSource();
    history = [];
  }
  function vertex(xy, z, nextFog, skip, sourceOffset) {
    if (primitive === undefined || rgba === undefined) throw new Error('Native GIF vertex has unresolved PRIM/RGBAQ');
    if (draw && drawChanged(draw.registers, draw.primitive, registers, primitive)
      && (!skip || primClass(draw.primitive) !== primClass(primitive)
        || !sameRegister(draw.registers, registers, contextRegisters(primitive).xy, 0x18))) {
      flushSource(); draw = undefined;
    }
    const index = vertices.length;
    vertices.push({ xy, z, rgba: [...rgba], stq: stWords ? [...stWords.map(float), float(effectiveQ)] : undefined,
      rawStqWords: stWords ? [...stWords, rawQ] : undefined, uv: uv ? [...uv] : undefined,
      fog: nextFog, adc: skip, offset: sourceOffset });
    history.push(index);
    sourceBuffer.push(index);
    const type = primitive & 7, count = [1, 2, 2, 3, 3, 3, 2, 0][type];
    if (!count) throw new Error('Unsupported native GIF primitive type');
    if (history.length < count) { traceSource(); return; }
    const indices = type === 5 ? [history[0], history.at(-2), index] : history.slice(-count);
    const culled = nativeCull(indices);
    if (skip || culled) {
      if ([0, 1, 3, 6].includes(type)) sourceBuffer.length = sourceHead;
      else if ([2, 4].includes(type)) sourceHead++;
    } else if ([2, 4].includes(type)) {
      if (sourceNext < sourceHead) {
        const compact = sourceBuffer.slice(sourceHead, sourceHead + count);
        sourceBuffer.splice(sourceNext, sourceBuffer.length - sourceNext, ...compact);
        sourceHead = sourceNext;
      }
      sourceNext = sourceHead + count;
      sourceHead++;
    } else if (type === 5) sourceNext = sourceBuffer.length;
    else sourceHead = sourceNext = sourceHead + count;
    if (!skip) {
      if (!draw || drawChanged(draw.registers, draw.primitive, registers, primitive)) {
        if (imageBoundary && !drawChanged(imageBoundary.registers, imageBoundary.primitive, registers, primitive)) {
          throw new Error('Unresolved native IMAGE write spanning an otherwise unchanged draw group');
        }
        imageBoundary = undefined;
        draw = { primitive, registers: new Map(registers), indices: [], primitives: [], sourceVertexIndices: [] };
        draws.push(draw);
        operations.push({ kind: 'draw', draw });
      }
      draw.indices.push(...indices);
      draw.primitives.push({ primitive, indices: [...indices], offset: sourceOffset });
    }
    traceSource();
    if ([0, 1, 3, 6].includes(type)) history = [];
  }
  function write(address, value, packed, sourceOffset) {
    if (allowImages && [0x16, 0x17, 0x54].includes(address)) {
      throw new Error('Unsupported native VRAM TEX2/HWREG side effect');
    }
    // A CLUT load may change texture contents even when TEX0 compares equal.
    // Until overlap-aware GS flushing is recovered, do not merge primitives
    // across this side effect under an otherwise unchanged draw state.
    if (allowImages && [6, 7].includes(address) && field(value, 61, 3) !== 0) {
      imageBoundary ??= draw;
      if (draw) flushSource();
      draw = undefined;
    }
    if ([6, 7, 0x50, 0x51, 0x52, 0x53].includes(address)) operations.push({ kind: 'register', address, value });
    const low = Number(value & 0xffffffffn), high = Number(value >> 32n);
    const lo = (shift, width) => field(value, shift, width);
    if (address === 0) applyPrim(value);
    else if (address === 1 || address === 0x11) {
      rgba = [0, 8, 16, 24].map((n) => (low >>> n) & 255);
      rawQ = high; effectiveQ = qWord(high, false);
    } else if (address === 2) stWords = [low, high];
    else if (address === 3) uv = [lo(0, 14), lo(16, 14)];
    else if ([4, 5, 12, 13].includes(address)) {
      const hasFog = address === 4 || address === 12;
      if (hasFog) fog = high >>> 24;
      vertex([low & 65535, low >>> 16], hasFog ? high & 0xffffff : high, fog, address >= 12, sourceOffset);
    } else if (address === 10) fog = lo(56, 8);
    else if (address === 0x1b && !(registers.get(0x1a) & 1n)) primitive = (primitive & 7) | (low & 0x7f8);
    registers.set(address, address === 0 ? BigInt(primitive) : value);
    if (address === 0x1b && !(registers.get(0x1a) & 1n)) registers.set(0, BigInt(primitive));
    if (address === 1 || address === 0x11) registers.set(1, (value & 0xffffffffn) | BigInt(effectiveQ) << 32n);
    if (!packed) events.push({ kind: 'register', address, value, offset: sourceOffset });
  }
  while (offset < bytes.length) {
    const start = offset, tag = view.getBigUint64(offset, true), list = view.getBigUint64(offset + 8, true);
    offset += 16;
    const loops = field(tag, 0, 15), format = field(tag, 58, 2), nreg = field(tag, 60, 4) || 16;
    const regList = Array.from({ length: nreg }, (_, i) => field(list, i * 4, 4));
    events.push({ kind: 'tag', value: tag, registers: list, offset: start });
    if (!loops) continue;
    if (format > 1) {
      if (!allowImages || format !== 2) throw new Error('Native GIF IMAGE requires external VRAM transfer support');
      const end = offset + loops * 16;
      if (end > bytes.length) throw new Error('Truncated native GIF IMAGE payload');
      operations.push({ kind: 'image', data: bytes.slice(offset, end) });
      // Upload overlap can drain native pending draws. This bounded transport
      // accepts a following independently changed draw state; unchanged groups
      // across an upload need the separate native overlap/flush scheduler.
      imageBoundary ??= draw;
      if (draw) flushSource();
      draw = undefined;
      offset = end;
      continue;
    }
    const end = offset + Math.ceil(loops * nreg * (format === 0 ? 16 : 8) / 16) * 16;
    if (end > bytes.length) throw new Error('Truncated native GIF payload');
    latchQ = 0x3f800000;
    if (format === 0 && field(tag, 46, 1)) write(0, BigInt(field(tag, 47, 11)), false, start);
    for (let i = 0; i < loops * nreg; i++) {
      const address = regList[i % nreg], value = view.getBigUint64(offset, true), at = offset;
      if (format === 1) {
        if (address === 14) throw new Error('Unsupported native GIF REGLIST A+D');
        if (address !== 15) write(address, value, false, at);
        offset += 8;
        continue;
      }
      const upper = view.getBigUint64(offset + 8, true);
      events.push({ kind: 'packed', address, value, upper, offset: at });
      if (address === 14) write(Number(upper & 127n), value, false, at);
      else if (address === 1) {
        rgba = [0, 4, 8, 12].map((n) => view.getUint8(at + n));
        rawQ = latchQ; effectiveQ = qWord(latchQ, true);
        registers.set(1, rgba.reduce((n, c, i) => n | BigInt(c) << BigInt(i * 8), BigInt(effectiveQ) << 32n));
      } else if (address === 2) {
        stWords = [view.getUint32(at, true), view.getUint32(at + 4, true)];
        latchQ = view.getUint32(at + 8, true);
        registers.set(2, value);
      } else if (address === 3) {
        uv = [field(value, 0, 14), field(value, 32, 14)];
        registers.set(3, BigInt(uv[0]) | BigInt(uv[1]) << 16n);
      }
      else if ([4, 5, 12, 13].includes(address)) {
        const z = view.getUint32(at + 8, true), last = view.getUint32(at + 12, true);
        const hasFog = address === 4 || address === 12;
        if (hasFog) fog = (last >>> 4) & 255;
        vertex([view.getUint16(at, true), view.getUint16(at + 4, true)], hasFog ? (z >>> 4) & 0xffffff : z,
          fog, address >= 12 || !!(last & 0x8000), at);
      } else if (address === 10) {
        fog = field(upper, 36, 8); registers.set(10, BigInt(fog) << 56n);
      }
      else if (address !== 15) write(address, value, true, at);
      offset += 16;
    }
    offset = end;
  }
  return { events, vertices, draws, operations, initialRegisters: new Map(initialRegisters), registers, bytes, effectivePrimitive: primitive,
    vertexState: { rgba, stWords, rawQ, effectiveQ, uv, fog, latchQ } };
}

function required(registers, address) {
  const value = registers.get(address);
  if (value === undefined) throw new Error(`Unresolved native GS register 0x${address.toString(16)}`);
  return value;
}

// target explicitly identifies the single native framebuffer/depth binding:
// {fbp,fbw,zbp,width,height,rgba:Uint8Array,depth:Uint16Array}. Its initial
// contents are caller-owned. resolveTexture(tex0,{tex1,clamp,texa,...}) must
// return the actual bound native RGBA base image with readOnly:true. There is
// no fabricated VRAM image, color-space conversion or unresolved fallback.
export function renderNativeVehicleGIF(decoded, { target, resolveTexture } = {}) {
  if (!target || !Number.isInteger(target.width) || !Number.isInteger(target.height)
    || target.width < 1 || target.height < 1 || !(target.rgba instanceof Uint8Array)
    || !(target.depth instanceof Uint16Array || target.depth instanceof Uint32Array) || target.rgba.length !== target.width * target.height * 4
    || target.depth.length !== target.width * target.height) throw new Error('Explicit native framebuffer/depth target is required');
  for (const name of ['fbp', 'fbw', 'zbp']) if (!Number.isInteger(target[name])) throw new Error('Explicit native target binding is required');
  const stats = { draws: 0, triangles: 0, sprites: 0, pixels: 0 };
  for (const [drawIndex, draw] of decoded.draws.entries()) {
    const p = draw.primitive, r = contextRegisters(p), regs = draw.registers;
    const sprite = primClass(p) === 3;
    if (!sprite && primClass(p) !== 2) throw new Error('Unsupported native vehicle raster primitive');
    const frame = required(regs, r.frame), zbuf = required(regs, r.zbuf), test = required(regs, r.test);
    const depthFormat = field(zbuf, 24, 4), depthBits = depthFormat === 0 ? 32 : 16;
    if (field(frame, 24, 6) !== 0 || ![0, 10].includes(depthFormat)) throw new Error('Unsupported native framebuffer/depth format');
    if (!(target.depth instanceof (depthBits === 32 ? Uint32Array : Uint16Array))) throw new Error('Native depth storage differs from ZBUF format');
    if (field(frame, 0, 9) !== target.fbp || field(frame, 16, 6) !== target.fbw || field(zbuf, 0, 9) !== target.zbp) {
      throw new Error('Native draw target binding differs');
    }
    const xy = required(regs, r.xy), sc = required(regs, r.scissor);
    const xyOffset = [field(xy, 0, 16), field(xy, 32, 16)];
    const scissor = [field(sc, 0, 11), field(sc, 32, 11), field(sc, 16, 11) + 1, field(sc, 48, 11) + 1];
    if (scissor[2] > target.width || scissor[3] > target.height) throw new Error('Native scissor exceeds explicit target');
    if (field(required(regs, 0x22), 0, 2)) throw new Error('Unsupported native scan mask');
    const abe = !!(p & 64), alpha = abe ? required(regs, r.alpha) : 0n;
    const state = { framebuffer: 'PSMCT32', depthFormat: depthBits === 32 ? 'PSMZ32' : 'PSMZ16S', fbmask: field(frame, 32, 32),
      ate: !!field(test, 0, 1), atst: field(test, 1, 3), aref: field(test, 4, 8), afail: field(test, 12, 2),
      date: !!field(test, 14, 1), datm: field(test, 15, 1), zte: !!field(test, 16, 1), ztst: field(test, 17, 2),
      zmsk: !!field(zbuf, 32, 1), abe, pabe: !!field(required(regs, 0x49), 0, 1),
      fba: !!field(required(regs, r.fba), 0, 1), colclamp: !!field(required(regs, 0x46), 0, 1),
      aa1: !!(p & 128), fge: !!(p & 32), dthe: !!field(required(regs, 0x45), 0, 1),
      blend: [field(alpha, 0, 2), field(alpha, 2, 2), field(alpha, 4, 2), field(alpha, 6, 2), field(alpha, 32, 8)] };
    if (state.aa1 || state.fge || state.dthe) throw new Error('Unsupported native AA/fog/dither');
    const textured = !!(p & 16), fixedUV = !!(p & 256);
    if (sprite && textured && !fixedUV) throw new Error('Unsupported native sprite STQ profile');
    const active = draw.primitives.filter((item) => sprite || intersectsGSScissor(item.indices.map((i) => decoded.vertices[i]), { xyOffset, scissor }));
    if (!active.length) continue;
    const referenced = [...new Set(active.flatMap((item) => item.indices))];
    const sourceVertices = referenced.map((i) => decoded.vertices[i]);
    let bilinear = true, mipPlan, variableMip = false;
    let image, sample, tex0, tex1, clamp, tfx = 4, tcc = true, textureSize = [1, 1];
    if (textured) {
      tex0 = required(regs, r.tex0); tex1 = required(regs, r.tex1); clamp = required(regs, r.clamp);
      const mipLevels = field(tex1, 2, 3);
      if (mipLevels && fixedUV) throw new Error('Unsupported native fixed-UV mip profile');
      if (mipLevels && !field(tex1, 0, 1) && (field(tex1, 6, 3) < 2 || field(tex1, 6, 3) > 5)) throw new Error('Unsupported native mip/nearest sampling profile');
      bilinear = !!field(tex1, 5, 1);
      const psm = field(tex0, 20, 6), cpsm = field(tex0, 51, 4);
      if (![0, 19, 20].includes(psm) || (psm !== 0 && cpsm !== 0)) throw new Error('Unsupported native texture alpha expansion');
      if (typeof resolveTexture !== 'function') throw new Error('Native texture binding resolver is required');
      textureSize = [2 ** field(tex0, 26, 4), 2 ** field(tex0, 30, 4)];
      image = resolveTexture(tex0, { tex1, clamp, texa: regs.get(0x3b), primitive: p, registers: regs, drawIndex });
      if (!image || image.readOnly !== true || image.width !== textureSize[0] || image.height !== textureSize[1]
        || !(image.data instanceof Uint8Array) || image.data.length !== image.width * image.height * 4) {
        throw new Error('Unresolved native texture image or feedback dependency');
      }
      tfx = field(tex0, 35, 2); tcc = !!field(tex0, 34, 1);
      if (mipLevels) {
        variableMip = !field(tex1, 0, 1);
        const qs = sourceVertices.map(v => v.stq?.[2]);
        mipPlan = variableMip ? createNativeVehicleVariableMipSampler({levels:image.levels,tex1,clamp,
          drawTrace:{qMin:Math.min(...qs),qMax:Math.max(...qs)}})
          : createNativeVehicleConstantMipSampler({ levels: image.levels, tex1, clamp });
        // Native mip sampling shifts the unbiased converted coordinate before
        // subtracting half a texel; STQ is divided per pixel even for flat Q.
        bilinear = false;
        sample = (u, v, x, q) => mipPlan.sample(u, v, variableMip ? q : x);
      } else sample = createNativeVehicleSampler({ image, tex1, clamp });
    }
    const q = sourceVertices[0].stq?.[2];
    const constantQ = !textured || fixedUV || !mipPlan && sourceVertices.every((v) => v.stq?.[2] === q);
    // GSVertexTrace computes float32 bounds from indexed vertices, then its
    // depth correction scans the source vertex buffer (including ADC history).
    let zEqual = sourceVertices.every((v) => Math.fround(v.z) === Math.fround(sourceVertices[0].z));
    if (zEqual && state.zte && state.ztst > 1) {
      const raw = draw.sourceVertexIndices.map((i) => decoded.vertices[i].z), first = raw[0];
      zEqual = raw.reduce((z, value) => first & 1 ? (z & value) >>> 0 : (z | value) >>> 0, first) === first;
    }
    const zOverflow = sourceVertices.some((v) => Math.fround(v.z) >= 2147483648);
    const converted = new Map(referenced.map((i) => {
      const v = decoded.vertices[i];
      let stq = v.stq;
      if (!textured) stq = [0, 0, 1]; // This GS draw never reads STQ.
      else if (fixedUV) {
        if (!v.uv) throw new Error('Unresolved native fixed UV');
        stq = [v.uv[0] / (16 * textureSize[0]), v.uv[1] / (16 * textureSize[1]), 1];
      } else if (!stq) throw new Error('Unresolved native STQ');
      else if (zEqual) stq = roundGSSTQ(stq);
      return [i, { ...v, stq }];
    }));
    stats.draws++;
    for (const item of active) {
      stats[sprite ? 'sprites' : 'triangles']++;
      const rasterize = sprite ? rasterizeNativeVehicleSprite : rasterizeNativeVehicleTriangle;
      rasterize(item.indices.map((i) => converted.get(i)), {
        xyOffset, scissor, textureSize, constantQ, textured, depthBits, bilinear, emitQ: variableMip, zEqual, zOverflow, gouraud: !!(p & 8), onPixel(x, y, pixel) {
          const source = nativeTextureFunction({ vertex128: pixel.vertex128,
            texture: textured ? sample(pixel.u, pixel.v, x, pixel.q) : null, tfx, tcc });
          const index = y * target.width + x, destination = Array.from(target.rgba.subarray(index * 4, index * 4 + 4));
          const out = nativeVehicleFragment({ source, destination, z: pixel.z, destinationZ: target.depth[index], state });
          target.rgba.set(out.rgba, index * 4); target.depth[index] = out.z; stats.pixels++;
        } });
    }
  }
  return stats;
}
