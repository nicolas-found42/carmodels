// Native serialized inputs and bounded specialized EE binders. All lighting,
// gameplay state and generated images are explicit caller inputs.
import {nativeVUAdd as add,nativeVUMultiply as mul} from './mc3-vehicle-math.mjs';
const bits=new DataView(new ArrayBuffer(4));
function need(value,message){if(!value)throw Error(message);}
function word(value){need(Number.isInteger(value)&&value>=0&&value<=0xffffffff,'Invalid native input word.');return value;}
export function nativeWordFloat(value){bits.setUint32(0,word(value),true);const result=bits.getFloat32(0,true);need(Number.isFinite(result),'Nonfinite native input.');return result;}
function vector(value,size,label){need(Array.isArray(value)&&value.length===size&&value.every(Number.isFinite),'Missing native '+label+'.');return value.map(Math.fround);}
function u32vector(value,size,label){need(Array.isArray(value)&&value.length===size,'Missing native '+label+'.');return value.map(word);}
function bytes(value){return [value&255,(value>>>8)&255,(value>>>16)&255,value>>>24];}
function parameterByte(node,offset){const v=node.parameter_words?.[(offset-48)>>>2];return bytes(word(v))[offset&3];}
function parameterFloat(node,offset){return nativeWordFloat(node.parameter_words?.[(offset-48)>>>2]);}
function inputWord(words,index){need(Number.isInteger(index)&&index>=0&&index<words.length,'Unresolved native parameter index.');return word(words[index]);}
function inputFloat(words,index){return nativeWordFloat(inputWord(words,index));}
function cvt(value){need(Number.isFinite(value)&&value>=-2147483648&&value<2147483648,'Native CVT.W outside bounded profile.');return Math.trunc(value);}
function rgba(values){const result=values.map(v=>cvt(mul(v,255))&255);result[3]=(result[3]+1)>>>1;return result;}
function rgb(values){return [...values.map(v=>cvt(mul(v,255))&255),128];}
function towardWhite(ambient,factor){return ambient.map(value=>add(value,mul(add(1,-value),factor)));}

export function nativeVehicleInputWords(table,overrides={}){
 const rows=Array.isArray(table)?table:table?.inputs;
 need(Array.isArray(rows),'Missing native material input table.');
 const words=rows.map((row,index)=>{need(row.index===index&&typeof row.name==='string','Invalid native input order.');return word(row.word);});
 for(const [name,value] of Object.entries(overrides)){
  const index=rows.findIndex(row=>row.name===name);need(index>=0,'Unknown native input override: '+name);words[index]=word(value);
 }
 return words;
}

// State values are retained as native command selectors. The GS stage must
// interpret them; absent commands inherit the explicit current state.
export function nativeVehiclePassState(commands,inherited){
 need(inherited&&typeof inherited==='object','Missing native inherited render state.');
 const state={...inherited};
 for(const command of commands){need(Number.isInteger(command.command)&&command.command>=0&&command.command<64,'Invalid native state command.');state[command.command]=word(command.value);}
 return state;
}

