import assert from 'node:assert/strict';
import {createNativeEEState,runNativeEE} from '../dealership/mc3-ee.mjs';
const ram=new Uint8Array(0x2000000),spad=new Uint8Array(16384);
const regions=[{start:0x1000,size:0x1000,read:true,write:true},{start:0x1fe0000,size:0x10000,read:true,write:true}];
function execute(words,{gpr=[],fpr=[],allocations=regions,maxSteps=1000}={}){
 const code=new Map(words.map((w,i)=>[0x1000+i*4,w]));
 const state=createNativeEEState({ram,spad,code,entry:0x1000,gpr,fpr,regions:allocations});
 runNativeEE(state,{maxSteps});return state;
}
let checks=0;const check=(name,fn)=>{fn();console.log('PASS',name);checks++;};
check('taken branch executes delay slot exactly once',()=>{
 const s=execute([0x10000002,0x24020005,0x24020006,0x03e00008,0]);assert.equal(s.gpr[2],5n);
});
check('false likely branch skips delay slot',()=>{
 const s=execute([0x54000002,0x24020005,0x24030006,0x03e00008,0]);assert.equal(s.gpr[2],0n);assert.equal(s.gpr[3],6n);
});
check('32bit result sign-extends without altering upper128 half',()=>{
 const s=execute([0x2402ffff,0x00021842,0x03e00008,0]);assert.equal(s.gpr[2],0xffffffffffffffffn);assert.equal(s.gpr[3],0x7fffffffn);
});
check('128bit loads/stores retain all lanes',()=>{
 const original=Uint8Array.from({length:16},(_,i)=>i*13+1);ram.set(original,0x1800);
 const s=execute([0x78220000,0x7c220010,0x03e00008,0],{gpr:[[1,0x1800n]]});
 assert.deepEqual(s.ram.slice(0x1810,0x1820),original);ram.fill(0,0x1800,0x1810);
});
check('unallocated memory fails closed',()=>assert.throws(()=>execute([0x8c020000]),/outside allocated/));
check('read-only memory rejects stores',()=>assert.throws(()=>execute([0xac200000],{gpr:[[1,0x1000n]],allocations:[{start:0x1000,size:16,read:true,write:false}]}),/write regions/));
check('missing source instruction fails closed',()=>assert.throws(()=>execute([0]),/source closure/));
check('unknown opcode fails closed',()=>assert.throws(()=>execute([0x74000000]),/Unsupported EE opcode/));
check('loop budget fails closed',()=>assert.throws(()=>execute([0x1000ffff,0],{maxSteps:8}),/budget/));
check('branch in delay slot fails closed',()=>assert.throws(()=>execute([0x10000000,0x10000000]),/delay slot/));
check('untaken branch in a delay slot also fails closed',()=>assert.throws(()=>execute([0x10000000,0x14000000]),/delay slot/));
check('COP1 scalar add follows selected RTZ output',()=>{
 const s=execute([0x46010080,0x03e00008,0],{fpr:[[0,0x3f800000],[1,0x33800000]]});assert.equal(s.fpr[2],0x3f800000);
});
check('COP1 reciprocal sqrt has no intermediate float32 sqrt',()=>{
 const s=execute([0x46010096,0x03e00008,0],{fpr:[[0,0x3f800000],[1,0x40000000]]});assert.equal(s.fpr[2],0x3f3504f3);
});
check('COP1 CVT.W truncates selected finite profile',()=>{
 const s=execute([0x460000a4,0x03e00008,0],{fpr:[[0,0x3fc00000]]});assert.equal(s.fpr[2],1);
});
check('zero register remains immutable',()=>{const s=execute([0x2400ffff,0x03e00008,0]);assert.equal(s.gpr[0],0n);});
console.log(`${checks} bounded EE controls passed.`);

