import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fetchModel,readGLB,assetURL} from '../dealership/model-load.mjs';

const assetBase='https://raw.githubusercontent.com/example/cars/abcdef/dealership/';
assert.equal(assetURL('./dealership/models/CAR.glb'),'./dealership/models/CAR.glb');
for(const path of ['./dealership/models/CAR.glb','public/game/car%20name.glb','public/game/native.zip','dealership/assets/CAR.dat']) {
 assert.equal(assetURL(path,assetBase),assetBase+path.replace(/^\.\//,''));
}
assert.equal(assetURL(new URL('../dealership/public/car.glb',import.meta.url),assetBase),assetBase+'public/car.glb');
for(const path of ['public/models.json','vendor/three.module.js','public/preview.png','../private.glb','https://example.com/car.glb','blob:https://example.com/123']) {
 assert.equal(assetURL(path,assetBase),path);
}
assert.equal(assetURL('public/car.glb?download=1#model',assetBase),assetBase+'public/car.glb?download=1#model');

const bytes=fs.readFileSync(new URL('../dealership/public/ford-racing-2/GRAN_TORINO.glb',import.meta.url));
const buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
assert.equal(readGLB(buffer).doc.extras.car,'GRAN_TORINO');
for(const length of [0,4,12,19,buffer.byteLength-1])assert.throws(()=>readGLB(buffer.slice(0,length)),/GLB/);
const nativeFetch=globalThis.fetch;
try {
 globalThis.fetch=async()=>({ok:false,status:404});
 await assert.rejects(fetchModel('test'),/HTTP 404/);
 globalThis.fetch=async()=>({ok:true,arrayBuffer:async()=>buffer});
 assert.equal(await fetchModel('test'),buffer);
 globalThis.fetch=async(url,{signal})=>{
  const stall=()=>new Promise((resolve,reject)=>{
   const cancel=()=>reject(new DOMException('Aborted','AbortError'));
   if(signal.aborted)cancel();else signal.addEventListener('abort',cancel,{once:true});
  });
  return {ok:true,arrayBuffer:stall};
 };
 await assert.rejects(fetchModel('test',undefined,10),/timed out/);
 const controller=new AbortController();
 const request=fetchModel('test',controller.signal);controller.abort();
 await assert.rejects(request,{name:'AbortError'});
 controller.abort();
 await assert.rejects(fetchModel('test',controller.signal),{name:'AbortError'});
} finally { globalThis.fetch=nativeFetch; }
console.log('PASS test_model_load: local and pinned hosted assets, external/traversal exclusions, corpus GLB, truncations, 404, successful body, stalled body timeout, cancellation');
