// Correct the static GT4 preview's material interpretation without rewriting its
// recovered geometry, PNGs or factory variants. This is not native PS2 shading.
export const GT4_MATERIAL_PROFILE='gt4-preview-materials-v1';
const NATIVE_CUTOFF=63/255;
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const specular=m=>{const a=m?.extras?.gt4_material?.specular;return Array.isArray(a)&&a.length===4&&a.every(Number.isFinite)?a.slice(0,3):[0,0,0];};
function nativeDefinition(m) {
 if(!m||typeof m!=='object')return false;
 const p=m.pbrMetallicRoughness,n=m.extras?.gt4_material;
 if(n!==undefined&&(!n||!Array.isArray(n.diffuse)||n.diffuse.length!==4||!n.diffuse.every(Number.isFinite)))return false;
 const expected=n?n.diffuse.map(x=>Math.max(0,Math.min(1,x))):[1,1,1,1];
 return /^body\/set\d+\/tex\d+\/mat-?\d+(?:\+vc)?\/(?:MASK|BLEND)\/paint\d+$/.test(m.name??'')&&
  p?.baseColorTexture&&equal(p.baseColorFactor,expected)&&p.metallicFactor===0;
}

// Repo-produced PNGs are RGBA8, non-interlaced, filter 0. Preserve an unknown
// encoding rather than guessing its pixels. Bound the inflated data as it streams.
export async function greenMarkerPixels(bytes) {
 if(bytes.length<33||![137,80,78,71,13,10,26,10].every((x,i)=>bytes[i]===x))return null;
 const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),width=v.getUint32(16),height=v.getUint32(20);
 if(!width||!height||width>1024||height>1024||bytes[24]!==8||bytes[25]!==6||bytes[26]||bytes[27]||bytes[28])return null;
 const parts=[];let at=8,ended=false;
 while(at+12<=bytes.length) {
  const n=v.getUint32(at);if(at+12+n>bytes.length)return null;
  const kind=String.fromCharCode(...bytes.subarray(at+4,at+8));
  if(kind==='IDAT')parts.push(bytes.subarray(at+8,at+8+n));
  if(kind==='IEND'){ended=true;break;}at+=12+n;
 }
 if(!ended||!parts.length)return null;
 const limit=(width*4+1)*height,reader=new Blob(parts).stream().pipeThrough(new DecompressionStream('deflate')).getReader();
 const chunks=[];let size=0;
 try {
  for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();return null;}chunks.push(value);}
 } catch {return null;} finally {reader.releaseLock();}
 if(size!==limit)return null;
 const raw=new Uint8Array(size);let offset=0;for(const c of chunks){raw.set(c,offset);offset+=c.length;}
 let count=0,transparentKey=0,visibleColour=0;
 for(let y=0;y<height;y++) {
  const start=y*(width*4+1);if(raw[start]!==0)return null;
  for(let x=0;x<width;x++){const i=start+1+x*4;if(raw[i]===8&&raw[i+1]===255&&[16,55].includes(raw[i+2])&&raw[i+3]>=63)count++;if(raw[i]===8&&raw[i+1]===255&&raw[i+2]===16&&raw[i+3]===0)transparentKey++;if(raw[i+3]>0&&(raw[i]||raw[i+1]||raw[i+2]))visibleColour++;}
 }
 return {count,total:width*height,transparentKey,visibleColour};
}

function encode(buffer,doc) {
 const json=new TextEncoder().encode(JSON.stringify(doc)),length=(json.length+3)&~3,original=new DataView(buffer),chunks=[];let at=12;
 while(at<buffer.byteLength){const n=original.getUint32(at,true);if(original.getUint32(at+4,true)!==0x4e4f534a)chunks.push(new Uint8Array(buffer,at,n+8));at+=n+8;}
 const result=new ArrayBuffer(20+length+chunks.reduce((s,c)=>s+c.length,0)),view=new DataView(result),bytes=new Uint8Array(result);
 view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,result.byteLength,true);view.setUint32(12,length,true);view.setUint32(16,0x4e4f534a,true);
 bytes.fill(32,20,20+length);bytes.set(json,20);at=20+length;for(const c of chunks){bytes.set(c,at);at+=c.length;}return result;
}

