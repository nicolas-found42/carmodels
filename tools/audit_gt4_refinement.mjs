// Re-derive every dealership enhancement without writing a model. Hash pins,
// source preservation, texture bytes, variants and bounded geometry are checked.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {parseEditableGLB} from '../dealership/editable-glb.mjs';
import {enhanceGT4GLB} from '../dealership/gt4-refinement.mjs';
import {readGLB} from '../dealership/model-load.mjs';

const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const arrayBuffer=bytes=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
function requireEqual(a,b,reason) {if(JSON.stringify(a)!==JSON.stringify(b))throw Error(reason);}

export function verifyGT4Enhancement(buffer,enhancedBuffer) {
 const parsed=parseEditableGLB(buffer),original=readGLB(buffer),enhanced=parseEditableGLB(enhancedBuffer),rebuilt=readGLB(enhancedBuffer);
 const report=enhanced.doc.extras.gt4Enhancement;
 if(report?.sourceSha256!==digest(new Uint8Array(buffer)))throw Error('Enhancement provenance hash mismatch.');
 if(!Number.isFinite(report.displacementLimitMetres)||report.displacementLimitMetres<=0||report.displacementLimitMetres>.02)throw Error('Invalid enhancement displacement policy.');
 const expectedParts=parsed.meshes.flatMap((ps,m)=>ps.map((_,p)=>`${m}:${p}`));
 requireEqual(report.parts.map(p=>`${p.mesh}:${p.primitive}`),expectedParts,'Refinement part coverage mismatch.');
 requireEqual(enhanced.doc.nodes,parsed.doc.nodes,'Enhancement changed assembly transforms.');
 requireEqual(enhanced.doc.extensions?.KHR_materials_variants,parsed.doc.extensions?.KHR_materials_variants,'Enhancement changed factory presets.');
 if(enhanced.images.length!==parsed.images.length||enhanced.images.some((image,i)=>digest(image)!==digest(parsed.images[i])))throw Error('Enhancement changed embedded textures.');
 const prefix=new Uint8Array(rebuilt.bin,0,original.bin.byteLength);
 if(digest(prefix)!==digest(new Uint8Array(original.bin)))throw Error('Enhancement changed original binary payload.');
 let measuredDisplacement=0;
 function values(index,width,componentType) {
  const a=enhanced.doc.accessors[index],v=enhanced.doc.bufferViews[a?.bufferView];
  if(!a||a.componentType!==componentType||a.type!==(width===1?'SCALAR':'VEC2')||v.byteStride||a.byteOffset||v.byteLength!==a.count*width*4)throw Error('Invalid refinement provenance accessor.');
  const Type=componentType===5125?Uint32Array:Float32Array;
  return new Type(rebuilt.bin,v.byteOffset,a.count*width);
 }
 for(const part of report.parts) {
  const a=parsed.meshes[part.mesh][part.primitive],b=enhanced.meshes[part.mesh][part.primitive];
  requireEqual(b.source.extensions,a.source.extensions,'Enhancement changed material mappings.');
  if(part.status==='retained') {
   if(digest(b.positions)!==digest(a.positions)||digest(b.indices)!==digest(a.indices))throw Error('Fallback changed original geometry.');
  } else {
   const provenance=b.source.extras?.gt4Refinement;
   requireEqual(provenance?.attributes,a.source.attributes,'Refinement lost original attribute provenance.');
   if(provenance.indices!==a.source.indices)throw Error('Refinement lost original index provenance.');
   const triangle=values(provenance.triangleAccessor,1,5125),bary=values(provenance.barycentricAccessor,2,5126);
   if(triangle.length!==b.positions.length/3||bary.length!==triangle.length*2)throw Error('Refinement sample coverage mismatch.');
   for(let i=0;i<triangle.length;i++) {
    const t=triangle[i],v=bary[i*2],w=bary[i*2+1],weights=[1-v-w,v,w];
    if(t>=a.indices.length/3||weights.some(x=>!Number.isFinite(x)||x<0||x>1))throw Error('Invalid source sample mapping.');
    let squared=0;
    for(let axis=0;axis<3;axis++) {
     const source=weights.reduce((s,k,j)=>s+k*a.positions[a.indices[t*3+j]*3+axis],0);
     squared+=(b.positions[i*3+axis]-source)**2;
    }
    const distance=Math.sqrt(squared);measuredDisplacement=Math.max(measuredDisplacement,distance);
    if(distance>report.displacementLimitMetres+1e-6)throw Error('Enhancement exceeded measured displacement limit.');
    for(const [name,width] of [['uv',2],['colors',a.colorWidth]])if(a[name])for(let axis=0;axis<width;axis++) {
     const expected=weights.reduce((s,k,j)=>s+k*a[name][a.indices[t*3+j]*width+axis],0);
     if(Math.abs(b[name][i*width+axis]-expected)>1e-6)throw Error('Enhancement changed attribute correspondence.');
    }
    if(Math.abs(Math.hypot(...b.normals.subarray(i*3,i*3+3))-1)>1e-5)throw Error('Invalid refined normal length.');
   }
   function normal(array,ids) {
    const [i,j,k]=ids.map(v=>v*3),u=[0,1,2].map(axis=>array[j+axis]-array[i+axis]),v=[0,1,2].map(axis=>array[k+axis]-array[i+axis]);
    return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
   }
   for(let at=0;at<b.indices.length;at+=3) {
    const ids=Array.from(b.indices.subarray(at,at+3)),face=triangle[ids[0]];
    if(ids.some(id=>triangle[id]!==face))throw Error('Triangle crosses source face mapping.');
    const before=normal(a.positions,Array.from(a.indices.subarray(face*3,face*3+3))),after=normal(b.positions,ids),denom=Math.hypot(...before)*Math.hypot(...after);
    if(Math.hypot(...before)>1e-12&&(Math.hypot(...after)<=1e-14||before.reduce((s,v,i)=>s+v*after[i],0)/denom<.099999))throw Error(`Refined triangle folds or degenerates (${part.mesh}:${part.primitive}, triangle ${at/3}).`);
   }
   const vertices=new Set();for(let i=0;i<b.positions.length;i+=3)vertices.add(`${b.positions[i]},${b.positions[i+1]},${b.positions[i+2]}`);
   for(let i=0;i<a.positions.length;i+=3)if(!vertices.has(`${a.positions[i]},${a.positions[i+1]},${a.positions[i+2]}`))throw Error('Enhancement lost a source corner.');
  }
 }
 return {report,measuredDisplacement};
}

