import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import zlib from 'node:zlib';
import {fileURLToPath} from 'node:url';
import * as THREE from '../dealership/vendor/three.module.js';
import {readGLB} from '../dealership/model-load.mjs';
import {applyMaterial,createMaterial,isRecoveredUnderShadow} from '../dealership/materials.mjs';
import {createPresentation} from '../dealership/enhanced-presentation.mjs';
import {parseEditableGLB} from '../dealership/editable-glb.mjs';
import {geometryOptions,defaultGeometryValue,sceneLabel} from '../dealership/scene-options.mjs';
import {requiresNativeTireNormal} from '../dealership/mc3-tire-material.mjs';
import {isNativePackage} from '../dealership/dealership.mjs';

// The recovered under-car shadow is authored opaque: a 64x64 white texture with graded alpha on a record
// no exported tree references. This test pins the authored facts, the candidate blend the viewer applies
// instead of an opaque square, the unchanged state of every other material (textured body and the
// glass/Header parts), and the selector the inspector rebuilds the record with. No capture covers this
// quad, so a browser render of it is a separate, documented measurement, not part of this offline check.

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const corpus=path.join(root,'dealership/public/ford-racing-2');

// These producer PNGs are RGBA8, non-interlaced and filter 0; the same reader as the MC3 texture tests.
function rgba(bytes) {
 assert.deepEqual([...bytes.subarray(0,8)],[137,80,78,71,13,10,26,10]);
 let offset=8,width,height;const idat=[];
 while(offset<bytes.length) {
  const size=bytes.readUInt32BE(offset),kind=bytes.toString('latin1',offset+4,offset+8),body=bytes.subarray(offset+8,offset+8+size);
  if(kind==='IHDR'){width=body.readUInt32BE(0);height=body.readUInt32BE(4);assert.deepEqual([...body.subarray(8,13)],[8,6,0,0,0]);}
  if(kind==='IDAT')idat.push(body);
  offset+=12+size;
 }
 const raw=zlib.inflateSync(Buffer.concat(idat)),stride=width*4,pixels=new Uint8Array(stride*height);
 assert.equal(raw.length,height*(stride+1));
 for(let y=0;y<height;y++){assert.equal(raw[y*(stride+1)],0);pixels.set(raw.subarray(y*(stride+1)+1,(y+1)*(stride+1)),y*stride);}
 return {width,height,pixels};
}

// A recovered source GLB with its binary chunk located, so accessor and image bytes can be read directly.
function parse(file) {
 const bytes=fs.readFileSync(path.join(corpus,file));
 const buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
 const {doc}=readGLB(buffer);
 return {doc,buffer,bytes,binStart:20+bytes.readUInt32LE(12)+8};
}

function imageBytes({doc,bytes,binStart},index) {
 const view=doc.bufferViews[doc.images[index].bufferView],start=binStart+(view.byteOffset??0);
 return bytes.subarray(start,start+view.byteLength);
}

function uvPairs({doc,buffer,binStart},index) {
 const accessor=doc.accessors[index],view=doc.bufferViews[accessor.bufferView];
 const stride=view.byteStride??8,start=binStart+(view.byteOffset??0)+(accessor.byteOffset??0);
 const data=new DataView(buffer);
 const pairs=[];
 for(let i=0;i<accessor.count;i++)pairs.push([data.getFloat32(start+i*stride,true),data.getFloat32(start+i*stride+4,true)]);
 return pairs;
}

const html=fs.readFileSync(path.join(root,'dealership/recovered.html'),'utf8');
const selectors=vm.runInNewContext(html.match(/function underCarShadowPrimitive\(doc\).*\n/)[0]+
 html.match(/function sourceSceneRecords\(doc,scene\).*\n/)[0]+';({underCarShadowPrimitive,sourceSceneRecords});',{isRecoveredUnderShadow});

