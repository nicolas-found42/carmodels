// Game shading (candidate): the decoded Ford Racing 2 pass-4 reflection and pass-5 specular in the
// recovered inspector.
//
// The static decode (research/vu-handler-dump.md, research/pass-source-join.md, receipt
// research/evidence/vu-dispatch/handlers-pass4-pass5.json) reads pass 4, per vertex, as:
//   V = (position - eye) * position.w        d = V . N
//   R = -reflect(V, N)                       (x', y', z') = R * (TOP[12], TOP[13], TOP[14])
//   inv = 1 / (-1 - |z'|)
//   s = (0.5 * x' * inv + 0.5) * Q           t = (-0.5 * y' * inv + 0.5) * Q
//   RGBA = (paint * min(1 + 0.95 d, 1), min(1 + 0.95 d, 1))
// and pass 5, per vertex, as:
//   L = DM[6]                                V = (DM[7] - position) * position.w
//   R = 2 (N . L) N - L
//   S = max(0.5 * ((R + V) . V) - 0.5, 0)    s = S * Q     t = TOP[1].w * Q
//   RGBA = ftoi0(min(DM[5] . colour, 128))   alpha = ftoi0(min(DM[5].w, 128))
// "Reflection map", "environment lookup" and "specular" are readings of that arithmetic; the receipt
// calls itself a static derivation of the microcode, not a captured frame. The capture comparison
// (research/evidence/vu-dispatch/handler-dump-comparison.json) verifies the pass-4 colour factor and
// the pass-5 RGBA relation and T lane on the aligned draws; it does not verify full pass-5 S, whose
// working-plane inputs the receipt does not retain. Everything here is a candidate until a capture
// settles it.
//
// Every arithmetic step rounds to binary32, the same host reconstruction the repository's numeric
// handler executor uses (tools/vu1_exec.py, NumDomain); tools/test_recovered_game_shading.mjs
// compares this implementation with that executor through tools/vu_shading_executor.py.
//
// Stand-ins, recorded because the real values come from game state (docs/adr/0004-inspector-game-shading-stand-ins.md):
//  * eye (DM[7]): the inspector camera position. The model node transform is ignored, and the
//    position plane is the model's own coordinate (the recovered geometry keeps original
//    coordinates).
//  * the position plane's w lane: the exported geometry has no such lane. The capture comparison
//    reads the pass-4 factor within [0, 1] on every aligned vertex, so that reading has V unit
//    length; the inspector reconstructs w = 1/|position - eye|, which is the same reading the pass-5
//    specular needs (it is also a difference from DM[7]).
//  * the 3x3 matrix: the camera's world basis (view-derived). The game's TOP[12]-TOP[14] come from
//    its own view state and are not captured per draw.
//  * the pass-5 light: DM[5] (colour and intensity) and DM[6] (the direction the specular reflects)
//    come from game state. The inspector substitutes the retained capture values every one of the 63
//    aligned pass-5 draws carries; they are not per-draw game state, and no other light is added.
//  * the pass-5 colour constant: the decoded RGBA is the draw's own constant, ftoi0(min(DM[5] *
//    colour, 128)), with colour taken from the displayed paint; with the retained DM[5] its alpha
//    lane truncates to 0, so the highlight is added to RGB and composites nothing through alpha.
//  * compositing: the decoded passes write their RGB and sample textures through the GS texture
//    function, whose state is not in the receipt, so both terms are added over the baseline pass-2
//    colour. The sampled pass-4 texture is the retained preview of the view render target
//    (research/evidence/vu-dispatch/pass4-retained-target.png), which the receipt marks as
//    capture-time contents at the sampled address, not the post-render frame.
import * as THREE from './vendor/three.module.js';

export const SHADING_LABEL = 'Game shading (candidate)';
export const SHADING_CAVEAT = 'Candidate: the decoded pass-4 paraboloid environment lookup and pass-5 specular of the game VU1 handlers. The eye (DM[7]) is the inspector camera, the reflection matrix is view-derived, and the pass-5 light (DM[5] colour, DM[6] direction) is the retained capture value; the game\'s own state is not captured. Parts without an established assignment keep the baseline shading.';

