import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from '../dealership/vendor/three.module.js';
import {readGLB} from '../dealership/model-load.mjs';
import {createMaterial} from '../dealership/materials.mjs';
import {geometryOptions,defaultGeometryValue} from '../dealership/scene-options.mjs';
import {isNativePackage} from '../dealership/dealership.mjs';

const corpus=new URL('../dealership/public/ford-racing-2/',import.meta.url);
const index=JSON.parse(fs.readFileSync(new URL('../dealership/public/models.json',import.meta.url)));
const html=fs.readFileSync(new URL('../dealership/recovered.html',import.meta.url),'utf8');
const callback=html.slice(html.indexOf('function disposeState('),html.indexOf('function updateMaterials('));
const elements=Object.fromEntries(['car','record','variant','textures','sharp','wire','flip','download','retry','error'].map(id=>[id,{
 value:'',disabled:false,hidden:false,options:[],textContent:'',
 removeAttribute(name){delete this[name];},
 replaceChildren(...options){this.options=options;},append(option){this.options.push(option);},
}]));
const stage={setAttribute(name,value){this[name]=value;}};
const status={textContent:''};
const scene=new THREE.Scene();
const urls=new Set();
let mode='success',pending=[],disposals=0;const requests=[];
const context={THREE:{...THREE,TextureLoader:class {
 async loadAsync(){const t=new THREE.Texture();t.addEventListener('dispose',()=>disposals++);return t;}
}},document:{querySelector(selector){return elements[selector.slice(1)];},createElement(){return {};}},
 carSelect:elements.car,recordSelect:elements.record,stage,status,scene,index,
 loaded:null,selected:null,requestId:0,pendingRequest:null,AbortController,Blob,
 URL:{createObjectURL(){const id='blob:'+urls.size;urls.add(id);return id;},revokeObjectURL(id){urls.delete(id);}},
 readGLB,createMaterial,geometryOptions,defaultGeometryValue,isNativePackage,showRecord(){status.textContent=context.selected.code;},updateDescription(){},
 async fetchModel(url,signal){
  requests.push(url);
  if(mode==='failure')throw Error('Geometry file unavailable (HTTP 404)');
  if(mode==='pending')await new Promise((resolve,reject)=>{
   pending.push(resolve);signal.addEventListener('abort',()=>reject(new DOMException('Abort','AbortError')),{once:true});
  });
  const raw=url.includes('generic')?genericGLB:fs.readFileSync(new URL(url.split('/').at(-1),corpus));
  return raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength);
 },
};
vm.createContext(context);vm.runInContext(callback,context);
elements.car.value='ford-racing-2/GRAN_TORINO';await context.loadCar();
assert.equal(context.selected.code,'GRAN_TORINO');
assert.match(elements.download.href,/GRAN_TORINO/);
assert.equal(elements.record.disabled,false);
mode='failure';elements.car.value='ford-racing-2/COBRA';await context.loadCar();
assert.equal(context.loaded,null);
assert.equal(scene.children.length,0);
assert.equal(urls.size,0);
assert.equal(elements.download.href,undefined);
assert.equal(elements.record.disabled,true);
assert.equal(elements.retry.hidden,false);
assert.match(elements.error.textContent,/COBRA.*HTTP 404/);
const failureStatus=status.textContent;context.showRecord=()=>{};
assert.equal(status.textContent,failureStatus);
mode='success';await context.loadCar();
assert.equal(context.selected.code,'COBRA');
assert.equal(elements.retry.hidden,true);
assert.match(elements.download.href,/COBRA/);
mode='pending';elements.car.value='ford-racing-2/FOCUS_WRC';const stale=context.loadCar();
assert.equal(elements.download.href,undefined);
assert.equal(elements.record.disabled,true);
assert.equal(stage['aria-busy'],'true');
mode='success';elements.car.value='ford-racing-2/F350';await context.loadCar();await stale;
assert.equal(context.selected.code,'F350');
assert.match(elements.download.href,/F350/);
assert.equal(elements.error.textContent,'');
assert.equal(stage['aria-busy'],'false');
assert(disposals>0);
index.cars.push({...index.cars.find(c=>c.code==='GRAN_TORINO'),id:'another game/GRAN_TORINO',game:'another game',file:'another game/GRAN_TORINO.glb'});
elements.car.value='another game/GRAN_TORINO';await context.loadCar();
assert.equal(context.selected.id,'another game/GRAN_TORINO');
assert.equal(requests.at(-1),'public/another%20game/GRAN_TORINO.glb');
assert.equal(elements.download.href,'public/another%20game/GRAN_TORINO.glb');
context.dispose();assert.equal(urls.size,0);assert.equal(scene.children.length,0);
// A regular glTF scene has no Ford Racing record extras. Load its default scene,
// 16-bit indices, absent images/normals, and complete node transforms.
const geometry=Buffer.alloc(80);
const coordinates=[0,0,0,1,0,0,0,1,0];coordinates.forEach((n,i)=>geometry.writeFloatLE(n,i*4));
[0,1,2].forEach((n,i)=>geometry.writeUInt16LE(n,36+i*2));
[1,0,0,0,1,0,0,0,1].forEach((n,i)=>geometry.writeFloatLE(n,44+i*4));
const documentGLB={asset:{version:'2.0'},scene:0,scenes:[{name:'Gran Turismo LOD 0',nodes:[0]}],
 nodes:[{translation:[2,0,0],rotation:[0,0,0,1],scale:[2,2,2],children:[1]},
 {mesh:0,matrix:[1,0,0,0,0,1,0,0,0,0,1,0,0,3,0,1]}],
 meshes:[{primitives:[{attributes:{POSITION:0,COLOR_0:2},indices:1,material:0}]}],
 materials:[{pbrMetallicRoughness:{baseColorFactor:[1,0,0,1]}}],buffers:[{byteLength:geometry.length}],
 bufferViews:[{buffer:0,byteOffset:0,byteLength:36},{buffer:0,byteOffset:36,byteLength:6},{buffer:0,byteOffset:44,byteLength:36}],
 accessors:[{bufferView:0,componentType:5126,count:3,type:'VEC3'},{bufferView:1,componentType:5123,count:3,type:'SCALAR'},{bufferView:2,componentType:5126,count:3,type:'VEC3'}]};
