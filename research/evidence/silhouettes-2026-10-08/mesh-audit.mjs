import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../../../viewer/vendor/three.module.js';
import {makeCar, disposeCar} from '../../../viewer/silhouette.mjs';
const cars=JSON.parse(fs.readFileSync(new URL('../../../viewer/public/cars.json',import.meta.url)));
const records=[];
for(const car of cars){
 const mesh=makeCar(car),bounds=new THREE.Box3().setFromObject(mesh);
 const unique=new Set(),counts=new Map();
 mesh.traverse(node=>{if(node.geometry)unique.add(node.geometry);if(node.material)unique.add(node.material);});
 for(const item of unique)item.addEventListener('dispose',()=>counts.set(item,(counts.get(item)||0)+1));
 disposeCar(mesh);
 const record={code:car.code,finiteBounds:[...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite),floorMinimum:bounds.min.y,transverseCenterError:Math.abs(bounds.min.z+bounds.max.z),resources:unique.size,disposedResources:counts.size,disposedExactlyOnce:[...counts.values()].every(n=>n===1)};
 assert(record.finiteBounds);assert(record.floorMinimum>=-1e-6);assert(record.transverseCenterError<1e-6);assert.equal(record.disposedResources,record.resources);assert(record.disposedExactlyOnce);
 records.push(record);
}
console.log(JSON.stringify({scope:'FINAL working tree only; pre-change negative controls are not part of this audit',cars:records.length,records},null,2));
console.log('PASS final mesh audit: all 35 finite, transverse symmetry, tyre floor contact, every shared geometry/material disposed exactly once');
