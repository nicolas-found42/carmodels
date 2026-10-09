import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../dealership/vendor/three.module.js';
import {parseEditableGLB,loadEditableGLB} from '../dealership/editable-glb.mjs';
import {disposeCar} from '../dealership/dealership.mjs';

function fixture(mutate=()=>{}) {
  const binary=Buffer.alloc(112);
  [0,0,0,2,0,0,0,2,1].forEach((v,i)=>binary.writeFloatLE(v,i*4));
  [0,0,1,0,0,1,0,0,1].forEach((v,i)=>binary.writeFloatLE(v,36+i*4));
  [0,0,1,0,0,1].forEach((v,i)=>binary.writeFloatLE(v,72+i*4));
  [0,1,2].forEach((v,i)=>binary.writeUInt16LE(v,96+i*2));
  const doc={asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{mesh:0}],
    buffers:[{byteLength:112}],bufferViews:[{buffer:0,byteOffset:0,byteLength:36},{buffer:0,byteOffset:36,byteLength:36},{buffer:0,byteOffset:72,byteLength:24},{buffer:0,byteOffset:96,byteLength:6},{buffer:0,byteOffset:104,byteLength:8}],
    accessors:[{bufferView:0,componentType:5126,count:3,type:'VEC3'},{bufferView:1,componentType:5126,count:3,type:'VEC3'},{bufferView:2,componentType:5126,count:3,type:'VEC2'},{bufferView:3,componentType:5123,count:3,type:'SCALAR'}],
    meshes:[{primitives:[{attributes:{POSITION:0,NORMAL:1,TEXCOORD_0:2},indices:3,material:0}]}],
    materials:[{doubleSided:true,alphaMode:'MASK',alphaCutoff:0.25,pbrMetallicRoughness:{baseColorTexture:{index:0},metallicFactor:0}}],
    textures:[{source:0}],images:[{bufferView:4,mimeType:'image/png'}]};
  mutate(doc,binary);
  let text=Buffer.from(JSON.stringify(doc));text=Buffer.concat([text,Buffer.alloc((4-text.length%4)%4,32)]);
  const out=Buffer.alloc(28+text.length+binary.length);out.writeUInt32LE(0x46546c67,0);out.writeUInt32LE(2,4);out.writeUInt32LE(out.length,8);
  out.writeUInt32LE(text.length,12);out.writeUInt32LE(0x4e4f534a,16);text.copy(out,20);
  out.writeUInt32LE(binary.length,20+text.length);out.writeUInt32LE(0x004e4942,24+text.length);binary.copy(out,28+text.length);
  return out.buffer.slice(out.byteOffset,out.byteOffset+out.byteLength);
}
const data=fixture();
assert.equal(parseEditableGLB(data).meshes[0][0].indices.length,3);
const colored=fixture(d=>{d.accessors.push({...d.accessors[1]});d.meshes[0].primitives[0].attributes.COLOR_0=4;});
assert.deepEqual([...parseEditableGLB(colored).meshes[0][0].colors],[0,0,1,0,0,1,0,0,1]);
for(const mutate of [d=>d.nodes[0].children=[0],d=>d.accessors[0].count=100,d=>d.images[0].uri='https://example.com/secret',d=>d.nodes[0].rotation=[0,0,0,0],d=>d.meshes[0].primitives[0].mode=1,(_d,b)=>b.writeUInt16LE(7,96),(_d,b)=>b.writeFloatLE(NaN,0),d=>d.bufferViews[0].byteOffset=-1,d=>d.nodes[0].scale=[0,1,1]])assert.throws(()=>parseEditableGLB(fixture(mutate)));
const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');
const car={model:{source:{glb:'dealership/models/GT_TEST.glb',sha256:hash}}};
const texture=new THREE.Texture();let textureDisposals=0;texture.addEventListener('dispose',()=>textureDisposals++);
const group=await loadEditableGLB(car,{fetchImpl:async()=>data,textureImpl:async()=>texture});
const bounds=new THREE.Box3().setFromObject(group);assert.equal(bounds.min.y,0);assert.equal(bounds.min.x+bounds.max.x,0);
const mesh=group.children[0].children[0];assert.equal(mesh.material.map,texture);assert.equal(mesh.material.alphaTest,0.25);assert.equal(mesh.material.transparent,false);
disposeCar(group);assert.equal(textureDisposals,1);
const colorHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',colored)),v=>v.toString(16).padStart(2,'0')).join('');
const colorGroup=await loadEditableGLB({model:{source:{...car.model.source,sha256:colorHash}}},{fetchImpl:async()=>colored,textureImpl:async()=>new THREE.Texture()});
assert.equal(colorGroup.children[0].children[0].material.vertexColors,true);
assert.equal(colorGroup.children[0].children[0].geometry.attributes.color.count,3);
disposeCar(colorGroup);
await assert.rejects(loadEditableGLB({model:{source:{...car.model.source,sha256:'0'.repeat(64)}}},{fetchImpl:async()=>data,textureImpl:async()=>texture}),/changed/);
await assert.rejects(loadEditableGLB(car,{fetchImpl:async()=>data,textureImpl:async()=>{throw Error('decode fail');}}),/decode fail/);
const controller=new AbortController();controller.abort();
await assert.rejects(loadEditableGLB(car,{signal:controller.signal,fetchImpl:async()=>data,textureImpl:async()=>new THREE.Texture()}),/cancelled/);
// Every real GT editable GLB must pass strict renderer parsing. Texture decoding
// is exercised in the browser; Node validates structural and byte boundaries.
const indexURL=new URL('../dealership/public/gran-turismo/index.json',import.meta.url);
if(fs.existsSync(indexURL)) {
  const index=JSON.parse(fs.readFileSync(indexURL));
  for(const row of index.cars){const raw=fs.readFileSync(new URL('../dealership/public/gran-turismo/'+row.file,import.meta.url));parseEditableGLB(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength));}
  console.log(`PASS test_editable_glb: ${index.cars.length} GT GLBs, embedded textured triangles, MASK alpha, transforms, independent paths, hash mismatch, cancellation and disposal controls`);
} else console.log('PASS test_editable_glb: synthetic textured triangles and failure controls; GT export not present');
