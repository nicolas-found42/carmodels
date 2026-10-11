import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isNativePackage, dealershipDownload, loadCar, validateCars} from '../dealership/dealership.mjs';

const native={code:'MC3_VP_TEST_04',name:'vp_test_04',sourceCode:'vp_test_04',game:'midnight-club-3-remix',
  gameLabel:'Midnight Club 3 Remix',sourceVariant:'native',displayMode:'native-package',bodyStyle:'unknown',
  agility:null,accel:null,speed:null,weight:null,bhp:null,kg:null,liveries:[],paint:null,
  model:{schema:3,previewStatus:'unavailable',source:{package:'dealership/assets/MC3_VP_TEST_04.dat',
    profile:'mc3-ps2-native-package-v1',preset:'dealership',sha256:'a'.repeat(64),bytes:8192,nativeMembers:3}}};
assert.equal(validateCars([native]).length,1);
assert(isNativePackage(native));
assert.equal(dealershipDownload(native).href,'./dealership/assets/MC3_VP_TEST_04.dat');
await assert.rejects(loadCar(native),/preview unavailable/);
for(const change of [c=>c.model.source.package='../wrong.dat',c=>c.model.source.sha256='bad',
  c=>c.model.source.bytes=0,c=>c.model.source.nativeMembers=0,c=>c.model.previewStatus='ready',
  c=>c.game='redline',c=>c.sourceCode='vp_other',c=>c.displayMode='textured-glb']) {
  const c=structuredClone(native);change(c);assert.throws(()=>validateCars([c]),/native/);
}

function element(){return {textContent:'',hidden:false,disabled:false,value:'',options:[],style:{},attributes:{},
  classList:{add(){},remove(){}},parentElement:{},replaceChildren(...nodes){this.options=nodes;},
  removeAttribute(k){delete this.attributes[k];if(k==='href')delete this.href;},setAttribute(k,v){this.attributes[k]=v;}};}
const sourcePage=fs.readFileSync(new URL('../dealership/recovered.html',import.meta.url),'utf8');
const start=sourcePage.indexOf('async function loadCar(){'),end=sourcePage.indexOf('function updateMaterials()',start);
assert(start>0 && end>start);
const elements=new Map();const node=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
const entry={id:'midnight-club-3-remix/vp_test_04',code:'vp_test_04',game:'midnight-club-3-remix',
  asset_kind:'native-package',file:'midnight-club-3-remix/native/vp_test_04.dat',native_members:3};
node('#car').value=entry.id;node('#retry').hidden=false;
let fetches=0,disposals=0;
const runSource=new Function('document','carSelect','recordSelect','status','index','isNativePackage','fetchModel',
  'readGLB','dispose','setLoading','updateDescription',
  `let requestId=0,pendingRequest=null,selected=null;${sourcePage.slice(start,end)}return loadCar;`)(
  {querySelector:node},node('#car'),node('#record'),node('#status'),{cars:[entry]},isNativePackage,
  async()=>{fetches++;throw Error('fixture GLB unavailable');},()=>assert.fail('native data was parsed as GLB'),
  ()=>disposals++,busy=>{node('#record').disabled=busy||true;},()=>{});
await runSource();
assert.equal(fetches,0);assert.equal(disposals,1);assert(node('#record').disabled);assert(node('#retry').hidden);
assert.equal(node('#download').href,'public/midnight-club-3-remix/native/vp_test_04.dat');
assert.match(node('#download').textContent,/native package/);assert.match(node('#status').textContent,/3D preview unavailable/);
assert.equal(node('#error').textContent,'');

const page=fs.readFileSync(new URL('../dealership/dealership.html',import.meta.url),'utf8');
const selectStart=page.indexOf('async function select(c) {'),selectEnd=page.indexOf('/* ---------- inspection controls',selectStart);
assert(selectStart>0 && selectEnd>selectStart);
let modelLoads=0,removed=0,disposed=0,filters=0;
const dealerElements=new Map();const $=id=>{if(!dealerElements.has(id))dealerElements.set(id,element());return dealerElements.get(id);};
const select=new Function('$','document','gameLabel','isNativePackage','dealershipDownload','scene','disposeCar',
  'loadCar','applyFilters','fmt',
  `let selectionId=0,selectionController=null,current=null,carMesh={};${page.slice(selectStart,selectEnd)}return select;`)(
  $,{querySelectorAll:()=>[]},()=>native.gameLabel,isNativePackage,dealershipDownload,{remove(){removed++;}},
  ()=>disposed++,()=>{modelLoads++;assert.fail('native preview tried to allocate geometry');},()=>filters++,String);
await select(native);
assert.equal(modelLoads,0);assert.equal(removed,1);assert.equal(disposed,1);assert.equal(filters,1);
assert.equal($('download-model').href,dealershipDownload(native).href);
assert.match($('loading').textContent,/3D preview unavailable/);assert.equal($('loading').hidden,false);
assert.equal($('v-sp').textContent,'Not decoded');assert.equal($('k-liv').textContent,'Not decoded');
assert.match($('paint-caveat').textContent,/not been converted/);
assert.equal($('auto-rotate').disabled,true);
await select(native);assert.equal(removed,1);assert.equal(modelLoads,0);
console.log('PASS native catalog UI: native selection clears prior models, enables DAT downloads, skips GLB/GPU loading, exposes preview state, validates identity and rejects corrupt metadata');
