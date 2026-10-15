import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isNativePackage, dealershipDownload, loadCar, validateCars, gameId, sourceCarId, createCarSearch} from '../dealership/dealership.mjs';
import {createColourControls} from '../dealership/colour-controls.mjs';
import * as THREE from '../dealership/vendor/three.module.js';
import {applyMaterial} from '../dealership/materials.mjs';

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
  'readGLB','dispose','setLoading','updateDescription','rememberCar',
  `let requestId=0,pendingRequest=null,selected=null;${sourcePage.slice(start,end)}return loadCar;`)(
  {querySelector:node},node('#car'),node('#record'),node('#status'),{cars:[entry]},isNativePackage,
  async()=>{fetches++;throw Error('fixture GLB unavailable');},()=>assert.fail('native data was parsed as GLB'),
  ()=>disposals++,busy=>{node('#record').disabled=busy||true;},()=>{},()=>{});
await runSource();
assert.equal(fetches,0);assert.equal(disposals,1);assert(node('#record').disabled);assert(node('#retry').hidden);
assert.equal(node('#download').href,'public/midnight-club-3-remix/native/vp_test_04.dat');
assert.match(node('#download').textContent,/native package/);assert.match(node('#status').textContent,/3D preview unavailable/);
assert.equal(node('#error').textContent,'');
assert.equal(node('#download').download,'vp_test_04.dat');assert.equal(new URLSearchParams(node('#dealership-link').href.split('?')[1]).get('car'),entry.id);assert.match(node('#download').textContent,/\(\.dat\)/);

// GT4 packages are ZIPs: the label and saved name follow the published file, not a fixed extension.
const gt4={id:'gran-turismo-4/test0001',code:'test0001',game:'gran-turismo-4',asset_kind:'native-package',
  file:'gran-turismo-4/native/test0001.zip',native_members:5};
node('#car').value=gt4.id;
const runGt4=new Function('document','carSelect','recordSelect','status','index','isNativePackage','fetchModel',
  'readGLB','dispose','setLoading','updateDescription','rememberCar',
  `let requestId=0,pendingRequest=null,selected=null;${sourcePage.slice(start,end)}return loadCar;`)(
  {querySelector:node},node('#car'),node('#record'),node('#status'),{cars:[gt4]},isNativePackage,
  async()=>{fetches++;throw Error('fixture GLB unavailable');},()=>assert.fail('native data was parsed as GLB'),
  ()=>disposals++,busy=>{node('#record').disabled=busy||true;},()=>{},()=>{});
await runGt4();
assert.equal(fetches,0);assert.equal(node('#download').href,'public/gran-turismo-4/native/test0001.zip');
assert.equal(node('#download').download,'test0001.zip');assert.match(node('#download').textContent,/native package \(\.zip\)/);
assert.match(node('#status').textContent,/5 native files · 3D preview unavailable/);

const page=fs.readFileSync(new URL('../dealership/dealership.html',import.meta.url),'utf8');
const selectStart=page.indexOf('async function select(c) {'),selectEnd=page.indexOf('/* ---------- inspection controls',selectStart);
assert(selectStart>0 && selectEnd>selectStart);
let modelLoads=0,removed=0,disposed=0,filters=0;
const dealerElements=new Map();const $=id=>{if(!dealerElements.has(id))dealerElements.set(id,element());return dealerElements.get(id);};
// Start enabled, as after a loaded 3D preview, so native selection must disable the controls.
const colourControls={enabled:true,clears:0,setEnabled(value){this.enabled=value;},clear(){this.clears++;}};
const select=new Function('$','document','gameLabel','isNativePackage','dealershipDownload','scene','disposeCar',
  'loadCar','applyFilters','fmt','colourControls','gameId','sourceCarId','rememberCar',
  `let selectionId=0,selectionController=null,current=null,carMesh={};${page.slice(selectStart,selectEnd)}return select;`)(
  $,{querySelectorAll:()=>[],createElement:element},()=>native.gameLabel,isNativePackage,dealershipDownload,{remove(){removed++;}},
  ()=>disposed++,()=>{modelLoads++;assert.fail('native preview tried to allocate geometry');},()=>filters++,String,colourControls,gameId,sourceCarId,()=>{});
