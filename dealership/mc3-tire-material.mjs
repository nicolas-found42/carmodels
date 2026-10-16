import * as THREE from './vendor/three.module.js';
import {nativeGarageProvider} from './mc3-environment.mjs';

// The retained diffuse PNG doubles PS2 palette alpha, saturating 128 to 255.
// Recover each texel before filtering: undoing this after sampling is lossy.
export function nativeAlphaPixels(data,width,height) {
 if(!Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||data.length!==width*height*4)throw Error('Invalid MC3 alpha image.');
 const result=new Uint8Array(data.length);
 for(let i=0;i<data.length;i+=4) {
  const alpha=Math.floor((data[i+3]+1)/2);
  result[i]=result[i+1]=result[i+2]=alpha;result[i+3]=255;
 }
 return result;
}

function imagePixels(image) {
 const width=image.width,height=image.height;
 if(image.data)return {width,height,data:image.data};
 const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
 const context=canvas.getContext('2d',{willReadFrequently:true});
 if(!context)throw Error('MC3 tire alpha decode needs a canvas context.');
 context.drawImage(image,0,0);
 return {width,height,data:context.getImageData(0,0,width,height).data};
}

export function createNativeAlphaTexture(source) {
 const {width,height,data}=imagePixels(source.image);
 const texture=new THREE.DataTexture(nativeAlphaPixels(data,width,height),width,height);
 texture.colorSpace=THREE.NoColorSpace;
 updateAlphaSampling(texture,source);texture.needsUpdate=true;return texture;
}

export function updateAlphaSampling(texture,source) {
 let changed=false;
 for(const key of ['flipY','wrapS','wrapT','magFilter','minFilter','generateMipmaps']) {
  if(texture[key]!==source[key]){texture[key]=source[key];changed=true;}
 }
 if(changed)texture.needsUpdate=true;
}

export function reflectionScale(fov) {
 return Number.isFinite(fov) ? .175+.325*((fov-25)/40) : .5;
}

// Integer GS arithmetic on byte-valued inputs. Base lighting remains the
// viewer's lighting; the native lookup, TFX and blend gains are separate.
export function addNativeReflection(base,lookup,alpha) {
 const source=Math.min(255,Math.floor(lookup*127/128));
 return Math.min(255,base+Math.floor(source*alpha/128));
}

const states=new WeakMap();
export function requiresNativeTireNormal(doc,source) {
 return doc.extras?.source_profile==='mc3-ps2-static-preview-v1'
  && doc.extras?.tireAlphaTranslation?.policy==='native-ps2-tire-reflection-v2'
  && source.extras?.shader_template==='tire';
}
function reset(material) {
 const state=states.get(material);if(!state)return;
 state.alpha.dispose();
 material.onBeforeCompile=state.beforeCompile;
 material.onBeforeRender=state.beforeRender;
 material.customProgramCacheKey=state.cacheKey;
 material.removeEventListener('dispose',state.dispose);
 states.delete(material);
}

export function applyMC3TireMaterial(material,doc,source) {
 const enabled=requiresNativeTireNormal(doc,source) && material.map;
 if(!enabled){reset(material);return;}
 let state=states.get(material);
 if(state?.source!==material.map){reset(material);state=null;}
 if(state){updateAlphaSampling(state.alpha,material.map);return;}
 state={source:material.map,alpha:createNativeAlphaTexture(material.map),lookup:{value:null},
  beforeCompile:material.onBeforeCompile,beforeRender:material.onBeforeRender,cacheKey:material.customProgramCacheKey,
  scale:{value:.5}};
 material.onBeforeCompile=function(shader,renderer) {
  state.beforeCompile.call(this,shader,renderer);
  shader.uniforms.mc3NativeAlpha={value:state.alpha};shader.uniforms.mc3NativeSpecular=state.lookup;shader.uniforms.mc3ReflectionScale=state.scale;
  shader.vertexShader='attribute vec3 mc3NativeNormal;\nuniform float mc3ReflectionScale;\nvarying vec2 mc3ReflectionUv;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <project_vertex>',`#include <project_vertex>
 vec4 mc3ClipP=projectionMatrix*modelViewMatrix*vec4(position,1.0);
 vec4 mc3ClipN=projectionMatrix*modelViewMatrix*vec4(mc3NativeNormal,0.0);
 mc3ReflectionUv=mc3ReflectionScale*(mc3ClipN.xy+0.1*mc3ClipP.xy)+vec2(0.5);`);
  shader.fragmentShader='uniform sampler2D mc3NativeAlpha;\nuniform sampler2D mc3NativeSpecular;\nvarying vec2 mc3ReflectionUv;\n'+shader.fragmentShader;
  shader.fragmentShader=shader.fragmentShader.replace('#include <opaque_fragment>',`
 // Preserve PS2 byte arithmetic in display RGB, separately from viewer lighting.
 float mc3Ad=floor(texture2D(mc3NativeAlpha,vMapUv).r*255.0+0.0001);
 vec3 mc3Tex=texture2D(mc3NativeSpecular,mc3ReflectionUv).rgb*255.0;
 vec3 mc3Cs=min(vec3(255.0),floor(mc3Tex*(127.0/128.0)));
 vec3 mc3Cd=floor(clamp(sRGBTransferOETF(vec4(outgoingLight,1.0)).rgb,0.0,1.0)*255.0+0.5);
 vec3 mc3Result=min(vec3(255.0),mc3Cd+floor(mc3Cs*(mc3Ad/128.0)))/255.0;
 outgoingLight=sRGBTransferEOTF(vec4(mc3Result,1.0)).rgb;
 #include <opaque_fragment>`);
 };
 material.onBeforeRender=function(renderer,scene,camera,...rest) {
  state.beforeRender.call(this,renderer,scene,camera,...rest);
  state.scale.value=reflectionScale(camera.isPerspectiveCamera?camera.fov:undefined);
  if(renderer) {
   const provider=nativeGarageProvider(renderer);provider.updateCamera(camera);state.lookup.value=provider.texture;
  }
  updateAlphaSampling(state.alpha,state.source);
 };
 material.customProgramCacheKey=()=>state.cacheKey.call(material)+';mc3-native-tire-reflection-v2;native-garage-specular-v1';
 state.dispose=()=>reset(material);material.addEventListener('dispose',state.dispose);states.set(material,state);
}