const ENVIRONMENT_ATTRIBUTE = 'pass4Env';
const SPECULAR_ATTRIBUTE = 'pass5Spec';
const FACTOR_CONSTANT = Math.fround(-0.949999988); // the decoded -0.949999988 constant, as binary32
// The pass-5 light stand-ins: DM[5] (colour, intensity and the alpha lane) and DM[6] (the direction
// the specular reflects), as the retained capture words every aligned pass-5 draw carries.
export const PASS5_LIGHT = Object.freeze([0.7450979948043823, 0.7176470160484314, 0.7176470160484314, 0.6470587849617004]);
export const PASS5_LIGHT_DIRECTION = Object.freeze([0.6956135630607605, -0.5310018062591553, -0.4838990271091461]);
const f32 = Math.fround;
const ftoi0 = value => Math.max(-(2 ** 31), Math.min(2 ** 31 - 1, Math.trunc(value)));

// The decoded colour factor min(1 - d * -0.949999988, 1) for d = V . N.
export function pass4Factor(dot) {
 return Math.min(f32(1 - f32(dot * FACTOR_CONSTANT)), 1);
}

// The decoded pass-4 per-vertex output: unit texture coordinates u/v, the colour factor, the
// homogeneous s/t the handler writes (u*Q, v*Q) and the ftoi0 colour lanes. rows is the 3x3 matrix
// read row-major; q is the previous output buffer's Q lane.
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
 return {u, v, factor, s: f32(u * q), t: f32(v * q),
         rgb: colour === undefined ? null : colour.slice(0, 3).map(k => ftoi0(f32(k * factor)))};
}

// View-derived stand-in for TOP[12]-TOP[14]: the camera's world basis, row-major.
export function pass4Matrix(matrixWorld) {
 const e = matrixWorld.elements;
 return [e[0], e[1], e[2], e[4], e[5], e[6], e[8], e[9], e[10]];
}

// The decoded pass-5 specular intensity S for one vertex: the reflection of the light direction about
// the surface normal, against the view vector V = (eye - position) * position.w. The handler sums
// (R + V) . V * 0.5 term by term and subtracts 0.5, so the rounding order is kept.
export function pass5Specular(position, normal, eye, lightDirection = PASS5_LIGHT_DIRECTION) {
 const [vx, vy, vz] = [0, 1, 2].map(k => f32(f32(eye[k] - position[k]) * position[3]));
 const doubled = lightDirection.map(value => f32(value + value));
 const projected = f32(f32(f32(normal[0] * doubled[0]) + f32(normal[1] * doubled[1])) + f32(normal[2] * doubled[2]));
 const view = [vx, vy, vz];
 // R = 2 (N . L) N - L, then ((R + V) * 0.5) * V per lane.
 const term = k => f32(f32(f32(f32(f32(normal[k] * projected) - lightDirection[k]) + view[k]) * 0.5) * view[k]);
 const sum = f32(f32(term(0) + term(1)) + term(2));
 return f32(Math.max(f32(sum - 0.5), 0));
}

// The decoded pass-5 per-draw colour constant: ftoi0(min(DM[5] * colour, 128)) on the RGB lanes and
// ftoi0(min(DM[5].w, 128)) on the alpha lane - the receipt's decode clamps DM[5].w alone, without the
// draw colour, so the RGB lanes are paint-tinted and the alpha lane is not.
export function pass5Colour(colour, light = PASS5_LIGHT) {
 return [0, 1, 2, 3].map(k => ftoi0(Math.min(k === 3 ? light[3] ?? 0 : f32((light[k] ?? 0) * (colour[k] ?? 0)), 128)));
}

// The decoded pass-5 per-vertex output: the specular S the handler shades with, the stored STQ s lane
// (S * Q) and the per-draw colour lanes.
export function pass5Vertex(position, normal, eye, q, colour, light = PASS5_LIGHT, lightDirection = PASS5_LIGHT_DIRECTION) {
 const specular = pass5Specular(position, normal, eye, lightDirection);
 return {specular, s: f32(specular * q), q, rgba: pass5Colour(colour, light)};
}

