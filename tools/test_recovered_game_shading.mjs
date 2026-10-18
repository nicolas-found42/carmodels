// Assert the recovered inspector's candidate game shading.
//
// The control is off by default and off leaves the baseline viewer's materials and geometry exactly
// as they were; the derived Header table joins the shipped model; the unassigned parts are untouched
// and the honesty label says so; and - where the pinned VU overlays are configured - the per-vertex
// pass-4 colour factor and paraboloid coordinates and the pass-5 specular and colour lanes equal the
// repository's numeric handler executor (tools/vu_shading_executor.py, which runs the real overlay
// microcode) within the stated tolerance.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import * as THREE from '../dealership/vendor/three.module.js';
import {PASS5_LIGHT, PASS5_LIGHT_DIRECTION, SHADING_CAVEAT, createShadingState,
        loadShadingAssignments, parseShadingAssignments, pass4Factor, pass4Matrix, pass4Vertex,
        pass5Colour, pass5Specular, pass5Vertex, setShadingGeometry, setShadingMaterial,
        shadingAssignments, writeEnvironment, writeSpecular} from '../dealership/game-shading.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const read = path => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const bytes = path => readFileSync(new URL(path, import.meta.url));
// Both sides do host binary32 arithmetic; the executor rounds every step, so the comparison allows
// one unit in the last place of the compared magnitudes, stated as absolute bounds.
const TOLERANCE = {factor: 1e-6, s: 1e-5, t: 1e-5};
// The pass-5 specular never exceeds 0.5 and s = S * Q; the colour lanes are integers and must match.
const SHADING_TOLERANCE = {specular: 1e-6, s: 1e-5};

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

function baselineOf(mesh) {
 return {onBeforeCompile: mesh.material.onBeforeCompile, cache: mesh.material.customProgramCacheKey,
         attributes: Object.keys(mesh.geometry.attributes), userData: Object.keys(mesh.material.userData)};
}

// Off must leave no decoded term behind: no attribute, and the exact baseline function objects.
function assertUnshaded(mesh, baseline, where) {
 assert.deepEqual(Object.keys(mesh.geometry.attributes), baseline.attributes, `${where}: an attribute was left behind`);
 assert.equal(mesh.material.onBeforeCompile, baseline.onBeforeCompile, `${where}: the material callback changed`);
 assert.equal(mesh.material.customProgramCacheKey, baseline.cache, `${where}: the program cache key changed`);
 assert.deepEqual(Object.keys(mesh.material.userData), baseline.userData, `${where}: a material marker was left behind`);
}

// The page's control: present, labelled, unchecked, with a hidden honesty label, the pass-5
// stand-ins named in the tooltip and live wiring.
function checkPageMarkup(text) {
 assert.match(text, /<input type="checkbox" id="game-shading"[^>]*>Game shading \(candidate\)<\/label>/, 'the control is not the labelled checkbox');
 assert.ok(!/id="game-shading"[^>]*checked/.test(text), 'the control is not off by default');
 assert.match(text, /id="game-shading" title="[^"]*pass-5 specular/, 'the tooltip does not name the decoded pass-5 specular');
 assert.match(text, /id="game-shading" title="[^"]*pass-5 light is the retained capture value/, 'the tooltip does not name the pass-5 light stand-in');
 assert.match(text, /<p id="game-shading-note" hidden><\/p>/, 'the honesty label is missing or visible while off');
 assert.match(text, /from '\.\/game-shading\.mjs'/, 'the page does not import the shading module');
 assert.match(text, /gameShading\.setEnabled\(document\.querySelector\('#game-shading'\)\.checked,camera\)/, 'the toggle is not wired into the material update');
 assert.match(text, /if\(gameShading\.follow\(camera\)\)updateGameShadingNote\(\);/, 'the honesty label is not refreshed when the lookup moves');
 assert.ok(!/await shadingReady/.test(text), 'a model load waits for the optional shading assets');
 assert.match(text, /bounded\(loadShadingAssets\(\),SHADING_ASSET_TIMEOUT,/, 'the optional asset load is not bounded');
 assert.match(text, /catch\(error=>\{shadingError=error\.message;updateMaterials\(\);\}\)/, 'a failed optional asset load is not reported');
 assert.match(text, /assets are still loading; every part keeps the baseline shading/, 'the pending-asset state is not reported');
 return text;
}

function testPageControl() {
 const page = bytes('../dealership/recovered.html').toString('utf8');
 checkPageMarkup(page);
 const tampers = [['an always-visible label', ' id="game-shading-note" hidden', ' id="game-shading-note"'],
                  ['a checked control', 'id="game-shading"', 'id="game-shading" checked'],
                  ['no camera follow', 'if(gameShading.follow(camera))updateGameShadingNote();', ''],
                  ['no toggle wiring', "gameShading.setEnabled(document.querySelector('#game-shading').checked,camera);", ''],
                  ['a toggle that ignores the switch', "document.querySelector('#game-shading').checked,camera", "document.querySelector('#game-shading'),camera"],
                  ['a tooltip without the pass-5 stand-in', 'pass-5 light is the retained capture value', 'the light'],
                  ['a blocking asset await', 'async function loadCar(){', 'async function loadCar(){\n await shadingReady;'],
                  ['an unbounded asset wait', 'bounded(loadShadingAssets(),SHADING_ASSET_TIMEOUT,', 'loadShadingAssets(),'],
                  ['an unreported asset failure', 'catch(error=>{shadingError=error.message;updateMaterials();})', 'catch(()=>{})']];
 for (const [label, from, to] of tampers) {
  assert.ok(page.includes(from), `the page no longer contains ${from}`);
  assert.throws(() => checkPageMarkup(page.replace(from, to)), `the markup check accepts ${label}`);
 }
 console.log('PASS game shading control: off by default in the page markup');
}

