// Explicit, bounded GS fragment arithmetic. Raster coverage, interpolation,
// texture sampling and material-state selection belong to the caller.
// Reference: PCSX2 v2.8.2 fd9d310, software GS AlphaTFX/TestAlpha/
// ColorTFX/TestDestAlpha/AlphaBlend/WriteFrame and GSRendererSW masks.
const byte = (v) => Math.max(0, Math.min(255, v));

function integer(value, min, max, name) {
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new Error(`Invalid native fragment ${name}`);
  }
  return value;
}

function flag(value, name) {
  if (typeof value !== 'boolean') throw new Error(`Invalid native fragment ${name}`);
  return value;
}

function vector(value, max, name) {
  if (!value || value.length !== 4) throw new Error(`Invalid native fragment ${name}`);
  return Array.from(value, (v) => integer(v, 0, max, name));
}

// vertex128 retains the software GS's seven fractional color bits. For a
// literal native RGBAQ byte use byte*128; do not round interpolated lanes first.
export function nativeTextureFunction({ vertex128, texture, tfx, tcc }) {
  const v = vector(vertex128, 32767, 'vertex128');
  integer(tfx, 0, 4, 'tfx'); // 4 is untextured (TFX_NONE).
  flag(tcc, 'tcc');
  const base = v.map((c) => c >> 7);
  if (tfx === 4) return base;
  const t = vector(texture, 255, 'texture');
  const modulated = t.map((c, i) => Math.floor(c * v[i] / 16384));
  let rgb;
  if (tfx === 1) rgb = t.slice(0, 3);
  else if (tfx === 0) rgb = modulated.slice(0, 3).map(byte);
  else rgb = modulated.slice(0, 3).map((c) => byte(c + base[3]));
  const alpha = !tcc ? base[3] : tfx === 0 ? byte(modulated[3])
    : tfx === 2 ? byte(t[3] + base[3]) : t[3];
  return [...rgb, alpha];
}

function alphaPass(alpha, test, reference) {
  switch (test) {
    case 0: return false;
    case 1: return true;
    case 2: return alpha < reference;
    case 3: return alpha <= reference;
    case 4: return alpha === reference;
    case 5: return alpha >= reference;
    case 6: return alpha > reference;
    case 7: return alpha !== reference;
  }
}

// state contains literal fields, with no implicit engine/render defaults:
// framebuffer='PSMCT32', depthFormat='PSMZ16S' or 'PSMZ32', fbmask=u32;
// ate,atst,aref,afail,date,datm,zte,ztst,zmsk,abe,pabe,fba,colclamp;
// aa1,fge,dthe must explicitly be false (not supported by this stage).
// blend=[A,B,C,D,FIX], A/B/D:Cs,Cd,zero; C:As,Ad,FIX.
// source is post-TFX native RGBA, destination is the stored native RGBA.
export function nativeVehicleFragment({ source, destination, z, destinationZ, state }) {
  const s = vector(source, 255, 'source');
  const d = vector(destination, 255, 'destination');
  if (state?.framebuffer !== 'PSMCT32' || !['PSMZ16S', 'PSMZ32'].includes(state.depthFormat)) {
    throw new Error('Unsupported native fragment framebuffer/depth profile');
  }
  for (const name of ['ate', 'date', 'zte', 'zmsk', 'abe', 'pabe', 'fba', 'colclamp']) {
    flag(state[name], name);
  }
  for (const name of ['aa1', 'fge', 'dthe']) {
    flag(state[name], name);
    if (state[name]) throw new Error(`Unsupported native fragment ${name}`);
  }
  integer(state.atst, 0, 7, 'atst');
  integer(state.aref, 0, 255, 'aref');
  integer(state.afail, 0, 3, 'afail');
  integer(state.datm, 0, 1, 'datm');
  integer(state.ztst, 0, 3, 'ztst');
  integer(state.fbmask, 0, 0xffffffff, 'fbmask');
  const b = state.blend;
  if (!b || b.length !== 5) throw new Error('Invalid native fragment blend');
  for (let i = 0; i < 4; i++) integer(b[i], 0, 2, 'blend selector');
  integer(b[4], 0, 255, 'FIX');
  integer(z, 0, 0xffffffff, 'z');
  const maximumZ = state.depthFormat === 'PSMZ32' ? 0xffffffff : 65535;
  integer(destinationZ, 0, maximumZ, 'destinationZ');
  const zs = Math.min(z, maximumZ);
  let mask = state.fbmask >>> 0;
  let depthWrite = state.zte && !state.zmsk;
  let rejected = state.date && (d[3] >> 7) !== state.datm;
  if (state.zte) {
    rejected ||= state.ztst === 0 || (state.ztst === 2 && zs < destinationZ)
      || (state.ztst === 3 && zs <= destinationZ);
  }
  if (state.ate && !alphaPass(s[3], state.atst, state.aref)) {
    if (state.afail === 0) rejected = true;
    else if (state.afail === 1) depthWrite = false;
    else if (state.afail === 2) mask = 0xffffffff;
    else { mask = (mask | 0xff000000) >>> 0; depthWrite = false; }
  }
  if (rejected) return { rgba: d, z: destinationZ, framebufferWrite: false, depthWrite: false };
  const rgb = s.slice(0, 3);
  if (state.abe && (!state.pabe || (s[3] & 128))) {
    const factor = [s[3], d[3], b[4]][b[2]];
    for (let i = 0; i < 3; i++) {
      const choices = [s[i], d[i], 0];
      rgb[i] = Math.floor((choices[b[0]] - choices[b[1]]) * factor / 128) + choices[b[3]];
    }
  }
  const out = [...rgb.map((v) => state.colclamp ? byte(v) : v & 255), s[3] | (state.fba ? 128 : 0)];
  const rgba = out.map((v, i) => {
    const laneMask = (mask >>> (i * 8)) & 255;
    return (v & (255 ^ laneMask)) | (d[i] & laneMask);
  });
  return { rgba, z: depthWrite ? zs : destinationZ, framebufferWrite: mask !== 0xffffffff, depthWrite };
}
