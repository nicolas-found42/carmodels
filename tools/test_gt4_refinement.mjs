import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import * as THREE from '../dealership/vendor/three.module.js';
import {refineGT4Primitive,enhanceGT4GLB,GT4_REFINEMENT_PROFILE} from '../dealership/gt4-refinement.mjs';
import {parseEditableGLB,loadEditableGLB} from '../dealership/editable-glb.mjs';
import {createPaintSession} from '../dealership/game-paint.mjs';
import {exportPaintGLB} from '../dealership/paint-export.mjs';
import {createMaterial,applyMaterial} from '../dealership/materials.mjs';
import {disposeCar} from '../dealership/dealership.mjs';
import {auditGT4Car,verifyGT4Enhancement} from './audit_gt4_refinement.mjs';
import {readGLB} from '../dealership/model-load.mjs';

const primitive={positions:Float32Array.from([0,0,0,1,0,0,1,1,0,0,1,0]),
 normals:Float32Array.from([-.3,-.3,1,.3,-.3,1,.3,.3,1,-.3,.3,1]),
 indices:Uint32Array.from([0,1,2,0,2,3]),uv:Float32Array.from([0,0,1,0,1,1,0,1]),
 colors:Float32Array.from([0,0,0,1,0,0,1,1,0,0,1,0]),colorWidth:3};
const original=structuredClone(primitive),refined=refineGT4Primitive(primitive);
assert.equal(refined.report.status,'refined');assert.equal(refined.report.triangles,32);
assert(refined.report.maxDisplacement>0&&refined.report.maxDisplacement<=.006);
assert.deepEqual(primitive,original,'input arrays are immutable');
const p=refined.primitive;let curved=0;
for(let i=0;i<p.positions.length/3;i++) {
 const [x,y,z]=p.positions.subarray(i*3,i*3+3);
 assert(Math.hypot(x-p.uv[i*2],y-p.uv[i*2+1],z)<=.006001,'new samples stay near their barycentric source position');
 assert(Math.abs(p.colors[i*3]-p.uv[i*2])<1e-7);
 if(x===0||x===1||y===0||y===1)assert.equal(z,0,'open boundaries stay on their original straight edge');
 if(Math.abs(z)>1e-7)curved++;
 assert(Math.abs(Math.hypot(...p.normals.subarray(i*3,i*3+3))-1)<1e-6);
}
assert(curved>0,'geometry really curves; this is not just a larger triangle count');
const diagonal=[];for(let i=0;i<p.positions.length;i+=3)if(p.positions[i]===.5&&p.positions[i+1]===.5)diagonal.push(p.positions[i+2]);
assert.equal(diagonal.length,2);assert.equal(diagonal[0],diagonal[1],'shared edge samples agree');
assert.equal(refineGT4Primitive(primitive,{maxVertices:3}).report.reason,'vertex-budget');
const flat={...primitive,normals:Float32Array.from([0,0,1,0,0,1,0,0,1,0,0,1])};
assert.equal(refineGT4Primitive(flat).report.reason,'no-supported-curvature');
// Two coincident but separate render domains must not be welded by position.
const split={positions:Float32Array.from([0,0,0,1,0,0,1,1,0,0,0,0,1,1,0,0,1,0]),
 normals:Float32Array.from([-.3,-.3,1,.3,-.3,1,.3,.3,1,-.3,-.3,1,.3,.3,1,-.3,.3,1]),indices:Uint32Array.from([0,1,2,3,4,5])};
assert.equal(refineGT4Primitive(split).report.status,'retained');
const tiny={...primitive,positions:Float32Array.from(primitive.positions,v=>100+v*.00002)};
assert.equal(refineGT4Primitive(tiny).report.reason,'folded-surface','Float32-collapsed triangles retain the original part');
for(const options of [{segments:1},{segments:9},{maxDisplacement:Infinity},{maxVertices:0}])assert.throws(()=>refineGT4Primitive(primitive,options),/Invalid GT4/);