await select(native);
assert.equal(modelLoads,0);assert.equal(removed,1);assert.equal(disposed,1);assert.equal(filters,1);
assert.equal($('download-model').href,dealershipDownload(native).href);assert.equal(new URLSearchParams($('source-link').href.split('?')[1]).get('car'),sourceCarId(native));
assert.match($('loading').textContent,/3D preview unavailable/);assert.equal($('loading').hidden,false);
assert.equal($('v-sp').textContent,'Not decoded');assert.equal($('k-liv').textContent,'Not decoded');
assert.match($('paint-caveat').textContent,/not been converted/);
assert.equal($('auto-rotate').disabled,true);
assert.equal(colourControls.enabled,false,'native packages disable custom colours');
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
new Function('$','carMesh','colourControls',page.slice(handlerStart,handlerEnd))($,{userData:{setColourVariant:index=>switched=index}},colourControls);
$('colour-variant').value='1';$('colour-variant').listeners.change();assert.equal(switched,1);
$('colour-variant').value='';$('colour-variant').listeners.change();assert.equal(switched,null,'the original/default option restores the base materials');
assert.equal(colourControls.clears,2,'factory choices remove a custom preview tint');

const colourNodes=new Map();const colourNode=id=>{if(!colourNodes.has(id))colourNodes.set(id,element());return colourNodes.get(id);};
const tints=[];let resets=0;
const custom=createColourControls({root:{querySelector:colourNode},onTint:value=>tints.push(value),onReset:()=>resets++});
const picker=colourNode('#custom-colour'),hex=colourNode('#custom-colour-hex'),reset=colourNode('#reset-colour');
assert(picker.disabled && hex.disabled && reset.disabled);
hex.value='#ff0000';hex.listeners.input();assert.equal(tints.length,0,'disabled controls cannot change a model');
custom.setEnabled(true);assert.equal(picker.disabled,false);assert.equal(hex.value,'#ffffff');
picker.value='#FA8072';picker.listeners.input();assert.equal(custom.tint,'#fa8072');assert.equal(hex.value,'#fa8072');
picker.value='#FF8800';picker.listeners.change();assert.equal(custom.tint,'#ff8800','native pickers can commit through change as well as live input');
hex.value='#0000ff';hex.listeners.input();assert.equal(picker.value,'#0000ff');assert.equal(tints.at(-1),'#0000ff');
const validCount=tints.length;hex.value='#ff';hex.listeners.input();
assert.equal(hex.attributes['aria-invalid'],'true');assert.equal(custom.tint,'#0000ff');assert.equal(tints.length,validCount);
assert.match(colourNode('#custom-colour-status').textContent,/last valid colour/);
hex.value='#00FF00';hex.listeners.input();assert.equal(custom.tint,'#00ff00');assert.equal(hex.attributes['aria-invalid'],undefined);
reset.listeners.click();assert.equal(custom.tint,null);assert.equal(tints.at(-1),null);assert.equal(resets,1);assert.equal(picker.value,'#ffffff');
picker.value='#aa0000';picker.listeners.input();custom.clear();assert.equal(custom.tint,null);assert.equal(tints.at(-1),null);
picker.value='#ff0000';picker.listeners.input();custom.setEnabled(false);
assert.equal(custom.tint,null);assert.equal(hex.value,'#ffffff');assert(picker.disabled && hex.disabled && reset.disabled);
custom.setEnabled(true);assert.equal(custom.tint,null,'new selections never inherit the previous car preview');

// Run the source page's actual material and factory-selection callbacks with real
// materials. Tint changes must coexist with texture/wire/filter inspector state.
const sourceNodes=new Map(),sourceNode=id=>{if(!sourceNodes.has(id))sourceNodes.set(id,element());return sourceNodes.get(id);};
let updateSource;
const sourceColours=createColourControls({root:{querySelector:sourceNode},onTint:()=>updateSource(),onReset:()=>{sourceNode('#variant').value='';updateSource();}});
const sourceTextures=[new THREE.Texture(),new THREE.Texture()];
const sourceMaterial=new THREE.MeshStandardMaterial();sourceMaterial.vertexColors=true;
const sourceDoc={materials:[{pbrMetallicRoughness:{baseColorFactor:[1,1,1,1],baseColorTexture:{index:0}}},
  {pbrMetallicRoughness:{baseColorFactor:[.5,1,1,1],baseColorTexture:{index:1}}}],textures:[{source:0},{source:1}]};
const sourceState={doc:sourceDoc,textures:sourceTextures,meshes:[{material:sourceMaterial,userData:{baseMaterial:0,variantMappings:[{material:1,variants:[1]}]}}]};
sourceNode('#variant').value='1';for(const id of ['textures','wire','sharp'])sourceNode('#'+id).checked=true;
const materialStart=sourcePage.indexOf('function updateMaterials()'),materialEnd=sourcePage.indexOf('// Keep the fitted',materialStart);
updateSource=new Function('loaded','document','applyMaterial','colourControls',sourcePage.slice(materialStart,materialEnd)+'return updateMaterials;')(
  sourceState,{querySelector:sourceNode},applyMaterial,sourceColours);
