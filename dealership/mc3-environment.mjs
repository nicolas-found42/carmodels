import * as THREE from './vendor/three.module.js';
import {copyNativeEnvironmentRGBA} from './mc3-specular.mjs';
import {prepareNativeGSDraw,rasterizeGSTriangle,sampleGSFixedRGBA,testGSDepth16} from './mc3-gs-raster.mjs';
import {nativeVUAdd as nativeAdd,nativeVUMultiply as nativeMul,nativeVUDivide as nativeDiv} from './mc3-vehicle-math.mjs';

const SIZE=256;
const clampByte=value=>Math.max(0,Math.min(255,value));
const providers=new WeakMap();
export function nativeGarageAssetURL(moduleURL=import.meta.url) {
 return new URL('./public/midnight-club-3-remix/environment/native-garage.json',moduleURL).href;
}

// GS bilinear interpolation uses four fractional bits and truncates each
// horizontal interpolation before interpolating the resulting rows.
export function sampleNativeRGBA(image,s,t,wrap='repeat') {
 const {width,height,data}=image;
 if(!Number.isFinite(s)||!Number.isFinite(t))throw Error('Nonfinite native texture coordinate.');
 const u=Math.floor((s*width-.5)*16),v=Math.floor((t*height-.5)*16);
 const x=u>>4,y=v>>4,fx=u&15,fy=v&15;
 const address=(n,size)=>wrap==='clamp'?Math.max(0,Math.min(size-1,n)):((n%size)+size)%size;
 const a=(address(y,height)*width+address(x,width))*4;
 const b=(address(y,height)*width+address(x+1,width))*4;
 const c=(address(y+1,height)*width+address(x,width))*4;
 const d=(address(y+1,height)*width+address(x+1,width))*4;
 return [0,1,2,3].map(channel=>{
  const top=(data[a+channel]*(16-fx)+data[b+channel]*fx)>>4;
  const bottom=(data[c+channel]*(16-fx)+data[d+channel]*fx)>>4;
  return (top*(16-fy)+bottom*fy)>>4;
 });
}

export function floorNativeRGBA(base,lightmap) {
 const result=[0,0,0,base[3]];
 for(let c=0;c<3;c++)result[c]=clampByte(((base[c]*[75,69,65][c]>>7)-lightmap[c])*lightmap[3]>>7);
 return result;
}

function nativeGIFBytes(records) {
 const chunks=records.flatMap(record=>record.gif_chunks.map(value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0))));
 const bytes=new Uint8Array(chunks.reduce((n,chunk)=>n+chunk.length,0));
 let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
 return bytes;
}

function validateNativeVisibility(pack,state) {
 const expected=new Set(pack.draws.flatMap((draw,i)=>draw.material_index===8?[]:[i]));
 const controls=pack.native_gs.visibility_controls;
 if(!expected.size&&!controls)return;
 if(!controls||Object.keys(controls).sort().join(',')!=='0,192')throw Error('Native GS visibility controls are required.');
 for(const control of [0,192]) {
  const records=controls[control],seen=new Set();
  if(!Array.isArray(records)||records.length!==expected.size)throw Error('Incomplete native GS visibility control.');
  for(const record of records) {
   const draw=pack.draws[record.draw_index],native=draw?.native,packet=native&&pack.native_packets[native.packet];
   if(!expected.has(record.draw_index)||seen.has(record.draw_index)||record.material_index!==draw.material_index
    ||record.batch_offset!==native?.batch_offset||record.source_packet_sha256!==packet?.sha256)throw Error('Native GS visibility source binding changed.');
   seen.add(record.draw_index);
   if(prepareNativeGSDraw(nativeGIFBytes([record]),state).indices.length)throw Error('Unsupported source geometry reaches the native GS scissor.');
  }
 }
}

