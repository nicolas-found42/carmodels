// Bounded read-only pilot. Native evidence is retained separately from display nodes.
export const MC3_INSPECTION_MODEL='midnight-club-3-remix/vp_350z_04';

export function formatMC3Value(value) {
 return value===null||value===undefined||value===''?'Unknown':String(value);
}

export function pickRecord(hits) {
 const eligible=hits.filter(hit=>hit.visible!==false&&Number.isFinite(hit.distance)&&hit.distance>0&&typeof hit.identity==='string');
 eligible.sort((a,b)=>a.distance-b.distance||(a.identity<b.identity?-1:a.identity>b.identity?1:0));
 return eligible[0]?.identity??null;
}

function multiply(a,b) {
 return Array.from({length:16},(_,i)=>{
  const row=i%4,column=Math.floor(i/4);
  return [0,1,2,3].reduce((sum,k)=>sum+a[row+k*4]*b[k+column*4],0);
 });
}

function localFrame(joint) {
 const position=joint?.local_position,angles=joint?.rotation_raw;
 if(!position||!angles)return null;
 if(position.length!==3||angles.length!==3||![...position,...angles].every(Number.isFinite))throw Error('MC3 transform mismatch: invalid native frame.');
 const [x,y,z]=angles,cx=Math.cos(x),sx=Math.sin(x),cy=Math.cos(y),sy=Math.sin(y),cz=Math.cos(z),sz=Math.sin(z);
 // Native rest convention Rz*Ry*Rx, in column-major affine layout.
 return [cz*cy,sz*cy,-sy,0,cz*sy*sx-sz*cx,sz*sy*sx+cz*cx,cy*sx,0,cz*sy*cx+sz*sx,sz*sy*cx-cz*sx,cy*cx,0,...position,1];
}

function worldFrame(bones,index,active=new Set()) {
 const joint=bones?.[index];
 if(!joint)return null;
 if(active.has(index))throw Error('MC3 transform mismatch: cyclic parent chain.');
 const local=localFrame(joint);
 if(!local||joint.parent===undefined)return null;
 if(joint.parent===null)return local;
 active.add(index);
 const parent=worldFrame(bones,joint.parent,active);
 active.delete(index);
 return parent?multiply(parent,local):null;
}

function requireMatrix(actual,expected,label) {
 if(actual&&(!Array.isArray(expected)||expected.length!==16||actual.some((value,i)=>!Number.isFinite(expected[i])||Math.abs(value-expected[i])>1e-6)))throw Error('MC3 transform mismatch: '+label+'.');
}

function displayFrame(node) {
 if(node.matrix)return node.matrix;
 if(!node.translation||!node.rotation||!node.scale)return null;
 const [x,y,z,w]=node.rotation,[sx,sy,sz]=node.scale;
 return [(1-2*(y*y+z*z))*sx,2*(x*y+z*w)*sx,2*(x*z-y*w)*sx,0,
  2*(x*y-z*w)*sy,(1-2*(x*x+z*z))*sy,2*(y*z+x*w)*sy,0,
  2*(x*z+y*w)*sz,2*(y*z-x*w)*sz,(1-2*(x*x+y*y))*sz,0,...node.translation,1];
}

/** Validate and expose only the two pinned native records; absent metadata stays null. */
export function inspectMC3Records(doc,evidence) {
 if(evidence?.schema!==1||evidence.modelId!==MC3_INSPECTION_MODEL||doc?.extras?.car!=='vp_350z_04')throw Error('MC3 pilot input mismatch.');
 const bones=doc.extras.nativeSkeleton?.bones;
 return evidence.records.map(expected=>{
  const records=doc.extras.records?.filter(record=>record.role===expected.identity)??[];
  const nodes=(doc.nodes??[]).map((node,index)=>({node,index})).filter(({node})=>node.name===expected.identity);
  if(records.length!==1||nodes.length!==1)throw Error('MC3 ownership mismatch: missing or ambiguous pilot identity.');
  const record=records[0],{node,index:nodeIndex}=nodes[0];
  if(nodeIndex!==expected.nodeIndex||record.bone!==expected.bone||node.extras?.nativeBone!==expected.bone)throw Error('MC3 ownership mismatch: native bone or node binding.');
  const primitive=doc.meshes?.[node.mesh]?.primitives?.[0],vif=primitive?.extras?.native_vif;
  if(vif&&(vif.source_packet_offset!==expected.firstPacketOffset||vif.source_carrier_sha256!==expected.sourceHash))throw Error('MC3 ownership mismatch: source occurrence.');
  if(record.native_sha256!==undefined&&record.native_sha256!==expected.sourceHash)throw Error('MC3 ownership mismatch: source hash.');
  const source=doc.extras.nativeResources?.find(resource=>resource.sha256===record.native_sha256);
  if(source&&source.file!==evidence.source.file)throw Error('MC3 ownership mismatch: source resource.');
  const joint=bones?.[record.bone],parent=joint?.parent===null?null:bones?.[joint?.parent];
  const parentIdentity=joint?.parent===null?'None (native root)':parent?.name??null;
  if((joint?.parent===null&&expected.parentIdentity!==null)||(parent&&parent.name!==expected.parentIdentity))throw Error('MC3 ownership mismatch: parent identity.');
  const localMatrix=localFrame(joint),worldMatrix=worldFrame(bones,record.bone);
  requireMatrix(localMatrix,expected.localMatrix,'local rest frame');
  requireMatrix(worldMatrix,expected.worldMatrix,'parent-chain world frame');
  requireMatrix(displayFrame(node),expected.worldMatrix,'display placement');
  const sourceHash=record.native_sha256??null;
  return {identity:expected.identity,nodeIndex,sourceOccurrence:vif&&source?expected.sourceOccurrence:null,sourceHash,parentIdentity,localMatrix,worldMatrix};
 });
}
