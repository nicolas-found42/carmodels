import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from '../dealership/vendor/three.module.js';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {materialOptions} from '../dealership/material-options.mjs';
import {defaultGeometryValue,geometryOptions,sceneHasGeometry,sceneLabel} from '../dealership/scene-options.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const corpus=path.join(root,'dealership/public/ford-racing-2');
let cars=0,emptyChoices=0,materialBindings=0;
for(const file of fs.readdirSync(corpus).filter(f=>f.endsWith('.glb'))) {
 const bytes=fs.readFileSync(path.join(corpus,file));
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 // Source texture slots and GLB material slots are separate tables: header colours
 // inserted into the material table must never shift body primitives onto glass.
 for(const mesh of doc.meshes)for(const primitive of mesh.primitives) {
  const sourceTexture=primitive.extras.third;
  const material=doc.materials[primitive.material];
  if(sourceTexture===65535) {
   assert.equal(material.pbrMetallicRoughness.baseColorTexture,undefined,file+' untextured header acquired a texture');
  } else {
   assert.equal(material.pbrMetallicRoughness.baseColorTexture?.index,sourceTexture,file+' body primitive points at the wrong material');
   assert.notEqual(material.alphaMode,'BLEND',file+' body primitive points at glass');
  }
 }
 const images=doc.images.map(()=>new THREE.Texture());
 for(const mesh of doc.meshes)for(const primitive of mesh.primitives) {
  const settings=materialOptions(doc,primitive.material,images);
  const sourceTexture=primitive.extras.third;
  assert.equal(settings.map,sourceTexture===65535?null:images[doc.textures[sourceTexture].source],file+' viewer used a material index as an image index');
  materialBindings++;
 }
 const options=geometryOptions(doc,[]);
 for(const [i,scene] of doc.scenes.entries()) {
  if(i===0)continue;
  const choice=options.find(o=>o.value==='scene'+i);
  if(scene.name.toLowerCase().includes('tree 4')) {
   assert.equal(sceneHasGeometry(doc,scene),false,file+' tree 4 unexpectedly has geometry');
   assert.equal(choice.disabled,true,file+' offers empty tree 4 as renderable');
   assert.match(choice.textContent,/4.*no geometry/);
   emptyChoices++;
  }
 }
 const normal=defaultGeometryValue(doc,options);
 assert(options.some(o=>o.value===normal&&!o.disabled),file+' has no usable default');
 const empty=doc.scenes.findIndex(s=>s.name==='Candidate tree 4 — all states');
 assert.equal(defaultGeometryValue({...doc,scene:empty},options),options.find(o=>!o.disabled).value);
 cars++;
}
assert.equal(cars,35);
assert.equal(emptyChoices,105);
// A parent can be empty while its descendant holds the drawable mesh.
const fixture={scene:1,nodes:[{children:[1]},{mesh:0},{}],meshes:[{primitives:[{attributes:{POSITION:0},indices:1}]}],accessors:[{count:3},{count:3}],scenes:[{nodes:[]},{name:'Candidate tree 0 — all states',nodes:[0]},{name:'Candidate tree 4 — all states',nodes:[2]}]};
assert.equal(sceneHasGeometry(fixture,fixture.scenes[1]),true);
fixture.accessors[1].count=0;
assert.equal(sceneHasGeometry(fixture,fixture.scenes[1]),false);
assert.equal(defaultGeometryValue(fixture,geometryOptions(fixture,[])),'');
const records=geometryOptions(fixture,[{record:7,triangles:1}]);
assert.equal(defaultGeometryValue(fixture,records),'7');
assert.match(sceneLabel('Candidate tree 2 — all states'),/^Candidate 2/);
// Exercise the actual viewer callback: an empty selection must not reframe the camera.
const emptyGroup=new THREE.Group();
emptyGroup.userData={record:'scene5',label:'Candidate tree 4 — all states'};
const status={textContent:''};
const camera=new THREE.PerspectiveCamera();
const initial=camera.position.clone();
const context={loaded:{groups:[emptyGroup]},recordSelect:{value:'scene5'},selected:{code:'GRAN_TORINO'},
 status,THREE,camera,sceneLabel,controls:{update(){throw Error('empty scene reached camera controls');}},
 updateMaterials(){throw Error('empty scene reached material update');}};