// Original EE/VU execution supplies clipping and emitted GS vertices. Only
// the pinned software-GS raster/texture/depth path is translated here.
export function captureNativeGarage(pack,{initialRGBA}={}) {
 const native=pack.native_gs,context=native?.context;
 if(native?.schema!==1||context?.depth_format!=='PSMZ16S'||!Array.isArray(native.passes)
  ||!Array.isArray(context.xy_offset)||context.xy_offset.length!==2
  ||context.xy_offset.some(v=>!Number.isInteger(v)||v<0||v>65535)
  ||JSON.stringify(context.scissor)!=='[0,0,256,256]')throw Error('Executed native GS capture context is required.');
 if(initialRGBA!==undefined&&(!(initialRGBA instanceof Uint8Array)||initialRGBA.length!==SIZE*SIZE*4))throw Error('Invalid native initial capture buffer.');
 const output=initialRGBA?new Uint8Array(initialRGBA):new Uint8Array(SIZE*SIZE*4),depthBuffer=new Uint16Array(SIZE*SIZE);
 const owners=new Uint8Array(SIZE*SIZE),contributing=new Set(),state={xyOffset:context.xy_offset,scissor:context.scissor};
 validateNativeVisibility(pack,state);
 function draw(records,sky) {
  const first=records[0],supported=sky||(first.material_index===8&&[0,1].includes(first.pass_index));
  const image=sky?pack.sky.images[first.image]:supported?pack.images[first.pass_index?'floorLightmap':'floorBase']:null;
  const data=prepareNativeGSDraw(nativeGIFBytes(records),state);
  if(!data.indices.length)return;
  if(supported&&!image)throw Error('Native GS source image is missing.');
  const colour=data.vertices[data.indices[0]].rgba;
  if(data.indices.some(i=>data.vertices[i].rgba.some((v,k)=>v!==colour[k])))throw Error('Unsupported native GS varying vertex colour.');
  for(let index=0;index<data.indices.length;index+=3) {
   const vertices=data.indices.slice(index,index+3).map(i=>data.vertices[i]);
   rasterizeGSTriangle(vertices,{...state,textureSize:image?[image.width,image.height]:[1,1],constantQ:data.constantQ,onPixel(x,y,fragment){
    if(!supported)throw Error('Original garage capture includes an unsupported visible material '+first.material_index+'.');
    contributing.add(sky?'sky':first.material_index);
    const pixel=y*SIZE+x,z=testGSDepth16(fragment.z,depthBuffer[pixel]);if(!z.pass)return;
    const texel=sampleGSFixedRGBA(image,fragment.u,fragment.v,sky?'clamp':'repeat');
    const source=texel.map((v,k)=>clampByte(v*colour[k]>>7)),offset=pixel*4;
    if(!sky&&first.pass_index===1) {
     for(let c=0;c<3;c++)output[offset+c]=clampByte((output[offset+c]-source[c])*source[3]>>7);
    } else output.set(source,offset);
    depthBuffer[pixel]=z.z;owners[pixel]=sky?1:2;
   }});
  }
 }
 let group=[],key,skyStarted=false;
 const prefill=()=>{for(let i=3;i<output.length;i+=4)if(output[i]<128)output[i]=48;};
 const flush=()=>{if(group.length)draw(group,(group[0].stage||'model')==='sky');group=[];};
 for(const record of native.passes) {
  if(record.stage!==undefined&&!['model','sky'].includes(record.stage))throw Error('Unsupported native GS capture stage.');
  const sky=(record.stage||'model')==='sky';
  if(skyStarted&&!sky)throw Error('Native GS model pass follows sky.');
  if(sky&&!skyStarted){flush();prefill();skyStarted=true;}
  const next=[record.stage||'model',record.material_index,record.pass_index,record.image].join(':');
  if(next!==key){flush();key=next;}
  group.push(record);
 }
 flush();if(!skyStarted)prefill();
 const coverage={uncovered:0,sky:0,floor:0};for(const owner of owners)coverage[['uncovered','sky','floor'][owner]]++;
 return {rgba:output,contributing:[...contributing],coverage};
}

export function decodeEnvironmentImage(image) {
 if(!Number.isInteger(image.width)||!Number.isInteger(image.height)||image.width<1||image.height<1)throw Error('Invalid native environment image size.');
 const binary=atob(image.rgba_base64),data=Uint8Array.from(binary,value=>value.charCodeAt(0));
 if(data.length!==image.width*image.height*4)throw Error('Invalid native environment image byte count.');
 return {...image,data};
}

export function nativeSpecularTexture(bytes) {
 const texture=new THREE.DataTexture(copyNativeEnvironmentRGBA(bytes),64,64);
 texture.colorSpace=THREE.NoColorSpace;texture.minFilter=texture.magFilter=THREE.LinearFilter;
 texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.flipY=false;texture.needsUpdate=true;
 return texture;
}

