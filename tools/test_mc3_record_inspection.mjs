import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {inspectMC3Records,pickRecord,formatMC3Value} from '../dealership/mc3-record-inspection.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));
const evidence=JSON.parse(fs.readFileSync(root+'dealership/mc3-record-evidence.json'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const [path,hash] of Object.entries(evidence.files))assert.equal(sha(fs.readFileSync(root+path)),hash,'pinned pilot input: '+path);
const source=fs.readFileSync(root+'games/midnight-club-3-remix/cars/'+evidence.source.file);
const pointer=offset=>source.readUInt32LE(offset)-source.readUInt32LE(0)+128;
const text=offset=>source.subarray(offset,source.indexOf(0,offset)).toString('ascii');
const group=evidence.source.highGroupOffset;
assert.equal(source.readUInt16LE(group),2);
const meshes=pointer(group+8),names=pointer(group+12),boneIndices=pointer(group+16);

// Independent direct reads of original PCK collection and joint bytes. No exporter is invoked.
for(const expected of evidence.records) {
 const index=expected.partIndex;
 assert.equal(text(pointer(names+index*4)),expected.identity);
 assert.equal(pointer(meshes+index*4),expected.meshOffset);
 assert.equal(source.readUInt32LE(boneIndices+index*4),expected.bone);
 const descriptors=pointer(expected.meshOffset+16),firstDescriptor=pointer(descriptors);
 assert.equal(pointer(firstDescriptor),expected.firstPacketOffset);
 assert.equal(expected.sourceOccurrence,evidence.source.file+'#part='+index+'#mesh='+expected.meshOffset+'#packet='+expected.firstPacketOffset);
}

// Independent quaternion/basis-vector composition, reading original joint fields directly.
function nativeFrame(index) {
 const retained=evidence.joints[index],offset=retained.offset;
 const angles=[0,1,2].map(i=>source.readFloatLE(offset+44+i*4)/2);
 const [sx,sy,sz]=angles.map(Math.sin),[cx,cy,cz]=angles.map(Math.cos);
 const q=[sx*cy*cz-cx*sy*sz,cx*sy*cz+sx*cy*sz,cx*cy*sz-sx*sy*cz,cx*cy*cz+sx*sy*sz];
 const rotate=([px,py,pz])=>{
  const [x,y,z,w]=q,tx=2*(y*pz-z*py),ty=2*(z*px-x*pz),tz=2*(x*py-y*px);
  return [px+w*tx+y*tz-z*ty,py+w*ty+z*tx-x*tz,pz+w*tz+x*ty-y*tx];
 };
 const matrix=[...rotate([1,0,0]),0,...rotate([0,1,0]),0,...rotate([0,0,1]),0,
  ...[0,1,2].map(i=>source.readFloatLE(offset+32+i*4)),1];
 return matrix;
}
function nativeWorld(index) {
 const matrix=nativeFrame(index),parent=evidence.joints[index].parent;
 if(parent===null)return matrix;
 const ancestor=nativeWorld(parent),result=[];
 for(let column=0;column<4;column++)for(let row=0;row<4;row++) {
  let total=0;for(let k=0;k<4;k++)total+=ancestor[k*4+row]*matrix[column*4+k];
  result.push(total);
 }
 return result;
}
for(const expected of evidence.records)for(const [key,actual] of [['localMatrix',nativeFrame(expected.bone)],['worldMatrix',nativeWorld(expected.bone)]]) {
 for(let i=0;i<16;i++)assert.ok(Math.abs(actual[i]-expected[key][i])<=1e-6,'raw PCK independent '+key+' component '+i);
}
for(const joint of evidence.joints) {
 assert.equal(text(pointer(joint.offset+12)),joint.name);
 assert.equal(source.readUInt16LE(joint.offset+56),joint.index);
 const parentPointer=source.readUInt32LE(joint.offset+28);
 assert.equal(parentPointer?pointer(joint.offset+28):null,joint.parent_offset);
 for(let i=0;i<3;i++) {
  assert.equal(source.readFloatLE(joint.offset+32+i*4),joint.local_position[i]);
  assert.equal(source.readFloatLE(joint.offset+44+i*4),joint.rotation_raw[i]);
 }
}

const glb=fs.readFileSync(root+'games/midnight-club-3-remix/recovered-models/vp_350z_04.glb');
assert.equal(sha(glb),evidence.sourceGlbSha256);
const doc=JSON.parse(glb.subarray(20,20+glb.readUInt32LE(12)));
const baseline=JSON.stringify(doc),result=inspectMC3Records(doc,evidence);
assert.equal(result.length,2);
for(const actual of result) {
 const expected=evidence.records.find(row=>row.identity===actual.identity);
 for(const key of ['nodeIndex','sourceOccurrence','sourceHash'])assert.equal(actual[key],expected[key]);
 assert.equal(actual.parentIdentity,expected.parentIdentity??'None (native root)');
 for(const key of ['localMatrix','worldMatrix'])for(let i=0;i<16;i++)assert.ok(Math.abs(actual[key][i]-expected[key][i])<=1e-6,key+' component '+i);
}
assert.equal(JSON.stringify(doc),baseline,'inspection does not mutate source');
const lf=result.find(row=>row.identity.includes('Arm_Front_L'));
const body=result.find(row=>row.identity.includes('HLOD_HLOD'));
const rebound=structuredClone(doc);
rebound.nodes[lf.nodeIndex].mesh=rebound.nodes[body.nodeIndex].mesh;
assert.throws(()=>inspectMC3Records(rebound,evidence),/ownership mismatch: source occurrence/);
const translated=structuredClone(doc);
translated.extras.nativeSkeleton.bones[1].local_position[0]+=.1;
assert.throws(()=>inspectMC3Records(translated,evidence),/transform mismatch: parent-chain world frame/);
const moved=structuredClone(doc);moved.nodes[lf.nodeIndex].translation[0]+=.1;
assert.throws(()=>inspectMC3Records(moved,evidence),/transform mismatch: display placement/);
const reparented=structuredClone(doc);reparented.extras.nativeSkeleton.bones[2].parent=null;
assert.throws(()=>inspectMC3Records(reparented,evidence),/ownership mismatch: parent identity/);
const missing=structuredClone(doc);delete missing.extras.nativeSkeleton.bones[2].rotation_raw;
assert.equal(formatMC3Value(inspectMC3Records(missing,evidence)[0].localMatrix),'Unknown');
assert.equal(formatMC3Value(undefined),'Unknown');
assert.equal(formatMC3Value(0),'0');
const hit=(identity,distance,visible=true)=>({identity,distance,visible});
assert.equal(pickRecord([hit('body',2),hit('front',1)]),'front');
assert.equal(pickRecord([hit('z',1),hit('a',1)]),'a');
assert.equal(pickRecord([hit('hidden',.5,false),hit('zero',0),hit('behind',-1),hit('nan',NaN),hit('front',2)]),'front');
assert.equal(pickRecord([]),null);
console.log('PASS MC3 pilot pins, independent PCK ownership/joints, metadata/rest matrices, ownership and parent/display transform controls, Unknown fields, deterministic positive visible hit selection.');
