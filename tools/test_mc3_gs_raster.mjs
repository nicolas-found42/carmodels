import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {decodeNativeGIF,prepareNativeGSDraw,fusedGSFloat32,fusedGSFloat64,roundGSSTQ,rasterizeGSTriangle,sampleGSFixedRGBA,testGSDepth16} from '../dealership/mc3-gs-raster.mjs';

assert.equal(fusedGSFloat32(1+2**-23,1-2**-23,-1),-(2**-46),'fused cancellation retains product bits');
assert.equal(fusedGSFloat32(1,2**-24,1),1,'halfway rounds to even lower significand');
assert.equal(fusedGSFloat32(1,2**-24,1+2**-23),1+2**-22,'halfway rounds to even upper significand');
const doubleRound=[1+2**-23,(1-2**-23)*2**-24,1+2**-23];
assert.equal(fusedGSFloat32(...doubleRound),1+2**-23);
assert.equal(Math.fround(doubleRound[0]*doubleRound[1]+doubleRound[2]),1+2**-22,'double intermediate is an independently different rounding result');
assert.equal(fusedGSFloat64(1+2**-52,1-2**-52,-1),-(2**-104));
assert.equal(fusedGSFloat64(1,2**-53,1),1);
assert.equal(fusedGSFloat64(1,2**-53,1+2**-52),1+2**-51);
const bitView=new DataView(new ArrayBuffer(4));
const floatFromBits=n=>{bitView.setUint32(0,n,true);return bitView.getFloat32(0,true);};
const floatToBits=n=>{bitView.setFloat32(0,n,true);return bitView.getUint32(0,true);};
assert.deepEqual(roundGSSTQ([0x3f812345,0xbf012345,0x3f9696ad].map(floatFromBits)).map(floatToBits),[0x3f812200,0xbf012000,0x3f969600]);

function packet(primitive,points,{pre=true,loops=points.length,registers=0x412}={}) {
 const bytes=new Uint8Array(16+points.length*48),view=new DataView(bytes.buffer);
 view.setUint32(0,loops|0x8000,true);
 view.setUint32(4,0x30000000|(pre?0x4000:0)|(primitive<<15),true);
 view.setUint32(8,registers,true);
 for(let i=0;i<points.length;i++) {
  const v=points[i],offset=16+i*48;
  (v.stq||[0,0,1]).forEach((n,k)=>view.setFloat32(offset+k*4,n,true));
  [75,69,65,128].forEach((n,k)=>view.setUint8(offset+16+k*4,n));
  view.setUint16(offset+32,v.x??i*16,true);view.setUint16(offset+36,v.y??i*32,true);
  view.setUint32(offset+40,(v.z??12345)*16,true);
  view.setUint32(offset+44,(37<<4)|(v.adc?0x8000:0),true);
 }
 return bytes;
}
const join=(...parts)=>Uint8Array.from(parts.flatMap(part=>[...part]));
const decoded=decodeNativeGIF(join(packet(5,[{},{},{},{}]),packet(4,[],{registers:0x512}),
 packet(5,[{},{},{},{stq:[0,0,2]}]),packet(4,[{adc:true},{adc:true},{},{adc:true},{}])));
assert.equal(decoded.length,2,'zero-loop PRE is ignored; nonempty primitive change starts the next topology group');
assert.deepEqual(decoded[0].indices,[0,1,2,0,2,3,4,5,6,4,6,7],'same-PRE fan restarts assembly without splitting constant-Q draw');
assert.deepEqual(decoded[1].indices,[0,1,2,2,3,4],'ADC suppresses the current strip triangle while preserving assembly');
assert.deepEqual(decodeNativeGIF(packet(4,[{},{},{},{}]))[0].indices,[0,1,2,1,2,3],'selected software-GS strip index order remains chronological');
assert.deepEqual(decoded[0].vertices[0],{xy:[0,0],z:12345,stq:[0,0,1],rgba:[75,69,65,128],fog:37,adc:false});
assert.equal(decodeNativeGIF(join(packet(5,[{},{},{}]),packet(5,[{}],{pre:false})))[0].indices.length,6,'tag without PRE continues assembly');
assert.throws(()=>decodeNativeGIF(packet(5,[{},{},{}],{pre:false})),/initial primitive/);
assert.throws(()=>decodeNativeGIF(packet(0,[{}])),/Unsupported native GIF primitive/);
assert.throws(()=>decodeNativeGIF(packet(5,[{}],{registers:0x512})),/Unsupported native GIF layout/);
assert.throws(()=>decodeNativeGIF(packet(5,[{}]).slice(0,16)),/Truncated/);
assert.equal(decodeNativeGIF(packet(4,[{stq:[0,0,-1],adc:true}]))[0].vertices[0].stq[2],-1,'transport preserves unused ADC attributes without guessing');
const prepared=prepareNativeGSDraw(join(packet(4,[{x:0,y:0},{x:64,y:0},{x:0,y:64}]),
 packet(5,[{x:8192,y:8192,stq:[0,0,2]},{x:8256,y:8192,stq:[0,0,2]},{x:8192,y:8256,stq:[0,0,2]}])),
 {xyOffset:[0,0],scissor:[0,0,256,256]});
assert.equal(prepared.indices.length,3);assert.equal(prepared.constantQ,true,'scissored guardband triangles do not change whole-draw Q selection');
assert.equal(prepareNativeGSDraw(packet(4,[{stq:[0,0,7],adc:true},{x:0,y:0},
 {x:64,y:0,adc:true},{x:0,y:64},{x:64,y:64}]),{xyOffset:[0,0],scissor:[0,0,256,256]}).constantQ,true,
 'unreferenced ADC-only vertices do not alter indexed Q tracing');

