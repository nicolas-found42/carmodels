import {nativeVUAdd as add,nativeVUMultiply as mul,nativeVUDivide as divide} from './mc3-vehicle-math.mjs';

// Bounded VU1 interpreter for source-program comparison. The renderer must
// supply original microcode, data memory and register state. Unsupported
// instructions and exceptional arithmetic fail rather than use GPU math.
const bits=new DataView(new ArrayBuffer(4));
const word=value=>{bits.setFloat32(0,value,true);return bits.getUint32(0,true);};
const number=value=>{bits.setUint32(0,value,true);return bits.getFloat32(0,true);};
const signed16=value=>(value<<16)>>16;
const signed11=value=>(value<<21)>>21;
const mask=code=>(code>>>21)&15;
const fs=code=>(code>>>11)&31,ft=code=>(code>>>16)&31,fd=code=>(code>>>6)&31;
const lanes=mask=>[0,1,2,3].filter(i=>mask&(8>>>i));
function need(value,message){if(!value)throw Error(message);}
function intFloat(value) {
 const rounded=Math.fround(value),raw=word(rounded);
 return Math.abs(rounded)>Math.abs(value)?number(raw-1):rounded;
}
const fixedUpper=['mulq','maxi','muli','minii','addq','maddq','addi','maddi','subq','msubq','subi','msubi',
 'add','madd','mul','max','sub','msub','opmsub','mini'];
const lowerTop={0:'lq',1:'sq',4:'ilw',5:'isw',8:'iaddiu',9:'isubiu',16:'fceq',17:'fcset',18:'fcand',19:'fcor',
 20:'fseq',21:'fsset',22:'fsand',23:'fsor',26:'fmand',28:'fcget',32:'b',33:'bal',36:'jr',37:'jalr',40:'ibeq',41:'ibne',44:'ibltz',45:'ibgtz',46:'iblez',47:'ibgez'};
const lowerSpecial={0x33c:'move',0x33d:'mr32',0x37c:'lqi',0x37d:'sqi',0x37e:'lqd',0x37f:'sqd',
 0x3bc:'div',0x3bf:'waitq',0x3fc:'mtir',0x3fd:'mfir',0x3fe:'ilwr',0x3ff:'iswr',0x6bc:'xtop',0x6bd:'xitop',0x6fc:'xgkick'};
export function decodeNativeVUPair(lower,upper) {
 const op=upper&63,extension=fd(upper);let u;
 if(op<28)u=['add','sub','madd','msub','max','mini','mul'][op>>>2]+'xyzw'[op&3];
 else if(op<48)u=fixedUpper[op-28];
 else if(op>=60) {
  if([0,1,2,3,6].includes(extension))u=({0:'adda',1:'suba',2:'madda',3:'msuba',6:'mula'})[extension]+'xyzw'[op&3];
  else if(extension===4)u='itof'+[0,4,12,15][op&3];
  else if(extension===5)u='ftoi'+[0,4,12,15][op&3];
  else u=({[0x1fc]:'mulaq',[0x1fd]:'abs',[0x1fe]:'mulai',[0x1ff]:'clip',
   [0x2fe]:'opmula',[0x2ff]:'nop',[0x23c]:'addaq',[0x23e]:'addai',
   [0x27c]:'subaq',[0x27e]:'subai',[0x23d]:'maddaq',[0x23f]:'maddai',
   [0x27d]:'msubaq',[0x27f]:'msubai',[0x2bc]:'adda',[0x2bd]:'madda',[0x2be]:'mula',[0x2bf]:'unsupported',
   [0x2fc]:'suba',[0x2fd]:'msuba'})[upper&0x7ff];
 }
 let l;
 if(upper>>>31)l='loi';
 else if(lower===0x8000033c)l='nop';
 else if(!(lower>>>31))l=lowerTop[lower>>>25];
 else l=lowerSpecial[lower&0x7ff]??({48:'iadd',49:'isub',50:'iaddi',52:'iand',53:'ior'})[lower&63];
 need(u&&u!=='unsupported'&&l,'Unsupported native VU instruction: '+lower.toString(16)+'/'+upper.toString(16));
 return {lower,upper,u,l};
}

