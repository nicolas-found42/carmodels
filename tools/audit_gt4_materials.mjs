// Offline independent checks for the derived GT4 material correction. No model writes.
import fs from 'node:fs';
import path from 'node:path';
import {inflateSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {readGLB} from '../dealership/model-load.mjs';
import {parseEditableGLB} from '../dealership/editable-glb.mjs';
import {correctGT4Materials,GT4_MATERIAL_PROFILE} from '../dealership/gt4-materials.mjs';
const sha=b=>createHash('sha256').update(new Uint8Array(b)).digest('hex');
const equal=(a,b,why)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(why);};
const arrayBuffer=b=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);

// Independent synchronous decoder for the source exporter's RGBA8/filter0 PNGs.
export function markerCount(png) {
 const b=Buffer.from(png),w=b.readUInt32BE(16),h=b.readUInt32BE(20),chunks=[];
 if(b[24]!==8||b[25]!==6||b[28]||w>1024||h>1024)return null;
 for(let at=8;at+12<=b.length;){const n=b.readUInt32BE(at),kind=b.toString('ascii',at+4,at+8);if(kind==='IDAT')chunks.push(b.subarray(at+8,at+8+n));at+=12+n;}
 const raw=inflateSync(Buffer.concat(chunks),{maxOutputLength:(w*4+1)*h});
 if(raw.length!==(w*4+1)*h)throw Error('Unexpected PNG size.');
 let count=0,transparentKey=0,visibleColour=0;for(let y=0;y<h;y++){const start=y*(w*4+1);if(raw[start])return null;for(let x=0;x<w;x++){const i=start+1+4*x;if(raw[i]===8&&raw[i+1]===255&&(raw[i+2]===55||raw[i+2]===16)&&raw[i+3]>=63)count++;if(raw[i]===8&&raw[i+1]===255&&raw[i+2]===16&&raw[i+3]===0)transparentKey++;if(raw[i+3]>0&&(raw[i]||raw[i+1]||raw[i+2]))visibleColour++;}}
 return {count,total:w*h,transparentKey,visibleColour};
}

