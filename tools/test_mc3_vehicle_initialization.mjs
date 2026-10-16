import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {decodeNativeVehicleInitialization} from '../dealership/mc3-vehicle-initialization.mjs';
import {executeNativeVehicleTransfers} from '../dealership/mc3-vehicle-pipeline.mjs';
import {createNativeVIFState} from '../dealership/mc3-vif-decoder.mjs';
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-initialization.json',import.meta.url)));
const stream=await decodeNativeVehicleInitialization(proof.pack),vf=new Uint32Array(128);vf[3]=0x3f800000;
const result=executeNativeVehicleTransfers({vu:{micro:new Uint32Array(4096),memory:new Uint32Array(4096),vf,vi:new Uint16Array(16),acc:new Uint32Array(4)},
 vif:createNativeVIFState(),transfers:[stream],initialGSRegisters:new Map([[0x1a,1n]])});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
assert.equal(sha(result.vu.memory),proof.coupled.memory_sha256);
assert.equal(sha(result.vu.vf),proof.coupled.vf_sha256);
assert.equal(result.gifChunks.length,0);assert.equal(result.calls.length,0);
assert.ok(result.vu.memory.subarray(35*4,40*4).some(v=>v!==0),'native GIF templates initialized');
assert.ok(result.vu.micro.some(v=>v!==0),'original normal microprogram loaded');
for(const change of [{schema:0},{source_executable_sha256:'0'.repeat(64)},{vif_bytes:0},{vif_base64:'AAAA'},{vif_sha256:'0'.repeat(64)}])
 await assert.rejects(()=>decodeNativeVehicleInitialization({...proof.pack,...change}));
const changed=stream.slice();changed[8]^=1;
await assert.rejects(()=>decodeNativeVehicleInitialization({...proof.pack,vif_base64:Buffer.from(changed).toString('base64'),vif_sha256:sha(changed)}));
console.log('PASS actual original initialization DMA→VIF, complete native VU memory/VF, original microprogram and corruption controls');
