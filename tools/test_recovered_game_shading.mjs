// Assert the recovered inspector's candidate game shading.
//
// The control is off by default and off leaves the baseline viewer's materials and geometry exactly
// as they were; the derived Header table joins the shipped model; the unassigned parts are untouched
// and the honesty label says so; and - where the pinned VU overlays are configured - the per-vertex
// colour factor and paraboloid coordinates equal the repository's numeric handler executor
// (tools/vu_pass4_executor.py, which runs the real overlay microcode) within the stated tolerance.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import * as THREE from '../dealership/vendor/three.module.js';
import {PASS4_CAVEAT, PASS4_LABEL, assignedOffsets, createPass4State, parsePass4Assignments,
        pass4Factor, pass4Matrix, pass4Vertex, setPass4Geometry, setPass4Material} from '../dealership/game-shading.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const read = path => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const bytes = path => readFileSync(new URL(path, import.meta.url));
// Both sides do host binary32 arithmetic; the executor rounds every step, so the comparison allows
// one unit in the last place of the compared magnitudes, stated as absolute bounds.
const TOLERANCE = {factor: 1e-6, s: 1e-5, t: 1e-5};

function glbDocument(url) {
 const data = readFileSync(url);
 assert.equal(data.readUInt32LE(0), 0x46546C67, 'not a GLB container');
 assert.equal(data.readUInt32LE(16), 0x4E4F534A, 'the first GLB chunk is not JSON');
 return JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)).toString('utf8'));
}

function fixtureMesh(offset) {
 const geometry = new THREE.BufferGeometry();
 geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array([0.62, 0.86, 1.34, 0.62, 0.86, 1.64, 0.82, 0.9, 1.34]), 3));
 geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array([0, 1, 0, 0, 1, 0, 0, 1, 0]), 3));
 const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial());
 mesh.userData.paintPrimitive = {extras: {headerOffset: offset}};
 return mesh;
}

// The page's control: present, labelled, unchecked, with a hidden honesty label and live wiring.
function checkPageMarkup(text) {
 assert.match(text, /<input type="checkbox" id="game-shading"[^>]*>Game shading \(candidate\)<\/label>/, 'the control is not the labelled checkbox');
 assert.ok(!/id="game-shading"[^>]*checked/.test(text), 'the control is not off by default');
 assert.match(text, /<p id="game-shading-note" hidden><\/p>/, 'the honesty label is missing or visible while off');
 assert.match(text, /from '\.\/game-shading\.mjs'/, 'the page does not import the shading module');
 assert.match(text, /gameShading\.setEnabled\(document\.querySelector\('#game-shading'\)\.checked,camera\)/, 'the toggle is not wired into the material update');
 assert.match(text, /gameShading\.follow\(camera\)/, 'the animation loop does not follow the camera');
 return text;
}

function testPageControl() {
 const page = bytes('../dealership/recovered.html').toString('utf8');
 checkPageMarkup(page);
 const tampers = [['an always-visible label', ' id="game-shading-note" hidden', ' id="game-shading-note"'],
                  ['a checked control', 'id="game-shading"', 'id="game-shading" checked'],
                  ['no camera follow', 'gameShading.follow(camera);', ''],
                  ['no toggle wiring', "gameShading.setEnabled(document.querySelector('#game-shading').checked,camera);", '']];
 for (const [label, from, to] of tampers) {
  assert.ok(page.includes(from), `the page no longer contains ${from}`);
  assert.throws(() => checkPageMarkup(page.replace(from, to)), `the markup check accepts ${label}`);
 }
 console.log('PASS game shading control: off by default in the page markup');
}