// These complete FPR goldens were freshly executed by the pinned official EE
// interpreter; expected arithmetic is not computed by this implementation.
const fs=await import('node:fs');
const por=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-por.json',import.meta.url)));
for(const control of por.cases){
 const data=new Uint8Array(Buffer.from(control.input_hex,'hex'));ram.set(data,0x1800);
 const rd=control.instruction>>>11&31;
 const s=execute([0x79010000,0x79020010,control.instruction,(0x7d000020|(rd<<16))>>>0,0x03e00008,0],{gpr:[[8,0x1800n]]});
 const view=new DataView(s.ram.buffer,s.ram.byteOffset+0x1820,16);
 assert.deepEqual(Array.from({length:4},(_,i)=>view.getUint32(i*4,true)),control.expected_words,control.name+' original128bit POR');
 ram.fill(0,0x1800,0x1830);
 console.log('PASS original EE128bit POR',control.name);
}
assert.equal(por.cases.length,4);
assert.throws(()=>execute([0x70000029,0x03e00008,0]),/Unsupported EE MMI/);
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-paint-native.json',import.meta.url)));
for(const control of proof.arithmetic_controls.cases){
 const words=[proof.arithmetic_controls.wrapper_accumulator_seed,control.instruction,proof.arithmetic_controls.wrapper_accumulator_copy,...Array.from({length:32},(_,i)=>(0xe5000000|(i<<16)|(i*4))>>>0),0x03e00008,0];
 const s=execute(words,{fpr:proof.arithmetic_controls.input_fpr,gpr:[[8,0x1800n]]});
 assert.deepEqual(Array.from(s.fpr),control.expected_fpr,control.name+' original EE output differs');
 console.log('PASS original EE complete FPR golden',control.name);
}

// Original EE macro controls retain all 128 VF words, including masked and
// untouched lanes. Source vectors are loaded before destination-alias writes.
const cop2=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-cop2.json',import.meta.url)));
for(const control of cop2.cases){
 const input=new DataView(ram.buffer,0x1800,512);const values=[...cop2.inputs];if(control.profile==='finite-boundary'){values.splice(32,4,0x7f7fffff,0xff7fffff,0x00800000,0x80800000);values.splice(20,4,...Array(4).fill((control.instruction&63)<=3?0x00800000:0x3f800000));}for(let i=0;i<128;i++)input.setUint32(i*4,values[i],true);
 const words=[...Array.from({length:32},(_,r)=>(0xd9000000|(r<<16)|(r*16))>>>0),cop2.seed_accumulator,control.instruction,
  ...Array.from({length:32},(_,r)=>(0xf9200000|(r<<16)|(r*16))>>>0),0x03e00008,0];
 const s=execute(words,{gpr:[[8,0x1800n],[9,0x1a00n]]}),view=new DataView(s.ram.buffer,0x1a00,512);
 assert.deepEqual(Array.from({length:128},(_,i)=>view.getUint32(i*4,true)),control.expected_vf,control.name+' all original VF lanes');
 ram.fill(0,0x1800,0x1c00);
}
console.log('PASS original EE COP2 full/broadcast MUL and broadcast ADD, masks, register aliases, VF0 and finite/subnormal lanes:',cop2.cases.length);
assert.throws(()=>execute([0x4be84129,0x03e00008,0]),/Unsupported EE COP2 macro/);
for(const word of [0x7f800000,0x7fc00000,0xff800000]){
 const code=new Map([[0x1000,0x4be54100],[0x1004,0x03e00008],[0x1008,0]]);
 const s=createNativeEEState({ram,spad,code,entry:0x1000,regions});s.vf[8*4]=word;s.vf[5*4]=0x3f800000;
 assert.throws(()=>runNativeEE(s),/Nonfinite native VU input/);
}
for(const instruction of [0x4be54100,0x4be54118,0x4be54128]){
 const code=new Map([[0x1000,instruction],[0x1004,0x03e00008],[0x1008,0]]);
 const s=createNativeEEState({ram,spad,code,entry:0x1000,regions});s.vf[8*4]=0x7f7fffff;s.vf[5*4]=0x7f7fffff;
 assert.throws(()=>runNativeEE(s),/outside bounded finite profile/);
}
console.log('PASS nonfinite, finite-overflow and unobserved full SUB boundaries remain explicit failures');

