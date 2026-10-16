import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {decodeNativeVehicleGIF,renderNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-depth-trace.json',import.meta.url)));
const output=spawnSync('python3',['tools/mc3_vehicle_depth_trace.py','--emit-controls'],{encoding:'utf8'});
assert.equal(output.status,0,output.stderr);
const controls=JSON.parse(output.stdout),hash=b=>createHash('sha256').update(b).digest('hex');
let mismatches=[];
for(const [index,row]of proof.records.entries()){
 const previousMismatchCount=mismatches.length;
 assert.equal(controls[index].name,row.case.name);
 const decoded=decodeNativeVehicleGIF(controls[index].chunks_hex.map(h=>new Uint8Array(Buffer.from(h,'hex'))),{initialRegisters:new Map([[0x1a,1n],[0x22,0n]])});
 const target={width:256,height:256,fbp:0,fbw:4,zbp:128,rgba:new Uint8Array(262144),depth:new Uint32Array(65536)};
 renderNativeVehicleGIF(decoded,{target,resolveTexture(){const image=row.case.image;return image?{...image,data:new Uint8Array(image.data),readOnly:true}:undefined;}});
 for(const [field,depth]of [['frames',false],['depth_frames',true]]){
  const [w,h]=row[field][0].size,bytes=new Uint8Array(w*h*4),view=new DataView(bytes.buffer);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(depth)view.setUint32((y*w+x)*4,target.depth[y*256+x],true);
  else bytes.set(target.rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*w+x)*4);
  if(!row[field].every(frame=>frame.sha256===hash(bytes)))mismatches.push(row.case.name+' GIF '+field);
 }
 console.log(previousMismatchCount===mismatches.length?'PASS':'MISMATCH','original GIF→whole-draw trace→RGBA/Z32',row.case.name);
}
assert.deepEqual(mismatches,[],'Original whole-draw depth trace mismatches');