const texture={width:128,height:128,data:new Uint8Array(128*128*4)};
for(let y=0;y<128;y++)for(let x=0;x<128;x++)texture.data.set([x,y,x^y,128],(y*128+x)*4);
const vertices=[{xy:[32764,32776],z:0x12345678,stq:[0,0,1]},
 {xy:[36860,32768],z:0x12345678,stq:[1,0,1]},
 {xy:[32784,36850],z:0x12345678,stq:[0,1,1]}];
const state={xyOffset:[32768,32768],scissor:[0,0,256,256],textureSize:[128,128],constantQ:true};
function draw(points,options={}) {
 const rgba=new Uint8Array(256*256*4);for(let i=3;i<rgba.length;i+=4)rgba[i]=128;
 let count=0;
 rasterizeGSTriangle(points,{...state,...options,onPixel(x,y,v){
  assert.equal(v.z,0x12345678);count++;rgba.set(sampleGSFixedRGBA(texture,v.u,v.v),(y*256+x)*4);
 }});
 return {rgba,count};
}
// Independently executed official PCSX2 v2.8.2 software GS AVX2, one
// subpixel textured triangle, native PSMCT32 RGBA and bilinear repeat.
const original=draw(vertices);
assert.equal(original.count,32521);
assert.equal(createHash('sha256').update(original.rgba).digest('hex'),'24b10b8c49f435c6e26c37c696ca086bbf21d6e470fb7b649acbf3fac426df9a');
assert.deepEqual(draw(vertices.map(v=>({...v,stq:v.stq.map(n=>n*2)}))).rgba,original.rgba,'independent Q2 replay confirms constant-Q conversion');
const perspective=vertices.map((v,i)=>({...v,stq:i===1?[2,0,2]:i===2?[0,.5,.5]:v.stq}));
assert.equal(createHash('sha256').update(draw(perspective,{constantQ:false}).rgba).digest('hex'),'b96045a08e4b8817e22ae59b9cb4fa8b03d48ea26ae87491508c089e26b4e259','independent varying-Q replay confirms perspective divide and scanline precision');
assert.deepEqual(draw([...vertices].reverse()).rgba,original.rgba,'winding does not alter neutral textured triangle interpolation');
const rightTriangle=[[0,0],[256,0],[0,256]].map(xy=>({xy:xy.map(v=>32768+v*16),z:0x12345678,stq:[0,0,1]}));
assert.equal(draw(rightTriangle).count,32896,'independent red-triangle replay establishes integer sample origin/top-left coverage');
assert.equal(draw(vertices,{scissor:[32,32,64,64]}).count,1024,'GS scissor uses exclusive right/bottom bounds after context conversion');
assert.equal(draw([vertices[0],vertices[0],vertices[1]]).count,0);
assert.throws(()=>rasterizeGSTriangle(vertices),/Explicit GS triangle state/);
assert.throws(()=>draw(vertices.map(v=>({...v,xy:[-1,0]}))),/Invalid bounded/);
assert.throws(()=>draw(vertices.map((v,i)=>({...v,stq:[0,0,i+1]}))),/varying Q/);
assert.throws(()=>draw(vertices.map(v=>({...v,stq:[1e30,0,1]}))),/texture conversion range/);
assert.throws(()=>sampleGSFixedRGBA(texture,.5,0),/16.16 integers/);
const small={width:2,height:2,data:Uint8Array.from([0,1,2,3,31,32,33,34,64,65,66,67,127,128,129,130])};
assert.deepEqual(sampleGSFixedRGBA(small,32768,32768),[55,56,57,58]);
assert.deepEqual(sampleGSFixedRGBA(small,-32768,-32768),[55,56,57,58]);
assert.deepEqual(sampleGSFixedRGBA(small,-32768,-32768,'clamp'),[0,1,2,3]);
// Independent PSMZ16S replay draws red at source Z65536, then green at Z1.
// Its 32521 covered pixels stay red: source depth clamps before GEQUAL/store.
const depths=new Uint16Array(256*256),depthRGBA=new Uint8Array(256*256*4);
for(let i=3;i<depthRGBA.length;i+=4)depthRGBA[i]=128;
for(const [z,colour] of [[65536,[255,0,0,128]],[1,[0,255,0,128]]]) {
 rasterizeGSTriangle(vertices.map(v=>({...v,z})),{...state,onPixel(x,y,v){
  const pixel=y*256+x,result=testGSDepth16(v.z,depths[pixel]);
  if(result.pass){depths[pixel]=result.z;depthRGBA.set(colour,pixel*4);}
 }});
}
assert.equal(depths.filter(z=>z===65535).length,32521);
assert.equal(depthRGBA.filter((v,i)=>i%4===1&&v!==0).length,0);
assert.equal(createHash('sha256').update(depthRGBA).digest('hex'),'ef4e200ef7fa3e6d6f78b9b0a1721c310e55938f96b6729a053cb2c41e82918b','independent native PSMZ16S full-frame replay');
assert.deepEqual(testGSDepth16(65536,65535),{pass:true,z:65535});
assert.deepEqual(testGSDepth16(65536,65535,'greater'),{pass:false,z:65535});
assert.deepEqual(testGSDepth16(1,65535,'always'),{pass:true,z:1});
assert.deepEqual(testGSDepth16(65535,0,'never'),{pass:false,z:65535});
assert.throws(()=>testGSDepth16(-1,0),/Invalid bounded/);
assert.throws(()=>testGSDepth16(0,0,'less'),/Unsupported GS depth/);
console.log('PASS test_mc3_gs_raster: independently executed AVX2 GS golden frames/depth16S control, exact FMA32/FMA64 cancellation/halfway/double-rounding, native GIF topology/ADC transport, pretrace scissor rejection/STQ truncation, fixed16.16 sampling and bounded guards');
