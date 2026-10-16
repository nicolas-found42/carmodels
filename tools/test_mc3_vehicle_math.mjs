import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {nativeFloatWords,nativeVUAdd,nativeVUMultiply,nativeVUDivide,nativeVehicleVertex} from '../dealership/mc3-vehicle-math.mjs';

const proof=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-vu.json',import.meta.url)));
const bits=new DataView(new ArrayBuffer(4));
const floats=words=>words.map(word=>{bits.setUint32(0,word,true);return bits.getFloat32(0,true);});
for(const probe of proof.numerical_probes) {
 const memory={...proof.synthetic_probe_context.memory_rows,...probe.memory_overrides};
 const row=index=>floats(memory[index]);
 const input={program:probe.program,normal:memory[2].slice(0,3).map(word=>word|0),position:row(86).slice(0,3),
  mvp:[20,21,22,23].map(row),uvMatrix:[16,17,18].map(row),lightRows:[24,25,26].map(i=>row(i).slice(0,3)),
  lightColors:[28,29,30,31].map(row),material:row(42),parameters:row(53)};
 const actual=nativeVehicleVertex(input),kernel=proof.kernels[probe.program];
 assert.deepEqual(actual.rgba,probe.register_words[kernel.rgba_register],probe.name+' native RGBA');
 if(probe.program==='light_texgen_dc')assert.deepEqual(nativeFloatWords(actual.stq),probe.register_words[20].slice(0,3),probe.name+' native STQ');
 if(probe.program==='carpaint_3pass_dc') {
  assert.deepEqual(nativeFloatWords(actual.stq.slice(0,2)),probe.register_words[22].slice(2),probe.name+' first ST');
  assert.deepEqual(nativeFloatWords(actual.secondStq),probe.register_words[21].slice(0,3),probe.name+' second STQ at Q=1');
 }
 console.log('PASS executed native vehicle words: '+probe.name);
}
// Opposite-sign, tiny addends expose host-double shortcuts even when all
// operands themselves are exactly representable float32 values.
assert.equal(nativeVUAdd(1,-(2**-100)),1-2**-24);
assert.equal(nativeVUAdd(-1,2**-100),-1+2**-24);
assert.equal(nativeVUAdd(1,2**-100),1);
assert.equal(nativeVUAdd(2**-126,-(2**-127)),2**-126);
assert.equal(nativeVUMultiply(2**-126,.5),0);
assert.equal(nativeVUDivide(1,3),.3333333134651184);
assert.throws(()=>nativeVUDivide(1,0),/division by zero/);
assert.throws(()=>nativeVUMultiply(Infinity,1),/Nonfinite/);
assert.throws(()=>nativeVehicleVertex({program:'guessed'}),/Unsupported/);
console.log('PASS native round-toward-zero, DAZ/FTZ and explicit kernel boundaries');

const reference=JSON.parse(readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-math-reference.json',import.meta.url)));
for(const [program,record] of Object.entries(reference.programs)) {
 for(let i=0;i<reference.contexts.length;i++) {
  const actual=nativeVehicleVertex({...reference.contexts[i],program}),expected=record.outputs[i];
  assert.deepEqual(actual.rgba,expected.rgba,program+' context '+i+' RGBA');
  if(expected.stq_words)assert.deepEqual(nativeFloatWords(actual.stq),expected.stq_words,program+' context '+i+' STQ');
  if(expected.st_words)assert.deepEqual(nativeFloatWords(actual.stq.slice(0,2)),expected.st_words,program+' context '+i+' ST');
  if(expected.second_stq_words)assert.deepEqual(nativeFloatWords(actual.secondStq),expected.second_stq_words,program+' context '+i+' second STQ');
 }
 console.log('PASS '+reference.contexts.length+' independently executed contexts: '+program);
}
assert.equal(Object.is(nativeVUMultiply(-0,1),-0),true);
assert.equal(Object.is(nativeVUAdd(-0,-0),-0),true);
assert.equal(Object.is(nativeVUDivide(0,-1),-0),true);
