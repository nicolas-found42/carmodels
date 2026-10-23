import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../dealership/vendor/three.module.js';

// Load the real UI against the repository's offline Three runtime.
const uiURL=new URL('../dealership/mc3-record-ui.mjs',import.meta.url);
const source=fs.readFileSync(uiURL,'utf8')
 .replace("from 'three'","from '"+new URL('../dealership/vendor/three.module.js',import.meta.url).href+"'")
 .replace("from './mc3-record-inspection.mjs'","from '"+new URL('../dealership/mc3-record-inspection.mjs',import.meta.url).href+"'");
const {createMC3RecordInspector}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));

class Element {
 constructor(tag,ownerDocument){this.tagName=tag;this.ownerDocument=ownerDocument;this.children=[];this.dataset={};this.style={};this.handlers={};this.value='';this.hidden=false;}
 append(...children){this.children.push(...children);}
 setAttribute(name,value){this[name]=value;}
 addEventListener(name,handler){(this.handlers[name]??=[]).push(handler);}
 replaceChildren(...children){this.children=children;this.value=children[0]?.value??'';}
 dispatch(name,properties={}){const event={preventDefault(){this.defaultPrevented=true;},...properties};for(const handler of this.handlers[name]??[])handler(event);return event;}
 focus(){this.ownerDocument.activeElement=this;}
 getBoundingClientRect(){return {left:0,top:0,width:200,height:200};}
}
const document={createElement(tag){return new Element(tag,this);}},container=document.createElement('section'),canvas=document.createElement('canvas');
const camera=new THREE.PerspectiveCamera(50,1,.1,100);camera.position.z=5;camera.lookAt(0,0,0);camera.updateProjectionMatrix();
let changes=0;
const inspector=createMC3RecordInspector({container,canvas,camera,onChange(){changes++;}});
const find=(node,predicate)=>predicate(node)?node:node.children.map(child=>find(child,predicate)).find(Boolean);
const list=find(container,node=>node.id==='source-record-list');
const detail=field=>find(container,node=>node.dataset.field===field).textContent;
const body='vroot_shell_lod_HLOD_HLOD.mesh',front='vroot_Suspension_Arm_Front_L_Front_L.mesh';
const records=[{identity:body,nodeIndex:6,sourceOccurrence:'native-body',sourceHash:'body-sha',parentIdentity:'None (native root)',localMatrix:[1,0,0,0],worldMatrix:[1,0,0,0]},
 {identity:front,nodeIndex:0,sourceOccurrence:'native-front',sourceHash:'front-sha',parentIdentity:'Suspension',localMatrix:null,worldMatrix:null}];
const material=new THREE.MeshBasicMaterial({color:0xabcdef});
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute([-1,-1,0,1,-1,0,0,1,0],3));
let sourceDisposals=0;geometry.addEventListener('dispose',()=>sourceDisposals++);material.addEventListener('dispose',()=>sourceDisposals++);
function meshGroup(index,z){const group=new THREE.Group();group.userData.sourceNodeIndex=index;const mesh=new THREE.Mesh(geometry,material);mesh.position.z=z;group.add(mesh);return {group,mesh};}
const back=meshGroup(6,0),near=meshGroup(0,1),hidden=new THREE.Mesh(geometry,material);hidden.visible=false;back.group.add(hidden);
const groups=[back.group,near.group];
const overlays=mesh=>mesh.children.filter(child=>child.userData.inspectorHighlight);
function change(identity){list.value=identity;list.dispatch('change');}
function click(x=100,y=100){canvas.dispatch('pointerdown',{button:0,clientX:x,clientY:y});canvas.dispatch('pointerup',{button:0,clientX:x,clientY:y});}
inspector.bind(records,groups);
assert.equal(container.hidden,false);assert.equal(list.children.length,2);
change(body);
assert.equal(inspector.snapshot().selected,body);assert.equal(list.value,body);assert.equal(detail('identity'),body);
assert.equal(detail('sourceOccurrence'),'native-body');assert.equal(detail('sourceHash'),'body-sha');
assert.equal(overlays(back.mesh).length,1);assert.equal(overlays(near.mesh).length,0);assert.equal(overlays(hidden).length,0);
assert.equal(inspector.snapshot().records.find(record=>record.identity===body).highlightedMeshes,1);

let overlayDisposals=0;
const oldOverlay=overlays(back.mesh)[0];oldOverlay.geometry.addEventListener('dispose',()=>overlayDisposals++);oldOverlay.material.addEventListener('dispose',()=>overlayDisposals++);
list.focus();assert.equal(document.activeElement,list);
assert.equal(list.dispatch('keydown',{key:'ArrowDown'}).defaultPrevented,true);
assert.equal(list.value,front);assert.equal(inspector.snapshot().selected,front);assert.equal(detail('localMatrix'),'Unknown');
assert.equal(overlays(back.mesh).length,0);assert.equal(overlays(near.mesh).length,1);assert.equal(overlayDisposals,2);assert.equal(oldOverlay.parent,null);
list.dispatch('keydown',{key:'ArrowUp'});assert.equal(inspector.snapshot().selected,body);
list.value=front;list.dispatch('keydown',{key:'Enter'});assert.equal(inspector.snapshot().selected,front);

near.group.visible=false;change(front);
assert.equal(near.group.visible,false);assert.equal(back.group.visible,true);assert.equal(hidden.visible,false);
assert.equal(inspector.snapshot().records.find(record=>record.identity===front).highlightedMeshes,0);
assert.equal(overlays(near.mesh).length,0);assert.equal(overlays(back.mesh).length,0);
click();assert.equal(inspector.snapshot().selected,body,'actual raycaster ignores hidden nearer geometry');
near.group.visible=true;change(body);click();
assert.equal(inspector.snapshot().selected,front,'actual raycaster selects nearest visible triangle');
assert.equal(list.value,front);assert.equal(detail('identity'),front);assert.equal(overlays(near.mesh).length,1);
change(body);canvas.dispatch('pointerdown',{button:0,clientX:100,clientY:100});canvas.dispatch('pointerup',{button:0,clientX:120,clientY:100});
assert.equal(inspector.snapshot().selected,body,'orbit drag does not select');
click(1,1);assert.equal(inspector.snapshot().selected,body,'empty ray preserves selection');

const lastOverlay=overlays(back.mesh)[0];lastOverlay.geometry.addEventListener('dispose',()=>overlayDisposals++);lastOverlay.material.addEventListener('dispose',()=>overlayDisposals++);
const previousDisposals=overlayDisposals;inspector.clear();
assert.equal(overlayDisposals,previousDisposals+2);assert.equal(lastOverlay.parent,null);
assert.equal(container.hidden,true);assert.equal(inspector.snapshot().selected,null);assert.equal(inspector.snapshot().records.length,0);
assert.equal(overlays(back.mesh).length,0);assert.equal(overlays(near.mesh).length,0);assert.equal(sourceDisposals,0);
assert.equal(back.mesh.geometry,geometry);assert.equal(near.mesh.geometry,geometry);assert.equal(back.mesh.material,material);assert.equal(near.mesh.material,material);
assert.equal(geometry.getAttribute('position').count,3);assert.equal(hidden.visible,false);assert.ok(changes>=8);
console.log('PASS real MC3 inspector list/detail/highlight, focus+Arrow/Enter, hidden selection, actual Three raycast, drag guard, Unknown and overlay disposal preserving source geometry/materials.');
