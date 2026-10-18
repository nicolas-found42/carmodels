// Game shading (candidate): the decoded Ford Racing 2 pass-4 handler in the recovered inspector.
//
// The static decode (research/vu-handler-dump.md, research/pass-source-join.md, receipt
// research/evidence/vu-dispatch/handlers-pass4-pass5.json) reads pass 4, per vertex, as:
//   V = (position - eye) * position.w        d = V . N
//   R = -reflect(V, N)                       (x', y', z') = R * (TOP[12], TOP[13], TOP[14])
//   inv = 1 / (-1 - |z'|)
//   s = (0.5 * x' * inv + 0.5) * Q           t = (-0.5 * y' * inv + 0.5) * Q
//   RGBA = (paint * min(1 + 0.95 d, 1), min(1 + 0.95 d, 1))
// "Reflection map" and "environment lookup" are readings of that arithmetic; the receipt calls
// itself a static derivation of the microcode, not a captured frame. Everything here is a
// candidate until a capture settles it.
//
// Every arithmetic step rounds to binary32, the same host reconstruction the repository's numeric
// handler executor uses (tools/vu1_exec.py, NumDomain); tools/test_recovered_game_shading.mjs compares
// this implementation with that executor through tools/vu_pass4_executor.py.
//
// Stand-ins, recorded because the real values come from game state:
//  * eye: the inspector camera position. The handler reads DM[7], a game-state position, and its
//    position plane is the model's own coordinate (the recovered geometry keeps original
//    coordinates); the model node transform is ignored.
//  * the position plane's w lane: the exported geometry has no such lane. The capture comparison
//    reads the pass-4 factor within [0, 1] on every aligned vertex, so that reading has V unit
//    length; the inspector reconstructs w = 1/|position - eye| (a reading, not a decoded input).
//  * the 3x3 matrix: the camera's world basis (view-derived). The game's TOP[12]-TOP[14] come from
//    its own view state and are not captured per draw.
//  * compositing: the decoded pass writes RGB = paint * factor and samples the environment texture
//    through the GS texture function; the draw's ALPHA_1 blend equation is not in the receipt, so
//    the term is added over the baseline pass-2 colour.
//  * the sampled texture is the retained preview of the view render target
//    (research/evidence/vu-dispatch/pass4-retained-target.png). The receipt marks it as
//    capture-time contents at the sampled address, not the post-render frame.
import * as THREE from './vendor/three.module.js';

export const PASS4_LABEL = 'Game shading (candidate)';
export const PASS4_CAVEAT = 'Candidate: the decoded pass-4 paraboloid environment lookup of the game VU1 handler. The eye is the inspector camera and the reflection matrix is view-derived; the real eye and matrix come from game state. Parts without an established pass-4 assignment keep the baseline shading.';

const ENVIRONMENT_ATTRIBUTE = 'pass4Env';
const FACTOR_CONSTANT = Math.fround(-0.949999988); // the decoded -0.949999988 constant, as binary32
const f32 = Math.fround;

// The decoded colour factor min(1 - d * -0.949999988, 1) for d = V . N.
export function pass4Factor(dot) {
 return Math.min(f32(1 - f32(dot * FACTOR_CONSTANT)), 1);
}

