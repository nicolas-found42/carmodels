// Selected PCSX2 v2.8.2 software-GS base-level sampling. GSVertexTrace::Update
// explicitly ignores MMIN when MXL=0 and uses MMAG. The caller supplies the
// filter-specific signed16.16 coordinates produced by the native GS raster.
// This does not implement LOD or mip selection.
function need(value, message) { if (!value) throw new Error(message); }
const field = (value, shift, width) => Number(value >> BigInt(shift) & ((1n << BigInt(width)) - 1n));
const signed16 = (value) => (value << 16) >> 16;

export function createNativeVehicleSampler({ image, tex1, clamp } = {}) {
  for (const value of [tex1, clamp]) need(typeof value === 'bigint' && value >= 0n && value <= 0xffffffffffffffffn,
    'Explicit native TEX1/CLAMP words are required');
  need(field(tex1, 2, 3) === 0, 'Unsupported native mip/nearest coordinate profile');
  const bilinear = field(tex1, 5, 1) === 1;
  const { width, height, data } = image ?? {};
  need([width, height].every((n) => Number.isInteger(n) && n >= 1 && n <= 1024 && !(n & (n - 1)))
    && data instanceof Uint8Array && data.length === width * height * 4 && image.readOnly === true,
  'Explicit read-only native RGBA image is required');
  const modes = [field(clamp, 0, 2), field(clamp, 2, 2)];
  const minimum = [field(clamp, 4, 10), field(clamp, 24, 10)];
  const maximum = [field(clamp, 14, 10), field(clamp, 34, 10)];
  const sizes = [width, height];
  for (let axis = 0; axis < 2; axis++) {
    if (modes[axis] >= 2) need(maximum[axis] < sizes[axis]
      && (modes[axis] !== 2 || minimum[axis] <= maximum[axis]),
    'Native region sampling outside supplied image requires an explicit VRAM view');
  }
  function bound(value, axis) {
    const size = sizes[axis];
    switch (modes[axis]) {
      case 0: return value & (size - 1);
      case 1: return Math.min(Math.max(value, 0), size - 1);
      case 2: return Math.min(Math.max(value, minimum[axis]), maximum[axis]);
      case 3: return (value & (minimum[axis] & (size - 1))) | maximum[axis];
    }
  }
  return function sample(u, v) {
    need([u, v].every((n) => Number.isInteger(n) && n >= -2147483648 && n <= 2147483647),
      'Native sampler requires filter-specific signed16.16 coordinates');
    const x = u >> 16, y = v >> 16, fx = u >>> 12 & 15, fy = v >>> 12 & 15;
    const at = (xx, yy, channel) => data[(bound(yy, 1) * width + bound(xx, 0)) * 4 + channel];
    if (!bilinear) return [0, 1, 2, 3].map((channel) => at(x, y, channel));
    const xx = signed16(x + 1), yy = signed16(y + 1);
    return [0, 1, 2, 3].map((channel) => {
      const a = (at(x, y, channel) * (16 - fx) + at(xx, y, channel) * fx) >> 4;
      const b = (at(x, yy, channel) * (16 - fx) + at(xx, yy, channel) * fx) >> 4;
      return (a * (16 - fy) + b * fy) >> 4;
    });
  };
}
