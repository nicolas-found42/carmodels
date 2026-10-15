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
  children:[],childElementCount:0,listeners:{},append(...nodes){this.children.push(...nodes);this.childElementCount=this.children.length;},
  addEventListener(type,listener){this.listeners[type]=listener;},
  classList:{add(){},remove(){}},parentElement:{},replaceChildren(...nodes){this.options=nodes;this.children=[...nodes];this.childElementCount=nodes.length;},
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
assert.equal(node('#download').download,'vp_test_04.dat');assert.match(node('#download').textContent,/\(\.dat\)/);

// GT4 packages are ZIPs: the label and saved name follow the published file, not a fixed extension.
const gt4={id:'gran-turismo-4/test0001',code:'test0001',game:'gran-turismo-4',asset_kind:'native-package',
  file:'gran-turismo-4/native/test0001.zip',native_members:5};
node('#car').value=gt4.id;
const runGt4=new Function('document','carSelect','recordSelect','status','index','isNativePackage','fetchModel',
  'readGLB','dispose','setLoading','updateDescription',
  `let requestId=0,pendingRequest=null,selected=null;${sourcePage.slice(start,end)}return loadCar;`)(
  {querySelector:node},node('#car'),node('#record'),node('#status'),{cars:[gt4]},isNativePackage,
  async()=>{fetches++;throw Error('fixture GLB unavailable');},()=>assert.fail('native data was parsed as GLB'),
  ()=>disposals++,busy=>{node('#record').disabled=busy||true;},()=>{});
await runGt4();
assert.equal(fetches,0);assert.equal(node('#download').href,'public/gran-turismo-4/native/test0001.zip');
assert.equal(node('#download').download,'test0001.zip');assert.match(node('#download').textContent,/native package \(\.zip\)/);
assert.match(node('#status').textContent,/5 native files · 3D preview unavailable/);

const page=fs.readFileSync(new URL('../dealership/dealership.html',import.meta.url),'utf8');
const selectStart=page.indexOf('async function select(c) {'),selectEnd=page.indexOf('/* ---------- inspection controls',selectStart);
assert(selectStart>0 && selectEnd>selectStart);
let modelLoads=0,removed=0,disposed=0,filters=0;
const dealerElements=new Map();const $=id=>{if(!dealerElements.has(id))dealerElements.set(id,element());return dealerElements.get(id);};
const select=new Function('$','document','gameLabel','isNativePackage','dealershipDownload','scene','disposeCar',
  'loadCar','applyFilters','fmt',
  `let selectionId=0,selectionController=null,current=null,carMesh={};${page.slice(selectStart,selectEnd)}return select;`)(
  $,{querySelectorAll:()=>[],createElement:element},()=>native.gameLabel,isNativePackage,dealershipDownload,{remove(){removed++;}},
  ()=>disposed++,()=>{modelLoads++;assert.fail('native preview tried to allocate geometry');},()=>filters++,String);
await select(native);
assert.equal(modelLoads,0);assert.equal(removed,1);assert.equal(disposed,1);assert.equal(filters,1);
assert.equal($('download-model').href,dealershipDownload(native).href);
assert.match($('loading').textContent,/3D preview unavailable/);assert.equal($('loading').hidden,false);
assert.equal($('v-sp').textContent,'Not decoded');assert.equal($('k-liv').textContent,'Not decoded');
assert.match($('paint-caveat').textContent,/not been converted/);
assert.equal($('auto-rotate').disabled,true);
await select(native);assert.equal(removed,1);assert.equal(modelLoads,0);
const helpersStart=page.indexOf('function showColourVariants('),helpersEnd=page.indexOf('/* ---------- inspection controls',helpersStart);
const {showColourVariants,showNativeSpecifications}=new Function('$','document',
  `${page.slice(helpersStart,helpersEnd)}return {showColourVariants,showNativeSpecifications};`)($,{createElement:element});
showColourVariants({userData:{colourVariants:[{index:0,name:'Native white'},{index:1,name:'Native red'}]}});
assert.equal($('colour-control').hidden,false);assert.equal($('colour-variant').disabled,false);
assert.equal($('colour-variant').value,'');assert.equal($('k-colours').textContent,'2');
assert.deepEqual($('colour-variant').options.map(o=>o.textContent),['Original / default colour','Native white','Native red']);
assert.equal($('colour-variant').options[0].value,'','initial label describes the GLB default, which can differ from variant zero');
showColourVariants({userData:{colourVariants:[{index:0,name:'Native white'},{index:1,name:'Native red'}],colourVariant:1}});
assert.equal($('colour-variant').value,'1','a previously applied material selection retains its label');
showColourVariants({userData:{colourVariants:[]}});
assert.equal($('colour-control').hidden,true);assert.equal($('colour-variant').options.length,0);
assert.equal($('k-colours').textContent,'Not available','edited model without embedded variants does not advertise catalog colours');
showColourVariants({userData:{colourVariants:[{index:0,name:'Only native set'}]}});
assert.equal($('colour-control').hidden,false);assert.equal($('colour-variant').disabled,false,'one variant can still differ from the GLB default');
let switched=null;
const handlerStart=page.indexOf("$('colour-variant').addEventListener('change'"),handlerEnd=page.indexOf('const motion',handlerStart);
new Function('$','carMesh',page.slice(handlerStart,handlerEnd))($,{userData:{setColourVariant:index=>switched=index}});
$('colour-variant').value='1';$('colour-variant').listeners.change();assert.equal(switched,1);
$('colour-variant').value='';$('colour-variant').listeners.change();assert.equal(switched,null,'the original/default option restores the base materials');
showNativeSpecifications({nativeMetadata:{identity:{status:'verified'},specifications:{drive:'FR',engine_type:'DOHC',
  length_mm:4310,power_rpm:6500,torque_kgm:28.5,suspension_front:'Double wishbone',displacement_cc:1998}}});
assert.equal($('native-specs').hidden,false);
const specRows=()=>Object.fromEntries($('native-specs').children.map(row=>row.children.map(n=>n.textContent)));
assert.equal(specRows().Drive,'FR');assert.equal(specRows().Length,'4310 mm');assert.equal(specRows()['Power at'],'6500 rpm');
assert.equal(specRows().Torque,'28.5 kg·m');assert.equal(specRows().Displacement,'1998 cc');
showNativeSpecifications({nativeMetadata:{identity:{status:'verified'}},specifications:{
  displacement_display_kind:'rotary-chamber-times-factor',displacement_rotary_chamber_cc:654,displacement_rotary_factor:2,displacement_cc:null}});
assert.equal(specRows().Displacement,'654 cc × 2');
showNativeSpecifications({nativeMetadata:{identity:{status:'unresolved'},specifications:{drive:'FR',mass_kg:1200}}});
assert.equal($('native-specs').hidden,true);assert.equal($('native-specs').children.length,0,'unresolved racing entries do not display stock specifications');
showNativeSpecifications(native);assert.equal($('native-specs').hidden,true);
console.log('PASS native catalog UI: native package downloads and preview state; GLB-backed colour selection, missing-variant edits, verified specifications, rotary display and unresolved-identity controls');
