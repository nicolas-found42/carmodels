// Bounded constant-LOD reconstruction of the pinned software GS sampler.
// This is a separate stage: raster coordinates must have NO half-texel bias,
// and must retain native signed16.16 conversion before the mip-level shift.
import {createNativeVehicleSampler} from './mc3-vehicle-sampler.mjs';
const field=(v,s,n)=>Number(v>>BigInt(s)&((1n<<BigInt(n))-1n));
const need=(ok,message)=>{if(!ok)throw Error(message);};
const signed16=x=>x<<16>>16;

export function createNativeVehicleConstantMipSampler({levels,tex1,clamp}={}){
 need(typeof tex1==='bigint'&&tex1>=0n&&tex1<=0xffffffffffffffffn
  &&typeof clamp==='bigint'&&clamp>=0n&&clamp<=0xffffffffffffffffn,'Explicit native mip registers are required.');
 const maximum=field(tex1,2,3),minFilter=field(tex1,6,3),k=field(tex1,32,12)<<20>>20;
 need(field(tex1,0,1)===1&&maximum>0&&maximum<=6&&minFilter>=2&&minFilter<=5&&k>0,
  'Unsupported native constant mip profile.');
 need(Array.isArray(levels)&&levels.length===maximum+1,'Explicit complete native mip images are required.');
 let blend=!!(minFilter&1),lodMaximum=maximum*65536;
 // GSRendererSW integer minimum-LOD comparison forces the last level and
 // disables interpolation when even the smallest LOD reaches MXL.
 if(Math.trunc(k/16)>=maximum)blend=false;
 if(blend)lodMaximum--;
 let lod=Math.max(0,Math.min(k*4096,lodMaximum));
 if(!blend)lod=(lod+32768)&0xffff0000;
 const index=lod>>>16,fraction=lod&65535,bilinear=minFilter>=4;
 const samplers=levels.map((image,level)=>{
  need(level===0||image?.width===Math.max(1,levels[0].width>>level)
   &&image?.height===Math.max(1,levels[0].height>>level),'Native mip dimensions differ.');
  let shifted=clamp&15n;
  for(const [offset,width]of [[4,10],[14,10],[24,10],[34,10]])shifted|=BigInt(field(clamp,offset,width)>>>level)<<BigInt(offset);
  return createNativeVehicleSampler({image,tex1:bilinear?32n:0n,clamp:shifted});
 });
 function at(level,u,v){const bias=bilinear?32768:0;return samplers[level](((u>>level)-bias)|0,((v>>level)-bias)|0);}
 return {level:index,fraction,blend,bilinear,sample(u,v,x){
  need([u,v].every(n=>Number.isInteger(n)&&n>=-2147483648&&n<=2147483647)
   &&Number.isInteger(x)&&x>=0,'Explicit native mip coordinates and absolute pixel x are required.');
  const first=at(index,u,v);if(!blend)return first;
  const second=at(index+1,u,v);
  return first.map((a,channel)=>{
   // Original GSRendererSW stores GSVector4i(lod.f).xxxxl().xxzz().
   // The high-word shuffle leaves blue/alpha fractions zero for lanes2/3
   // of each four pixels. This reproduces that selected software profile;
   // it is not asserted as physical PS2 GS behavior.
   const weight=channel>=2&&(x&3)>=2?0:fraction>>>1;
   const difference=signed16(signed16(second[channel]-a)<<1);
   return signed16(a+(difference*weight>>16));
  });
 }};
}
