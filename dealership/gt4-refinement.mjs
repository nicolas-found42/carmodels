// Dealership-only derivation. Source corner positions and render-attribute seams
// remain anchors. Curved PN triangles: Vlachos et al., I3D 2001.
// This is bounded interpolation of recovered art, not recovered GT4 subdivision.
export const GT4_REFINEMENT_PROFILE='gt4-dealership-pn-v1';
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const add=(a,b)=>a.map((v,i)=>v+b[i]);
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const mul=(a,k)=>a.map(v=>v*k);
const length=a=>Math.hypot(...a);
const unit=a=>mul(a,1/(length(a)||1));
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const mix=(rows,bary)=>rows[0].map((_,i)=>rows.reduce((s,r,j)=>s+r[i]*bary[j],0));
const row=(array,index,width=3)=>Array.from(array.subarray(index*width,(index+1)*width));

function optionsFor(options) {
 const o={segments:4,maxDisplacement:.006,maxVertices:600000,...options};
 if(!Number.isInteger(o.segments)||o.segments<2||o.segments>8||!Number.isFinite(o.maxDisplacement)||
    o.maxDisplacement<=0||o.maxDisplacement>.02||!Number.isInteger(o.maxVertices)||o.maxVertices<3||o.maxVertices>1000000)
  throw Error('Invalid GT4 refinement limits.');
 return o;
}

// Work within each render domain. Open, nonmanifold, hard-normal and sharp
// dihedral edges are linear. Adjacent smooth faces evaluate identical edge curves.
export function refineGT4Primitive(primitive,options={}) {
 const o=optionsFor(options),p=primitive,faces=[],edges=new Map();
 const fallback=reason=>({primitive:p,report:{status:'retained',reason,sourceTriangles:p.indices.length/3,triangles:p.indices.length/3,maxDisplacement:0}});
 if(p.positions.length/3*o.segments*o.segments>o.maxVertices)return fallback('vertex-budget');
 for(let at=0;at<p.indices.length;at+=3) {
  const ids=Array.from(p.indices.subarray(at,at+3)),points=ids.map(i=>row(p.positions,i)),normals=ids.map(i=>unit(row(p.normals,i)));
  const faceNormal=cross(sub(points[1],points[0]),sub(points[2],points[0]));
  const valid=length(faceNormal)>1e-12&&normals.every(n=>dot(n,unit(faceNormal))>.15);
  const face={index:at/3,ids,points,normals,faceNormal:unit(faceNormal),valid,edges:[]};
  for(let i=0;i<3;i++) {
   const a=ids[i],b=ids[(i+1)%3],key=a<b?`${a}:${b}`:`${b}:${a}`;
   if(!edges.has(key))edges.set(key,[]);
   edges.get(key).push(face);face.edges.push(key);
  }
  faces.push(face);
 }
 const smooth=new Set();
 for(const [key,pair] of edges)if(pair.length===2&&pair.every(f=>f.valid)&&dot(pair[0].faceNormal,pair[1].faceNormal)>.7071) {
  const [a,b]=key.split(':').map(Number);
  if(dot(unit(row(p.normals,a)),unit(row(p.normals,b)))>.5)smooth.add(key);
 }
 const positions=[],normals=[],uv=[],colors=[],indices=[],sourceTriangles=[],barycentrics=[];let curvedFaces=0,maxDisplacement=0;
 function append(face,bary,point) {
  // Validate the same Float32 geometry that will reach the GLB/GPU. Tiny source
  // triangles can collapse after quantization even when doubles looked valid.
  const index=positions.length/3;positions.push(...point.map(Math.fround));normals.push(...unit(mix(face.normals,bary)));
  sourceTriangles.push(face.index);barycentrics.push(bary[1],bary[2]);
  if(p.uv)uv.push(...mix(face.ids.map(i=>row(p.uv,i,2)),bary));
  if(p.colors)colors.push(...mix(face.ids.map(i=>row(p.colors,i,p.colorWidth)),bary));
  return index;
 }
 for(const face of faces) {
  if(!face.valid||!face.edges.some(key=>smooth.has(key))) {
   indices.push(...face.points.map((point,i)=>append(face,[Number(i===0),Number(i===1),Number(i===2)],point)));continue;
  }
  curvedFaces++;
  const controls=[];
  for(let i=0;i<3;i++)for(const [a,b] of [[i,(i+1)%3],[(i+1)%3,i]]) {
   const correction=smooth.has(face.edges[i])?dot(sub(face.points[b],face.points[a]),face.normals[a]):0;
   controls.push(mul(sub(add(mul(face.points[a],2),face.points[b]),mul(face.normals[a],correction)),1/3));
  }
  const centre=mul(controls.reduce(add,[0,0,0]),1/6),vertexCentre=mul(face.points.reduce(add,[0,0,0]),1/3);
  const middle=add(centre,mul(sub(centre,vertexCentre),.5));
  function evaluate(bary) {
   const [u,v,w]=bary,weights=[3*u*u*v,3*u*v*v,3*v*v*w,3*v*w*w,3*w*w*u,3*w*u*u];
   let point=add(mix(face.points,[u*u*u,v*v*v,w*w*w]),mul(middle,6*u*v*w));
   controls.forEach((c,i)=>{point=add(point,mul(c,weights[i]));});
   const linear=mix(face.points,bary),delta=sub(point,linear),distance=length(delta);
   if(distance>o.maxDisplacement)point=add(linear,mul(delta,o.maxDisplacement/distance));
   maxDisplacement=Math.max(maxDisplacement,Math.min(distance,o.maxDisplacement));
   return point;
  }
  const grid=[];
  for(let i=0;i<=o.segments;i++) {
   grid[i]=[];
   for(let j=0;j<=o.segments-i;j++) {
    const bary=[1-(i+j)/o.segments,i/o.segments,j/o.segments];
    grid[i][j]=append(face,bary,evaluate(bary));
   }
  }
  function triangle(a,b,c) {
   const normal=cross(sub(positions.slice(b*3,b*3+3),positions.slice(a*3,a*3+3)),sub(positions.slice(c*3,c*3+3),positions.slice(a*3,a*3+3)));
   if(length(normal)<1e-14||dot(unit(normal),face.faceNormal)<.1)return false;
   indices.push(a,b,c);return true;
  }
  for(let i=0;i<o.segments;i++)for(let j=0;j<o.segments-i;j++) {
   if(!triangle(grid[i][j],grid[i+1][j],grid[i][j+1]))return fallback('folded-surface');
   if(j<o.segments-i-1&&!triangle(grid[i+1][j],grid[i+1][j+1],grid[i][j+1]))return fallback('folded-surface');
  }
 }
 if(!curvedFaces||maxDisplacement<1e-8)return fallback('no-supported-curvature');
 if(positions.length/3>o.maxVertices)return fallback('vertex-budget');
 return {primitive:{...p,positions:Float32Array.from(positions),normals:Float32Array.from(normals),
  indices:Uint32Array.from(indices),uv:p.uv?Float32Array.from(uv):null,colors:p.colors?Float32Array.from(colors):null,
  sourceTriangles:Uint32Array.from(sourceTriangles),sourceBarycentrics:Float32Array.from(barycentrics)},
 report:{status:'refined',sourceTriangles:p.indices.length/3,triangles:indices.length/3,curvedFaces,maxDisplacement}};
}