let json=Buffer.from(JSON.stringify(documentGLB));json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
const genericGLB=Buffer.alloc(28+json.length+geometry.length);genericGLB.writeUInt32LE(0x46546c67,0);genericGLB.writeUInt32LE(2,4);genericGLB.writeUInt32LE(genericGLB.length,8);
genericGLB.writeUInt32LE(json.length,12);genericGLB.writeUInt32LE(0x4e4f534a,16);json.copy(genericGLB,20);
genericGLB.writeUInt32LE(geometry.length,20+json.length);genericGLB.writeUInt32LE(0x004e4942,24+json.length);geometry.copy(genericGLB,28+json.length);
index.cars.push({id:'gran-turismo/simulation/synthetic/night',game:'gran-turismo',code:'simulation/_0logn/night',file:'gran-turismo/generic.glb',records:[]});
elements.car.value='gran-turismo/simulation/synthetic/night';await context.loadCar();
assert.equal(context.selected.game,'gran-turismo');assert.equal(elements.record.value,'scene0');
assert.equal(context.loaded.groups.length,1);assert.equal(context.loaded.meshes.length,1);
const mesh=context.loaded.meshes[0];assert(mesh.geometry.index.array.constructor.name==='Uint16Array');assert(mesh.geometry.attributes.normal);assert(mesh.geometry.attributes.color);assert.equal(mesh.material.vertexColors,true);
assert.deepEqual(Array.from(mesh.geometry.attributes.color.array),[1,0,0,0,1,0,0,0,1]);
context.loaded.groups[0].visible=true;const bounds=new THREE.Box3().setFromObject(context.loaded.groups[0]);
assert.deepEqual(bounds.min.toArray(),[2,6,0]);assert.deepEqual(bounds.max.toArray(),[4,8,0]);
assert.equal(elements.download.href,'public/gran-turismo/generic.glb');
index.cars.push({id:'midnight-club-3-remix/native-fixture',game:'midnight-club-3-remix',code:'vp_fixture',
  asset_kind:'native-package',file:'midnight-club-3-remix/native/vp_fixture.dat',native_members:3,records:[]});
const beforeNativeRequests=requests.length;
elements.car.value='midnight-club-3-remix/native-fixture';await context.loadCar();
assert.equal(requests.length,beforeNativeRequests,'native selection must not fetch/parse a DAT as GLB');
assert.equal(context.loaded,null);assert.equal(scene.children.length,0);assert.equal(urls.size,0);
assert.equal(elements.record.disabled,true);assert.equal(elements.retry.hidden,true);
assert.match(elements.download.href,/vp_fixture\.dat$/);assert.match(status.textContent,/3D preview unavailable/);
assert.equal(elements.download.download,'vp_fixture.dat');
elements.car.value='ford-racing-2/COBRA';await context.loadCar();
assert.equal(context.selected.code,'COBRA');assert.equal(elements.download.download,'COBRA.glb');
context.dispose();assert.equal(scene.children.length,0);assert.equal(urls.size,0);
// Exercise actual library filters and semantic response handling independently of WebGL.
const control=(value='')=>({value,options:[],events:{},disabled:false,textContent:'',
 addEventListener(event,fn){this.events[event]=fn;},replaceChildren(...options){this.options=options;},append(option){this.options.push(option);},removeAttribute(name){delete this[name];}});
