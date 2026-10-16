import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {decodeNativeVehicleGIF,renderNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
import {createNativeGSVRAM,writeNativeGSRegister,uploadNativeGSImage,readNativeGSTexture} from '../dealership/mc3-gs-vram.mjs';
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-target.json',import.meta.url)));
const sha=b=>createHash('sha256').update(b).digest('hex'),bytes=s=>new Uint8Array(Buffer.from(s,'base64'));
for(const record of proof.cases){
 const initial=proof.initial_gif_base64.map(bytes),chunks=record.gif_chunks_base64.map(bytes);
 assert.deepEqual(initial.map(sha),record.initial_gif_sha256);
 assert.equal(sha(Buffer.concat(chunks)),record.coupled.gif_sha256);
 const decoded=decodeNativeVehicleGIF([...initial,...chunks],{
  initialRegisters:new Map(Array.from({length:128},(_,i)=>[i,0n])),allowImages:true});
 const vram=createNativeGSVRAM(new Uint8Array(4194304));
 const target={fbp:480,fbw:4,zbp:464,width:256,height:256,
  rgba:new Uint8Array(262144),depth:new Uint16Array(65536)};
 let pixels=0;
 for(const operation of decoded.operations){
  if(operation.kind==='register')writeNativeGSRegister(vram,operation.address,operation.value);
  else if(operation.kind==='image')uploadNativeGSImage(vram,operation.data);
  else if(operation.kind==='draw')pixels+=renderNativeVehicleGIF({...decoded,draws:[operation.draw]},
   {target,resolveTexture:tex0=>readNativeGSTexture(vram,tex0)}).pixels;
  else assert.fail('unexpected native operation');
 }
 if(record.name==='positive'){
  assert.equal(pixels,203);
  assert.ok(proof.positive_complete_rgba.every(frame=>frame.bytes===262144&&sha(target.rgba)===frame.sha256));
  const depth=new Uint8Array(177*135*2),view=new DataView(depth.buffer);
  for(let y=0;y<135;y++)for(let x=0;x<177;x++)view.setUint16((y*177+x)*2,target.depth[y*256+x],true);
  assert.ok(proof.positive_gs.depth_frames.every(frame=>sha(depth)===frame.sha256));
 }else{
  assert.equal(decoded.draws.length,0,'original clipped/pass-disabled GIF has no raster draw');
  assert.equal(pixels,0);assert.ok(target.rgba.every(v=>v===0));
 }
 console.log('PASS original SDK/default/RT/authored source GIF, uploaded native texture and GS:',record.name);
}
console.log('PASS complete256-square nativePCRTC RGBA and cropped nativePSMZ16S depth, all3nativeframes');