// The decoded per-vertex output: unit texture coordinates u/v, the colour factor, the homogeneous
// s/t the handler writes (u*Q, v*Q) and the ftoi0 colour lanes. rows is the 3x3 matrix read
// row-major; q is the previous output buffer's Q lane.
export function pass4Vertex(position, normal, eye, rows, q, colour) {
 const [vx, vy, vz] = [0, 1, 2].map(k => f32(f32(position[k] - eye[k]) * position[3]));
 const dot = f32(f32(f32(f32(vx * normal[0]) + f32(vy * normal[1])) + f32(vz * normal[2])));
 const twice = f32(f32(-dot) + f32(-dot));
 // The handler negates each reflected component: -(N * 2d + V).
 const reflected = [vx, vy, vz].map((value, k) => f32(-f32(f32(normal[k] * twice) + value)));
 const transform = row => f32(f32(f32(rows[row * 3] * reflected[0]) + f32(rows[row * 3 + 1] * reflected[1])) + f32(rows[row * 3 + 2] * reflected[2]));
 const [x, y, z] = [transform(0), transform(1), transform(2)];
 const inverse = f32(1 / f32(-1 - Math.abs(z)));
 const u = f32(f32(f32(x * inverse) * 0.5) + 0.5);
 const v = f32(-f32(f32(y * inverse) * 0.5) + 0.5);
 const factor = pass4Factor(dot);
 const ftoi0 = value => Math.max(-(2 ** 31), Math.min(2 ** 31 - 1, Math.trunc(value)));
 return {u, v, factor, s: f32(u * q), t: f32(v * q),
         rgb: colour === undefined ? null : colour.slice(0, 3).map(k => ftoi0(f32(k * factor)))};
}

// View-derived stand-in for TOP[12]-TOP[14]: the camera's world basis, row-major.
export function pass4Matrix(matrixWorld) {
 const e = matrixWorld.elements;
 return [e[0], e[1], e[2], e[4], e[5], e[6], e[8], e[9], e[10]];
}

// Validate the assignment table derived by tools/build_pass4_assignments.py.
export function parsePass4Assignments(value) {
 if (!value || typeof value !== 'object' || value.schema !== 'fr2-game-shading-pass4/v1' || !Array.isArray(value.cars)) {
  throw Error('Unsupported pass-4 assignment table');
 }
 const cars = value.cars.map(car => ({
  code: String(car.code ?? ''),
  game: String(car.game ?? ''),
  label: String(car.label ?? ''),
  // offsets and flags are index-aligned; each pair is one source Header with an aligned pass-4 draw.
  offsets: car.headers.map(header => header.offset),
  flags: car.headers.map(header => header.flags),
 }));
 if (!cars.length || cars.some(car => !car.code || !car.game || !car.offsets.length || car.offsets.some(offset => !Number.isInteger(offset)))) {
  throw Error('Pass-4 assignment table has no usable Header rows');
 }
 if (cars.some((car, index) => index && `${cars[index - 1].game}/${cars[index - 1].code}` >= `${car.game}/${car.code}`)) {
  throw Error('Pass-4 assignment table is not sorted by game and car code');
 }
 return {schema: value.schema, label: String(value.label), texture: value.texture, cars};
}

export async function loadPass4Assignments(url = 'public/game-shading-pass4.json') {
 const response = await fetch(url, {cache: 'no-store'});
 if (!response.ok) throw Error(`Pass-4 assignment table did not load (${response.status})`);
 return parsePass4Assignments(await response.json());
}

export async function loadPass4Assets({assignmentsUrl = 'public/game-shading-pass4.json',
                                       textureUrl = 'public/pass4-retained-target.png'} = {}) {
 const assignments = await loadPass4Assignments(assignmentsUrl);
 const texture = await new THREE.TextureLoader().loadAsync(encodeURI(textureUrl));
 texture.colorSpace = THREE.SRGBColorSpace;
 texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
 texture.flipY = false;
 texture.needsUpdate = true;
 return {assignments, texture};
}

// The Header offsets with an established pass-4 assignment for this game and car, or null when the
// receipt covers no draw of it. Header offsets are per-model file offsets and coincide numerically
// across cars, so the lookup is scoped by game and code.
export function assignedOffsets(assignments, game, code) {
 const car = assignments.cars.find(row => row.game === game && row.code === code);
 return car ? new Set(car.offsets) : null;
}

