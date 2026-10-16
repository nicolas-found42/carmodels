import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {rasterizeNativeVehicleSprite} from '../dealership/mc3-vehicle-sprite.mjs';
import {createNativeVehicleSampler} from '../dealership/mc3-vehicle-sampler.mjs';
import {nativeTextureFunction,nativeVehicleFragment} from '../dealership/mc3-vehicle-fragment.mjs';
import {decodeNativeVehicleGIF,renderNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-sprite.json',import.meta.url)));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const record of proof.records) {
 const input=record.case,rgba=new Uint8Array(256*256*4),depth=new Uint16Array(256*256);
 for(let i=0;i<256*256;i++)rgba.set(input.background,i*4);
 const sample=createNativeVehicleSampler({image:{...input.texture,data:new Uint8Array(input.texture.data),readOnly:true},tex1:288n,clamp:0n});
 rasterizeNativeVehicleSprite(input.vertices,{xyOffset:input.xyOffset,scissor:input.scissor,textured:input.textured,
  onPixel(x,y,pixel) {
   const i=y*256+x,source=nativeTextureFunction({vertex128:pixel.vertex128,texture:input.textured?sample(pixel.u,pixel.v):null,tfx:input.textured?0:4,tcc:true});
   const result=nativeVehicleFragment({source,destination:Array.from(rgba.subarray(i*4,i*4+4)),z:pixel.z,destinationZ:depth[i],state:input.state});
   rgba.set(result.rgba,i*4);depth[i]=result.z;
  }});
 const target={fbp:0,fbw:4,zbp:128,width:256,height:256,rgba:new Uint8Array(256*256*4),depth:new Uint16Array(256*256)};
 for(let i=0;i<256*256;i++)target.rgba.set(input.background,i*4);
 const decoded=decodeNativeVehicleGIF(record.draw_chunks.map(s=>new Uint8Array(Buffer.from(s,'base64'))),{initialRegisters:new Map([[0x1a,1n]])});
 const stats=renderNativeVehicleGIF(decoded,{target,resolveTexture(){return {...input.texture,data:new Uint8Array(input.texture.data),readOnly:true};}});
 assert.equal(stats.sprites,1);assert.equal(stats.triangles,0);
 assert.deepEqual(target.rgba,rgba,input.name+' original GIF integration RGBA');
 assert.deepEqual(target.depth,depth,input.name+' original GIF integration Z16');
 for(const [field,stride] of [['frames',4],['depth_frames',2]]) {
  const [w,h]=record[field][0].size,bytes=new Uint8Array(w*h*stride),view=new DataView(bytes.buffer);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
   if(stride===4)bytes.set(rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*w+x)*4);
   else view.setUint16((y*w+x)*2,depth[y*256+x],true);
  }
  assert.equal(record[field].length,3);assert.ok(record[field].every(frame=>frame.sha256===hash(bytes)),input.name+' every original '+field+' byte');
 }
 console.log('PASS original sprite '+input.name+' RGBA/Z16, three frames');
}
assert.equal(proof.records.length,8);
assert.throws(()=>rasterizeNativeVehicleSprite([],{}),/Explicit/);
const input=proof.records[0].case;
assert.throws(()=>rasterizeNativeVehicleSprite([{...input.vertices[0],z:-1},input.vertices[1]],{...input,onPixel(){}}),/vertex/);
console.log('PASS native sprite flat provoking color/depth, independent axes, fractional/scissor sampling and explicit bounds');