// The rebuild count must be evidence, not a restatement of the assertions above: this runs the page's own
// loader slice (the same slice tools/test_viewer_loading.mjs exercises) for one car and hands back the state
// it built, so every overlay claim below is about the group loadCar actually created.
function loadedByTheInspector(code,file,bytes,records) {
 const ids=['car','record','variant','presentation','presentation-label','textures','sharp','wire','flip','game-shading','game-shading-note','download',
  'native-download','native-download-wrap','retry','error','dealership-link'];
 const elements=Object.fromEntries(ids.map(id=>[id,{value:'',disabled:false,hidden:false,options:[],textContent:'',
  removeAttribute(name){delete this[name];},replaceChildren(...options){this.options=options;},append(option){this.options.push(option);},addEventListener(){}}]));
 const scene=new THREE.Scene(),urls=new Set(),status={textContent:''};
 const context={
  THREE:{...THREE,TextureLoader:class {async loadAsync(){const texture=new THREE.Texture();texture.dispose=()=>{};return texture;}}},
  document:{querySelector(selector){return elements[selector.slice(1)]??null;},createElement(){return {};}},
  carSelect:elements.car,recordSelect:elements.record,stage:{setAttribute(){}},status,scene,sceneLabel,
  index:{cars:[{id:'ford-racing-2/'+code,game:'ford-racing-2',code,file:'ford-racing-2/'+file,display_name:code,records}]},
  colourControls:{enabled:false,setEnabled(value){this.enabled=value;},bind(){},session:null},
  paintDownload:{clear(){}},presentation:{mode:'original',enhanced:false,label:'',setMode(){},finish(material){return material;}},
  gamePalette:[],paletteError:'',paletteReady:Promise.resolve(),loaded:null,selected:null,requestId:0,pendingRequest:null,
  AbortController,Blob,URLSearchParams,
  URL:{createObjectURL(){const id='blob:'+urls.size;urls.add(id);return id;},revokeObjectURL(id){urls.delete(id);}},
  readGLB,parseEditableGLB,loadNativeVehicleResources:async()=>null,bindNativeVehicleResources(){},
  createMaterial,isRecoveredUnderShadow,requiresNativeTireNormal,geometryOptions,defaultGeometryValue,isNativePackage,
  correctGT4Materials:async()=>{throw Error('not a GT4 car');},renderer:{},prepareMC3Environment:async()=>{},
  rememberCar(){},updateDescription(){},fetch:async()=>({ok:true,json:async()=>[]}),
  async fetchModel(){return bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);},
  async prepareMC3Environment(){},
 };
 context.camera=new THREE.PerspectiveCamera();
 context.controls={target:new THREE.Vector3(),update(){}};
 vm.createContext(context);
 const callback=html.slice(html.indexOf('function disposeState('),html.indexOf('function updateMaterials('));
 const helpers=html.slice(html.indexOf('function underCarShadowPrimitive('),html.indexOf('function updateDescription('));
 const showRecord=html.match(/function showRecord\(\).*\n/)[0],shownMeshes=html.match(/function shownMeshes\(root\).*\n/)[0];
 // updateMaterials lives past the slice boundary and needs a paint session; the page's showRecord calls it.
 vm.runInContext(helpers+callback+'function updateMaterials(){}\n'+showRecord+shownMeshes,context);
 return {context,scene,elements,urls,
  async load() {
   context.carSelect.value='ford-racing-2/'+code;
   await context.loadCar();
  },
  show(view) {
   context.recordSelect.value=view;
   vm.runInContext('showRecord();',context);
   return context.loaded;
  }};
}

