import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createNativeVIFState,unpackNativeVIF,runNativeVIF} from '../dealership/mc3-vif-decoder.mjs';
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const receipt=fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-vif-reference.json',import.meta.url));
assert.equal(sha(receipt),'db9411a48c997c7075a45963e56b0cee13e3842ae202c831e459b60af239def9');
const proof=JSON.parse(receipt);
const rawCases=[];
for(const c of proof.cases) {
 const broad=c.name.startsWith('broad-'),state=createNativeVIFState();
 Object.assign(state,{cl:c.cl??1,wl:c.wl??1,mode:c.mode??0,mask:c.mask??0});
 state.row.set(c.row??[0,0,0,0]);state.col.set(c.col??[0,0,0,0]);
 const memory=broad?Uint8Array.from({length:16384},(_,i)=>(i*23+7)&255):new Uint8Array(16384);
 new Uint8Array(state.memory.buffer).set(memory);
 const bytes=broad?Uint8Array.from({length:256},(_,i)=>(i*17+Math.floor(i/3)*19)&255):Uint8Array.from({length:112},(_,i)=>i+1);
 const cmd=0x60+c.kind+(c.masked?16:0),vif=new Uint8Array(144),regs=new Uint8Array(384),v=new DataView(vif.buffer),r=new DataView(regs.buffer);
 for(let i=0;i<4;i++){v.setUint32(i*4,state.row[i],true);v.setUint32(16+i*4,state.col[i],true);}
 v.setUint32(32,(c.start??0)*16,true);v.setUint32(48,cmd,true);vif[60]=c.unsigned?1:0;vif[61]=c.alignment;
 regs[64]=state.cl;regs[65]=state.wl;r.setUint32(80,state.mode,true);r.setUint32(96,8,true);r.setUint32(112,state.mask,true);
 const size=Buffer.alloc(4);size.writeUInt32LE(bytes.length);const input=Buffer.concat([vif,regs,memory,size,bytes]);
 assert.equal(sha(input),c.case_sha256,c.name+' exact native inputs');rawCases.push(input);
 unpackNativeVIF(bytes,state,(cmd<<24)|(8<<16)|(c.unsigned?0x4000:0)|(c.start??0),4*(c.alignment-1));
 assert.equal(sha(new Uint8Array(state.memory.buffer)),c.memory_sha256,c.name+' complete memory');
 assert.deepEqual([...state.row],c.result_row,c.name+' final row');
}
const count=Buffer.alloc(4);count.writeUInt32LE(rawCases.length);
assert.equal(sha(Buffer.concat([Buffer.from('MC3VIF02'),count,...rawCases])),proof.job_sha256);
const words=(...values)=>{const b=new Uint8Array(values.length*4),v=new DataView(b.buffer);values.forEach((x,i)=>v.setUint32(i*4,x,true));return b;};
const s=createNativeVIFState(),calls=[];
runNativeVIF(words(0x03000040,0x02000100,0x04000098,0x14000006,0x14000008,0x04000030,0x17000000),s,{onMicro:({pc,top,itop})=>calls.push([pc,top,itop])});
assert.deepEqual(calls,[[6,64,152],[8,320,152],[null,64,48]]);
assert.equal(s.tops,320);
const masked=createNativeVIFState();runNativeVIF(words(0x20000000,0xffffffff,0x7c010000,1,2,3,4),masked);assert.deepEqual([...masked.memory.slice(0,4)],[0,0,0,0]);
assert.throws(()=>runNativeVIF(words(0x30000000,1)),/Truncated/);
assert.throws(()=>runNativeVIF(words(0x08000000)),/Unsupported/);
assert.throws(()=>unpackNativeVIF(new Uint8Array(4),createNativeVIFState(),0x6c010000),/Truncated/);
console.log('PASS'+proof.cases.length+' original VIF dynamic/fallback memory and row goldens, exact job inputs, TOP/ITOP/DBF callbacks and rejection controls');

const direct=createNativeVIFState();runNativeVIF(words(0x50000001,0,0,0,0,0x04000077),direct);assert.equal(direct.itops,0x77);
