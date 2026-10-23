// Share the diagnostics state vocabulary, with an explicit, bounded URL envelope.
export const INSPECTION_PARAM='inspection';
export const MAX_INSPECTION_BYTES=8192;
export const PILOT=Object.freeze({game:'gran-turismo-4',car:'gran-turismo-4/acra0001'});
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'&&value.length<=256;
const vector=value=>Array.isArray(value)&&value.length===3&&value.every(Number.isFinite);
const byteLength=value=>new TextEncoder().encode(new URLSearchParams({[INSPECTION_PARAM]:value}).toString().slice(INSPECTION_PARAM.length+1)).length;
const available=(values,value)=>values===undefined||values.some(option=>typeof option==='string'?option===value:!option.disabled&&option.value===value);

export function decodeInspectionState(raw,{cars,records,variants,paintSession}={}) {
  const state={},issues=[],reject=(field,reason)=>issues.push({field,reason});
  if(raw===null||raw===undefined)return {present:false,state,issues};
  const result=()=>({present:true,state,issues});
  if(typeof raw!=='string'||byteLength(raw)>MAX_INSPECTION_BYTES){reject('snapshot','Inspection snapshot exceeds the 8 KiB URL limit.');return result();}
  let value;
  try{value=JSON.parse(raw);}catch{reject('snapshot','Inspection snapshot is not valid JSON.');return result();}
  if(!object(value)||value.version!==1){reject('version','Unsupported inspection snapshot version; use version 1.');return result();}
  if(value.game!==PILOT.game||value.car!==PILOT.car||cars&&!cars.some(car=>car.id===value.car&&car.game===value.game)){
    reject('car','Inspection car is unavailable; this snapshot pilot supports gran-turismo-4/acra0001 only.');return result();
  }
  Object.assign(state,PILOT);
  for(const [field,options] of [['record',records],['variant',variants]]) {
    if(!(field in value))continue;
    if(text(value[field])&&available(options,value[field]))state[field]=value[field];
    else reject(field,`Unsupported inspection ${field==='record'?'geometry':'preset'}; using the default.`);
  }
  if('controls' in value){
    if(!object(value.controls))reject('controls','Invalid inspection presentation controls; using defaults.');
    else {
      const controls={};
      for(const field of ['textures','sharp','wire','flip','game-shading','presentation']){
        if(!(field in value.controls))continue;
        const saved=value.controls[field];
        if(field==='presentation'?['original','enhanced'].includes(saved):typeof saved==='boolean')controls[field]=saved;
        else reject(`controls.${field}`,`Invalid inspection ${field}; using the default.`);
      }
      if(Object.keys(controls).length)state.controls=controls;
    }
  }
  if('camera' in value){
    const camera=value.camera;
    if(!object(camera)||!vector(camera.position)||!vector(camera.target)||!Number.isFinite(camera.near)||!Number.isFinite(camera.far)||!Number.isFinite(camera.fov)||!(camera.near>0&&camera.far>camera.near&&camera.fov>0&&camera.fov<180))
      reject('camera','Invalid inspection camera: finite position/target and valid clipping/FOV bounds are required; using the default.');
    else state.camera={position:[...camera.position],target:[...camera.target],near:camera.near,far:camera.far,fov:camera.fov};
  }
  if('paint' in value){
    const paint=value.paint;
    if(!object(paint)||paint.schema!==1||!object(paint.channels))reject('paint','Invalid inspection paint; using the default.');
    else {
      const output={schema:1,preset:null,presetName:null,channels:{}};
      const validPreset=paint.preset===null&&paint.presetName===null||Number.isInteger(paint.preset)&&paint.preset>=0&&text(paint.presetName)&&(!paintSession||paintSession.presets[paint.preset]?.name===paint.presetName);
      if(validPreset){output.preset=paint.preset;output.presetName=paint.presetName;}
      else reject('paint.preset','Unsupported inspection paint preset; using the default.');
      for(const [id,saved] of Object.entries(paint.channels)){
        const channel=paintSession?.channels.find(channel=>channel.id===id);
        if(!/^[a-z0-9][a-z0-9_-]{0,80}$/i.test(id)||!object(saved)||paintSession&&!channel){reject('paint.channels','Unsupported inspection paint channel; using its default.');continue;}
        const clean={};
        for(const field of ['color','finish']){
          if(!(field in saved))continue;
          const item=saved[field];
          const known=!paintSession||(field==='color'?paintSession.colors.some(color=>JSON.stringify([color.source,color.id])===item):channel.finishes.some(finish=>finish.id===item));
          if(item===null||text(item)&&known)clean[field]=item;
          else reject(`paint.channels.${id}.${field}`,`Unsupported inspection paint ${field}; using its default.`);
        }
        if(Object.keys(clean).length)output.channels[id]=clean;
      }
      state.paint=output;
    }
  }
  // The selector and paint session describe the same native preset. A malformed
  // duplicate must not restore a rejected selection through the other path.
  if(state.paint&&'variant' in value){
    const expected=state.paint.preset===null?'':String(state.paint.preset);
    if(state.variant!==expected){
      reject('paint.preset','Inspection preset and paint selection disagree; using the default preset.');
      delete state.variant;state.paint.preset=null;state.paint.presetName=null;
    }
  }
  return result();
}

export function encodeInspectionState(state) {
  // Validation precedes JSON serialization so NaN/Infinity cannot become JSON null.
  const input={version:1};
  for(const key of ['game','car','record','variant','controls','camera','paint'])if(state[key]!==undefined)input[key]=state[key];
  if(input.camera&&(!vector(input.camera.position)||!vector(input.camera.target)||!['near','far','fov'].every(key=>Number.isFinite(input.camera[key]))))throw Error('Invalid inspection camera.');
  const decoded=decodeInspectionState(JSON.stringify(input));
  if(decoded.issues.length)throw Error(decoded.issues.map(issue=>issue.reason).join(' '));
  const raw=JSON.stringify({version:1,...decoded.state});
  if(byteLength(raw)>MAX_INSPECTION_BYTES)throw Error('Inspection snapshot exceeds the 8 KiB URL limit.');
  return raw;
}

export function inspectionURL(base,state) {
  const url=new URL(base);
  url.searchParams.set('game',state.game);url.searchParams.set('car',state.car);
  url.searchParams.set(INSPECTION_PARAM,encodeInspectionState(state));
  return url;
}
