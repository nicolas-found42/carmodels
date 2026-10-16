import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createNativeEEState,runNativeEE} from '../dealership/mc3-ee.mjs';
const proof=JSON.parse(fs.readFileSync(new URL('../research/evidence/midnight-club-3-remix/previews/ee-division.json',import.meta.url)));
const job=spawnSync('python3',['tools/mc3_ee_division.py','--emit-job'],{maxBuffer:1048576});
assert.equal(job.status,0,job.stderr.toString());
assert.equal(createHash('sha256').update(job.stdout).digest('hex'),proof.execution.job_sha256,'independently rebuilt exact original native inputs');
const split=value=>[Number(value&0xffffffffn),Number(value>>32n&0xffffffffn)];
for(const row of proof.cases){
 const w=row.instruction,rs=w>>>21&31,rt=w>>>16&31,rd=w>>>(row.kind==='daddiu'?16:11)&31;
 const values=new Map([...new Set([rs,rt,rd])].filter(r=>r!==0).map(r=>[r,[0xabcdef00+r,0x87654321,0x12340000+r,0xfedc0000+r]]));
 const inputs=row.kind==='daddiu'?[[rs,row.a]]:[[rs,row.a],[rt,row.b]];
 for(const[r,raw]of inputs)if(r&&row.kind!=='mfhi')values.get(r).splice(0,2,parseInt(raw.slice(8),16),parseInt(raw.slice(0,8),16));
 const state=createNativeEEState({ram:new Uint8Array(0x2000000),spad:new Uint8Array(16384),
  code:new Map([[0x1000,w],[0x1004,0x03e00008],[0x1008,0]]),entry:0x1000,
  regions:[{start:0x1000,size:12,read:true,write:false}]});
 for(const[r,raw]of values){state.gpr[r]=BigInt(raw[0])|BigInt(raw[1])<<32n;state.upper[r]=BigInt(raw[2])|BigInt(raw[3])<<32n;}
 [state.lo,state.hi,state.lo1,state.hi1]=proof.accumulator_inputs.map(v=>BigInt('0x'+v));
 runNativeEE(state);
 assert.deepEqual([...split(state.gpr[rd]),...split(state.upper[rd])],row.expected_destination,row.name+' raw128 GPR');
 assert.deepEqual([state.lo,state.hi,state.lo1,state.hi1].flatMap(split),row.expected_accumulators,row.name+' both independent128 accumulator halves');
}
for(const w of [0x01c00011,0x70006010,0x70006012,0x7000001a,0x70000019]){
 const state=createNativeEEState({ram:new Uint8Array(0x2000000),spad:new Uint8Array(16384),
  code:new Map([[0x1000,w]]),entry:0x1000,regions:[{start:0x1000,size:4,read:true,write:false}]});
 assert.throws(()=>runNativeEE(state),/Unsupported EE/);
}
console.log('PASS original DIV/DIVU zero/overflow/sign, MFHI raw64, DADDIU/DSUBU wrap and MULT1 independentupperaccumulators:',proof.cases.length);
console.log('PASS exact native job, raw128 GPR aliases/register0 and unsupported neighboring instruction refusals');
