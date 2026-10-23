import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {createDiagnostics,createLoadTimeline,LIMITS,safeText,DIAGNOSTICS_KEY} from '../dealership/diagnostics.mjs';
import {replayIncident} from './replay_incident.mjs';

const values=new Map(),storage={getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)};
let time=Date.now();const ids=()=>crypto.randomUUID();
const create=options=>createDiagnostics({app:'source',storage:()=>storage,now:()=>time,uuid:ids,...options});
const first=create();first.snapshot({car:'ford-racing-2/COBRA',camera:{position:[1,2,3],target:[0,0,0]},paint:{preset:1}},'state.change');
first.record('load.failure',{error:{message:'token=PRIVATE Bearer PRIVATE sk-PRIVATE',stack:'at https://user:password@example.org/file.js?api_key=PRIVATE:2'},query:'PRIVATE',raw_response:'PRIVATE'});
assert(!JSON.stringify(first.bundle()).includes('PRIVATE'));
assert(!JSON.stringify(first.bundle()).includes('user:password'));
time+=1000;const afterReload=create();const previous=afterReload.history().find(b=>b.session_id===first.sessionId);
assert.equal(previous.state.car,'ford-racing-2/COBRA');assert.equal(previous.events.at(-1).kind,'load.failure');
assert.deepEqual(previous.state.camera.position,[1,2,3]);
console.log('PASS persistence: prior failure, camera and paint survive a fresh recorder; secret-bearing errors are redacted');
// Interleaved writes by two live tabs retain each other's sessions.
first.record('tab.first');afterReload.record('tab.second');assert.equal(first.history().length,2);
for(let i=0;i<400;i++)afterReload.record('bounded',{i});
assert.equal(afterReload.bundle().events.length,LIMITS.events);
for(let i=0;i<12;i++){time+=1000;create();}
assert.equal(create().history().length,LIMITS.sessions);
assert(new TextEncoder().encode([...values.values()][0]).length<=LIMITS.bytes);
time+=8*86400000;assert.equal(create().history().length,1);
const quota=create({storage:()=>({getItem(){throw Error('quota');},setItem(){throw Error('quota');},removeItem(){throw Error('quota');}})});
quota.record('load.failure');assert(quota.storageError);assert.equal(quota.bundle().events.at(-1).kind,'load.failure');
quota.setEnabled(false);quota.record('ignored');assert.equal(quota.bundle().events.length,0);
console.log('PASS bounds: event, session, age and byte limits; tab merge; quota denial stays exportable; opt-out clears recording');
const diag=create(),timeline=createLoadTimeline(diag),old=timeline.begin('old'),latest=timeline.begin('latest');
assert(latest.publish());assert(!old.publish());assert(diag.bundle().events.some(e=>e.kind==='load.stale'));
const cancelled=new AbortController(),attempt=timeline.begin('cancelled',cancelled.signal);cancelled.abort();assert(!attempt.publish());
assert.equal(diag.bundle().events.filter(e=>e.kind==='load.cancelled').length,2);
console.log('PASS race regression: a late old load cannot publish over the latest selection; explicit cancellation is retained');

