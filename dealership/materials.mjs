import * as THREE from './vendor/three.module.js';
import {applyMC3TireMaterial} from './mc3-tire-material.mjs';

export function normaliseColourTint(value) {
 if(value==null)return null;
 if(typeof value!=='string' || !/^#[0-9a-f]{6}$/i.test(value))throw Error('Invalid custom colour. Use #RRGGBB.');
 return value.toLowerCase();
}

// The recovered cars name their under-car shadow material UNDER_SHADOW, EX_UNDER_SHADOW2 or
// GT90_UNDER_SHADOW; only Ford Racing 2 carries a material with this shape. The name is the selector,
// never the texture index: the same texture index means different textures on other cars.
export function isRecoveredUnderShadow(source) {
 return typeof source?.name==='string' && /(^|_)UNDER_SHADOW/i.test(source.name);
}

// The recovered under-car shadow is authored OPAQUE: its texture is white with graded alpha (the
// exporter embeds the display-alpha PNG, min(255, 2a), over a stored 0..127 alpha) and its glTF
// material records no blend state, so the quad would draw as a hard square in the material's own
// colour. The repo's captured draws contain no draw for this quad, so the original blend function is
// not captured. The candidate drawn here is the smallest reading of the ticket's own criterion: the
// texture's alpha is the blend factor at the recovered alpha/128 scale (the scale the glass path
// already uses) and the quad keeps its stored colour. Candidate, not a trace: the stored colour is
// white in every car, so this blend lightens rather than darkens the studio background, and the game's
// darker ground-contact appearance is not reproduced.
export function applyRecoveredUnderShadow(material, source) {
 if(!isRecoveredUnderShadow(source))return false;
 material.transparent=true;
 material.depthWrite=false;
 return true;
}

// GT4 also draws a body "overlay" pass: a shape the render model hands to the GS with no MDLS
// material and depth writes off, which the exporter names body/setN/texN/mat-1[+vc]/BLEND/paintN.
// The native walk shows it re-draws body geometry the same frame already drew (the shape kinds the
// preview profile omits), so over the paint it reads as dark blotches on roof edges, pillars and
// window surrounds. Previews committed before that omission still carry the pass; skip it here too.
export function isGT4OverlayPass(source) {
 return typeof source?.name==='string' && /\/mat-1(?:\+vc)?\/BLEND\//.test(source.name);
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
  const wraps={33071:THREE.ClampToEdgeWrapping,10497:THREE.RepeatWrapping,33648:THREE.MirroredRepeatWrapping};
  if(sampler.wrapS)material.map.wrapS=wraps[sampler.wrapS]??THREE.RepeatWrapping;
  if(sampler.wrapT)material.map.wrapT=wraps[sampler.wrapT]??THREE.RepeatWrapping;
  material.map.needsUpdate=true;
 }
 material.color.fromArray(factor); // glTF factors already use linear RGB.
 // CSS picker colours are sRGB. Blend surfaces retain their stored glass colour.
 if(tint!==null && source.alphaMode!=='BLEND')material.color.multiply(new THREE.Color(tint));
 material.opacity=factor[3];
 material.transparent=source.alphaMode==='BLEND';
 material.alphaTest=source.alphaMode==='MASK'?(source.alphaCutoff??.5):0;
 material.depthWrite=!material.transparent;
 applyRecoveredUnderShadow(material,source);
 material.roughness=pbr.roughnessFactor??1;
 material.metalness=pbr.metallicFactor??1;
 if(material.isMeshPhysicalMaterial) {
  const coat=source.extensions?.KHR_materials_clearcoat;
  material.clearcoat=coat?.clearcoatFactor??0;
  material.clearcoatRoughness=coat?.clearcoatRoughnessFactor??0;
 }
 material.side=(source.doubleSided&&!source.name?.startsWith('body/'))?THREE.DoubleSide:THREE.FrontSide;
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