for(const control of cop2.addi.cases){
 const input=new DataView(ram.buffer,0x1800,32);for(let i=0;i<8;i++)input.setUint32(i*4,control.input_words[i],true);
 const rs=control.instruction>>>21&31,rt=control.instruction>>>16&31;
 const words=[(0x79400000|(rs<<16))>>>0,...(rs===rt?[]:[(0x79400010|(rt<<16))>>>0]),control.instruction,(0x7d600000|(rt<<16))>>>0,0x03e00008,0];
 const s=execute(words,{gpr:[[10,0x1800n],[11,0x1840n]]}),view=new DataView(s.ram.buffer,0x1840,16);
 assert.deepEqual(Array.from({length:4},(_,i)=>view.getUint32(i*4,true)),control.expected_words,control.name+' original ADDI full128 destination');
 ram.fill(0,0x1800,0x1850);
}
assert.throws(()=>execute([0x20e70001],{gpr:[[7,0x7fffffffn]]}),/ADDI signed overflow/);
assert.throws(()=>execute([0x20e7ffff],{gpr:[[7,0x80000000n]]}),/ADDI signed overflow/);
console.log('PASS source ADDI sign-extension, original signed32 finite boundaries and upper128 preservation:',cop2.addi.cases.length);

const mr32=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-mr32.json',import.meta.url)));
for(const control of mr32.cases){
 const input=new DataView(ram.buffer,0x1800,512);for(let i=0;i<128;i++)input.setUint32(i*4,mr32.inputs[i],true);
 const words=[...Array.from({length:32},(_,r)=>(0xd9000000|(r<<16)|(r*16))>>>0),control.instruction,
  ...Array.from({length:32},(_,r)=>(0xf9200000|(r<<16)|(r*16))>>>0),0x03e00008,0];
 const s=execute(words,{gpr:[[8,0x1800n],[9,0x1a00n]]}),view=new DataView(s.ram.buffer,0x1a00,512);
 assert.deepEqual(Array.from({length:128},(_,i)=>view.getUint32(i*4,true)),control.expected_vf,control.name+' original raw MR32 VF lanes');
 ram.fill(0,0x1800,0x1c00);
}
assert.throws(()=>execute([0x4be6333c]),/Unsupported EE COP2 accumulator macro/);
console.log('PASS original EE MR32 all16 masks, alias/VF0 and raw exceptional bit patterns:',mr32.cases.length);

const fullAdd=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-full-add.json',import.meta.url)));
for(const control of fullAdd.cases){
 const values=[...fullAdd.inputs];if(control.profile==='finite-boundary'){values.splice(32,4,0x7f7fffff,0xff7fffff,0x00800000,0x80800000);values.splice(20,4,...Array(4).fill(0x00800000));}
 const input=new DataView(ram.buffer,0x1800,512);for(let i=0;i<128;i++)input.setUint32(i*4,values[i],true);
 const words=[...Array.from({length:32},(_,r)=>(0xd9000000|(r<<16)|(r*16))>>>0),fullAdd.seed_accumulator,control.instruction,
  ...Array.from({length:32},(_,r)=>(0xf9200000|(r<<16)|(r*16))>>>0),0x03e00008,0];
 const s=execute(words,{gpr:[[8,0x1800n],[9,0x1a00n]]}),view=new DataView(s.ram.buffer,0x1a00,512);
 assert.deepEqual(Array.from({length:128},(_,i)=>view.getUint32(i*4,true)),control.expected_vf,control.name+' original full ADD VF lanes');
 ram.fill(0,0x1800,0x1c00);
}
for(const word of [0x7f800000,0x7fc00000]){
 const s=execute([0x03e00008,0]);s.pc=0x1000;s.steps=0;s.code.set(0x1000,0x4be54128);s.vf[8*4]=word;
 assert.throws(()=>runNativeEE(s),/Nonfinite native VU input/);
}
console.log('PASS original EE full ADD all16 masks, aliases, VF0 and finite/subnormal boundaries:',fullAdd.cases.length);

for(const control of fullAdd.mflo.cases){
 const input=new DataView(ram.buffer,0x1800,48);for(let i=0;i<12;i++)input.setUint32(i*4,control.input_words[i],true);
 const rd=control.instruction>>>11&31;
 const words=[0x79420000,0x79460010,...([2,6].includes(rd)?[]:[(0x79400020|(rd<<16))>>>0]),0x00460018,control.instruction,(0x7d600000|(rd<<16))>>>0,0x03e00008,0];
 const s=execute(words,{gpr:[[10,0x1800n],[11,0x1840n]]}),view=new DataView(s.ram.buffer,0x1840,16);
 assert.deepEqual(Array.from({length:4},(_,i)=>view.getUint32(i*4,true)),control.expected_words,control.name+' original MFLO destination');
 ram.fill(0,0x1800,0x1850);
}
console.log('PASS original MULT to MFLO signed/edge products, aliases/register0 and upper128 preservation:',fullAdd.mflo.cases.length);