export function bindNativeVehicleMaterial(graph,table,context){
 need(context&&typeof context==='object','Missing native binder context.');
 const words=nativeVehicleInputWords(table,context.inputOverrides),path=[];
 let node=graph?.root??graph,tint=null;
 const seen=new Set();
 while(node?.kind==='composite'){
  need(!seen.has(node)&&seen.size<64,'Native composite cycle.');seen.add(node);
  let selected;
  if([0x3b6330,0x3b6540,0x3bad30].includes(node.draw_address))selected=inputWord(words,parameterByte(node,60));
  else if(node.draw_address===0x3b6170)selected=word(node.selected);
  else return {supported:false,reason:'Unrecovered composite draw method.',node,path};
  need(Array.isArray(node.children)&&selected<node.children.length,'Native composite selector outside children.');
  if(node.draw_address===0x3bad30){
   const values=[61,62,63,64].map(offset=>inputFloat(words,parameterByte(node,offset)));
   // Original SQ writes these parameter vectors to both children before selection.
   tint=selected===0?[...values.slice(0,3),Math.fround(.8)]:selected===1?values:null;
  }
  path.push({source_offset:node.source_offset,selected});node=node.children[selected];
 }
 need(node?.kind==='material','Native graph does not select a drawable material.');
 const result={supported:true,node,path,vu:{},passes:[],claimLimits:['Bounded native binder and ordered pass selectors; generated texture pixels and complete engine cache/epilogues are separate.','Explicit source/default input words and caller state; no inferred gameplay updates.']};
 let state={...context.state};
 need(context.state&&Object.hasOwn(context.state,8),'Missing native inherited RGBA state.');
 let material=null,ambient=null,postRGBA=null;
 const ambientInput=()=>vector(context.ambient,3,'ambient RGB');
 const indices=(offset,count)=>Array.from({length:count},(_,i)=>parameterByte(node,offset+i));
 switch(node.bind_address){
  case 0x3b6928:
   material=[255,255,255,128];
   result.vu[53]=node.paint_input_indices.map(i=>inputFloat(words,i));
   result.vu40Words=[word(context.paintControlWord),0,0,word(context.paintControlByte)];
   need(context.paintControlByte<=255,'Native paint control byte outside range.');
   result.vu43To50Words=u32vector(context.paintLightWords,32,'paint lighting words');
   break;
  case 0x3b7b38:{
   const i=node.window_input_indices;need(Array.isArray(i)&&i.length===9,'Missing native window indices.');
   material=rgba(i.slice(0,4).map(n=>inputFloat(words,n)));
   result.vu[52]=[127,127,127,255];
   result.vu[53]=[inputFloat(words,i[4]),mul(inputFloat(words,i[5]),.5),mul(inputFloat(words,i[6]),.5),inputFloat(words,i[7])];
   result.vu40Words=[3,0,0,0];
   result.windowTexture=node.window_texture_variants[inputWord(words,i[8])===0?0:1];
   break;
  }
  case 0x3b7408:{
   const i=node.glass_light_indices;need(Array.isArray(i)&&i.length===2,'Missing native glass light indices.');
   const first=mul(inputFloat(words,i[0]),.5),mode=node.glass_light_mode;
   const factor=mode===1?first:mode===2?add(first,mul(inputFloat(words,i[1]),.5)):0;
   ambient=towardWhite(ambientInput(),factor);
   material=rgba(node.glass_rgba_words.map(nativeWordFloat));
   result.restoreRGBA=[255,255,255,128];
   result.vu[53]=vector(context.generationParameters,4,'generation parameters');
   break;
  }
  case 0x3bc280:{
   const authored=parameterByte(node,84)!==0,headlight=parameterByte(node,85)!==0;
   const factor=headlight?inputFloat(words,node.parameter_words[8]):authored?parameterFloat(node,60):inputFloat(words,parameterByte(node,67));
   ambient=towardWhite(ambientInput(),factor);result.vu[53]=[Math.fround(.8),1,1,1];
   let color=tint?.slice(0,3)??(authored?[48,52,56].map(offset=>parameterFloat(node,offset)):indices(64,3).map(i=>inputFloat(words,i)));
   if(headlight){const light=vector(context.headlightColor,3,'headlight color');color=color.map((v,i)=>add(v,mul(add(light[i],-v),factor)));}
   postRGBA=rgb(color);break;
  }
  case 0x3bce58:{
   const authored=parameterByte(node,64)!==0;
   const factor=authored?parameterFloat(node,60):inputFloat(words,parameterByte(node,68));
   ambient=towardWhite(ambientInput(),factor);result.vu[53]=[Math.fround(.8),1,1,1];
   const color=tint?.slice(0,3)??(authored?[48,52,56].map(offset=>parameterFloat(node,offset)):indices(65,3).map(i=>inputFloat(words,i)));
   postRGBA=rgb(color);break;
  }
  case 0x3b8728:{
   material=[255,255,255,128];const scale=parameterFloat(node,48);
   result.vu[52]=[scale,scale>Math.fround(1.1)?mul(scale,.5):0,0,0];
   result.vu[53]=[Math.fround(.8),Math.fround(.1),Math.fround(.8),1];
   result.textureAlpha=[10,0x58,0x44];break;
  }
  case 0x3b8fe0:
   state[3]=inputWord(words,parameterByte(node,52))===0?0:0x10048;state[7]=0;
   material=rgba(indices(48,4).map(i=>inputFloat(words,i)));break;
  case 0x3bb328:
   result.vu[53]=vector(context.generationParameters,4,'generation parameters');break;
  case 0x2b2168: case 0x2b1f90:
   if(node.draw_address===0x3bae90){
    material=rgba(tint??[48,52,56,60].map(offset=>parameterFloat(node,offset)));
    result.restoreRGBA=[255,255,255,128];
   }else if(node.draw_address===0x3bb070){
    const color=tint??[48,52,56,60].map(offset=>parameterFloat(node,offset));
    material=rgb(color.slice(0,3));ambient=towardWhite(ambientInput(),color[3]);
    const mode=word(context.decalChromeDepthMode)|0;state[1]=Math.min(mode,1)>>>0;
    result.vu[53]=vector(context.generationParameters,4,'generation parameters');
    result.restoreRGBA=[255,255,255,128];
   }else if(node.draw_address===0x3b7040){
    result.vu[53]=indices(48,4).map(i=>inputFloat(words,i));
   }else if(node.draw_address!==0x2b21a8)return {supported:false,reason:'Unrecovered specialized material draw method.',node,path};
   break;
  default:
   return {supported:false,reason:'Unrecovered specialized material binder.',node,path};
 }
 if(material)state[8]=(material[0]|material[1]<<8|material[2]<<16|material[3]<<24)>>>0;
 for(const pass of node.passes){
  state=nativeVehiclePassState(pass.state,state);
  const current=postRGBA??bytes(word(state[8]));
  result.passes.push({program:pass.program,state:{...state},textures:pass.textures,materialRGBA:current});
 }
 if(postRGBA)state[8]=(postRGBA[0]|postRGBA[1]<<8|postRGBA[2]<<16|postRGBA[3]<<24)>>>0;
 result.state=state;result.materialRGBA=postRGBA??bytes(word(state[8]));
 if(result.restoreRGBA)result.state={...state,8:0x80ffffff};
 if(ambient)result.ambient=ambient;
 return result;
}
