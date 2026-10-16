import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createNativeVehicleVariableMipSampler} from '../dealership/mc3-vehicle-variable-mip.mjs';
import {rasterizeNativeVehicleTriangle} from '../dealership/mc3-vehicle-raster.mjs';
import {roundGSSTQ,rasterizeGSTriangle} from '../dealership/mc3-gs-raster.mjs';
const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-variable-mip.json',import.meta.url)));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function input(row){return {tex1:BigInt(row.tex1),clamp:BigInt(row.clamp),drawTrace:{qMin:Math.min(...row.vertices.map(v=>Math.fround(v.stq[2]))),qMax:Math.max(...row.vertices.map(v=>Math.fround(v.stq[2])))},levels:row.levels.map(level=>({...level,data:new Uint8Array(Buffer.from(level.data_hex,'hex')),readOnly:true}))};}
for(const record of proof.records){
 const plan=createNativeVehicleVariableMipSampler(input(record.case)),rgba=new Uint8Array(256*256*4),depth=new Uint16Array(256*256);
 rasterizeNativeVehicleTriangle(record.case.vertices.map(v=>({...v,stq:roundGSSTQ(v.stq)})),{xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[8,8],constantQ:false,bilinear:false,emitQ:true,gouraud:false,
  onPixel(x,y,pixel){const i=y*256+x;rgba.set(plan.sample(pixel.u,pixel.v,pixel.q),i*4);depth[i]=pixel.z;}});
 for(const [field,stride]of [['frames',4],['depth_frames',2]]){
  const [width,height]=record[field][0].size,raw=new Uint8Array(width*height*stride),view=new DataView(raw.buffer);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(stride===4)raw.set(rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*width+x)*4);
  else view.setUint16((y*width+x)*2,depth[y*256+x],true);
  assert.ok(record[field].every(frame=>frame.sha256===hash(raw)),record.case.name+' complete original '+field);
 }
 console.log('PASS original variable mip',record.case.name,'three RGBA/Z16 frames');
}
const context=input(proof.records[0].case);
for(const change of [{tex1:context.tex1|1n},{tex1:context.tex1&~28n},{tex1:context.tex1&~(7n<<6n)},
 {drawTrace:undefined},{drawTrace:{qMin:1,qMax:1}},{drawTrace:{qMin:0,qMax:1}},
 {drawTrace:{qMin:2,qMax:3}}])assert.throws(()=>createNativeVehicleVariableMipSampler({...context,...change}));
assert.throws(()=>createNativeVehicleVariableMipSampler({...context,levels:context.levels.slice(1)}),/complete native mip images/);
assert.throws(()=>createNativeVehicleVariableMipSampler({...context,levels:[context.levels[0],context.levels[0],context.levels[2]]}),/dimensions differ/);
const sampler=createNativeVehicleVariableMipSampler(context);
for(const q of [0,-1,NaN,Infinity,2**-127])assert.throws(()=>sampler.sample(0,0,q),/Unsupported native mip Q/);
assert.throws(()=>sampler.sample(2**31,0,1),/coordinates/);
console.log('PASS variable-Q trace/register/image/coordinate boundaries');
const triangle=proof.records[0].case.vertices.map(v=>({...v,stq:roundGSSTQ(v.stq)}));
const state={xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[8,8],constantQ:false,bilinear:false};
const oldPixels=[],withQ=[];
rasterizeGSTriangle(triangle,{...state,onPixel:(x,y,p)=>oldPixels.push([x,y,p])});
rasterizeGSTriangle(triangle,{...state,emitQ:true,onPixel:(x,y,p)=>withQ.push([x,y,p])});
assert.deepEqual(withQ.map(([x,y,{q,...p}])=>[x,y,p]),oldPixels);
assert.ok(withQ.every(([, ,p])=>Number.isFinite(p.q)&&p.q>0));
assert.throws(()=>rasterizeGSTriangle(triangle,{...state,emitQ:null,onPixel(){}}),/Explicit GS triangle state/);
const constant=triangle.map(v=>({...v,stq:[...v.stq.slice(0,2),.25]}));
rasterizeGSTriangle(constant,{...state,constantQ:true,emitQ:true,onPixel(x,y,p){assert.equal(p.q,.25);}});
console.log('PASS opt-in Q retains default raster pixel contract and constant source Q');