export function verifyGT4MaterialRepair(originalBuffer,correctedBuffer) {
 const a=readGLB(originalBuffer),b=readGLB(correctedBuffer),parsed=parseEditableGLB(originalBuffer),out=parseEditableGLB(correctedBuffer),declared=b.doc.extras?.gt4MaterialRepair,r=declared??{profile:GT4_MATERIAL_PROFILE,sourceSha256:sha(originalBuffer),cutouts:[],glass:[],frames:[]};
 if(!declared&&sha(originalBuffer)!==sha(correctedBuffer))throw Error('Changed GLB lacks repair provenance.');
 if(!r||r.profile!==GT4_MATERIAL_PROFILE||r.sourceSha256!==sha(originalBuffer))throw Error('Material repair provenance mismatch.');
 if(sha(a.bin)!==sha(b.bin))throw Error('Material repair changed binary geometry or images.');
 const x=structuredClone(a.doc),y=structuredClone(b.doc);delete x.materials;delete y.materials;delete y.extras.gt4MaterialRepair;
 equal(x,y,'Material repair changed non-material document data.');
 const cutouts=new Set(r.cutouts),glass=new Map(r.glass.map(g=>[g.material,g])),frames=new Map(r.frames.map(g=>[g.material,g]));
 if(cutouts.size!==r.cutouts.length||glass.size!==r.glass.length||frames.size!==r.frames.length)throw Error('Duplicate corrected material.');
 if(a.doc.materials.length!==b.doc.materials.length)throw Error('Material count changed.');
 const targets=new Set(),markers=new Map();
 for(const mesh of a.doc.meshes)if(mesh.name==='body')for(const primitive of mesh.primitives) {
  const ids=[primitive.material,...(primitive.extensions?.KHR_materials_variants?.mappings??[]).map(m=>m.material)];
  if(ids.some(i=>Array.isArray(a.doc.materials[i]?.extras?.gt4_material?.specular)&&a.doc.materials[i].extras.gt4_material.specular.length===4&&a.doc.materials[i].extras.gt4_material.specular.every(Number.isFinite)&&a.doc.materials[i].extras.gt4_material.specular.slice(0,3).some(x=>Number.isFinite(x)&&x>0)))
   for(const i of ids)if(a.doc.materials[i]?.extras?.gt4_material)targets.add(i);
 }
 for(let i=0;i<a.doc.materials.length;i++) {
  const before=a.doc.materials[i],after=b.doc.materials[i],expected=structuredClone(before),p=before.pbrMetallicRoughness,n=before.extras?.gt4_material;
  const diffuse=n?.diffuse,validNative=n===undefined||Array.isArray(diffuse)&&diffuse.length===4&&diffuse.every(Number.isFinite);
  const factor=validNative?(diffuse?.map(x=>Math.max(0,Math.min(1,x)))??[1,1,1,1]):null;
  const recognized=validNative&&/^body\/set\d+\/tex\d+\/mat-?\d+(?:\+vc)?\/(?:MASK|BLEND)\/paint\d+$/.test(before.name??'')&&p?.baseColorTexture&&p.metallicFactor===0&&JSON.stringify(p.baseColorFactor)===JSON.stringify(factor);
  const mustCut=recognized&&targets.has(i)&&before.alphaMode==='MASK'&&before.alphaCutoff===63/255;
  if(cutouts.has(i)!==!!mustCut)throw Error('Missing or extra expected body cutout correction.');
  const strength=Array.isArray(n?.specular)&&n.specular.length===4&&n.specular.every(Number.isFinite)?Math.max(...n.specular.slice(0,3)):0;
  const defaultFinish=p?.roughnessFactor===.7&&!before.extensions||before.extras?.dealershipFinish==='native-specular-artistic-translation'&&p?.roughnessFactor===.3&&JSON.stringify(before.extensions)===JSON.stringify({KHR_materials_clearcoat:{clearcoatFactor:Math.min(1,strength),clearcoatRoughnessFactor:.18}});
  let mustGlass=false,mustFrame=false;
  const image=a.doc.textures?.[p?.baseColorTexture?.index]?.source;
  if(recognized&&defaultFinish&&!before.normalTexture&&!p.metallicRoughnessTexture&&p.baseColorFactor[3]>0&&p.baseColorFactor[0]>0&&p.baseColorFactor.slice(0,3).every(x=>x===p.baseColorFactor[0])&&parsed.images[image]) {
   if(!markers.has(image))markers.set(image,markerCount(parsed.images[image]));const marker=markers.get(image);
   mustGlass=before.alphaMode==='BLEND'&&!!marker&&marker.count>=marker.total/4;
   mustFrame=before.alphaMode==='MASK'&&before.alphaCutoff===63/255&&!n&&/\/mat-1\/MASK\//.test(before.name)&&!!marker&&marker.transparentKey>=marker.total/4&&!marker.visibleColour;
  }
  if(glass.has(i)!==mustGlass||frames.has(i)!==mustFrame)throw Error('Missing or extra expected glass/frame correction.');
  if(cutouts.has(i)) {
   if(before.alphaMode!=='MASK'||before.alphaCutoff!==63/255)throw Error('Incorrect cutout correction target.');
   expected.alphaCutoff=1/255;expected.pbrMetallicRoughness.baseColorFactor[3]=1;
   if(after.alphaCutoff<=0||after.alphaCutoff>31/255)throw Error('Bumper alpha cutout is still broken.');
  }
  if(glass.has(i)) {
   const g=glass.get(i),image=a.doc.textures[before.pbrMetallicRoughness.baseColorTexture.index].source,marker=markerCount(parsed.images[image]);
   if(before.alphaMode!=='BLEND'||!marker||marker.count<marker.total/4)throw Error('Incorrect green-marker correction target.');
   equal([g.image,g.markerPixels,g.pixels],[image,marker.count,marker.total],'Green marker evidence mismatch.');
   expected.pbrMetallicRoughness.baseColorFactor=[0,0,0,.35];expected.pbrMetallicRoughness.roughnessFactor=.16;
   if(before.extras?.dealershipFinish==='native-specular-artistic-translation'){delete expected.extensions?.KHR_materials_clearcoat;if(!Object.keys(expected.extensions??{}).length)delete expected.extensions;}
   expected.extras={...expected.extras,dealershipFinish:'neutral-glass-preview-fallback'};
  }
  if(frames.has(i)) {
   const f=frames.get(i),image=a.doc.textures[before.pbrMetallicRoughness.baseColorTexture.index].source,marker=markerCount(parsed.images[image]);
   if(before.alphaMode!=='MASK'||!marker||marker.transparentKey<marker.total/4||marker.visibleColour)throw Error('Incorrect keyed-frame target.');
   equal([f.image,f.keyPixels,f.pixels],[image,marker.transparentKey,marker.total],'Frame evidence mismatch.');
   expected.pbrMetallicRoughness.baseColorFactor=[0,0,0,1];expected.extras={...expected.extras,dealershipFinish:'neutral-keyed-frame-preview'};
  }
  equal(after,expected,'Unexpected material mutation.');
 }
 for(const i of [...cutouts,...glass.keys(),...frames.keys()])if(!Number.isInteger(i)||i<0||i>=a.doc.materials.length)throw Error('Invalid corrected material index.');
 equal(out.images,parsed.images,'Embedded image bytes changed.');
 return {cutouts:cutouts.size,glass:glass.size,frames:frames.size};
}

