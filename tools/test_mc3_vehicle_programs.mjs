import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeNativeVehiclePrograms,nativeVehicleProgramsURL} from '../dealership/mc3-vehicle-programs.mjs';
const source='1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d';
const bytes=new Uint8Array([60,3,0,128,255,2,0,64]),digest=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
const record=(index,variant)=>({index,variant,name:index===0?'builtin-'+variant:'program'+index,instructions:1,
 microcode_base64:Buffer.from(bytes).toString('base64'),microcode_sha256:digest});
const pack={schema:1,source_executable_sha256:source,programs:[record(0,'normal'),record(0,'alternate'),...Array.from({length:12},(_,i)=>record(i+1))]};
const registry=await decodeNativeVehiclePrograms(pack);
assert.equal(registry.program(0,0).source.variant,'normal');assert.equal(registry.program(0,128).source.variant,'alternate');
assert.equal(registry.program(12).code[0],0x8000033c);assert.equal(registry.program(12).code.length,4096);
assert.throws(()=>registry.program(0),/selector/);assert.throws(()=>registry.program(13),/index/);
registry.program(1).code[0]=0;assert.equal(registry.program(1).code[0],0x8000033c,'execution cannot mutate shared source programs');
assert.equal(nativeVehicleProgramsURL('https://example.test/subpath/dealership/mc3-vehicle-programs.mjs'),
 'https://example.test/subpath/dealership/public/midnight-club-3-remix/rendering/native-vehicle-programs.json');
for(const [mutate,reason] of [
 [p=>p.programs[0].microcode_base64='AAAA',/payload/],
 [p=>p.programs[0].microcode_sha256='0'.repeat(64),/payload/],
 [p=>p.programs[0].instructions=2049,/descriptor/],
 [p=>p.programs[1].variant='normal',/Duplicate/],
 [p=>p.programs[1].variant='guessed',/binding/],
 [p=>p.programs[1].index=13,/descriptor/],
 [p=>p.source_executable_sha256='0'.repeat(64),/pack/],
 [p=>p.programs.pop(),/pack/],
]) {const changed=structuredClone(pack);mutate(changed);await assert.rejects(()=>decodeNativeVehiclePrograms(changed),reason);}
console.log('PASS native registry, explicit builtin choice, instruction hashes, subpath URL and corruption controls');
if(process.argv[2]) {
 const actual=await decodeNativeVehiclePrograms(JSON.parse(readFileSync(process.argv[2])));
 for(let i=0;i<=12;i++)actual.program(i,0);
 actual.program(0,1);console.log('PASS all14 source-derived native program inputs');
}