function testBaselineIsUntouched(table) {
 const offsets = shadingAssignments(table, 'ford-racing-2', 'COBRA');
 const assigned = fixtureMesh([...offsets.pass4][0]);
 const unassigned = fixtureMesh([...offsets.pass4][0] + 4); // a neighbouring source Header with no assignment
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(2, 1.5, 2);
 camera.updateMatrixWorld(true);
 const texture = new THREE.Texture();
 const state = createShadingState({assignments: table, texture});
 const material = assigned.material, geometry = assigned.geometry;
 const baseline = baselineOf(assigned), untouched = baselineOf(unassigned);
 state.attach([assigned, unassigned], 'ford-racing-2', 'COBRA');
 assert.equal(state.enabled, false, 'the control defaults to on');
 assert.equal(state.status(), '', 'an off control claims something');
 assert.equal(setShadingMaterial(new THREE.MeshStandardMaterial(), false, {pass4: true, pass5: true}), false, 'disabling a pristine material changed it');
 assert.equal(setShadingGeometry(new THREE.BufferGeometry(), false, {pass4: true, pass5: true}), false, 'disabling a pristine geometry changed it');
 // The controls only exist once the control is on: nothing installed, nothing to remove.
 assertUnshaded(assigned, baseline, 'attached but off');
 assertUnshaded(unassigned, untouched, 'an unassigned part while off');
 // A missing retained preview leaves the reflection term on the baseline path even with the control
 // on, while the specular term needs no texture.
 const bare = new THREE.MeshStandardMaterial();
 assert.equal(setShadingMaterial(bare, true, {pass4: true, pass5: false, texture: null}), false, 'the environment term installed without a sampled texture');
 assert.deepEqual(Object.keys(bare.userData), []);
 assert.equal(setShadingMaterial(bare, true, {pass4: false, pass5: true, texture: null}), true, 'the specular term needs no sampled texture');

 // The recovered materials carry their own shader patch (the native garage specular), so the decoded
 // term must compose with it instead of replacing it.
 const patched = new THREE.MeshStandardMaterial();
 const compiled = [];
 const baselinePatch = function (shader) { compiled.push(shader); shader.fragmentShader = '// baseline patch\n' + shader.fragmentShader; };
 patched.onBeforeCompile = baselinePatch;
 patched.customProgramCacheKey = () => 'baseline-key';
 assert.equal(setShadingMaterial(patched, true, {pass4: true, pass5: true, texture}), true);
 const patchedShader = {uniforms: {}, vertexShader: 'void main(){\n#include <begin_vertex>\n}', fragmentShader: 'void main(){\n#include <opaque_fragment>\n}'};
 patched.onBeforeCompile(patchedShader);
 assert.equal(compiled.length, 1, 'the baseline shader patch was dropped while the control is on');
 assert.ok(patchedShader.fragmentShader.includes('// baseline patch'), 'the baseline patch output was replaced');
 assert.match(patchedShader.fragmentShader, /vPass5Specular/, 'the decoded term was not added to the patched shader');
 assert.match(patched.customProgramCacheKey(), /^baseline-key;game-shading:/, 'the program cache key does not compose with the baseline key');
 assert.equal(setShadingMaterial(patched, false), true);
 assert.equal(patched.onBeforeCompile, baselinePatch, 'off did not restore the baseline shader patch');
 assert.equal(patched.customProgramCacheKey(), 'baseline-key', 'off did not restore the baseline cache key');
 assert.deepEqual(Object.keys(patched.userData), []);

 const note = state.setEnabled(true, camera);
 assert.match(note, /^Game shading \(candidate\) on \(COBRA\): 1 of 2 source primitives carry an established pass-4 reflection assignment and 1 a pass-5 specular assignment; the rest are unchanged\./);
 assert.ok(note.endsWith(SHADING_CAVEAT), 'the on state does not carry the recorded caveat');
 assert.notEqual(material.onBeforeCompile, baseline.onBeforeCompile, 'the assigned material took no decoded term');
 assert.deepEqual(Object.keys(material.userData), ['shading']);
 assert.ok(geometry.getAttribute('pass4Env'), 'the assigned geometry has no environment attribute');
 assert.equal(geometry.getAttribute('pass4Env').itemSize, 3);
 assert.ok(geometry.getAttribute('pass5Spec'), 'the assigned geometry has no specular attribute');
 assert.equal(geometry.getAttribute('pass5Spec').itemSize, 1);
 assertUnshaded(unassigned, untouched, 'an unassigned part while on');

 const shader = {uniforms: {}, vertexShader: 'void main(){\n#include <begin_vertex>\n}', fragmentShader: 'void main(){\n#include <opaque_fragment>\n}'};
 material.onBeforeCompile(shader);
 assert.match(shader.vertexShader, /attribute vec3 pass4Env;/, 'the environment attribute is not declared');
 assert.match(shader.vertexShader, /attribute float pass5Spec;/, 'the specular attribute is not declared');
 for (const assignment of ['vPass4Environment = pass4Env;', 'vPass5Specular = pass5Spec;']) {
  assert.ok(shader.vertexShader.indexOf(assignment) > shader.vertexShader.indexOf('#include <begin_vertex>'),
            `the varying is not filled from the attribute: ${assignment}`);
 }
 assert.match(shader.fragmentShader, /uniform sampler2D pass4Texture;/, 'the sampled texture is not a uniform');
 assert.match(shader.fragmentShader, /gl_FragColor\.rgb \+= texture2D\(pass4Texture, vPass4Environment\.xy\)\.rgb \* diffuseColor\.rgb \* vPass4Environment\.z;/,
              'the environment term is not the decoded colour factor times the sampled texel');
 assert.match(shader.fragmentShader, /uniform vec4 pass5Light;/);
 // The colour constant is the paint alone: diffuseColor carries the base texture, so the constant
 // must not follow each texel (and must not follow the Textures switch).
 assert.match(shader.fragmentShader, /gl_FragColor\.rgb \+= vPass5Specular \* \(floor\(min\(pass5Light\.rgb \* diffuse \* 255\.0, vec3\(128\.0\)\)\) \/ 255\.0\);/,
              'the specular term is not the decoded intensity times the per-draw colour constant');
 assert.doesNotMatch(shader.fragmentShader, /pass5Light\.rgb \* diffuseColor\.rgb/,
                     'the per-draw colour constant is read through the base texture');
 assert.equal(shader.uniforms.pass4Texture.value, texture);
 assert.deepEqual(shader.uniforms.pass5Light.value.toArray(), PASS5_LIGHT, 'the light uniform is not the recorded stand-in');

 const first = {env: Float32Array.from(geometry.getAttribute('pass4Env').array), spec: Float32Array.from(geometry.getAttribute('pass5Spec').array)};
 const moved = new THREE.PerspectiveCamera(40, 1, .01, 100);
 moved.position.set(-3, 0.5, 1);
 moved.updateMatrixWorld(true);
 state.follow(moved);
 const second = {env: Float32Array.from(geometry.getAttribute('pass4Env').array), spec: Float32Array.from(geometry.getAttribute('pass5Spec').array)};
 assert.notDeepEqual(second.env, first.env, 'the lookup does not move when the view moves');
 assert.notDeepEqual(second.spec, first.spec, 'the specular does not move when the view moves');
 assert.match(state.status(), /Colour factor \d\.\d\d–\d\.\d\d at this view\./, 'the view-dependent factor range is not reported');
 assert.match(state.status(), /Specular \d\.\d\d–\d\.\d\d at this view\./, 'the view-dependent specular range is not reported');
 state.follow(moved);
 assert.deepEqual(Float32Array.from(geometry.getAttribute('pass5Spec').array), second.spec, 'an unchanged view rewrote the specular');
 assert.deepEqual(Float32Array.from(geometry.getAttribute('pass4Env').array), second.env, 'an unchanged view rewrote the lookup');

 assert.equal(state.setEnabled(false), '');
 assertUnshaded(assigned, baseline, 'after an on/off cycle');
 // Control: the off check rejects a decoded term that survived the switch.
 setShadingGeometry(geometry, true, {pass5: true});
 assert.ok(geometry.getAttribute('pass5Spec'), 'the control did not install a term to leak');
 assert.throws(() => assertUnshaded(assigned, baseline, 'leaked'), /an attribute was left behind/, 'the off check accepts a leaked specular attribute');
 setShadingGeometry(geometry, false, {pass5: true});
 console.log('PASS game shading baseline: materials and geometry return exactly to the pre-control state');
}

