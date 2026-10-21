import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../dealership/vendor/three.module.js';
import {createMaterial} from '../dealership/materials.mjs';
import {readGLB,assetURL} from '../dealership/model-load.mjs';
import {createPresentation,isTexturedOpaque,presentationMode,ENHANCED_PRESENTATION} from '../dealership/enhanced-presentation.mjs';
import {createContactShadow,CONTACT_SHADOW} from '../dealership/contact-shadow.mjs';

// The studio is injected so the renderer/scene state machine is testable without WebGL;
// the real default is the in-repo asset-free environment (dealership/gt4-studio.mjs).
const environmentTexture={isTexture:true};
function stubStudio() {
  return {calls:[],disposed:false,
    setEnabled(scene,enabled){this.calls.push(enabled);scene.environment=enabled?environmentTexture:null;scene.environmentIntensity=enabled?.8:1;},
    dispose(){this.disposed=true;}};
}
// The renderer is stubbed too: the presentation's only renderer use is the render-target, clear
// alpha and render calls it makes, so a recorder makes the shadow passes observable without WebGL.
function stubRenderer() {
  return {calls:[],target:null,clearAlpha:0,toneMapping:THREE.NoToneMapping,toneMappingExposure:1,
    setRenderTarget(target){this.target=target;this.calls.push({call:'target',target});},
    getClearAlpha(){return this.clearAlpha;},
    setClearAlpha(alpha){this.clearAlpha=alpha;this.calls.push({call:'alpha',alpha});},
    render(object,camera){this.calls.push({call:'render',object,camera,target:this.target,visible:object.visible,
      override:object.isScene?object.overrideMaterial:null,background:object.isScene?object.background:undefined,
      // the scene's children are snapshotted because the shadow group is hidden for the depth pass
      children:object.isScene?object.children.map(child=>({name:child.name,visible:child.visible})):null,
      // and the blur plane's material and uniforms change from pass to pass
      material:object.material??null,
      shader:object.material?.fragmentShader??null,
      uniforms:object.material?.uniforms?{tDiffuse:object.material.uniforms.tDiffuse.value,h:object.material.uniforms.h.value}:null});}};
}

// 1. Original is the default and does not touch the renderer, the scene or the studio.
{
  const renderer=stubRenderer(),scene=new THREE.Scene(),studio=stubStudio();
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
  const renderer=stubRenderer(),scene=new THREE.Scene(),studio=stubStudio();
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
  const renderer=stubRenderer(),scene=new THREE.Scene(),studio=stubStudio();
  const shadow=createContactShadow(renderer);
  const presentation=createPresentation(renderer,scene,{studio,shadow});
  const box=new THREE.Box3(new THREE.Vector3(-1,0,-2),new THREE.Vector3(1,1,2));
  presentation.follow(box);
  for(const value of ['ENHANCED','',null,undefined,1,{}])
    assert.throws(()=>presentation.setMode(value),/Unknown presentation/);
  assert.throws(()=>presentationMode('enhanced '),/Unknown presentation/);
  assert.equal(presentationMode('enhanced'),'enhanced');
  assert.deepEqual(studio.calls,[],'a rejected mode never reaches the studio');
  assert.equal(presentation.mode,'original');
  assert.equal(renderer.toneMapping,THREE.NoToneMapping);
  // the guard fires before anything is built, added or rendered
  assert.equal(shadow.enabled,false);
  assert.equal(shadow.ground,null);
  assert.equal(shadow.plane,null);
  assert.deepEqual(scene.children,[]);
  assert.deepEqual(renderer.calls,[]);
}
// 4. The contact shadow refuses a resolution it cannot render.
{
  assert.throws(()=>createContactShadow(stubRenderer(),{resolution:0}),/resolution/);
  assert.throws(()=>createContactShadow(stubRenderer(),{resolution:512.5}),/resolution/);
  const shadow=createContactShadow(stubRenderer(),{resolution:512});
  assert.equal(shadow.enabled,false);
  shadow.dispose();
}
// 5. Only textured, opaque coverage takes the clearcoat.
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
  const presentation=createPresentation(stubRenderer(),new THREE.Scene(),{studio:stubStudio()});
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

