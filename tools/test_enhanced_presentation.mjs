import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../dealership/vendor/three.module.js';
import {createMaterial} from '../dealership/materials.mjs';
import {readGLB} from '../dealership/model-load.mjs';
import {createPresentation,isTexturedOpaque,presentationMode,ENHANCED_PRESENTATION} from '../dealership/enhanced-presentation.mjs';

// The studio is injected so the renderer/scene state machine is testable without WebGL;
// the real default is the in-repo asset-free environment (dealership/gt4-studio.mjs).
const environmentTexture={isTexture:true};
function stubStudio() {
  return {calls:[],disposed:false,
    setEnabled(scene,enabled){this.calls.push(enabled);scene.environment=enabled?environmentTexture:null;scene.environmentIntensity=enabled?.8:1;},
    dispose(){this.disposed=true;}};
}
function stubRenderer() {return {toneMapping:THREE.NoToneMapping,toneMappingExposure:1};}

// 1. Original is the default and does not touch the renderer, the scene or the studio.
{
  const renderer=stubRenderer(),scene={environment:null,environmentIntensity:1},studio=stubStudio();
  const presentation=createPresentation(renderer,scene,{studio});
  assert.equal(presentation.mode,'original');
  assert.equal(presentation.enhanced,false);
  assert.equal(presentation.label,'','the enhanced label is absent while the original look is shown');
  assert.deepEqual(studio.calls,[],'the environment is not built for the original look');
  assert.equal(renderer.toneMapping,THREE.NoToneMapping);
  assert.equal(renderer.toneMappingExposure,1);
  assert.equal(scene.environment,null);
  assert.equal(scene.environmentIntensity,1);
  presentation.setMode('original');
  assert.deepEqual(studio.calls,[],'re-selecting original is a no-op, so it cannot drift');
  assert.equal(renderer.toneMapping,THREE.NoToneMapping);
  assert.equal(presentation.label,'');
}
// 2. Enhanced applies the environment and the neutral tone mapper; Original restores exactly.
{
  const renderer=stubRenderer(),scene={environment:null,environmentIntensity:1},studio=stubStudio();
  const presentation=createPresentation(renderer,scene,{studio});
  presentation.setMode('enhanced');
  assert.equal(presentation.enhanced,true);
  assert.deepEqual(studio.calls,[true]);
  assert.equal(scene.environment,environmentTexture,'enhanced reflects the asset-free studio environment');
  assert.equal(scene.environmentIntensity,ENHANCED_PRESENTATION.environmentIntensity);
  assert.equal(renderer.toneMapping,THREE.NeutralToneMapping,'neutral mapping, not the studio\u2019s ACES default');
  assert.equal(renderer.toneMappingExposure,ENHANCED_PRESENTATION.exposure);
  assert(presentation.label.includes('not the original game'),'the label says enhanced is not the original look');
  presentation.setMode('enhanced');
  assert.deepEqual(studio.calls,[true],'re-selecting enhanced does not rebuild the environment');
  presentation.setMode('original');
  assert.deepEqual(studio.calls,[true,false]);
  assert.equal(scene.environment,null);
  assert.equal(scene.environmentIntensity,1);
  assert.equal(renderer.toneMapping,THREE.NoToneMapping);
  assert.equal(renderer.toneMappingExposure,1);
  presentation.setMode('enhanced');presentation.dispose();
  assert.equal(studio.disposed,true,'dispose releases the studio environment');
}
// 3. Unknown modes are rejected before any state changes (control).
{
  const renderer=stubRenderer(),scene={environment:null,environmentIntensity:1},studio=stubStudio();
  const presentation=createPresentation(renderer,scene,{studio});
  for(const value of ['ENHANCED','',null,undefined,1,{}])
    assert.throws(()=>presentation.setMode(value),/Unknown presentation/);
  assert.throws(()=>presentationMode('enhanced '),/Unknown presentation/);
  assert.equal(presentationMode('enhanced'),'enhanced');
  assert.deepEqual(studio.calls,[]);
  assert.equal(presentation.mode,'original');
  assert.equal(renderer.toneMapping,THREE.NoToneMapping);
}
// 4. Only textured, opaque coverage takes the clearcoat.
{
  assert.equal(isTexturedOpaque({pbrMetallicRoughness:{baseColorTexture:{index:0}}}),true);
  assert.equal(isTexturedOpaque({pbrMetallicRoughness:{baseColorTexture:{index:0}},alphaMode:'MASK'}),true,'cutout coverage is still opaque');
  assert.equal(isTexturedOpaque({pbrMetallicRoughness:{baseColorTexture:{index:0}},alphaMode:'BLEND'}),false,'windows keep their recovered appearance');
  assert.equal(isTexturedOpaque({pbrMetallicRoughness:{}}),false);
  assert.equal(isTexturedOpaque(undefined),false,'a missing definition cannot crash the paint update');
  // The recovered under-car shadow is visible in the default view (issue #23) and is a coverage
  // decal, so Enhanced must leave it to its candidate alpha blend instead of glossing it.
  const shadow={name:'UNDER_SHADOW',doubleSided:true,pbrMetallicRoughness:{baseColorTexture:{index:5},metallicFactor:0,roughnessFactor:1}};
  assert.equal(isTexturedOpaque(shadow),false,'the under-car shadow keeps its candidate alpha blend, not a clearcoat');
  assert.equal(isTexturedOpaque({...shadow,name:'GT90_UNDER_SHADOW'}),false);
  assert.equal(isTexturedOpaque({...shadow,name:'BODY_PANEL'}),true,'an ordinary textured surface is unaffected by the exclusion');
}
{
  const presentation=createPresentation(stubRenderer(),{environment:null,environmentIntensity:1},{studio:stubStudio()});
  const textured={pbrMetallicRoughness:{baseColorTexture:{index:0}}},blend={pbrMetallicRoughness:{baseColorTexture:{index:0}},alphaMode:'BLEND'},plain={pbrMetallicRoughness:{}};
  const physical=new THREE.MeshPhysicalMaterial({roughness:.9,metalness:.1});
  assert.equal(presentation.finish(physical,textured),physical);
  assert.deepEqual([physical.roughness,physical.metalness,physical.clearcoat],[.9,.1,0],'original mode never glosses');
  const version=physical.version;
  presentation.setMode('enhanced');
  presentation.finish(physical,textured);
  assert.deepEqual([physical.roughness,physical.metalness,physical.clearcoat,physical.clearcoatRoughness],
    [ENHANCED_PRESENTATION.roughness,ENHANCED_PRESENTATION.metalness,ENHANCED_PRESENTATION.clearcoat,ENHANCED_PRESENTATION.clearcoatRoughness]);
  assert.equal(physical.version,version+1,'the clearcoat define rebuilds the program once');
  presentation.finish(physical,textured);
  assert.equal(physical.version,version+1,'repeat updates are uniform-only and rebuild nothing');
  const untouched=new THREE.MeshPhysicalMaterial({roughness:.9,metalness:.1});
  for(const source of [blend,plain,undefined])presentation.finish(untouched,source);
  assert.deepEqual([untouched.roughness,untouched.metalness,untouched.clearcoat],[.9,.1,0]);
  const authored=new THREE.MeshPhysicalMaterial({roughness:.9,metalness:.1,clearcoat:1,clearcoatRoughness:.03});
  presentation.finish(authored,textured);
  assert.deepEqual([authored.roughness,authored.metalness,authored.clearcoat,authored.clearcoatRoughness],
    [.9,.1,1,.03],'an authored clearcoat (the GT4 refinement) is not replaced by the uniform finish');
  const standard=new THREE.MeshStandardMaterial({roughness:1,metalness:0});
  assert.equal(presentation.finish(standard,textured),standard);
  assert.equal('clearcoat' in standard,false,'a standard material stays a standard material');
}