function upperShape(pair) {
 const c=pair.upper,m=mask(c),{u}=pair;
 if(u==='nop')return {reads:[],write:0,flags:false};
 if(u==='clip')return {reads:[[fs(c),14],[ft(c),1]],write:0,flags:true,clip:true};
 if(u==='opmula'||u==='opmsub')return {reads:[[fs(c),14],[ft(c),14]],write:u==='opmula'?0:fd(c),mask:14,flags:true};
 if(u==='abs'||/^(ftoi|itof)/.test(u))return {reads:[[fs(c),m]],write:ft(c),flags:true};
 const {broadcast,scalar}=upperOperands(c),special=broadcast>=0||scalar;
 return {reads:[[fs(c),m],...(broadcast>=0?[[ft(c),8>>>broadcast]]:special?[]:[[ft(c),m]])],
  write:/^(adda|suba|madda|msuba|mula|opmula)/.test(u)?0:fd(c),flags:true};
}
function upperOperands(c) {
 const op=c&63,extension=fd(c);
 if(op<28||op>=60&&[0,1,2,3,6].includes(extension))return {broadcast:op&3,scalar:null};
 if(op>=28&&op<40)return {broadcast:-1,scalar:[28,32,33,36,37].includes(op)?'q':'i'};
 if(op>=60&&[7,8,9].includes(extension))return {broadcast:-1,scalar:(op&2)?'i':'q'};
 return {broadcast:-1,scalar:null};
}
function lowerShape(pair) {
 const c=pair.lower,m=mask(c),{l}=pair;let reads=[],write=0,pipe='none',viRead=[],viWrite=0;
 if(['lq','lqi','lqd','move','mr32','mfir'].includes(l)){write=ft(c);pipe='fmac';}
 if(['move','mr32','sq','sqi','sqd'].includes(l)){reads=[[fs(c),l==='mr32'?(m>>>1)|((m<<3)&8):m]];pipe='fmac';}
 if(l==='mtir'){reads=[[fs(c),8>>>((c>>>21)&3)]];pipe='fmac';}
 if(l==='div'){reads=[[fs(c),8>>>((c>>>21)&3)],[ft(c),8>>>((c>>>23)&3)]];pipe='q';}
 if(l==='waitq')pipe='q';
 if(['fcget','fceq','fcand','fcor','fcset','fmand','fseq','fsset','fsand','fsor'].includes(l))pipe='fmac';
 if(['ilw','ilwr'].includes(l)){pipe='ialu';viWrite=ft(c)&15;}
 if(['b','bal','jr','jalr','ibeq','ibne','ibltz','ibgtz','iblez','ibgez'].includes(l)) {
  pipe='branch';viRead=['b','bal'].includes(l)?[]:[fs(c)&15];if(['ibeq','ibne'].includes(l))viRead.push(ft(c)&15);
 }
 return {reads,write,mask:m,pipe,viRead,viWrite};
}

export function createNativeVUState({micro,memory,vf,vi,acc,clip=0,mac=0,q=0,i=0,top=0,itop=0}) {
 need(micro instanceof Uint32Array&&micro.length===4096&&memory instanceof Uint32Array&&memory.length===4096
  &&vf instanceof Uint32Array&&vf.length===128&&vi instanceof Uint16Array&&vi.length===16
  &&acc instanceof Uint32Array&&acc.length===4,'Invalid explicit native VU state.');
 need(vf[0]===0&&vf[1]===0&&vf[2]===0&&vf[3]===0x3f800000&&vi[0]===0,'Invalid native constant registers.');
 return {micro:micro.slice(),memory:memory.slice(),vf:vf.slice(),vi:vi.slice(),acc:acc.slice(),clip,visibleClip:clip,
  mac,visibleMac:mac,status:0,visibleStatus:0,q,i,top,itop,cycle:0,pipes:[],alu:[],qPipe:null,backup:null,kicks:[],kick:null};
}

