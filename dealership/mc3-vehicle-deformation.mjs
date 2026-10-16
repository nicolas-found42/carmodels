// Original carpaint VU007c..009f morph preprocessing. Runtime palette/state
// remains explicit; this supplies no collision or rider simulation.
import {nativeVUAdd as add,nativeVUMultiply as mul} from './mc3-vehicle-math.mjs';

export function nativeVehicleDeformVertex(position,morph,scale,paletteWeights) {
 if(!Array.isArray(position)||position.length!==3||!position.every(x=>Number.isInteger(x)&&x>=-32768&&x<=32767))throw Error('Invalid native position integers.');
 if(!Array.isArray(morph)||morph.length!==4||!morph.every(x=>Number.isInteger(x)&&x>=0&&x<=255))throw Error('Invalid native morph bytes.');
 if(!Number.isFinite(scale)||!Array.isArray(paletteWeights)||paletteWeights.length!==16||!paletteWeights.every(Number.isFinite))throw Error('Invalid native morph palette.');
 const weight=Math.fround(paletteWeights[morph[3]&15]),s=Math.fround(scale);
 return position.map((value,i)=>add(mul(add(morph[i],-127.5),weight),mul(value,s)));
}