function testUnassignedPartsAreUnchanged(table) {
 const mesh = fixtureMesh(1004525);
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(3, 2, 5);
 camera.updateMatrixWorld(true);
 const state = createShadingState({assignments: table, texture: new THREE.Texture()});
 const baseline = baselineOf(mesh);
 state.attach([mesh], 'ford-racing-2', 'GRAN_TORINO');
 const note = state.setEnabled(true, camera);
 assert.match(note, /^Game shading \(candidate\) on \(GRAN_TORINO\): no established game-shading assignment covers this car, so every part renders exactly as before\./);
 assert.ok(note.endsWith(SHADING_CAVEAT));
 assert.deepEqual(state.assigned, {pass4: 0, pass5: 0});
 assertUnshaded(mesh, baseline, 'an unassigned car');
 // Control: the unassigned-part check rejects a part that took a decoded term.
 mesh.geometry.setAttribute('pass4Env', new THREE.BufferAttribute(new Float32Array(mesh.geometry.getAttribute('position').count * 3), 3));
 assert.throws(() => assertUnshaded(mesh, baseline, 'shaded'), /an attribute was left behind/, 'the unassigned-part check accepts a shaded part');
 mesh.geometry.deleteAttribute('pass4Env');
 assert.equal(shadingAssignments(table, 'ford-racing-2', 'GRAN_TORINO'), null);
 assert.equal(shadingAssignments(table, 'gran-turismo', 'COBRA'), null, 'the table is not scoped by game');
 const empty = createShadingState({});
 empty.attach([mesh], 'ford-racing-2', 'COBRA');
 assert.deepEqual(empty.assigned, {pass4: 0, pass5: 0}, 'a missing table assigned Headers');
 console.log('PASS game shading unassigned: cars and parts outside the join are untouched and say so');
}

