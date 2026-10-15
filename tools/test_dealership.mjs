import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import * as THREE from '../dealership/vendor/three.module.js';
import {makeCar, disposeCar, decodeModel, validateCars, fetchCars, gameId, matchesVariant, dealershipDownload, createCarSearch, resolveCarAlias, sourceCarId, rememberCar} from '../dealership/dealership.mjs';

const cars = JSON.parse(fs.readFileSync(new URL('../dealership/public/dealership/cars.json', import.meta.url)));
const dealershipPage = fs.readFileSync(new URL('../dealership/dealership.html',import.meta.url),'utf8');
const sourcePage = fs.readFileSync(new URL('../dealership/recovered.html',import.meta.url),'utf8');
assert.match(dealershipPage,/fetchCars\('\.\/public\/dealership\/cars.json'\)/);
assert(!dealershipPage.includes('silhouette')&&!dealershipPage.includes('Silhouette'),'old visible terminology removed');
assert.equal(dealershipDownload(cars[0]).href,`./dealership/models/${cars[0].code}.glb`,'dealership downloads its own copies');
assert.match(sourcePage,/public\/models.json/,'source showcase retains its own corpus');
assert.match(sourcePage,/<h1>Source model library<\/h1>/);
assert.equal(validateCars(cars).length, cars.length);
const compactCars=cars.filter(c=>c.model.schema===4);
assert.equal(compactCars.length,35);
// Project-owned showcase geometry has one index encoding: unsigned 32-bit.
const largeCar=structuredClone(compactCars[0]),vertexCount=65538;
const vertices=Buffer.alloc(vertexCount*25),indices32=Buffer.alloc(vertexCount*4);
for(let i=0;i<vertexCount;i++) {
  vertices.writeFloatLE(i,i*25);vertices.writeFloatLE(i%2,i*25+4);vertices.writeFloatLE(i%3,i*25+8);
  vertices.writeFloatLE(1,i*25+16);vertices.writeUInt8(128,i*25+24);indices32.writeUInt32LE(i,i*4);
}
largeCar.model.parts=[{kind:'body',vertexCount,vertices:vertices.toString('base64'),indices:indices32.toString('base64')}];
largeCar.model.bounds=[0,0,0,vertexCount,2,3];largeCar.model.wheelHubs=[];largeCar.model.triangleCount=vertexCount/3;
const decodedLarge=decodeModel(largeCar);
assert(decodedLarge[0].indices instanceof Uint32Array);
assert.equal(decodedLarge[0].indices.at(-1),65537,'index above65535 must retain its value');
const largeMesh=makeCar(largeCar);
assert(largeMesh.children[0].geometry.index.array instanceof Uint32Array);
assert.equal(largeMesh.children[0].geometry.index.array.at(-1),65537);
disposeCar(largeMesh);
const tintCar=makeCar(compactCars[0]),tintBody=tintCar.children.find(n=>n.name==='body');
const stored=tintBody.material.color.clone(),storedSource=JSON.stringify(compactCars[0]);
const otherMaterials=tintCar.children.filter(n=>n.name!=='body').map(n=>[n.material,n.material.color.clone()]);
tintCar.userData.setColourTint('#ff0000');assert.deepEqual(tintBody.material.color.toArray(),[stored.r,0,0]);
tintCar.userData.setColourTint('#0000ff');assert.deepEqual(tintBody.material.color.toArray(),[0,0,stored.b]);
for(const [material,colour] of otherMaterials)assert(material.color.equals(colour),'known compact wheel/detail materials keep their colour');
assert.throws(()=>tintCar.userData.setColourTint('red'),/Invalid custom colour/);
assert.equal(tintCar.userData.colourTint,'#0000ff');tintCar.userData.setColourTint();assert(tintBody.material.color.equals(stored));
assert.equal(JSON.stringify(compactCars[0]),storedSource);disposeCar(tintCar);
assert.throws(()=>decodeModel({...largeCar,model:{...largeCar.model,schema:1}}),/invalid dealership model/,'stale16-bit schema must be rejected');
for(const width of [2,4]) {
  const bad=structuredClone(largeCar);
  const raw=Buffer.from(bad.model.parts[0].indices,'base64');
  if(width===2)bad.model.parts[0].indices=raw.subarray(0,raw.length-2).toString('base64');
  else {raw.writeUInt32LE(vertexCount,raw.length-4);bad.model.parts[0].indices=raw.toString('base64');}
  assert.throws(()=>decodeModel(bad),/invalid dealership model/);
}
const gtCars=cars.filter(c=>c.game==='gran-turismo');
assert.equal(gtCars.length,342);
assert(gtCars.every(c=>c.sourceVariant==='canonical'&&!/_(DAY|NIGHT)$/.test(c.code)));
assert(!dealershipPage.includes('<option value="night">')&&!dealershipPage.includes('<option value="day">'));
for(const c of gtCars){for(const alias of c.sourceAliases)assert.equal(resolveCarAlias(cars,alias,'code'),c);}
assert.equal(resolveCarAlias(cars,'missing','code'),undefined);
for(const c of gtCars){
  const specs=c.nativeMetadata?.identity?.status==='verified'?c.nativeMetadata.specifications:null;
  assert.equal(c.model.schema,2);assert.equal(c.bhp,specs?.power_hp_game??null);assert.equal(c.kg,specs?.mass_kg??null);
  assert.equal(c.speed,null);assert.equal(gameId(c),'gran-turismo');
}
assert.equal(gameId(compactCars[0]),'ford-racing-2');
const redlineCars=cars.filter(c=>c.game==='redline');
for(const c of redlineCars){assert.equal(c.model.schema,2);assert.equal(c.bhp,null);assert.equal(c.speed,null);assert.equal(gameId(c),'redline');}
const redlineFixture={...gtCars[0],game:'redline',gameLabel:'Redline',sourceVariant:'base'};
assert.equal(validateCars([redlineFixture]).length,1);
assert(matchesVariant(redlineFixture,'base'));
assert(!matchesVariant(redlineFixture,'addon'));
assert.match(dealershipPage,/<option value="base">Base game<\/option>/);
assert.match(dealershipPage,/<option value="addon">Add-on<\/option>/);
assert.match(sourcePage,/'redline':'Redline'/);
assert(matchesVariant({sourceVariant:'night'},'night'));
assert(!matchesVariant({sourceVariant:'day'},'night'));
assert(matchesVariant({sourceCollection:'arcade'},'arcade'));
// Frozen name/year cases and negative controls; all complete IDs remain discoverable.
for (const query of ['mustang 1968', '1968 mustang', '  MUSTANG   1968  ', 'mustang, 1968', 'ｍｕｓｔａｎｇ 1968']) {
  assert.deepEqual(cars.filter(createCarSearch(query)).map(c=>c.code), ['MUSTANG_68','MUSTANG_68B'], query);
}
for (const query of ['mustang 1967', 'not-a-real-car-xyz', '1968 lightning'])assert.equal(cars.filter(createCarSearch(query)).length,0,query);
assert.equal(cars.filter(c=>c.game!=='midnight-club-los-angeles').filter(createCarSearch('mustang')).length,15);
assert(cars.filter(createCarSearch('mustang')).some(c=>c.game==='midnight-club-los-angeles'),'newMCLA names participate in search');
assert.equal(cars.filter(createCarSearch('')).length,cars.length);
assert.equal(cars.filter(createCarSearch('f 150')).length,3);
for(const car of cars)assert(cars.filter(createCarSearch(car.code)).some(c=>c.code===car.code),car.code);
assert.equal(createCarSearch('!!!')(cars[0]),false,'punctuation-only input must not match every car');
assert(createCarSearch('_')({name:'test',code:'GT_TEST',year:null}),'literal identifier punctuation remains searchable');

