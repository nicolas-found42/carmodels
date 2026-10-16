// PCSX2 v2.8.2/fd9d310 VIF1 dynamic-unpack profile. Raw 32-bit VU
// input, not the approximate geometry planes used for the GLB fallback.
const need=(v,m)=>{if(!v)throw Error(m);};
const sizes=[4,2,1,0,8,4,2,0,12,6,3,0,16,8,4,2];
export function createNativeVIFState() {
 return {memory:new Uint32Array(4096),microcode:new Uint32Array(4096),row:new Uint32Array(4),col:new Uint32Array(4),cl:1,wl:1,mode:0,mask:0,base:0,offset:0,tops:0,top:0,itops:0,itop:0,dbf:false};
}
// A complete, padded source transfer is required. Chunk scheduling/IRQs and DMA
// address resolution belong to the caller; this decoder never invents missing bytes.
export function unpackNativeVIF(bytes,state,word,commandOffset=0) {
 need(bytes instanceof Uint8Array&&state.memory instanceof Uint32Array&&state.memory.length===4096,'Invalid native VIF storage.');
 const kind=(word>>>24)&15,size=sizes[kind],count=(word>>>16)&255||256;
 need(size>0,'Unsupported native VIF UNPACK format.');
 const cl=state.cl,wl=state.wl||256,fill=cl<wl;
 need(Number.isInteger(cl)&&cl>=0&&cl<=255&&Number.isInteger(state.wl)&&state.wl>=0&&state.wl<=255,'Invalid native STCYCL.');
 const reads=fill?cl*Math.floor(count/wl)+Math.min(count%wl,cl):count;
 const consumed=(reads*size+3)&~3;
 need(bytes.length>=consumed,'Truncated native VIF UNPACK.');
 const start=((((word&1023)+((word&0x8000)?state.tops:0))&1023)*16);
 const length=Math.min(count*16+(fill?0:(Math.ceil(count/wl)-1)*(cl-wl)*16),65535);
 const fallback=start+length>16384,mode=state.mode&3,unsigned=!!(word&0x4000),masked=!!(word&0x10000000);
 const alignment=((commandOffset>>>2)&3)+1,aligned=kind===9?alignment:alignment&1;
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 let source=0,cycle=0,address=start,iteration=0;
 function component(offset,bits) {
  // Original unpack functions read ahead inside the padded incoming transfer.
  need(offset+bits/8<=bytes.length,'Native VIF read-ahead is missing.');
  if(bits===32)return view.getUint32(offset,true);
  return (bits===16?(unsigned?view.getUint16(offset,true):view.getInt16(offset,true)):(unsigned?view.getUint8(offset):view.getInt8(offset)))>>>0;
 }
 for(let i=0;i<count;i++) {
  const active=!fill||cycle<cl;
  if(!fallback&&active&&(kind===9||kind===10))iteration++;
  const bits=kind===15?16:32>>((word>>>24)&3),components=(kind>>>2)+1;
  let data;
  if(kind===15){const value=component(source,16);data=[(value&31)<<3,(value&992)>>>2,(value&31744)>>>7,(value&32768)>>>8];}
  else if(components===1){const value=component(source,bits);data=[value,value,value,value];}
  else if(components===2){const x=component(source,bits),y=component(source+bits/8,bits);data=[x,y,x,y];}
  else data=Array.from({length:4},(_,lane)=>component(source+lane*bits/8,bits));
  if(fallback&&mode===0) {
   if(kind===4||kind===8||kind===9||kind===10)data[3]=0;
  } else if(!fallback) {
   if(kind===4&&aligned)data[3]=0;
   if((kind===8||kind===10)&&iteration!==aligned)data[3]=0;
   if(kind===9&&(iteration&1)===0&&(((Math.floor(iteration/4)+1+(4-aligned))&3)===0))data[3]=0;
  }
  for(let lane=0;lane<4;lane++) {
   const destination=((address&16368)>>>2)+lane,selector=masked?(state.mask>>>(Math.min(cycle,3)*8+lane*2))&3:0;
   if(selector===3)continue;
   let value=selector===1?state.row[lane]:selector===2?state.col[Math.min(cycle,3)]:data[lane];
   if(selector===0&&kind!==15){if(mode===1||mode===2)value=(value+state.row[lane])>>>0;if(mode===2||mode===3)state.row[lane]=value;}
   state.memory[destination]=value;
  }
  address+=16;cycle++;
  if(fill){if(cycle<=cl)source+=size;else if(cycle===wl)cycle=0;}
  else {source+=size;if(cycle>=wl){address+=(cl-wl)*16;cycle=0;}}
  if(!fallback&&active){if(kind<=2)iteration=(iteration+1)&3;else if(kind>=4&&kind<=8)iteration=(iteration+1)&1;}
 }
 return {consumed,count,start,fallback};
}
export function runNativeVIF(bytes,state=createNativeVIFState(),callbacks={}) {
 need(bytes instanceof Uint8Array&&bytes.length%4===0,'Native VIF transfer must contain whole words.');
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let offset=0;
 function take(length){need(offset+length<=bytes.length,'Truncated native VIF command payload.');const data=bytes.subarray(offset,offset+length);offset+=length;return data;}
 while(offset<bytes.length){const commandOffset=offset,word=view.getUint32(offset,true),cmd=(word>>>24)&127,immediate=word&65535;offset+=4;
  callbacks.onCommand?.({offset:commandOffset,word,state});
  if(cmd>=0x60){callbacks.onUnpack?.({phase:'before',offset:commandOffset,word,data:bytes.subarray(offset),state});const result=unpackNativeVIF(bytes.subarray(offset),state,word,commandOffset);callbacks.onUnpack?.({phase:'after',offset:commandOffset,word,result,state});offset+=result.consumed;continue;}
  switch(cmd){
   case 0:case 6:case 7:case 0x10:case 0x11:case 0x13:break;
   case 1:state.cl=immediate&255;state.wl=immediate>>>8;break;
   case 2:state.offset=immediate&1023;state.dbf=false;state.tops=state.base;break;
   case 3:state.base=immediate&1023;break;
   case 4:state.itops=immediate&1023;break;
   case 5:state.mode=immediate&3;break;
   case 0x20:{const data=take(4);state.mask=new DataView(data.buffer,data.byteOffset,4).getUint32(0,true);break;}
   case 0x30:case 0x31:{const data=take(16),v=new DataView(data.buffer,data.byteOffset,16),target=cmd===0x30?state.row:state.col;for(let i=0;i<4;i++)target[i]=v.getUint32(i*4,true);break;}
   case 0x14:case 0x15:case 0x17:{state.itop=state.itops;state.top=state.tops&1023;state.tops=state.dbf?state.base:state.base+state.offset;state.dbf=!state.dbf;callbacks.onMicro?.({pc:cmd===0x17?null:immediate&2047,top:state.top,itop:state.itop,offset:commandOffset,command:cmd,state});break;}
   case 0x4a:{const count=(word>>>16)&255||256,data=take(count*8),v=new DataView(data.buffer,data.byteOffset,data.length);for(let i=0;i<count*2;i++)state.microcode[((immediate&2047)*2+i)&4095]=v.getUint32(i*4,true);break;}
   case 0x50:case 0x51:{const data=take((immediate||65536)*16);callbacks.onDirect?.(data,cmd===0x51);break;}
   default:throw Error('Unsupported native VIF command 0x'+cmd.toString(16));
  }
 }
 return state;
}
