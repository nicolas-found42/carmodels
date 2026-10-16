// Bounded EE helper execution. The caller supplies source-pinned instruction
// words and an explicit RAM/SPAD context; unsupported instructions fail closed.
import {nativeVUAdd as add,nativeVUMultiply as mul,nativeVUDivide as div} from './mc3-vehicle-math.mjs';
const bits=new DataView(new ArrayBuffer(4)),u64=x=>BigInt.asUintN(64,x),i64=x=>BigInt.asIntN(64,x);
const f=w=>{bits.setUint32(0,w,true);return bits.getFloat32(0,true);};
const arithmetic=w=>f((w&0x7f800000)===0?w&0x80000000:w);
const word=x=>{bits.setFloat32(0,x,true);return bits.getUint32(0,true);};
const need=(ok,label)=>{if(!ok)throw Error(label);};
const signed32=x=>BigInt(x|0),low=x=>Number(x&0xffffffffn)>>>0;
export function createNativeEEState({ram,spad,code,entry,gpr,fpr,regions}) {
 need(ram instanceof Uint8Array&&ram.length===0x2000000&&spad instanceof Uint8Array&&spad.length===0x4000,'Invalid explicit EE memory.');
 need(code instanceof Map&&code.size>0&&Number.isInteger(entry),'Invalid EE instruction closure.');
 need(Array.isArray(regions)&&regions.length>0&&regions.every(r=>Number.isInteger(r.start)&&r.start>=0&&Number.isInteger(r.size)&&r.size>0&&r.start+r.size<=0x100000000&&typeof r.read==='boolean'&&typeof r.write==='boolean'),'Invalid explicit EE allocations.');
 const s={regions:regions.map(r=>({...r})),ram:ram.slice(),spad:spad.slice(),code:new Map(code),pc:entry,gpr:Array(32).fill(0n),upper:Array(32).fill(0n),fpr:new Uint32Array(32),vf:new Uint32Array(128),vacc:new Uint32Array(4),acc:0,condition:false,hi:0n,lo:0n,hi1:0n,lo1:0n,steps:0,cp0:new Uint32Array(32)};
 s.cp0[12]=0x70400004;s.gpr[29]=0x1ff0000n;s.gpr[31]=0x10000n;s.vf[3]=0x3f800000;
 for(const [r,v]of gpr??[]){need(Number.isInteger(r)&&r>0&&r<32&&typeof v==='bigint','Invalid explicit EE GPR.');s.gpr[r]=u64(v);}
 for(const [r,v]of fpr??[]){need(Number.isInteger(r)&&r>=0&&r<32&&Number.isInteger(v)&&v>=0&&v<=0xffffffff,'Invalid explicit EE FPR.');s.fpr[r]=v;}
 return s;
}
function view(s,address,size,write=false) {
 address>>>=0;need(s.regions.some(r=>address>=r.start&&address+size<=r.start+r.size&&r[write?'write':'read']),'EE access outside allocated '+(write?'write':'read')+' regions: '+address.toString(16));let memory,offset;
 if(address>=0x70000000&&address+size<=0x70004000){memory=s.spad;offset=address-0x70000000;}
 else {need(address+size<=s.ram.length,'EE address outside explicit memory: '+address.toString(16));memory=s.ram;offset=address;}
 return new DataView(memory.buffer,memory.byteOffset+offset,size);
}
function sqrt(x) {
 need(Number.isFinite(x)&&x>=0,'Exceptional EE square root.');if(!x)return x;
 let value=Math.fround(Math.sqrt(x));if(value*value>x)value=f(word(value)-1);return value;
}
function rsqrt(x,y) {
 need(Number.isFinite(x)&&Number.isFinite(y)&&y>0,'Exceptional EE reciprocal square root.');
 let candidate=Math.fround(Math.abs(x)/Math.sqrt(y));need(Number.isFinite(candidate),'EE reciprocal square root overflow.');
 const parts=v=>{const w=word(v),e=(w>>>23)&255;return [BigInt((w&0x7fffff)|(e?0x800000:0)),e?e-150:-149];};
 const [a,ae]=parts(Math.abs(x)),[b,be]=parts(y),[c,ce]=parts(candidate);
 let left=c*c*b,right=a*a;const delta=2*ce+be-2*ae;
 if(delta>=0)left<<=BigInt(delta);else right<<=BigInt(-delta);
 if(left>right)candidate=f(word(candidate)-1);
 return x<0||Object.is(x,-0)?-candidate:candidate;
}
export function runNativeEE(s,{maxSteps=100000,stopPC=0x10000,onInstruction}={}) {
 need(Number.isInteger(maxSteps)&&maxSteps>0,'Invalid EE execution budget.');
 let pending=null;
 const set=(r,v)=>{if(r)s.gpr[r]=u64(v);};
 while(s.pc!==stopPC){
  need(++s.steps<=maxSteps,'EE instruction budget exceeded.');
  const pc=s.pc,w=s.code.get(pc);need(Number.isInteger(w),'EE instruction outside source closure: '+pc.toString(16));
  onInstruction?.(pc,w,s);const op=w>>>26,rs=w>>>21&31,rt=w>>>16&31,rd=w>>>11&31,sa=w>>>6&31,fn=w&63,imm=w&65535,se=imm<<16>>16;
  const a=s.gpr[rs],b=s.gpr[rt],address=(low(a)+se)>>>0,old=pending;pending=null;let skip=false,controlFlow=false;
  const branch=(yes,likely=false)=>{controlFlow=true;if(yes)pending=(pc+4+(se<<2))>>>0;else if(likely)skip=true;else pending=(pc+8)>>>0;};
  const sx=v=>signed32(v),load=(n,signed=false)=>{const d=view(s,address,n);return n===8?d.getBigUint64(0,true):signed?sx(n===4?d.getInt32(0,true):n===2?d.getInt16(0,true):d.getInt8(0)):BigInt(n===4?d.getUint32(0,true):n===2?d.getUint16(0,true):d.getUint8(0));};
  if(op===0){
   if(fn===0)set(rd,sx(low(b)<<sa));else if(fn===2)set(rd,sx(low(b)>>>sa));else if(fn===3)set(rd,sx((low(b)|0)>>sa));
   else if(fn===4)set(rd,sx(low(b)<<(low(a)&31)));
   else if(fn===8||fn===9){controlFlow=true;pending=low(a);if(fn===9)set(rd,BigInt(pc+8));}
   else if(fn===10||fn===11){if((b===0n)===(fn===10))set(rd,a);}
   else if(fn===15){} // SYNC has no asynchronous devices in this bounded context.
   else if(fn===16)set(rd,s.hi);
   else if(fn===18)set(rd,s.lo);
   else if(fn===19)s.lo=a;
   else if(fn===26||fn===27){const x=fn===26?BigInt(low(a)|0):BigInt(low(a)),y=fn===26?BigInt(low(b)|0):BigInt(low(b));
    const quotient=y===0n?(fn===26&&x<0n?1n:-1n):x/y,remainder=y===0n?BigInt(low(a)|0):x%y;
    s.lo=u64(sx(Number(quotient&0xffffffffn)));s.hi=u64(sx(Number(remainder&0xffffffffn)));}
   else if(fn===24){const p=BigInt(low(a)|0)*BigInt(low(b)|0);s.lo=u64(sx(Number(p&0xffffffffn)));s.hi=u64(sx(Number(p>>32n&0xffffffffn)));set(rd,s.lo);}
   else if(fn===33)set(rd,sx((low(a)+low(b))>>>0));else if(fn===35)set(rd,sx((low(a)-low(b))>>>0));
   else if(fn===36)set(rd,a&b);else if(fn===37)set(rd,a|b);else if(fn===38)set(rd,a^b);else if(fn===39)set(rd,~(a|b));
   else if(fn===42)set(rd,i64(a)<i64(b)?1n:0n);else if(fn===43)set(rd,a<b?1n:0n);else if(fn===45)set(rd,a+b);else if(fn===47)set(rd,a-b);
   else if([56,58,59,60,62,63].includes(fn)){const shift=BigInt(sa+(fn>=60?32:0));set(rd,fn===56||fn===60?b<<shift:fn===59||fn===63?i64(b)>>shift:b>>shift);}
   else throw Error('Unsupported EE SPECIAL '+fn.toString(16));
  }else if(op===1){need([0,1,2,3,16,17].includes(rt),'Unsupported EE REGIMM.');if(rt>=16)set(31,BigInt(pc+8));branch((i64(a)>=0n)===(!!(rt&1)),rt===2||rt===3);}
  else if(op===2||op===3){controlFlow=true;pending=((pc+4)&0xf0000000)|((w&0x3ffffff)<<2);if(op===3)set(31,BigInt(pc+8));}
  else if([4,5,6,7,20,21,22,23].includes(op)){const k=op&15;branch(k===4?a===b:k===5?a!==b:k===6?i64(a)<=0n:i64(a)>0n,op>=20);}
  else if(op===8){const sum=(low(a)|0)+se;need(sum>=-2147483648&&sum<=2147483647,'Unsupported EE ADDI signed overflow.');set(rt,sx(sum));}
  else if(op===25)set(rt,a+BigInt(se));
  else if(op===9)set(rt,sx((low(a)+se)>>>0));else if(op===10)set(rt,i64(a)<BigInt(se)?1n:0n);else if(op===11)set(rt,a<u64(BigInt(se))?1n:0n);
  else if(op===12)set(rt,a&BigInt(imm));else if(op===13)set(rt,a|BigInt(imm));else if(op===14)set(rt,a^BigInt(imm));else if(op===15)set(rt,sx(imm<<16));
  else if(op===16){need(rs===0&&[12,28].includes(rd),'Unsupported EE COP0 context.');set(rt,signed32(s.cp0[rd]));}
  else if(op===17){
   const ft=rt,fs=rd,fd=sa,x=arithmetic(s.fpr[fs]),y=arithmetic(s.fpr[ft]);
   if(rs===0)set(rt,sx(s.fpr[fs]));else if(rs===4)s.fpr[fs]=low(b);
   else if(rs===8)branch(s.condition===!!(rt&1),!!(rt&2));
   else if(rs===20){need(fn===32,'Unsupported EE integer float conversion.');let value=Math.fround(s.fpr[fs]|0);if(Math.abs(value)>Math.abs(s.fpr[fs]|0))value=f(word(value)-1);s.fpr[fd]=word(value);}
   else {need(rs===16,'Unsupported EE COP1 format.');let z;
    if(fn===0)z=add(x,y);else if(fn===1)z=add(x,-y);else if(fn===2)z=mul(x,y);else if(fn===3)z=(s.fpr[ft]&0x7f800000)===0?f(((s.fpr[fs]^s.fpr[ft])&0x80000000)|0x7f7fffff):div(x,y);else if(fn===4)z=sqrt(y);
    else if(fn===5){s.fpr[fd]=s.fpr[fs]&0x7fffffff;continueAt();continue;}
    else if(fn===6){s.fpr[fd]=s.fpr[fs];continueAt();continue;}
    else if(fn===7){s.fpr[fd]=s.fpr[fs]^0x80000000;continueAt();continue;}
    else if(fn===22)z=rsqrt(x,y);
    else if(fn===24)s.acc=add(x,y);else if(fn===25)s.acc=add(x,-y);else if(fn===26)s.acc=mul(x,y);
    else if(fn===28)z=add(s.acc,mul(x,y));else if(fn===29)z=add(s.acc,-mul(x,y));else if(fn===30)s.acc=add(s.acc,mul(x,y));else if(fn===31)s.acc=add(s.acc,-mul(x,y));
    else if(fn===40||fn===41){need([s.fpr[fs],s.fpr[ft]].every(w=>(w&0x7f800000)!==0&&(w&0x7f800000)!==0x7f800000||(w&0x7fffffff)===0),'Unsupported EE MIN/MAX exceptional input.');z=fn===40?Math.max(x,y):Math.min(x,y);}
    else if(fn===36){need(Number.isFinite(x),'Exceptional EE CVT.W.');s.fpr[fd]=Math.max(-2147483648,Math.min(2147483647,Math.trunc(x)))>>>0;}
    else if([48,50,52,54].includes(fn))s.condition=fn===50?x===y:fn===52?x<y:fn===54?x<=y:false;
    else throw Error('Unsupported EE COP1 operation '+fn.toString(16));
    if(z!==undefined)s.fpr[fd]=word(z);
   }
  }else if(op===18){
   need(rs>=16,'Unsupported EE COP2 transfer.');const mask=w>>>21&15,vs=rd,vt=rt,vd=sa,component=fn&3;
   if(fn===61&&vd===12){
    const source=Array.from(s.vf.subarray(vs*4,vs*4+4));
    for(let lane=0;lane<4;lane++)if(vt&&(mask&(8>>>lane)))s.vf[vt*4+lane]=source[(lane+1)&3];
   }else {
   const broadcastAdd=fn<=3,broadcastMul=fn>=24&&fn<=27,fullMul=fn===42,fullAdd=fn===40;
   need(fn>=60||fn>=8&&fn<=11||broadcastAdd||broadcastMul||fullMul||fullAdd,'Unsupported EE COP2 macro.');
   // All source lanes are read before any destination write. A broadcast's
   // destination may alias vt, including its broadcast component.
   const left=Array.from(s.vf.subarray(vs*4,vs*4+4)),right=Array.from(s.vf.subarray(vt*4,vt*4+4));
   for(let lane=0;lane<4;lane++)if(mask&(8>>>lane)){
    const x=f(left[lane]),y=f(right[fullMul||fullAdd?lane:component]);
    if(broadcastAdd||fullAdd){const sum=add(x,y);if(vd)s.vf[vd*4+lane]=word(sum);}
    else {
     const product=mul(x,y);
     if(fn>=60){need(vd===2||vd===6,'Unsupported EE COP2 accumulator macro.');s.vacc[lane]=word(vd===6?product:add(f(s.vacc[lane]),product));}
     else if(vd)s.vf[vd*4+lane]=word(broadcastMul||fullMul?product:add(f(s.vacc[lane]),product));
    }
   }
   }
  }else if(op===28){
   if(fn===24&&sa===0){const p=BigInt(low(a)|0)*BigInt(low(b)|0);s.lo1=u64(sx(Number(p&0xffffffffn)));s.hi1=u64(sx(Number(p>>32n&0xffffffffn)));set(rd,s.lo1);}
   else if(fn===0&&sa===0){const total=u64((s.lo&0xffffffffn)|((s.hi&0xffffffffn)<<32n))+BigInt(low(a)|0)*BigInt(low(b)|0);s.lo=u64(sx(Number(total&0xffffffffn)));s.hi=u64(sx(Number(total>>32n&0xffffffffn)));set(rd,s.lo);}
   else {const copyLow=fn===9&&sa===14;need(copyLow||fn===0x29&&sa===18,'Unsupported EE MMI operation.');
    if(rd){if(copyLow){s.upper[rd]=a;s.gpr[rd]=b;}else{s.gpr[rd]=a|b;s.upper[rd]=s.upper[rs]|s.upper[rt];}}}
  }else if([32,33,35,36,37,39,55].includes(op))set(rt,load(op===55?8:[32,36].includes(op)?1:[33,37].includes(op)?2:4,[32,33,35].includes(op)));
  else if([40,41,43,63].includes(op)){const n=op===63?8:op===43?4:op===41?2:1,d=view(s,address,n,true);if(n===8)d.setBigUint64(0,b,true);else if(n===4)d.setUint32(0,low(b),true);else if(n===2)d.setUint16(0,low(b),true);else d.setUint8(0,low(b));}
  else if([34,38,42,46].includes(op)){
   const aligned=address&~3,k=address&3,d=view(s,aligned,4,op===42||op===46),v=BigInt(d.getUint32(0,true)),shift=BigInt((op===34||op===42?3-k:k)*8),mask=0xffffffffn,bv=b&mask;
   if(op===34)set(rt,sx(Number(((bv&((1n<<shift)-1n))|(v<<shift))&mask)));
   else if(op===38)set(rt,sx(Number((bv&(mask^((1n<<(32n-shift))-1n)))|(v>>shift))));
   else if(op===42)d.setUint32(0,Number((v&(mask^((1n<<(32n-shift))-1n)))|(bv>>shift)),true);
   else d.setUint32(0,Number(((v&((1n<<shift)-1n))|(bv<<shift))&mask),true);
  }else if(op===26||op===27||op===44||op===45){const aligned=address&~7,k=address&7,d=view(s,aligned,8,op===44||op===45),v=d.getBigUint64(0,true),shift=BigInt((op===26||op===44?7-k:k)*8),mask=(1n<<64n)-1n;
   if(op===26)set(rt,(b&((1n<<shift)-1n))|(v<<shift));else if(op===27)set(rt,(b&(mask^((1n<<(64n-shift))-1n)))|(v>>shift));
   else if(op===44)d.setBigUint64(0,(v&(mask^((1n<<(64n-shift))-1n)))|(b>>shift),true);
   else d.setBigUint64(0,u64((v&((1n<<shift)-1n))|(b<<shift)),true);
  }else if(op===30||op===31){const d=view(s,address&~15,16,op===31);if(op===30){if(rt){s.gpr[rt]=d.getBigUint64(0,true);s.upper[rt]=d.getBigUint64(8,true);}}else{d.setBigUint64(0,b,true);d.setBigUint64(8,s.upper[rt],true);}}
  else if(op===49)s.fpr[rt]=view(s,address,4).getUint32(0,true);else if(op===57)view(s,address,4,true).setUint32(0,s.fpr[rt],true);
  else if(op===54||op===62){const d=view(s,address&~15,16,op===62);for(let i=0;i<4;i++)if(op===54){if(rt)s.vf[rt*4+i]=d.getUint32(i*4,true);}else d.setUint32(i*4,s.vf[rt*4+i],true);}
  else if(op===47){} // CACHE has no asynchronous cache state in isolated jobs.
  else throw Error('Unsupported EE opcode '+op.toString(16)+' at '+pc.toString(16));
  continueAt();
  function continueAt(){need(!(old!==null&&controlFlow),'EE branch in delay slot.');s.pc=old!==null?old:(pc+(skip?8:4))>>>0;s.gpr[0]=0n;}
 }
 return s;
}
