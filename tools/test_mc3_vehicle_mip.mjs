import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createNativeVehicleConstantMipSampler} from '../dealership/mc3-vehicle-mip.mjs';
import {rasterizeNativeVehicleTriangle} from '../dealership/mc3-vehicle-raster.mjs';
import {roundGSSTQ} from '../dealership/mc3-gs-raster.mjs';
const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-mip.json',import.meta.url)));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function input(row){return {tex1:BigInt(row.tex1),clamp:BigInt(row.clamp),levels:row.levels.map(level=>({...level,data:new Uint8Array(Buffer.from(level.data_hex,'hex')),readOnly:true}))};}
for(const record of proof.records){
 const plan=createNativeVehicleConstantMipSampler(input(record.case)),rgba=new Uint8Array(256*256*4),depth=new Uint16Array(256*256);
 rasterizeNativeVehicleTriangle(record.case.vertices.map(v=>({...v,stq:roundGSSTQ(v.stq)})),{xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[8,8],constantQ:false,bilinear:false,gouraud:false,
  onPixel(x,y,pixel){const i=y*256+x;rgba.set(plan.sample(pixel.u,pixel.v,x),i*4);depth[i]=pixel.z;}});
 for(const [field,stride]of [['frames',4],['depth_frames',2]]){
  const [width,height]=record[field][0].size,raw=new Uint8Array(width*height*stride),view=new DataView(raw.buffer);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(stride===4)raw.set(rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*width+x)*4);
  else view.setUint16((y*width+x)*2,depth[y*256+x],true);
  assert.ok(record[field].every(frame=>frame.sha256===hash(raw)),record.case.name+' complete original '+field);
 }
 console.log('PASS original constant mip',record.case.name,'three RGBA/Z16 frames');
}
const context=input(proof.records[0].case);
for(const tex1 of [context.tex1&~1n,context.tex1&~28n,context.tex1&~(7n<<6n),context.tex1&0xffffffffn])
 assert.throws(()=>createNativeVehicleConstantMipSampler({...context,tex1}),/Unsupported native constant mip profile/);
assert.throws(()=>createNativeVehicleConstantMipSampler({...context,levels:context.levels.slice(1)}),/complete native mip images/);
assert.throws(()=>createNativeVehicleConstantMipSampler({...context,levels:[context.levels[0],context.levels[0],context.levels[2]]}),/dimensions differ/);
const sampler=createNativeVehicleConstantMipSampler(context);
assert.throws(()=>sampler.sample(0,0),/coordinates and absolute pixel x/);
assert.throws(()=>sampler.sample(2**31,0,0),/coordinates and absolute pixel x/);
console.log('PASS explicit constant-only LOD, complete image and unshifted coordinate boundaries');
