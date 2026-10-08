import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import * as THREE from '../viewer/vendor/three.module.js';
import {makeCar, disposeCar, validateCars, fetchCars} from '../viewer/dealership.mjs';

const cars = JSON.parse(fs.readFileSync(new URL('../viewer/public/dealership/cars.json', import.meta.url)));
const dealershipPage = fs.readFileSync(new URL('../viewer/dealership.html',import.meta.url),'utf8');
const sourcePage = fs.readFileSync(new URL('../viewer/recovered.html',import.meta.url),'utf8');
assert.match(dealershipPage,/fetchCars\('\.\/public\/dealership\/cars.json'\)/);
assert(!dealershipPage.includes('silhouette')&&!dealershipPage.includes('Silhouette'),'old visible terminology removed');
assert.match(dealershipPage,/dealership\/models\/\$\{c.code\}\.glb/,'dealership downloads its own copies');
assert.match(sourcePage,/public\/recovered\/index.json/,'source showcase retains its own corpus');
assert.match(sourcePage,/<h1>Source models<\/h1>/);
assert.equal(validateCars(cars).length, 35);
for (const car of cars) {
  const mesh = makeCar(car);
  const bounds = new THREE.Box3().setFromObject(mesh);
  assert(bounds.min.toArray().every(Number.isFinite) && bounds.max.toArray().every(Number.isFinite));
  assert(bounds.min.y >= -1e-6, `${car.code}: tyres penetrate the floor`);
  assert(Math.abs(bounds.min.z + bounds.max.z) < 1e-6, `${car.code}: body extends asymmetrically across its width`);
  assert.equal(mesh.userData.wheels.length, car.model.parts.filter(p=>p.kind==='wheel').length, 'render only the dealership wheel geometry');
  assert(mesh.children.length <= 3, 'compact body, wheel and detail meshes');
  assert.equal(mesh.children.reduce((sum,n)=>sum+n.geometry.index.count/3,0),car.model.triangleCount);
  for (const node of mesh.children) assert.equal(node.material.map, null, 'no runtime texture dependency');
  const geometries = new Set(), materials = new Set();
  mesh.traverse(node => {
    if (node.geometry) geometries.add(node.geometry);
    if (node.material) materials.add(node.material);
  });
  const counts = new Map();
  for (const resource of [...geometries, ...materials]) resource.addEventListener('dispose', () => counts.set(resource, (counts.get(resource) || 0) + 1));
  disposeCar(mesh);
  assert.equal(counts.size, geometries.size + materials.size);
  assert([...counts.values()].every(n => n === 1), 'shared resources disposed exactly once');
}
const seed = {...cars[0], speed:0, weight:0, agility:0, accel:0, paint:{rgb:[128,64,32]}};
const zero = makeCar(seed), half = makeCar({...seed, speed:0.5});
assert.deepEqual(zero.children[0].geometry.attributes.position.array,half.children[0].geometry.attributes.position.array,'handling ratings must not stretch geometry');
assert.equal(zero.children[0].material.color.getHexString(), '804020', 'display RGB sample must round trip through sRGB');
disposeCar(zero); disposeCar(half);
const bodyOnly = structuredClone(cars[0]);
bodyOnly.model.parts = bodyOnly.model.parts.filter(p=>p.kind!=='wheel');
bodyOnly.model.wheelHubs = [];
bodyOnly.model.triangleCount = bodyOnly.model.parts.reduce((sum,p)=>sum+Buffer.from(p.indices,'base64').length/6,0);
validateCars([bodyOnly]);
const custom = makeCar(bodyOnly);
assert.equal(custom.userData.wheels.length,0,'edited dealership models need not preserve source wheel counts');
disposeCar(custom);
for (const data of [[], {}, [cars[0],cars[0]], [{...cars[0],speed:NaN}], [{...cars[0],weight:2}], [{...cars[0],liveries:null}], [{...cars[0],paint:{rgb:[256,0,0]}}], [{...cars[0],bodyStyle:'unknown'}]]) assert.throws(() => validateCars(data));
for (const mutate of [
  c=>delete c.model,
  c=>c.model.source.glb='dealership/models/OTHER.glb',
  c=>c.model.parts[0].vertices='bad',
  c=>c.model.parts[0].vertexCount++,
  c=>c.model.triangleCount++,
  c=>{const b=Buffer.from(c.model.parts[0].vertices,'base64');b.writeFloatLE(NaN,0);c.model.parts[0].vertices=b.toString('base64');},
  c=>{const b=Buffer.from(c.model.parts[0].vertices,'base64');b.writeFloatLE(0,12);b.writeFloatLE(0,16);b.writeFloatLE(0,20);c.model.parts[0].vertices=b.toString('base64');},
  c=>{const b=Buffer.from(c.model.parts[0].indices,'base64');b.writeUInt16LE(65535,0);c.model.parts[0].indices=b.toString('base64');},
]) {
  const corrupted=structuredClone(cars[0]);mutate(corrupted);
  assert.throws(()=>validateCars([corrupted]),/model/);
}
assert.equal((await fetchCars('test', {fetchImpl:async()=>({ok:true,json:async()=>cars})})).length,35);
await assert.rejects(fetchCars('test', {fetchImpl:async()=>({ok:false,status:404,json:async()=>cars})}), /HTTP 404/);
await assert.rejects(fetchCars('test', {fetchImpl:async()=>({ok:true,json:async()=>[]})}), /empty/);
for (const bodyStall of [false,true]) {
  await assert.rejects(fetchCars('test', {timeoutMs:20,fetchImpl:async(_url,{signal})=>{
    const stalled = () => new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('aborted')),{once:true}));
    return bodyStall ? {ok:true,json:stalled} : stalled();
  }}), /timed out/);
}
// Actual transport: response headers arrive, but JSON body never completes.
const server = http.createServer((_request, response) => {
  response.writeHead(200, {'Content-Type':'application/json'});
  response.write('[');
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  await assert.rejects(fetchCars(`http://127.0.0.1:${server.address().port}/`, {timeoutMs:100}), /timed out/);
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
console.log('PASS test_dealership: 35 dealership meshes, editable wheel counts, floor contact, <=3 meshes, unique disposal, rating-independent geometry, sRGB, malformed mesh controls, editable model data, corpus errors and real HTTP body timeout');