const filename=new URL('../dealership/dealership/models/GT4_ACRA0001.glb',import.meta.url),bytes=fs.readFileSync(filename),buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
const sha=createHash('sha256').update(bytes).digest('hex'),parsed=parseEditableGLB(buffer),result=enhanceGT4GLB(buffer,parsed,{sourceHash:sha});
function rewriteJSON(buffer,mutate) {
 const {doc,bin}=readGLB(buffer);mutate(doc);
 const json=Buffer.from(JSON.stringify(doc)),length=(json.length+3)&~3,out=Buffer.alloc(28+length+bin.byteLength,32);
 out.writeUInt32LE(0x46546c67,0);out.writeUInt32LE(2,4);out.writeUInt32LE(out.length,8);
 out.writeUInt32LE(length,12);out.writeUInt32LE(0x4e4f534a,16);json.copy(out,20);
 out.writeUInt32LE(bin.byteLength,20+length);out.writeUInt32LE(0x004e4942,24+length);Buffer.from(bin).copy(out,28+length);
 return out.buffer.slice(out.byteOffset,out.byteOffset+out.byteLength);
}
assert.equal(result.report.profile,GT4_REFINEMENT_PROFILE);assert(result.report.parts.some(p=>p.status==='refined'));
const enhanced=parseEditableGLB(result.buffer);
assert.deepEqual(enhanced.doc.nodes,parsed.doc.nodes,'wheel assembly and mirrored transforms retained');
assert.deepEqual(enhanced.doc.extensions.KHR_materials_variants,parsed.doc.extensions.KHR_materials_variants);
assert.deepEqual(enhanced.images,parsed.images,'every embedded factory texture byte is retained');
assert(result.report.materials.nativeSpecular>0&&result.report.materials.tires>0&&result.report.materials.unchanged>0);
for(let i=0;i<parsed.doc.materials.length;i++) {
 const a=parsed.doc.materials[i],b=enhanced.doc.materials[i];
 assert.deepEqual(b.pbrMetallicRoughness.baseColorFactor,a.pbrMetallicRoughness.baseColorFactor);
 if(!b.extras?.dealershipFinish)assert.deepEqual(b,a,'uncertain materials remain unchanged');
}
assert.equal(enhanceGT4GLB(result.buffer,enhanced,{sourceHash:sha}).buffer,result.buffer,'enhanced downloads are not subdivided again');
assert.throws(()=>enhanceGT4GLB(buffer,parsed),/verified source hash/);
const unknown=structuredClone(parsed);unknown.doc.extras.source_profile='some-other-game';assert.equal(enhanceGT4GLB(buffer,unknown).report,null);
const audit=auditGT4Car(buffer,sha);assert(audit.refinedParts>0);assert(audit.triangles>audit.sourceTriangles);
assert.throws(()=>auditGT4Car(buffer,'0'.repeat(64)),/catalog hash/);
const edited=rewriteJSON(buffer,d=>{for(const m of d.materials) {m.pbrMetallicRoughness.roughnessFactor=.12;m.extensions={KHR_materials_clearcoat:{clearcoatFactor:.6}};}});
const editedHash=createHash('sha256').update(new Uint8Array(edited)).digest('hex');
const editedResult=enhanceGT4GLB(edited,parseEditableGLB(edited),{sourceHash:editedHash});
assert.equal(editedResult.report.materials.unchanged,parsed.doc.materials.length,'authored finishes are preserved');
assert.deepEqual(parseEditableGLB(editedResult.buffer).doc.materials,parseEditableGLB(edited).doc.materials);
const enhancedHash=createHash('sha256').update(new Uint8Array(result.buffer)).digest('hex');
assert.equal(auditGT4Car(result.buffer,enhancedHash).status,'already-enhanced','reimported enhanced files are not reprocessed or misreported as freshly audited');
// Mutation controls exercise the verifier independently of generator reports.
{
 const bad=result.buffer.slice(0),{doc}=readGLB(bad),part=result.report.parts.find(p=>p.status==='refined');
 const primitive=doc.meshes[part.mesh].primitives[part.primitive],a=doc.accessors[primitive.attributes.POSITION],v=doc.bufferViews[a.bufferView];
 const header=new DataView(bad),binAt=28+header.getUint32(12,true),view=new DataView(bad);
 view.setFloat32(binAt+v.byteOffset,view.getFloat32(binAt+v.byteOffset,true)+.1,true);
 assert.throws(()=>verifyGT4Enhancement(buffer,bad),/measured displacement limit/,'a forged unchanged report cannot hide vertex movement');
}
{
 const bad=result.buffer.slice(0),{doc}=readGLB(bad),part=result.report.parts.find(p=>p.status==='refined');
 const q=doc.meshes[part.mesh].primitives[part.primitive],a=doc.accessors[q.attributes.NORMAL],v=doc.bufferViews[a.bufferView];
 const view=new DataView(bad),binAt=28+view.getUint32(12,true);
 for(let axis=0;axis<3;axis++)view.setFloat32(binAt+v.byteOffset+axis*4,2,true);
 assert.throws(()=>verifyGT4Enhancement(buffer,bad),/normal length/);
}
const session=createPaintSession(enhanced.doc,{game:'gran-turismo-4'});session.setPreset(1);
const exported=parseEditableGLB(exportPaintGLB(result.buffer,session));
assert.deepEqual(exported.meshes.map(m=>m.map(p=>p.positions)),enhanced.meshes.map(m=>m.map(p=>p.positions)),'selected-paint downloads retain refined geometry');
assert.equal(exported.doc.extras.gt4Enhancement.profile,GT4_REFINEMENT_PROFILE);
const index=enhanced.doc.materials.findIndex(m=>m.extensions?.KHR_materials_clearcoat);
const material=createMaterial(enhanced.doc,[],index);assert(material.isMeshPhysicalMaterial);assert(material.clearcoat>0);
applyMaterial(material,{materials:[{pbrMetallicRoughness:{}}]},[],0);assert.equal(material.clearcoat,0,'material changes clear prior finish');
material.dispose();
const car={game:'gran-turismo-4',model:{source:{glb:'dealership/models/GT4_ACRA0001.glb',sha256:sha}}};
const load=options=>loadEditableGLB(car,{correctMaterials:false,fetchImpl:async()=>buffer,textureImpl:async()=>new THREE.Texture(),...options});
const group=await load();assert(group.userData.gt4Enhancement);assert.equal(group.userData.paintBuffer.byteLength,result.buffer.byteLength);
assert(group.userData.paintDoc.extras.gt4Enhancement);group.userData.setColourVariant(1);disposeCar(group);
const baseline=await load({enhance:false});assert.equal(baseline.userData.gt4Enhancement,null);assert.equal(baseline.userData.paintBuffer,buffer);disposeCar(baseline);
assert.equal(createHash('sha256').update(fs.readFileSync(filename)).digest('hex'),sha,'real working asset never written');
console.log('PASS test_gt4_refinement: curved samples, pinned edges/corners, split domains, bounded movement, fallback, UV/colour interpolation, real GLB variants/images/transforms, physical finish reset, enhanced download/reimport, disabled comparison and source preservation');