// 5. Real recovered Ford Racing 2 materials: Original is exactly the pre-change path.
function fixture(path) {
  const bytes=fs.readFileSync(path);
  return bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
}
const glb=name=>new URL(`../dealership/public/ford-racing-2/${name}.glb`,import.meta.url);
const {doc}=readGLB(fixture(glb('GRAN_TORINO')));
const images=doc.images.map(()=>new THREE.Texture());
const sharedState=material=>({map:material.map,name:material.name,color:material.color.toArray(),
  opacity:material.opacity,transparent:material.transparent,alphaTest:material.alphaTest,depthWrite:material.depthWrite,
  side:material.side,wireframe:material.wireframe,roughness:material.roughness,metalness:material.metalness,
  vertexColors:material.vertexColors});
const enhancedPresentation=createPresentation(stubRenderer(),{environment:null,environmentIntensity:1},{studio:stubStudio()});
enhancedPresentation.setMode('enhanced');
const texturedOpaque=[],originalOnly=createPresentation(stubRenderer(),{environment:null,environmentIntensity:1},{studio:stubStudio()});
for(const [index,source] of doc.materials.entries()) {
  const before=createMaterial(doc,images,index); // the pre-change call, unchanged
  const original=createMaterial(doc,images,index,{presentation:'original'});
  assert.equal(original.type,before.type);
  assert.deepEqual(sharedState(original),sharedState(before),'Original renders the material it rendered before the control existed');
  assert.deepEqual([original.roughness,original.metalness,original.clearcoat??null],[1,0,null]);
  const enhanced=createMaterial(doc,images,index,{presentation:'enhanced'});
  assert.equal(enhanced.isMeshPhysicalMaterial,true,'enhanced needs the clearcoat-capable material');
  assert.deepEqual(sharedState(enhanced),sharedState(before),'the class swap alone changes nothing visible');
  assert.equal(enhanced.clearcoat,0,'no clearcoat until the finish is applied');
  originalOnly.finish(enhanced,source);
  assert.equal(enhanced.clearcoat,0,'original mode leaves the physical material unglossed');
  enhancedPresentation.finish(enhanced,source);
  if(isTexturedOpaque(source)) {
    texturedOpaque.push(index);
    assert.equal(enhanced.clearcoat,ENHANCED_PRESENTATION.clearcoat);
    assert.equal(enhanced.clearcoatRoughness,ENHANCED_PRESENTATION.clearcoatRoughness);
    assert.equal(enhanced.metalness,ENHANCED_PRESENTATION.metalness);
    assert.equal(enhanced.map,before.map,'the recovered texture is the same object');
  }else{
    assert.equal(enhanced.clearcoat,0,'untextured header colours and blended glass keep their recovered finish');
    assert.equal(enhanced.roughness,before.roughness);
    assert.equal(enhanced.metalness,before.metalness);
  }
  if(source.name==='UNDER_SHADOW') {
    assert.equal(isTexturedOpaque(source),false,'the under-car shadow is never glossed');
    assert.deepEqual([enhanced.roughness,enhanced.metalness,enhanced.clearcoat],[before.roughness,before.metalness,0],
      'Enhanced leaves the under-car shadow to its candidate alpha blend');
    assert.equal(enhanced.transparent,true,'and that blend still sets transparency');
    assert.equal(enhanced.depthWrite,false,'without writing depth over the wheels');
  }
  assert.throws(()=>createMaterial(doc,images,index,{presentation:'glossy'}),/Unknown presentation/);
  before.dispose();original.dispose();enhanced.dispose();
}
assert.deepEqual(texturedOpaque,[0,1,2,3,4],'the five textured body/wheel surfaces are the ones enhanced glosses; the under-car shadow is excluded');
const fordGT=readGLB(fixture(glb('FORD_GT'))).doc;
assert(fordGT.materials.filter(isTexturedOpaque).length>0,'Ford GT also has textured opaque surfaces to gloss');