// Run the actual dependent-filter reconciliation against real cars and native-like controls.
const availabilityStart=dealershipPage.indexOf('function updateFilterAvailability()');
const availabilityBody=dealershipPage.slice(availabilityStart,dealershipPage.indexOf('function applyFilters()',availabilityStart));
const availabilityControls={
  'game-filter':{value:'gran-turismo-4'},
  'variant-filter':{value:'night',options:['','canonical','day','night','arcade','base','addon','native','showroom','stock'].map(value=>({value,textContent:value||'All variants'}))},
  'filter-status':{textContent:''},
};
const chips=[['SIMULATION',c=>c.group==='SIMULATION'],['COUPE',c=>c.bodyStyle==='coupe']].map(([textContent,pred])=>({
  textContent,_pred:pred,on:true,setAttribute(key,value){this[key]=value;},classList:{contains(){return this.owner.on;},remove(){this.owner.on=false;}}}));
for(const chip of chips)chip.classList.owner=chip;
const reconcile=new Function('$','CARS','document','gameId','matchesVariant',availabilityBody+'return updateFilterAvailability;')(
  id=>availabilityControls[id],cars,{querySelectorAll:()=>chips},gameId,matchesVariant);
reconcile();
assert.equal(availabilityControls['variant-filter'].value,'');
assert.deepEqual(availabilityControls['variant-filter'].options.filter(o=>!o.disabled).map(o=>o.value),['','showroom']);
assert(chips.every(c=>c.disabled && !c.on && c['aria-pressed']==='false'));
assert.match(availabilityControls['filter-status'].textContent,/night, SIMULATION, COUPE/);
availabilityControls['game-filter'].value='all';availabilityControls['variant-filter'].value='canonical';reconcile();
assert.equal(availabilityControls['variant-filter'].value,'canonical','available cross-game restriction must stay');
availabilityControls['game-filter'].value='gran-turismo';reconcile();
assert.equal(availabilityControls['variant-filter'].value,'canonical','valid game-specific restriction must stay');
availabilityControls['game-filter'].value='redline';reconcile();
assert.deepEqual(availabilityControls['variant-filter'].options.filter(o=>!o.disabled).map(o=>o.value),['','base','addon']);