// Audit the current input. Reimports preserve historical provenance; without the
// pre-repair checkpoint we can verify preservation, not re-prove that derivation.
export async function auditGT4MaterialCar(buffer,expectedHash) {
 const hash=sha(buffer);if(hash!==expectedHash)throw Error('Working catalog hash mismatch.');
 const parsed=parseEditableGLB(buffer),prior=parsed.doc.extras?.gt4MaterialRepair;
 const result=await correctGT4Materials(buffer,parsed,{sourceHash:hash});
 if(prior?.profile===GT4_MATERIAL_PROFILE&&result.report===prior) {
  if(result.buffer!==buffer||sha(result.buffer)!==hash)throw Error('Already-corrected input changed.');
  return {buffer:result.buffer,status:'already-corrected',cutouts:0,glass:0,frames:0};
 }
 if(parsed.doc.extras?.source_profile!=='gt4-ps2-static-car-v2'||prior) {
  if(result.buffer!==buffer)throw Error('Unknown profile changed.');
  return {buffer:result.buffer,status:'unsupported-profile',cutouts:0,glass:0,frames:0};
 }
 const counts=verifyGT4MaterialRepair(buffer,result.buffer);
 return {buffer:result.buffer,status:result.report?'corrected':'unchanged',...counts};
}

export async function auditGT4Materials(root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')) {
 const cars=JSON.parse(fs.readFileSync(path.join(root,'dealership/public/dealership/cars.json'))).filter(c=>c.game==='gran-turismo-4');
 const source=JSON.parse(fs.readFileSync(path.join(root,'dealership/public/gran-turismo-4/index.json'))),sourceCars=source.cars;
 const rows=[];let cutouts=0,glass=0,frames=0,correctedCars=0,alreadyCorrectedCars=0;
 for(const c of cars) {
  const file=path.join(root,'dealership',c.model.source.glb),data=fs.readFileSync(file),buffer=arrayBuffer(data),hash=sha(buffer);
  if(hash!==c.model.source.sha256)throw Error('Working catalog hash mismatch.');
  const native=sourceCars.find(s=>s.code===c.sourceCode),sourceFile=path.join(root,'dealership/public/gran-turismo-4',native.file);
  const sourceData=fs.readFileSync(sourceFile);if(sha(sourceData)!==native.sha256)throw Error('Source catalog hash mismatch.');
  const result=await auditGT4MaterialCar(buffer,hash);
  const {buffer:derived,...counts}=result;
  if(native.sha256!==hash){await auditGT4MaterialCar(arrayBuffer(sourceData),native.sha256);}
  if(sha(fs.readFileSync(file))!==hash||sha(fs.readFileSync(sourceFile))!==native.sha256)throw Error('Stored model changed.');
  cutouts+=counts.cutouts;glass+=counts.glass;frames+=counts.frames;correctedCars+=Number(result.status==='corrected');alreadyCorrectedCars+=Number(result.status==='already-corrected');
  rows.push({car:c.sourceCode,sourceSha256:native.sha256,workingSha256:hash,correctedSha256:sha(derived),...counts});
 }
 return {cars:cars.length,correctedCars,alreadyCorrectedCars,cutoutMaterials:cutouts,glassMaterials:glass,frameMaterials:frames,claim_limits:[
  'All default working files processed; source and working pins verified unchanged. Fresh corrections preserve geometry, texture bytes, variant mappings and non-material JSON.',
  'Already-corrected reimports are verified unchanged with zero new corrections; historical repairs are not re-derived without the pre-repair checkpoint. Unknown profiles are preserved.',
  'Cutout counts are material corrections, not an all-car visual review. Alpha-zero texels remain cutouts.',
  'Canonical green-marker glass is a neutral translucent preview fallback, not native shader reconstruction.'],rows};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
 const result=await auditGT4Materials();const at=process.argv.indexOf('--output');if(at>=0)fs.writeFileSync(process.argv[at+1],JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 const {rows,...summary}=result;console.log(JSON.stringify(summary));
}