// 6. Real recovered Ford Racing 2 materials: Original is exactly the pre-change path.
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
const enhancedPresentation=createPresentation(stubRenderer(),new THREE.Scene(),{studio:stubStudio()});
enhancedPresentation.setMode('enhanced');
const texturedOpaque=[],originalOnly=createPresentation(stubRenderer(),new THREE.Scene(),{studio:stubStudio()});
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

// 7. Enhanced stands the car on a ground surface with a soft contact shadow; Original builds
// neither. The technique is three.js's contact shadow -- a depth pass under the floor, blurred and
// painted on a plane -- so the whole pipeline is observable through the renderer calls it makes.
function sceneBox(doc,index) {
  const box=new THREE.Box3(),root=new THREE.Matrix4();
  function walk(index,parent) {
    const node=doc.nodes[index],local=new THREE.Matrix4();
    if(node.matrix)local.fromArray(node.matrix);
    else local.compose(new THREE.Vector3().fromArray(node.translation||[0,0,0]),new THREE.Quaternion().fromArray(node.rotation||[0,0,0,1]),new THREE.Vector3().fromArray(node.scale||[1,1,1]));
    const matrix=parent.clone().multiply(local);
    if(node.mesh!==undefined)for(const primitive of doc.meshes[node.mesh].primitives) {
      const accessor=doc.accessors[primitive.attributes.POSITION];
      box.union(new THREE.Box3(new THREE.Vector3().fromArray(accessor.min),new THREE.Vector3().fromArray(accessor.max)).applyMatrix4(matrix));
    }
    for(const child of node.children||[])walk(child,matrix);
  }
  for(const node of doc.scenes[index].nodes)walk(node,root);
  return box;
}
const close=(actual,expected,message)=>assert(Math.abs(actual-expected)<1e-9,`${message}: ${actual} vs ${expected}`);
const planeSide=box=>{const extent=box.getSize(new THREE.Vector3());return Math.max(extent.x,extent.z,CONTACT_SHADOW.minimumFootprint)*(1+CONTACT_SHADOW.margin);};
const torinoBox=sceneBox(doc,doc.scene),fordGTBox=sceneBox(fordGT,fordGT.scene);
assert.equal(doc.scene,6,'the Gran Torino GLB stores tree 0 low-speed as its default scene');
assert.equal(torinoBox.isEmpty(),false);
assert.equal(fordGTBox.isEmpty(),false);
close(torinoBox.min.y,0,'the recovered Gran Torino stands on y=0');
{
  // Original: no ground and no shadow are built, added or drawn.
  const renderer=stubRenderer(),scene=new THREE.Scene();
  scene.background=new THREE.Color('#151a22');
  const shadow=createContactShadow(renderer);
  const presentation=createPresentation(renderer,scene,{studio:stubStudio(),shadow});
  presentation.follow(torinoBox);
  assert.equal(shadow.enabled,false);
  assert.equal(shadow.ground,null,'Original builds no ground surface');
  assert.equal(shadow.plane,null,'Original builds no shadow plane');
  assert.equal(shadow.camera,null);
  assert.equal(shadow.renders,0);
  assert.equal(shadow.update(scene),false,'Original draws no shadow pass');
  assert.equal(presentation.prepare(),false,'the per-frame hook does nothing in Original');
  assert.deepEqual(scene.children,[],'Original adds nothing to the scene');
  assert.deepEqual(renderer.calls,[],'the shadow path never reaches the renderer while Original is selected');
}
{
  // Enhanced: a ground under the car, a shadow on it, both placed from the visible box.
  const renderer=stubRenderer(),scene=new THREE.Scene(),background=new THREE.Color('#151a22');
  scene.background=background;
  const shadow=createContactShadow(renderer);
  const presentation=createPresentation(renderer,scene,{studio:stubStudio(),shadow});
  presentation.follow(torinoBox);
  presentation.setMode('enhanced');
  assert.equal(shadow.enabled,true);
  const group=scene.children.find(object=>object.name==='contact-shadow');
  assert(group,'Enhanced adds the ground and the shadow to the scene');
  assert.equal(group.children.includes(shadow.ground),true);
  assert.equal(group.children.includes(shadow.plane),true);
  assert.equal(shadow.ground.name,'contact-shadow-ground');
  assert.equal(shadow.plane.name,'contact-shadow-plane');
  assert.equal(group.visible,true);
  // The placement is derived from the visible geometry's box, which is the page's only input:
  // the selected car and the geometry choice both arrive as a fresh box.
  const extent=torinoBox.getSize(new THREE.Vector3()),centre=torinoBox.getCenter(new THREE.Vector3());
  const side=planeSide(torinoBox),height=Math.max(torinoBox.max.y-torinoBox.min.y,Math.max(extent.x,extent.z,CONTACT_SHADOW.minimumFootprint)*.05);
  close(group.position.x,centre.x,'the ground is centred on the car');
  close(group.position.z,centre.z);
  close(group.position.y,torinoBox.min.y,"the ground sits at the car's lowest point");
  close(shadow.plane.scale.x,side,'the shadow plane spans the footprint plus its margin');
  close(shadow.plane.scale.z,side);
  close(shadow.plane.position.y,-side*CONTACT_SHADOW.planeDrop,'and sits a hair under the floor the placement chose, so the recovered under-car shadow quad stands above it');
  close(shadow.ground.scale.x,side*CONTACT_SHADOW.groundSpan,'the ground extends well past the shadow');
  close(shadow.ground.position.y,-side*CONTACT_SHADOW.groundDrop,'and sits a hair below the contact plane');
  close(shadow.camera.left,-side/2,'the depth camera covers exactly the shadow plane');
  close(shadow.camera.top,side/2);
  close(shadow.camera.near,0);
  close(shadow.camera.far,side*CONTACT_SHADOW.cameraDrop+height*1.05,"the depth camera reaches the car's roof");
  assert.equal(presentation.prepare(),true,'the first Enhanced frame draws the shadow');
  // the pass sequence, read back from the renderer
  const passes=renderer.calls.filter(call=>call.call==='render');
  assert.equal(passes.length,5,'one depth pass and two two-pass blurs');
  assert.equal(passes[0].object,scene);
  assert.equal(passes[0].camera,shadow.camera);
  assert.equal(passes[0].target.texture,shadow.plane.material.map,'the plane samples the target the passes write');
  assert.equal(passes[0].override.isMeshDepthMaterial,true);
  assert.equal(passes[0].override.depthPacking,THREE.BasicDepthPacking);
  assert.equal(passes[0].override.side,THREE.DoubleSide,'both faces of an unproven winding reach the depth field');
  assert.equal(passes[0].children.find(child=>child.name==='contact-shadow').visible,false,'the ground and the shadow are outside the depth pass');
  assert.equal(passes[0].background,null,'the page backdrop does not fill the depth target');
  assert.equal(scene.background,background,'and it is restored straight after');
  assert.equal(scene.overrideMaterial,null,"the depth override never reaches the page's own render");
  assert.equal(group.visible,true,'the ground is visible again for the page render');
  // the rewrite the height field depends on is the tracked three.js r182 string
  const depthShader={uniforms:{},fragmentShader:'gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );'};
  passes[0].override.onBeforeCompile(depthShader);
  assert.equal(depthShader.uniforms.darkness.value,CONTACT_SHADOW.darkness);
  assert.match(depthShader.fragmentShader,/gl_FragColor = vec4\( vec3\( 0\.0 \), \( 1\.0 - fragCoordZ \) \* darkness \);/,'black where a surface meets the floor, feathered with its height');
  // the blur: nine weighted samples per axis, a narrower second pass, ping-ponged into the plane's texture
  const blurs=passes.slice(1);
  // dispose() must release the depth material as well as the rest of the field
  const depthMaterial=passes[0].override;
  let depthDisposed=false;const depthDispose=depthMaterial.dispose.bind(depthMaterial);
  depthMaterial.dispose=()=>{depthDisposed=true;depthDispose();};
  assert.deepEqual(blurs.map(pass=>pass.material.name),['HorizontalBlurShader','VerticalBlurShader','HorizontalBlurShader','VerticalBlurShader']);
  // The generated offsets, not the shader text: each tap moves along one axis by a whole multiple of
  // the step h, and the outermost tap lands the configured blur radius away in texture pixels.
  const texels=(pass,factors,offset)=>Math.max(...factors.map(factor=>Math.abs(factor)))*pass.uniforms.h*offset;
  const reach=[];
  for(const pass of blurs) {
    assert.equal((pass.shader.match(/sum \+= texture2D/g)||[]).length,9,'nine samples per pass');
    const taps=[...pass.shader.matchAll(/vUv \+ vec2\( (-?[\d.]+), (-?[\d.]+) \) \* (-?[\d.]+) \* h/g)].map(match=>match.slice(1).map(Number));
    assert.equal(taps.length,9,'every tap is one axis-aligned step of h from the texel: a second h in the offset would collapse the blur');
    assert.deepEqual(taps.map(([, , factor])=>factor).sort((a,b)=>a-b),[-4,-3,-2,-1,0,1,2,3,4]);
    for(const [x,y] of taps)assert.equal(Math.abs(x)+Math.abs(y),1,'a tap moves along one axis only');
    reach.push(texels(pass,taps.map(([, , factor])=>factor),CONTACT_SHADOW.resolution));
  }
  assert.deepEqual(reach,[40,40,16,16],'the outermost tap lands 40 texture pixels from the texel for the full-width pair and 16 for the narrower second pair, at the shipped 1024² and blur '+CONTACT_SHADOW.blur);
  assert.deepEqual(blurs.map(pass=>pass.uniforms.h),[CONTACT_SHADOW.blur/256,CONTACT_SHADOW.blur/256,CONTACT_SHADOW.blur*.4/256,CONTACT_SHADOW.blur*.4/256]);
  assert.equal(blurs[0].uniforms.tDiffuse,passes[0].target.texture,'the horizontal pass blurs the depth field');
  assert.equal(blurs[3].uniforms.tDiffuse,blurs[2].target.texture);
  assert.equal(blurs[3].target,passes[0].target,'the last pass writes the texture the plane shows');
  assert.equal(blurs.every(pass=>pass.visible),true);
  assert.equal(shadow.renders,1);
  const drawn=renderer.calls.length;
  assert.equal(presentation.prepare(),false,'an unchanged car is not drawn again');
  assert.equal(renderer.calls.length,drawn,'so a still frame costs nothing at all');
  assert.equal(shadow.renders,1);
  // The car change: the Ford GT's own recovered box moves and resizes the ground and the shadow.
  const fordGTExtent=fordGTBox.getSize(new THREE.Vector3()),fordGTCentre=fordGTBox.getCenter(new THREE.Vector3());
  assert.notDeepEqual(fordGTExtent.toArray(),extent.toArray(),'the two cars really have different boxes');
  presentation.follow(fordGTBox);
  assert.equal(presentation.prepare(),true,'a new car is drawn');
  assert.equal(shadow.renders,2);
  close(group.position.x,fordGTCentre.x);
  close(group.position.z,fordGTCentre.z);
  close(group.position.y,fordGTBox.min.y);
  close(shadow.plane.scale.x,planeSide(fordGTBox));
  assert(Math.abs(shadow.plane.scale.x-side)>.1,'and the shadow plane visibly changed size');
  // The geometry choice: another recovered tree of the same car is a different box again.
  const treeBox=sceneBox(doc,4);
  assert.equal(treeBox.isEmpty(),false);
  assert.notDeepEqual(treeBox.getSize(new THREE.Vector3()).toArray(),extent.toArray(),'the geometry choice really changes the box');
  presentation.follow(treeBox);
  assert.equal(presentation.prepare(),true,'a different record is drawn');
  assert.equal(shadow.renders,3);
  close(shadow.plane.scale.x,planeSide(treeBox));
  close(group.position.z,treeBox.getCenter(new THREE.Vector3()).z);
  // An empty source tree is not a car, and neither is a cleared viewer: nothing to stand on.
  const emptyBox=sceneBox(doc,10);
  assert.equal(emptyBox.isEmpty(),true,'tree 4 of the low-speed set carries no drawable geometry');
  presentation.follow(emptyBox);
  assert.equal(group.visible,false,'an empty tree shows no ground and no shadow');
  assert.equal(presentation.prepare(),false,'and draws nothing');
  presentation.follow(null);
  assert.equal(group.visible,false,'nor does a car that has not loaded');
  // Control: the placement is derived from the box rather than a constant.
  presentation.follow(sceneBox(doc,doc.scene).translate(new THREE.Vector3(1,0,2)));
  assert.equal(presentation.prepare(),true);
  close(group.position.x,centre.x+1,'a moved box moves the ground');
  close(group.position.z,centre.z+2);
  // The mode round trip: Original takes the ground and the shadow out of the scene.
  presentation.setMode('original');
  assert.equal(shadow.enabled,false);
  assert.equal(group.parent,null,'Original takes the ground and the shadow out of the scene');
  assert.equal(presentation.prepare(),false);
  presentation.setMode('enhanced');
  assert.equal(group.parent,scene,'and Enhanced puts them back');
  assert.equal(presentation.prepare(),true,'redrawing the shadow for the box it already holds');
  presentation.dispose();
  assert.equal(group.parent,null);
  assert.equal(shadow.ground,null,'dispose releases the ground');
  assert.equal(shadow.plane,null);
  assert.equal(depthDisposed,true,'dispose releases the depth material too, so three.js keeps no program reference to it');
  assert.equal(shadow.enabled,false);
}

