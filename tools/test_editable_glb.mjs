import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../dealership/vendor/three.module.js';
import {parseEditableGLB,loadEditableGLB} from '../dealership/editable-glb.mjs';
import {disposeCar} from '../dealership/dealership.mjs';

function fixture(mutate=()=>{}) {
  const binary=Buffer.alloc(244);
  [0,0,0,2,0,0,0,2,1].forEach((v,i)=>binary.writeFloatLE(v,i*4));
  [0,0,1,0,0,1,0,0,1].forEach((v,i)=>binary.writeFloatLE(v,36+i*4));
  [0,0,1,0,0,1].forEach((v,i)=>binary.writeFloatLE(v,72+i*4));
  [0,1,2].forEach((v,i)=>binary.writeUInt16LE(v,96+i*2));
  const doc={asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{mesh:0}],
    buffers:[{byteLength:binary.length}],bufferViews:[{buffer:0,byteOffset:0,byteLength:36},{buffer:0,byteOffset:36,byteLength:36},{buffer:0,byteOffset:72,byteLength:24},{buffer:0,byteOffset:96,byteLength:6},{buffer:0,byteOffset:104,byteLength:8}],
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
const nativeNormals=fixture(d=>{d.meshes[0].primitives[0].attributes._MC3_NATIVE_NORMAL=1;});
function addNativeInputs(d,b) {
  d.extras={nativeVertexInputs:'mc3-vif-vertex-inputs-v1'};
  d.extras.nativeSkeleton={source_sha256:'b'.repeat(64),bones:[{parent:null,child:1},{parent:0,child:null}]};
  d.nodes[0].name='native-wheel';d.nodes[0].extras={nativeBone:1};
  const p=d.meshes[0].primitives[0];p.attributes._MC3_NATIVE_NORMAL=1;
  for(const [name,offset,rows] of [['_MC3_NATIVE_COLOR',112,[255,128,0,-1]],['_MC3_NATIVE_UV',160,[-4096,8192,23,-24]]]) {
    for(let i=0;i<12;i++)b.writeFloatLE(rows[i%4],offset+i*4);
    const view=d.bufferViews.push({buffer:0,byteOffset:offset,byteLength:48})-1;
    p.attributes[name]=d.accessors.push({bufferView:view,componentType:5126,count:3,type:'VEC4'})-1;
  }
  p.extras={native_batches:[{vertex_start:0,vertex_count:3,packet_offset:128,position_scale:1/1024,header_words:[0,3]}]};
}
const nativeInputs=fixture(addNativeInputs), nativeParsed=parseEditableGLB(nativeInputs).meshes[0][0];
function addNativePositions(d,b) {
  addNativeInputs(d,b);
  d.extras.nativePositionInputs='mc3-vif-integer-position-v1';
  const p=d.meshes[0].primitives[0];
  for(let i=0;i<9;i++)b.writeFloatLE([127,-3,4,2048,17,-15,-4096,31,7][i],208+i*4);
  const view=d.bufferViews.push({buffer:0,byteOffset:208,byteLength:36})-1;
  p.attributes._MC3_NATIVE_POSITION=d.accessors.push({bufferView:view,componentType:5126,count:3,type:'VEC3'})-1;
  Object.assign(p.extras.native_batches[0],{position_scale_word:0x39800000,position_scale:1/4096,header_words:[0x39800000,3]});
}
const nativePositions=fixture(addNativePositions);
assert.deepEqual([...parseEditableGLB(nativePositions).meshes[0][0].mc3NativePositions],[127,-3,4,2048,17,-15,-4096,31,7]);
for(const [mutate,reason] of [
  [d=>delete d.meshes[0].primitives[0].attributes._MC3_NATIVE_POSITION,/position inputs are incomplete/],
  [(_d,b)=>b.writeFloatLE(.5,208),/integer attribute mismatch/],
  [(_d,b)=>b.writeFloatLE(0x80000000,208),/integer attribute mismatch/],
  [d=>d.meshes[0].primitives[0].extras.native_batches[0].position_scale_word=0,/position scale word/],
  [d=>d.meshes[0].primitives[0].extras.native_batches[0].position_scale=1/8192,/position scale word/]
])assert.throws(()=>parseEditableGLB(fixture((d,b)=>{addNativePositions(d,b);mutate(d,b);})),reason);
assert.deepEqual([...nativeParsed.mc3NativeColors],[255,128,0,-1,255,128,0,-1,255,128,0,-1]);
assert.deepEqual([...nativeParsed.mc3NativeUvs],[-4096,8192,23,-24,-4096,8192,23,-24,-4096,8192,23,-24]);
for(const [mutate,reason] of [
  [d=>delete d.meshes[0].primitives[0].attributes._MC3_NATIVE_COLOR,/incomplete/],
  [d=>d.accessors[4].count=2,/integer attribute mismatch/],
  [(_d,b)=>b.writeFloatLE(.5,112),/integer attribute mismatch/],
  [d=>d.meshes[0].primitives[0].extras.native_batches[0].vertex_start=1,/batch context/],
  [d=>d.meshes[0].primitives[0].extras.native_batches[0].header_words=[0],/batch context/],
  [d=>d.meshes[0].primitives[0].extras.native_batches[0].vertex_count=2,/batch coverage/]
])assert.throws(()=>parseEditableGLB(fixture((d,b)=>{addNativeInputs(d,b);mutate(d,b);})),reason);
assert.deepEqual([...parseEditableGLB(nativeNormals).meshes[0][0].mc3NativeNormals],[0,0,1,0,0,1,0,0,1]);
assert.throws(()=>parseEditableGLB(fixture(d=>{d.accessors.push({...d.accessors[1],count:2});d.meshes[0].primitives[0].attributes._MC3_NATIVE_NORMAL=4;})),/MC3 native normal count mismatch/);
function requireNativeReflection(d) {
  d.extras={source_profile:'mc3-ps2-static-preview-v1',tireAlphaTranslation:{policy:'native-ps2-tire-reflection-v2'}};
  d.materials[0].extras={shader_template:'tire'};
}
assert.throws(()=>parseEditableGLB(fixture(requireNativeReflection)),/MC3 native reflection needs the original normal attribute/);
assert.doesNotThrow(()=>parseEditableGLB(fixture(d=>{requireNativeReflection(d);d.meshes[0].primitives[0].attributes._MC3_NATIVE_NORMAL=1;})));
assert.equal(parseEditableGLB(data).meshes[0][0].indices.length,3);
assert(parseEditableGLB(data).meshes[0][0].indices instanceof Uint32Array,'imported16-bit GLB indices normalize to32-bit');
const colored=fixture(d=>{d.accessors.push({...d.accessors[1]});d.meshes[0].primitives[0].attributes.COLOR_0=4;});
assert.deepEqual([...parseEditableGLB(colored).meshes[0][0].colors],[0,0,1,0,0,1,0,0,1]);
function addVariants(d) {
  d.extensionsUsed=['KHR_materials_variants'];
  d.extensions={KHR_materials_variants:{variants:[{name:'Native white'},{name:'Native red'}]}};
  d.materials.push({alphaMode:'BLEND',pbrMetallicRoughness:{baseColorFactor:[0.6,0.2,0.1,0.4],baseColorTexture:{index:1},roughnessFactor:0.3,metallicFactor:0.2}});
  d.images.push({...d.images[0]});d.textures.push({source:1});
  d.meshes[0].primitives[0].extensions={KHR_materials_variants:{mappings:[{material:0,variants:[0]},{material:1,variants:[1]}]}};
  d.accessors.push({...d.accessors[1]});d.meshes[0].primitives[0].attributes.COLOR_0=4;
  d.meshes[0].primitives.push({...d.meshes[0].primitives[0],extensions:undefined});
}
const variantData=fixture(addVariants);
assert.deepEqual(parseEditableGLB(variantData).colourVariants.map(v=>v.name),['Native white','Native red']);
for(const [mutate,reason] of [
  [d=>d.extensionsRequired=['KHR_materials_variants'],/Unsupported/],
  [d=>delete d.extensionsUsed,/Invalid GLB colour variants/],
  [d=>d.extensions.KHR_materials_variants.variants=[],/Invalid GLB colour variants/],
  [d=>d.extensions.KHR_materials_variants.variants[0].name=7,/Invalid GLB colour variants/],
  [d=>delete d.extensions,/Invalid GLB colour mappings/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings=null,/Invalid GLB colour mappings/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[0].variants=[],/Invalid GLB colour mappings/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[1].variants=[0],/duplicate GLB colour variant/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[1].variants=[1,1],/duplicate GLB colour variant/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[1].variants=[2],/Invalid or duplicate/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[1].variants=[-1],/Invalid or duplicate/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[1].variants=['1'],/Invalid or duplicate/],
  [d=>d.meshes[0].primitives[0].extensions.KHR_materials_variants.mappings[1].material=2,/Missing GLB material/],
  [d=>d.materials[1].pbrMetallicRoughness.baseColorTexture.index=2,/Invalid GLB texture mapping/],
  [d=>{delete d.meshes[0].primitives[0].attributes.TEXCOORD_0;delete d.materials[0].pbrMetallicRoughness.baseColorTexture;},/Invalid GLB texture mapping/],
  [d=>d.meshes[0].primitives[0].extensions.UNKNOWN_extension={},/static triangles/]
])assert.throws(()=>parseEditableGLB(fixture(d=>{addVariants(d);mutate(d);})),reason);
for(const mutate of [d=>d.nodes[0].children=[0],d=>d.accessors[0].count=100,d=>d.images[0].uri='https://example.com/secret',d=>d.nodes[0].rotation=[0,0,0,0],d=>d.meshes[0].primitives[0].mode=1,(_d,b)=>b.writeUInt16LE(7,96),(_d,b)=>b.writeFloatLE(NaN,0),d=>d.bufferViews[0].byteOffset=-1,d=>d.nodes[0].scale=[0,1,1]])assert.throws(()=>parseEditableGLB(fixture(mutate)));
const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');
const car={model:{source:{glb:'dealership/models/GT_TEST.glb',sha256:hash}}};
const texture=new THREE.Texture();let textureDisposals=0;texture.addEventListener('dispose',()=>textureDisposals++);
const group=await loadEditableGLB(car,{fetchImpl:async()=>data,textureImpl:async()=>texture});
const bounds=new THREE.Box3().setFromObject(group);assert.equal(bounds.min.y,0);assert.equal(bounds.min.x+bounds.max.x,0);
const mesh=group.children[0].children[0];assert(mesh.geometry.index.array instanceof Uint32Array);assert.equal(mesh.material.map,texture);assert.equal(mesh.material.alphaTest,0.25);assert.equal(mesh.material.transparent,false);
disposeCar(group);assert.equal(textureDisposals,1);
const nativeHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',nativeNormals)),v=>v.toString(16).padStart(2,'0')).join('');
const nativeGroup=await loadEditableGLB({model:{source:{...car.model.source,sha256:nativeHash}}},{fetchImpl:async()=>nativeNormals,textureImpl:async()=>new THREE.Texture()});
assert.deepEqual([...nativeGroup.children[0].children[0].geometry.attributes.mc3NativeNormal.array],[0,0,1,0,0,1,0,0,1]);
disposeCar(nativeGroup);
const nativeInputHash=Buffer.from(await crypto.subtle.digest('SHA-256',nativeInputs)).toString('hex');
const nativeInputGroup=await loadEditableGLB({model:{source:{...car.model.source,sha256:nativeInputHash}}},{fetchImpl:async()=>nativeInputs,textureImpl:async()=>new THREE.Texture()});
const nativeInputMesh=nativeInputGroup.children[0].children[0];
assert.deepEqual(nativeInputGroup.userData.mc3NativeSkeleton,parseEditableGLB(nativeInputs).doc.extras.nativeSkeleton);
assert.equal(nativeInputGroup.children[0].userData.mc3NativeBone,1);
assert.equal(nativeInputGroup.children[0].name,'native-wheel');
assert.equal(nativeInputMesh.geometry.attributes.mc3NativeUv.itemSize,4);
assert.deepEqual([...nativeInputMesh.geometry.attributes.mc3NativeColor.array],[...nativeParsed.mc3NativeColors]);
assert.deepEqual(nativeInputMesh.geometry.userData.mc3NativeBatches,nativeParsed.mc3NativeBatches);
assert.equal(nativeInputMesh.material.vertexColors,false,'raw VIF color/flag lanes are not normalized display COLOR_0');
disposeCar(nativeInputGroup);
const nativePositionHash=Buffer.from(await crypto.subtle.digest('SHA-256',nativePositions)).toString('hex');
const nativePositionGroup=await loadEditableGLB({model:{source:{...car.model.source,sha256:nativePositionHash}}},{fetchImpl:async()=>nativePositions,textureImpl:async()=>new THREE.Texture()});
const nativePositionMesh=nativePositionGroup.children[0].children[0];
assert.deepEqual([...nativePositionMesh.geometry.attributes.mc3NativePosition.array],[127,-3,4,2048,17,-15,-4096,31,7]);
assert.deepEqual([...nativePositionMesh.geometry.attributes.position.array],[0,0,0,2,0,0,0,2,1],'native source integer lanes never replace editable display rest');
disposeCar(nativePositionGroup);
const colorHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',colored)),v=>v.toString(16).padStart(2,'0')).join('');
const colorGroup=await loadEditableGLB({model:{source:{...car.model.source,sha256:colorHash}}},{fetchImpl:async()=>colored,textureImpl:async()=>new THREE.Texture()});
assert.equal(colorGroup.children[0].children[0].material.vertexColors,true);
assert.equal(colorGroup.children[0].children[0].geometry.attributes.color.count,3);
disposeCar(colorGroup);
const variantHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',variantData)),v=>v.toString(16).padStart(2,'0')).join('');
const variantTextures=[new THREE.Texture(),new THREE.Texture()];let variantDecodes=0,variantTextureDisposals=0,materialDisposals=0;
for(const t of variantTextures)t.addEventListener('dispose',()=>variantTextureDisposals++);
const variantGroup=await loadEditableGLB({model:{source:{...car.model.source,sha256:variantHash}}},{fetchImpl:async()=>variantData,textureImpl:async()=>variantTextures[variantDecodes++]});
const [variantMesh,unchangedMesh]=variantGroup.children[0].children;
variantMesh.material.addEventListener('dispose',()=>materialDisposals++);
assert.deepEqual(variantGroup.userData.colourVariants,[{index:0,name:'Native white'},{index:1,name:'Native red'}]);
assert.equal(variantGroup.userData.colourVariant,null);
const initialMaterial=variantMesh.material;
variantGroup.userData.setColourVariant(1);
assert.equal(variantMesh.material,initialMaterial,'switching variants reuses the material');
assert.equal(variantMesh.material.map,variantTextures[1]);assert.equal(variantMesh.material.vertexColors,true);
assert.equal(variantMesh.material.transparent,true);assert.equal(variantMesh.material.opacity,0.4);
assert.equal(variantMesh.material.alphaTest,0);assert.equal(variantMesh.material.depthWrite,false);
assert.equal(variantMesh.material.roughness,0.3);assert.equal(variantMesh.material.metalness,0.2);
assert.equal(variantMesh.material.side,THREE.FrontSide);assert.deepEqual(variantMesh.material.color.toArray(),[0.6,0.2,0.1]);
assert.equal(unchangedMesh.material.map,variantTextures[0],'unmapped primitives retain their base material');
variantGroup.userData.setColourVariant(0);
assert.equal(variantMesh.material.map,variantTextures[0]);assert.equal(variantMesh.material.alphaTest,0.25);
assert.equal(variantMesh.material.transparent,false);assert.equal(variantMesh.material.vertexColors,true);
assert.equal(variantMesh.material.side,THREE.DoubleSide);assert.equal(variantMesh.material.depthWrite,true);
const geometryBefore=variantMesh.geometry.attributes.position.array.slice(),colourBefore=variantMesh.geometry.attributes.color.array.slice();
variantGroup.userData.setColourTint('#FF0000');assert.equal(variantGroup.userData.colourTint,'#ff0000');
assert.deepEqual(variantMesh.material.color.toArray(),[1,0,0]);
assert.equal(variantMesh.material.map,variantTextures[0]);assert.equal(variantMesh.material.alphaTest,.25);
assert.deepEqual(variantMesh.geometry.attributes.color.array,colourBefore);assert.deepEqual(variantMesh.geometry.attributes.position.array,geometryBefore);
variantGroup.userData.setColourTint('#0000ff');assert.deepEqual(variantMesh.material.color.toArray(),[0,0,1]);
variantGroup.userData.setColourVariant(1);assert.deepEqual(variantMesh.material.color.toArray(),[.6,.2,.1],'transparent native variant keeps its stored colour');
variantGroup.userData.setColourVariant(0);assert.deepEqual(variantMesh.material.color.toArray(),[0,0,1],'custom preview survives a material reapplication');
assert.throws(()=>variantGroup.userData.setColourTint('red'),/Invalid custom colour/);assert.equal(variantGroup.userData.colourTint,'#0000ff');
variantGroup.userData.setColourTint();assert.deepEqual(variantMesh.material.color.toArray(),[1,1,1]);assert.equal(variantGroup.userData.colourTint,null);
assert.equal(variantMesh.material,initialMaterial,'custom changes also reuse the material');
variantGroup.userData.setColourVariant(1);variantGroup.userData.setColourVariant();
assert.equal(variantMesh.material.map,variantTextures[0]);assert.equal(variantGroup.userData.colourVariant,null);
for(const index of [-1,2,0.5,'1'])assert.throws(()=>variantGroup.userData.setColourVariant(index),/Invalid colour variant selection/);
assert.equal(materialDisposals,0);assert.equal(variantTextureDisposals,0);
disposeCar(variantGroup);assert.equal(materialDisposals,1);assert.equal(variantTextureDisposals,2);
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
  console.log(`PASS test_editable_glb: ${index.cars.length} GT GLBs; native variant and custom tint texture/alpha/vertex-colour switches, mapping corruption controls, embedded triangles, transforms, hash mismatch, cancellation and disposal`);
} else console.log('PASS test_editable_glb: synthetic native variant switches, textured triangles and failure controls; GT export not present');