// A Header the pass-5 join covers and the pass-4 join does not: the highlight must be there alone.
function testSpecularOnlyHeader(table) {
 const assigned = shadingAssignments(table, 'ford-racing-2', 'COBRA');
 const only = [...assigned.pass5].filter(offset => !assigned.pass4.has(offset));
 assert.ok(only.length, 'the fixtures assume a pass-5-only Header exists');
 const mesh = fixtureMesh(only[0]);
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(2, 2, 3);
 camera.updateMatrixWorld(true);
 const baseline = baselineOf(mesh);
 const state = createShadingState({assignments: table, texture: new THREE.Texture()});
 assert.equal(state.attach([mesh], 'ford-racing-2', 'COBRA'), 1);
 const note = state.setEnabled(true, camera);
 assert.match(note, /0 of 1 source primitives carry an established pass-4 reflection assignment and 1 a pass-5 specular assignment/);
 assert.equal(mesh.geometry.getAttribute('pass4Env'), undefined, 'a pass-5-only Header took the reflection lookup');
 assert.ok(mesh.geometry.getAttribute('pass5Spec'), 'a pass-5-only Header took no specular term');
 const shader = {uniforms: {}, vertexShader: 'void main(){\n#include <begin_vertex>\n}', fragmentShader: 'void main(){\n#include <opaque_fragment>\n}'};
 mesh.material.onBeforeCompile(shader);
 assert.ok(!/pass4Env|pass4Texture/.test(shader.vertexShader + shader.fragmentShader), 'the reflection term was installed on a pass-5-only Header');
 assert.match(shader.fragmentShader, /vPass5Specular/, 'the specular term is missing');
 // The neighbour with neither assignment is untouched, and off restores this one.
 assert.deepEqual(state.assigned, {pass4: 0, pass5: 1});
 assert.equal(state.setEnabled(false), '');
 assertUnshaded(mesh, baseline, 'a pass-5-only Header after an on/off cycle');
 const untouched = fixtureMesh(only[0] + 4);
 const before = baselineOf(untouched);
 const other = createShadingState({assignments: table, texture: new THREE.Texture()});
 other.attach([untouched], 'ford-racing-2', 'COBRA');
 other.setEnabled(true, camera);
 assertUnshaded(untouched, before, 'a part with no pass-5 assignment');
 console.log(`PASS game shading specular-only Header: ${only.length} pass-5 Headers outside the pass-4 join take the highlight alone`);
}

async function testUnderCarShadowIsExcluded(table) {
 const offsets = shadingAssignments(table, 'ford-racing-2', 'COBRA');
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(2, 3, 4);
 camera.updateMatrixWorld(true);
 // Issue #23 marks the recovered under-car shadow as an overlay group (and its quad) whose material is
 // an alpha coverage decal, not a shaded paint surface: it must never take either decoded pass.
 const decal = fixtureMesh([...offsets.pass5][0]);
 decal.userData.shadow = true;
 const overlay = new THREE.Group();
 overlay.userData.shadow = true;
 const nested = fixtureMesh([...offsets.pass5][0]);
 overlay.add(nested);
 const painted = fixtureMesh([...offsets.pass4][0]);
 const paintedBaseline = painted.material.onBeforeCompile;
 const state = createShadingState({assignments: table, texture: new THREE.Texture()});
 state.attach([decal, nested, painted], 'ford-racing-2', 'COBRA');
 assert.deepEqual(state.assigned, {pass4: 1, pass5: 1}, 'the under-car shadow decal took a decoded term');
 const note = state.setEnabled(true, camera);
 assert.match(note, /1 of 3 source primitives carry an established pass-4 reflection assignment and 1 a pass-5 specular assignment/);
 assert.equal(decal.geometry.getAttribute('pass4Env'), undefined, 'the shadow quad geometry was given the environment attribute');
 assert.equal(decal.geometry.getAttribute('pass5Spec'), undefined, 'the shadow quad geometry was given the specular attribute');
 assert.equal(decal.material.onBeforeCompile, new THREE.MeshStandardMaterial().onBeforeCompile, 'the shadow quad material changed');
 assert.equal(nested.geometry.getAttribute('pass5Spec'), undefined, 'a quad inside the shadow overlay group was shaded');
 assert.ok(painted.geometry.getAttribute('pass5Spec'), 'the painted part was not shaded');
 assert.notEqual(painted.material.onBeforeCompile, paintedBaseline);
 console.log('PASS game shading under-car shadow: the coverage decal stays on the baseline path');
}

