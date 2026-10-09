import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from '../dealership/vendor/three.module.js';
import {readGLB} from '../dealership/model-load.mjs';
import {createMaterial} from '../dealership/materials.mjs';
import {geometryOptions,defaultGeometryValue} from '../dealership/scene-options.mjs';

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
 readGLB,createMaterial,geometryOptions,defaultGeometryValue,showRecord(){status.textContent=context.selected.code;},
 async fetchModel(url,signal){
  requests.push(url);
  if(mode==='failure')throw Error('Geometry file unavailable (HTTP 404)');
  if(mode==='pending')await new Promise((resolve,reject)=>{
   pending.push(resolve);signal.addEventListener('abort',()=>reject(new DOMException('Abort','AbortError')),{once:true});
  });
  const raw=fs.readFileSync(new URL(url.split('/').at(-1),corpus));
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
console.log('PASS test_viewer_loading: actual callback, success, 404 clears geometry/download, retry, pending controls, obsolete selection cancellation, resource cleanup');
