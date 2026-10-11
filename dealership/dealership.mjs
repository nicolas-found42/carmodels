import * as THREE from './vendor/three.module.js';
import {loadEditableGLB} from './editable-glb.mjs';

export const gameId = c => c.game || 'ford-racing-2';
export const gameLabel = c => c.gameLabel || (gameId(c)==='ford-racing-2'?'Ford Racing 2':gameId(c));
export const isNativePackage = c => c.asset_kind==='native-package' || c.displayMode==='native-package';
export function dealershipDownload(c) {
  return isNativePackage(c) ? {href:'./'+c.model.source.package, filename:c.code+'-dealership.dat', label:'Download native package (.dat)'} :
    {href:`./dealership/models/${c.code}.glb`, filename:c.code+'-dealership.glb', label:'Download dealership model (.glb)'};
}
export function matchesVariant(c, variant) {
  return !variant || (variant==='arcade' ? c.sourceCollection==='arcade' : c.sourceVariant===variant);
}
export async function loadCar(c, options={}) {
  if(isNativePackage(c))throw Error('3D preview unavailable for this native package.');
  return c.model.schema===2 ? loadEditableGLB(c,options) : makeCar(c);
}

// Compact offline mesh: little-endian XYZ + normal XYZ float32, then a tone byte.
function bytes(encoded) {
  if (typeof encoded !== 'string' || !encoded.length || encoded.length % 4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded)) throw Error('Invalid model mesh encoding.');
  return Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
}

export function decodeModel(c) {
  const s = c.model;
  const fail = () => { throw Error(`${c.code}: invalid dealership model.`); };
  if (!s || s.schema !== 1 || !Array.isArray(s.parts) || s.parts.length < 1 || s.parts.length > 3 ||
      !Array.isArray(s.bounds) || s.bounds.length !== 6 || !s.bounds.every(Number.isFinite) ||
      !s.source || s.source.glb !== `dealership/models/${c.code}.glb` || !/^[a-f0-9]{64}$/.test(s.source.sha256) ||
      s.source.preset !== 'dealership' || !Array.isArray(s.wheelHubs) || s.wheelHubs.length > 16) fail();
  if (s.bounds.some((v,i) => i < 3 && v >= s.bounds[i+3]) || Math.abs(s.bounds[1]) > 1e-5) fail();
  if (s.wheelHubs.some(h => !h || !Array.isArray(h.position) || h.position.length !== 3 || !h.position.every(Number.isFinite))) fail();
  let triangles = 0;
  const kinds = new Set();
  const parts = s.parts.map(part => {
    if (!['body','wheel','detail'].includes(part.kind) || kinds.has(part.kind) || !Number.isInteger(part.vertexCount) || part.vertexCount <= 0 || part.vertexCount > 65535) fail();
    kinds.add(part.kind);
    const raw = bytes(part.vertices), faces = bytes(part.indices);
    if (raw.byteLength !== part.vertexCount * 25 || !faces.byteLength || faces.byteLength % 6) fail();
    const view = new DataView(raw.buffer), faceView = new DataView(faces.buffer);
    const positions = new Float32Array(part.vertexCount * 3), normals = new Float32Array(positions.length), colors = new Float32Array(positions.length);
    for (let i = 0; i < part.vertexCount; i++) {
      for (let axis = 0; axis < 3; axis++) {
        const p = view.getFloat32(i*25+axis*4,true), n = view.getFloat32(i*25+12+axis*4,true);
        if (!Number.isFinite(p) || !Number.isFinite(n) || p < s.bounds[axis]-1e-4 || p > s.bounds[axis+3]+1e-4) fail();
        positions[i*3+axis] = p; normals[i*3+axis] = n;
      }
      const length = Math.hypot(...normals.subarray(i*3,i*3+3));
      if (Math.abs(length-1) > 0.01) fail();
      const tone = view.getUint8(i*25+24)/255;
      const linear = tone <= 0.04045 ? tone/12.92 : ((tone+0.055)/1.055)**2.4;
      colors.fill(linear,i*3,i*3+3);
    }
    const indices = new Uint16Array(faces.byteLength/2);
    for (let i = 0; i < indices.length; i++) {
      indices[i] = faceView.getUint16(i*2,true);
      if (indices[i] >= part.vertexCount) fail();
    }
    triangles += indices.length / 3;
    return {kind:part.kind, positions, normals, colors, indices};
  });
  if (!kinds.has('body') || triangles !== s.triangleCount) fail();
  return parts;
}

export function makeCar(c) {
  // Decode completely before allocating GPU resources, so malformed data cannot leak.
  const parts = decodeModel(c);
  const g = new THREE.Group();
  const paint = c.paint?.rgb || [150,155,165];
  const bodyColor = new THREE.Color().setRGB(paint[0]/255,paint[1]/255,paint[2]/255,THREE.SRGBColorSpace);
  const materials = {
    body: new THREE.MeshStandardMaterial({color:bodyColor, vertexColors:true, roughness:0.52, metalness:0.16, side:THREE.DoubleSide}),
    wheel: new THREE.MeshStandardMaterial({color:0xb4bac2, vertexColors:true, roughness:0.64, metalness:0.28, side:THREE.DoubleSide}),
    detail: new THREE.MeshStandardMaterial({color:0x9aa6b3, vertexColors:true, roughness:0.35, metalness:0.2, side:THREE.DoubleSide}),
  };
  g.userData.wheels = [];
  g.userData.source = c.model.source;
  for (const part of parts) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.BufferAttribute(part.positions,3));
    geo.setAttribute('normal',new THREE.BufferAttribute(part.normals,3));
    geo.setAttribute('color',new THREE.BufferAttribute(part.colors,3));
    geo.setIndex(new THREE.BufferAttribute(part.indices,1));
    geo.computeBoundingBox(); geo.computeBoundingSphere();
    const mesh = new THREE.Mesh(geo,materials[part.kind]);
    mesh.name = part.kind; mesh.castShadow = mesh.receiveShadow = true;
    g.add(mesh);
    if (part.kind === 'wheel') g.userData.wheels.push(mesh);
  }
  // Dispose only resources actually attached to the car.
  for (const [kind,material] of Object.entries(materials)) if (!parts.some(p=>p.kind===kind)) material.dispose();
  return g;
}

