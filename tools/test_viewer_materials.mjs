import assert from 'node:assert/strict';
import * as THREE from '../dealership/vendor/three.module.js';
import {applyMaterial,createMaterial,isGT4OverlayPass} from '../dealership/materials.mjs';

const images=[new THREE.Texture(),new THREE.Texture()];
const doc={samplers:[{magFilter:9729,minFilter:9729}],textures:[{source:1,sampler:0},{source:0,sampler:0}],materials:[
 {pbrMetallicRoughness:{baseColorFactor:[0,0,0,.7]},alphaMode:'BLEND',doubleSided:true},
 {pbrMetallicRoughness:{baseColorTexture:{index:0},baseColorFactor:[.2,.4,.6,1],roughnessFactor:.9,metallicFactor:0}},
 {pbrMetallicRoughness:{baseColorTexture:{index:1}}},
]};
const material=createMaterial(doc,images,0);
assert.equal(material.map,null);
assert.deepEqual(material.color.toArray(),[0,0,0]);
assert.equal(material.opacity,.7);
assert.equal(material.transparent,true);
assert.equal(material.depthWrite,false);
applyMaterial(material,doc,images,1);
assert.equal(material.map,images[1]);
assert.equal(material.map.magFilter,THREE.LinearFilter);
assert.equal(material.map.minFilter,THREE.LinearFilter);
assert.equal(material.map.generateMipmaps,false);
applyMaterial(material,doc,images,1,{sharp:true});
assert.equal(material.map.magFilter,THREE.NearestFilter);
assert.equal(material.map.minFilter,THREE.NearestFilter);
applyMaterial(material,doc,images,1);
assert.equal(material.map.magFilter,THREE.LinearFilter);
assert.deepEqual(material.color.toArray(),[.2,.4,.6]);
assert.equal(material.transparent,false);
assert.equal(material.depthWrite,true);
assert.equal(material.opacity,1);
assert.equal(material.roughness,.9);
assert.equal(material.metalness,0);
applyMaterial(material,doc,images,2,{textures:false,wireframe:true});
assert.equal(material.map,null);
assert.equal(material.wireframe,true);
applyMaterial(material,doc,images,2);
assert.equal(material.map,images[0]);
assert.deepEqual(material.color.toArray(),[1,1,1]);
doc.materials.push({alphaMode:'MASK',alphaCutoff:.3,pbrMetallicRoughness:{baseColorTexture:{index:0}}});
applyMaterial(material,doc,images,3);assert.equal(material.alphaTest,.3);assert.equal(material.transparent,false);assert.equal(material.depthWrite,true);
delete doc.materials[3].alphaCutoff;applyMaterial(material,doc,images,3);assert.equal(material.alphaTest,.5);
applyMaterial(material,doc,images,0);assert.equal(material.alphaTest,0);assert.equal(material.transparent,true);
applyMaterial(material,doc,images,1);assert.equal(material.alphaTest,0);
const before=JSON.stringify(doc),initialTextures=[...images];
applyMaterial(material,doc,images,1,{colourTint:'#808080',sharp:true,wireframe:true});
const grey=new THREE.Color('#808080');
assert.deepEqual(material.color.toArray(),[.2*grey.r,.4*grey.g,.6*grey.b],'picker sRGB converts once before multiplying linear glTF factors');
assert.equal(material.map,images[1]);assert.equal(material.opacity,1);assert.equal(material.wireframe,true);
applyMaterial(material,doc,images,1,{colourTint:'#ff0000'});
assert.deepEqual(material.color.toArray(),[.2,0,0],'repeated picker changes start from source factors, not the previous tint');
doc.materials[0].pbrMetallicRoughness.baseColorFactor=[.2,.3,.4,.7];
applyMaterial(material,doc,images,0,{colourTint:'#ff0000'});
assert.deepEqual(material.color.toArray(),[.2,.3,.4],'transparent glass retains its source colour');
assert.equal(material.opacity,.7);assert.equal(material.transparent,true);
doc.materials[0].pbrMetallicRoughness.baseColorFactor=[0,0,0,.7];
applyMaterial(material,doc,images,3,{colourTint:'#0000ff'});
assert.deepEqual(material.color.toArray(),[0,0,1]);assert.equal(material.alphaTest,.5);assert.equal(material.depthWrite,true);
applyMaterial(material,doc,images,1,{colourTint:null});
assert.deepEqual(material.color.toArray(),[.2,.4,.6]);assert.equal(material.map,images[1]);
for(const value of ['red','#fff','#gg0000','',17,{},[1,0,0]]) {
 assert.throws(()=>applyMaterial(material,doc,images,1,{colourTint:value}),/Invalid custom colour/);
 assert.deepEqual(material.color.toArray(),[.2,.4,.6],'invalid input cannot partially modify the material');
}
assert.equal(JSON.stringify(doc),before);assert.deepEqual(images,initialTextures,'tints reuse the existing texture objects');
// The editable loader forces RepeatWrapping on every texture; a glTF sampler's wrap must win, or
// GT4 body textures clamp-sampled in the game repeat their painted border into roof and pillar UVs.
doc.samplers[0]={wrapS:33071,wrapT:10497};
applyMaterial(material,doc,images,1);
assert.equal(material.map.wrapS,THREE.ClampToEdgeWrapping);
assert.equal(material.map.wrapT,THREE.RepeatWrapping);
images[1].wrapS=images[1].wrapT=THREE.RepeatWrapping;
doc.samplers[0]={};
applyMaterial(material,doc,images,1);
assert.equal(material.map.wrapS,THREE.RepeatWrapping,'no sampler wrap keeps the loader default');
// GT4 body shells are closed: their backfaces are interior panels, and drawing them double-sided
// z-fights the outer panel into dark blotches over the roof and pillars.
doc.materials.push({name:'body/set0/tex20/mat-1+vc/BLEND/paint0',doubleSided:true,pbrMetallicRoughness:{}});
applyMaterial(material,doc,images,4);assert.equal(material.side,THREE.FrontSide);
doc.materials.push({name:'glass/tex2/mat3',doubleSided:true,pbrMetallicRoughness:{}});
applyMaterial(material,doc,images,5);assert.equal(material.side,THREE.DoubleSide);
doc.materials.push({name:'body/set0/tex20/mat2/MASK/paint0',doubleSided:false,pbrMetallicRoughness:{}});
applyMaterial(material,doc,images,6);assert.equal(material.side,THREE.FrontSide);
// A no-material, depth-writes-off body draw is the GT4 overlay pass the exporter omits; committed
// previews still carry it, so the viewer must skip exactly those primitives.
for(const name of ['body/set0/tex20/mat-1+vc/BLEND/paint0','body/set0/tex22/mat-1/BLEND/paint3'])assert.equal(isGT4OverlayPass({name}),true,name);
for(const name of ['body/set0/tex20/mat-2+vc/BLEND/paint0','body/set0/tex20/mat-1+vc/MASK/paint0','body/set0/tex20/mat-1+vc/OPAQUE/paint0','body/set0/tex20/mat-1+vc/BLENDX/paint0',undefined])assert.equal(isGT4OverlayPass({name}),false,String(name));
console.log('PASS test_viewer_materials: independent material/texture/image indices, linear factors, custom sRGB tints/reset/input controls, alpha, variant changes, toggles, linear/no-mip and Sharp pixels, sampler wrap, GT4 body culling and overlay selector round trip');