function testBaselineIsUntouched(table) {
 const offsets = [...assignedOffsets(table, 'ford-racing-2', 'COBRA')];
 const assigned = fixtureMesh(offsets[0]);
 const unassigned = fixtureMesh(offsets[0] + 4); // a neighbouring source Header with no pass-4 row
 const untouched = fixtureMesh(offsets[0] + 4);
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(2, 1.5, 2);
 camera.updateMatrixWorld(true);
 const texture = new THREE.Texture();
 const state = createPass4State({assignments: table, texture});
 const material = assigned.material, geometry = assigned.geometry;
 const baseline = {onBeforeCompile: material.onBeforeCompile, cache: material.customProgramCacheKey,
                   attributes: Object.keys(geometry.attributes), userData: Object.keys(material.userData)};
 const before = {onBeforeCompile: unassigned.material.onBeforeCompile, attributes: Object.keys(unassigned.geometry.attributes)};
 state.attach([assigned, unassigned], 'ford-racing-2', 'COBRA');
 assert.equal(state.enabled, false, 'the control defaults to on');
 assert.equal(state.status(), '', 'an off control claims something');
 assert.equal(setPass4Material(new THREE.MeshStandardMaterial(), false, texture), false, 'disabling a pristine material changed it');
 assert.equal(setPass4Geometry(new THREE.BufferGeometry(), false), false, 'disabling a pristine geometry changed it');
 // A missing retained preview leaves the material on the baseline path even with the control on.
 const bare = new THREE.MeshStandardMaterial();
 assert.equal(setPass4Material(bare, true, null), false, 'the environment term installed without a sampled texture');
 assert.deepEqual(Object.keys(bare.userData), []);

 const note = state.setEnabled(true, camera);
 assert.match(note, /^Game shading \(candidate\) on \(COBRA\): 1 of 2 source primitives carry an established pass-4 assignment; the rest are unchanged\./);
 assert.ok(note.endsWith(PASS4_CAVEAT), 'the on state does not carry the recorded caveat');
 assert.notEqual(material.onBeforeCompile, baseline.onBeforeCompile, 'the assigned material took no environment term');
 assert.deepEqual(Object.keys(material.userData), ['pass4']);
 assert.ok(geometry.getAttribute('pass4Env'), 'the assigned geometry has no environment attribute');
 assert.equal(geometry.getAttribute('pass4Env').itemSize, 3);
 assert.equal(unassigned.geometry.getAttribute('pass4Env'), undefined, 'an unassigned part took the environment lookup');
 assert.equal(unassigned.material.onBeforeCompile, before.onBeforeCompile, 'an unassigned part changed material');
 assert.deepEqual(Object.keys(unassigned.geometry.attributes), before.attributes);
 assert.equal(untouched.material.onBeforeCompile, untouched.material.onBeforeCompile);

 const shader = {uniforms: {}, vertexShader: 'void main(){\n#include <begin_vertex>\n}', fragmentShader: 'void main(){\n#include <opaque_fragment>\n}'};
 material.onBeforeCompile(shader);
 assert.match(shader.vertexShader, /attribute vec3 pass4Env;/, 'the environment attribute is not declared');
 assert.match(shader.vertexShader, /include <begin_vertex>\n vPass4Environment = pass4Env;/, 'the varying is not filled from the attribute');
 assert.match(shader.fragmentShader, /uniform sampler2D pass4Texture;/, 'the sampled texture is not a uniform');
 assert.match(shader.fragmentShader, /gl_FragColor\.rgb \+= texture2D\(pass4Texture, vPass4Environment\.xy\)\.rgb \* diffuseColor\.rgb \* vPass4Environment\.z;/,
              'the environment term is not the decoded colour factor times the sampled texel');
 assert.equal(shader.uniforms.pass4Texture.value, texture);

 const first = Float32Array.from(geometry.getAttribute('pass4Env').array);
 const moved = new THREE.PerspectiveCamera(40, 1, .01, 100);
 moved.position.set(-3, 0.5, 1);
 moved.updateMatrixWorld(true);
 state.follow(moved);
 const second = Float32Array.from(geometry.getAttribute('pass4Env').array);
 assert.notDeepEqual(second, first, 'the lookup does not move when the view moves');
 assert.match(state.status(), /Colour factor \d\.\d\d–\d\.\d\d at this view\./, 'the view-dependent factor range is not reported');
 state.follow(moved);
 assert.deepEqual(Float32Array.from(geometry.getAttribute('pass4Env').array), second, 'an unchanged view rewrote the lookup');

 assert.equal(state.setEnabled(false), '');
 assert.equal(material.onBeforeCompile, baseline.onBeforeCompile, 'off did not restore the baseline callback');
 assert.equal(material.customProgramCacheKey, baseline.cache, 'off did not restore the baseline program cache key');
 assert.deepEqual(Object.keys(material.userData), baseline.userData, 'off left a material marker');
 assert.deepEqual(Object.keys(geometry.attributes), baseline.attributes, 'off left the environment attribute');
 console.log('PASS game shading baseline: materials and geometry return exactly to the pre-control state');
}

