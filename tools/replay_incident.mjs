#!/usr/bin/env node
// Offline load replay: executes the shipped fetch/GLB parser and load timeline.
// GPU, texture decoding, render appearance and arbitrary runtime errors need browser replay.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {createDiagnostics,createLoadTimeline} from '../dealership/diagnostics.mjs';
import {fetchModel,readGLB} from '../dealership/model-load.mjs';

const root=fileURLToPath(new URL('../dealership/',import.meta.url));
const hash=buffer=>createHash('sha256').update(buffer).digest('hex');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settle(task) {
  let timer;
  try {await Promise.race([task,new Promise((resolve,reject)=>{timer=setTimeout(()=>reject(Error('Recorded terminal event has no settled fetch outcome')),2000);})]);}
  finally{clearTimeout(timer);}
}
export async function replayIncident(bundle,{readAsset,allowVersionMismatch=false,timelineFactory=createLoadTimeline}={}) {
  if(bundle?.schema!==1||!Array.isArray(bundle.events)||!bundle.events.length)throw Error('Expected a nonempty schema-1 incident');
  const events=bundle.events,attempts=new Map(),requests=new Map(),results=[];
  let previous=0,visible=null;
  for(const e of events){if(!Number.isInteger(e.seq)||e.seq<=previous)throw Error('Incident event order is invalid');previous=e.seq;}
  if(!events.some(e=>e.kind==='load.begin'))throw Error('No retained load start; replay requires a complete load timeline');
  const diagnostics=createDiagnostics({app:bundle.app,storage:()=>null});
  const timeline=timelineFactory(diagnostics),nativeFetch=globalThis.fetch,nativeDiagnostics=globalThis.__carDiagnostics;
  globalThis.__carDiagnostics=diagnostics;
  function bytesFor(resource,expected) {
    let bytes;
    if(readAsset)bytes=readAsset(resource);
    else {
      let relative=resource;
      if(/^https?:/.test(resource)) {
        const assetBase=bundle.identity?.asset_base;
        if(!assetBase||!resource.startsWith(assetBase))throw Error('Resource is outside the recorded asset base');
        relative=resource.slice(assetBase.length);
      }
      relative=decodeURIComponent(relative.split(/[?#]/)[0]);
      const resolved=fs.realpathSync(path.resolve(root,relative));
      if(!resolved.startsWith(root)||!resolved.endsWith('.glb'))throw Error('Replay resource is outside the GLB corpus');
      bytes=fs.readFileSync(resolved);
    }
    const buffer=Buffer.from(bytes);
    if(!expected&&!allowVersionMismatch)throw Error('No recorded asset hash; exact byte replay is unavailable');
    if(expected&&hash(buffer)!==expected&&!allowVersionMismatch)throw Error('Recorded asset hash differs; restore that asset or explicitly allow version mismatch');
    return buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength);
  }
  globalThis.fetch=(resource,{signal})=>new Promise((resolve,reject)=>{
    const request=requests.get(resource);if(!request){reject(Error('Unrecorded network request'));return;}
    request.headers=resolve;request.reject=reject;
    signal.addEventListener('abort',()=>{reject(new DOMException('Recorded cancellation','AbortError'));request.rejectBody?.(new DOMException('Recorded cancellation','AbortError'));},{once:true});
  });
  try {
    for(const event of events) {
      const data=event.data??{},id=data.load_id;
      if(event.kind==='load.begin') {
        const controller=new AbortController(),attempt=timeline.begin(data.car,controller.signal);
        attempts.set(id,{attempt,controller,car:data.car});
      } else if(event.kind==='fetch.begin') {
        const item=attempts.get(id);if(!item)throw Error('Retained fetch has no load start');
        if(item.task)throw Error('Multiple primary fetches in one attempt require browser reproduction');
        const request={resource:data.resource};requests.set(data.resource,request);item.request=request;
        const timeout=events.some(e=>e.kind==='fetch.timeout'&&e.data?.load_id===id)?20:60000;
        item.task=(async()=>{
          try {
            const buffer=await fetchModel(data.resource,item.controller.signal,timeout,item.attempt);
            readGLB(buffer);
            const published=item.attempt.publish({},()=>{visible=item.car;});
            results.push({load_id:id,outcome:published?'success':'stale',car:item.car});
          } catch(error){item.attempt.fail(error);results.push({load_id:id,outcome:item.controller.signal.aborted?'cancelled':'failure',message:error.message});}
        })();
      } else if(event.kind==='fetch.headers') {
        const request=attempts.get(id)?.request;if(!request?.headers)throw Error('Response has no recorded request');
        request.headers({ok:data.status>=200&&data.status<300,status:data.status,arrayBuffer:()=>new Promise((resolve,reject)=>{request.body=resolve;request.rejectBody=reject;})});
      } else if(event.kind==='fetch.success') {
        const request=attempts.get(id)?.request;if(!request?.body)throw Error('Body has no recorded successful headers');
        request.complete=true;
        request.body(bytesFor(request.resource,data.sha256));
      } else if(event.kind==='fetch.failure') {
        const request=attempts.get(id)?.request;if(request)request.complete=true;(request?.rejectBody??request?.reject)?.(Error(data.error?.message??'Recorded network failure'));
      } else if(event.kind==='fetch.timeout') {
        await settle(attempts.get(id)?.task);
      } else if(event.kind==='load.cancelled') {
        attempts.get(id)?.controller.abort();
      } else if(['load.success','load.failure','load.stale'].includes(event.kind)&&attempts.get(id)?.task) {
        await settle(attempts.get(id).task);
      }
      await tick();
    }
    for(const [id,item] of attempts) {
      if(item.task&&!results.some(r=>r.load_id===id)) {
        item.controller.abort();throw Error('Trace ends before all responses settle');
      }
    }
    await Promise.all([...attempts.values()].map(item=>item.task));
    const failures=events.filter(e=>e.kind==='load.failure');
    const reproduced=failures.map(e=>({load_id:e.data.load_id,reproduced:results.some(r=>r.load_id===e.data.load_id&&r.outcome==='failure'&&(!e.data.error?.message||r.message===e.data.error.message))}));
    const unrepresented=events.filter(e=>['runtime.error','runtime.rejection','webglcontextlost'].includes(e.kind)).map(e=>e.kind);
    const expectedVisible=[...events].reverse().find(e=>e.kind==='load.success'&&e.data?.preview!==false)?.data?.load_id;
    const expectedCar=attempts.get(expectedVisible)?.car??null;
    const staleViolation=visible!==expectedCar;
    return {schema:1,session_id:bundle.session_id,recorded_state:bundle.state,results,visible,expected_visible:expectedCar,
      reproduced,unrepresented,ok:!staleViolation&&!unrepresented.length&&reproduced.every(r=>r.reproduced),asset_version_override:allowVersionMismatch,
      events:diagnostics.bundle().events,
      claim_limits:['Offline replay covers primary fetch outcomes, GLB parsing and latest-selection publication.','Camera, paint, rendering, context loss and texture decode require Replay viewer state in the actual browser.','Recorded assets must be available locally; this report contains no historical response bodies.']};
  } finally {for(const item of attempts.values())item.controller.abort();globalThis.fetch=nativeFetch;globalThis.__carDiagnostics=nativeDiagnostics;}
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1])) {
  try {
    const args=process.argv.slice(2),input=args.find(arg=>!arg.startsWith('--'));
    if(!input)throw Error('Usage: node tools/replay_incident.mjs incident.json [--allow-version-mismatch]');
    const report=await replayIncident(JSON.parse(fs.readFileSync(input,'utf8')),{allowVersionMismatch:args.includes('--allow-version-mismatch')});
    process.stdout.write(JSON.stringify(report,null,2)+'\n');process.exitCode=report.ok?0:1;
  }catch(error){process.stderr.write(error.message+'\n');process.exitCode=2;}
}
