import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createNativeEEState,runNativeEE} from '../dealership/mc3-ee.mjs';
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-paint-components.json',import.meta.url)));
function execute(words,{gpr=[],fpr=[],data=[]}={}){
 const ram=new Uint8Array(0x2000000),spad=new Uint8Array(16384);for(const[a,bytes]of data)ram.set(bytes,a);
 const state=createNativeEEState({ram,spad,entry:0x1000,code:new Map(words.map((w,i)=>[0x1000+i*4,w])),gpr,fpr,regions:[{start:0x1800,size:256,read:true,write:true}]});
 runNativeEE(state);return state;
}
for(const [value,expected]of [[-1n,0n],[0n,1n],[1n,1n]]){
 const s=execute([0x04230002,0x24020001,0x03e00008,0,0x03e00008,0],{gpr:[[1,value]]});assert.equal(s.gpr[2],expected);
}
console.log('PASS native BGEZL taken/untaken delay-slot controls');
for(const[op,expected]of [[0x460100a8,0x3f800000],[0x460100a9,0x3f000000]]){
 const s=execute([op,0x03e00008,0],{fpr:[[0,0x3f800000],[1,0x3f000000]]});assert.equal(s.fpr[2],expected);
}
assert.throws(()=>execute([0x460100a9],{fpr:[[0,1],[1,0x3f800000]]}),/MIN\/MAX exceptional/);
console.log('PASS native finite MIN/MAX and unsupported denormal refusal');
const bytes=Uint8Array.from({length:16},(_,i)=>i*17);
for(let offset=0;offset<4;offset++){
 // Original LWL/LWR pair reconstructs four bytes, including sign extension.
 const lwl=(0x88220000|(offset+3))>>>0,lwr=(0x98220000|offset)>>>0;
 const s=execute([lwl,lwr,0x03e00008,0],{gpr:[[1,0x1800n]],data:[[0x1800,bytes]]});
 const expected=new DataView(bytes.buffer).getInt32(offset,true);assert.equal(BigInt.asIntN(64,s.gpr[2]),BigInt(expected));
 // SWL/SWR preserves adjacent bytes at every unaligned position.
 const swl=(0xa8220000|(offset+3))>>>0,swr=(0xb8220000|offset)>>>0;
 const out=execute([swl,swr,0x03e00008,0],{gpr:[[1,0x1800n],[2,0xdeadbeefn]],data:[[0x1800,bytes]]});
 const expectedBytes=bytes.slice();new DataView(expectedBytes.buffer).setUint32(offset,0xdeadbeef,true);
 assert.deepEqual(out.ram.slice(0x1800,0x1810),expectedBytes);
}
console.log('PASS native unaligned32bit transport at all four byte offsets');
const at=process.argv.indexOf('--source-packs');
if(at<0){console.log('SKIP explicit private original radial/palette execution (use --source-packs DIR).');}
else for(const control of proof.cases){
 const pack=JSON.parse(fs.readFileSync(process.argv[at+1]+'/'+control.name+'.json')),ram=new Uint8Array(0x2000000),spad=new Uint8Array(16384);
 for(const c of pack.chunks){const data=Buffer.from(c.data_hex,'hex');if(c.address>=0x70000000)spad.set(data,c.address-0x70000000);else ram.set(data,c.address);}
 const s=createNativeEEState({...pack,ram,spad,code:new Map(pack.code),gpr:pack.gpr.map(([r,lo])=>[r,BigInt(lo)])});
 for(const[r,,hi]of pack.gpr)s.upper[r]=BigInt(hi);
 runNativeEE(s,{maxSteps:1000000});assert.equal(sha(s.ram),control.ram_sha256,control.name+' complete native RAM');
 assert.equal(sha(s.ram.subarray(control.output_address,control.output_address+control.output_bytes)),control.output_sha256,control.name+' original indices/CLUT');
 console.log('PASS original component full32MiB RAM and native index/CLUT bytes',control.name,s.steps);
}
