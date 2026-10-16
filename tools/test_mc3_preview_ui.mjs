import assert from 'node:assert/strict';
import fs from 'node:fs';
import zlib from 'node:zlib';
import * as THREE from '../dealership/vendor/three.module.js';
import {loadCar, validateCars, disposeCar, dealershipDownload} from '../dealership/dealership.mjs';
import {readGLB} from '../dealership/model-load.mjs';
import {createMaterial} from '../dealership/materials.mjs';

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
  .filter(c=>c.game==='midnight-club-3-remix');
assert.equal(cars.length,94);
let triangles=0,texturedMeshes=0,alphaTested=0,transparent=0,tireMeshes=0,sourceTires=0;
function assertVisibleTire(material,label) {
  assert.equal(material.transparent,false,label+' tire is opaque');
  assert.equal(material.alphaTest,0,label+' tire alpha must not erase rubber');
  assert.equal(material.opacity,1,label+' tire opacity');
  assert.equal(material.side,THREE.FrontSide,label+' native back-face culling prevents cap depth conflict');
  assert(material.map,label+' keeps the original diffuse texture');
}
for(const car of cars) {
  assert.equal(car.model.schema,2);
  assert.equal(car.displayMode,'textured-glb');
  const raw=fs.readFileSync(new URL('../dealership/'+car.model.source.glb,import.meta.url));
  const buffer=raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength);
  const doc=readGLB(buffer).doc,loadedTextures=[];
  assert.equal(doc.extras?.gamePaint?.schema,1,car.code+' retains native paint metadata');
  assert.equal(doc.extras?.tireAlphaTranslation?.policy,'native-ps2-tire-reflection-v2');
  assert.equal(doc.extras.tireAlphaTranslation.alpha_test,'always');
  const nativeTires=doc.nodes.filter(n=>n.extras?.nativeWheelComponent==='tire').flatMap(n=>doc.meshes[n.mesh].primitives);
  assert([2,4].includes(nativeTires.length),car.code+' physical tire coverage');
  const tireImageIndices=new Set(nativeTires.map(p=>doc.textures[doc.materials[p.material].pbrMetallicRoughness.baseColorTexture.index].source));
  const group=await loadCar(car,{textureImpl:async bytes=>{const texture=await textureImpl(bytes);loadedTextures.push(texture);return texture;},fetchImpl:async url=>{
    assert.equal(url,'./'+car.model.source.glb);
    return buffer;
  }});
  const tireTextures=new Set([...tireImageIndices].map(i=>loadedTextures[i]));
  const primitiveWheelFlags=[];
  function visitNativeNode(index) {
    const node=doc.nodes[index],wheel=node.extras?.nativeWheelComponent;
    for(const p of node.mesh===undefined?[]:doc.meshes[node.mesh].primitives)primitiveWheelFlags.push({wheel,uv:p.attributes.TEXCOORD_0});
    for(const child of node.children??[])visitNativeNode(child);
  }
  for(const index of doc.scenes[doc.scene??0].nodes)visitNativeNode(index);
  let count=0,mapped=0,carTires=0,meshOrdinal=0;
  group.traverse(node=>{
    if(!node.isMesh)return;
    count+=node.geometry.index.count/3;
    assert(node.geometry.attributes.position.count>0);
    assert(node.geometry.attributes.normal.count===node.geometry.attributes.position.count);
    const material=node.material;
    const primitive=primitiveWheelFlags[meshOrdinal++],wheel=primitive.wheel;
    const uv=node.geometry.attributes.uv;
    assert.equal(!!uv,primitive.uv!==undefined,car.code+' retains authored UV presence independently of diffuse textures');
    if(uv)assert.equal(uv.count,doc.accessors[primitive.uv].count,car.code+' retains every authored UV');
    if(wheel==='rim'||wheel==='tire')assert.equal(material.side,THREE.FrontSide,car.code+' every physical wheel material culls backfaces');
    if(wheel==='tire')assert.equal(node.geometry.getAttribute('mc3NativeNormal').count,node.geometry.getAttribute('position').count);
    if(tireTextures.has(material.map)){assertVisibleTire(material,car.code);carTires++;}
    if(material.map) {
      mapped++;
      assert(uv && uv.count===node.geometry.attributes.position.count,car.code+' textured mesh lacks one UV per vertex');
      assert(material.map.image.width>=16 && material.map.image.data.length>0);
      assert.deepEqual(material.color.toArray(),[1,1,1],car.code+' texture must not be tinted by the neutral factor');
      if(material.alphaTest>0)alphaTested++;
    }
    if(material.transparent)transparent++;
  });
  assert(mapped>=5,car.code+' has too few textured meshes');
  assert.equal(carTires,nativeTires.length,car.code+' every physical tire reaches the renderer');
  tireMeshes+=carTires;
  // Source showcase has its own retained GLB; validate its real material path too.
  const source=fs.readFileSync(new URL('../dealership/public/midnight-club-3-remix/previews/'+car.sourceCode+'.glb',import.meta.url));
  const {doc:sourceDoc,bin:sourceBin}=readGLB(source.buffer.slice(source.byteOffset,source.byteOffset+source.byteLength));
  assert.equal(sourceDoc.extras?.gamePaint?.schema,1,car.code+' source retains native paint metadata');
  assert.deepEqual(sourceDoc.extras?.tireAlphaTranslation,doc.extras.tireAlphaTranslation);
  const sourcePrimitives=sourceDoc.nodes.filter(n=>n.extras?.nativeWheelComponent==='tire').flatMap(n=>sourceDoc.meshes[n.mesh].primitives);
  assert([2,4].includes(sourcePrimitives.length),car.code+' source tire coverage');
  const sourceTextures=[];
  for(const node of sourceDoc.nodes.filter(n=>['rim','tire'].includes(n.extras?.nativeWheelComponent))) {
    for(const p of sourceDoc.meshes[node.mesh].primitives) {
      const wheelMaterial=createMaterial(sourceDoc,[],p.material);
      assert.equal(wheelMaterial.side,THREE.FrontSide,car.code+' source wheel culling');wheelMaterial.dispose();
    }
  }
  for(const p of sourcePrimitives) {
    const index=sourceDoc.textures[sourceDoc.materials[p.material].pbrMetallicRoughness.baseColorTexture.index].source;
    if(!sourceTextures[index]) {
      const v=sourceDoc.bufferViews[sourceDoc.images[index].bufferView];
      sourceTextures[index]=await textureImpl(new Uint8Array(sourceBin,v.byteOffset??0,v.byteLength));
    }
    const material=createMaterial(sourceDoc,sourceTextures,p.material);
    assertVisibleTire(material,car.code+' source');material.dispose();sourceTires++;
  }
  sourceTextures.forEach(t=>t.dispose());
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
assert(alphaTested>94 && transparent>94,'alpha-tested and blended materials must reach the renderer');
// Exercise the actual camera handler against a renderable object in each source frame.
const page=fs.readFileSync(new URL('../dealership/dealership.html',import.meta.url),'utf8');
const start=page.indexOf('function setView(view) {'),end=page.indexOf("document.querySelectorAll('[data-view]')",start);
assert(start>0 && end>start);
for(const [game,axis,frontSign] of [['midnight-club-3-remix','z',-1],['redline','z',1],['ford-racing-2','x',1]]) {
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
console.log(`PASS MC3 preview renderer: ${cars.length} real editable GLBs, ${triangles} triangles, native node transforms, normals, ${texturedMeshes} textured meshes with UVs and decoded pixels, ${alphaTested} alpha-tested and ${transparent} blended meshes, ${tireMeshes} dealership and ${sourceTires} source tires retain texture and opaque visibility, floor placement, downloads, disposal, corrupt-texture and changed-asset rejection`);