// 6. The presentation adds no request of any kind and reuses the in-repo studio environment.
const moduleSource=fs.readFileSync(new URL('../dealership/enhanced-presentation.mjs',import.meta.url),'utf8');
const studioSource=fs.readFileSync(new URL('../dealership/gt4-studio.mjs',import.meta.url),'utf8');
const pageSource=fs.readFileSync(new URL('../dealership/recovered.html',import.meta.url),'utf8');
const materialsSource=fs.readFileSync(new URL('../dealership/materials.mjs',import.meta.url),'utf8');
assert.match(moduleSource,/import \{createGT4Studio\} from '\.\/gt4-studio\.mjs'/,'the environment is the existing in-repo one, not a vendored helper');
assert.doesNotMatch(moduleSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the enhanced path requests nothing');
assert.doesNotMatch(studioSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the reused studio environment is asset-free');
assert.doesNotMatch(materialsSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the material path requests nothing');
assert.match(pageSource,/import \{createPresentation,ENHANCED_PRESENTATION\} from '\.\/enhanced-presentation\.mjs'/);
assert.match(pageSource,/<option value="original" selected>Original<\/option><option value="enhanced">Enhanced<\/option>/,'Original is the default option');
assert.match(pageSource,/<p id="presentation-label" role="note" hidden><\/p>/,'the label starts hidden and is revealed by the enhanced mode');
assert.match(pageSource,/document\.querySelector\('#presentation-label'\)\.hidden=!presentation\.enhanced/,'the label is tied to the enhanced mode');
assert.match(pageSource,/createMaterial\(doc,state\.textures,p\.material,\{presentation:presentation\.mode\}\)/,'loaded meshes follow the selected presentation');
assert.match(pageSource,/presentation\.finish\(m\.material,definition\)/,'the finish is applied after every paint update');
assert.match(pageSource,/download\.href=encodeURI\('public\/'\+entry\.file\)/,'the download still serves the unmodified source file');
assert.doesNotMatch(pageSource,/presentation[^\n]{0,80}buffer[^\n]{0,40}=[^\n]{0,40}(gloss|enhanc|finish)/i,'the presentation never rewrites the download buffer');
console.log('PASS test_enhanced_presentation: original default and exact restore, enhanced environment and neutral mapping, label, mode and material-type controls, clearcoat only on textured opaque coverage, real Gran Torino and Ford GT materials, asset-free in-repo studio reused, unchanged download path');