// Validate the assignment table derived by tools/build_game_shading_assignments.py.
export function parseShadingAssignments(value) {
 if (!value || typeof value !== 'object' || value.schema !== 'fr2-game-shading/v2' || !Array.isArray(value.cars)) {
  throw Error('Unsupported game-shading assignment table');
 }
 const cars = value.cars.map(car => ({
  code: String(car.code ?? ''),
  game: String(car.game ?? ''),
  label: String(car.label ?? ''),
  // offsets, flags and passes are index-aligned; each entry is one source Header with the aligned
  // draws the receipt joins to it.
  offsets: car.headers.map(header => header.offset),
  flags: car.headers.map(header => header.flags),
  passes: car.headers.map(header => header.passes),
 }));
 const usable = passes => Array.isArray(passes) && passes.length
  && passes.every(pass => pass === 4 || pass === 5) && passes.length === new Set(passes).size;
 if (!cars.length || cars.some(car => !car.code || !car.game || !car.offsets.length
   || car.offsets.some(offset => !Number.isInteger(offset)) || !car.passes.every(usable))) {
  throw Error('Game-shading assignment table has no usable Header rows');
 }
 if (cars.some((car, index) => index && `${cars[index - 1].game}/${cars[index - 1].code}` >= `${car.game}/${car.code}`)) {
  throw Error('Game-shading assignment table is not sorted by game and car code');
 }
 return {schema: value.schema, label: String(value.label), texture: value.pass4_texture, cars};
}

export async function loadShadingAssignments(url = 'public/game-shading.json') {
 const response = await fetch(url, {cache: 'no-store'});
 if (!response.ok) throw Error(`Game-shading assignment table did not load (${response.status})`);
 return parseShadingAssignments(await response.json());
}

export async function loadShadingAssets({assignmentsUrl = 'public/game-shading.json',
                                         textureUrl = 'public/pass4-retained-target.png'} = {}) {
 const assignments = await loadShadingAssignments(assignmentsUrl);
 const texture = await new THREE.TextureLoader().loadAsync(encodeURI(textureUrl));
 texture.colorSpace = THREE.SRGBColorSpace;
 texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
 texture.flipY = false;
 texture.needsUpdate = true;
 return {assignments, texture};
}

// The Header offsets with an established assignment for this game and car, per decoded pass, or null
// when the receipt covers no draw of it. Header offsets are per-model file offsets and coincide
// numerically across cars, so the lookup is scoped by game and code.
export function shadingAssignments(assignments, game, code) {
 const car = assignments.cars.find(row => row.game === game && row.code === code);
 if (!car) return null;
 const offsets = (pass) => new Set(car.offsets.filter((offset, index) => car.passes[index].includes(pass)));
 return {pass4: offsets(4), pass5: offsets(5)};
}

// The per-vertex attributes the decoded passes read, added only while the control is on and removed
// when it is off (or when the part loses its assignment), so a disabled control leaves the geometry
// exactly as the baseline viewer built it.
export function setShadingGeometry(geometry, on, parts = {}) {
 let changed = false;
 for (const [attribute, size, needed] of [[ENVIRONMENT_ATTRIBUTE, 3, on && parts.pass4 === true],
                                          [SPECULAR_ATTRIBUTE, 1, on && parts.pass5 === true]]) {
  const present = geometry.getAttribute(attribute);
  if (needed && !present) {
   geometry.setAttribute(attribute, new THREE.BufferAttribute(new Float32Array(geometry.getAttribute('position').count * size), size));
   changed = true;
  } else if (!needed && present) {
   geometry.deleteAttribute(attribute);
   changed = true;
  }
 }
 return changed;
}

// Rewrite (u, v, factor) for every vertex from the current eye and matrix; returns the factor range
// seen, so the page can state that the lookup moved.
export function writeEnvironment(geometry, eye, rows) {
 const positions = geometry.getAttribute('position');
 const normals = geometry.getAttribute('normal');
 const environment = geometry.getAttribute(ENVIRONMENT_ATTRIBUTE);
 if (!environment) return null;
 const values = environment.array;
 let low = Infinity, high = -Infinity;
 for (let index = 0; index < positions.count; index += 1) {
  const {u, v, factor} = pass4Vertex(vertexPosition(positions, index, eye), vertexNormal(normals, index), eye, rows, 1);
  values[index * 3] = u;
  values[index * 3 + 1] = v;
  values[index * 3 + 2] = factor;
  low = Math.min(low, factor);
  high = Math.max(high, factor);
 }
 environment.needsUpdate = true;
 return {low, high};
}

// Rewrite the per-vertex pass-5 specular from the current eye; returns the range seen.
export function writeSpecular(geometry, eye) {
 const positions = geometry.getAttribute('position');
 const normals = geometry.getAttribute('normal');
 const specular = geometry.getAttribute(SPECULAR_ATTRIBUTE);
 if (!specular) return null;
 const values = specular.array;
 let low = Infinity, high = -Infinity;
 for (let index = 0; index < positions.count; index += 1) {
  const value = pass5Specular(vertexPosition(positions, index, eye), vertexNormal(normals, index), eye);
  values[index] = value;
  low = Math.min(low, value);
  high = Math.max(high, value);
 }
 specular.needsUpdate = true;
 return {low, high};
}

