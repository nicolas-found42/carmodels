import assert from 'node:assert/strict';
import fs from 'node:fs';
import{createHash}from'node:crypto';
import{rasterizeGSTriangle}from'../dealership/mc3-gs-raster.mjs';
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-high-z.json',import.meta.url)));
const sha=b=>createHash('sha256').update(b).digest('hex');
for(const row of proof.records){
 const rgba=new Uint8Array(256*256*4),depth=new Uint32Array(256*256);
 rasterizeGSTriangle(row.case.vertices,{xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[1,1],constantQ:true,depthTraceCorrected:row.case.ztst>1,onPixel(x,y,p){const i=y*256+x;rgba.set([17,39,113,128],i*4);depth[i]=p.z;}});
 for(const[field,isDepth]of[['frames',false],['depth_frames',true]]){
  const[w,h]=row[field][0].size,b=new Uint8Array(w*h*4),view=new DataView(b.buffer);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(isDepth)view.setUint32((y*w+x)*4,depth[y*256+x],true);else b.set(rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*w+x)*4);
  assert.equal(row[field].length,3);assert(row[field].every(v=>v.sha256===sha(b)),row.case.name+' '+field);
 }
 console.log('PASS original high-Z32 triangle',row.case.name);
}

assert.equal(proof.records.length,26);
const base=proof.records[0].case.vertices;
for(const patch of [{zEqual:0},{zOverflow:0},{depthTraceCorrected:0}])assert.throws(()=>rasterizeGSTriangle(base,{xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[1,1],constantQ:true,onPixel(){},...patch}),/state|selectors/);
for(const z of [-1,0x100000000,NaN])assert.throws(()=>rasterizeGSTriangle(base.map((v,i)=>i===0?{...v,z}:v),{xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[1,1],constantQ:true,onPixel(){}}),/vertex/);
const varying=proof.records.find(r=>r.case.name==='near-boundary').case.vertices,selector=options=>{const rows=[];rasterizeGSTriangle(varying,{xyOffset:[0,0],scissor:[0,0,256,256],textureSize:[1,1],constantQ:true,...options,onPixel(x,y,p){rows.push([x,y,p.z]);}});return rows;};
assert.deepEqual(selector({depthTraceCorrected:false}),selector({zEqual:true,zOverflow:true}));
assert.deepEqual(selector({depthTraceCorrected:true}),selector({zEqual:false,zOverflow:true}));
assert.notDeepEqual(selector({depthTraceCorrected:false}),selector({depthTraceCorrected:true}),'source corrected raw equality changes selected high-depth scanline path');
console.log('PASS high-Z32 explicit whole-draw trace selectors, corrected/uncorrected equality and invalid vertex bounds');
