import * as THREE from './vendor/three.module.js';

// Material, texture and image indices are separate glTF namespaces.
export function applyMaterial(material, doc, images, materialIndex, options={}) {
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
 material.opacity=factor[3];
 material.transparent=source.alphaMode==='BLEND';
 material.alphaTest=source.alphaMode==='MASK'?(source.alphaCutoff??.5):0;
 material.depthWrite=!material.transparent;
 material.roughness=pbr.roughnessFactor??1;
 material.metalness=pbr.metallicFactor??1;
 material.side=source.doubleSided?THREE.DoubleSide:THREE.FrontSide;
 material.wireframe=options.wireframe===true;
 material.needsUpdate=true;
}

export function createMaterial(doc, images, materialIndex) {
 const material=new THREE.MeshStandardMaterial();
 applyMaterial(material,doc,images,materialIndex);
 return material;
}