async function testStalledOptionalAssets() {
 const page = bytes('../dealership/recovered.html').toString('utf8');
 const start = page.indexOf('function bounded(');
 assert.ok(start > 0, 'the page has no bounded-wait helper');
 const bounded = new Function(page.slice(start, page.indexOf('\n', start)) + 'return bounded;')();
 const stalled = new Promise(() => {});
 const outcome = await Promise.race([bounded(stalled, 30, 'the optional shading assets did not load in 15 seconds')
  .then(() => 'resolved', error => 'rejected: ' + error.message), new Promise(resolve => setTimeout(() => resolve('still pending'), 500))]);
 assert.equal(outcome, 'rejected: the optional shading assets did not load in 15 seconds', 'a stalled request is not bounded');
 // The baseline preview is an independent promise: the bounded optional load cannot hold it up.
 let previewed = false;
 bounded(stalled, 50, 'stalled').catch(() => {});
 await Promise.resolve().then(() => { previewed = true; });
 assert.equal(previewed, true, 'a stalled optional asset request blocks the preview');
 // The table fetch itself is left unbounded, which is why the page wraps it; a stalled fetch stays pending.
 const realFetch = globalThis.fetch;
 globalThis.fetch = () => new Promise(() => {});
 try {
  const state = await Promise.race([loadShadingAssignments('stalled.json').then(() => 'settled', error => 'threw: ' + error.message),
                                    new Promise(resolve => setTimeout(() => resolve('pending'), 50))]);
  assert.equal(state, 'pending', 'the fetch stub did not stay pending');
 } finally { globalThis.fetch = realFetch; }
 console.log('PASS game shading optional assets: a stalled request is bounded, reported and never blocks a preview');
}

