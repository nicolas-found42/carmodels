import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {packNativeVehicleState} from '../dealership/mc3-vehicle-state.mjs';
const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-state.json',import.meta.url)));
assert.equal(proof.source_executable_sha256,'1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d');
assert.equal(proof.contexts.length,32);
for(const context of proof.contexts) {
 const actual=packNativeVehicleState(context);
 assert.deepEqual(actual.gs.map(([register,value])=>[register,String(value)]),context.gs,context.name+' native GS register words');
 assert.deepEqual(actual.vu,context.vu,context.name+' native VIF uniform words');
}
const context=proof.contexts[0];
assert.throws(()=>packNativeVehicleState({}),/Explicit/);
assert.throws(()=>packNativeVehicleState({...context,bpp:16}),/Unsupported/);
assert.throws(()=>packNativeVehicleState({...context,colorMode:0}),/color mode/);
for(const [index,value,reason] of [[0,8,/lookup/],[10,4,/lookup/],[15,3,/lookup/],[3,7,/blend/],[5,256,/selector/]]) {
 const changed=structuredClone(context);changed.words[index]=value;assert.throws(()=>packNativeVehicleState(changed),reason);
}
console.log('PASS all32 original EE state controls: literal GS blend/test/write registers and VU flags/colors');
console.log('PASS source lookup, selector and explicit framebuffer profile refusal');