export function auditGT4Car(buffer,sourceHash) {
 if(digest(new Uint8Array(buffer))!==sourceHash)throw Error('Working GLB differs from its catalog hash.');
 const parsed=parseEditableGLB(buffer),before=digest(new Uint8Array(buffer)),result=enhanceGT4GLB(buffer,parsed,{sourceHash});
 if(!result.report)throw Error('Unsupported GT4 source profile.');
 if(digest(new Uint8Array(buffer))!==before)throw Error('Enhancement mutated source bytes.');
 if(result.buffer===buffer) {
  const triangles=parsed.meshes.flat().reduce((s,p)=>s+p.indices.length/3,0);
  return {car:parsed.doc.extras.car,sourceSha256:sourceHash,enhancedSha256:sourceHash,bytes:buffer.byteLength,
   status:'already-enhanced',sourceTriangles:triangles,triangles,refinedParts:0,retainedReasons:{'already-enhanced':1},
   maxDisplacement:null,materials:result.report.materials};
 }
 const {measuredDisplacement}=verifyGT4Enhancement(buffer,result.buffer);
 return {car:result.report.car,sourceSha256:sourceHash,enhancedSha256:digest(new Uint8Array(result.buffer)),
  bytes:result.buffer.byteLength,sourceTriangles:result.report.parts.reduce((s,p)=>s+p.sourceTriangles,0),
  triangles:result.report.parts.reduce((s,p)=>s+p.triangles,0),
  refinedParts:result.report.parts.filter(p=>p.status==='refined').length,
  retainedReasons:result.report.parts.filter(p=>p.status==='retained').reduce((s,p)=>({...s,[p.reason]:(s[p.reason]??0)+1}),{}),
  maxDisplacement:measuredDisplacement,materials:result.report.materials};
}

export function auditGT4Collection(root) {
 const dealership=path.join(root,'dealership'),catalog=JSON.parse(fs.readFileSync(path.join(dealership,'public/dealership/cars.json')));
 const sourceIndex=JSON.parse(fs.readFileSync(path.join(dealership,'public/gran-turismo-4/index.json')));
 const sourceRows=new Map(sourceIndex.cars.map(row=>[row.code,row])),cars=[];
 for(const car of catalog.filter(c=>c.game==='gran-turismo-4')) {
  const filename=path.resolve(dealership,car.model.source.glb);
  if(!filename.startsWith(path.join(dealership,'dealership/models')+path.sep))throw Error('Unexpected dealership model path.');
  const source=sourceRows.get(car.sourceCode);
  if(!source||!source.file.startsWith('previews/')||source.file.includes('..'))throw Error('Missing source reference.');
  const sourcePath=path.join(dealership,'public/gran-turismo-4',source.file),sourceBefore=digest(fs.readFileSync(sourcePath));
  if(sourceBefore!==source.sha256)throw Error('Source GLB differs from its pinned hash.');
  const before=fs.readFileSync(filename);let row;
  try {row=auditGT4Car(arrayBuffer(before),car.model.source.sha256);}
  catch(error){throw Error(`${car.code}: ${error.message}`,{cause:error});}
  if(row.car!==car.sourceCode)throw Error('Enhancement source identity differs from catalog.');
  if(digest(fs.readFileSync(filename))!==digest(before)||digest(fs.readFileSync(sourcePath))!==sourceBefore)throw Error('Asset preservation failed.');
  cars.push(row);
 }
 if(!cars.length||cars.length!==sourceIndex.cars.length)throw Error('GT4 catalog coverage mismatch.');
 return {schema:1,profile:'gt4-dealership-pn-v1',cars,
  summary:{cars:cars.length,refinedCars:cars.filter(c=>c.refinedParts>0).length,refinedParts:cars.reduce((s,c)=>s+c.refinedParts,0),
   maxDisplacement:Math.max(...cars.map(c=>c.maxDisplacement))},
  claimLimits:['Structural and source-preservation audit; not visual proof of vehicle identity or photogrammetric accuracy.',
   'Generated GLBs were parsed, not rendered. No source or working model was written. No real-car dimension correction was inferred.',
   'Already-enhanced working files are retained without a second refinement; their prior or subsequent authored displacement is not revalidated.']};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
 const args=process.argv.slice(2);
 if(args.length!==0&&(args.length!==2||args[0]!=='--output'))throw Error('Usage: node tools/audit_gt4_refinement.mjs [--output new-receipt.json]');
 const root=fileURLToPath(new URL('../',import.meta.url)),receipt=auditGT4Collection(root);
 if(args.length)fs.writeFileSync(args[1],JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify(receipt.summary));
}