function testUnassignedPartsAreUnchanged(table) {
 const mesh = fixtureMesh(1004525);
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(3, 2, 5);
 camera.updateMatrixWorld(true);
 const state = createPass4State({assignments: table, texture: new THREE.Texture()});
 state.attach([mesh], 'ford-racing-2', 'GRAN_TORINO');
 const note = state.setEnabled(true, camera);
 assert.match(note, /^Game shading \(candidate\) on \(GRAN_TORINO\): no established pass-4 assignment covers this car, so every part renders exactly as before\./);
 assert.ok(note.endsWith(PASS4_CAVEAT));
 assert.equal(state.assigned, 0);
 assert.equal(mesh.geometry.getAttribute('pass4Env'), undefined);
 assert.equal(mesh.material.onBeforeCompile, new THREE.MeshStandardMaterial().onBeforeCompile);
 assert.equal(assignedOffsets(table, 'ford-racing-2', 'GRAN_TORINO'), null);
 assert.equal(assignedOffsets(table, 'gran-turismo', 'COBRA'), null, 'the table is not scoped by game');
 const empty = createPass4State({});
 empty.attach([mesh], 'ford-racing-2', 'COBRA');
 assert.equal(empty.assigned, 0, 'a missing table assigned Headers');
 console.log('PASS game shading unassigned: cars and parts outside the join are untouched and say so');
}

function testDecodedArithmetic() {
 assert.equal(pass4Factor(1), 1, 'a positive dot product must clamp the factor to 1');
 assert.equal(pass4Factor(0), 1);
 assert.ok(Math.abs(pass4Factor(-1) - 0.05) < 1e-7, 'the factor at d = -1 is not 1 - 0.95');
 assert.ok(pass4Factor(-4) < 0.05);
 const identity = [1, 0, 0, 0, 1, 0, 0, 0, 1];
 const flat = pass4Vertex([0, 0, -2, 1], [0, 1, 0], [0, 0, 0], identity, 1);
 assert.deepEqual([flat.u, flat.v], [0.5, 0.5], 'a centred reflection is not at the map centre');
 assert.equal(flat.factor, 1);
 assert.deepEqual(pass4Vertex([0, 0, -2, 1], [0, 1, 0], [0, 0, 0], identity, 0.5).s, 0.25, 's is not u times Q');
 const side = pass4Vertex([1, 0, -2, 1], [0, 1, 0], [0, 0, 0], identity, 1);
 // R = -V, so the vertex one unit along +x maps to x' = -1 and u = 0.5*(-1)*(-1/3)+0.5.
 assert.ok(Math.abs(side.u - (0.5 * (-1) * (1 / -3) + 0.5)) < 1e-6, 'the x translation is missing or has the wrong sign');
 assert.ok(Math.abs(side.v - 0.5) < 1e-7, 'a reflection with no y component is not at v = 0.5');
 const above = pass4Vertex([0, 1, -2, 1], [0, 1, 0], [0, 0, 0], identity, 1);
 assert.equal(above.factor, 1, 'd = 1 must clamp the factor to 1');
 assert.ok(Math.abs(above.v - 0.6666667) < 1e-6, 'the negative y translation is missing');
 const dim = pass4Vertex([0, -1, -2, 1], [0, 1, 0], [0, 0, 0], identity, 1, [128, 64, 32]);
 assert.ok(Math.abs(dim.factor - 0.05) < 1e-7);
 assert.deepEqual(dim.rgb, [6, 3, 1], 'the colour lanes are not ftoi0(paint * factor)');
 const rotation = pass4Matrix(new THREE.Matrix4().makeRotationY(Math.PI / 2));
 assert.ok(Math.abs(rotation[0]) < 1e-9 && Math.abs(rotation[4] - 1) < 1e-9, 'the matrix is not the camera world basis');
 assert.ok(Math.abs(rotation[2] + 1) < 1e-9, 'the third column of the view basis differs');
 console.log('PASS game shading arithmetic: decoded factor, paraboloid coordinates and colour relation');
}