// One vertex's position plane, with the reconstructed w lane. The source position plane's w lane is
// not in the exported geometry: the capture comparison reads the pass-4 factor in [0, 1] on every
// aligned vertex, i.e. d = V . N is a cosine, so V is unit length and w = 1/|position - eye|.
function vertexPosition(positions, index, eye) {
 const point = [0, 1, 2].map(k => positions.getComponent(index, k));
 const distance = Math.hypot(point[0] - eye[0], point[1] - eye[1], point[2] - eye[2]);
 return point.concat(distance > 1e-6 ? f32(1 / distance) : 1);
}

function vertexNormal(normals, index) {
 return [0, 1, 2].map(k => normals.getComponent(index, k));
}

// Install or remove the two decoded terms on one material. parts selects which terms this part
// carries; the pass-4 term needs the retained preview to sample, and without it that term is left
// out. Off restores the exact function objects the baseline material had, so a disabled control
// recompiles nothing.
export function setShadingMaterial(material, on, {pass4 = false, pass5 = false, texture = null} = {}) {
 const installed = material.userData.shading;
 const key = `${pass4 && texture ? 'env' : ''}${pass5 ? 'spec' : ''}`;
 if (!on) {
  if (!installed) return false;
  material.onBeforeCompile = installed.onBeforeCompile;
  material.customProgramCacheKey = installed.customProgramCacheKey;
  delete material.userData.shading;
  material.needsUpdate = true;
  return true;
 }
 if (installed && installed.key === key) {
  installed.uniforms.value = texture ?? installed.uniforms.value;
  return false;
 }
 if (installed) setShadingMaterial(material, false);
 if (!key) return false;
 const previous = {key, onBeforeCompile: material.onBeforeCompile, customProgramCacheKey: material.customProgramCacheKey,
                   uniforms: {value: texture ?? null}, light: {value: new THREE.Vector4(...PASS5_LIGHT)}};
 material.userData.shading = previous;
 material.customProgramCacheKey = () => `${previous.customProgramCacheKey.call(material)};game-shading:${key}`;
 // The recovered materials carry their own shader patch (dealership/mc3-tire-material.mjs adds the
 // native garage specular), so the decoded term composes with it: the baseline callback still runs
 // and the added term lands on the colour it produced.
 material.onBeforeCompile = function (shader, renderer) {
  previous.onBeforeCompile.call(this, shader, renderer);
  let vertexShader = shader.vertexShader, fragmentShader = shader.fragmentShader;
  if (key.includes('env')) {
   shader.uniforms.pass4Texture = previous.uniforms;
   vertexShader = `attribute vec3 ${ENVIRONMENT_ATTRIBUTE};\nvarying vec3 vPass4Environment;\n${vertexShader}`
    .replace('#include <begin_vertex>', `#include <begin_vertex>\n vPass4Environment = ${ENVIRONMENT_ATTRIBUTE};`);
   fragmentShader = `uniform sampler2D pass4Texture;\nvarying vec3 vPass4Environment;\n${fragmentShader}`
    .replace('#include <opaque_fragment>',
             '#include <opaque_fragment>\n gl_FragColor.rgb += texture2D(pass4Texture, vPass4Environment.xy).rgb * diffuseColor.rgb * vPass4Environment.z;');
  }
  if (key.includes('spec')) {
   shader.uniforms.pass5Light = previous.light;
   vertexShader = `attribute float ${SPECULAR_ATTRIBUTE};\nvarying float vPass5Specular;\n${vertexShader}`
    .replace('#include <begin_vertex>', `#include <begin_vertex>\n vPass5Specular = ${SPECULAR_ATTRIBUTE};`);
   fragmentShader = `uniform vec4 pass5Light;\nvarying float vPass5Specular;\n${fragmentShader}`
    .replace('#include <opaque_fragment>',
             '#include <opaque_fragment>\n gl_FragColor.rgb += vPass5Specular * (floor(min(pass5Light.rgb * diffuseColor.rgb * 255.0, vec3(128.0))) / 255.0);');
  }
  shader.vertexShader = vertexShader;
  shader.fragmentShader = fragmentShader;
 };
 material.needsUpdate = true;
 return true;
}

