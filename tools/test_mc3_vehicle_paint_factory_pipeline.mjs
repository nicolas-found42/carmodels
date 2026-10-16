import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {executePack,collectDMA,capturePrefix,sha} from './mc3_vehicle_paint_factory.mjs';
import {executeNativeVehicleVRAMPipeline} from '../dealership/mc3-vehicle-pipeline.mjs';
import {createNativeVIFState} from '../dealership/mc3-vif-decoder.mjs';

const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-paint-pipeline.json',import.meta.url)));
for(const row of proof.records){
 const exported=spawnSync('python3',['tools/mc3_vehicle_paint_factory.py','--emit-pack',row.name],{encoding:'utf8',maxBuffer:4*1024*1024});
 assert.equal(exported.status,0,exported.stderr);
 const pack=JSON.parse(exported.stdout),ee=executePack(pack);
 assert.equal(sha(ee.ram),pack.expected.projected_ram_sha256,row.name+' original EE sparse RAM');
 const dma=collectDMA(ee.ram,0x1100000,new DataView(ee.ram.buffer).getUint32(0x1009008,true));
 const capture=capturePrefix(dma.bytes);
 assert.equal(sha(dma.bytes),pack.expected.dma.sha256);
 assert.equal(sha(capture.bytes),row.vif_sha256,row.name+' original EE-produced VIF');
 assert.deepEqual(capture.bytes,new Uint8Array(Buffer.from(row.vif_base64,'base64')));
 const vf=new Uint32Array(128);vf[3]=0x3f800000;
 const result=executeNativeVehicleVRAMPipeline({
  vu:{micro:new Uint32Array(4096),memory:new Uint32Array(4096),vf,vi:new Uint16Array(16),acc:new Uint32Array(4)},
  vif:createNativeVIFState(),transfers:[capture.bytes],
  initialGSRegisters:new Map(Array.from({length:128},(_,a)=>[a,a===0x1a?1n:0n])),
  initialVRAM:new Uint8Array(4194304),target:{...proof.initial_state.target}});
 assert.equal(sha(Buffer.concat(result.gifChunks)),row.coupled_execution.gif_sha256);
 assert.equal(sha(result.vu.memory),row.coupled_execution.memory_sha256);
 assert.equal(sha(result.vu.vf),row.coupled_execution.vf_sha256);
 assert.equal(result.frame.rgba.length,262144);
 assert.equal(sha(result.frame.rgba),row.complete_rgba.sha256);
 console.log('PASS sparse original EE factory → exact DMA/VIF → original VU/GIF → native VRAM/CLUT → all262144 RGBA bytes:',row.name);
}
console.log('PASS isolated explicit factory contexts; actor state, variable recipes and showcase activation remain separate');