const model=fs.readFileSync(new URL('../dealership/public/ford-racing-2/GRAN_TORINO.glb',import.meta.url));
const sha=createHash('sha256').update(model).digest('hex');
const makeTrace=events=>({schema:1,session_id:crypto.randomUUID(),app:'source',state:{car:'new',camera:{position:[1,2,3]}},identity:{},events:events.map(([kind,data],i)=>({seq:i+1,kind,data}))});
const trace=makeTrace([
  ['load.begin',{load_id:'1',car:'old'}],['fetch.begin',{load_id:'1',resource:'old.glb'}],
  ['load.begin',{load_id:'2',car:'new'}],['fetch.begin',{load_id:'2',resource:'new.glb'}],
  ['fetch.headers',{load_id:'2',status:200}],['fetch.success',{load_id:'2',sha256:sha}],['load.success',{load_id:'2'}],
  ['fetch.headers',{load_id:'1',status:200}],['fetch.success',{load_id:'1',sha256:sha}],['load.stale',{load_id:'1'}],
]);
const replay=await replayIncident(trace,{readAsset:()=>model});assert(replay.ok);assert.equal(replay.visible,'new');
const moduleText=fs.readFileSync(new URL('../dealership/diagnostics.mjs',import.meta.url),'utf8');
assert(moduleText.includes('if(!attempt.current())'));
const broken=await import('data:text/javascript;base64,'+Buffer.from(moduleText.replace('if(!attempt.current())','if(false)')).toString('base64'));
const mutant=await replayIncident(trace,{readAsset:()=>model,timelineFactory:broken.createLoadTimeline});assert(!mutant.ok);assert.equal(mutant.visible,'old');
assert.deepEqual(replay.recorded_state.camera.position,[1,2,3]);
const failureTrace=makeTrace([['load.begin',{load_id:'1',car:'missing'}],['fetch.begin',{load_id:'1',resource:'missing.glb'}],['fetch.headers',{load_id:'1',status:404}],['load.failure',{load_id:'1'}]]);
const failed=await replayIncident(failureTrace);assert(failed.ok);assert.equal(failed.reproduced[0].reproduced,true);assert.match(failed.results[0].message,/HTTP 404/);
const timeoutTrace=makeTrace([['load.begin',{load_id:'1',car:'stalled'}],['fetch.begin',{load_id:'1',resource:'stalled.glb'}],['fetch.headers',{load_id:'1',status:200}],['fetch.timeout',{load_id:'1'}],['load.failure',{load_id:'1'}]]);
const timed=await replayIncident(timeoutTrace);assert(timed.ok);assert.match(timed.results[0].message,/timed out/);
await assert.rejects(replayIncident(trace,{readAsset:()=>Buffer.from('changed')}),/asset hash differs/);
await assert.rejects(replayIncident({...trace,events:trace.events.slice(1)}),/no load start/);
console.log('PASS offline replay: actual fetch/parser, response ordering, 404, stalled body timeout, pinned-byte mismatch, incomplete trace; obsolete-publication mutation fails');