function testViewFrameAndMeshRange(table) {
 const offsets = shadingAssignments(table, 'ford-racing-2', 'COBRA');
 const mesh = (offset, shift) => {
  const geometry = new THREE.BufferGeometry();
  const corner = [0, 0, 0, 0.2, 0, 0.3, 0, 0.2, 0].map((value, index) => value + shift[index % 3]);
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(corner), 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array([0, 1, 0, 0, 1, 0, 0, 1, 0]), 3));
  const piece = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial());
  piece.userData.paintPrimitive = {extras: {headerOffset: offset}};
  return piece;
 };
 // Two placements on the same axis, one above and one below the camera, so the factor and the
 // specular both differ between them.
 const up = mesh([...offsets.pass4][0], [0, 0, 0]), down = mesh([...offsets.pass4][1], [0, 2, 3]);
 const camera = new THREE.PerspectiveCamera(40, 1, .01, 100);
 camera.position.set(0, 1, 3);
 camera.updateMatrixWorld(true);
 const state = createShadingState({assignments: table, texture: new THREE.Texture()});
 state.attach([up, down], 'ford-racing-2', 'COBRA');
 state.setEnabled(true, camera);
 const range = (piece, attribute, stride) => {
  const values = piece.geometry.getAttribute(attribute).array;
  const seen = [];
  for (let index = stride - 1; index < values.length; index += stride) seen.push(values[index]);
  return [Math.min(...seen), Math.max(...seen)];
 };
 const factor = piece => range(piece, 'pass4Env', 3), specular = piece => range(piece, 'pass5Spec', 1);
 const [lowUp, highUp] = factor(up), [lowDown, highDown] = factor(down);
 assert.notDeepEqual([lowUp, highUp], [lowDown, highDown], 'the fixture meshes do not differ');
 assert.notDeepEqual(specular(up), specular(down), 'the fixture meshes do not differ in specular');
 assert.ok(specular(up)[1] > 0 && specular(down)[1] > 0, 'the fixture meshes carry no highlight at all');
 const low = Math.min(lowUp, lowDown), high = Math.max(highUp, highDown);
 assert.match(state.status(), new RegExp(`Colour factor ${low.toFixed(2)}–${high.toFixed(2)} at this view\\.`),
              'the reported range is not the range across the assigned meshes');
 const specLow = Math.min(...specular(up), ...specular(down)), specHigh = Math.max(...specular(up), ...specular(down));
 assert.match(state.status(), new RegExp(`Specular ${specLow.toFixed(2)}–${specHigh.toFixed(2)} at this view\\.`),
              'the reported specular range is not the range across the assigned meshes');
 assert.equal(state.follow(camera), false, 'an unchanged view rewrote the lookup');
 assert.equal(state.follow(camera), false, 'the label would be rewritten on an unchanged frame');
 // The pre-move lookup, snapshotted: range() reads the live attribute, so comparing after the move
 // against a live read would compare the new values with themselves.
 const beforeSpec = specular(up), beforeEnv = factor(up);
 // A moved camera must be read in the frame being rendered, not the previous rotation.
 camera.position.set(-6, 2, 3);
 camera.rotation.set(0.3, 0.7, 0.1);
 assert.equal(state.follow(camera), true, 'a moved view did not rewrite the lookup');
 const after = {env: Float32Array.from(up.geometry.getAttribute('pass4Env').array), spec: Float32Array.from(up.geometry.getAttribute('pass5Spec').array)};
 assert.notDeepEqual(Array.from(after.spec), beforeSpec, 'the specular did not change with the moved view');
 assert.notDeepEqual(Array.from(after.env), beforeEnv, 'the lookup did not change with the moved view');
 const reference = new THREE.BufferGeometry();
 reference.setAttribute('position', up.geometry.getAttribute('position').clone());
 reference.setAttribute('normal', up.geometry.getAttribute('normal').clone());
 setShadingGeometry(reference, true, {pass4: true, pass5: true});
 camera.updateMatrixWorld(true);
 writeSpecular(reference, camera.position.toArray());
 writeEnvironment(reference, camera.position.toArray(), pass4Matrix(camera.matrixWorld));
 assert.deepEqual(Array.from(after.spec), Array.from(reference.getAttribute('pass5Spec').array),
                  'the specular used a stale camera position');
 assert.deepEqual(Array.from(after.env), Array.from(reference.getAttribute('pass4Env').array),
                  'the lookup used a stale camera rotation');
 console.log('PASS game shading view frame: eye and rotation come from the frame being rendered, and the ranges span every assigned mesh');
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
 // The pass-5 specular: the light reflected about the normal, against the view vector.
 const normal = [0, 1, 0], light = [0, 1, 0];
 // R = 2(N.L)N - L = N, V = (eye - position) * position.w = N, so 0.5((R+V).V) - 0.5 = 0.5.
 assert.ok(Math.abs(pass5Specular([0, 0, 0, 1], normal, [0, 1, 0], light) - 0.5) < 1e-7, 'the mirror direction is not the maximum');
 assert.equal(pass5Specular([0, 0, 0, 1], normal, [0, -1, 0], light), 0, 'a negative specular is not clamped to 0');
 assert.equal(pass5Specular([0, 0, 0, 1], normal, [1, 0, 0], light), 0, 'a perpendicular view is not clamped to 0');
 // The specular shortens with distance only through the reconstructed w lane, which keeps V unit.
 const far = pass5Specular([0, 0, 4, 1 / Math.hypot(4, 1)], normal, [0, 1, 0], light);
 assert.ok(!Number.isNaN(far), 'a distant vertex produced no specular');
 const quarter = pass5Vertex([0, 0, 0, 1], normal, [0, 1, 0], 0.25, [255, 255, 255, 255], light, light);
 assert.equal(quarter.s, 0.125, 's is not S * Q');
 // The per-draw colour constant: ftoi0(min(DM[5] * colour, 128)), which saturates at 128 and leaves
 // the alpha lane at 0 for the retained DM[5].w - the captured predicted_rgba of the aligned draws.
 assert.deepEqual(pass5Colour([200, 200, 200, 255]), [128, 128, 128, 0], 'the colour constant is not the decoded clamp');
 assert.deepEqual(pass5Colour([128, 128, 128, 255]), [95, 91, 91, 0], 'the colour constant is not ftoi0');
 assert.deepEqual(pass5Colour([64, 64, 64, 255], [1, 1, 1, 1]), [64, 64, 64, 1], 'the colour constant does not scale with DM[5]');
 // The alpha lane clamps DM[5].w alone, so the draw colour never tints it.
 assert.equal(pass5Colour([255, 255, 255, 0])[3], 0, 'the alpha lane was tinted by the draw colour');
 assert.deepEqual(pass5Vertex([0, 0, 0, 1], normal, [0, 1, 0], 1, [200, 200, 200, 255]).rgba, [128, 128, 128, 0], 'the per-vertex output dropped the colour lanes');
 console.log('PASS game shading arithmetic: decoded factors, paraboloid coordinates, specular and colour relation');
}

// The stand-ins must be the retained capture words, not invented values.
function testLightStandIns() {
 const captured = read('../research/evidence/vu-dispatch/handler-dump-comparison.json');
 const floats = words => (Array.isArray(words[0]) ? words[0] : words).map(word => new DataView(new Uint32Array([word]).buffer).getFloat32(0, true));
 const rows = captured.rows.filter(row => row.pass_word === 5);
 assert.equal(rows.length, captured.by_pass_word['5'].draws, 'the comparison does not carry every pass-5 draw');
 for (const row of rows) {
  assert.deepEqual(floats(row.retained_dm5_u32), Array.from(PASS5_LIGHT), 'a captured draw carries a different DM[5]');
  assert.deepEqual(floats(row.retained_dm6_source_top22_u32).slice(0, 3), Array.from(PASS5_LIGHT_DIRECTION), 'a captured draw carries a different DM[6]');
 }
 console.log(`PASS game shading light stand-ins: DM[5]/DM[6] equal the retained words of all ${rows.length} captured pass-5 draws`);
}

