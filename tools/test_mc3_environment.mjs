import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {sampleNativeRGBA,floorNativeRGBA,captureNativeGarage,decodeEnvironmentImage,nativeSpecularTexture,nativeAtan2,nativePanoramaOffset,addNativePanorama,prepareMC3Environment,nativeGarageProvider,disposeMC3Environment,nativeGarageAssetURL} from '../dealership/mc3-environment.mjs';

const image={width:2,height:2,data:Uint8Array.from([0,1,2,3,31,32,33,34,64,65,66,67,127,128,129,130])};
assert.deepEqual(sampleNativeRGBA(image,.5,.5),[55,56,57,58]);
assert.deepEqual(sampleNativeRGBA(image,.3125,.5),[37,38,39,40],'four-bit fraction truncates before row combination');
assert.deepEqual(sampleNativeRGBA(image,0,0,'clamp'),[0,1,2,3]);
assert.deepEqual(sampleNativeRGBA(image,0,0),[55,56,57,58]);
assert.deepEqual(sampleNativeRGBA(image,1.5,.5),sampleNativeRGBA(image,.5,.5));
assert.throws(()=>sampleNativeRGBA(image,NaN,0),/Nonfinite/);
assert.deepEqual(floorNativeRGBA([128,128,128,19],[0,0,0,128]),[75,69,65,19]);
assert.deepEqual(floorNativeRGBA([128,128,128,19],[76,68,64,127]),[0,0,0,19]);
assert.deepEqual(floorNativeRGBA([255,255,255,26],[1,2,3,64]),[74,67,63,26]);

const solid=(rgba)=>({width:1,height:1,data:Uint8Array.from(rgba)});
const context={xy_offset:[32768,32768],scissor:[0,0,256,256],depth_format:'PSMZ16S'};
function record(material,pass,{sky=false,hidden=false,z=19263,colour=pass?[128,128,128,128]:[75,69,65,128]}={}) {
 const bytes=new Uint8Array(160),view=new DataView(bytes.buffer);
 view.setUint32(0,0x8003,true);view.setUint32(4,0x30024000,true);view.setUint32(8,0x412,true);
 const points=hidden?[[1024,1024],[1028,1024],[1024,1028]]:[[-256,-256],[512,-256],[128,512]];
 for(let i=0;i<3;i++) {
  const offset=16+i*48;view.setFloat32(offset+8,1,true);
  colour.forEach((v,k)=>view.setUint8(offset+16+k*4,v));
  view.setUint16(offset+32,32768+points[i][0]*16,true);view.setUint16(offset+36,32768+points[i][1]*16,true);
  view.setUint32(offset+40,z*16,true);
 }
 return {material_index:material,pass_index:pass,stage:sky?'sky':'model',image:sky?'test':undefined,gif_chunks:[Buffer.from(bytes).toString('base64')]};
}
const pack={car_heading:0,native_gs:{schema:1,context,passes:[record(8,0),record(8,1)]},
 draws:[],sky:{draws:[],images:{}},images:{floorBase:solid([128,128,128,23]),floorLightmap:solid([0,0,0,128])}};
const empty={...pack,native_gs:{...pack.native_gs,passes:[]}};
assert.throws(()=>captureNativeGarage({...pack,native_gs:undefined}),/Executed native GS capture context/);
const capture=captureNativeGarage(pack);
assert.deepEqual(capture.contributing,[8]);
assert.deepEqual([...capture.rgba.slice((128*256+128)*4,(128*256+128)*4+4)],[75,69,65,48],'tail alpha-only prefill follows separate native floor passes');
assert.equal(capture.rgba[(255*256)*4+3],48);
const initial=new Uint8Array(256*256*4);initial.set([11,22,33,7]);
assert.deepEqual([...captureNativeGarage(empty,{initialRGBA:initial}).rgba.slice(0,4)],[11,22,33,48],'alpha-only tail prefill preserves prior RGB');
for(const [alpha,expected] of [[127,48],[128,128],[255,255]]) {
 initial.set([11,22,33,alpha]);
 assert.deepEqual([...captureNativeGarage(empty,{initialRGBA:initial}).rgba.slice(0,4)],[11,22,33,expected],'DATE admits destination alpha high-bit0 only');
}
assert.throws(()=>captureNativeGarage({...pack,native_gs:{...pack.native_gs,passes:[record(9,0)]}}),/unsupported visible material 9/);
assert.deepEqual(captureNativeGarage({...empty,native_gs:{...pack.native_gs,passes:[record(9,0,{hidden:true})]}}).contributing,[]);
const hiddenRecord={...record(9,0,{hidden:true}),draw_index:0,batch_offset:3,source_packet_sha256:'source-sha'};
const proven={...pack,draws:[{material_index:9,native:{packet:'source',batch_offset:3}}],native_packets:{source:{sha256:'source-sha'}},
 native_gs:{...pack.native_gs,visibility_controls:{0:[hiddenRecord],192:[hiddenRecord]}}};
