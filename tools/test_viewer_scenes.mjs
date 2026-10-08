import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from '../viewer/vendor/three.module.js';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {defaultGeometryValue,geometryOptions,sceneHasGeometry,sceneLabel} from '../viewer/scene-options.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const corpus=path.join(root,'viewer/public/recovered');
let cars=0,emptyChoices=0;
for(const file of fs.readdirSync(corpus).filter(f=>f.endsWith('.glb'))) {
 const bytes=fs.readFileSync(path.join(corpus,file));
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
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
const html=fs.readFileSync(path.join(root,'viewer/recovered.html'),'utf8');
const showRecord=html.match(/function showRecord\(\).*\n/)[0];
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
vm.runInNewContext(shownMeshes+showRecord+';showRecord();',visibleContext);
assert.match(status.textContent,/glass\/Header-colour parts \(1 here\)/);
assert.match(status.textContent,/candidate, not proven shading/);
console.log(`PASS test_viewer_scenes: ${cars} cars, ${emptyChoices} disabled empty tree-4 choices, child geometry, default fallback, empty-selection camera guard and visible header-colour honesty label`);
