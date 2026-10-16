import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {decodeNativeVehicleGIF,renderNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
const receipt=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-mip.json',import.meta.url)));
const exported=spawnSync('python3',['tools/mc3_vehicle_mip_transport.py'],{encoding:'utf8'});assert.equal(exported.status,0,exported.stderr);
const transports=JSON.parse(exported.stdout),hash=b=>createHash('sha256').update(b).digest('hex');
for(const [i,row]of receipt.records.entries()){
 const transport=transports[i];assert.equal(transport.name,row.case.name);
 const decoded=decodeNativeVehicleGIF(transport.chunks_hex.map(h=>new Uint8Array(Buffer.from(h,'hex'))),{initialRegisters:new Map([[0x1a,1n]])});
 const target={width:256,height:256,fbp:0,fbw:4,zbp:128,rgba:new Uint8Array(262144),depth:new Uint16Array(65536)};
 const levels=row.case.levels.map(level=>({...level,data:new Uint8Array(Buffer.from(level.data_hex,'hex')),readOnly:true}));
 renderNativeVehicleGIF(decoded,{target,resolveTexture:()=>({...levels[0],levels})});
 for(const [field,stride]of [['frames',4],['depth_frames',2]]){
  const [width,height]=row[field][0].size,raw=new Uint8Array(width*height*stride),view=new DataView(raw.buffer);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(stride===4)raw.set(target.rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*width+x)*4);
  else view.setUint16((y*width+x)*2,target.depth[y*256+x],true);
  assert.ok(row[field].every(frame=>frame.sha256===hash(raw)),row.case.name+' original GIF-to-mip '+field);
 }
 assert.throws(()=>renderNativeVehicleGIF(decoded,{target,resolveTexture:()=>levels[0]}),/complete native mip images/);
 const fixed={...decoded,draws:decoded.draws.map(draw=>({...draw,primitive:draw.primitive|256}))};
 assert.throws(()=>renderNativeVehicleGIF(fixed,{target,resolveTexture:()=>({...levels[0],levels})}),/Unsupported native fixed-UV mip profile/);
 console.log('PASS original GIF→mip→RGBA/depth',row.case.name);
}
