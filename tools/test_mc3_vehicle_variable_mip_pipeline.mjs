import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {decodeNativeVehicleGIF,renderNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-variable-mip.json',import.meta.url)));
const output=spawnSync('python3',['tools/mc3_vehicle_variable_mip_transport.py'],{encoding:'utf8'});
assert.equal(output.status,0,output.stderr);
const controls=JSON.parse(output.stdout),sha=b=>createHash('sha256').update(b).digest('hex');
for(const [index,row]of proof.records.entries()){
 assert.equal(controls[index].name,row.case.name);
 const decoded=decodeNativeVehicleGIF(controls[index].chunks_hex.map(h=>new Uint8Array(Buffer.from(h,'hex'))),{initialRegisters:new Map([[0x1a,1n]])});
 const target={width:256,height:256,fbp:0,fbw:4,zbp:128,rgba:new Uint8Array(262144),depth:new Uint16Array(65536)};
 const levels=row.case.levels.map(level=>({...level,data:new Uint8Array(Buffer.from(level.data_hex,'hex')),readOnly:true}));
 renderNativeVehicleGIF(decoded,{target,resolveTexture:()=>({...levels[0],levels})});
 for(const [field,stride]of [['frames',4],['depth_frames',2]]){
  const [w,h]=row[field][0].size,raw=new Uint8Array(w*h*stride),view=new DataView(raw.buffer);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(stride===4)raw.set(target.rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*w+x)*4);
  else view.setUint16((y*w+x)*2,target.depth[y*256+x],true);
  assert(row[field].every(frame=>frame.sha256===sha(raw)),row.case.name+' original GIF variable mip '+field);
 }
 assert.throws(()=>renderNativeVehicleGIF(decoded,{target,resolveTexture:()=>levels[0]}),/complete native mip images/);
 console.log('PASS original GIF→varying-Q mip→RGBA/Z16',row.case.name);
}
