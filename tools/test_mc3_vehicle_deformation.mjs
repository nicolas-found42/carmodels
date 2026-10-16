import assert from 'node:assert/strict';
import fs from 'node:fs';
import {nativeVehicleDeformVertex} from '../dealership/mc3-vehicle-deformation.mjs';
import {nativeFloatWords} from '../dealership/mc3-vehicle-math.mjs';
const root=new URL('../research/evidence/midnight-club-3-remix/previews/',import.meta.url);
const proof=JSON.parse(fs.readFileSync(new URL('vehicle-deformation.json',root)));
const animation=JSON.parse(fs.readFileSync(new URL('vehicle-animation.json',root)));
const bits=new DataView(new ArrayBuffer(4));
const value=word=>{bits.setUint32(0,word,true);return bits.getFloat32(0,true);};
for(const probe of proof.probes) {
 const palette=animation.numerical_probes.find(p=>p.kind==='morph'&&p.state_byte===probe.state_byte).output.palette_words.map(row=>value(row[3]));
 proof.inputs.positions.forEach((position,i)=>assert.deepEqual(nativeFloatWords(nativeVehicleDeformVertex(position,proof.inputs.morphs[i],proof.inputs.position_scale,palette)),probe.output_words[i].slice(0,3)));
}
const palette=Array(16).fill(1);
assert.deepEqual(nativeVehicleDeformVertex([0,0,0],[127,128,255,255],1,palette),[-.5,.5,127.5]);
assert.throws(()=>nativeVehicleDeformVertex([32768,0,0],[0,0,0,0],1,palette));
assert.throws(()=>nativeVehicleDeformVertex([0,0,0],[256,0,0,0],1,palette));
assert.throws(()=>nativeVehicleDeformVertex([0,0,0],[0,0,0,0],Infinity,palette));
assert.throws(()=>nativeVehicleDeformVertex([0,0,0],[0,0,0,0],1,[1]));
console.log('PASS:42 original VU vertex outputs across7 original EE palette states; selector/bias/input controls.');
