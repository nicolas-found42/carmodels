import assert from 'node:assert/strict';
import fs from 'node:fs';
import zlib from 'node:zlib';
import * as THREE from '../dealership/vendor/three.module.js';
import {readGLB} from '../dealership/model-load.mjs';
import {loadCar, validateCars, disposeCar, dealershipDownload} from '../dealership/dealership.mjs';

// Strict decoder for the converter's own PNGs (8-bit RGBA, filter 0): the renderer receives real pixels.
function decodePng(bytes) {
  const buf=Buffer.from(bytes);
  assert.deepEqual([...buf.subarray(0,8)],[137,80,78,71,13,10,26,10]);
  let offset=8,width,height,idat=[];
  while(offset<buf.length) {
    const size=buf.readUInt32BE(offset),kind=buf.toString('latin1',offset+4,offset+8),body=buf.subarray(offset+8,offset+8+size);
    if(kind==='IHDR'){width=body.readUInt32BE(0);height=body.readUInt32BE(4);assert.deepEqual([...body.subarray(8,13)],[8,6,0,0,0]);}
    if(kind==='IDAT')idat.push(body);
    offset+=12+size;
  }
  const raw=zlib.inflateSync(Buffer.concat(idat)),stride=width*4,pixels=new Uint8Array(stride*height);
  assert.equal(raw.length,height*(stride+1));
  for(let y=0;y<height;y++){assert.equal(raw[y*(stride+1)],0);pixels.set(raw.subarray(y*(stride+1)+1,(y+1)*(stride+1)),y*stride);}
  return {width,height,pixels};
}
const textureImpl=async bytes=>{
  const {width,height,pixels}=decodePng(bytes);
  const texture=new THREE.DataTexture(pixels,width,height,THREE.RGBAFormat);
  texture.colorSpace=THREE.SRGBColorSpace;texture.flipY=false;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.needsUpdate=true;
  return texture;
};
const cars=validateCars(JSON.parse(fs.readFileSync(new URL('../dealership/public/dealership/cars.json',import.meta.url))))
  .filter(c=>c.game==='midnight-club-los-angeles');
assert.equal(cars.length,106);
let triangles=0,texturedMeshes=0,alphaTested=0,transparent=0;
for(const car of cars) {
  assert.equal(car.model.schema,2);
  assert.equal(car.displayMode,'textured-glb');
  const raw=fs.readFileSync(new URL('../dealership/'+car.model.source.glb,import.meta.url));
  const buffer=raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength);
  const group=await loadCar(car,{textureImpl,fetchImpl:async url=>{
    assert.equal(url,'./'+car.model.source.glb);
    return buffer;
  }});
  const {doc}=readGLB(buffer),factors=[];
  function sourceFactors(index) {
    const node=doc.nodes[index];
    for(const p of node.mesh===undefined?[]:doc.meshes[node.mesh].primitives)factors.push(doc.materials[p.material].pbrMetallicRoughness?.baseColorFactor??[1,1,1,1]);
    for(const child of node.children??[])sourceFactors(child);
  }
  for(const index of doc.scenes[doc.scene??0].nodes)sourceFactors(index);
  let count=0,mapped=0,meshIndex=0;
  group.traverse(node=>{
    if(!node.isMesh)return;
    count+=node.geometry.index.count/3;
    assert(node.geometry.attributes.position.count>0);
    assert(node.geometry.attributes.normal.count===node.geometry.attributes.position.count);
    assert(node.geometry.index.array instanceof Uint32Array);
    const material=node.material,factor=factors[meshIndex++];
    material.color.toArray().forEach((value,i)=>assert(Math.abs(value-factor[i])<1e-7,car.code+' source diffuse factor'));
    if(material.map) {
      mapped++;
      const uv=node.geometry.attributes.uv;
      assert(uv && uv.count===node.geometry.attributes.position.count,car.code+' textured mesh lacks one UV per vertex');
      assert(material.map.image.width>0 && material.map.image.height>0);
      assert.equal(material.map.image.data.length,material.map.image.width*material.map.image.height*4);

      if(material.alphaTest>0)alphaTested++;
    }
    if(material.transparent)transparent++;
  });
  assert.equal(meshIndex,factors.length,car.code+' source-instance coverage');
  assert(count>0,car.code+' has no geometry');
  texturedMeshes+=mapped;
  assert.equal(count,car.model.triangleCount,car.code);
  const bounds=new THREE.Box3().setFromObject(group);
  assert(!bounds.isEmpty(),car.code);
  assert(Math.abs(bounds.min.y)<1e-5,car.code+' floor placement');
  assert(Math.abs(bounds.min.x+bounds.max.x)<1e-5,car.code+' centered X');
  assert.equal(dealershipDownload(car).href,'./dealership/models/'+car.code+'.glb');
  triangles+=count;
  disposeCar(group);
}
const selected=cars[0],raw=fs.readFileSync(new URL('../dealership/'+selected.model.source.glb,import.meta.url));
await assert.rejects(loadCar({...selected,model:{...selected.model,source:{...selected.model.source,sha256:'0'.repeat(64)}}},
  {textureImpl,fetchImpl:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)}),/changed/);
// A corrupt embedded image fails the whole load instead of silently dropping the texture.
await assert.rejects(loadCar(selected,{fetchImpl:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength),
  textureImpl:async()=>{throw Error('decode fail');}}),/decode fail/);
assert(texturedMeshes>106,'decoded diffuse textures must reach the renderer');
// Exercise the actual camera handler against a renderable object in each source frame.
const page=fs.readFileSync(new URL('../dealership/dealership.html',import.meta.url),'utf8');
const start=page.indexOf('function setView(view) {'),end=page.indexOf("document.querySelectorAll('[data-view]')",start);
assert(start>0 && end>start);
for(const [game,axis,frontSign] of [['midnight-club-los-angeles','z',-1],['midnight-club-3-remix','z',-1],['redline','z',1],['ford-racing-2','x',1]]) {
  const camera=new THREE.PerspectiveCamera(45,1);
  const controls={target:new THREE.Vector3(),update(){}};
  const model=new THREE.Mesh(new THREE.BoxGeometry(2,1,4),new THREE.MeshBasicMaterial());
  const setView=new Function('THREE','carMesh','current','camera','controls',page.slice(start,end)+'return setView;')
    (THREE,model,{game},camera,controls);
  setView('front');assert.equal(Math.sign(camera.position[axis]-controls.target[axis]),frontSign);
  const sideAxis=axis==='z'?'x':'z';
  assert.equal(camera.position[sideAxis],controls.target[sideAxis]);
  setView('side');assert(camera.position[sideAxis]>controls.target[sideAxis]);
  assert.equal(camera.position[axis],controls.target[axis]);
  model.geometry.dispose();model.material.dispose();
}
console.log(`PASS MCLA preview renderer: ${cars.length} real editable GLBs, ${triangles} triangles, native node transforms, normals, ${texturedMeshes} textured meshes with UVs and decoded pixels, ${alphaTested} alpha-tested and ${transparent} blended meshes, floor placement, downloads, disposal, corrupt-texture and changed-asset rejection`);
