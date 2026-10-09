import * as THREE from './vendor/three.module.js';

// glTF material, texture and image indexes each refer to their own table.
export function materialOptions(doc, materialIndex, images) {
 const source=doc.materials[materialIndex];
 const pbr=source.pbrMetallicRoughness||{};
 const textureIndex=pbr.baseColorTexture?.index;
 const imageIndex=textureIndex===undefined?undefined:doc.textures[textureIndex].source;
 const factor=pbr.baseColorFactor||[1,1,1,1];
 return {
  map:imageIndex===undefined?null:images[imageIndex],
  color:new THREE.Color().setRGB(factor[0],factor[1],factor[2]),
  opacity:factor[3],
  transparent:source.alphaMode==='BLEND',
  depthWrite:source.alphaMode!=='BLEND'
 };
}