// The per-vertex environment attribute, added only while the control is on and removed when it is
// off so a disabled control leaves the geometry exactly as the baseline viewer built it.
export function setPass4Geometry(geometry, on) {
 if (!on) { if (geometry.getAttribute(ENVIRONMENT_ATTRIBUTE)) geometry.deleteAttribute(ENVIRONMENT_ATTRIBUTE); return false; }
 const count = geometry.getAttribute('position').count;
 if (!geometry.getAttribute(ENVIRONMENT_ATTRIBUTE)) {
  geometry.setAttribute(ENVIRONMENT_ATTRIBUTE, new THREE.BufferAttribute(new Float32Array(count * 3), 3));
 }
 return true;
}

// Rewrite (u, v, factor) for every vertex from the current eye and matrix; returns the factor range
// seen, so the page can state that the lookup moved.
export function writePass4Environment(geometry, eye, rows) {
 const positions = geometry.getAttribute('position');
 const normals = geometry.getAttribute('normal');
 const environment = geometry.getAttribute(ENVIRONMENT_ATTRIBUTE);
 if (!environment) return null;
 const values = environment.array;
 let low = Infinity, high = -Infinity;
 for (let index = 0; index < positions.count; index += 1) {
  const point = [0, 1, 2].map(k => positions.getComponent(index, k));
  // The source position plane's w lane is not in the exported geometry. The capture comparison reads
  // the pass-4 factor in [0, 1] on every aligned vertex, i.e. d = V . N is a cosine, so V is
  // unit length; the reading used here is w = 1/|position - eye|.
  const distance = Math.hypot(point[0] - eye[0], point[1] - eye[1], point[2] - eye[2]);
  const position = point.concat(distance > 1e-6 ? f32(1 / distance) : 1);
  const normal = [0, 1, 2].map(k => normals.getComponent(index, k));
  const {u, v, factor} = pass4Vertex(position, normal, eye, rows, 1);
  values[index * 3] = u;
  values[index * 3 + 1] = v;
  values[index * 3 + 2] = factor;
  low = Math.min(low, factor);
  high = Math.max(high, factor);
 }
 environment.needsUpdate = true;
 return {low, high};
}

// Install or remove the environment term on one material. Off restores the exact function objects
// the baseline material had, so a disabled control recompiles nothing.
export function setPass4Material(material, on, texture) {
 const installed = material.userData.pass4;
 if (!on) {
  if (!installed) return false;
  material.onBeforeCompile = installed.onBeforeCompile;
  material.customProgramCacheKey = installed.customProgramCacheKey;
  delete material.userData.pass4;
  material.needsUpdate = true;
  return true;
 }
 if (installed) {
  if (texture) installed.uniforms.value = texture;
  return false;
 }
 // Nothing to sample without the retained preview, so the material stays on the baseline path.
 if (!texture) return false;
 const previous = {onBeforeCompile: material.onBeforeCompile, customProgramCacheKey: material.customProgramCacheKey, uniforms: {value: texture ?? null}};
 material.userData.pass4 = previous;
 material.customProgramCacheKey = () => 'pass4-environment';
 material.onBeforeCompile = shader => {
  shader.uniforms.pass4Texture = previous.uniforms;
  shader.vertexShader = `attribute vec3 ${ENVIRONMENT_ATTRIBUTE};\nvarying vec3 vPass4Environment;\n${shader.vertexShader}`
   .replace('#include <begin_vertex>', `#include <begin_vertex>\n vPass4Environment = ${ENVIRONMENT_ATTRIBUTE};`);
  shader.fragmentShader = `uniform sampler2D pass4Texture;\nvarying vec3 vPass4Environment;\n${shader.fragmentShader}`
   .replace('#include <opaque_fragment>',
            '#include <opaque_fragment>\n gl_FragColor.rgb += texture2D(pass4Texture, vPass4Environment.xy).rgb * diffuseColor.rgb * vPass4Environment.z;');
 };
 material.needsUpdate = true;
 return true;
}

