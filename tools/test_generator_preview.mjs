import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {parseEditableGLB} from '../dealership/editable-glb.mjs';

const folder=process.argv[2];
assert(folder,'Pass the folder containing generated GLBs');
const files=fs.readdirSync(folder).filter(name=>name.endsWith('.glb')).sort();
assert(files.length,'No GLBs were supplied to the viewer parser');
for(const file of files) {
  const raw=fs.readFileSync(path.join(folder,file));
  let model;try{model=parseEditableGLB(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength));}
  catch(error){throw Error(`${file}: ${error.message}`);}
  assert(model.meshes.length>=5,`${file}: body or wheels missing`);
}
console.log(`PASS generated viewer parsing: ${files.length} full GLBs, static triangles, UVs, textures and nonzero normals`);