sourceColours.setEnabled(true);sourceNode('#custom-colour-hex').value='#ff0000';sourceNode('#custom-colour-hex').listeners.input();
assert.deepEqual(sourceMaterial.color.toArray(),[.5,0,0]);assert.equal(sourceMaterial.map,sourceTextures[1]);
assert.equal(sourceMaterial.wireframe,true);assert.equal(sourceMaterial.map.magFilter,THREE.NearestFilter);assert.equal(sourceMaterial.vertexColors,true);
sourceNode('#textures').checked=false;updateSource();assert.equal(sourceMaterial.map,null);assert.deepEqual(sourceMaterial.color.toArray(),[.5,0,0]);
sourceNode('#textures').checked=true;
const factoryStart=sourcePage.indexOf("document.querySelector('#variant').addEventListener('change'"),factoryEnd=sourcePage.indexOf('const parameters=',factoryStart);
new Function('document','colourControls',sourcePage.slice(factoryStart,factoryEnd))({querySelector:sourceNode},sourceColours);
sourceNode('#variant').listeners.change();assert.equal(sourceColours.tint,null);assert.deepEqual(sourceMaterial.color.toArray(),[.5,1,1]);
sourceNode('#custom-colour-hex').value='#0000ff';sourceNode('#custom-colour-hex').listeners.input();sourceNode('#reset-colour').listeners.click();
assert.equal(sourceNode('#variant').value,'');assert.deepEqual(sourceMaterial.color.toArray(),[1,1,1]);assert.equal(sourceMaterial.map,sourceTextures[0]);
sourceMaterial.dispose();sourceTextures.forEach(texture=>texture.dispose());
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
console.log('PASS native catalog UI: native package downloads and preview state; factory/custom picker and hex/reset controls, actual source material callbacks, GLB-backed colour selection, missing-variant edits, verified specifications, rotary display and unresolved-identity controls');

// Execute source filtering with a real catalog: incompatible variants recover,
// while valid restrictions and explicit empty searches keep their meaning.
{
  const catalog=JSON.parse(fs.readFileSync(new URL('../dealership/public/models.json',import.meta.url),'utf8'));
  const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
  const game=get('#game'),variant=get('#source-variant'),car=get('#car'),search=get('#search');
  game.value='gran-turismo';variant.value='canonical';
  variant.options=['','canonical','showroom','native','stock','base','addon'].map(value=>({value,textContent:value}));
  let loads=0,aborts=0,disposals=0;
  const filterStart=sourcePage.indexOf('function updateFilterAvailability()');
  const filterEnd=sourcePage.indexOf("document.querySelector('#interpret').addEventListener",filterStart);
  const filter=new Function('index','document','gameSelect','sourceVariant','carSelect','recordSelect','search','filterStatus','gameNames','dispose','setLoading','loadCar','onAbort','createCarSearch',
    `const status=document.querySelector('#status');let filterRevision=0,requestId=0,pendingRequest={abort(){onAbort();}};${sourcePage.slice(filterStart,filterEnd)}return filterCars;`)(
    catalog,{querySelector:get,createElement:element},game,variant,car,get('#record'),search,get('#filter-status'),{},
    ()=>disposals++,()=>{},()=>loads++,()=>aborts++,createCarSearch);
  filter();assert.equal(variant.value,'canonical');assert.equal(car.options.length,342);
  game.value='redline';filter();assert.equal(variant.value,'');assert(car.options.length>0);
  assert.match(get('#filter-status').textContent,/Cleared unavailable variant: canonical/);
  assert(variant.options.find(o=>o.value==='canonical').disabled);
  variant.value='base';game.value='all';filter();assert.equal(variant.value,'base','available restriction survives');
  get('#native-download').href='old.zip';get('#native-download-wrap').hidden=false;get('#error').textContent='Old failure';
  get('#record').options=[{value:'old'}];get('#variant').options=[{value:'old'}];
  search.value='no-such-car-xyz';filter();assert.equal(car.options.length,0);assert(car.disabled);
  assert.equal(get('#record').options.length,0);assert.equal(get('#variant').options.length,0);
  assert(get('#native-download-wrap').hidden);assert.equal(get('#native-download').href,undefined);
  assert.equal(get('#error').textContent,'');assert.match(get('#source-description').textContent,/No car selected/);
  assert(aborts>0&&disposals>0);
  search.focus=()=>{search.focused=true;};get('#clear-filters').listeners.click();
  assert.equal(search.value,'');assert.equal(game.value,'all');assert.equal(variant.value,'');
  assert.equal(car.options.length,catalog.cars.length);assert.equal(car.disabled,false);assert(search.focused);assert(loads>0);
}
console.log('PASS source filter recovery: incompatible variants, preserved valid filters, stale empty-state cleanup and clear action');
