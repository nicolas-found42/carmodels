import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {executeNativeVehiclePipeline} from '../dealership/mc3-vehicle-pipeline.mjs';
import {createNativeVIFState} from '../dealership/mc3-vif-decoder.mjs';
const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-gif.json',import.meta.url)));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function words(...values){const out=new Uint8Array(values.length*4),view=new DataView(out.buffer);values.forEach((v,i)=>view.setUint32(i*4,v,true));return out;}
function direct(raw){const out=new Uint8Array(raw.length+4);out.set(words(0x50000000|raw.length/16));out.set(raw,4);return out;}
function input(record) {
 const micro=new Uint32Array(4096),vf=new Uint32Array(128);vf[3]=0x3f800000;
 for(let i=0;i<4;i++)micro.set([0x8000033c,i%2===0?0x400002ff:0x2ff],i*2);
 return {vu:{micro,memory:new Uint32Array(4096),vf,vi:new Uint16Array(16),acc:new Uint32Array(4)},
  vif:createNativeVIFState(),transfers:[words(0x14000000),...record.case.chunks.map(s=>direct(new Uint8Array(Buffer.from(s,'base64')))),words(0x17000000)],
  initialGSRegisters:new Map(record.case.initial.map(([a,v])=>[a,BigInt(v)])),
  target:{fbp:0,fbw:4,zbp:128,width:256,height:256,rgba:new Uint8Array(256*256*4),depth:new Uint16Array(256*256)},
  resolveTexture(tex0){const image=record.case.images['0x'+(tex0&0x3fffn).toString(16)];return image?{...image,data:new Uint8Array(image.data),readOnly:true}:null;}};
}
for(const record of proof.records) {
 const context=input(record),initial=hash(context.vu.memory),result=executeNativeVehiclePipeline(context);
 assert.deepEqual(result.calls.map(c=>c.pc),[0,2],'MSCNT resumes returned VU continuation');
 assert.equal(result.vif.memory,result.vu.memory,'VIF and VU share private native memory');
 assert.equal(result.vif.microcode,result.vu.micro,'MPG and VU share private original instructions');
 assert.equal(hash(context.vu.memory),initial,'input execution memory is unchanged');
 assert.ok(context.target.rgba.every(v=>v===0),'output is committed to a separate target');
 for(const [field,stride] of [['frames',4],['depth_frames',2]]) {
  const [width,height]=record[field][0].size,raw=new Uint8Array(width*height*stride),view=new DataView(raw.buffer);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++) {
   const index=y*width+x,source=y*256+x;
   if(stride===4)raw.set(result.target.rgba.subarray(source*4,source*4+4),index*4);
   else view.setUint16(index*2,result.target.depth[source],true);
  }
  assert.ok(record[field].every(frame=>frame.sha256===hash(raw)),record.case.name+' composed native '+field);
 }
}
const context=input(proof.records[0]),before=hash(context.target.rgba);
const broken={...context,initialGSRegisters:new Map([...context.initialGSRegisters,[0x45,1n]])};
assert.throws(()=>executeNativeVehiclePipeline(broken),/Unsupported/);
assert.equal(hash(context.target.rgba),before,'a rejected native draw cannot publish partial pixels');
assert.throws(()=>executeNativeVehiclePipeline({...context,transfers:[words(0x17000000)]}),/continuation/);
assert.throws(()=>executeNativeVehiclePipeline({...context,vif:{...context.vif,dbf:undefined}}),/double-buffer/);
assert.throws(()=>executeNativeVehiclePipeline({...context,maxSteps:1}),/budget/);
console.log('PASS composed VIF DIRECT + VU start/continue + GIF/GS for all'+proof.records.length+' original control framebuffers/depths');
console.log('PASS private shared execution buffers, continuation bounds and no partial target publication');
