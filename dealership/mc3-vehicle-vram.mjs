// Chronological native IMAGE/CLUT/draw execution for generated paint targets.
// Depth access is explicitly excluded here. The original paint generator uses
// masked PSMZ32 and ALWAYS; no framebuffer/depth or upload fallback is supplied.
import {createNativeGSVRAM,writeNativeGSRegister,uploadNativeGSImage,readNativeGSTexture,readNativeGSPixel,writeNativeGSPixel} from './mc3-gs-vram.mjs';
import {renderNativeVehicleGIF} from './mc3-vehicle-gif.mjs';
const field=(value,shift,width)=>Number(value>>BigInt(shift)&((1n<<BigInt(width))-1n));
function need(ok,message){if(!ok)throw Error(message);}
export function renderNativeVehicleVRAMGIF(decoded,{initialVRAM,target}={}) {
 need(decoded?.initialRegisters instanceof Map&&Array.isArray(decoded.operations),'Explicit decoded native operation stream is required.');
 need(target&&['width','height','fbp','fbw','zbp'].every(k=>Number.isInteger(target[k]))
  &&target.width>0&&target.height>0&&target.width<=2048&&target.height<=2048
  &&target.fbp>=0&&target.fbp<=511&&target.zbp>=0&&target.zbp<=511
  &&target.fbw>0&&target.fbw<=63&&target.width<=target.fbw*64,'Explicit bounded native paint target is required.');
 const vram=createNativeGSVRAM(initialVRAM);
 for(const [address,value]of decoded.initialRegisters)if([6,7,0x50,0x51,0x52,0x53].includes(address)){
  // Initial registers are an already established context, not new transfer
  // commands. TEX0 loads need their explicit initial CLUT/VRAM state.
  if(address!==0x53)writeNativeGSRegister(vram,address,value);
 }
 const frame={...target,rgba:new Uint8Array(target.width*target.height*4),depth:new Uint32Array(target.width*target.height)};
 const stats={draws:0,triangles:0,sprites:0,pixels:0};
 function readFrame(){
  for(let y=0;y<frame.height;y++)for(let x=0;x<frame.width;x++){
   const word=readNativeGSPixel(vram,0,x,y,frame.fbp*32,frame.fbw),i=(y*frame.width+x)*4;
   for(let c=0;c<4;c++)frame.rgba[i+c]=word>>>(c*8)&255;
  }
 }
 for(const operation of decoded.operations){
  if(operation.kind==='register')writeNativeGSRegister(vram,operation.address,operation.value);
  else if(operation.kind==='image')uploadNativeGSImage(vram,operation.data);
  else if(operation.kind==='draw'){
   const draw=operation.draw,context=draw.primitive>>9&1,z=draw.registers.get(0x4e+context),test=draw.registers.get(0x47+context);
   need(z!==undefined&&test!==undefined&&field(z,24,4)===0&&field(z,32,1)===1
    &&(!field(test,16,1)||field(test,17,2)<2),'Native paint VRAM stage requires masked PSMZ32 without depth reads.');
   readFrame();
   const result=renderNativeVehicleGIF({...decoded,draws:[draw]},{target:frame,resolveTexture:tex0=>readNativeGSTexture(vram,tex0)});
   for(const key of Object.keys(stats))stats[key]+=result[key];
   for(let y=0;y<frame.height;y++)for(let x=0;x<frame.width;x++){
    const i=(y*frame.width+x)*4,word=(frame.rgba[i]|frame.rgba[i+1]<<8|frame.rgba[i+2]<<16|frame.rgba[i+3]<<24)>>>0;
    writeNativeGSPixel(vram,0,x,y,frame.fbp*32,frame.fbw,word);
   }
  }else throw Error('Unsupported native VRAM operation.');
 }
 readFrame();
 return {vram,frame:{width:frame.width,height:frame.height,fbp:frame.fbp,fbw:frame.fbw,rgba:frame.rgba},stats,depthAccess:false};
}