function encode(doc,chunks) {
 const binaryLength=chunks.reduce((sum,b)=>sum+b.byteLength,0),text=new TextEncoder().encode(JSON.stringify(doc)),n=(text.length+3)&~3;
 const buffer=new ArrayBuffer(28+n+binaryLength),view=new DataView(buffer),bytes=new Uint8Array(buffer);
 view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,buffer.byteLength,true);
 view.setUint32(12,n,true);view.setUint32(16,0x4e4f534a,true);bytes.fill(32,20,20+n);bytes.set(text,20);
 view.setUint32(20+n,binaryLength,true);view.setUint32(24+n,0x004e4942,true);
 let offset=28+n;for(const chunk of chunks){bytes.set(new Uint8Array(chunk.buffer,chunk.byteOffset,chunk.byteLength),offset);offset+=chunk.byteLength;}
 return buffer;
}

function modernMaterials(doc) {
 const counts={nativeSpecular:0,tires:0,unchanged:0};
 for(const m of doc.materials) {
  const pbr=m.pbrMetallicRoughness;
  // Only translate the known exporter defaults. An artist's working finish is
  // already a deliberate dealership edit, even when native extras remain.
  if(!pbr||pbr.roughnessFactor!==.7||pbr.metallicFactor!==0||m.extensions||m.normalTexture||pbr.metallicRoughnessTexture) {counts.unchanged++;continue;}
  // A native tyre node/material identity is meaningful; arbitrary display names
  // and differences between paint presets are not paint-region masks.
  const tire=/^tire_(front|rear)\//.test(m.name??''),native=m.extras?.gt4_material;
  const spec=native?.specular?.slice(0,3),specular=Array.isArray(spec)&&spec.length===3&&spec.every(Number.isFinite)?Math.max(...spec):0;
  if(!tire&&specular<=0){counts.unchanged++;continue;}
  if(tire){m.pbrMetallicRoughness.roughnessFactor=.88;counts.tires++;}
  else {
   m.pbrMetallicRoughness.roughnessFactor=.3;
   m.extensions={...m.extensions,KHR_materials_clearcoat:{clearcoatFactor:Math.min(1,specular),clearcoatRoughnessFactor:.18}};
   counts.nativeSpecular++;
  }
  m.extras={...m.extras,dealershipFinish:tire?'rubber':'native-specular-artistic-translation'};
 }
 if(counts.nativeSpecular)doc.extensionsUsed=[...new Set([...(doc.extensionsUsed??[]),'KHR_materials_clearcoat'])];
 return counts;
}

