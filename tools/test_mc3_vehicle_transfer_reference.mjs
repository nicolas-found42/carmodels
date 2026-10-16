import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createNativeVIFState} from '../dealership/mc3-vif-decoder.mjs';
import {executeNativeVehicleTransfers} from '../dealership/mc3-vehicle-pipeline.mjs';
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const receipt=fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-transfer-reference.json',import.meta.url));
assert.equal(sha(receipt),'50d72f622b107c24475db91b0d2063b7af9ba23f846e0da0dc9b84f8cd1bbe9d');
const proof=JSON.parse(receipt);
function compare(job,expected,rejection,label) {
 assert.equal(sha(job),expected.job_sha256,label+' exact original inputs');
 const view=new DataView(job.buffer,job.byteOffset,job.length),words=(offset,count)=>Uint32Array.from({length:count},(_,i)=>view.getUint32(offset+i*4,true));
 const vf=new Uint32Array(128);vf[3]=0x3f800000;
 let execution;
 try {execution=executeNativeVehicleTransfers({vu:{micro:words(8,4096),memory:words(16392,4096),vf,vi:new Uint16Array(16),acc:new Uint32Array(4)},vif:createNativeVIFState(),transfers:[new Uint8Array(job.subarray(33308,33308+view.getUint32(33304,true)))],initialGSRegisters:new Map([[0,0n],[0x1a,0n],[0x1b,0n]]),maxSteps:100000});}
 catch(error){assert.equal(error.message,rejection,label);console.log('PASS explicit unsupported cross-program context',label);return;}
 assert.equal(rejection,undefined,label+' unexpectedly accepted unsupported context');
 const bytes=Buffer.concat(execution.gifChunks);
 assert.equal(bytes.length,expected.gif_bytes,label);
 assert.equal(sha(bytes),expected.gif_sha256,label+' chronological GIF');
 assert.equal(sha(new Uint8Array(execution.vu.memory.buffer)),expected.memory_sha256,label+' full VU memory');
 assert.equal(sha(new Uint8Array(execution.vu.vf.buffer)),expected.vf_sha256,label+' all VF words');
 console.log('PASS original coupled VIF/coordinator oracle',label,bytes.length);
}
// Minimal self-authored input, independently executed by the original native
// dispatcher. This test does not replace the source-packet integration below.
const synthetic=Buffer.alloc(33308+32);synthetic.write('MC3CV001');
for(const [index,value] of [0x8000033c,0x400002ff,0x8000033c,0x000002ff].entries())synthetic.writeUInt32LE(value,8+index*4);
synthetic[32776+144+64]=1;synthetic[32776+144+65]=1;synthetic.writeUInt32LE(32,33304);
for(const [index,value] of [0x6c010010,1,2,3,4,0x14000000,0x10000000,0].entries())synthetic.writeUInt32LE(value,33308+index*4);
compare(synthetic,proof.synthetic_control,undefined,'self-authored control');
assert.equal(proof.probes.length,13);
assert.equal(new Set(proof.probes.map(row=>row.name)).size,13);
if(process.argv[2])for(const probe of proof.probes){
 const job=fs.readFileSync(path.join(process.argv[2],probe.name,'input.job'));
 compare(job,{...probe.expected,job_sha256:probe.source.job_sha256},probe.browser_rejection,probe.name);
}