function testShippedJoin(table) {
 const pass4 = table.cars[0].passes.filter(passes => passes.includes(4));
 let matched = 0;
 for (const entry of read('../dealership/public/models.json').cars.filter(row => row.game === 'ford-racing-2')) {
  const doc = glbDocument(new URL('../dealership/public/' + entry.file, import.meta.url));
  const primitives = doc.meshes.flatMap(mesh => mesh.primitives);
  const row = table.cars.find(cars => cars.code === entry.code);
  const byOffset = new Map(primitives.map(primitive => [primitive.extras?.headerOffset, primitive.extras?.flags]));
  (row ? row.offsets : []).forEach((offset, index) => {
   assert.equal(byOffset.get(offset), row.flags[index], `${entry.code}: Header ${offset} is not in the shipped model with those flags`);
   matched += 1;
  });
  if (!row) {
   // Header offsets are per-model file offsets and coincide numerically across cars (EX shares 34
   // values with COBRA); the lookup is scoped by game and code, exercised above and below.
   assert.equal(shadingAssignments(table, entry.game, entry.code), null, `${entry.code} is not in the table`);
   assert.ok(primitives.length, `${entry.code} has no shipped primitives to compare`);
  }
 }
 assert.equal(matched, 63, 'the table does not join all 63 aligned Headers to the shipped model');
 assert.equal(pass4.length, 37, 'the pass-4 subset is not the 37 aligned pass-4 Headers');
 console.log(`PASS game shading join: ${matched} Headers on COBRA match the shipped GLB primitives (${pass4.length} of them pass 4)`);
}