// Shared geometries/materials belong to the selected car and are disposed once.
export function disposeCar(car) {
  if (!car) return;
  const geometries = new Set(), materials = new Set(), textures = new Set(car.userData.textures||[]);
  car.traverse(node => {
    if (node.geometry) geometries.add(node.geometry);
    if (node.material) for (const mat of [node.material].flat()) { materials.add(mat); if(mat.map)textures.add(mat.map); }
  });
  geometries.forEach(geo => geo.dispose());
  materials.forEach(mat => mat.dispose());
  textures.forEach(texture => texture.dispose());
}

export function validateCars(cars) {
  if (!Array.isArray(cars) || !cars.length) throw Error('The vehicle list is empty or is not an array.');
  const codes = new Set();
  const styles = new Set(['coupe', 'sedan', 'hatchback', 'pickup', 'suv', 'racecar', 'concept', 'unknown']);
  for (const c of cars) {
    if (!c || typeof c.code !== 'string' || !/^[A-Z0-9_]+$/.test(c.code) || codes.has(c.code)) throw Error('A vehicle code is missing or duplicated.');
    codes.add(c.code);
    const unknownSpecs = ['gran-turismo','redline','midnight-club-3-remix'].includes(c.game);
    if(c.game!=null && !/^[a-z0-9][a-z0-9-]*$/.test(c.game))throw Error(`${c.code}: invalid game.`);
    if(c.gameLabel!=null && typeof c.gameLabel!=='string')throw Error(`${c.code}: invalid game label.`);
    if (typeof c.name !== 'string' || !c.name || !styles.has(c.bodyStyle)) throw Error(`${c.code}: invalid name or illustration style.`);
    for (const key of ['agility', 'accel', 'speed', 'weight']) {
      if (!(unknownSpecs && c[key]===null) && (!Number.isFinite(c[key]) || c[key] < 0 || c[key] > 1)) throw Error(`${c.code}: ${key} must be a rating from 0 to 1.`);
    }
    for (const key of ['bhp', 'kg']) {
      if (!(unknownSpecs && c[key]===null) && (!Number.isFinite(c[key]) || c[key] < 0)) throw Error(`${c.code}: invalid ${key}.`);
    }
    if (c.topSpeed != null && (!Number.isFinite(Number(c.topSpeed)) || Number(c.topSpeed) < 0)) throw Error(`${c.code}: invalid top speed.`);
    if (c.year != null && !['string','number'].includes(typeof c.year)) throw Error(`${c.code}: invalid year.`);
    if (c.group != null && typeof c.group !== 'string') throw Error(`${c.code}: invalid group.`);
    if (c.sound != null && typeof c.sound !== 'string') throw Error(`${c.code}: invalid sound bank.`);
    if (!Array.isArray(c.liveries) || c.liveries.some(l => !l || typeof l.label !== 'string' || typeof l.code !== 'string')) throw Error(`${c.code}: invalid liveries.`);
    if (c.paint != null && (!Array.isArray(c.paint.rgb) || c.paint.rgb.length !== 3 || c.paint.rgb.some(v => !Number.isInteger(v) || v < 0 || v > 255))) throw Error(`${c.code}: invalid paint sample.`);
    if(isNativePackage(c)!==(c.model?.schema===3))throw Error(`${c.code}: inconsistent native package model.`);
    if(c.model?.schema===3) {
      const s=c.model.source;
      if(c.game!=='midnight-club-3-remix' || c.displayMode!=='native-package' || c.model.previewStatus!=='unavailable' ||
         !s || s.package!==`dealership/assets/${c.code}.dat` || s.preset!=='dealership' ||
         s.profile!=='mc3-ps2-native-package-v1' || !/^[a-f0-9]{64}$/.test(s.sha256) ||
         !Number.isInteger(s.bytes) || s.bytes<=0 || s.bytes>256*1024*1024 ||
         !Number.isInteger(s.nativeMembers) || s.nativeMembers<=0 || s.nativeMembers>100000 ||
         !/^vp_[a-z0-9_]+$/.test(c.sourceCode) || c.code!=='MC3_'+c.sourceCode.toUpperCase())throw Error(`${c.code}: invalid native dealership package.`);
    } else if(c.model?.schema===2) {
      if(c.displayMode!=='textured-glb' || !c.model.source || c.model.source.glb!==`dealership/models/${c.code}.glb` ||
         c.model.source.preset!=='dealership' || !/^[a-f0-9]{64}$/.test(c.model.source.sha256) ||
         !Number.isInteger(c.model.triangleCount) || c.model.triangleCount<=0)throw Error(`${c.code}: invalid textured dealership model.`);
    } else decodeModel(c);
  }
  return cars;
}

// The timeout spans both response headers and JSON body consumption.
export async function fetchCars(url, {timeoutMs = 15000, fetchImpl = fetch} = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, {signal: controller.signal});
    if (!response.ok) throw Error(`Vehicle data unavailable (HTTP ${response.status}).`);
    return validateCars(await response.json());
  } catch (error) {
    if (controller.signal.aborted) throw Error('Vehicle data timed out. Retry when the local server responds.');
    throw error;
  } finally { clearTimeout(timer); }
}