let cars=0,records=0,rebuilt=0,otherMaterials=0,glassMaterials=0;
for(const file of fs.readdirSync(corpus).filter(name=>name.endsWith('.glb')).sort()) {
 const code=file.replace(/\.glb$/,''),parsed=parse(file),{doc,buffer,bytes}=parsed,textures=doc.images.map(()=>new THREE.Texture());
 const shadows=doc.materials.map((material,index)=>index).filter(index=>isRecoveredUnderShadow(doc.materials[index]));
 assert.equal(shadows.length,1,`${code}: exactly one under-car shadow material`);
 const shadow=shadows[0],source=doc.materials[shadow],pbr=source.pbrMetallicRoughness??{};
 // Authored state: opaque, no colour factor, UVs present, 64x64 white texture with graded alpha.
 assert.equal(source.alphaMode,undefined,`${code}: the shadow material is authored opaque`);
 assert.equal(pbr.baseColorFactor,undefined,`${code}: the shadow material carries no colour factor`);
 const primitives=[];
 for(const [mesh,definition] of doc.meshes.entries())for(const p of definition.primitives)if(p.material===shadow)primitives.push([mesh,p]);
 assert.equal(primitives.length,1,`${code}: one primitive uses the shadow material`);
 const [shadowMesh,primitive]=primitives[0];
 assert(primitive.attributes.TEXCOORD_0!==undefined,`${code}: the shadow primitive samples its texture`);
 assert(primitive.indices!==undefined&&doc.accessors[primitive.indices].count%3===0,`${code}: triangles`);
 const image=doc.textures[pbr.baseColorTexture.index].source;
 const {width,height,pixels}=rgba(imageBytes(parsed,image));
 assert.deepEqual([width,height],[64,64],`${code}: the shadow texture is 64x64`);
 const alphas=[...pixels.filter((_,i)=>i%4===3)];
 assert.equal(Math.min(...alphas),0,`${code}: the shadow texture alpha starts at zero`);
 assert(Math.max(...alphas)>0,`${code}: the shadow texture alpha is graded`);
 assert(alphas.every(value=>value%2===0),`${code}: the shadow texture carries the doubled display alpha`);
 assert([...pixels].filter((_,i)=>i%4<3).every(value=>value===255),`${code}: the stored texture colour is white`);
 // The UVs sample a graded coverage, so the drawn patch cannot be a hard opaque square.
 const sampled=new Set();
 for(const [u,v] of uvPairs(parsed,primitive.attributes.TEXCOORD_0)) {
  const px=Math.min(width-1,Math.floor(((u%1)+1)%1*width)),py=Math.min(height-1,Math.floor(((v%1)+1)%1*height));
  sampled.add(pixels[(py*width+px)*4+3]);
 }
 assert(sampled.size>2,`${code}: the shadow UVs sample a graded alpha, not one flat value`);
 // Drawn state: the texture alpha as a candidate alpha blend, no depth write, texture retained.
 const material=new THREE.MeshStandardMaterial();
 applyMaterial(material,doc,textures,shadow);
 assert.equal(material.transparent,true,`${code}: the shadow draws as a blend`);
 assert.equal(material.depthWrite,false,`${code}: the shadow must not write depth over the wheels`);
 assert.equal(material.blending,THREE.NormalBlending,`${code}: the texture alpha is the blend factor`);
 assert.equal(material.opacity,1,`${code}: the blend factor is the texture alpha alone`);
 assert.equal(material.alphaTest,0,`${code}: the shadow keeps graded coverage, not a cutout`);
 assert.equal(material.map,textures[image],`${code}: the shadow keeps its own texture`);
 // The presentation control (issue #22) must not disturb that blend: the enhanced path builds a
 // clearcoat-capable material and then glosses textured opaque surfaces, and the shadow is neither an
 // opaque surface nor glossed. Its blend reads the same in both modes; only the scene environment and
 // tone mapping differ under Enhanced.
 const enhanced=createMaterial(doc,textures,shadow,{presentation:'enhanced'});
 assert.equal(enhanced.isMeshPhysicalMaterial,true,`${code}: enhanced builds the physical material`);
 assert.equal(enhanced.transparent,true,`${code}: enhanced keeps the shadow blend`);
 assert.equal(enhanced.depthWrite,false,`${code}: enhanced keeps the shadow out of the depth buffer`);
 assert.equal(enhanced.blending,THREE.NormalBlending,`${code}: enhanced keeps the texture-alpha blend factor`);
 assert.equal(enhanced.opacity,1,`${code}: enhanced keeps the blend factor at the alpha channel alone`);
 assert.equal(enhanced.alphaTest,0,`${code}: enhanced keeps the graded coverage`);
 assert.equal(enhanced.map,textures[image],`${code}: enhanced keeps the shadow texture`);
 const presentation=createPresentation({toneMapping:THREE.NoToneMapping,toneMappingExposure:1},
  {environment:null,environmentIntensity:1},{studio:{setEnabled(){},dispose(){}}});
 const unglossed=[enhanced.roughness,enhanced.metalness,enhanced.clearcoat],standardRoughness=material.roughness;
 presentation.setMode('enhanced');
 presentation.finish(enhanced,source);
 presentation.finish(material,source);
 assert.deepEqual([enhanced.roughness,enhanced.metalness,enhanced.clearcoat],unglossed,
  `${code}: Enhanced does not gloss the under-car shadow`);
 assert.equal(material.roughness,standardRoughness,`${code}: a standard shadow material stays unglossed`);
 enhanced.dispose();presentation.dispose();
 const selection=selectors.underCarShadowPrimitive(doc);
 assert.equal(selection.node.mesh,shadowMesh,`${code}: the inspector finds the shadow record`);
 const record=selection.node.extras.geometryRecord;
 records++;
 assert.equal(selectors.sourceSceneRecords(doc,doc.scenes[0]).has(record),true,
  `${code}: the record layout carries the shadow record`);
 assert.equal(selectors.sourceSceneRecords(doc,doc.scenes[doc.scene]).has(record),false,
  `${code}: the exported default scene does not reference the shadow record`);
 // Rebuilt means the shipped loader produced the overlay, with this car's own geometry and blend.
 const viewer=loadedByTheInspector(code,file,bytes,[{record,node:selection.node.index??0,triangles:doc.accessors[primitive.indices].count/3}]);
 await viewer.load();
 assert(viewer.context.selected,`${code}: the sandbox car loaded (${viewer.elements.error.textContent})`);
 const view='scene'+doc.scene;
 assert.equal(viewer.context.recordSelect.value,view,`${code}: the default view the loader selected`);
 const overlay=viewer.context.loaded.groups.find(group=>group.userData.shadow===true);
 assert(overlay,`${code}: the loader must add the rebuilt under-car shadow overlay`);
 assert.equal(viewer.scene.children.includes(overlay),true,`${code}: the overlay is part of the drawn scene`);
 assert.equal(overlay.userData.record,'under-car shadow');
 assert.equal(overlay.userData.overlay,view,`${code}: the overlay belongs to the selected default view`);
 assert.equal(overlay.visible,true,`${code}: the loader's own showRecord leaves the overlay visible in the default view`);
 assert.equal(overlay.children.length,1,`${code}: exactly the one original record is rebuilt`);
 const rebuilt_mesh=overlay.children[0];
 assert.equal(rebuilt_mesh.geometry.getAttribute('position').count,doc.accessors[primitive.attributes.POSITION].count,
  `${code}: the overlay carries the record's own vertices`);
 assert.equal(rebuilt_mesh.geometry.getIndex().count,doc.accessors[primitive.indices].count,
  `${code}: the overlay carries the record's own triangles`);
 assert.equal(rebuilt_mesh.geometry.getAttribute('uv').count,doc.accessors[primitive.attributes.TEXCOORD_0].count,
  `${code}: the overlay carries the UVs the alpha blend samples`);
 assert.equal(rebuilt_mesh.material.transparent,true,`${code}: the overlay draws as a candidate blend`);
 assert.equal(rebuilt_mesh.material.depthWrite,false,`${code}: the overlay writes no depth`);
 assert.equal(rebuilt_mesh.material.blending,THREE.NormalBlending);
 assert.equal(rebuilt_mesh.material.opacity,1);
 assert.equal(rebuilt_mesh.material.alphaTest,0);
 assert.equal(rebuilt_mesh.material.map,viewer.context.loaded.textures[image],`${code}: the overlay keeps the shadow texture`);
 assert.equal(viewer.show(view).groups.find(group=>group.userData.shadow===true).visible,true,
  `${code}: the overlay shows with the default view`);
 assert.equal(viewer.show(String(record)).groups.find(group=>group.userData.shadow===true).visible,false,
  `${code}: the overlay is not part of another record's view`);
 rebuilt++;
 // Every other material keeps its authored glTF state: textured body and glass/Header parts unchanged.
 for(let index=0;index<doc.materials.length;index++) {
  if(index===shadow)continue;
  const definition=doc.materials[index],factor=definition.pbrMetallicRoughness?.baseColorFactor??[1,1,1,1];
  assert.equal(isRecoveredUnderShadow(definition),false,`${code}: material ${index} is not a shadow surface`);
  const other=new THREE.MeshStandardMaterial();
  applyMaterial(other,doc,textures,index);
  assert.equal(other.transparent,definition.alphaMode==='BLEND',`${code}: material ${index} transparency`);
  assert.equal(other.depthWrite,definition.alphaMode!=='BLEND',`${code}: material ${index} depth write`);
  assert.equal(other.alphaTest,definition.alphaMode==='MASK'?(definition.alphaCutoff??.5):0,`${code}: material ${index} cutout`);
  assert.equal(other.blending,THREE.NormalBlending,`${code}: material ${index} keeps normal blending`);
  assert.equal(other.opacity,factor[3],`${code}: material ${index} keeps its stored alpha`);
  assert.deepEqual(other.color.toArray(),factor.slice(0,3),`${code}: material ${index} keeps its stored colour`);
  assert.equal(other.map,definition.pbrMetallicRoughness?.baseColorTexture===undefined?null:
   textures[doc.textures[definition.pbrMetallicRoughness.baseColorTexture.index].source],`${code}: material ${index} binding`);
  if(definition.name?.startsWith('Header untextured '))glassMaterials++;else otherMaterials++;
 }
 cars++;
}
assert.equal(cars,35);
assert.equal(records,35);
assert.equal(rebuilt,35);
// A material outside the recovered name shape is never treated as the shadow, whatever its texture is.
const sample=parse('GRAN_TORINO.glb').doc;
const renamed={...sample,materials:sample.materials.map(material=>isRecoveredUnderShadow(material)?{...material,name:'BODY_PANEL'}:material)};
assert.equal(selectors.underCarShadowPrimitive(renamed),null,'a renamed shadow material must not be selected');
assert.equal(isRecoveredUnderShadow({name:'UNDER_SHADOW'}),true);
assert.equal(isRecoveredUnderShadow({name:'EX_UNDER_SHADOW2'}),true);
assert.equal(isRecoveredUnderShadow({name:'GT90_UNDER_SHADOW'}),true);
assert.equal(isRecoveredUnderShadow({name:'SHADOWLESS_BODY'}),false);
console.log(`PASS test_under_car_shadow: ${cars} cars, ${records} shadow records outside the exported default scene, `
 +`${rebuilt} rebuilt at load, ${otherMaterials} other textured/detail materials and ${glassMaterials} Header-colour parts unchanged, `
 +'candidate alpha blend kept in both presentation modes');