// 7b. The plane's floor is the lower of the framing box's and the recovered under-car shadow quad's
// (issue #72). The quad is the one surface the framing box deliberately leaves out -- showRecord fits
// the camera to the car alone -- so it arrives as follow()'s second argument.
{
  const renderer=stubRenderer(),scene=new THREE.Scene(),shadow=createContactShadow(renderer);
  const presentation=createPresentation(renderer,scene,{studio:stubStudio(),shadow});
  const box=new THREE.Box3(new THREE.Vector3(-1,0,-2),new THREE.Vector3(1,1,2)),side=planeSide(box);
  const footprint=Math.max(2,2,CONTACT_SHADOW.minimumFootprint);
  presentation.follow(box,0);
  presentation.setMode('enhanced');
  const group=scene.children.find(object=>object.name==='contact-shadow');
  const planeWorld=()=>new THREE.Box3().setFromObject(shadow.plane).min.y;
  close(group.position.y,0,'a quad at the box floor leaves the placement where it was');
  close(planeWorld(),-side*CONTACT_SHADOW.planeDrop,'and the plane is under that quad');
  presentation.follow(box,.25);
  close(group.position.y,0,"a quad above the box's floor cannot lift the plane");
  assert(planeWorld()<.25,'the plane stays under the higher quad too');
  presentation.follow(box,-.003);
  close(group.position.y,-.003,'a quad below the box floor carries the plane down to it');
  close(planeWorld(),-.003-side*CONTACT_SHADOW.planeDrop);
  assert(planeWorld()<-.003,'so the plane is under the quad rather than the quad under the plane');
  close(shadow.camera.far,side*CONTACT_SHADOW.cameraDrop+Math.max(box.max.y+.003,footprint*.05)*1.05,
   'the depth camera reaches the car from that lowered floor');
  // An unusable second input is not a floor: the box's own floor stands (control for the new input).
  for(const value of [undefined,null,NaN,Infinity,'-0.003']) {
   presentation.follow(box,value);
   close(group.position.y,0,`an unusable quad floor (${String(value)}) leaves the box's floor`);
   close(planeWorld(),-side*CONTACT_SHADOW.planeDrop);
  }
  presentation.follow(null,-.003);
  assert.equal(group.visible,false,'nor does an empty box become visible with a floor');
  // The floor survives a mode round trip, because setEnabled() places from what follow() kept.
  presentation.follow(box,-.003);
  presentation.setMode('original');presentation.setMode('enhanced');
  close(group.position.y,-.003,'returning to Enhanced keeps the floor it was given');
  presentation.dispose();
}

