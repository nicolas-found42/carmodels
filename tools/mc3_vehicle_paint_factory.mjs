// Tools-only native EE closure discovery. Full ELF input stays private; emitted
// source packs contain only observed instructions/read-before-write source bytes.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createNativeEEState,runNativeEE} from '../dealership/mc3-ee.mjs';
export const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const need=(ok,message)=>{if(!ok)throw Error(message);};
export function spans(flags){const rows=[];for(let i=0;i<flags.length;){if(!flags[i]){i++;continue;}const start=i;while(i<flags.length&&flags[i])i++;rows.push([start,i-start]);}return rows;}
export function memoryFootprint(pc,w,s){
 const op=w>>>26,rs=w>>>21&31,imm=w<<16>>16,address=(Number(s.gpr[rs]&0xffffffffn)+imm)>>>0;
 let size=0,read=false,write=false,aligned=address;
 if([32,36].includes(op)){size=1;read=true;}else if([33,37].includes(op)){size=2;read=true;}
 else if([35,39,49].includes(op)){size=4;read=true;}else if(op===55){size=8;read=true;}
 else if([30,54].includes(op)){size=16;read=true;aligned&=~15;}
 else if([34,38].includes(op)){size=4;read=true;aligned&=~3;}
 else if([26,27].includes(op)){size=8;read=true;aligned&=~7;}
 else if([40,41,43,63,57].includes(op)){size=op===40?1:op===41?2:op===63?8:4;write=true;}
 else if([31,62].includes(op)){size=16;write=true;aligned&=~15;}
 else if([42,46].includes(op)){size=4;read=true;write=true;aligned&=~3;}
 else if([44,45].includes(op)){size=8;read=true;write=true;aligned&=~7;}
 return size?{address:aligned>>>0,size,read,write}:null;
}
export function parseEEJob(bytes){
 const b=Buffer.from(bytes);need(b.length>=28&&b.subarray(0,8).toString()==='MC3EE001','Invalid factory EE job');
 need(28+b.readUInt32LE(16)*20+b.readUInt32LE(20)*8+b.readUInt32LE(24)*8<=b.length,'Truncated factory EE context header');
 let at=28;const gpr=[],fpr=[],chunks=[];
 for(let i=0;i<b.readUInt32LE(16);i++,at+=20)gpr.push([b.readUInt32LE(at),b.readBigUInt64LE(at+4).toString(),b.readBigUInt64LE(at+12).toString()]);
 for(let i=0;i<b.readUInt32LE(20);i++,at+=8)fpr.push([b.readUInt32LE(at),b.readUInt32LE(at+4)]);
 for(let i=0;i<b.readUInt32LE(24);i++){need(at+8<=b.length,'Truncated factory patch header');const address=b.readUInt32LE(at),size=b.readUInt32LE(at+4);at+=8;need(at+size<=b.length,'Truncated factory patch');chunks.push({address,data_hex:b.subarray(at,at+size).toString('hex')});at+=size;}
 need(at===b.length,'Factory EE job trailing bytes');return{entry:b.readUInt32LE(8),maxSteps:b.readUInt32LE(12),gpr,fpr,chunks};
}
export function collectDMA(ram,start,end){
 need(ram instanceof Uint8Array&&ram.length===0x2000000&&Number.isInteger(start)&&Number.isInteger(end)&&start%16===0&&end%16===0&&start>=0&&start<end&&end<=ram.length,'Invalid factory DMA extent');
 const view=new DataView(ram.buffer,ram.byteOffset,ram.byteLength),rows=[],parts=[];let at=start,total=0;
 while(at<end){need(rows.length<4096&&at+16<=end,'Invalid factory DMA chain');const lo=view.getUint32(at,true),address=view.getUint32(at+4,true),tag=lo>>>28&7,qwc=lo&65535;
  need([1,3].includes(tag)&&!(lo&0x8fff0000),'Unsupported factory DMA tag flags');const size=qwc*16,source=tag===1?at+16:address;
  need(source%16===0&&source+size<=ram.length&&(tag!==1||source+size<=end),'Factory DMA payload outside memory');need(total+8+size<=0x100000,'Factory DMA output exceeds bounded stream');
  const command=ram.slice(at+8,at+16),payload=ram.slice(source,source+size);parts.push(command,payload);rows.push({offset:at,tag,qwc,address,source,bytes:size,stream_offset:total});total+=8+size;at+=16+(tag===1?size:0);
 }need(at===end,'Factory DMA chain end differs');const bytes=new Uint8Array(total);let pos=0;for(const p of parts){bytes.set(p,pos);pos+=p.length;}return{rows,bytes};
}
export function vifCommands(bytes){
 need(bytes instanceof Uint8Array&&bytes.length<=0x100000,'Factory VIF outside bounded stream');
 const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),rows=[];let at=0,cl=1,wl=1;
 while(at<bytes.length){need(at+4<=bytes.length,'Truncated factory VIF word');const offset=at,word=v.getUint32(at,true),cmd=word>>>24&127,n=word>>>16&255,imm=word&65535;at+=4;let size=0;
  if(cmd===0x4a)size=(n||256)*8;else if([0x50,0x51].includes(cmd))size=imm*16;else if(cmd===0x20)size=4;else if([0x30,0x31].includes(cmd))size=16;
  else if(cmd>=0x60){need(wl<=cl,'Unsupported factory VIF fill cycle');const vl=cmd&3,vn=(cmd>>>2&3)+1;size=Math.ceil((n||256)*(vl===3?16:vn*(32>>>vl))/8);size=(size+3)&~3;}
  else need([0,1,2,3,4,5,6,7,0x10,0x11,0x13,0x14,0x15,0x17].includes(cmd),'Unsupported factory VIF command');
  need(at+size<=bytes.length,'Truncated factory VIF payload');rows.push({offset,word,cmd,size});at+=size;
  if(cmd===1){cl=(imm&255)||256;wl=(imm>>>8)||256;}
 }return rows;
}
export function capturePrefix(bytes){
 const parts=[],owners=[];for(const c of vifCommands(bytes))if([0x50,0x51].includes(c.cmd)){const p=bytes.subarray(c.offset+4,c.offset+4+c.size);parts.push(p);owners.push(...Array(p.length).fill(c.offset));}
 const direct=Buffer.concat(parts),frames=[];let at=0;
 while(at<direct.length){need(at+16<=direct.length,'Truncated factory DIRECT GIF');const start=at,lo=direct.readBigUInt64LE(at),hi=direct.readBigUInt64LE(at+8),n=Number(lo&32767n),type=Number(lo>>58n&3n),nr=Number(lo>>60n)||16;at+=16;
  if(type===0){need(at+n*nr*16<=direct.length,'Truncated factory PACKED');for(let i=0;i<n*nr;i++,at+=16)if(Number(hi>>BigInt(i%nr*4)&15n)===14&&direct.readBigUInt64LE(at+8)===0x4cn)frames.push({offset:owners[start],word:direct.readBigUInt64LE(at).toString(),fbp:Number(direct.readBigUInt64LE(at)&511n)});}
  else if(type===1)at+=Math.ceil(n*nr/2)*16;else if(type===2)at+=n*16;else throw Error('Unsupported factory GIF mode');need(at<=direct.length,'Truncated factory GIF payload');
 }let active=false,activeOffset;for(const frame of frames){if(frame.fbp===256){active=true;activeOffset=frame.offset;}else if(active){need(frame.offset>activeOffset,'Factory restore shares active DIRECT command');return{bytes:bytes.slice(0,frame.offset),cut:frame.offset,frames};}}throw Error('Unresolved factory target restore boundary');
}
export function executePack(pack){
 const codeBytes=Buffer.alloc(pack.code.length*8);for(const[i,[a,w]]of pack.code.entries()){need(Number.isInteger(a)&&a%4===0&&Number.isInteger(w)&&w>=0&&w<=0xffffffff,'Invalid factory instruction closure');codeBytes.writeUInt32LE(a,i*8);codeBytes.writeUInt32LE(w,i*8+4);}need(sha(codeBytes)===pack.code_sha256,'Factory instruction closure digest differs');
 const ram=new Uint8Array(0x2000000),spad=new Uint8Array(16384);for(const c of pack.chunks){need(typeof c.data_hex==='string'&&c.data_hex.length%2===0&&/^[0-9a-f]*$/.test(c.data_hex),'Invalid factory source chunk encoding');const bytes=Buffer.from(c.data_hex,'hex');need(sha(bytes)===c.sha256,'Factory source chunk digest differs');if(c.address>=0x70000000)spad.set(bytes,c.address-0x70000000);else ram.set(bytes,c.address);}
 const state=createNativeEEState({...pack,ram,spad,code:new Map(pack.code),gpr:pack.gpr.map(([r,low])=>[r,BigInt(low)])});for(const[r,,high]of pack.gpr)state.upper[r]=BigInt(high);
 runNativeEE(state,{maxSteps:pack.maxSteps});return state;
}
export function discover(executable,job,nativeRam){
 need(sha(executable)==='1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d','Original factory executable differs');
 const e=Buffer.from(executable),ram=new Uint8Array(0x2000000),spad=new Uint8Array(16384),code=new Map(),regions=[],fileRanges=[];
 const p=e.readUInt32LE(28),width=e.readUInt16LE(42),count=e.readUInt16LE(44);
 for(let i=0;i<count;i++){const at=p+i*width;if(e.readUInt32LE(at)!==1)continue;const source=e.readUInt32LE(at+4),address=e.readUInt32LE(at+8),size=e.readUInt32LE(at+16),memorySize=e.readUInt32LE(at+20),flags=e.readUInt32LE(at+24);ram.set(e.subarray(source,source+size),address);fileRanges.push([address,size,source]);regions.push({start:address,size:memorySize,read:true,write:!!(flags&2)});if(flags&1)for(let o=0;o+4<=size;o+=4)code.set(address+o,e.readUInt32LE(source+o));}
 const context=parseEEJob(job);for(const c of context.chunks){const b=Buffer.from(c.data_hex,'hex');if(c.address>=0x70000000)spad.set(b,c.address-0x70000000);else ram.set(b,c.address);regions.push({start:c.address,size:b.length,read:true,write:true});if(c.address===context.entry)for(let o=0;o+4<=b.length;o+=4)code.set(c.address+o,b.readUInt32LE(o));}
 regions.push(...[[0x1009000,12],[0x70000000,16384],[0x1100000,0x100000],[0x1400000,0x200000],[0x1fe0000,0x20000]].map(([start,size])=>({start,size,read:true,write:true})));
 const state=createNativeEEState({...context,ram,spad,code,regions,gpr:context.gpr.map(([r,low])=>[r,BigInt(low)])});for(const[r,,high]of context.gpr)state.upper[r]=BigInt(high);
 const maps=[{start:0,read:new Uint8Array(ram.length),write:new Uint8Array(ram.length),initial:new Uint8Array(ram.length)},{start:0x70000000,read:new Uint8Array(16384),write:new Uint8Array(16384),initial:new Uint8Array(16384)}],visited=new Map();
 const mark=(address,size,read,write)=>{const m=maps.find(m=>address>=m.start&&address+size<=m.start+m.read.length);need(m,'Factory memory footprint outside RAM/SPAD');for(let i=address-m.start;i<address-m.start+size;i++){if(read){m.read[i]=1;if(!m.write[i])m.initial[i]=1;}if(write)m.write[i]=1;}};
 runNativeEE(state,{maxSteps:context.maxSteps,onInstruction(pc,w,s){visited.set(pc,w);const m=memoryFootprint(pc,w,s);if(m)mark(m.address,m.size,m.read,m.write);}});
 need(nativeRam.length===ram.length&&Buffer.from(state.ram).equals(Buffer.from(nativeRam)),'Whole native factory RAM differs before sparse projection');
 const end=new DataView(state.ram.buffer).getUint32(0x1009008,true),dma=collectDMA(state.ram,0x1100000,end);
 for(const row of dma.rows)mark(row.source,row.bytes,true,false);const capture=capturePrefix(dma.bytes);
 return {context,fileRanges,code:[...visited].sort((a,b)=>a[0]-b[0]),access:maps.map(m=>({start:m.start,read:spans(m.read),write:spans(m.write),initial:spans(m.initial)})),steps:state.steps,native_ram_sha256:sha(nativeRam),dma:{end,rows:dma.rows,sha256:sha(dma.bytes),bytes:dma.bytes.length,capture_sha256:sha(capture.bytes),capture_bytes:capture.cut,frames:capture.frames}};
}
if(process.argv[2]==='discover'){const result=discover(fs.readFileSync(process.argv[3]),fs.readFileSync(process.argv[4]),fs.readFileSync(process.argv[5]));fs.writeFileSync(process.argv[6],JSON.stringify(result));}
