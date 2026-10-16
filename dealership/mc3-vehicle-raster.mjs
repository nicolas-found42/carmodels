// Selected pinned software-GS AVX2 Gouraud arithmetic. Coverage/STQ/Z keep
// using the independently validated capture raster; no capture code changes.
import { fusedGSFloat32, rasterizeGSTriangle } from './mc3-gs-raster.mjs';

const f = Math.fround;
const sub = (a, b) => f(a - b), mul = (a, b) => f(a * b), div = (a, b) => f(a / b);
const signed16 = (v) => (v << 16) >> 16;
const sorted = [[0, 1, 2], [1, 0, 2], [0, 0, 0], [1, 2, 0], [0, 2, 1], [0, 0, 0], [2, 0, 1], [2, 1, 0]];

// Input vertices are decoded native GS vertices (xy16.4, Z, STQ, RGBAQ bytes).
// Flat color uses the original third vertex. Gouraud interpolation is affine
// in screen coordinates, independent of Q; vertex128 retains seven fraction
// bits, including the signed16 wrapping of the selected GS implementation.
export function rasterizeNativeVehicleTriangle(vertices, state) {
  if (typeof state?.gouraud !== 'boolean' || typeof state.onPixel !== 'function'
    || !Array.isArray(state.xyOffset) || state.xyOffset.length !== 2) {
    throw new Error('Explicit native vehicle raster shading state is required');
  }
  if (!Array.isArray(vertices) || vertices.length !== 3 || vertices.some((v) =>
    !Array.isArray(v.rgba) || v.rgba.length !== 4 || v.rgba.some((n) => !Number.isInteger(n) || n < 0 || n > 255))) {
    throw new Error('Invalid native vehicle raster RGBAQ');
  }
  if (!state.gouraud) {
    const vertex128 = vertices[2].rgba.map((n) => n * 128);
    rasterizeGSTriangle(vertices, { ...state, onPixel: (x, y, pixel) =>
      state.onPixel(x, y, { ...pixel, vertex128: [...vertex128] }) });
    return;
  }
  const cv = vertices.map((v) => ({ x: f((v.xy[0] - state.xyOffset[0]) / 16),
    y: f((v.xy[1] - state.xyOffset[1]) / 16), color: v.rgba.map((c) => c * 128) }));
  const order = (cv[0].y > cv[1].y ? 1 : 0) | (cv[0].y > cv[2].y ? 2 : 0) | (cv[1].y > cv[2].y ? 4 : 0);
  const [a, b, c] = sorted[order].map((i) => cv[i]);
  const dx0 = sub(b.x, a.x), dy0 = sub(b.y, a.y), dx1 = sub(c.x, a.x), dy1 = sub(c.y, a.y);
  const cross = sub(mul(dy0, dx1), mul(dx0, dy1));
  if (!cross) return;
  const nx0 = div(dx0, cross), ny0 = div(dy0, cross), nx1 = div(dx1, cross), ny1 = div(dy1, cross);
  const tx = a.color.map((n, i) => fusedGSFloat32(sub(c.color[i], n), ny0, -mul(sub(b.color[i], n), ny1)));
  const ty = a.color.map((n, i) => fusedGSFloat32(sub(b.color[i], n), nx1, -mul(sub(c.color[i], n), nx0)));
  const step = tx.map((n) => signed16(Math.trunc(mul(n, 8))));
  let row = -1, block = 0, lanes;
  rasterizeGSTriangle(vertices, { ...state, onPixel: (x, y, pixel) => {
    if (row !== y) {
      row = y;
      const anchor = a.y === b.y ? (cross < 0 ? a : b) : y < Math.ceil(b.y) ? a : b;
      const dy = sub(y, anchor.y), prestep = sub(x, anchor.x), skip = x & 7;
      const scan = anchor.color.map((n, i) => Math.trunc(fusedGSFloat32(tx[i], prestep, fusedGSFloat32(ty[i], dy, n))));
      block = x - skip;
      lanes = Array.from({ length: 8 }, (_, lane) => scan.map((n, i) =>
        signed16(n + Math.trunc(mul(tx[i], lane - skip)))));
    }
    while (x >= block + 8) {
      for (const lane of lanes) for (let i = 0; i < 4; i++) lane[i] = Math.max(0, signed16(lane[i] + step[i]));
      block += 8;
    }
    state.onPixel(x, y, { ...pixel, vertex128: [...lanes[x - block]] });
  } });
}