// Execute the shipped UI module with DOM/clipboard/network adapters. Test its effects,
// rather than asserting its source contains particular labels or callbacks.
const uiValues=new Map(),uiStorage={getItem:key=>uiValues.get(key)??null,setItem:(key,value)=>uiValues.set(key,value),removeItem:key=>uiValues.delete(key)};
const windowListeners={},documentListeners={},timers=new Map(),nodes=[],posts=[],downloads=[];let timerId=0,copied='',restored=null,downloadBlob=null;
function element(tag){
  const node={tag,style:{},children:[],listeners:{},value:'',textContent:'',checked:false,
    setAttribute(name,value){this[name]=value;},append(...children){this.children.push(...children);},
    replaceChildren(...children){this.children=children;if(tag==='select')this.value=children[0]?.value??'';},
    addEventListener(type,fn){this.listeners[type]=fn;},click(){if(tag==='a')downloads.push({href:this.href,name:this.download});return this.listeners.click?.();},
    get options(){return this.children;}};nodes.push(node);return node;
}
const ui={createDiagnostics,createLoadTimeline,safeText,DIAGNOSTICS_KEY,buildInfo:{git_sha:'fixture'},assetBaseURL:null,
  location:{pathname:'/recovered.html',hostname:'127.0.0.1'},localStorage:uiStorage,crypto,
  navigator:{userAgent:'test-browser',clipboard:{async writeText(value){copied=value;}}},innerWidth:1000,innerHeight:700,devicePixelRatio:1,
  document:{body:element('body'),createElement:element,createTextNode:value=>({textContent:value}),addEventListener:(kind,fn)=>{documentListeners[kind]=fn;}},
  addEventListener:(kind,fn)=>{windowListeners[kind]=fn;},
  setTimeout:(fn,delay)=>{timers.set(++timerId,{fn,delay});return timerId;},clearTimeout:id=>timers.delete(id),
  AbortController,Blob,URL:{createObjectURL:blob=>{downloadBlob=blob;return 'blob:report';},revokeObjectURL(){}},queueMicrotask,TextEncoder,
  fetch:async(url,options)=>{
    if(options?.method==='POST'){posts.push({url,options});return {ok:true,json:async()=>({session_id:JSON.parse(options.body).session_id})};}
    return {ok:true,json:async()=>({schema:1,identity:{git_sha:'fixture'}})};
  },
};
const uiCode=fs.readFileSync(new URL('../dealership/diagnostics-ui.mjs',import.meta.url),'utf8').replace(/^import .*;\n/gm,'');
vm.createContext(ui);vm.runInContext(uiCode,ui);await new Promise(resolve=>setImmediate(resolve));
const vector=value=>({value,toArray(){return this.value;},fromArray(next){this.value=[...next];}});
const canvasListeners={},controlListeners={};
const camera={position:vector([1,2,3]),near:.1,far:100,fov:40,updateProjectionMatrix(){}},orbit={target:vector([0,0,0]),enableDamping:true,autoRotate:true,update(){},addEventListener:(type,fn)=>{controlListeners[type]=fn;}};
ui.__carDiagnostics.attachViewer({renderer:{domElement:{addEventListener:(type,fn)=>{canvasListeners[type]=fn;}},getContext:()=>({VERSION:1,getParameter:()=> 'WebGL test'}),info:{memory:{geometries:2,textures:3},render:{calls:2,triangles:50}}},camera,controls:orbit,getState:()=>({car:'fixture',paint:{preset:1}}),restoreState:async state=>{restored=state;}});
canvasListeners.webglcontextlost();canvasListeners.webglcontextrestored();
windowListeners.error({error:Error('token=PRIVATE')});windowListeners.unhandledrejection({reason:Error('Bearer PRIVATE')});
const uiBundle=ui.__carDiagnostics.bundle();assert(!JSON.stringify(uiBundle).includes('PRIVATE'));
for(const kind of ['webglcontextlost','webglcontextrestored','runtime.error','runtime.rejection'])assert(uiBundle.events.some(e=>e.kind===kind),kind);
const uiButton=label=>nodes.find(n=>n.tag==='button'&&n.textContent===label);
await uiButton('Copy diagnostics').click();assert.equal(JSON.parse(copied).state.car,'fixture');
await uiButton('Download diagnostics').click();assert.match(downloads[0].name,/^car-incident-.*\.json$/);assert.equal(JSON.parse(await downloadBlob.text()).state.car,'fixture');
await uiButton('Replay viewer state').click();assert.equal(restored.car,'fixture');assert.deepEqual(camera.position.value,[1,2,3]);assert.equal(orbit.autoRotate,false);
for(const [id,timer] of [...timers])if(timer.delay===300){timers.delete(id);await timer.fn();}
assert(posts.some(post=>post.url==='/api/diagnostics'&&post.options.headers['X-Car-Diagnostics']==='1'));
assert(!JSON.stringify(posts).includes('PRIVATE'));
const importControl=nodes.find(n=>n.tag==='input'&&n.type==='file');
importControl.files=[{size:100,text:async()=>JSON.stringify(uiBundle)}];await importControl.listeners.change();assert.equal(restored.car,'fixture');
const toggle=nodes.find(n=>n.tag==='input'&&n.type==='checkbox');toggle.checked=false;toggle.listeners.change();
assert.equal(ui.__carDiagnostics.enabled,false);assert.equal(uiStorage.getItem(DIAGNOSTICS_KEY),null);
assert.equal(ui.__carDiagnostics.viewerState().car,'fixture','sharing reads live state even with diagnostic recording disabled');
console.log('PASS actual diagnostics UI: global errors/rejections, context loss/restoration, clipboard/download export, imported state replay, local upload, redaction and opt-out effects');
