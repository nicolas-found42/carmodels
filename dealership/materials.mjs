import * as THREE from './vendor/three.module.js';
import {applyMC3TireMaterial} from './mc3-tire-material.mjs';

export function normaliseColourTint(value) {
 if(value==null)return null;
 if(typeof value!=='string' || !/^#[0-9a-f]{6}$/i.test(value))throw Error('Invalid custom colour. Use #RRGGBB.');
 return value.toLowerCase();
}

// Material, texture and image indices are separate glTF namespaces.
export function applyMaterial(material, doc, images, materialIndex, options={}) {
 const tint=normaliseColourTint(options.colourTint);
 const source=doc.materials[materialIndex], pbr=source.pbrMetallicRoughness||{};
 const factor=pbr.baseColorFactor||[1,1,1,1];
 const textureIndex=pbr.baseColorTexture?.index;
 material.map=options.textures===false||textureIndex===undefined?null:images[doc.textures[textureIndex].source];
 if(material.map) {
  const sampler=doc.samplers?.[doc.textures[textureIndex].sampler]||{};
  const filters={9728:THREE.NearestFilter,9729:THREE.LinearFilter,9984:THREE.NearestMipmapNearestFilter,
   9985:THREE.LinearMipmapNearestFilter,9986:THREE.NearestMipmapLinearFilter,9987:THREE.LinearMipmapLinearFilter};
  material.map.magFilter=options.sharp?THREE.NearestFilter:filters[sampler.magFilter??9729];
  material.map.minFilter=options.sharp?THREE.NearestFilter:filters[sampler.minFilter??9729];
  material.map.generateMipmaps=![THREE.NearestFilter,THREE.LinearFilter].includes(material.map.minFilter);
  material.map.needsUpdate=true;
 }
 material.color.fromArray(factor); // glTF factors already use linear RGB.
 // CSS picker colours are sRGB. Blend surfaces retain their stored glass colour.
 if(tint!==null && source.alphaMode!=='BLEND')material.color.multiply(new THREE.Color(tint));
 material.opacity=factor[3];
 material.transparent=source.alphaMode==='BLEND';
 material.alphaTest=source.alphaMode==='MASK'?(source.alphaCutoff??.5):0;
 material.depthWrite=!material.transparent;
 material.roughness=pbr.roughnessFactor??1;
 material.metalness=pbr.metallicFactor??1;
 if(material.isMeshPhysicalMaterial) {
  const coat=source.extensions?.KHR_materials_clearcoat;
  material.clearcoat=coat?.clearcoatFactor??0;
  material.clearcoatRoughness=coat?.clearcoatRoughnessFactor??0;
 }
 material.side=source.doubleSided?THREE.DoubleSide:THREE.FrontSide;
 material.wireframe=options.wireframe===true;
 applyMC3TireMaterial(material,doc,source);
 material.needsUpdate=true;
}

// `presentation: 'enhanced'` asks for the clearcoat-capable physical material the
// Recovered inspector's enhanced look needs; anything else, including the default,
// builds exactly the standard material it always did.
export function createMaterial(doc, images, materialIndex, options={}) {
 const {presentation}=options;
 if(presentation!==undefined && presentation!=='original' && presentation!=='enhanced')throw Error('Unknown presentation. Use original or enhanced.');
 const material=doc.extras?.gt4Enhancement||presentation==='enhanced'?new THREE.MeshPhysicalMaterial():new THREE.MeshStandardMaterial();
 applyMaterial(material,doc,images,materialIndex);
 return material;
}