// 8. The presentation adds no request of any kind and reuses the in-repo studio environment.
const moduleSource=fs.readFileSync(new URL('../dealership/enhanced-presentation.mjs',import.meta.url),'utf8');
const studioSource=fs.readFileSync(new URL('../dealership/gt4-studio.mjs',import.meta.url),'utf8');
const pageSource=fs.readFileSync(new URL('../dealership/recovered.html',import.meta.url),'utf8');
const materialsSource=fs.readFileSync(new URL('../dealership/materials.mjs',import.meta.url),'utf8');
const shadowSource=fs.readFileSync(new URL('../dealership/contact-shadow.mjs',import.meta.url),'utf8');
const threeSource=fs.readFileSync(new URL('../dealership/vendor/three.module.js',import.meta.url),'utf8');
assert.match(moduleSource,/import \{createGT4Studio\} from '\.\/gt4-studio\.mjs'/,'the environment is the existing in-repo one, not a vendored helper');
assert.match(moduleSource,/import \{createContactShadow\} from '\.\/contact-shadow\.mjs'/,'the ground and the shadow are this repository\'s own module');
assert.doesNotMatch(moduleSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the enhanced path requests nothing');
assert.doesNotMatch(studioSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the reused studio environment is asset-free');
assert.doesNotMatch(materialsSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the material path requests nothing');
assert.deepEqual([...shadowSource.matchAll(/^import .*$/gm)].map(match=>match[0]),["import * as THREE from './vendor/three.module.js';"],'the shadow\'s only import is the pinned vendored three.js: no addon and no vendored example helper');
assert.doesNotMatch(shadowSource,/fetch\(|XMLHttpRequest|https?:\/\//,'the shadow loads no external asset');
assert(threeSource.includes('gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );'),'the depth rewrite still matches the vendored three.js depth shader');
assert(fs.readFileSync(new URL('../dealership/vendor/three.core.js',import.meta.url),'utf8').includes("REVISION = '182'"),'three.js is still at its pinned revision');
assert.match(pageSource,/import \{createPresentation,ENHANCED_PRESENTATION\} from '\.\/enhanced-presentation\.mjs'/);
assert.match(pageSource,/<option value="original" selected>Original<\/option><option value="enhanced">Enhanced<\/option>/,'Original is the default option');
assert.match(pageSource,/<p id="presentation-label" role="note" hidden><\/p>/,'the label starts hidden and is revealed by the enhanced mode');
assert.match(pageSource,/document\.querySelector\('#presentation-label'\)\.hidden=!presentation\.enhanced/,'the label is tied to the enhanced mode');
assert.match(pageSource,/createMaterial\(doc,state\.textures,p\.material,\{presentation:presentation\.mode\}\)/,'loaded meshes follow the selected presentation');
assert.match(pageSource,/presentation\.finish\(m\.material,definition\)/,'the finish is applied after every paint update');
assert.match(pageSource,/presentation\.follow\(box\.isEmpty\(\)\?null:box,underCarShadowFloor\(\)\)/,'the ground and the shadow follow the car, the geometry choice and the drawn under-car shadow quad');
assert.match(pageSource,/function underCarShadowFloor\(\)\{[^\n]*mesh\.userData\.underCarShadow[^\n]*expandByObject\(mesh\)/,'the page measures the floor of the quad the selected view draws');
assert.match(pageSource,/presentation\.follow\(null\)/,'and they are cleared when the preview is disposed');
assert.match(pageSource,/presentation\.prepare\(\);renderer\.render\(scene,camera\)/,'the shadow pass runs before the page\'s own render, beside the other per-frame hooks');
assert.match(pageSource,/title="Original renders the recovered materials[^"]*soft contact shadow under the car/,'the control says what Enhanced adds');
assert.match(pageSource,/download\.href=assetURL\(encodeURI\('public\/'\+entry\.file\)\)/,'the download still serves the unmodified source file');
assert.doesNotMatch(pageSource,/presentation[^\n]{0,80}buffer[^\n]{0,40}=[^\n]{0,40}(gloss|enhanc|finish)/i,'the presentation never rewrites the download buffer');
console.log('PASS test_enhanced_presentation: original default and exact restore, enhanced environment and neutral mapping, label, mode and material-type controls, clearcoat only on textured opaque coverage, real Gran Torino and Ford GT materials, ground and contact shadow built, placed and drawn in enhanced only and following car, geometry, empty tree and dispose, the shadow plane\'s floor taken from the lower of the framing box and the drawn under-car shadow quad, blur tap structure and texture-pixel reach of the generated offsets, depth material released on dispose, asset-free in-repo studio and shadow reused, unchanged download path');