// Original 0041cc50 continued fraction. The selected official EE interpreter
// uses round-to-zero single-precision arithmetic and truncating CVT.W.S.
export function nativeAtan2(x,y) {
 if(!Number.isFinite(x)||!Number.isFinite(y))throw Error('Nonfinite native panorama axis.');
 const f=Math.fround,halfPi=f(Math.PI/2),pi=f(Math.PI);x=f(x);y=f(y);
 if(y===0)return x===0?0:x>0?halfPi:-halfPi;
 const ratio=nativeDiv(x,y),r=Math.abs(ratio)>1?nativeDiv(1,ratio):ratio;
 let tail=0;
 for(let i=14;i>0;i--)tail=nativeDiv(nativeMul(nativeMul(i*i,r),r),nativeAdd(nativeAdd(i+i,1),tail));
 let angle=nativeDiv(r,nativeAdd(tail,1));
 if(ratio>1)angle=nativeAdd(halfPi,-angle);else if(ratio< -1)angle=nativeAdd(-halfPi,-angle);
 if(y<=0)angle=nativeAdd(angle,x<=0?-pi:pi);
 return angle;
}

export function nativePanoramaOffset(axisX,axisZ,width=512) {
 if(!Number.isInteger(width)||width<1||width>1024||(width&(width-1)))throw Error('Unsupported native panorama width.');
 let offset=nativeMul(nativeAtan2(axisX,axisZ),nativeMul(width,Math.fround(1/(2*Math.PI))));
 if(offset<0)offset=nativeAdd(offset,width);
 return Math.trunc(nativeMul(offset,16));
}

export function addNativePanorama(base,panorama,offset16) {
 if(!Number.isInteger(offset16))throw Error('Native panorama offset needs sixteenth-texel units.');
 const output=new Uint8Array(base);
 for(let y=0;y<SIZE;y++)for(let x=0;x<SIZE;x++) {
  const texel=sampleNativeRGBA(panorama,(x*2+offset16/16)/panorama.width,y/panorama.height);
  const index=(y*SIZE+x)*4;
  for(let c=0;c<3;c++)output[index+c]=clampByte(output[index+c]+(texel[c]*127>>7));
 }
 return output;
}

export function createNativeGarageProvider(pack) {
 if(!Number.isFinite(pack.car_heading))throw Error('Original garage heading in radians is missing.');
 const decoded={...pack,images:Object.fromEntries(Object.entries(pack.images).map(([key,image])=>[key,decodeEnvironmentImage(image)])),
  sky:{...pack.sky,images:Object.fromEntries(Object.entries(pack.sky.images).map(([key,image])=>[key,decodeEnvironmentImage(image)]))}};
 const base=captureNativeGarage(decoded),texture=nativeSpecularTexture(base.rgba);
 let previousOffset,disposed=false;
 return {
  texture,pack,contributing:base.contributing,
  updateCamera(camera) {
   camera.updateMatrixWorld();
   const axis=camera.matrixWorld.elements,cos=Math.cos(pack.car_heading),sin=Math.sin(pack.car_heading),f=Math.fround;
   // city+19c stores the main camera's compact pose. Its first vector is
   // camera right, independently of the downward environment capture camera.
   const x=f(f(cos*axis[0])+f(sin*axis[2])),z=f(f(-sin*axis[0])+f(cos*axis[2]));
   return this.updateOffset(nativePanoramaOffset(x,z,decoded.images.panorama.width));
  },
  updateOffset(offset16) {
   if(disposed)throw Error('Native garage provider is disposed.');
   if(previousOffset===offset16)return false;
   texture.image.data.set(copyNativeEnvironmentRGBA(addNativePanorama(base.rgba,decoded.images.panorama,offset16)));
   texture.needsUpdate=true;previousOffset=offset16;return true;
  },
  dispose(){if(!disposed){disposed=true;texture.dispose();}}
 };
}

export async function prepareMC3Environment(renderer,{fetchImpl=fetch,url=nativeGarageAssetURL()}={}) {
 let entry=providers.get(renderer);
 if(!entry) {
  entry={};providers.set(renderer,entry);
  entry.ready=(async()=>{
   const response=await fetchImpl(url);
   if(!response.ok)throw Error('Original MC3 garage environment could not be loaded ('+response.status+').');
   const provider=createNativeGarageProvider(await response.json());
   if(entry.disposed){provider.dispose();throw Error('Native garage preparation was disposed.');}
   entry.provider=provider;return provider;
  })().catch(error=>{if(providers.get(renderer)===entry)providers.delete(renderer);throw error;});
 }
 return entry.ready;
}

export function nativeGarageProvider(renderer) {
 const provider=providers.get(renderer)?.provider;
 if(!provider)throw Error('Original MC3 garage environment is not prepared.');
 return provider;
}

export function disposeMC3Environment(renderer) {
 const entry=providers.get(renderer);if(!entry)return;
 entry.disposed=true;entry.provider?.dispose();providers.delete(renderer);
}