const gameSelect=control('all');gameSelect.options=[{value:'all'},{value:'ford-racing-2'},{value:'gran-turismo'}];
const sourceVariant=control('');sourceVariant.options=[{value:''},{value:'night'},{value:'day'},{value:'arcade'}];
const search=control(''),filterStatus=control(),carSelect=control(),interpret=control();
// Native select values cannot refer to options which have not yet been added.
Object.defineProperty(carSelect,'value',{get(){return this.options.some(o=>o.value===this.selectedValue)?this.selectedValue:this.options[0]?.value||'';},set(value){this.selectedValue=this.options.some(o=>o.value===value)?value:'';}});
const filterElements={interpret,download:control(),retry:control()};let modelLoads=0,disposed=0,responseJSON={status:'review',message:'Choose filters directly.'};
let delayedResolve=null;
const filterContext={gameSelect,sourceVariant,search,filterStatus,carSelect,index:{cars:[
 {id:'ford-racing-2/COBRA',game:'ford-racing-2',code:'COBRA'},
 {id:'gran-turismo/simulation/synthetic/night',game:'gran-turismo',code:'simulation/_0logn/night',source_variant:'night'},
 {id:'gran-turismo/simulation/synthetic/day',game:'gran-turismo',code:'simulation/_0logn/day',source_variant:'day'},
 {id:'gran-turismo/simulation/other/day',game:'gran-turismo',code:'simulation/other/day',source_variant:'day'}]},
 AbortController,setTimeout,clearTimeout,URLSearchParams,location:{search:''},gameNames:{'ford-racing-2':'Ford Racing 2','gran-turismo':'Gran Turismo'},filterRevision:0,requestId:0,pendingRequest:null,
 status:control(),dispose(){disposed++;},setLoading(){},loadCar(){modelLoads++;},
 document:{querySelector(selector){return filterElements[selector.slice(1)];},createElement(){return {};}},
 fetch:async()=>({ok:true,json:async()=>delayedResolve?new Promise(resolve=>{delayedResolve=resolve;}):responseJSON})};
vm.createContext(filterContext);const filters=html.slice(html.indexOf('function filterCars('),html.indexOf("carSelect.addEventListener('change',loadCar)"));vm.runInContext(filters,filterContext);
filterContext.filterCars();assert.equal(carSelect.options.length,4);assert.equal(modelLoads,1);
gameSelect.value='gran-turismo';sourceVariant.value='night';filterContext.filterCars();assert.equal(carSelect.options.length,1);assert.match(carSelect.value,/night$/);
search.value='missing';filterContext.filterCars();assert.equal(carSelect.options.length,0);assert.equal(disposed,1);assert.match(filterContext.status.textContent,/No source entries/);
search.value='night cars from Gran Turismo';await interpret.events.click();assert.equal(search.value,'night cars from Gran Turismo');assert.equal(filterStatus.textContent,'Choose filters directly.');
responseJSON={status:'ok',filters:{game:'gran-turismo',variant:'day'}};await interpret.events.click();assert.equal(search.value,'');assert.equal(carSelect.options.length,2);assert.match(carSelect.value,/day$/);
responseJSON={status:'ok',filters:{game:'invented-game',variant:null}};await interpret.events.click();assert.match(filterStatus.textContent,/unknown filter/);assert.equal(gameSelect.value,'gran-turismo');
// Changing an exact filter while semantic inference is pending invalidates that result.
delayedResolve=true;search.value='night cars';const staleFilter=interpret.events.click();await new Promise(resolve=>setImmediate(resolve));
gameSelect.value='ford-racing-2';sourceVariant.value='';search.value='';filterContext.filterCars();delayedResolve({status:'ok',filters:{game:'gran-turismo',variant:'night'}});await staleFilter;
assert.equal(gameSelect.value,'ford-racing-2');assert.equal(carSelect.value,'ford-racing-2/COBRA');assert.equal(interpret.disabled,false);
// A stalled semantic endpoint is aborted and the button becomes usable again.
let timeoutCallback,cleared=false;
filterContext.setTimeout=(callback,ms)=>{assert.equal(ms,20000);timeoutCallback=callback;return 7;};
filterContext.clearTimeout=id=>{assert.equal(id,7);cleared=true;};
filterContext.fetch=async(url,options)=>new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(new Error('Request timed out')),{once:true});});
const stalled=interpret.events.click();timeoutCallback();await stalled;
assert.equal(interpret.disabled,false);assert(cleared);assert.match(filterStatus.textContent,/timed out/);
// Run the actual startup sequence with an empty native select and a non-first ID.
const startup=html.slice(html.indexOf('const parameters='),html.indexOf('new ResizeObserver('));
carSelect.replaceChildren();filterContext.location.search='?game=gran-turismo&variant=day&car=gran-turismo%2Fsimulation%2Fother%2Fday';
vm.runInContext(startup,filterContext);assert.equal(carSelect.value,'gran-turismo/simulation/other/day');assert.equal(gameSelect.value,'gran-turismo');assert.equal(sourceVariant.value,'day');
filterContext.location.search='?game=gran-turismo&variant=day&car=missing';
vm.runInContext('{'+startup+'}',filterContext);assert.equal(carSelect.value,'gran-turismo/simulation/synthetic/day');
console.log('PASS test_viewer_loading: actual callback, success, 404 clears geometry/download, retry, pending controls, obsolete selection cancellation, resource cleanup');
