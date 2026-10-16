// Original 002ad228 packing, with explicit caller state and framebuffer fields.
// This emits a complete dirty-state update; it does not model engine caching,
// texture binding, microcode upload or draw epilogues.
import {nativeVUMultiply as multiply} from './mc3-vehicle-math.mjs';
const bits=new DataView(new ArrayBuffer(4));
function need(value,message){if(!value)throw Error(message);}
function word(value){need(Number.isInteger(value)&&value>=0&&value<=0xffffffff,'Invalid native render state word.');return value;}
function floatWord(value){bits.setFloat32(0,value,true);return bits.getUint32(0,true);}
const lanes=value=>[value&255,value>>>8&255,value>>>16&255,value>>>24];

export function packNativeVehicleState(context) {
 const {words,colorMode,primitiveBase,frameBase,frameWidth,bpp,zbits,zbuf}=context??{};
 need(Array.isArray(words)&&words.length===21,'Explicit native render state is required.');
 const s=words.map(word);
 for(const value of [primitiveBase,frameBase,frameWidth,zbuf])word(value);
 need(bpp===32&&zbits===16,'Unsupported native framebuffer packing profile.');
 need(s[0]<8&&s[10]<4&&s[15]<3,'Native render state lookup outside source table.');
 need(colorMode===1||colorMode===2,'Explicit native material color mode is required.');
 need(s[1]<=1&&s[2]<=1&&s[4]<=7&&s[5]<=255&&s[6]<=3&&s[7]<=1
  &&s[9]<=15&&s[11]<=1&&s[12]<=3&&s[13]<=1&&s.slice(18).every(v=>v<=1),
  'Unsupported native render state selector.');
 let alpha;
 if(s[3]&0x10000)alpha=BigInt(s[3]&255)|(BigInt(s[3]&0xff00)<<24n);
 else {
  const table=[0x44n,0x8000000068n,0x8000000062n,0x81n,0x58n,0x80000000a8n,0x54n];
  need(s[3]<table.length,'Unsupported native blend selector.');alpha=table[s[3]];
 }
 const prmode=(16|(s[13]<<3)|(s[2]<<5)|(s[11]<<6))>>>0;
 const reference=(s[5]+(s[5]>>>7))>>>1;
 const test=(1|(s[4]<<1)|(reference<<4)|([0,0x4000,0xc000,0][s[10]])|(s[12]<<12)|0x10000|(s[6]<<17))>>>0;
 let mask=0xffffffff;
 for(let i=0;i<4;i++)if(s[9]&(1<<i))mask=(mask&~(255<<(i*8)))>>>0;
 const frame=(BigInt(frameBase)|(BigInt((frameWidth>>>6)<<16)))|(BigInt(mask)<<32n);
 const primitive=(((s[18]<<11)|(s[19]<<12)|(s[20]<<13)|[0,128,192,0,0,0,0,0][s[0]]
  |(s[2]<<3)|(s[1]<<1)|primitiveBase)>>>0);
 let color;
 if(s[14]===0x80ffffff)color=lanes(s[8]);
 else if(s[8]===0x80ffffff)color=lanes(s[14]);
 else {const a=lanes(s[8]),b=lanes(s[14]);color=a.map((v,i)=>(v*b[i]>> (i===3?7:8))&255);}
 const factor=colorMode===2?1:Math.fround(0.5019608);
 return {gs:[[0x42,alpha],[0x4e,BigInt(zbuf)|(s[7]===0?0x100000000n:0n)],
   [0x47,BigInt(test)],[0x1b,BigInt(prmode)],[0x4c,frame]],
  vu:{45:[prmode,0,0x1b,0],47:[prmode|0x200,0,0x1b,0],
   34:[primitive,[0x30004000,0x30014002,0x30024004][s[15]],0,0],
   42:color.map((v,i)=>floatWord(i===3?v:multiply(v,factor)))}};
}