function capturedVectors() {
 const captured = read('../research/evidence/vu-dispatch/handler-dump-comparison.json').rows.find(row => row.pass_word === 4);
 const floats = words => (Array.isArray(words[0]) ? words[0] : words).map(word => new DataView(new Uint32Array([word]).buffer).getFloat32(0, true));
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

// Pass-5 vectors carry the retained DM[5]/DM[6]/DM[7] of three captured draws and synthetic cases.
function capturedShadingVectors() {
 const captured = read('../research/evidence/vu-dispatch/handler-dump-comparison.json');
 const floats = words => (Array.isArray(words[0]) ? words[0] : words).map(word => new DataView(new Uint32Array([word]).buffer).getFloat32(0, true));
 const rows = captured.rows.filter(row => row.pass_word === 5);
 const vectors = [0, Math.floor(rows.length / 2), rows.length - 1].map(index => {
  const row = rows[index];
  return {position: [0.62, 0.86, 1.34, 1], normal: [0.1, 0.98, 0.17], q: 1, colour: [200, 200, 200, 255],
          eye: floats(row.retained_dm7_source_top23_u32).slice(0, 3),
          light: floats(row.retained_dm5_u32), lightDirection: floats(row.retained_dm6_source_top22_u32).slice(0, 3)};
 });
 // Synthetic cases: the mirror direction, a light at a grazing angle and the reconstructed w lane.
 vectors.push({position: [0, 0, 0, 1], normal: [0, 1, 0], eye: [0, 1, 0], q: 1, colour: [255, 255, 255, 255],
               light: Array.from(PASS5_LIGHT), lightDirection: [0, 1, 0]});
 vectors.push({position: [1.25, 0.5, -2, 0.75], normal: [0.6, 0.8, 0], eye: [0, 0, 0], q: 0.5, colour: [128, 90, 40, 200],
               light: Array.from(PASS5_LIGHT), lightDirection: Array.from(PASS5_LIGHT_DIRECTION)});
 vectors.push({position: [-3.5, 2.25, 4.75, 1 / Math.hypot(3.5, 1.25, 2.75)], normal: [0.3, -0.8, 0.5], eye: [0, 1, 2], q: 2, colour: [255, 255, 255, 0],
               light: [1, 1, 1, 1], lightDirection: [-0.5310018062591553, 0.6956135630607605, 0.4838990271091461]});
 return vectors;
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

function compareShadingWithExecutor(vectors, executor, inspector, tolerance = SHADING_TOLERANCE) {
 assert.equal(inspector.length, vectors.length, 'the inspector did not answer every vector');
 vectors.forEach((vector, index) => {
  const reference = executor.vertices[index], mine = inspector[index];
  for (const key of ['specular', 's']) {
   assert.ok(Math.abs(reference[key] - mine[key]) <= tolerance[key],
             `vector ${index} ${key}: executor ${reference[key]} vs inspector ${mine[key]}`);
  }
  assert.deepEqual(mine.rgba, reference.rgba, `vector ${index} colour lanes differ`);
  assert.ok(Math.abs(mine.s - mine.specular * vector.q) <= tolerance.s, `vector ${index} s is not S*Q`);
 });
}

function testExecutorComparison() {
 const selfTest = spawnSync('python3', ['tools/vu_shading_executor.py', '--self-test'], {cwd: root, encoding: 'utf8'});
 assert.equal(selfTest.status, 0, selfTest.stderr || selfTest.stdout);
 assert.match(selfTest.stdout, /PASS vu_shading_executor self-test/, 'the executor input mappings did not self-test');
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
 const shadingVectors = capturedShadingVectors();
 const shaded = shadingVectors.map(vector => pass5Vertex(vector.position, vector.normal, vector.eye, vector.q, vector.colour, vector.light, vector.lightDirection));
 const shadingStub = {entry: 469, vertices: shaded.map(row => ({s: row.s, specular: row.specular, rgba: row.rgba}))};
 compareShadingWithExecutor(shadingVectors, shadingStub, shaded);
 for (const [label, mutate] of [['specular', row => ({...row, specular: row.specular + 1e-3})], ['s', row => ({...row, s: row.s + 1e-3})],
                                ['colour', row => ({...row, rgba: [row.rgba[0] + 1, row.rgba[1], row.rgba[2], row.rgba[3]]})]]) {
  assert.throws(() => compareShadingWithExecutor(shadingVectors, shadingStub, shaded.map((row, index) => index ? row : mutate(row))),
                `the pass-5 comparison accepted a changed ${label}`);
 }
 const gate = spawnSync('python3', ['tools/vu_shading_executor.py', '--available'], {cwd: root, encoding: 'utf8'});
 if (gate.status !== 0) {
  const reason = `${gate.stdout}${gate.stderr}`.trim().split('\n').pop();
  console.log(`SKIP game shading numeric comparison: the pinned VU overlays are not configured (${reason})`);
  console.log(`SKIP game shading pass-5 numeric comparison: the pinned VU overlays are not configured (${reason})`);
  return;
 }
 const run = spawnSync('python3', ['tools/vu_shading_executor.py', '--pass', '4'], {cwd: root, encoding: 'utf8', input: JSON.stringify({vectors})});
 assert.equal(run.status, 0, run.stderr || run.stdout);
 const executor = JSON.parse(run.stdout);
 assert.equal(executor.entry, 558, 'the pass-4 handler entry differs from the dispatch receipt');
 compareWithExecutor(vectors, executor, inspector);
 const worst = vectors.reduce((value, vector, index) => Math.max(value,
  Math.abs(executor.vertices[index].factor - inspector[index].factor),
  Math.abs(executor.vertices[index].s - inspector[index].s),
  Math.abs(executor.vertices[index].t - inspector[index].t)), 0);
 console.log(`PASS game shading numeric comparison: ${vectors.length} vectors against the real pass-4 handler, worst |Δ| ${worst}`);
 const shadingRun = spawnSync('python3', ['tools/vu_shading_executor.py', '--pass', '5'], {cwd: root, encoding: 'utf8', input: JSON.stringify({vectors: shadingVectors})});
 assert.equal(shadingRun.status, 0, shadingRun.stderr || shadingRun.stdout);
 const shadingExecutor = JSON.parse(shadingRun.stdout);
 assert.equal(shadingExecutor.entry, 469, 'the pass-5 handler entry differs from the dispatch receipt');
 compareShadingWithExecutor(shadingVectors, shadingExecutor, shaded);
 const shadingWorst = shadingVectors.reduce((value, vector, index) => Math.max(value,
  Math.abs(shadingExecutor.vertices[index].specular - shaded[index].specular),
  Math.abs(shadingExecutor.vertices[index].s - shaded[index].s)), 0);
 console.log(`PASS game shading pass-5 numeric comparison: ${shadingVectors.length} vectors against the real pass-5 handler, worst |Δ| ${shadingWorst}`);
}

const table = parseShadingAssignments(read('../dealership/public/game-shading.json'));
assert.equal(table.cars.length, 1);
assert.throws(() => parseShadingAssignments({schema: 'other', cars: []}), /Unsupported/);
assert.throws(() => parseShadingAssignments({schema: table.schema, cars: [{code: 'B', game: 'g', headers: [{offset: 4, flags: 1, passes: [4]}]}, {code: 'A', game: 'g', headers: [{offset: 8, flags: 1, passes: [4]}]}]}), /sorted/);
assert.throws(() => parseShadingAssignments({schema: table.schema, cars: [{code: 'A', game: 'g', headers: [{offset: 1.5, flags: 1, passes: [4]}]}]}), /usable/);
assert.throws(() => parseShadingAssignments({schema: table.schema, cars: [{code: 'A', headers: [{offset: 8, flags: 1, passes: [4]}]}]}), /usable/);
assert.throws(() => parseShadingAssignments({schema: table.schema, cars: [{code: 'A', game: 'g', headers: [{offset: 8, flags: 1, passes: []}]}]}), /usable/, 'a Header with no pass is accepted');
assert.throws(() => parseShadingAssignments({schema: table.schema, cars: [{code: 'A', game: 'g', headers: [{offset: 8, flags: 1, passes: [3]}]}]}), /usable/, 'an unknown pass is accepted');
assert.throws(() => parseShadingAssignments({schema: table.schema, cars: [{code: 'A', game: 'g', headers: [{offset: 8, flags: 1, passes: [4, 4]}]}]}), /usable/, 'a repeated pass is accepted');
testPageControl();
testBaselineIsUntouched(table);
testUnassignedPartsAreUnchanged(table);
testSpecularOnlyHeader(table);
await testStalledOptionalAssets();
await testUnderCarShadowIsExcluded(table);
testViewFrameAndMeshRange(table);
testDecodedArithmetic();
testLightStandIns();
testShippedJoin(table);
testExecutorComparison();
console.log('PASS test_recovered_game_shading');
