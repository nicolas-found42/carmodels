import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fetchModel,readGLB} from '../dealership/model-load.mjs';

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
console.log('PASS test_model_load: corpus GLB, truncations, 404, successful body, stalled body timeout, cancellation');