// Register writes are immediate in the pinned interpreter. Pipelines enforce
// operand stalls, delayed flags/Q and the branch's old-VI forwarding rule.
export function runNativeVU(state,startPC,{maxSteps=100000,onGIF,onKick}={}) {
 need(Number.isInteger(startPC)&&startPC>=0&&startPC<2048&&Number.isInteger(maxSteps)&&maxSteps>0,'Invalid native VU execution bounds.');
 const s=state;let pc=startPC,branch=null,delayBranch=null,end=0,steps=0;
 const transfer=(cycles,force,active=true)=>{
  const k=s.kick;if(!k)return;k.cycles+=cycles;k.lastCycle+=cycles;
  let tags=0;
  while(s.kick&&(force||k.cycles>=2)) {
   if(!k.remaining) {
    need(++tags<=4096,'Native GIF transfer tag budget exceeded.');
    const low=s.memory[k.address>>>2],high=s.memory[(k.address>>>2)+1],loops=low&32767,format=(high>>>26)&3,count=(high>>>28)||16;
    k.remaining=16+(format===0?loops*count*16:format===1?Math.ceil(loops*count/2)*16:loops*16);
    need(k.remaining<65536,'Native GIF tag outside bounded transfer profile.');k.end=!!(low&32768);
   }
   const quads=Math.min(k.remaining/16,(16384-k.address)/16,force?Infinity:Math.floor(k.cycles/2));
   need(quads>0,'Native GIF transfer did not advance.');
   const bytes=quads*16;onGIF(new Uint8Array(s.memory.buffer,k.address,bytes).slice());
   if(force&&active)s.cycle+=quads*2;
   k.cycles-=quads*2;k.address=(k.address+bytes)&16383;k.remaining-=bytes;
   if(!k.remaining&&k.end)s.kick=null;
  }
 };
 const flush=()=>{
  while(s.pipes.length&&s.pipes[0].ready<=s.cycle){const p=s.pipes.shift();if(p.clip)s.visibleClip=p.clipValue;s.visibleMac=p.mac;
   s.visibleStatus=p.statusWrite?(s.visibleStatus&0x30)|(p.status&0xfcf):(s.visibleStatus&0xff0)|(p.status&15)|((p.status&15)<<6);}
  s.alu=s.alu.filter(p=>p.ready>s.cycle);
  if(s.qPipe&&s.qPipe.ready<=s.cycle){s.q=s.qPipe.word;s.visibleStatus=(s.visibleStatus&0xfcf)|(s.qPipe.status&0xc30);s.qPipe=null;}
  if(s.kick)transfer(s.cycle-s.kick.lastCycle-1,false);
 };
 const stall=reads=>{for(const [reg,m] of reads)if(reg)for(const p of s.pipes)
  if(p.writes.some(w=>w[0]===reg&&(w[1]&m)))s.cycle=Math.max(s.cycle,p.ready);};
 const backup=reg=>{if(!reg)return;if(s.backup?.remaining&&s.backup.reg===reg)s.backup.remaining=2;
  else s.backup={reg,old:s.vi[reg],remaining:2};};
 const setVI=(reg,value,remember=false)=>{reg&=15;if(reg){if(remember)backup(reg);s.vi[reg]=value&65535;}};
 const scheduleBranch=target=>{const b={target:target&2047,left:2};if(branch?.left===1)delayBranch=b;else branch=b;};
 for(;steps<maxSteps;steps++) {
  const pair=decodeNativeVUPair(s.micro[pc*2],s.micro[pc*2+1]),us=upperShape(pair),ls=lowerShape(pair);
  const cycleBefore=s.cycle++;pc=(pc+1)&2047;
  if(pair.upper&0x40000000)end=2;
  stall(us.reads);
  if(['fmac','q'].includes(ls.pipe))stall(ls.reads);
  if(ls.pipe==='q'&&s.qPipe)s.cycle=Math.max(s.cycle,s.qPipe.ready);
  if(ls.pipe==='branch')for(const pending of s.alu)if(ls.viRead.includes(pending.reg))s.cycle=Math.max(s.cycle,pending.ready);
  flush();if(s.backup)s.backup.remaining=Math.max(0,s.backup.remaining-(s.cycle-cycleBefore));
  const old=s.vf.slice(),oldAcc=s.acc.slice(),oldClip=s.visibleClip;
  const read=(reg,lane)=>old[reg*4+lane];
  const put=(reg,lane,value)=>{if(reg)s.vf[reg*4+lane]=value;};
  const c=pair.upper,u=pair.u,enabled=u==='opmula'||u==='opmsub'?[0,1,2]:lanes(mask(c));
  if(u==='clip') {
   let limit=read(ft(c),3)&0x7fffffff;if(!(limit&0x7f800000))limit=0x7fffff;
   let value=(s.clip<<6)&0xffffff;
   for(let lane=0;lane<3;lane++){const v=read(fs(c),lane);if((v|0)>limit)value|=1<<(lane*2);if(((v^0x80000000)|0)>limit)value|=2<<(lane*2);}
   s.clip=value;
  }else if(u!=='nop') {
   const minmax=/^(max|mini)/.test(u),conversion=/^(ftoi|itof)/.test(u),accumulator=/^(adda|suba|madda|msuba|mula|opmula)/.test(u);
   const {broadcast,scalar}=upperOperands(c);
   for(const lane of enabled) {
    let a=read(fs(c),lane),b=broadcast>=0?read(ft(c),broadcast):scalar==='i'?s.i:scalar==='q'?s.q:read(ft(c),lane),value;
    if(minmax){const aa=a|0,bb=b|0,max=u.startsWith('max');value=(aa<0&&bb<0?(max?Math.min(aa,bb):Math.max(aa,bb)):(max?Math.max(aa,bb):Math.min(aa,bb)))>>>0;}
    else if(u==='abs')value=a&0x7fffffff;
    else if(conversion) {
     const shift=Number(u.slice(4));
     if(u.startsWith('itof'))value=word(mul(intFloat(a|0),2**-shift));
     else {const n=mul(number(a),2**shift);value=(n>=2147483648?0x7fffffff:n<=-2147483648?0x80000000:Math.trunc(n))>>>0;}
    }else {
     a=number(a);b=number(b);let result;
     if(u==='opmula')result=mul(number(read(fs(c),(lane+1)%3)),number(read(ft(c),(lane+2)%3)));
     else if(u==='opmsub')result=add(number(oldAcc[lane]),-mul(number(read(fs(c),(lane+1)%3)),number(read(ft(c),(lane+2)%3))));
     else if(u.startsWith('madd'))result=add(number(oldAcc[lane]),mul(a,b));
     else if(u.startsWith('msub'))result=add(number(oldAcc[lane]),-mul(a,b));
     else if(u.startsWith('mul'))result=mul(a,b);
     else if(u.startsWith('add'))result=add(a,b);
     else if(u.startsWith('sub'))result=add(a,-b);
     else throw Error('Unsupported native upper operation.');
     value=word(result);
     const shift=3-lane;s.mac&=~(0x1111<<shift);if(value>>>31)s.mac|=0x10<<shift;if(result===0)s.mac|=1<<shift;
    }
    if(accumulator)s.acc[lane]=value;else put(conversion||u==='abs'?ft(c):fd(c),lane,value);
   }
   if(!minmax&&!conversion&&u!=='abs') {
    if(u!=='opmula'&&u!=='opmsub')for(const lane of [0,1,2,3])if(!enabled.includes(lane))s.mac&=~(0x1111<<(3-lane));
    s.status=(s.mac&15?1:0)|(s.mac&0xf0?2:0)|(s.mac&0xf00?4:0)|(s.mac&0xf000?8:0);
   }
  }
  const l=pair.l,d=pair.lower,is=fs(d)&15,it=ft(d)&15,id=fd(d)&15,imm=signed11(d&2047),lm=lanes(mask(d));
  const discard=us.write&&us.write===ls.write;
  const address=row=>((row&1023)*4);
  let clipWrite=us.clip;
  if(!discard) {
   if(l==='loi')s.i=d;
   else if(['lq','lqi','lqd'].includes(l)) {
    if(l!=='lq')backup(is);if(l==='lqd')setVI(is,s.vi[is]-1);
    const row=l==='lq'?s.vi[is]+imm:s.vi[is],base=address(row);
    for(const lane of lm)put(ft(d),lane,s.memory[base+lane]);if(l==='lqi')setVI(is,s.vi[is]+1);
   }else if(['sq','sqi','sqd'].includes(l)) {
    if(l!=='sq')backup(it);if(l==='sqd')setVI(it,s.vi[it]-1);
    const row=l==='sq'?s.vi[it]+imm:s.vi[it],base=address(row);
    for(const lane of lm)s.memory[base+lane]=read(fs(d),lane);if(l==='sqi')setVI(it,s.vi[it]+1);
   }else if(['ilw','ilwr'].includes(l)) {
    const base=address(s.vi[is]+(l==='ilw'?imm:0));for(const lane of lm)setVI(it,s.memory[base+lane]);
   }else if(['isw','iswr'].includes(l)) {
    const base=address(s.vi[is]+(l==='isw'?imm:0));for(const lane of lm)s.memory[base+lane]=s.vi[it];
   }else if(l==='move'||l==='mr32')for(const lane of lm)put(ft(d),lane,read(fs(d),l==='mr32'?(lane+1)&3:lane));
   else if(l==='mfir')for(const lane of lm)put(ft(d),lane,signed16(s.vi[is])>>>0);
   else if(l==='mtir')setVI(it,read(fs(d),(d>>>21)&3),true);
   else if(l==='iadd'||l==='isub'||l==='iand'||l==='ior')setVI(id,l==='iadd'?s.vi[is]+s.vi[it]:l==='isub'?s.vi[is]-s.vi[it]:l==='iand'?s.vi[is]&s.vi[it]:s.vi[is]|s.vi[it],true);
   else if(l==='iaddi')setVI(it,s.vi[is]+((fd(d)<<27)>>27),true);
   else if(l==='iaddiu'||l==='isubiu')setVI(it,s.vi[is]+(l==='iaddiu'?1:-1)*(((d>>>21)&15)*2048+(d&2047)),true);
   else if(l==='xtop'||l==='xitop')setVI(it,l==='xtop'?s.top:s.itop);
   else if(l==='div') {
    const a=read(fs(d),(d>>>21)&3),b=read(ft(d),(d>>>23)&3),den=number(b);
    s.status&=~0x30;if(den===0)s.status|=number(a)===0?0x10:0x20;
    s.qPipe={ready:s.cycle+7,status:s.status,word:den===0?((a^b)&0x80000000)|0x7f7fffff:word(divide(number(a),den))};
   }else if(l==='fcset'){if(!us.clip){s.clip=d&0xffffff;clipWrite=true;}}
   else if(l==='fcget')setVI(it,oldClip&4095);
   else if(l==='fcand'||l==='fcor'||l==='fceq')setVI(1,l==='fcand'?!!(oldClip&(d&0xffffff)):l==='fcor'?(oldClip|(d&0xffffff))===0xffffff:oldClip===(d&0xffffff));
   else if(l==='fmand')setVI(it,s.vi[is]&s.visibleMac);
   else if(l==='fsset')s.status=(s.status&0x3f)|((((d>>>21)&1)*2048+(d&2047))&0xfc0);
   else if(['fsand','fsor','fseq'].includes(l)) {
    const imm12=((d>>>21)&1)*2048+(d&2047),flags=s.visibleStatus&4095;
    setVI(it,l==='fsand'?flags&imm12:l==='fsor'?flags|imm12:flags===imm12);
   }
   else if(ls.pipe==='branch') {
    const readVI=reg=>signed16(s.backup?.remaining&&s.backup.reg===reg?s.backup.old:s.vi[reg]);
    const a=readVI(is),b=readVI(it),take=({b:true,bal:true,jr:true,jalr:true,ibeq:a===b,ibne:a!==b,ibltz:a<0,ibgtz:a>0,iblez:a<=0,ibgez:a>=0})[l];
    const target=l==='jr'||l==='jalr'?s.vi[is]:pc+imm;
    if(l==='bal'||l==='jalr')setVI(it,branch?.left===1?branch.target+1:pc+1);
    if(take)scheduleBranch(target);
   }else if(l==='xgkick') {
    need(typeof onGIF==='function','Native XGKICK needs explicit GIF consumer.');
    if(s.kick){transfer(0,true);flush();}
    const row=s.vi[is]&1023;onKick?.(row,s.cycle);s.kicks.push({row,cycle:s.cycle});
    s.kick={address:row*16,remaining:0,end:false,lastCycle:s.cycle,cycles:1};
   }else need(l==='nop'||l==='waitq','Unsupported native lower operation.');
  }
  if(us.flags||ls.pipe==='fmac')s.pipes.push({ready:s.cycle+4,
   writes:[[us.write,us.mask??mask(c)],[discard?0:ls.write,ls.mask]].filter(w=>w[0]),clip:clipWrite,clipValue:s.clip,mac:s.mac,status:s.status,statusWrite:l==='fsset'});
  if(ls.viWrite)s.alu.push({ready:s.cycle+4,reg:ls.viWrite});
  if(branch&&--branch.left===0){pc=branch.target;branch=delayBranch;if(branch)branch.left=1;delayBranch=null;}
  if(end&&--end===0){s.cycle=Math.max(s.cycle,...s.pipes.map(p=>p.ready),...s.alu.map(p=>p.ready),s.qPipe?.ready??0);flush();if(s.kick)transfer(0,true,false);return {state:s,pc,steps:steps+1};}
 }
 throw Error('Native VU instruction budget exceeded.');
}