const mmi=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-mmi.json',import.meta.url)));
for(const control of mmi.cases){
 const input=new DataView(ram.buffer,0x1800,64),loads=[];
 for(const [index,[reg,raw]] of control.registers.entries()){for(let i=0;i<4;i++)input.setUint32(index*16+i*4,raw[i],true);loads.push((0x79400000|(reg<<16)|(index*16))>>>0);}
 const rd=control.instruction>>>11&31;
 const s=execute([...loads,control.instruction,(0x7d600000|(rd<<16))>>>0,0x03e00008,0],{gpr:[[10,0x1800n],[11,0x1840n]]}),view=new DataView(s.ram.buffer,0x1840,16);
 assert.deepEqual(Array.from({length:4},(_,i)=>view.getUint32(i*4,true)),control.expected_words,control.name+' original PCPYLD raw128');
 ram.fill(0,0x1800,0x1850);
}
assert.throws(()=>execute([0x70e313c9]),/Unsupported EE MMI/);
console.log('PASS original PCPYLD source words, raw128 halves, aliases and register0:',mmi.cases.length);

const mac=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-mac.json',import.meta.url)));
for(const control of mac.cases){
 const raw=new DataView(ram.buffer,0x1800,128),loads=[];
 for(const[index,[reg,words]]of control.registers.entries()){for(let i=0;i<4;i++)raw.setUint32(index*16+i*4,words[i],true);loads.push((0x79400000|(reg<<16)|(index*16))>>>0);}
 const rd=control.kind==='mtlo'?2:control.instruction>>>11&31;
 const words=[...loads,0x01a00013,control.instruction,(0x7d600000|(rd<<16))>>>0,0x03e00008,0];
 const code=new Map(words.map((w,i)=>[0x1000+i*4,w]));
 const state=createNativeEEState({ram,spad,code,entry:0x1000,gpr:[[10,0x1800n],[11,0x1880n]],regions});
 state.hi=BigInt(control.hi_words[0])|(BigInt(control.hi_words[1])<<32n);
 runNativeEE(state);
 const view=new DataView(state.ram.buffer,0x1880,16);
 assert.deepEqual(Array.from({length:4},(_,i)=>view.getUint32(i*4,true)),control.expected_destination,control.name+' original MAC destination');
 const split=value=>[Number(value&0xffffffffn),Number(value>>32n&0xffffffffn)];
 assert.deepEqual(split(state.lo),control.expected_lo,control.name+' original LO low64');
 assert.deepEqual(split(state.hi),control.expected_hi,control.name+' original HI low64');
 ram.fill(0,0x1800,0x1890);
}
assert.throws(()=>execute([0x01c00011]),/Unsupported EE SPECIAL/);
assert.throws(()=>execute([0x00007811]),/Unsupported EE SPECIAL/);
assert.throws(()=>execute([0x72622001]),/Unsupported EE MMI/);
console.log('PASS original MTLO/MADD carry/sign/wrap, low32 LO/HI composition, aliases/register0 and upper128 preservation:',mac.cases.length);

// Optional full-source integration is explicit; ordinary offline controls do
// not silently report this private original-function comparison as executed.
const packArgument=process.argv.indexOf('--paint-source-pack');
if(packArgument>=0){
 const pack=JSON.parse(fs.readFileSync(process.argv[packArgument+1])),ram=new Uint8Array(0x2000000),spad=new Uint8Array(16384);
 for(const chunk of pack.chunks){const data=Buffer.from(chunk.data_hex,'hex');if(chunk.address>=0x70000000)spad.set(data,chunk.address-0x70000000);else ram.set(data,chunk.address);}
 const s=createNativeEEState({...pack,ram,spad,code:new Map(pack.code),gpr:pack.gpr.map(([r,v])=>[r,BigInt(v)])});
 for(const[r,,high]of pack.gpr)s.upper[r]=BigInt(high);
 runNativeEE(s);const {createHash}=await import('node:crypto');
 const selected=pack.control==='positive'?proof.positive_control:proof;
 assert.equal(createHash('sha256').update(s.ram).digest('hex'),selected.reference_final_ram_sha256,'whole original paint RAM differs');
 assert.equal(s.steps,selected.reference_browser_instructions);
 console.log('PASS original whole paint function final 32MiB RAM and DMA byte-for-byte',s.steps);
}
