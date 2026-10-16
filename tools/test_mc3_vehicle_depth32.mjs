import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {nativeTextureFunction,nativeVehicleFragment} from '../dealership/mc3-vehicle-fragment.mjs';
import {rasterizeNativeVehicleSprite} from '../dealership/mc3-vehicle-sprite.mjs';
import {createNativeVehicleSampler} from '../dealership/mc3-vehicle-sampler.mjs';
const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-depth32.json',import.meta.url)));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const row of proof.records) {
 assert.equal(row.execution.runtime.binary_sha256,'9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a');
 const rgba=new Uint8Array(256*256*4),depth=new Uint32Array(256*256);
 if(row.name==='fragments') {
  for(const [index,input] of row.inputs.entries()) {
   const source=nativeTextureFunction({vertex128:input.vertex.map(v=>v*128),...input});
   const result=nativeVehicleFragment({source,...input});
   for(let y=0;y<16;y++)for(let x=0;x<16;x++) {
    const i=(Math.floor(index/16)*16+y)*256+(index%16)*16+x;
    rgba.set(result.rgba,i*4);depth[i]=result.z;
   }
  }
 } else {
  const input=row.inputs;
  for(let i=0;i<256*256;i++)rgba.set(input.background,i*4);
  const sample=createNativeVehicleSampler({image:{...input.texture,data:new Uint8Array(input.texture.data),readOnly:true},
   tex1:input.bilinear?288n:0n,clamp:0n});
  rasterizeNativeVehicleSprite(input.vertices,{xyOffset:input.xyOffset,scissor:input.scissor,textured:input.textured,
   depthBits:input.depthBits,bilinear:input.bilinear,onPixel(x,y,pixel) {
    const i=y*256+x,source=nativeTextureFunction({vertex128:pixel.vertex128,texture:sample(pixel.u,pixel.v),tfx:0,tcc:true});
    const result=nativeVehicleFragment({source,destination:Array.from(rgba.subarray(i*4,i*4+4)),z:pixel.z,destinationZ:depth[i],state:input.state});
    rgba.set(result.rgba,i*4);depth[i]=result.z;
   }});
 }
 for(const [field,isDepth] of [['frames',false],['depth_frames',true]]) {
  const [w,h]=row[field][0].size,bytes=new Uint8Array(w*h*4),view=new DataView(bytes.buffer);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
   if(isDepth)view.setUint32((y*w+x)*4,depth[y*256+x],true);
   else bytes.set(rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*w+x)*4);
  }
  assert.equal(row[field].length,3);assert(row[field].every(v=>v.sha256===hash(bytes)),row.name+' every original '+field+' byte');
 }
 console.log('PASS originalGS32 '+row.name+' fullRGBA/Z32 three frames');
}
assert.equal(proof.records.length,5);
const state=proof.records[0].inputs[0].state,source=[1,2,3,4],destination=[5,6,7,8];
assert.equal(nativeVehicleFragment({source,destination,z:0xffffffff,destinationZ:0,state:{...state,ate:false,ztst:1}}).z,0xffffffff);
assert.throws(()=>nativeVehicleFragment({source,destination,z:0x100000000,destinationZ:0,state}),/fragment z/);
assert.throws(()=>nativeVehicleFragment({source,destination,z:0,destinationZ:0x100000000,state}),/destinationZ/);
assert.throws(()=>nativeVehicleFragment({source,destination,z:0,destinationZ:65536,state:{...state,depthFormat:'PSMZ16S'}}),/destinationZ/);
const input=proof.records[1].inputs;
for(const invalid of [{depthBits:24},{bilinear:0}])assert.throws(()=>rasterizeNativeVehicleSprite(input.vertices,{xyOffset:[0,0],scissor:[0,0,256,256],textured:true,onPixel(){},...invalid}),/Explicit/);
console.log('PASS Z32 u32 bounds, default16 compatibility and explicit sprite state guards');
