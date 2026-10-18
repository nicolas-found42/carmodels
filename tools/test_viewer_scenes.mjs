import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from '../dealership/vendor/three.module.js';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {defaultGeometryValue,geometryOptions,sceneHasGeometry,sceneLabel} from '../dealership/scene-options.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const corpus=path.join(root,'dealership/public/ford-racing-2');
let cars=0,emptyChoices=0,materialBindings=0;
for(const file of fs.readdirSync(corpus).filter(f=>f.endsWith('.glb'))) {
 const bytes=fs.readFileSync(path.join(corpus,file));
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 for(const mesh of doc.meshes)for(const primitive of mesh.primitives) {
  const sourceTexture=primitive.extras.third;
  const material=doc.materials[primitive.material];
  assert.equal(material.pbrMetallicRoughness.baseColorTexture?.index,sourceTexture===65535?undefined:sourceTexture,file+' primitive points at the wrong material');
  if(sourceTexture!==65535)assert.notEqual(material.alphaMode,'BLEND',file+' body points at glass');
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
// GT index records describe LOD provenance rather than separately selectable mesh records.
const generic={...fixture,scenes:[{name:'LOD0',nodes:[0]}]};generic.accessors[1].count=3;
const gtOptions=geometryOptions(generic,[{lod:0,triangles:1}]);
assert.deepEqual(gtOptions.map(o=>o.value),['scene0']);
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
const showRecord=html.match(/function showRecord\(\).*\n/)[0];
const underCarShadowNote=html.match(/function underCarShadowNote\(shadow,value,game\).*\n/)[0];
const shadowNote=vm.runInNewContext(underCarShadowNote+';underCarShadowNote;',{});
vm.runInNewContext(showRecord+';showRecord();',context);
assert.match(status.textContent,/no drawable geometry/);
assert(camera.position.equals(initial));
// Exercise the actual status callback with a visible Header-colour part.
const glassGroup=new THREE.Group();
glassGroup.userData={record:'scene6',label:'Tree 0 — Low-speed wheels, lights off'};
const glass=new THREE.Mesh(new THREE.BoxGeometry(),new THREE.MeshStandardMaterial());
glass.userData.headerColour=true;
glassGroup.add(glass);
const visibleContext={...context,loaded:{groups:[glassGroup]},recordSelect:{value:'scene6'},
 selected:{code:'GRAN_TORINO',records:[]},controls:{target:new THREE.Vector3(),update(){}},updateMaterials(){}};
const shownMeshes=html.match(/function shownMeshes\(root\).*\n/)[0];
vm.runInNewContext(underCarShadowNote+shownMeshes+showRecord+';showRecord();',visibleContext);
assert.match(status.textContent,/glass\/Header-colour parts \(1 here\)/);
assert.match(status.textContent,/candidate, not proven shading/);
assert.doesNotMatch(status.textContent,/under-car shadow/);
const framed=visibleContext.camera.position.clone();
// The rebuilt under-car shadow joins the selected source tree without reframing the camera or
// replacing the existing labels. It sits first here so a missing overlay guard would be visible.
const shadowOverlay=new THREE.Group();
shadowOverlay.userData={shadow:true,record:'under-car shadow',overlay:'scene6'};
shadowOverlay.add(new THREE.Mesh(new THREE.BoxGeometry(.2,.2,.2),new THREE.MeshStandardMaterial()));
const shadowContext={...visibleContext,loaded:{groups:[shadowOverlay,glassGroup],shadow:{material:'UNDER_SHADOW',record:41,triangles:8,referencedByDefaultScene:false,view:'scene6'}}};
vm.runInNewContext(underCarShadowNote+shownMeshes+showRecord+';showRecord();',shadowContext);
assert.equal(shadowOverlay.visible,true);
assert(shadowContext.camera.position.equals(framed),'the shadow overlay must not frame the camera');
assert.match(status.textContent,/under-car shadow record 41 \(UNDER_SHADOW, 8 triangles\): the source default scene does not reference it \(it sits in the record-layout scene\), so this view rebuilds that original record; its blend state is not captured, so the texture-alpha blend is a candidate \(the record's stored colour is white\)/);
assert.match(status.textContent,/glass\/Header-colour parts \(1 here\)/);
// A Ford Racing 2 car without the record, and a view other than the default one, say so.
assert.match(shadowNote(null,'scene6','ford-racing-2'),/no under-car shadow record in this car/);
assert.equal(shadowNote(null,'scene6','redline'),'');
assert.match(shadowNote({material:'UNDER_SHADOW',record:41,triangles:8,referencedByDefaultScene:false,view:'scene6'},'41','ford-racing-2'),/not in this view; no exported tree references it/);
assert.match(shadowNote({material:'UNDER_SHADOW',record:41,triangles:8,referencedByDefaultScene:true,view:'scene6'},'scene6','ford-racing-2'),/the source default scene draws it here/);
console.log(`PASS test_viewer_scenes: ${cars} cars, ${materialBindings} material bindings, ${emptyChoices} disabled empty tree-4 choices, child geometry, default fallback, empty-selection camera guard, visible header-colour honesty label and under-car shadow candidate label`);
