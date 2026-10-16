import assert from 'node:assert/strict';
import * as THREE from '../dealership/vendor/three.module.js';
import {nativeAlphaPixels,createNativeAlphaTexture,updateAlphaSampling,reflectionScale,addNativeReflection} from '../dealership/mc3-tire-material.mjs';
import {applyMaterial,createMaterial} from '../dealership/materials.mjs';
import {prepareMC3Environment,disposeMC3Environment} from '../dealership/mc3-environment.mjs';

const pixels=new Uint8Array(129*4);
for(let alpha=0;alpha<=128;alpha++)pixels[alpha*4+3]=Math.min(255,alpha*2);
const native=nativeAlphaPixels(pixels,129,1);
for(let alpha=0;alpha<=128;alpha++)assert.equal(native[alpha*4],alpha);
assert.equal((native[0]+native[128*4])/2/128,.5,'native texels recover before bilinear interpolation');
assert.throws(()=>nativeAlphaPixels(pixels,3,1),/Invalid MC3 alpha/);
const source=new THREE.Texture({data:pixels,width:129,height:1});
source.flipY=false;source.wrapS=THREE.RepeatWrapping;source.wrapT=THREE.ClampToEdgeWrapping;
source.minFilter=source.magFilter=THREE.LinearFilter;
const alphaTexture=createNativeAlphaTexture(source);
assert.deepEqual(alphaTexture.image.data,native);assert.equal(alphaTexture.colorSpace,THREE.NoColorSpace);
assert.equal(alphaTexture.flipY,false);assert.equal(alphaTexture.wrapS,source.wrapS);assert.equal(alphaTexture.wrapT,source.wrapT);
source.minFilter=source.magFilter=THREE.NearestFilter;updateAlphaSampling(alphaTexture,source);
assert.equal(alphaTexture.minFilter,THREE.NearestFilter);assert.equal(alphaTexture.magFilter,THREE.NearestFilter);
assert.equal(reflectionScale(25),.175);assert.equal(reflectionScale(65),.5);assert.equal(reflectionScale(undefined),.5);
for(const base of [0,17,127,255])assert.equal(addNativeReflection(base,255,0),base,'zero alpha retains the visible base');
assert.equal(addNativeReflection(0,255,128),253);assert.equal(addNativeReflection(0,255,64),126);
assert.equal(addNativeReflection(127,255,128),255,'native add clamps at255');
const doc={extras:{source_profile:'mc3-ps2-static-preview-v1',tireAlphaTranslation:{policy:'native-ps2-tire-reflection-v2'}},textures:[{source:0}],materials:[
 {alphaMode:'OPAQUE',extras:{shader_template:'tire'},pbrMetallicRoughness:{baseColorTexture:{index:0},metallicFactor:0}},
 {alphaMode:'MASK',alphaCutoff:.4,extras:{shader_template:'default_shiny_rim'},pbrMetallicRoughness:{baseColorTexture:{index:0}}}
]};
const original=JSON.stringify(doc),material=createMaterial(doc,[source],0);
assert.equal(material.opacity,1);assert.equal(material.alphaTest,0);assert.equal(material.transparent,false);
const shader=()=>({uniforms:{},vertexShader:THREE.ShaderLib.standard.vertexShader,fragmentShader:THREE.ShaderLib.standard.fragmentShader});
const compiled=shader();material.onBeforeCompile(compiled);
assert.match(compiled.vertexShader,/vec4\(mc3NativeNormal,0\.0\)/);assert.match(compiled.vertexShader,/0\.1\*mc3ClipP.xy/);
assert.match(compiled.fragmentShader,/mc3Cs\*\(mc3Ad\/128\.0\)/);assert.match(compiled.fragmentShader,/sRGBTransferEOTF/);
assert.equal(compiled.uniforms.mc3NativeAlpha.value.image.data[128*4],128);
let alphaDisposed=0;
compiled.uniforms.mc3NativeAlpha.value.addEventListener('dispose',()=>alphaDisposed++);
assert.equal(compiled.uniforms.mc3NativeSpecular.value,null,'shader inspection never invents an environment input');
assert.throws(()=>material.onBeforeRender({},null,{isPerspectiveCamera:true,fov:25}),/environment is not prepared/);
material.onBeforeRender(null,null,{isPerspectiveCamera:true,fov:25});assert.equal(compiled.uniforms.mc3ReflectionScale.value,.175);
material.onBeforeRender(null,null,{isPerspectiveCamera:false});assert.equal(compiled.uniforms.mc3ReflectionScale.value,.5);
const renderer={},provider=await prepareMC3Environment(renderer,{fetchImpl:async()=>({ok:true,json:async()=>({
 native_gs:{schema:1,context:{xy_offset:[32768,32768],scissor:[0,0,256,256],depth_format:'PSMZ16S'},passes:[]},car_heading:0,camera:{eye:[0,0,0],right:[1,0,0],up:[0,1,0],backward:[0,0,1],fov:100,near:.25,far:1000},draws:[],sky:{draws:[],images:{}},images:{panorama:{width:1,height:1,rgba_base64:'AAAAAA=='}}
})})});
let sharedDisposed=0;provider.texture.addEventListener('dispose',()=>sharedDisposed++);
material.onBeforeRender(renderer,null,new THREE.PerspectiveCamera(40));
assert.equal(compiled.uniforms.mc3NativeSpecular.value,provider.texture,'native lookup reaches already-compiled shader');
const alphaVersion=compiled.uniforms.mc3NativeAlpha.value.version;
material.onBeforeRender(null,null,{isPerspectiveCamera:true,fov:65});
assert.equal(compiled.uniforms.mc3NativeAlpha.value.version,alphaVersion,'unchanged sampler does not upload each frame');
applyMaterial(material,doc,[source],0,{sharp:true});const recompiled=shader();material.onBeforeCompile(recompiled);
assert.equal(recompiled.uniforms.mc3NativeAlpha.value,compiled.uniforms.mc3NativeAlpha.value,'updates reuse the per-material alpha cache');
assert.equal(recompiled.uniforms.mc3NativeAlpha.value.minFilter,THREE.NearestFilter);
applyMaterial(material,doc,[source],1);assert.equal(alphaDisposed,1);
assert.equal(sharedDisposed,0,'material reset does not dispose the renderer-owned environment');
assert.equal(material.alphaTest,.4);const ordinary=shader();material.onBeforeCompile(ordinary);assert.deepEqual(ordinary.uniforms,{});
applyMaterial(material,doc,[source],0,{textures:false});assert.equal(material.map,null);assert.equal(material.alphaTest,0);
applyMaterial(material,doc,[source],0);const final=shader();material.onBeforeCompile(final);
let finalDisposed=0;final.uniforms.mc3NativeAlpha.value.addEventListener('dispose',()=>finalDisposed++);material.dispose();assert.equal(finalDisposed,1);
const foreign=structuredClone(doc);foreign.extras.source_profile='other-game';const other=createMaterial(foreign,[source],0),otherShader=shader();other.onBeforeCompile(otherShader);assert.deepEqual(otherShader.uniforms,{});
assert.equal(JSON.stringify(doc),original,'render hooks retain export metadata');
disposeMC3Environment(renderer);assert.equal(sharedDisposed,1);
console.log('PASS test_mc3_tire_material: per-texel native alpha recovery, bilinear alpha endpoint, sampler controls and mandatory native environment input');
