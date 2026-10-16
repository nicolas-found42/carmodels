// Shared explicit execution boundary: retained VIF -> original VU program ->
// native GIF -> bounded software GS. Actor uniforms, original texture images,
// material dispatch and render targets must already be source-bound by caller.
import {createNativeVUState,runNativeVU} from './mc3-vu-interpreter.mjs';
import {runNativeVIF} from './mc3-vif-decoder.mjs';
import {decodeNativeVehicleGIF,renderNativeVehicleGIF} from './mc3-vehicle-gif.mjs';
import {renderNativeVehicleVRAMGIF} from './mc3-vehicle-vram.mjs';
function need(value,message){if(!value)throw Error(message);}

// Each call owns its execution state and output. A rejected program or resource
// cannot publish a partially rendered frame or corrupt the caller's context.
export function executeNativeVehicleTransfers({vu,vif,transfers,initialGSRegisters,maxSteps=100000,allowImages=false}) {
 need(Array.isArray(transfers)&&transfers.length>0&&transfers.every(bytes=>bytes instanceof Uint8Array),
  'Explicit original VIF transfers are required.');
 need(Number.isSafeInteger(maxSteps)&&maxSteps>0,'Invalid native pipeline instruction budget.');
 need(vif&&vif.row instanceof Uint32Array&&vif.row.length===4&&vif.col instanceof Uint32Array&&vif.col.length===4,
  'Explicit native VIF row/column state is required.');
 const state={row:vif.row.slice(),col:vif.col.slice()};
 for(const [key,max] of Object.entries({cl:255,wl:255,mode:3,mask:0xffffffff,base:1023,offset:1023,
  tops:2046,top:1023,itops:1023,itop:1023})) {
  need(Number.isInteger(vif[key])&&vif[key]>=0&&vif[key]<=max,'Invalid native VIF '+key+'.');state[key]=vif[key];
 }
 need(typeof vif.dbf==='boolean','Explicit native VIF double-buffer flag is required.');state.dbf=vif.dbf;
 const vuState=createNativeVUState(vu);
 state.memory=vuState.memory;state.microcode=vuState.micro;
 const chunks=[],calls=[];
 let nextPC=null;
 for(const bytes of transfers)runNativeVIF(bytes,state,{
  onDirect(data){chunks.push(data.slice());},
  onMicro(call) {
   const pc=call.pc??nextPC;
   need(pc!==null,'Native MSCNT has no prior VU continuation.');
   vuState.top=call.top;vuState.itop=call.itop;
   const startCycle=vuState.cycle;
   const result=runNativeVU(vuState,pc,{maxSteps,onGIF:data=>chunks.push(data.slice())});
   nextPC=result.pc;
   calls.push({pc,top:call.top,itop:call.itop,startCycle,endCycle:vuState.cycle,steps:result.steps});
  }
 });
 const decoded=decodeNativeVehicleGIF(chunks,{initialRegisters:initialGSRegisters,allowImages});
 return {vu:vuState,vif:state,gifChunks:chunks,decoded,calls};
}

export function executeNativeVehiclePipeline(context) {
 const execution=executeNativeVehicleTransfers(context);
 need(!execution.decoded.operations.some(op=>op.kind==='image'),'Native IMAGE transfers require the VRAM pipeline.');
 const {target,resolveTexture}=context;
 need(target?.rgba instanceof Uint8Array&&(target?.depth instanceof Uint16Array||target?.depth instanceof Uint32Array),'Explicit native pipeline target is required.');
 const output={...target,rgba:target.rgba.slice(),depth:target.depth.slice()};
 const stats=renderNativeVehicleGIF(execution.decoded,{target:output,resolveTexture});
 return {...execution,target:output,stats};
}

// Generated paint has literal IMAGE uploads and CLUT loads between draws.
// The separate VRAM consumer admits only the recovered no-depth-access stage.
export function executeNativeVehicleVRAMPipeline(context) {
 const execution=executeNativeVehicleTransfers({...context,allowImages:true});
 return {...execution,...renderNativeVehicleVRAMGIF(execution.decoded,context)};
}