assert.deepEqual(captureNativeGarage(proven).rgba,capture.rgba,'both native culling controls prove complete hidden source geometry');
assert.throws(()=>captureNativeGarage({...proven,native_gs:pack.native_gs}),/visibility controls are required/);
assert.throws(()=>captureNativeGarage({...proven,native_gs:{...proven.native_gs,visibility_controls:{0:[],192:[hiddenRecord]}}}),/Incomplete native/);
assert.throws(()=>captureNativeGarage({...proven,native_packets:{source:{sha256:'changed'}}}),/source binding changed/);
assert.throws(()=>captureNativeGarage({...proven,native_gs:{...proven.native_gs,visibility_controls:{0:[{...hiddenRecord,gif_chunks:record(9,0).gif_chunks}],192:[hiddenRecord]}}}),/geometry reaches the native GS scissor/);
const skyRecord=record(-1,0,{sky:true,z:1,colour:[55,55,55,127]});
const withSky={...pack,native_gs:{...pack.native_gs,passes:[...pack.native_gs.passes,skyRecord]},sky:{draws:[],images:{test:solid([128,128,128,128])}}};
assert.deepEqual([...captureNativeGarage(withSky).rgba.slice((128*256+128)*4,(128*256+128)*4+4)],[75,69,65,48],'native floor depth survives prefill and occludes later sky');
const skyOnly=captureNativeGarage({...withSky,native_gs:{...pack.native_gs,passes:[skyRecord]}});
assert.deepEqual([...skyOnly.rgba.slice((128*256+128)*4,(128*256+128)*4+4)],[55,55,55,127]);
const differentPaint={...pack,native_gs:{...pack.native_gs,passes:[record(8,0,{colour:[64,32,16,128]})]}};
assert.deepEqual([...captureNativeGarage(differentPaint).rgba.slice((128*256+128)*4,(128*256+128)*4+4)],[64,32,16,48],'actual emitted RGBA drives shading rather than the old hardcoded floor colour');
const decoded=decodeEnvironmentImage({width:1,height:1,rgba_base64:Buffer.from([1,2,3,4]).toString('base64')});
assert.deepEqual([...decoded.data],[1,2,3,4]);
assert.throws(()=>decodeEnvironmentImage({width:2,height:1,rgba_base64:'AAAAAA=='}),/byte count/);
const texture=nativeSpecularTexture(new Uint8Array(256*256*4));
assert.equal(texture.image.width,64);assert.equal(texture.flipY,false);texture.dispose();
const angleProof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/panorama-angle.json',import.meta.url)));
const angleBits=new DataView(new ArrayBuffer(4)),angleFloat=word=>{angleBits.setUint32(0,word,true);return angleBits.getFloat32(0,true);};
for(const row of angleProof.angles){angleBits.setFloat32(0,nativeAtan2(angleFloat(row.x_word),angleFloat(row.z_word)),true);assert.equal(angleBits.getUint32(0,true),row.angle_word,'original scalar angle every bit');}
for(const row of angleProof.callers)assert.equal(nativePanoramaOffset(angleFloat(row.x_word),angleFloat(row.z_word),row.width),row.offset16,'original caller/native virtual image width/CVT.W every integer');
assert.throws(()=>nativePanoramaOffset(1,1,513),/width/);
assert.deepEqual([[0,1],[1,0],[0,-1],[-1,0],[1,1],[2,-3]].map(([x,z])=>nativePanoramaOffset(x,z)),[0,2047,4096,6144,1023,3329]);
assert.equal(nativeAtan2(0,-1),-Math.fround(Math.PI));assert.equal(nativeAtan2(0,0),0);
const base=new Uint8Array(256*256*4);base.set([250,4,7,48]);
assert.deepEqual([...addNativePanorama(base,solid([128,128,128,0]),0).slice(0,4)],[255,131,134,48]);
assert.throws(()=>addNativePanorama(base,solid([0,0,0,0]),.5),/sixteenth/);
const encoded=rgba=>({width:1,height:1,rgba_base64:Buffer.from(rgba).toString('base64')});
const packed={...pack,images:{floorBase:encoded([128,128,128,23]),floorLightmap:encoded([0,0,0,128]),panorama:encoded([128,128,128,0])}};
const renderer={};let fetches=0;
assert.equal(nativeGarageAssetURL('https://example.test/carmodels/mc3-environment.mjs'),'https://example.test/carmodels/public/midnight-club-3-remix/environment/native-garage.json');
assert.equal(nativeGarageAssetURL('https://example.test/nested/showcase/mc3-environment.mjs?revision=2'),'https://example.test/nested/showcase/public/midnight-club-3-remix/environment/native-garage.json');
const fetchImpl=async url=>{fetches++;assert.equal(url,nativeGarageAssetURL());return {ok:true,json:async()=>packed};};
const [first,second]=await Promise.all([prepareMC3Environment(renderer,{fetchImpl}),prepareMC3Environment(renderer,{fetchImpl})]);
assert.equal(first,second);assert.equal(fetches,1);assert.equal(nativeGarageProvider(renderer),first);
assert.equal(first.updateOffset(0),true);assert.equal(first.updateOffset(0),false);assert.equal(first.updateOffset(1),true);
assert.deepEqual([...first.texture.image.data.slice((32*64+32)*4,(32*64+32)*4+4)],[200,194,190,48],'floor, alpha prefill and panorama precede independent native64 gain');
const camera={matrixWorld:{elements:[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},updateMatrixWorld(){},getWorldDirection(){assert.fail('native panorama reads camera right, not forward');}};
assert(first.updateCamera(camera));assert.equal(first.updateCamera(camera),false,'unchanged camera-right offset is cached');
camera.matrixWorld.elements[0]=0;camera.matrixWorld.elements[2]=-1;
assert(first.updateCamera(camera),'orbiting camera changes native panorama offset');
camera.matrixWorld.elements[12]=100;
assert.equal(first.updateCamera(camera),false,'camera translation cannot affect native camera-right yaw');
let disposed=0;first.texture.addEventListener('dispose',()=>disposed++);disposeMC3Environment(renderer);disposeMC3Environment(renderer);
assert.equal(disposed,1);assert.throws(()=>nativeGarageProvider(renderer),/not prepared/);assert.throws(()=>first.updateOffset(0),/disposed/);
await assert.rejects(prepareMC3Environment(renderer,{fetchImpl:async()=>({ok:false,status:404})}),/could not be loaded \(404\)/);
await prepareMC3Environment(renderer,{fetchImpl});assert.equal(fetches,2,'failed source loading is retryable');disposeMC3Environment(renderer);
await prepareMC3Environment(renderer,{url:'https://assets.example.test/native-garage.json',fetchImpl:async url=>{
 assert.equal(url,'https://assets.example.test/native-garage.json');return {ok:true,json:async()=>packed};
}});disposeMC3Environment(renderer);
// The complete native capture matches independently executed official
// PCSX2 v2.8.2 software GS AVX2/FMA; physical hardware is a separate claim.
const sourcePack=JSON.parse(fs.readFileSync(new URL('../dealership/public/midnight-club-3-remix/environment/native-garage.json',import.meta.url)));
const sourceDecoded={...sourcePack,images:Object.fromEntries(Object.entries(sourcePack.images).map(([key,image])=>[key,decodeEnvironmentImage(image)])),
 sky:{...sourcePack.sky,images:Object.fromEntries(Object.entries(sourcePack.sky.images).map(([key,image])=>[key,decodeEnvironmentImage(image)]))}};
assert.equal(sourcePack.draws.length,416,'all selected original garage draw packets remain inputs');
let floorTriangles=0;
for(const draw of sourcePack.draws.filter(draw=>draw.material_index===8))for(let i=0;i<draw.indices.length;i+=3) {
 const [a,b,c]=draw.indices.slice(i,i+3).map(index=>draw.positions.slice(index*3,index*3+3));
 const crossY=(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]);
 assert(crossY>0&&a[1]<sourcePack.camera.eye[1],'authored floor triangles face the original camera above the floor');floorTriangles++;
}
assert.equal(floorTriangles,176);
const sourceCapture=captureNativeGarage(sourceDecoded);
assert.deepEqual(sourceCapture.contributing,[8,'sky']);
assert.deepEqual(sourceCapture.coverage,{uncovered:0,sky:0,floor:65536},'floor covers every pixel, so preserved prefill RGB is unexposed');
assert.equal(createHash('sha256').update(sourceCapture.rgba).digest('hex'),'9fa63bae26862424b078221da7422ff994093aba857eb800d0e02dc58ec3caba','independent three-frame official GS replay after base, lightmap and DATE alpha prefill');
assert(sourceCapture.rgba.every((value,index)=>index%4!==3||value===48),'native tail prefill replaces every final floor alpha with48');
const sourceTexture=nativeSpecularTexture(sourceCapture.rgba);
assert(sourceTexture.image.data.every((value,index)=>index%4!==3||value===48),'native64 copy preserves corrected native alpha48');sourceTexture.dispose();
assert.deepEqual(captureNativeGarage(sourceDecoded,{initialRGBA:new Uint8Array(256*256*4).fill(255)}).rgba,sourceCapture.rgba,'source floor coverage erases any prior RGB before panorama composition');
assert.throws(()=>captureNativeGarage({...sourceDecoded,native_gs:{...sourceDecoded.native_gs,passes:sourceDecoded.native_gs.passes.map(pass=>pass.material_index===8?{...pass,material_index:9}:pass)}}),/unsupported visible material 9/);
console.log('PASS test_mc3_environment: executed native GIF capture matches official GS golden, separate base/lightmap and DATE48→sky phases, emitted RGBA modulation, integer depth/scissor/material guard, native64 alpha48, image validation, nested module URLs, shared provider retry/cache/disposal');
