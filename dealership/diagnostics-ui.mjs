import {createDiagnostics,createLoadTimeline,safeText,DIAGNOSTICS_KEY} from './diagnostics.mjs';
import {buildInfo} from './build-info.mjs';
import {assetBaseURL} from './asset-config.mjs';

const app=location.pathname.endsWith('recovered.html')?'source':'dealership';
const diagnostics=createDiagnostics({app,identity:{...buildInfo,asset_base:assetBaseURL}});
globalThis.__carDiagnostics=diagnostics;
globalThis.__carLoadTimeline=createLoadTimeline(diagnostics);
const local=['localhost','127.0.0.1','[::1]'].includes(location.hostname);
let snapshot=()=>({}),bridge=false,sharing=local,uploadTimer=null,uploading=false,uploadAgain=false;
const prefs='carmodels:diagnostic-preferences:v1';
try {const saved=JSON.parse(localStorage.getItem(prefs)||'{}');if(saved.enabled===false)diagnostics.setEnabled(false);if(saved.sharing===false)sharing=false;}catch{/* The recorder reports storage failure. */}
addEventListener('storage',event=>{
  if(event.key===DIAGNOSTICS_KEY&&event.newValue===null)diagnostics.clear();
  if(event.key===prefs){try {const saved=JSON.parse(event.newValue||'{}');diagnostics.setEnabled(saved.enabled!==false);sharing=saved.sharing!==false&&local;}catch{/* Ignore malformed preferences. */}}
});
const errorData=error=>({name:error?.name??'Error',message:error?.message??String(error??''),stack:error?.stack});
addEventListener('error',event=>{capture('runtime.state');diagnostics.record('runtime.error',{error:errorData(event.error??event.message),resource:event.target?.src??event.target?.href});});
addEventListener('unhandledrejection',event=>{capture('runtime.state');diagnostics.record('runtime.rejection',{error:errorData(event.reason)});});
addEventListener('pagehide',()=>{capture('session.pagehide');diagnostics.flush();});
function capture(reason='state.change'){try {diagnostics.snapshot(snapshot(),reason);}catch(error){diagnostics.record('snapshot.failure',{error:errorData(error)});}}
diagnostics.attachViewer=({renderer,camera,controls,getState,restoreState})=>{
  snapshot=()=>({...getState(),camera:{position:camera.position.toArray(),target:controls.target.toArray(),near:camera.near,far:camera.far,fov:camera.fov},
    renderer:{geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,calls:renderer.info.render.calls,triangles:renderer.info.render.triangles}});
  const gl=renderer.getContext();
  diagnostics.environment({browser:navigator.userAgent,viewport:[innerWidth,innerHeight],pixel_ratio:devicePixelRatio,webgl:gl.getParameter(gl.VERSION)});
  for(const type of ['webglcontextlost','webglcontextrestored'])renderer.domElement.addEventListener(type,()=>{capture('context.change');diagnostics.record(type);});
  controls.addEventListener('end',()=>capture('camera.change'));
  diagnostics.restore=async bundle=>{
    if(bundle?.schema!==1||bundle.app!==app||!bundle.state||!restoreState)throw Error('Choose a report from this viewer edition.');
    await restoreState(bundle.state);
    const saved=bundle.state.camera;
    if(saved){
      for(const field of ['position','target'])if(!Array.isArray(saved[field])||saved[field].length!==3||!saved[field].every(Number.isFinite))throw Error('Invalid recorded camera.');
      if(!(saved.near>0&&saved.far>saved.near&&saved.fov>0&&saved.fov<180))throw Error('Invalid recorded camera bounds.');
      controls.autoRotate=false;const damping=controls.enableDamping;controls.enableDamping=false;controls.update();
      camera.position.fromArray(saved.position);controls.target.fromArray(saved.target);camera.near=saved.near;camera.far=saved.far;camera.fov=saved.fov;
      controls.update();controls.enableDamping=damping;camera.updateProjectionMatrix();
    }
    capture('replay.state-restored');
  };
  capture('viewer.ready');
};
diagnostics.capture=capture;
diagnostics.catalog=async response=>{
  if(!globalThis.crypto?.subtle){diagnostics.record('catalog.hash-unavailable');return;}
  const bytes=await response.clone().arrayBuffer();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  diagnostics.identify({catalog_sha256:hash});
};
diagnostics.filterHeaders=()=>({'Content-Type':'application/json','X-Car-Session':diagnostics.sessionId});
diagnostics.filterResponse=response=>diagnostics.record('filter.response',{request_id:response.headers.get('X-Request-ID'),status:response.status});
document.addEventListener('change',event=>{if(event.target.closest?.('#car-diagnostics'))return;capture('control.change');});
document.addEventListener('click',event=>{
  const control=event.target.closest?.('button');if(!control||control.closest('#car-diagnostics'))return;
  // IDs are fixed app identifiers; button labels may contain user search text.
  diagnostics.record('control.click',{control:control.id||'paint-choice'});queueMicrotask(()=>capture());
});
function savePrefs(){try {localStorage.setItem(prefs,JSON.stringify({enabled:diagnostics.enabled,sharing}));}catch{/* Status below exposes unavailable storage. */}}
async function upload() {
  if(!bridge||!sharing||!diagnostics.enabled)return;
  if(uploading){uploadAgain=true;return;}
  uploading=true;
  try {
    const receipt=await postBundle(diagnostics.bundle());syncStatus.textContent='Available to local tools as incident '+receipt.session_id;
  }catch(error){syncStatus.textContent='Local sharing failed. Download diagnostics instead. '+safeText(error.message);}
  finally {uploading=false;if(uploadAgain){uploadAgain=false;queueUpload();}}
}
async function postBundle(bundle) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);
  try {
    const response=await fetch('/api/diagnostics',{method:'POST',headers:{'Content-Type':'application/json','X-Car-Diagnostics':'1','X-Car-Session':diagnostics.sessionId},body:JSON.stringify(bundle),signal:controller.signal});
    if(!response.ok)throw Error('Incident service HTTP '+response.status);return await response.json();
  }finally{clearTimeout(timer);}
}
function queueUpload(){clearTimeout(uploadTimer);uploadTimer=setTimeout(upload,300);}
diagnostics.setSink(()=>{queueUpload();updateStatus();});
const panel=document.createElement('details');panel.id='car-diagnostics';panel.style.cssText='box-sizing:border-box;position:fixed;bottom:12px;right:12px;max-width:min(540px,calc(100vw - 24px));max-height:70vh;overflow:auto;padding:10px;border:1px solid #687587;border-radius:6px;color:#eef2f8;background:#202833;font:14px/1.5 system-ui;z-index:100';
const summary=document.createElement('summary');summary.textContent='Diagnostics';panel.append(summary);
const note=document.createElement('p');note.textContent='Recent activity is saved on this browser for up to 7 days (8 sessions, 512 KiB). Reports include viewer settings and sanitized technical errors. Search text and model files are excluded. Clearing browser history does not delete reports already shared with the local server.';panel.append(note);
const status=document.createElement('p');status.setAttribute('role','status');panel.append(status);
const syncStatus=document.createElement('p');panel.append(syncStatus);
const choose=document.createElement('select');choose.style.maxWidth='100%';choose.setAttribute('aria-label','Diagnostic session');panel.append(choose);
function refresh(){
  const selected=choose.value;
  choose.replaceChildren(...diagnostics.history().map(bundle=>{
    const option=document.createElement('option');option.value=bundle.session_id;option.textContent=`${bundle.app} · ${bundle.started_at} · ${bundle.session_id===diagnostics.sessionId?'current session':bundle.session_id}`;return option;
  }));
  if([...choose.options].some(o=>o.value===selected))choose.value=selected;
}
function chosen(){capture('report.export');return diagnostics.history().find(b=>b.session_id===choose.value)??diagnostics.bundle();}
function button(label,fn){const control=document.createElement('button');control.type='button';control.textContent=label;control.style.margin='6px';control.addEventListener('click',async()=>{try{await fn();}catch(error){status.textContent=safeText(error.message);}});panel.append(control);return control;}
button('Download diagnostics',()=>{
  const bundle=chosen(),url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=`car-incident-${bundle.session_id}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
button('Copy diagnostics',async()=>{await navigator.clipboard.writeText(JSON.stringify(chosen(),null,2));status.textContent='Diagnostics copied.';});
button('Refresh sessions',refresh);
button('Replay viewer state',async()=>{
  const bundle=diagnostics.history().find(b=>b.session_id===choose.value);
  if(!bundle)throw Error('Choose a saved incident first.');
  if(!diagnostics.restore)throw Error('The viewer has not finished starting. Export the report to diagnose its startup failure.');
  await diagnostics.restore(bundle);status.textContent='Viewer state restored using the currently served assets. Use the CLI for recorded network outcomes.';
});
const imported=document.createElement('input');imported.type='file';imported.accept='.json,application/json';imported.setAttribute('aria-label','Import diagnostics for viewer replay');
imported.addEventListener('change',async()=>{
  try {
    const file=imported.files[0];if(!file)return;if(file.size>524288)throw Error('Report exceeds 512 KiB.');
    const bundle=JSON.parse(await file.text());if(!diagnostics.restore)throw Error('The viewer has not finished starting.');await diagnostics.restore(bundle);
    status.textContent='Imported viewer state restored. Asset bytes and network outcomes are not imported.';
  }catch(error){status.textContent=safeText(error.message);}
});panel.append(imported);
button('Clear saved diagnostics',()=>{diagnostics.clear();refresh();status.textContent='Saved diagnostics cleared. Recording continues if enabled.';});
function checkbox(label,checked,fn){const wrap=document.createElement('label'),control=document.createElement('input');control.type='checkbox';control.checked=checked;wrap.append(control,document.createTextNode(label));panel.append(wrap);control.addEventListener('change',()=>{fn(control.checked);savePrefs();updateStatus();});return control;}
checkbox(' Save diagnostic history',diagnostics.enabled,value=>{diagnostics.setEnabled(value);refresh();});
const sharingControl=checkbox(' Share automatically with this local library server',sharing,value=>{sharing=value;queueUpload();});
sharingControl.disabled=!local;
button('Share selected incident with local server',async()=>{
  if(!bridge)throw Error('Start tools/serve_library.py, or download the report and import it with tools/diagnostics.py.');
  await postBundle(chosen());status.textContent='Selected incident is available to local tools.';
});
function updateStatus(){
  if(!diagnostics.enabled)status.textContent='Recording disabled; saved history cleared.';
  else if(diagnostics.storageError)status.textContent='Browser storage unavailable. Only this live session can be exported; history will not survive reload.';
  else if(!bridge)status.textContent='Saved on this browser. Download a report to share it; local tools cannot read browser storage directly.';
  else status.textContent=sharing?'Saved on this browser and shared with the local library server.':'Saved on this browser. Automatic local sharing is paused.';
}
panel.addEventListener('toggle',()=>{if(panel.open){refresh();updateStatus();}});
document.body.append(panel);refresh();updateStatus();
if(local)fetch('/api/diagnostics/capabilities').then(response=>response.ok?response.json():null).then(async result=>{
  if(result?.schema!==1)return;bridge=true;diagnostics.identify(result.identity);
  // A tab can close before its upload timer fires. Recover its saved report on reload.
  if(sharing&&diagnostics.enabled)for(const bundle of diagnostics.history())if(bundle.session_id!==diagnostics.sessionId)await postBundle(bundle);
  queueUpload();
}).catch(()=>{/* Static servers have no collector. Download/export remains available. */});
