import assert from 'node:assert/strict';
import * as THREE from '../viewer/vendor/three.module.js';
import {applyMaterial,createMaterial} from '../viewer/materials.mjs';

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
console.log('PASS test_viewer_materials: independent material/texture/image indices, linear factors, alpha, variant changes, toggles, linear/no-mip and Sharp pixels round trip');
