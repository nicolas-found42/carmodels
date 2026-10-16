// Pinned software-GS DrawSprite/SetupPrim fixed-UV profile. The GS uses the
// second vertex's flat color and raw clamped depth; axes reorder independently.
// Texture coordinates use the explicit nearest or bilinear signed16.16 origin.
const f=Math.fround,sub=(a,b)=>f(a-b),mul=(a,b)=>f(a*b),add=(a,b)=>f(a+b),div=(a,b)=>f(a/b);
function need(value,message){if(!value)throw Error(message);}
function int32(value){need(Number.isFinite(value)&&value>=-2147483648&&value<2147483648,'Native sprite interpolation outside int32 profile.');return Math.trunc(value);}
export function rasterizeNativeVehicleSprite(vertices,{xyOffset,scissor,textured,depthBits=16,bilinear=true,onPixel}={}) {
 need(Array.isArray(vertices)&&vertices.length===2&&Array.isArray(xyOffset)&&xyOffset.length===2
  &&Array.isArray(scissor)&&scissor.length===4&&[...xyOffset,...scissor].every(Number.isInteger)
  &&typeof textured==='boolean'&&[16,32].includes(depthBits)&&typeof bilinear==='boolean'&&typeof onPixel==='function','Explicit native sprite state is required.');
 for(const v of vertices)need(Array.isArray(v.xy)&&v.xy.length===2&&v.xy.every(n=>Number.isInteger(n)&&n>=0&&n<=65535)
  &&Number.isInteger(v.z)&&v.z>=0&&v.z<=0xffffffff&&Array.isArray(v.rgba)&&v.rgba.length===4
  &&v.rgba.every(n=>Number.isInteger(n)&&n>=0&&n<=255)
  &&(!textured||Array.isArray(v.uv)&&v.uv.length===2&&v.uv.every(n=>Number.isInteger(n)&&n>=0&&n<=16383)),
  'Invalid native sprite vertex.');
 const p=vertices.map(v=>v.xy.map((n,i)=>f((n-xyOffset[i])/16)));
 const lo=[0,1].map(i=>p[0][i]<p[1][i]?0:1),hi=lo.map(i=>1-i);
 const left=Math.max(Math.ceil(p[lo[0]][0]),scissor[0]),right=Math.min(Math.ceil(p[hi[0]][0]),scissor[2]);
 const top=Math.max(Math.ceil(p[lo[1]][1]),scissor[1]),bottom=Math.min(Math.ceil(p[hi[1]][1]),scissor[3]);
 if(left>=right||top>=bottom)return;
 const vertex128=vertices[1].rgba.map(n=>n*128),z=Math.min(vertices[1].z,depthBits===32?0xffffffff:65535);
 let dt=[0,0],scan=[0,0];
 if(textured) {
  const t=vertices.map(v=>v.uv.map(n=>sub(n*4096,bilinear?32768:0)));
  dt=[0,1].map(i=>div(sub(t[hi[i]][i],t[lo[i]][i]),sub(p[hi[i]][i],p[lo[i]][i])));
  scan=[left,top].map((n,i)=>add(t[lo[i]][i],mul(dt[i],sub(n,p[lo[i]][i]))));
 }
 const skip=left&7,start=left-skip,step=int32(mul(dt[0],8));
 for(let y=top;y<bottom;y++) {
  const lanes=Array.from({length:8},(_,i)=>(int32(scan[0])+int32(mul(dt[0],i-skip)))|0),v=int32(scan[1]);
  for(let x=start;x<right;x+=8) {
   for(let i=0;i<8;i++)if(x+i>=left&&x+i<right)onPixel(x+i,y,{u:lanes[i],v,z,vertex128:[...vertex128]});
   for(let i=0;i<8;i++)lanes[i]=(lanes[i]+step)|0;
  }
  scan[1]=add(scan[1],dt[1]);
 }
}