// The inspector's control state: which meshes carry an established assignment and for which decoded
// pass, the on/off switch and the per-frame refresh that makes both terms move as the camera orbits.
export function createShadingState(assets = {}) {
 // assets is read live: the page fills assignments and texture in when its fetch and image land.
 const state = {enabled: false, code: null, shaded: [], total: 0, eye: null, rows: null, range: null, specular: null};
 function applyMesh(entry) {
  setShadingGeometry(entry.mesh.geometry, state.enabled, entry);
  setShadingMaterial(entry.mesh.material, state.enabled, {pass4: entry.pass4, pass5: entry.pass5, texture: assets.texture ?? null});
 }
 // Rewrite every assigned mesh and report the factor and specular ranges across all of them, so the
 // label cannot show only the last mesh's values.
 function refresh() {
  if (!state.enabled || !state.eye) return false;
  let low = Infinity, high = -Infinity, specularLow = Infinity, specularHigh = -Infinity;
  for (const entry of state.shaded) {
   if (entry.pass4) {
    const range = writeEnvironment(entry.mesh.geometry, state.eye, state.rows);
    if (range) { low = Math.min(low, range.low); high = Math.max(high, range.high); }
   }
   if (entry.pass5) {
    const range = writeSpecular(entry.mesh.geometry, state.eye);
    if (range) { specularLow = Math.min(specularLow, range.low); specularHigh = Math.max(specularHigh, range.high); }
   }
  }
  if (low <= high) state.range = {low, high};
  if (specularLow <= specularHigh) state.specular = {low: specularLow, high: specularHigh};
  return true;
 }
 const range = (values, label) => values ? ` ${label} ${values.low.toFixed(2)}\u2013${values.high.toFixed(2)} at this view.` : '';
 function status() {
  if (!state.enabled) return '';
  if (!state.code) return `${SHADING_LABEL} on: no model is loaded, so no source Header is in view. ${SHADING_CAVEAT}`;
  const counts = state.shaded.reduce((total, entry) => ({pass4: total.pass4 + (entry.pass4 ? 1 : 0), pass5: total.pass5 + (entry.pass5 ? 1 : 0)}), {pass4: 0, pass5: 0});
  if (!state.shaded.length) {
   return `${SHADING_LABEL} on (${state.code}): no established game-shading assignment covers this car, so every part renders exactly as before. ${SHADING_CAVEAT}`;
  }
  return `${SHADING_LABEL} on (${state.code}): ${counts.pass4} of ${state.total} source primitives carry an established pass-4 reflection assignment and ${counts.pass5} a pass-5 specular assignment; the rest are unchanged.`
   + range(state.range, 'Colour factor') + range(state.specular, 'Specular') + ` ${SHADING_CAVEAT}`;
 }
 return {
  get enabled() { return state.enabled; },
  // How many parts each decoded pass shaded, and which passes the model's Headers carry at all.
  get assigned() {
   return state.shaded.reduce((total, entry) => ({pass4: total.pass4 + (entry.pass4 ? 1 : 0), pass5: total.pass5 + (entry.pass5 ? 1 : 0)}), {pass4: 0, pass5: 0});
  },
  // Record the loaded car's meshes; only Headers in the derived table take the decoded terms.
  attach(meshes, game, code) {
   const offsets = assets.assignments ? shadingAssignments(assets.assignments, game, code) : null;
   state.code = code ?? null;
   state.total = meshes.length;
   // The recovered under-car shadow (issue #23) is an alpha coverage decal over the ground, not a
   // shaded paint surface, so it never takes either decoded pass.
   state.shaded = offsets ? meshes.filter(mesh => !mesh.userData.shadow && !mesh.parent?.userData?.shadow)
    .map(mesh => {
     const offset = mesh.userData.paintPrimitive?.extras?.headerOffset;
     return {mesh, pass4: offsets.pass4.has(offset), pass5: offsets.pass5.has(offset)};
    }).filter(entry => entry.pass4 || entry.pass5) : [];
   if (state.enabled) { for (const entry of state.shaded) applyMesh(entry); refresh(); }
   return state.shaded.length;
  },
  // Turn the candidate shading on or off; off restores the baseline geometry and materials.
  setEnabled(on, camera) {
   state.enabled = on === true;
   for (const entry of state.shaded) applyMesh(entry);
   if (state.enabled && camera) { camera.updateMatrixWorld(true); state.eye = camera.position.toArray(); state.rows = pass4Matrix(camera.matrixWorld); }
   refresh();
   if (!state.enabled) { state.range = null; state.specular = null; }
   return status();
  },
  // Per frame while on: the eye and the view-derived matrix follow the inspector camera, and the
  // terms are recomputed only when the view actually moved.
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
