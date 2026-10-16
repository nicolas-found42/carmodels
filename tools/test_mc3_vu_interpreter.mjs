import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createNativeVUState,decodeNativeVUPair,runNativeVU} from '../dealership/mc3-vu-interpreter.mjs';

const hash=data=>createHash('sha256').update(data).digest('hex');
function initial(micro,memory=new Uint32Array(4096)) {
 const vf=new Uint32Array(128);vf[3]=0x3f800000;
 return createNativeVUState({micro,memory,vf,vi:new Uint16Array(16),acc:new Uint32Array(4)});
}
const fixtureBytes=readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vu-interpreter-controls.json',import.meta.url));
assert.equal(hash(fixtureBytes),'87b43bc6c378ff3b1f00c088791f463a16a68a13e3ad504699473ae46bd6ba16','independent control receipt identity');
const fixture=JSON.parse(fixtureBytes);
for(const probe of fixture.cases) {
 const micro=new Uint32Array(4096);
 for(let i=0;i<2048;i++)micro.set(probe.micro_fill??[0x8000033c,0x2ff],i*2);
 probe.pairs.forEach((pair,i)=>micro.set(pair,i*2));
 const state=initial(micro);
 for(const [row,words] of Object.entries(probe.memory))state.memory.set(words,Number(row)*4);
 for(const [reg,words] of Object.entries(probe.vf))state.vf.set(words,Number(reg)*4);
 const job=Buffer.alloc(32804+Object.keys(probe.vf).length*20);job.write('MC3VU001');
 Buffer.from(micro.buffer).copy(job,8);Buffer.from(state.memory.buffer).copy(job,16392);
 [1,0,0,0,probe.instruction_budget??10000,0,Object.keys(probe.vf).length].forEach((n,i)=>job.writeUInt32LE(n,32776+i*4));
 let offset=32804;
 for(const [reg,words] of Object.entries(probe.vf)){job.writeUInt32LE(Number(reg),offset);offset+=4;for(const n of words){job.writeUInt32LE(n,offset);offset+=4;}}
 assert.equal(hash(job),probe.job_sha256,probe.name+' exact independently executed input job');
 runNativeVU(state,0);
 assert.deepEqual([...state.vf],probe.expected.vf_words,probe.name+' all raw VF words');
 assert.equal(hash(new Uint8Array(state.memory.buffer)),probe.expected.memory_sha256,probe.name+' entire data memory');
 assert.equal(state.cycle,probe.expected.cycles,probe.name+' interpreter cycles');
 assert.equal(probe.execution.binary_sha256,'9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a');
 assert.equal(probe.execution.adapter_sha256,'e5d3af8ab74fcf55d5c6962deb62ac6b66a2d14e6b7fff571e99942c0a3aebf8');
 assert.equal(probe.execution.job_sha256,probe.job_sha256);
 console.log('PASS independent VU interpreter control: '+probe.name);
}
assert.throws(()=>decodeNativeVUPair(0x8000033c,0x30),/Unsupported/);
assert.throws(()=>createNativeVUState({}),/explicit/);
const endless=initial(new Uint32Array(4096));
endless.micro.set([0x400007ff,0x2ff,0x8000033c,0x2ff]);
assert.throws(()=>runNativeVU(endless,0,{maxSteps:12}),/budget/);
assert.throws(()=>runNativeVU(endless,2048),/bounds/);

// Optional full original-program comparison. The reference job and actual
// output directories must already exist; no expected output enters the VU.
// Usage: node tools/test_mc3_vu_interpreter.mjs <jobs-dir> [output-suffix]
if(process.argv[2]) {
 const directory=process.argv[2],suffix=process.argv[3]??'';
 for(const name of readdirSync(directory).filter(name=>name.endsWith('.job'))) {
  const bytes=readFileSync(directory+'/'+name);
  if(bytes.subarray(0,8).toString()!=='MC3VU001')continue;
  const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  const words=(offset,count)=>Uint32Array.from({length:count},(_,i)=>view.getUint32(offset+i*4,true));
  const state=initial(words(8,4096),words(16392,4096)),gif=[];let offset=32776;
  const count=view.getUint32(offset,true);offset+=4;
  for(let call=0;call<count;call++) {
   const [pc,top,itop,maxSteps,patches,vfpatches]=words(offset,6);offset+=24;state.top=top;state.itop=itop;
   for(let i=0;i<patches;i++) {
    const [at,size]=words(offset,2);offset+=8;
    new Uint8Array(state.memory.buffer).set(bytes.subarray(offset,offset+size),at);offset+=size;
   }
   for(let i=0;i<vfpatches;i++){const reg=words(offset,1)[0];offset+=4;state.vf.set(words(offset,4),reg*4);offset+=16;}
   runNativeVU(state,pc,{maxSteps,onGIF:bytes=>gif.push(Buffer.from(bytes))});
  }
  assert.equal(offset,bytes.length,name+' job framing');
  const target=directory+'/'+name.slice(0,-4)+suffix;
  const registers=readFileSync(target+'/final-vuregs.bin'),expected=new DataView(registers.buffer,registers.byteOffset,registers.byteLength);
  assert.deepEqual([...state.vf],Array.from({length:128},(_,i)=>expected.getUint32(i*4,true)),name+' all VF words');
  assert.deepEqual(Buffer.from(state.memory.buffer),readFileSync(target+'/final-vumem.bin'),name+' entire memory');
  const chunks=readFileSync(target+'/gif-chunks.bin'),parts=[];
  for(let at=0;at<chunks.length;) {const length=chunks.readUInt32LE(at);at+=4;parts.push(chunks.subarray(at,at+length));at+=length;}
  assert.deepEqual(Buffer.concat(gif),Buffer.concat(parts),name+' entire GIF stream');
  const calls=JSON.parse(readFileSync(target+'/calls.json'));
  assert.equal(state.cycle,calls.at(-1).end_cycle,name+' total cycles');
  console.log('PASS original whole VU job: '+name+'; GIF '+Buffer.concat(gif).length+' bytes, 16384 memory bytes, 128 VF words and '+state.cycle+' cycles');
 }
}