const html=fs.readFileSync(path.join(root,'dealership/recovered.html'),'utf8');
// The shared catalog must point at the same verified game exports after the move.
const catalog=JSON.parse(fs.readFileSync(path.join(root,'dealership/public/models.json'),'utf8'));
assert.equal(catalog.cars.length,35);
assert.equal(new Set(catalog.cars.map(c=>c.id)).size,35);
for(const entry of catalog.cars) {
 assert.equal(entry.game,'ford-racing-2');
 assert.equal(entry.id,entry.game+'/'+entry.code);
 assert(fs.existsSync(path.join(root,'dealership/public',entry.file)));
}
// Exercise the inspector's real loader with the same car code in two games.
const loadCarSource=html.match(/async function loadCar\(\)[\s\S]*?\n}\n/)[0];
const requested=[];
const error={textContent:''};
const loaderContext={requestId:0,index:{cars:[
 {id:'ford-racing-2/SHARED',code:'SHARED',file:'ford-racing-2/car.glb'},
 {id:'another game/SHARED',code:'SHARED',file:'another game/car.glb'}]},
 carSelect:{value:''},status:{textContent:''},document:{querySelector(){return error;}},
 fetch:async url=>{requested.push(url);return {ok:false};}};
for(const identifier of ['ford-racing-2/SHARED','another game/SHARED']) {
 loaderContext.carSelect.value=identifier;
 await vm.runInNewContext(loadCarSource+';loadCar();',loaderContext);
}
assert.deepEqual(requested,['public/ford-racing-2/car.glb','public/another%20game/car.glb']);
const showRecord=html.match(/function showRecord\(\).*\n/)[0];
vm.runInNewContext(showRecord+';showRecord();',context);
assert.match(status.textContent,/no drawable geometry/);
assert(camera.position.equals(initial));
// Deliberately permute all three index tables. A texture reference must resolve
// through doc.textures, and untextured glass must keep its stored colour and alpha.
const images=[new THREE.Texture(),new THREE.Texture()];
const materialDoc={images:[{},{}],textures:[{source:1},{source:0}],materials:[
 {name:'Header untextured 0x59000000',alphaMode:'BLEND',pbrMetallicRoughness:{baseColorFactor:[0,0,0,89/128]}},
 {pbrMetallicRoughness:{baseColorFactor:[.5,.5,.5,1]}},
 {pbrMetallicRoughness:{baseColorTexture:{index:0},baseColorFactor:[.2,.4,.6,1]}}
]};
const glassOptions=materialOptions(materialDoc,0,images);
assert.equal(glassOptions.map,null);
assert.equal(glassOptions.transparent,true);
assert.equal(glassOptions.depthWrite,false);
assert.equal(glassOptions.opacity,89/128);
assert.deepEqual(glassOptions.color.toArray(),[0,0,0]);
const paintOptions=materialOptions(materialDoc,2,images);
assert.equal(paintOptions.map,images[1]);
assert.equal(paintOptions.transparent,false);
assert.equal(paintOptions.depthWrite,true);
assert.deepEqual(paintOptions.color.toArray(),[.2,.4,.6]);
// Exercise the real UI callback, including switching back to a blended base
// material after a variant selected an opaque textured material.
const material=new THREE.MeshStandardMaterial(glassOptions);
const mesh={material,userData:{baseMaterial:0,variantMappings:[{material:2,variants:[0]}]}};
const inputs={variant:{value:'0'},textures:{checked:true},wire:{checked:false},flip:{checked:false}};
let pendingUpdates=0;
const pendingTexture={set needsUpdate(value){if(value)pendingUpdates++;}};
const updateContext={loaded:{doc:materialDoc,meshes:[mesh],textures:images.concat(pendingTexture)},
 document:{querySelector(selector){return inputs[selector.slice(1)];}},materialOptions};
const updateMaterials=html.match(/function updateMaterials\(\).*\n/)[0];
vm.runInNewContext(updateMaterials+';updateMaterials();',updateContext);
assert.equal(material.map,images[1]);
assert.equal(material.transparent,false);
assert.equal(material.opacity,1);
assert.equal(material.depthWrite,true);
inputs.textures.checked=false;
vm.runInNewContext(updateMaterials+';updateMaterials();',updateContext);
assert.equal(material.map,null);
inputs.variant.value='';inputs.textures.checked=true;
vm.runInNewContext(updateMaterials+';updateMaterials();',updateContext);
assert.equal(material.map,null);
assert.equal(material.transparent,true);
assert.equal(material.opacity,89/128);
assert.equal(material.depthWrite,false);
assert.equal(pendingUpdates,0,'pending images were uploaded before loading');
assert.match(html,/glass[^<]*candidate/i,'glass/header-colour mapping remains labelled as a candidate');
console.log(`PASS test_viewer_scenes: ${cars} cars, ${materialBindings} material bindings, ${emptyChoices} disabled empty tree-4 choices, variant switching, pending textures and empty-selection camera guard`);