function testShippedJoin(table) {
 const listed = new Set(table.cars.flatMap(car => car.offsets));
 let matched = 0;
 for (const car of read('../dealership/public/models.json').cars.filter(entry => entry.game === 'ford-racing-2')) {
  const doc = glbDocument(new URL('../dealership/public/' + car.file, import.meta.url));
  const primitives = doc.meshes.flatMap(mesh => mesh.primitives);
  const row = table.cars.find(entry => entry.code === car.code);
  const byOffset = new Map(primitives.map(primitive => [primitive.extras?.headerOffset, primitive.extras?.flags]));
  (row ? row.offsets : []).forEach((offset, index) => {
   assert.equal(byOffset.get(offset), row.flags[index], `${car.code}: Header ${offset} is not in the shipped model with those flags`);
   matched += 1;
  });
  if (!row) {
   // Header offsets are per-model file offsets and coincide numerically across cars (EX shares 34
   // values with COBRA); the lookup is scoped by game and code, exercised above and below.
   assert.equal(assignedOffsets(table, car.game, car.code), null, `${car.code} is not in the table`);
   assert.ok(primitives.length, `${car.code} has no shipped primitives to compare`);
  }
 }
 assert.equal(matched, 37, 'the table does not join all 37 aligned pass-4 Headers to the shipped model');
 console.log(`PASS game shading join: ${matched} pass-4 Headers on COBRA match the shipped GLB primitives`);
}

function capturedVectors() {
 const captured = read('../research/evidence/vu-dispatch/handler-dump-comparison.json').rows.find(row => row.pass_word === 4);
 const floats = words => words.map(word => new DataView(new Uint32Array([word]).buffer).getFloat32(0, true));
 const matrix = captured.retained_top12_14_u32.map(lanes => floats(lanes).slice(0, 3)).flat();
 const eye = floats(captured.retained_dm7_source_top23_u32).slice(0, 3);
 const identity = [1, 0, 0, 0, 1, 0, 0, 0, 1];
 return [
  {position: [0.62, 0.86, 1.34, 1], normal: [0, 0.99, 0.14], eye, rows: matrix, q: 1, colour: [128, 128, 128]},
  {position: [0.62, 0.86, 1.34, 0.5], normal: [0.7, 0.7, 0], eye, rows: matrix, q: 1, colour: [96, 128, 160]},
  {position: [-0.75, 0.42, 0.9, 1], normal: [-0.6, 0.8, 0], eye, rows: matrix, q: 1.75, colour: [128, 90, 40]},
  {position: [0, 1, -2, 1], normal: [0, 1, 0], eye: [0, 0, 0], rows: identity, q: 1, colour: [128, 128, 128]},
  {position: [1, 0, -2, 1], normal: [0, 1, 0], eye: [0, 0, 0], rows: identity, q: 0.25, colour: [64, 128, 32]},
  {position: [0, -1, -2, 1], normal: [0, 1, 0], eye: [0, 0, 0], rows: identity, q: 1, colour: [128, 64, 32]},
  {position: [-3.5, 2.25, 4.75, 1], normal: [0.3, -0.8, 0.5], eye: [-3, 1, 2], rows: [0.5, 0, 0, 0, 0.5, 0, 0, 0, 0.5], q: 2, colour: [128, 128, 128]},
 ];
}

function compareWithExecutor(vectors, executor, inspector, tolerance = TOLERANCE) {
 assert.equal(inspector.length, vectors.length, 'the inspector did not answer every vector');
 vectors.forEach((vector, index) => {
  const reference = executor.vertices[index], mine = inspector[index];
  for (const key of ['factor', 's', 't']) {
   assert.ok(Math.abs(reference[key] - mine[key]) <= tolerance[key],
             `vector ${index} ${key}: executor ${reference[key]} vs inspector ${mine[key]}`);
  }
  assert.deepEqual(mine.rgb, reference.rgb, `vector ${index} colour lanes differ`);
  assert.ok(Math.abs(mine.s - mine.u * vector.q) <= tolerance.s, `vector ${index} s is not u*Q`);
  assert.ok(Math.abs(mine.t - mine.v * vector.q) <= tolerance.t, `vector ${index} t is not v*Q`);
 });
}