// The parsed input must come from parseEditableGLB, which validates the static
// profile and all accessors. Appended data never overwrites original image bytes.
export function enhanceGT4GLB(buffer,parsed,{sourceHash,...options}={}) {
 if(parsed.doc.extras?.gt4Enhancement) {
  const report=parsed.doc.extras.gt4Enhancement;
  if(report.profile!==GT4_REFINEMENT_PROFILE)return {buffer,report:null};
  if(!Array.isArray(report.parts)||!Array.isArray(report.claimLimits))throw Error('Invalid GT4 enhancement provenance.');
  return {buffer,report};
 }
 if(parsed.doc.extras?.source_profile!=='gt4-ps2-static-car-v2')return {buffer,report:null};
 if(!/^[a-f0-9]{64}$/.test(sourceHash??''))throw Error('GT4 enhancement needs a verified source hash.');
 const o=optionsFor(options),doc=structuredClone(parsed.doc),chunks=[new Uint8Array(buffer).slice(0,0)];
 // Keep all original bytes and bufferViews, including palettes and native metadata.
 const original=new DataView(buffer);let cursor=12,bin;
 while(cursor<buffer.byteLength){const size=original.getUint32(cursor,true);if(original.getUint32(cursor+4,true)===0x004e4942)bin=new Uint8Array(buffer,cursor+8,size);cursor+=8+size;}
 chunks[0]=bin;let offset=bin.byteLength;
 const reports=[];let vertices=0;
 function accessor(array,width,index=false) {
  const data=index?new Uint32Array(array):new Float32Array(array),v=doc.bufferViews.length;
  doc.bufferViews.push({buffer:0,byteOffset:offset,byteLength:data.byteLength});chunks.push(new Uint8Array(data.buffer));offset+=data.byteLength;
  const a={bufferView:v,componentType:index?5125:5126,count:array.length/width,type:{1:'SCALAR',2:'VEC2',3:'VEC3',4:'VEC4'}[width]};
  if(!index&&width===3){a.min=[Infinity,Infinity,Infinity];a.max=[-Infinity,-Infinity,-Infinity];for(let i=0;i<array.length;i++) {const k=i%3;a.min[k]=Math.min(a.min[k],array[i]);a.max[k]=Math.max(a.max[k],array[i]);}}
  doc.accessors.push(a);return doc.accessors.length-1;
 }
 parsed.meshes.forEach((primitives,mesh)=>primitives.forEach((p,primitive)=>{
  // No remeshing of unknown attributes or alpha-cutout silhouettes (grilles,
  // badges and billboards). Their original geometry remains the fallback.
  const source=doc.meshes[mesh].primitives[primitive],material=doc.materials[source.material];
  const unknown=Object.keys(source.attributes).some(k=>!['POSITION','NORMAL','TEXCOORD_0','COLOR_0'].includes(k));
  const remaining=o.maxVertices-vertices;
  const result=unknown||material.alphaMode==='MASK'||remaining<3?
   {primitive:p,report:{status:'retained',reason:unknown?'unknown-attribute':material.alphaMode==='MASK'?'cutout-boundary':'vertex-budget',sourceTriangles:p.indices.length/3,triangles:p.indices.length/3,maxDisplacement:0}}:
   refineGT4Primitive(p,{...o,maxVertices:remaining});
  reports.push({mesh,primitive,...result.report});
  if(result.report.status!=='refined')return;
  const refined=result.primitive;vertices+=refined.positions.length/3;
  const provenance={attributes:structuredClone(source.attributes),indices:source.indices,
   triangleAccessor:accessor(refined.sourceTriangles,1,true),barycentricAccessor:accessor(refined.sourceBarycentrics,2)};
  source.extras={...source.extras,gt4Refinement:provenance};
  source.attributes={POSITION:accessor(refined.positions,3),NORMAL:accessor(refined.normals,3)};
  if(refined.uv)source.attributes.TEXCOORD_0=accessor(refined.uv,2);
  if(refined.colors)source.attributes.COLOR_0=accessor(refined.colors,p.colorWidth);
  source.indices=accessor(refined.indices,1,true);
 }));
 const report={profile:GT4_REFINEMENT_PROFILE,sourceSha256:sourceHash,car:doc.extras.car,segments:o.segments,
  displacementLimitMetres:o.maxDisplacement,materials:modernMaterials(doc),parts:reports,
  referenceStatus:'No verified exact-car reconstruction supplied; conservative native-mesh refinement.',
  claimLimits:['Enhanced dealership edition; not original game rendering.',
   'Source corners and render-domain boundaries are retained; new curved samples are bounded interpolations, not measured real-car detail.',
   'Material response is an artistic translation of native specular inputs and known tyre parts. Unidentified finishes remain unchanged.',
   'No real-car dimension or hidden-detail correction is inferred from an unmatched photograph.']};
 for(const sampler of doc.samplers??[])sampler.minFilter=9987;
 doc.extras={...doc.extras,gt4Enhancement:report};doc.buffers[0].byteLength=offset;
 return {buffer:encode(doc,chunks),report};
}