// The inspector's control state: which meshes carry an established assignment, the on/off switch
// and the per-frame refresh that makes the reflection move as the camera orbits.
export function createPass4State(assets = {}) {
 // assets is read live: the page fills assignments and texture in when its fetch and image land.
 const state = {enabled: false, code: null, assigned: [], total: 0, eye: null, rows: null, range: null};
 function applyMesh(mesh) {
  setPass4Geometry(mesh.geometry, state.enabled);
  setPass4Material(mesh.material, state.enabled, assets.texture ?? null);
 }
 // Rewrite every assigned mesh and report the factor range across all of them, so the label cannot
 // show only the last mesh's values.
 function refresh() {
  if (!state.enabled || !state.eye) return false;
  let low = Infinity, high = -Infinity;
  for (const mesh of state.assigned) {
   const range = writePass4Environment(mesh.geometry, state.eye, state.rows);
   if (range) { low = Math.min(low, range.low); high = Math.max(high, range.high); }
  }
  if (low <= high) state.range = {low, high};
  return true;
 }
 function status() {
  if (!state.enabled) return '';
  if (!state.code) return `${PASS4_LABEL} on: no model is loaded, so no source Header is in view. ${PASS4_CAVEAT}`;
  if (!state.assigned.length) {
   return `${PASS4_LABEL} on (${state.code}): no established pass-4 assignment covers this car, so every part renders exactly as before. ${PASS4_CAVEAT}`;
  }
  const range = state.range ? ` Colour factor ${state.range.low.toFixed(2)}–${state.range.high.toFixed(2)} at this view.` : '';
  return `${PASS4_LABEL} on (${state.code}): ${state.assigned.length} of ${state.total} source primitives carry an established pass-4 assignment; the rest are unchanged.${range} ${PASS4_CAVEAT}`;
 }
 return {
  get enabled() { return state.enabled; },
  get assigned() { return state.assigned.length; },
  // Record the loaded car's meshes; only Headers in the derived table take the environment lookup.
  attach(meshes, game, code) {
   const offsets = assets.assignments ? assignedOffsets(assets.assignments, game, code) : null;
   state.code = code ?? null;
   state.total = meshes.length;
   // The recovered under-car shadow (issue #23) is an alpha coverage decal over the ground, not a
   // shaded paint surface, so it never takes the pass-4 environment lookup.
   state.assigned = offsets ? meshes.filter(mesh => !mesh.userData.shadow && !mesh.parent?.userData?.shadow
    && offsets.has(mesh.userData.paintPrimitive?.extras?.headerOffset)) : [];
   if (state.enabled) { for (const mesh of state.assigned) applyMesh(mesh); refresh(); }
   return state.assigned.length;
  },
  // Turn the candidate shading on or off; off restores the baseline geometry and materials.
  setEnabled(on, camera) {
   state.enabled = on === true;
   for (const mesh of state.assigned) applyMesh(mesh);
   if (state.enabled && camera) { camera.updateMatrixWorld(true); state.eye = camera.position.toArray(); state.rows = pass4Matrix(camera.matrixWorld); }
   refresh();
   if (!state.enabled) state.range = null;
   return status();
  },
  // Per frame while on: the eye and the view-derived matrix follow the inspector camera, and the
  // lookup is recomputed only when the view actually moved.
 follow(camera) {
   if (!state.enabled || !camera) return false;
   // OrbitControls.update() runs lookAt() before this call, which leaves matrixWorld stale, so the
   // world matrix is updated here: eye and rotation then describe the frame being rendered.
   camera.updateMatrixWorld(true);
   const eye = camera.position.toArray(), rows = pass4Matrix(camera.matrixWorld);
   if (state.eye && state.rows && eye.every((value, k) => value === state.eye[k]) && rows.every((value, k) => value === state.rows[k])) return false;
   state.eye = eye;
   state.rows = rows;
   refresh();
   return true;
  },
  status,
 };
}
