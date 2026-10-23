// Metadata only: no model bytes, search text, provider envelopes or credentials.
export const DIAGNOSTICS_KEY='carmodels:diagnostics:v1';
export const LIMITS=Object.freeze({events:256,sessions:8,bytes:524288,days:7});
const clone=value=>JSON.parse(JSON.stringify(value));
export function safeText(value,limit=1000) {
  return String(value??'').replace(/https?:\/\/[^\s)]+/gi,url=>{
    try {const parsed=new URL(url);return parsed.origin+parsed.pathname;}catch{return '[url]';}
  }).replace(/(?:Bearer\s+|(?:api[_-]?key|authorization|token|password|secret)\s*[=:]\s*)[^\s,;]+/gi,'[redacted]')
    .replace(/\bsk-[\w-]+/g,'[redacted]').replace(/[?][^\s)]+/g,'?[redacted]').slice(0,limit);
}
export function clean(value,depth=0) {
  if(depth>7)return null;
  if(typeof value==='string')return safeText(value);
  if(typeof value==='number')return Number.isFinite(value)?value:null;
  if(value===null||typeof value==='boolean')return value;
  if(Array.isArray(value))return value.slice(0,40).map(v=>clean(v,depth+1));
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).slice(0,60)
    .filter(([key])=>!/query|search|token|secret|password|authorization|raw_response|cookie|payload/i.test(key))
    .map(([key,v])=>[safeText(key,64),clean(v,depth+1)]));
  return null;
}
export function createDiagnostics({app,storage=()=>globalThis.localStorage,now=()=>Date.now(),
  uuid=()=>globalThis.crypto?.randomUUID?.()??'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const n=Math.floor(Math.random()*16);return (c==='x'?n:(n&3)|8).toString(16);}),identity={},limits=LIMITS}={}) {
  const started=now(), sessionId=uuid();let seq=0,load=0,enabled=true,storageError=false;
  let state={},sink=null,stored=[];
  const current={schema:1,session_id:sessionId,app,started_at:new Date(started).toISOString(),
    updated_at:new Date(started).toISOString(),identity:clean(identity),environment:{},state:{},events:[]};
  const read=()=>{try {const raw=storage()?.getItem(DIAGNOSTICS_KEY);if(raw&&raw.length>limits.bytes)return [];return raw?JSON.parse(raw):[];}catch{storageError=true;return [];}};
  stored=read();if(!Array.isArray(stored))stored=[];
  function retained() {
    // Re-read before merging so different viewer tabs do not overwrite entire sessions.
    const disk=read();const merged=new Map();
    for(const item of [...stored,...(Array.isArray(disk)?disk:[]),current]) {
      if(item?.schema===1&&Array.isArray(item.events)&&Date.parse(item.updated_at)>=now()-limits.days*86400000)merged.set(item.session_id,item);
    }
    const list=[...merged.values()].sort((a,b)=>Date.parse(b.updated_at)-Date.parse(a.updated_at)).slice(0,limits.sessions);
    while(new TextEncoder().encode(JSON.stringify(list)).length>limits.bytes) {
      if(list.length>1)list.pop();else if(current.events.length>1)current.events.shift();else break;
    }
    return list;
  }
  function flush() {
    if(!enabled)return;
    stored=retained();
    try {storage()?.setItem(DIAGNOSTICS_KEY,JSON.stringify(stored));}catch{storageError=true;}
    // The sink schedules local upload; recording never waits on a server.
    try {sink?.(clone(current));}catch{/* Diagnostics cannot interrupt rendering. */}
  }
  function record(kind,data={}) {
    if(!enabled)return null;
    current.updated_at=new Date(now()).toISOString();current.state=clone(state);
    let cleaned=clean(data);
    if(JSON.stringify(cleaned).length>16384)cleaned={detail:'Event metadata exceeded 16 KiB; omitted.'};
    const event={seq:++seq,at:current.updated_at,elapsed_ms:Math.max(0,now()-started),kind:safeText(kind,64),data:cleaned};
    current.events.push(event);while(current.events.length>limits.events)current.events.shift();flush();return event;
  }
  const api={
    sessionId,record,flush,
    snapshot(value,reason='state.change'){const next=clean(value);state=JSON.stringify(next).length<=16384?next:{detail:'State exceeded 16 KiB; omitted.'};record(reason,{state});},
    identify(value){Object.assign(current.identity,clean(value));record('identity');},
    environment(value){Object.assign(current.environment,clean(value));record('environment');},
    beginLoad(car){const id=String(++load);record('load.begin',{load_id:id,car});return id;},
    phase(loadId,phase,data={}){record('load.phase',{load_id:loadId,phase,...data});},
    endLoad(loadId,outcome,data={}){record('load.'+outcome,{load_id:loadId,...data});},
    bundle(){return clone(current);},
    history(){return clone(retained());},
    setSink(value){sink=value;},
    get enabled(){return enabled;},
    get storageError(){return storageError;},
    clear(){stored=[];current.events=[];try{storage()?.removeItem(DIAGNOSTICS_KEY);}catch{storageError=true;}},
    setEnabled(value){enabled=!!value;if(!enabled)api.clear();else record('session.resume');},
  };
  record('session.start');return api;
}

// One load attempt is shared by the actual viewers and the offline replay harness.
// An obsolete attempt can finish, but must never publish itself as visible.
export function createLoadTimeline(diagnostics) {
  let active=null;
  return {
    begin(car,signal){
      if(active&&!active.finished)active.end('cancelled',{reason:'superseded'});
      const id=diagnostics.beginLoad(car);
      const attempt={id,signal,finished:false,
        phase(name,data){diagnostics.phase(id,name,data);},
        current(){return active===attempt&&!signal?.aborted;},
        end(outcome,data={}){
          if(attempt.finished)return false;
          attempt.finished=true;signal?.removeEventListener('abort',abort);
          diagnostics.endLoad(id,outcome,data);return true;
        },
        publish(data={},commit=()=>{}){
          if(!attempt.current()){diagnostics.record('load.stale',{load_id:id});return false;}
          commit();
          attempt.end('success',data);return true;
        },
        fail(error){return attempt.end(signal?.aborted?'cancelled':'failure',{error:{name:error?.name,message:error?.message,stack:error?.stack}});},
      };
      const abort=()=>attempt.end('cancelled',{reason:'abort'});
      active=attempt;signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)abort();
      return attempt;
    },
  };
}