export async function correctGT4Materials(buffer,parsed,{sourceHash}={}) {
 if(parsed.doc.extras?.source_profile!=='gt4-ps2-static-car-v2')return {buffer,report:null};
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),v=>v.toString(16).padStart(2,'0')).join('');
 if(sourceHash!==undefined&&sourceHash!==hash)throw Error('GT4 material correction source hash mismatch.');
 const prior=parsed.doc.extras.gt4MaterialRepair;
 if(prior) {
  if(prior.profile!==GT4_MATERIAL_PROFILE)return {buffer,report:null};
  if(!/^[a-f0-9]{64}$/.test(prior.sourceSha256??'')||!Array.isArray(prior.cutouts)||!Array.isArray(prior.glass)||!Array.isArray(prior.frames))throw Error('Invalid GT4 material correction provenance.');
  return {buffer,report:prior};
 }
 const doc=structuredClone(parsed.doc),cutouts=[],glass=[],frames=[],images=new Map(),paintTargets=new Set();
 // A finish-bearing native material identifies a surface across all its factory
 // variants, including black-paint variants whose specular input becomes zero.
 for(const mesh of doc.meshes)if(mesh.name==='body')for(const primitive of mesh.primitives) {
  const ids=[primitive.material,...(primitive.extensions?.KHR_materials_variants?.mappings??[]).map(m=>m.material)];
  if(ids.some(i=>specular(doc.materials[i]).some(x=>x>0)))
   for(const i of ids)if(doc.materials[i]?.extras?.gt4_material)paintTargets.add(i);
 }
 for(const [index,m] of doc.materials.entries()) {
  if(!nativeDefinition(m))continue;
  if(paintTargets.has(index)&&m.alphaMode==='MASK'&&m.alphaCutoff===NATIVE_CUTOFF) {
   // Native paint alpha also carries finish information. Keep any nonzero texel;
   // actual holes still have alpha zero. Preserve artist-authored cutoff values.
   m.alphaCutoff=1/255;m.pbrMetallicRoughness.baseColorFactor[3]=1;cutouts.push(index);
  }
  const p=m.pbrMetallicRoughness;
  const finish=m.extras?.dealershipFinish,strength=Math.max(...specular(m));
  const defaultFinish=p.roughnessFactor===.7&&!m.extensions||finish==='native-specular-artistic-translation'&&p.roughnessFactor===.3&&
   equal(m.extensions,{KHR_materials_clearcoat:{clearcoatFactor:Math.min(1,strength),clearcoatRoughnessFactor:.18}});
  const keyedFrame=m.alphaMode==='MASK'&&m.alphaCutoff===NATIVE_CUTOFF&&!m.extras?.gt4_material&&/\/mat-1\/MASK\//.test(m.name);
  if((m.alphaMode!=='BLEND'&&!keyedFrame)||!defaultFinish||p.baseColorFactor[3]<=0||
     p.baseColorFactor[0]<=0||!p.baseColorFactor.slice(0,3).every(x=>x===p.baseColorFactor[0])||
     m.normalTexture||p.metallicRoughnessTexture)continue;
  const image=doc.textures?.[p.baseColorTexture.index]?.source;
  if(!Number.isInteger(image)||!parsed.images[image])continue;
  if(!images.has(image))images.set(image,await greenMarkerPixels(parsed.images[image]));
  const marker=images.get(image);
  if(!marker)continue;
  if(keyedFrame) {
   // Opaque texels in this exact frame pattern are black; green is entirely
   // transparent padding. Black RGB removes bilinear green fringes, not graphics.
   if(marker.transparentKey<marker.total/4||marker.visibleColour)continue;
   p.baseColorFactor=[0,0,0,1];m.extras={...m.extras,dealershipFinish:'neutral-keyed-frame-preview'};
   frames.push({material:index,image,keyPixels:marker.transparentKey,pixels:marker.total});continue;
  }
  if(marker.count<marker.total/4)continue;
  // These canonical green marker passes are not usable glass colour. A neutral
  // translucent fallback retains texture alpha/contours and leaves RGB bytes intact.
  p.baseColorFactor=[0,0,0,.35];p.roughnessFactor=.16;
  if(finish==='native-specular-artistic-translation'){delete m.extensions?.KHR_materials_clearcoat;if(!Object.keys(m.extensions??{}).length)delete m.extensions;}
  m.extras={...m.extras,dealershipFinish:'neutral-glass-preview-fallback'};
  glass.push({material:index,image,markerPixels:marker.count,pixels:marker.total});
 }
 if(!cutouts.length&&!glass.length&&!frames.length)return {buffer,report:null};
 const report={profile:GT4_MATERIAL_PROFILE,sourceSha256:hash,cutouts,glass,frames,claimLimits:[
  'GT4 static-preview material correction; recovered geometry, PNG bytes and factory variant mappings are retained.',
  'Finish-bearing native body MASK materials retain nonzero texture alpha; alpha-zero cutouts remain transparent.',
  'Black window-frame masks retain their alpha; neutral RGB removes green transparent-padding filter fringes.',
  'Canonical green-marker BLEND passes use neutral translucent glass as a preview fallback, not recovered native GT4 glass shading.',
  'Different source profiles, authored factors/cutoffs and unrecognized texture encodings remain unchanged.']};
 doc.extras={...doc.extras,gt4MaterialRepair:report};return {buffer:encode(buffer,doc),report};
}
