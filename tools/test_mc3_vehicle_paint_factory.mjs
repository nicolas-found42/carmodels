import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {executePack,sha,collectDMA,capturePrefix,memoryFootprint,parseEEJob,vifCommands} from './mc3_vehicle_paint_factory.mjs';
const exportPack=control=>{const p=spawnSync('python3',['tools/mc3_vehicle_paint_factory.py','--emit-pack',control],{encoding:'utf8',maxBuffer:4*1024*1024});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout);};
for(const control of ['positive','flat']){
 const pack=exportPack(control),state=executePack(pack);
 assert.equal(sha(state.ram),pack.expected.projected_ram_sha256,control+' entire32MiB after explicit sparse-source projection');
 assert.equal(state.steps,pack.expected.steps);
 const end=new DataView(state.ram.buffer).getUint32(0x1009008,true),dma=collectDMA(state.ram,0x1100000,end),capture=capturePrefix(dma.bytes);
 assert.equal(end,pack.expected.dma.end);assert.equal(sha(dma.bytes),pack.expected.dma.sha256);
 assert.equal(sha(capture.bytes),pack.expected.dma.capture_sha256);assert.equal(capture.cut,pack.expected.dma.capture_bytes);
 assert.deepEqual(dma.rows,pack.expected.dma.rows);assert.deepEqual(capture.frames,pack.expected.dma.frames);
 const changed=structuredClone(pack);changed.code[0][1]=(changed.code[0][1]^1)>>>0;assert.throws(()=>executePack(changed),/closure digest differs/);
 const closed=structuredClone(pack);closed.code=closed.code.filter(([a])=>a!==closed.entry);const words=Buffer.alloc(closed.code.length*8);for(const[i,[a,w]]of closed.code.entries()){words.writeUInt32LE(a,i*8);words.writeUInt32LE(w,i*8+4);}closed.code_sha256=sha(words);assert.throws(()=>executePack(closed),/outside source closure/);
 const data=structuredClone(pack);data.chunks[0].data_hex=(parseInt(data.chunks[0].data_hex.slice(0,2),16)^1).toString(16).padStart(2,'0')+data.chunks[0].data_hex.slice(2);assert.throws(()=>executePack(data),/chunk digest differs/);
 const missing=structuredClone(pack);missing.regions=missing.regions.filter(r=>!r.write);assert.throws(()=>executePack(missing),/write regions/);
 console.log('PASS original native '+control+' sparse factory projected32MiB, ordered CNT/REF DMA and exact pre-restore VIF prefix');
}
const gpr=Array(32).fill(0n);gpr[2]=0x70000003n;const state={gpr};
for(const [op,size,read,write,alignment]of [[30,16,true,false,16],[31,16,false,true,16],[54,16,true,false,16],[62,16,false,true,16],
 [34,4,true,false,4],[38,4,true,false,4],[42,4,true,true,4],[46,4,true,true,4],
 [26,8,true,false,8],[27,8,true,false,8],[44,8,true,true,8],[45,8,true,true,8],
 [32,1,true,false,1],[33,2,true,false,1],[35,4,true,false,1],[55,8,true,false,1],[49,4,true,false,1],[57,4,false,true,1]]){
 const actual=memoryFootprint(0,((op<<26)|(2<<21))>>>0,state);
 assert.deepEqual(actual,{address:Math.floor(0x70000003/alignment)*alignment,size,read,write},'original memory footprint op'+op);
}
assert.equal(memoryFootprint(0,0,state),null);
const ram=new Uint8Array(0x2000000),v=new DataView(ram.buffer);
v.setUint32(0x100,0x10000001,true);v.setUint32(0x108,0x11000000,true);v.setUint32(0x10c,0,true);ram.fill(77,0x110,0x120);
v.setUint32(0x120,0x30000001,true);v.setUint32(0x124,0x200,true);ram.fill(88,0x200,0x210);
const dma=collectDMA(ram,0x100,0x130);assert.equal(dma.bytes.length,48);assert.equal(dma.bytes[8],77);assert.equal(dma.bytes[32],88);
v.setUint32(0x120,0x20000001,true);assert.throws(()=>collectDMA(ram,0x100,0x130),/tag flags/);
v.setUint32(0x120,0x30000001,true);v.setUint32(0x124,0x1fffff0,true);v.setUint32(0x120,0x30000002,true);assert.throws(()=>collectDMA(ram,0x100,0x130),/outside memory/);
assert.throws(()=>collectDMA(ram,0x101,0x130),/extent/);
v.setUint32(0x100,0x3000ffff,true);v.setUint32(0x104,0,true);v.setUint32(0x110,0x3000ffff,true);v.setUint32(0x114,0,true);assert.throws(()=>collectDMA(ram,0x100,0x120),/exceeds bounded stream/);
assert.throws(()=>vifCommands(new Uint8Array(3)),/Truncated/);
assert.throws(()=>vifCommands(Uint8Array.from([0,0,0,0x4a])),/payload/);
function cycleStream(cl,wl){const bytes=new Uint8Array(28),v=new DataView(bytes.buffer);v.setUint32(0,0x01000000|(wl<<8)|cl,true);v.setUint32(4,0x6c010000,true);return bytes;}
assert.throws(()=>vifCommands(cycleStream(1,2)),/Unsupported factory VIF fill cycle/);
assert.throws(()=>vifCommands(cycleStream(1,0)),/Unsupported factory VIF fill cycle/);
for(const [cl,wl]of [[1,1],[2,1],[0,0],[0,1]])assert.equal(vifCommands(cycleStream(cl,wl))[1].size,16,'equal/skip cycles consume one source vector');
assert.throws(()=>capturePrefix(new Uint8Array(4)),/restore boundary/);
assert.throws(()=>parseEEJob(new Uint8Array(28)),/Invalid/);
if(process.argv.includes('--packs-dir')){
 const directory=process.argv[process.argv.indexOf('--packs-dir')+1];
 for(const control of ['positive','flat']){const pack=JSON.parse(fs.readFileSync(directory+'/'+control+'-pack.json'));assert.equal(sha(executePack(pack).ram),pack.expected.projected_ram_sha256);}
 console.log('PASS freshly regenerated original factory source packs');
}
console.log('PASS exact load/store/RMW footprints, aligned VF/GPR access, split DMA sources and malformed boundary controls');
