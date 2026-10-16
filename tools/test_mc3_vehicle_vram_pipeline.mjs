import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {executeNativeVehicleVRAMPipeline} from '../dealership/mc3-vehicle-pipeline.mjs';
import {decodeNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
import {renderNativeVehicleVRAMGIF} from '../dealership/mc3-vehicle-vram.mjs';
import {createNativeVIFState} from '../dealership/mc3-vif-decoder.mjs';

const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const receipt=readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-paint-pipeline.json',import.meta.url));
assert.equal(hash(receipt),'105677890ab2aeba84bcb3962294fa0580adca03e00917997e6251f6c6d8201b');
const proof=JSON.parse(receipt);
function input(record){
 const vf=new Uint32Array(128);vf[3]=0x3f800000;
 return {vu:{micro:new Uint32Array(4096),memory:new Uint32Array(4096),vf,vi:new Uint16Array(16),acc:new Uint32Array(4)},
  vif:createNativeVIFState(),transfers:[new Uint8Array(Buffer.from(record.vif_base64,'base64'))],
  initialGSRegisters:new Map(Array.from({length:128},(_,address)=>[address,address===0x1a?1n:0n])),
  initialVRAM:new Uint8Array(4*1024*1024),target:{...proof.initial_state.target}};
}
let first;
for(const record of proof.records){
 const context=input(record),before=hash(context.initialVRAM);
 assert.equal(hash(context.transfers[0]),record.vif_sha256);
 const result=executeNativeVehicleVRAMPipeline(context),native=record.coupled_execution;
 assert.equal(hash(Buffer.concat(result.gifChunks)),native.gif_sha256,record.name+' chronological literal GIF');
 assert.equal(hash(result.vu.memory),native.memory_sha256,record.name+' all native VU memory');
 assert.equal(hash(result.vu.vf),native.vf_sha256,record.name+' all native VF words');
 assert.equal(hash(result.frame.rgba),record.complete_rgba.sha256,record.name+' entire native256-square RGBA');
 assert.equal(result.frame.rgba.length,262144);
 assert.equal(result.depthAccess,false);
 assert.equal(hash(context.initialVRAM),before,'caller VRAM is unchanged');
 assert.ok(context.vu.memory.every(v=>v===0),'caller VU memory is unchanged');
 assert.ok(result.vram.bytes!==context.initialVRAM);
 assert.equal(result.decoded.draws[0].registers.get(0x4c)>>32n,0xffffffn,'replay prefill masks all RGB');
 for(const draw of result.decoded.draws.slice(1))assert.equal(draw.registers.get(0x4c)>>32n,0xff000000n,'later draws preserve alpha');
 for(let i=3;i<result.frame.rgba.length;i+=4)assert.equal(result.frame.rgba[i],128,'prefill cannot change completed frame alpha');
 assert.ok(result.decoded.operations.some(op=>op.kind==='image'),'literal IMAGE uploads are consumed');
 assert.ok(result.stats.sprites>=3);
 if(!first)first={context,result};
 console.log('PASS original EE-produced '+record.name+' raw VIF → VU → IMAGE/CLUT/GIF → complete native RGBA');
}

const {context,result}=first,before=hash(context.initialVRAM);
const badDraw={...result.decoded.draws[0],registers:new Map(result.decoded.draws[0].registers)};
badDraw.registers.set(0x4e,1n<<32n|10n<<24n);
assert.throws(()=>renderNativeVehicleVRAMGIF({...result.decoded,operations:[...result.decoded.operations,{kind:'draw',draw:badDraw}]},context),/without depth reads/);
assert.equal(hash(context.initialVRAM),before,'late rejected draw cannot publish earlier private VRAM writes');
assert.throws(()=>renderNativeVehicleVRAMGIF(result.decoded,{...context,initialVRAM:undefined}),/VRAM/);
assert.throws(()=>renderNativeVehicleVRAMGIF(result.decoded,{...context,target:{...context.target,fbp:0}}),/binding differs/);
assert.throws(()=>renderNativeVehicleVRAMGIF({...result.decoded,operations:[{kind:'unknown'}]},context),/Unsupported native VRAM operation/);
assert.throws(()=>decodeNativeVehicleGIF(result.gifChunks,{initialRegisters:context.initialGSRegisters}),/IMAGE/);
assert.throws(()=>decodeNativeVehicleGIF(result.gifChunks,{initialRegisters:context.initialGSRegisters,allowImages:1}),/boolean/);

const gifProof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-gif.json',import.meta.url)));
const control=gifProof.records[4].case,bytes=control.chunks.map(s=>Buffer.from(s,'base64'));
const image=Buffer.alloc(32);image.writeBigUInt64LE(1n|(1n<<15n)|(2n<<58n));
const initialRegisters=new Map(control.initial.map(([a,v])=>[a,BigInt(v)]));
assert.throws(()=>decodeNativeVehicleGIF([bytes[0],bytes[1],image,bytes[1]],{initialRegisters,allowImages:true}),/otherwise unchanged draw group/);
assert.throws(()=>decodeNativeVehicleGIF([image.subarray(0,16)],{initialRegisters,allowImages:true}),/Truncated native GIF IMAGE/);
const setup=decodeNativeVehicleGIF([bytes[0]],{initialRegisters}),palette=Buffer.alloc(32);
palette.writeBigUInt64LE(1n|(1n<<15n)|(1n<<60n));palette.writeBigUInt64LE(14n,8);
palette.writeBigUInt64LE(setup.registers.get(6)|1n<<61n,16);palette.writeBigUInt64LE(6n,24);
assert.throws(()=>decodeNativeVehicleGIF([bytes[0],palette,bytes[1],palette,bytes[1]],{initialRegisters,allowImages:true}),/otherwise unchanged draw group/);
for(const address of [0x16,0x17,0x54]){
 const unsupported=palette.slice();unsupported.writeBigUInt64LE(BigInt(address),24);
 assert.throws(()=>decodeNativeVehicleGIF([unsupported],{initialRegisters,allowImages:true}),/Unsupported native VRAM TEX2\/HWREG side effect/);
}
console.log('PASS explicit upload opt-in, IMAGE bounds, unresolved overlap refusal, no-depth restriction and private failure atomicity');