// Run the page's actual semantic handlers with a delayed transport response.
// Manual controls must invalidate that pending response before it can apply.
const semanticStart=dealershipPage.indexOf('function invalidateSemantic()');
const semanticEnd=dealershipPage.indexOf('function buildList()',semanticStart);
const callbacks=dealershipPage.slice(semanticStart,semanticEnd);
assert(semanticStart>0 && semanticEnd>semanticStart);
for(const action of ['game','variant','search','query','clear']) {
  const controls={};
  for(const id of ['search','game-filter','variant-filter','semantic-query','semantic-form','semantic-filter','semantic-status','clear-filters'])controls[id]={value:'',textContent:'',listeners:{},addEventListener(type,callback){this.listeners[type]=callback;},focus(){}};
  controls['game-filter'].value='all';controls['game-filter'].options=[{value:'all'},{value:'gran-turismo'}];
  controls['variant-filter'].options=['','day','night','arcade'].map(value=>({value}));
  controls['semantic-query'].value='Gran Turismo night';
  let resolveResponse, applications=0;
  const pending=new Promise(resolve=>{resolveResponse=resolve;});
  let signal;
  new Function('$','document','applyFilters','updateFilterAvailability','fetch',`let semanticId=0,semanticController=null;${callbacks}`)(id=>controls[id],{querySelectorAll:()=>[]},()=>applications++,()=>{},(_url,options)=>{signal=options.signal;return pending;});
  const request=controls['semantic-form'].onsubmit({preventDefault(){}});
  assert.equal(controls['semantic-filter'].disabled,true);
  if(action==='game'){controls['game-filter'].value='all';controls['game-filter'].onchange();}
  if(action==='variant'){controls['variant-filter'].value='day';controls['variant-filter'].onchange();}
  if(action==='search')controls.search.listeners.input();
  if(action==='query')controls['semantic-query'].listeners.input();
  if(action==='clear')controls['clear-filters'].onclick();
  assert(signal.aborted,`obsolete ${action} request was not cancelled`);
  assert.equal(controls['semantic-status'].textContent,'');
  assert.equal(controls['semantic-filter'].disabled,false);
  if(action==='clear')assert.equal(controls['semantic-query'].value,'');
  const before={game:controls['game-filter'].value,variant:controls['variant-filter'].value,applications};
  resolveResponse({ok:true,json:async()=>({status:'ok',filters:{game:'gran-turismo',variant:'night'}})});
  await request;
  assert.deepEqual({game:controls['game-filter'].value,variant:controls['variant-filter'].value,applications},before,`stale semantic response overwrote ${action}`);
}
assert.match(dealershipPage,/el\.onclick = \(\) => \{ invalidateSemantic\(\);/,'chip changes invalidate semantic requests');
assert.match(dealershipPage,/<form id="semantic-form">/);
assert.match(dealershipPage,/<button type="submit" id="semantic-filter">/);
assert.match(dealershipPage,/aria-describedby="semantic-help"/);
// Failure statuses show the server's own explanation, a server without the API names the fix,
// and a timeout is explained instead of showing the browser's abort text.
for (const [transport, expected] of [
  [async()=>({ok:false,json:async()=>({status:'error',message:'A filter request is already running.'})}),'A filter request is already running.'],
  [async()=>({ok:false,json:async()=>{throw SyntaxError('HTML error page');}}),/needs the library server \(python3 tools\/serve_library\.py\)/],
  [async()=>{throw Object.assign(Error('signal is aborted without reason'),{name:'AbortError'});},'Interpreting took longer than 35 seconds. Use the game and variant selectors.']]) {
  const controls={};
  for(const id of ['search','game-filter','variant-filter','semantic-query','semantic-form','semantic-filter','semantic-status','clear-filters'])controls[id]={value:'',textContent:'',listeners:{},addEventListener(type,callback){this.listeners[type]=callback;},focus(){}};
  controls['game-filter'].value='all';controls['semantic-query'].value='Gran Turismo night';
  new Function('$','document','applyFilters','fetch',`let semanticId=0,semanticController=null;${callbacks}`)(id=>controls[id],{querySelectorAll:()=>[]},()=>assert.fail('failure applied filters'),transport);
  await controls['semantic-form'].onsubmit({preventDefault(){}});
  if(typeof expected==='string')assert.equal(controls['semantic-status'].textContent,expected);
  else assert.match(controls['semantic-status'].textContent,expected);
  assert.equal(controls['game-filter'].value,'all');
  assert.equal(controls['semantic-filter'].disabled,false);
}
// A valid response applies through the real path; nonexistent game/variant pairs leave it unchanged.
for(const [filters,expected] of [[{game:'gran-turismo',variant:'canonical'},true],[{game:'gran-turismo-4',variant:'night'},false]]) {
  const controls={};
  for(const id of ['search','game-filter','variant-filter','semantic-query','semantic-form','semantic-filter','semantic-status','clear-filters'])
    controls[id]={value:'',textContent:'',addEventListener(){},focus(){}};
  controls['game-filter'].value='all';controls['game-filter'].options=['all','gran-turismo','gran-turismo-4'].map(value=>({value}));
  controls['variant-filter'].options=['','canonical','night'].map(value=>({value}));controls['semantic-query'].value='a non-sensitive fixture';
  let applied=0,reconciled=0;
  new Function('$','document','applyFilters','updateFilterAvailability','fetch','CARS','gameId','matchesVariant',
    `let semanticId=0,semanticController=null;${callbacks}`)(id=>controls[id],{querySelectorAll:()=>[]},()=>applied++,()=>reconciled++,
    async()=>({ok:true,json:async()=>({status:'ok',filters})}),cars,gameId,matchesVariant);
  await controls['semantic-form'].onsubmit({preventDefault(){}});
  assert.equal(applied,Number(expected));assert.equal(reconciled,Number(expected));
  assert.equal(controls['game-filter'].value,expected?'gran-turismo':'all');
  if(!expected)assert.match(controls['semantic-status'].textContent,/no entries/);
  assert.equal(controls['semantic-filter'].disabled,false);
}
// Exercise the real timeout callback without waiting 35 seconds; an abort-aware transport rejects.
{
  const controls={};
  for(const id of ['search','game-filter','variant-filter','semantic-query','semantic-form','semantic-filter','semantic-status','clear-filters'])
    controls[id]={value:'',textContent:'',addEventListener(){},focus(){}};
  controls['semantic-query'].value='non-sensitive timeout fixture';
  let expire,delay,cleared=false;
  new Function('$','document','applyFilters','fetch','setTimeout','clearTimeout',
    `let semanticId=0,semanticController=null;${callbacks}`)(id=>controls[id],{querySelectorAll:()=>[]},()=>assert.fail('timeout applied filters'),
    (_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(Error('aborted'),{name:'AbortError'})),{once:true})),
    (callback,ms)=>{expire=callback;delay=ms;return 17;},timer=>{assert.equal(timer,17);cleared=true;});
  const request=controls['semantic-form'].onsubmit({preventDefault(){}});
  assert.equal(delay,35000,'UI must allow the existing 30-second provider budget');expire();await request;
  assert(cleared);assert.match(controls['semantic-status'].textContent,/35 seconds/);
  assert.equal(controls['semantic-filter'].disabled,false);
}
for (const car of compactCars) {
  const mesh = makeCar(car);
  const bounds = new THREE.Box3().setFromObject(mesh);
  assert(bounds.min.toArray().every(Number.isFinite) && bounds.max.toArray().every(Number.isFinite));
  assert(bounds.min.y >= -1e-6, `${car.code}: tyres penetrate the floor`);
  assert(Math.abs(bounds.min.z + bounds.max.z) < 1e-6, `${car.code}: body extends asymmetrically across its width`);
  assert.equal(mesh.userData.wheels.length, car.model.parts.filter(p=>p.kind==='wheel').length, 'render only the dealership wheel geometry');
  assert(mesh.children.length <= 3, 'compact body, wheel and detail meshes');
  assert.equal(mesh.children.reduce((sum,n)=>sum+n.geometry.index.count/3,0),car.model.triangleCount);
  for (const node of mesh.children) assert.equal(node.material.map, null, 'no runtime texture dependency');
  const geometries = new Set(), materials = new Set();
  mesh.traverse(node => {
    if (node.geometry) geometries.add(node.geometry);
    if (node.material) materials.add(node.material);
  });
  const counts = new Map();
  for (const resource of [...geometries, ...materials]) resource.addEventListener('dispose', () => counts.set(resource, (counts.get(resource) || 0) + 1));
  disposeCar(mesh);
  assert.equal(counts.size, geometries.size + materials.size);
  assert([...counts.values()].every(n => n === 1), 'shared resources disposed exactly once');
}
const seed = {...cars[0], speed:0, weight:0, agility:0, accel:0, paint:{rgb:[128,64,32]}};
const zero = makeCar(seed), half = makeCar({...seed, speed:0.5});
assert.deepEqual(zero.children[0].geometry.attributes.position.array,half.children[0].geometry.attributes.position.array,'handling ratings must not stretch geometry');
assert.equal(zero.children[0].material.color.getHexString(), '804020', 'display RGB sample must round trip through sRGB');
disposeCar(zero); disposeCar(half);
const bodyOnly = structuredClone(cars[0]);
bodyOnly.model.parts = bodyOnly.model.parts.filter(p=>p.kind!=='wheel');
bodyOnly.model.wheelHubs = [];
bodyOnly.model.triangleCount = bodyOnly.model.parts.reduce((sum,p)=>sum+Buffer.from(p.indices,'base64').length/12,0);
validateCars([bodyOnly]);
const custom = makeCar(bodyOnly);
assert.equal(custom.userData.wheels.length,0,'edited dealership models need not preserve source wheel counts');
disposeCar(custom);
// Display fields the page joins or prints must be validated before a car can be selected.
for (const [label, patch] of [['string limits',{claimLimits:'not a list'}],['object limits',{claimLimits:{a:1}}],['non-string limit',{claimLimits:[1]}],
    ['model limits',{model:{...cars[0].model,claimLimits:'x'}}],['unknown style without variant',{bodyStyle:'unknown',sourceVariant:undefined}],
    ['unknown style with empty variant',{bodyStyle:'unknown',sourceVariant:''}]])
  assert.throws(()=>validateCars([{...cars[0],...patch}]),/claim limits|source variant/,label);