function testExecutorComparison() {
 const selfTest = spawnSync('python3', ['tools/vu_pass4_executor.py', '--self-test'], {cwd: root, encoding: 'utf8'});
 assert.equal(selfTest.status, 0, selfTest.stderr || selfTest.stdout);
 assert.match(selfTest.stdout, /PASS vu_pass4_executor self-test/, 'the executor input mapping did not self-test');
 const vectors = capturedVectors();
 const inspector = vectors.map(vector => pass4Vertex(vector.position, vector.normal, vector.eye, vector.rows, vector.q, vector.colour));
 // The comparator is exercised without the microcode, then with it where the overlays are configured.
 const stub = {entry: 558, vertices: inspector.map(row => ({s: row.s, t: row.t, factor: row.factor, rgb: row.rgb}))};
 compareWithExecutor(vectors, stub, inspector);
 for (const [label, mutate] of [['factor', row => ({...row, factor: row.factor + 1e-3})], ['s', row => ({...row, s: row.s + 1e-3})],
                                ['t', row => ({...row, t: row.t + 1e-3})], ['colour', row => ({...row, rgb: [row.rgb[0] + 1, row.rgb[1], row.rgb[2]]})]]) {
  assert.throws(() => compareWithExecutor(vectors, stub, inspector.map((row, index) => index ? row : mutate(row))),
                `the comparison accepted a changed ${label}`);
 }
 const gate = spawnSync('python3', ['tools/vu_pass4_executor.py', '--available'], {cwd: root, encoding: 'utf8'});
 if (gate.status !== 0) {
  const reason = `${gate.stdout}${gate.stderr}`.trim().split('\n').pop();
  console.log(`SKIP game shading numeric comparison: the pinned VU overlays are not configured (${reason})`);
  return;
 }
 const run = spawnSync('python3', ['tools/vu_pass4_executor.py'], {cwd: root, encoding: 'utf8', input: JSON.stringify({vectors})});
 assert.equal(run.status, 0, run.stderr || run.stdout);
 const executor = JSON.parse(run.stdout);
 assert.equal(executor.entry, 558, 'the pass-4 handler entry differs from the dispatch receipt');
 compareWithExecutor(vectors, executor, inspector);
 const worst = vectors.reduce((value, vector, index) => Math.max(value,
  Math.abs(executor.vertices[index].factor - inspector[index].factor),
  Math.abs(executor.vertices[index].s - inspector[index].s),
  Math.abs(executor.vertices[index].t - inspector[index].t)), 0);
 console.log(`PASS game shading numeric comparison: ${vectors.length} vectors against the real pass-4 handler, worst |Δ| ${worst}`);
}

const table = parsePass4Assignments(read('../dealership/public/game-shading-pass4.json'));
assert.equal(table.cars.length, 1);
assert.throws(() => parsePass4Assignments({schema: 'other', cars: []}), /Unsupported/);
assert.throws(() => parsePass4Assignments({schema: table.schema, cars: [{code: 'B', game: 'g', headers: [{offset: 4, flags: 1}]}, {code: 'A', game: 'g', headers: [{offset: 8, flags: 1}]}]}), /sorted/);
assert.throws(() => parsePass4Assignments({schema: table.schema, cars: [{code: 'A', game: 'g', headers: [{offset: 1.5, flags: 1}]}]}), /usable/);
assert.throws(() => parsePass4Assignments({schema: table.schema, cars: [{code: 'A', headers: [{offset: 8, flags: 1}]}]}), /usable/);
testPageControl();
testBaselineIsUntouched(table);
testUnassignedPartsAreUnchanged(table);
testDecodedArithmetic();
testShippedJoin(table);
testExecutorComparison();
console.log('PASS test_recovered_game_shading');
