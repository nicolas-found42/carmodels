// Pinned AVX2/FMA software-GS LCM0 stage. Inputs are the whole-draw Q trace,
// uncorrected signed16.16 UV, and the raster's interpolated float32 Q.
import {fusedGSFloat32} from './mc3-gs-raster.mjs';
import {createNativeVehicleSampler} from './mc3-vehicle-sampler.mjs';
const f=Math.fround,need=(ok,message)=>{if(!ok)throw Error(message);};
const field=(v,s,n)=>Number(v>>BigInt(s)&((1n<<BigInt(n))-1n));
const bits=new DataView(new ArrayBuffer(4));
const signed16=n=>n<<16>>16;
const coefficients=[.204446009836232697516,-1.04913055217340124191,2.28330284476918490682].map(f);
function parts(q){
 need(Number.isFinite(q)&&f(q)>=2**-126&&Number.isFinite(f(q)),'Unsupported native mip Q.');
 bits.setFloat32(0,q,true);const raw=bits.getUint32(0,true);
 bits.setUint32(0,(raw&0x7fffff)|0x3f800000,true);
 return {mantissa:bits.getFloat32(0,true),exponent:(raw>>>23)-127};
}
function logQ(q,fused){
 const {mantissa:m,exponent:e}=parts(q),[a,b,c]=coefficients;
 if(fused)return fusedGSFloat32(f(m-1),fusedGSFloat32(fusedGSFloat32(a,m,b),m,c),e);
 // GSVector4::log2(3), including its deliberately unfused madd helper.
 const polynomial=f(f(f(f(a*m)+b)*m)+c);
 return f(f(polynomial*f(m-1))+e);
}
const even=n=>{const a=Math.floor(n),r=n-a;return r>.5||r===.5&&a%2?a+1:a;};

export function createNativeVehicleVariableMipSampler({levels,tex1,clamp,drawTrace}={}){
 need(typeof tex1==='bigint'&&tex1>=0n&&tex1<=0xffffffffffffffffn
  &&typeof clamp==='bigint'&&clamp>=0n&&clamp<=0xffffffffffffffffn,'Explicit native mip registers are required.');
 const maximum=field(tex1,2,3),filter=field(tex1,6,3),scale=field(tex1,19,2),k=field(tex1,32,12)<<20>>20;
 need(field(tex1,0,1)===0&&maximum>0&&maximum<=6&&filter>=2&&filter<=5,'Unsupported native variable mip profile.');
 need(drawTrace&&Number.isFinite(drawTrace.qMin)&&Number.isFinite(drawTrace.qMax)
  &&drawTrace.qMin<drawTrace.qMax,'Explicit whole-draw varying Q trace is required.');
 const lods=[drawTrace.qMin,drawTrace.qMax].map(q=>f(f(-logQ(q,false)*(1<<scale))+f(k/16)));
 const minLOD=Math.min(...lods),maxLOD=Math.max(...lods);
 need(maxLOD>0,'Native variable mip trace has no active mip draw.');
 const forced=Math.trunc(minLOD)>=maximum,blend=!forced&&!!(filter&1);
 const bilinear=minLOD>0?filter>=4:!!(field(tex1,5,1)||(filter>=4));
 need(Array.isArray(levels)&&levels.length===maximum+1,'Explicit complete native mip images are required.');
 const samplers=levels.map((image,level)=>{
  need(level===0||image?.width===Math.max(1,levels[0].width>>level)
   &&image?.height===Math.max(1,levels[0].height>>level),'Native mip dimensions differ.');
  let shifted=clamp&15n;
  for(const [offset,width]of [[4,10],[14,10],[24,10],[34,10]])shifted|=BigInt(field(clamp,offset,width)>>>level)<<BigInt(offset);
  return createNativeVehicleSampler({image,tex1:bilinear?32n:0n,clamp:shifted});
 });
 const at=(level,u,v)=>samplers[level](((u>>level)-(bilinear?32768:0))|0,((v>>level)-(bilinear?32768:0))|0);
 function lod(q){
  const log=logQ(q,true),maximumWord=maximum*65536-(blend?1:0);
  const word=forced?maximum*65536:even(Math.max(0,Math.min(fusedGSFloat32(log,-(65536<<scale),k*4096),maximumWord)));
  return blend?word:(word+32768)&0xffff0000;
 }
 return {minLOD,maxLOD,bilinear,blend,forced,lod,sample(u,v,q){
  need([u,v].every(n=>Number.isInteger(n)&&n>=-2147483648&&n<=2147483647),'Explicit native mip coordinates are required.');
  const word=lod(q),index=word>>>16,first=at(index,u,v);
  if(!blend)return first;
  const second=at(index+1,u,v),weight=(word&65535)>>>1;
  // Variable LOD PSHUFLW/PSHUFHW duplicates each pixel's fractional word
  // for both channel pairs. The constant-LOD high-word shuffle is different.
  return first.map((a,channel)=>signed16(a+(signed16(signed16(second[channel]-a)<<1)*weight>>16)));
 }};
}
