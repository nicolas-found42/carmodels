import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createPaintSession} from '../dealership/game-paint.mjs';
import {decodeInspectionState,encodeInspectionState,inspectionURL,INSPECTION_PARAM,MAX_INSPECTION_BYTES,PILOT} from '../dealership/inspection-state.mjs';

const bytes=fs.readFileSync(new URL('../dealership/public/gran-turismo-4/previews/acra0001.glb',import.meta.url));
const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
const paintSession=createPaintSession(doc,{game:PILOT.game});
assert(paintSession.presets.length>1,'The pinned pilot needs a nondefault factory preset.');
paintSession.setPreset(1);
const camera={position:[1.123456789012345,-2.5,3.3],target:[.000000000001,5.7,-9.123456789],near:.01,far:2000,fov:40};
const source={...PILOT,record:'node0',variant:'1',paint:paintSession.state,camera,controls:{presentation:'enhanced',textures:true,sharp:false,wire:false,flip:false,'game-shading':false},source_sha256:'omitted',api_key:'PRIVATE',asset_bytes:'PRIVATE'};
const options={cars:[{id:PILOT.car,game:PILOT.game}],records:[{value:'node0',disabled:false},{value:'scene0',disabled:false},{value:'bad',disabled:true}],variants:['','0','1'],paintSession};
const raw=encodeInspectionState(source),decoded=decodeInspectionState(raw,options);
assert.deepEqual(decoded.issues,[]);assert.deepEqual(decoded.state.camera,camera);
assert.deepEqual(decoded.state.paint,paintSession.state);assert.equal(decoded.state.record,'node0');
assert.equal(decoded.state.variant,'1');assert.equal(decoded.state.controls.presentation,'enhanced');
assert(!raw.includes('PRIVATE'));assert(!raw.includes('source_sha256'));
const url=inspectionURL('http://localhost/recovered.html?keep=1#anchor',source);
assert.equal(url.searchParams.get('game'),PILOT.game);assert.equal(url.searchParams.get('car'),PILOT.car);
assert.equal(url.searchParams.get('keep'),'1');assert.equal(url.hash,'#anchor');
assert.deepEqual(decodeInspectionState(url.searchParams.get(INSPECTION_PARAM),options),decoded);
console.log('PASS real pilot preset and complete discrete/camera state roundtrip at exact numeric precision; URL retains legacy selection and excludes non-state data');

const reject=(patch,field)=>{
  const result=decodeInspectionState(JSON.stringify({version:1,...source,...patch}),options);
  assert(result.issues.some(issue=>issue.field===field&&issue.reason.length>10),JSON.stringify(result));
  return result.state;
};
for(const record of ['missing','bad',null,12])assert.equal(reject({record},'record').record,undefined);
for(const variant of ['999',null,1])assert.equal(reject({variant},'variant').variant,undefined);
assert.equal(reject({variant:'999'},'variant').paint.preset,null,'Paint must not restore a rejected selector preset.');
const inconsistent=reject({variant:'0'},'paint.preset');
assert.equal(inconsistent.variant,undefined);assert.equal(inconsistent.paint.preset,null);
assert.equal(reject({car:'unknown'},'car').car,undefined);
assert.equal(reject({car:'midnight-club-3-remix/350Z',game:'midnight-club-3-remix'},'car').car,undefined);
assert.equal(reject({version:99},'version').car,undefined);
assert.equal(decodeInspectionState(raw,{...options,cars:[]}).state.car,undefined);
for(const bad of [NaN,Infinity,-Infinity,'NaN',null]){
  for(const key of ['position','target']){
    const saved={...camera,[key]:[1,bad,3]};
    assert.equal(reject({camera:saved},'camera').camera,undefined);
    assert.throws(()=>encodeInspectionState({...source,camera:saved}),/camera/);
  }
}
for(const saved of [{...camera,far:.001},{...camera,near:0},{...camera,fov:180},{...camera,position:[1,2]}])assert.equal(reject({camera:saved},'camera').camera,undefined);
const appearance=reject({record:'unknown',variant:'unknown',camera:{},paint:{schema:1,preset:999,presetName:'wrong',channels:{unknown:{color:'unknown'}}}},'record');
assert.equal(appearance.car,PILOT.car);assert.equal(appearance.paint.preset,null);assert.deepEqual(appearance.paint.channels,{});
assert.equal(reject({paint:{...source.paint,presetName:'renamed'}},'paint.preset').paint.preset,null);
assert.equal(reject({paint:{schema:1,preset:null,presetName:null,channels:{body:{color:'unknown'}}}},'paint.channels').car,PILOT.car);
const controls=reject({controls:{textures:'yes',presentation:'unknown',wire:true,secret:'PRIVATE'}},'controls.textures').controls;
assert.deepEqual(controls,{wire:true});
assert.equal(reject({paint:[]},'paint').paint,undefined);
console.log('PASS invalid car/version, unavailable geometry/preset/channel, malformed controls, nonfinite and invalid camera rejected by intended fields with visible reasons; appearance errors retain the pilot');

for(const raw of ['{','null','[]','NaN'])assert(decodeInspectionState(raw).issues.length);
for(const raw of ['x'.repeat(MAX_INSPECTION_BYTES+1),'é'.repeat(MAX_INSPECTION_BYTES/2)])assert.match(decodeInspectionState(raw).issues[0].reason,/8 KiB/);
const budgetEnvelope=JSON.stringify({version:1,...PILOT,padding:''});
const budgetSize=value=>new URLSearchParams({inspection:value}).toString().length-'inspection='.length;
const atLimit=budgetEnvelope.slice(0,-2)+'a'.repeat(MAX_INSPECTION_BYTES-budgetSize(budgetEnvelope))+'"}';
assert.equal(budgetSize(atLimit),MAX_INSPECTION_BYTES);
assert.deepEqual(decodeInspectionState(atLimit).issues,[],'Exactly 8 KiB is supported.');
assert.match(decodeInspectionState(atLimit.slice(0,-2)+'a"}').issues[0].reason,/8 KiB/);
assert.throws(()=>encodeInspectionState({...source,paint:{schema:1,preset:null,presetName:null,channels:Object.fromEntries(Array.from({length:100},(_,i)=>['channel'+i,{color:'c'.repeat(200)}]))}}),/8 KiB/);
assert.deepEqual(decodeInspectionState(null),{present:false,state:{},issues:[]});
assert.deepEqual(decodeInspectionState(JSON.stringify({version:1,...PILOT})),{present:true,state:PILOT,issues:[]});
assert.deepEqual(decodeInspectionState(encodeInspectionState(source),options).state,decoded.state,'A rejected attempt cannot contaminate a later restore.');
console.log('PASS bounded encoded URL budget including Unicode, malformed payloads, absent legacy snapshot, partial default state and independent restores');