assert.equal(validateCars([{...cars[0],claimLimits:['A limit.']}]).length,1);
assert.equal(validateCars([{...gtCars[0],bodyStyle:'unknown',sourceVariant:'day'}]).length,1);
// Hiding the preview schedules one deferred selection; it must not load a model per keystroke.
const filterStart=dealershipPage.indexOf('function applyFilters()');
const filterBody=dealershipPage.slice(filterStart,dealershipPage.indexOf("$('search').addEventListener('input'",filterStart));
assert(filterStart>0 && !/\bselect\(/.test(filterBody.slice(0,filterBody.indexOf('function selectFirstVisibleIfHidden'))),'applyFilters selects synchronously');
assert.match(filterBody,/clearTimeout\(autoSelectTimer\);\s*autoSelectTimer=setTimeout\(selectFirstVisibleIfHidden,300\)/);
for (const [currentHidden, expected] of [[true,['B']],[false,[]]]) {
  const selected=[];
  const rows=[{_code:'A',hidden:currentHidden},{_code:'B',hidden:false}];
  new Function('document','current','select','CARS','selected',filterBody.slice(filterBody.indexOf('function selectFirstVisibleIfHidden'))+';selectFirstVisibleIfHidden();')(
    {querySelectorAll:()=>rows},{code:'A'},car=>selected.push(car.code),[{code:'A'},{code:'B'}],selected);
  assert.deepEqual(selected,expected,`current hidden=${currentHidden}`);
}
for (const data of [[], {}, [cars[0],cars[0]], [{...cars[0],speed:NaN}], [{...cars[0],weight:2}], [{...cars[0],liveries:null}], [{...cars[0],paint:{rgb:[256,0,0]}}], [{...cars[0],bodyStyle:'invalid'}]]) assert.throws(() => validateCars(data));
for (const mutate of [
  c=>delete c.model,
  c=>c.model.source.glb='dealership/models/OTHER.glb',
  c=>c.model.parts[0].vertices='bad',
  c=>c.model.parts[0].vertexCount++,
  c=>c.model.triangleCount++,
  c=>{const b=Buffer.from(c.model.parts[0].vertices,'base64');b.writeFloatLE(NaN,0);c.model.parts[0].vertices=b.toString('base64');},
  c=>{const b=Buffer.from(c.model.parts[0].vertices,'base64');b.writeFloatLE(0,12);b.writeFloatLE(0,16);b.writeFloatLE(0,20);c.model.parts[0].vertices=b.toString('base64');},
  c=>{const b=Buffer.from(c.model.parts[0].indices,'base64');b.writeUInt32LE(0xffffffff,0);c.model.parts[0].indices=b.toString('base64');},
]) {
  const corrupted=structuredClone(cars[0]);mutate(corrupted);
  assert.throws(()=>validateCars([corrupted]),/model/);
}
assert.equal((await fetchCars('test', {fetchImpl:async()=>({ok:true,json:async()=>cars})})).length,cars.length);
await assert.rejects(fetchCars('test', {fetchImpl:async()=>({ok:false,status:404,json:async()=>cars})}), /HTTP 404/);
await assert.rejects(fetchCars('test', {fetchImpl:async()=>({ok:true,json:async()=>[]})}), /empty/);
for (const bodyStall of [false,true]) {
  await assert.rejects(fetchCars('test', {timeoutMs:20,fetchImpl:async(_url,{signal})=>{
    const stalled = () => new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('aborted')),{once:true}));
    return bodyStall ? {ok:true,json:stalled} : stalled();
  }}), /timed out/);
}
// Actual transport: response headers arrive, but JSON body never completes.
const server = http.createServer((_request, response) => {
  response.writeHead(200, {'Content-Type':'application/json'});
  response.write('[');
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  await assert.rejects(fetchCars(`http://127.0.0.1:${server.address().port}/`, {timeoutMs:100}), /timed out/);
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
console.log(`PASS test_dealership: ${cars.length} searchable IDs, name/year order and punctuation, precision controls, dependent variant/chip recovery, semantic cancellation/stale responses/35-second timeout/invalid pairs, compact body tint/reset with wheel/detail preservation, 35 dealership meshes, floor contact, <=3 meshes, unique disposal, rating-independent geometry, sRGB, malformed model/corpus controls and real HTTP body timeout`);

// Both viewers share source identities even when editable codes are namespaced.
const sourceCatalog=JSON.parse(fs.readFileSync(new URL('../dealership/public/models.json',import.meta.url),'utf8')).cars;
for(const car of cars){
  const source=sourceCatalog.find(entry=>entry.id===sourceCarId(car));
  assert(source,car.code);
  assert.equal(resolveCarAlias(cars,source.id,'code'),car);
  assert.equal(resolveCarAlias(sourceCatalog,sourceCarId(car)),source);
  const query=new URLSearchParams({game:gameId(car),car:sourceCarId(car)});
  assert.equal(resolveCarAlias(cars,new URLSearchParams(String(query)).get('car'),'code'),car);
}
assert.equal(resolveCarAlias(cars,'unknown/source','code'),undefined);
console.log('PASS viewer navigation identities: every editable car resolves to its source and back');

// Replace the current entry rather than growing history for every car click.
{
  const browser={location:{href:'http://localhost:8080/dealership.html?game=gran-turismo&car=old&variant=canonical&debug=1#viewer'},history:{state:{scroll:42},replaceState(state,title,href){this.saved={state,title,href};}}};
  const target=cars.find(car=>car.code==='MUSTANG_68B');
  rememberCar(target,browser);await Promise.resolve();
  const saved=new URL(browser.history.saved.href);
  assert.equal(saved.searchParams.get('car'),sourceCarId(target));assert.equal(saved.searchParams.get('game'),'ford-racing-2');
  assert.equal(saved.searchParams.has('variant'),false);assert.equal(saved.searchParams.get('debug'),'1');assert.equal(saved.hash,'#viewer');
  assert.equal(browser.history.saved.state,browser.history.state);
  assert.equal(resolveCarAlias(cars,saved.searchParams.get('car'),'code'),target);
  assert.equal(resolveCarAlias(sourceCatalog,saved.searchParams.get('car')).code,'MUSTANG_68B');
}
console.log('PASS selected identity replaces current URL and survives startup resolution');

// History writes are best effort and coalesced: browser quotas cannot abort selection.
{
  const writes=[];
  const browser={location:{href:'http://localhost:8080/recovered.html?variant=canonical'},history:{state:null,replaceState(_state,_title,href){writes.push(href);}}};
  const source=sourceCatalog.find(c=>c.game==='gran-turismo');
  rememberCar(source,browser);
  assert.equal(writes.length,0,'selection must defer history writes');
  await Promise.resolve();
  assert.equal(new URL(writes.at(-1)).searchParams.get('variant'),'canonical','valid source variant survives reload');
  writes.length=0;
  const first=cars.find(c=>c.code==='MUSTANG_68'),last=cars.find(c=>c.code==='MUSTANG_68B');
  rememberCar(first,browser);rememberCar(last,browser);await Promise.resolve();
  assert.equal(writes.length,1,'rapid selections coalesce to one URL update');
  assert.equal(new URL(writes[0]).searchParams.get('car'),sourceCarId(last));
  assert.equal(new URL(writes[0]).searchParams.has('variant'),false,'incompatible variant is cleared');
  browser.history.replaceState=()=>{throw new DOMException('History quota exceeded','SecurityError');};
  assert.doesNotThrow(()=>rememberCar(last,browser));await Promise.resolve();
}

// Exercise the actual startup selection for a game-only URL before history is written.
{
  const start=dealershipPage.indexOf('    const parameters = new URLSearchParams(location.search);');
  const end=dealershipPage.indexOf('    applyFilters();',start);
  const bootSelection=new Function('CARS','$','location','resolveCarAlias','gameId','updateFilterAvailability','select',
    `return (async()=>{${dealershipPage.slice(start,end)}})();`);
  for(const game of ['redline','gran-turismo','midnight-club-3-remix','all']){
    const filter={value:'all',options:['all','redline','gran-turismo','midnight-club-3-remix'].map(value=>({value}))};
    let selected;
    await bootSelection(cars,()=>filter,{search:'?game='+game},resolveCarAlias,gameId,()=>{},async car=>{selected=car;});
    assert.equal(filter.value,game);assert(selected);
    assert(game==='all'||gameId(selected)===game,'game-only startup must select within requested game');
  }
}
console.log('PASS startup game restrictions, coalesced history, valid variants and history quota recovery');
