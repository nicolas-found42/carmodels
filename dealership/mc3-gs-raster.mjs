// Scalar reconstruction of the selected PCSX2 v2.8.2 AVX2 software-GS path.
// Reference commit fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3:
// GSRendererSW.cpp vertex conversion, GSRasterizer.cpp triangle sections,
// GSDrawScanline.cpp setup/skip-eight stepping and 16.16 texel conversion.
// This contract is tested against independent executed GS replay. It does not
// assert physical GS pixel equivalence or implement native VU transformation.
const f=Math.fround;
const add=(a,b)=>f(a+b),sub=(a,b)=>f(a-b),mul=(a,b)=>f(a*b),div=(a,b)=>f(a/b);
const floatBits=new DataView(new ArrayBuffer(4));
// The pinned distributed AVX2 binary contracts triangle setup/prestep into
// VFMADD/VFMSUB. Integer significands avoid an intermediate double rounding.
export function fusedGSFloat32(a,b,c) {
 const parts=value=>{
  floatBits.setFloat32(0,value,true);const bits=floatBits.getUint32(0,true),exponent=(bits>>>23)&255;
  return {n:BigInt((bits&0x7fffff)|(exponent?0x800000:0))*(bits>>>31?-1n:1n),e:exponent?exponent-150:-149};
 };
 a=f(a);b=f(b);c=f(c);if(![a,b,c].every(Number.isFinite))return f(a*b+c);
 const aa=parts(a),bb=parts(b),cc=parts(c),productExponent=aa.e+bb.e,exponent=Math.min(productExponent,cc.e);
 let n=(aa.n*bb.n<<BigInt(productExponent-exponent))+(cc.n<<BigInt(cc.e-exponent));
 if(!n)return f(a*b+c);
 const sign=n<0n?-1:1;if(sign<0)n=-n;
 const unit=Math.max(exponent+n.toString(2).length-24,-149),shift=unit-exponent;
 if(shift>0) {
  const amount=BigInt(shift),remainder=n&((1n<<amount)-1n),half=1n<<(amount-1n);
  n>>=amount;if(remainder>half||(remainder===half&&(n&1n)))n++;
 } else n<<=BigInt(-shift);
 return f(sign*Number(n)*2**unit);
}
const doubleBits=new DataView(new ArrayBuffer(8));
export function fusedGSFloat64(a,b,c) {
 if(![a,b,c].every(Number.isFinite))return a*b+c;
 const parts=value=>{
  doubleBits.setFloat64(0,value,true);const bits=doubleBits.getBigUint64(0,true),exponent=Number((bits>>52n)&2047n);
  return {n:((bits&0xfffffffffffffn)|(exponent?0x10000000000000n:0n))*(bits>>63n?-1n:1n),e:exponent?exponent-1075:-1074};
 };
 const aa=parts(a),bb=parts(b),cc=parts(c),productExponent=aa.e+bb.e,exponent=Math.min(productExponent,cc.e);
 let n=(aa.n*bb.n<<BigInt(productExponent-exponent))+(cc.n<<BigInt(cc.e-exponent));
 if(!n)return a*b+c;
 const sign=n<0n?-1:1;if(sign<0)n=-n;
 const unit=Math.max(exponent+n.toString(2).length-53,-1074),shift=unit-exponent;
 if(shift>0) {
  const amount=BigInt(shift),remainder=n&((1n<<amount)-1n),half=1n<<(amount-1n);
  n>>=amount;if(remainder>half||(remainder===half&&(n&1n)))n++;
 } else n<<=BigInt(-shift);
 return sign*Number(n)*2**unit;
}
function boundedInt32(value) {
 if(!Number.isFinite(value)||value< -2147483648||value>=2147483648)throw Error('Unsupported GS texture conversion range.');
 return Math.trunc(value);
}
// GSState::FlushPrim applies this truncation for constant-depth textured
// triangle draws, after tracing the original Q values for draw dispatch.
export function roundGSSTQ(stq) {
 const bits=stq.map(value=>{floatBits.setFloat32(0,value,true);return floatBits.getUint32(0,true);});
 const qExponent=(bits[2]>>>23)&255;
 for(let i=0;i<2;i++) {
  const exponent=(bits[i]>>>23)&255,amount=Math.min(9+Math.max(0,qExponent-exponent),23);
  bits[i]&=~((1<<amount)-1);
 }
 bits[2]&=~255;
 return bits.map(value=>{floatBits.setUint32(0,value,true);return floatBits.getFloat32(0,true);});
}
const sorted=[[0,1,2],[1,0,2],[0,0,0],[1,2,0],[0,2,1],[0,0,0],[2,0,1],[2,1,0]];

// Bounded native capture transport: PACKED STQ/RGBA/XYZF2 only. GSRegs.h
// defines these fields; GSState::Transfer ignores zero-loop PRE, while
// ApplyPRIM restarts primitive assembly even when its value is unchanged.
// The returned groups preserve topology, not software-GS flush boundaries.
// Strip/fan groups can share a draw; prepareNativeGSDraw traces them together.
export function decodeNativeGIF(bytes) {
 if(!(bytes instanceof Uint8Array)||bytes.length%16)throw Error('Invalid native GIF byte stream.');
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),draws=[];
 let offset=0,primitive,draw,history=[],stq,rgba;
 while(offset<bytes.length) {
  const low=view.getUint32(offset,true),high=view.getUint32(offset+4,true),loops=low&0x7fff;
  const count=(high>>>28)||16,format=(high>>>26)&3,registers=view.getUint32(offset+8,true)&0xfff;
  offset+=16;
  if(!loops)continue;
  if(format!==0||count!==3||registers!==0x412)throw Error('Unsupported native GIF layout.');
  if(offset+loops*48>bytes.length)throw Error('Truncated native GIF payload.');
  if(high&0x4000) {
   const next=(high>>>15)&0x7ff;
   if((next&7)!==4&&(next&7)!==5)throw Error('Unsupported native GIF primitive.');
   if(next!==primitive){draw={primitive:next,vertices:[],indices:[]};draws.push(draw);}
   primitive=next;history=[];
  }
  if(primitive===undefined)throw Error('Native GIF initial primitive is missing.');
  // Every nonempty tag resets the GIF Q latch. STQ then supplies the Q
  // captured by RGBA, before XYZF2 emits the vertex.
  stq=undefined;rgba=undefined;
  for(let i=0;i<loops;i++,offset+=48) {
   stq=[0,4,8].map(k=>view.getFloat32(offset+k,true));
   rgba=[0,4,8,12].map(k=>view.getUint8(offset+16+k));
   const zword=view.getUint32(offset+40,true),last=view.getUint32(offset+44,true);
   const vertex={xy:[view.getUint16(offset+32,true),view.getUint16(offset+36,true)],
    z:(zword>>>4)&0xffffff,stq,rgba,fog:(last>>>4)&255,adc:!!(last&0x8000)};
   const index=draw.vertices.length;draw.vertices.push(vertex);history.push(index);
   if(history.length>=3&&!vertex.adc) {
    const n=history.length;
    draw.indices.push(...((primitive&7)===5?[history[0],history[n-2],index]:
     [history[n-3],history[n-2],index]));
   }
  }
 }
 return draws;
}

// GSState::VertexKick at native resolution rejects these bounds before
// tracing STQ. GSDrawingContext expands inclusive SCISSOR by half a pixel;
// the transport consumer supplies its usual half-open pixel bounds here.
export function intersectsGSScissor(vertices,{xyOffset,scissor}) {
 const x=vertices.map(v=>v.xy[0]-xyOffset[0]),y=vertices.map(v=>v.xy[1]-xyOffset[1]);
 for(let i=0;i<3;i++)for(let j=i+1;j<3;j++)if(x[i]===x[j]&&y[i]===y[j])return false;
 const box=[(Math.min(...x)+15)&~15,(Math.min(...y)+15)&~15,
  ((Math.max(...x)-1)&~15)+1,((Math.max(...y)-1)&~15)+1];
 if(box[0]>=box[2]||box[1]>=box[3])return false;
 const cull=[scissor[0]*16-8,scissor[1]*16-8,(scissor[2]-1)*16+8,(scissor[3]-1)*16+8];
 return box[0]<cull[2]&&box[1]<cull[3]&&box[2]+1>cull[0]&&box[3]+1>cull[1];
}

// One material/context flush, possibly containing many PRE fan/strip tags.
// Select constant-Q from the original referenced vertices AFTER GS bounds
// rejection, then apply constant-depth STQ truncation without retracing Q.
export function prepareNativeGSDraw(bytes,state) {
 const groups=decodeNativeGIF(bytes),vertices=[],indices=[];
 for(const group of groups) {
  const base=vertices.length;vertices.push(...group.vertices);
  for(let i=0;i<group.indices.length;i+=3) {
   const triangle=group.indices.slice(i,i+3);
   if(intersectsGSScissor(triangle.map(n=>group.vertices[n]),state))indices.push(...triangle.map(n=>n+base));
  }
 }
 const q=indices.length?vertices[indices[0]].stq[2]:undefined;
 const constantQ=indices.every(i=>vertices[i].stq[2]===q);
 const constantZ=vertices.length===0||vertices.every(v=>v.z===vertices[0].z);
 return {vertices:vertices.map(v=>({...v,stq:constantZ?roundGSSTQ(v.stq):v.stq})),indices,constantQ,constantZ};
}

// Selected PCSX2 v2.8.2 AVX2 software-GS arithmetic, not a hardware-equivalence claim.
// xy includes the packed GS XYOFFSET. z is the decoded GS integer value:
// native XYZF2 transport removes the four fractional bits in the VU word.
// constantQ is a whole-draw decision supplied by the packet consumer.
// zEqual/zOverflow are optional whole-draw GS trace selectors. The bounded
// single-triangle fallback corrects raw depth equality by default; callers with
// TEST.ZTST<=ALWAYS supply depthTraceCorrected=false or explicit draw selectors.
// emitQ opts into the original interpolated float32 Q needed by variable LOD;
// the default pixel contract keeps its existing u/v/z fields.
export function rasterizeGSTriangle(vertices,{xyOffset,scissor,textureSize,constantQ,bilinear=true,emitQ=false,depthTraceCorrected=true,zEqual,zOverflow,onPixel}={}) {
 if(!Array.isArray(vertices)||vertices.length!==3||!Array.isArray(xyOffset)||xyOffset.length!==2
  ||!Array.isArray(scissor)||scissor.length!==4||!Array.isArray(textureSize)||textureSize.length!==2
  ||typeof constantQ!=='boolean'||typeof bilinear!=='boolean'||typeof emitQ!=='boolean'||typeof depthTraceCorrected!=='boolean'||typeof onPixel!=='function')throw Error('Explicit GS triangle state is required.');
 const [width,height]=textureSize;
 if(![...xyOffset,...scissor,width,height].every(Number.isInteger)||width<1||height<1)throw Error('Invalid GS triangle bounds.');
 for(const vertex of vertices) {
  if(!Array.isArray(vertex.xy)||vertex.xy.length!==2||!vertex.xy.every(v=>Number.isInteger(v)&&v>=0&&v<=65535)
   ||!Number.isInteger(vertex.z)||vertex.z<0||vertex.z>0xffffffff||!Array.isArray(vertex.stq)||vertex.stq.length!==3
   ||!vertex.stq.every(Number.isFinite)||vertex.stq[2]<=0)throw Error('Invalid bounded native GS vertex.');
 }
 if(constantQ&&!vertices.every(v=>f(v.stq[2])===f(vertices[0].stq[2])))throw Error('Constant-Q GS draw has varying Q.');

 if((zEqual!==undefined&&typeof zEqual!=='boolean')||(zOverflow!==undefined&&typeof zOverflow!=='boolean'))throw Error('Invalid explicit GS depth trace selectors.');
 const tracedEqual=vertices.every(v=>f(v.z)===f(vertices[0].z));
 const correctedWord=vertices.reduce((z,v)=>vertices[0].z&1?(z&v.z)>>>0:(z|v.z)>>>0,vertices[0].z);
 const equalZ=zEqual??(tracedEqual&&(!depthTraceCorrected||correctedWord===vertices[0].z)),overflowZ=zOverflow??(f(Math.max(...vertices.map(v=>v.z)))>=2147483648);
 const roundEven=value=>{const base=Math.floor(value),fraction=value-base;return fraction>.5||fraction===.5&&base%2!==0?base+1:base;};
 // Selected GS zequal bypass converts/broadcasts the scanline anchor Z. Varying high depths
 // use CVTPD2DQ's RNE after the source double bias, then unsigned offset.
 const depthWord=(value,scan)=>equalZ?(Math.trunc(scan)>>>0):overflowZ?((roundEven(value-2147483648.4999995)+2147483648)>>>0):(Math.trunc(value)>>>0);
 const halfPel=bilinear?32768:0;
 const cv=vertices.map(v=>({x:f((v.xy[0]-xyOffset[0])/16),y:f((v.xy[1]-xyOffset[1])/16),z:v.z,
  t:constantQ?[sub(mul(div(f(v.stq[0]),f(v.stq[2])),width*65536),halfPel),sub(mul(div(f(v.stq[1]),f(v.stq[2])),height*65536),halfPel),0]:[mul(f(v.stq[0]),width*65536),mul(f(v.stq[1]),height*65536),f(v.stq[2])]}));
 const order=(cv[0].y>cv[1].y?1:0)|(cv[0].y>cv[2].y?2:0)|(cv[1].y>cv[2].y?4:0);
 const [a,b,c]=sorted[order].map(i=>cv[i]);if(a.y===c.y)return;
 const dx0=sub(b.x,a.x),dy0=sub(b.y,a.y),dx1=sub(c.x,a.x),dy1=sub(c.y,a.y);
 const cross=sub(mul(dy0,dx1),mul(dx0,dy1));if(!cross)return;
 const nx0=div(dx0,cross),ny0=div(dy0,cross),nx1=div(dx1,cross),ny1=div(dy1,cross);
 const tx=[0,1,2].map(i=>fusedGSFloat32(sub(c.t[i],a.t[i]),ny0,-mul(sub(b.t[i],a.t[i]),ny1)));
 const ty=[0,1,2].map(i=>fusedGSFloat32(sub(b.t[i],a.t[i]),nx1,-mul(sub(c.t[i],a.t[i]),nx0)));
 const zx=fusedGSFloat64(c.z-a.z,ny0,-((b.z-a.z)*ny1)),zy=fusedGSFloat64(b.z-a.z,nx1,-((c.z-a.z)*nx0));
 const longSlope=div(dx1,dy1),upperSlope=div(dx0,dy0),lowerSlope=div(sub(c.x,b.x),sub(c.y,b.y));
 const leftLong=cross<0;
 function section(top,bottom,anchor,leftBase,rightBase,leftSlope,rightSlope) {
  top=Math.max(Math.ceil(top),scissor[1]);bottom=Math.min(Math.ceil(bottom),scissor[3]);
  for(let y=top;y<bottom;y++) {
   const dy=sub(y,anchor.y),left=Math.max(Math.ceil(fusedGSFloat32(leftSlope,dy,leftBase)),scissor[0]);
   const right=Math.min(Math.ceil(fusedGSFloat32(rightSlope,dy,rightBase)),scissor[2]);if(left>=right)continue;
   const prestep=sub(left,anchor.x),scan=anchor.t.map((t,i)=>fusedGSFloat32(tx[i],prestep,fusedGSFloat32(ty[i],dy,t)));
   const scanZ=fusedGSFloat64(zx,prestep,fusedGSFloat64(zy,dy,anchor.z)),skip=left&7,start=left-skip;
   const lanes=Array.from({length:8},(_,i)=>scan.map((t,k)=>constantQ?(boundedInt32(t)+boundedInt32(mul(tx[k],i-skip)))|0:add(t,mul(tx[k],i-skip))));
   const zs=Array.from({length:8},(_,i)=>scanZ+mul(f(zx),i-skip));
   const step=tx.map(t=>constantQ?boundedInt32(mul(t,8)):mul(t,8));
   for(let x=start;x<right;x+=8) {
    for(let i=0;i<8;i++)if(x+i>=left&&x+i<right) {
     const t=lanes[i];
     const u=constantQ?t[0]:(boundedInt32(div(t[0],t[2]))-halfPel)|0;
     const v=constantQ?t[1]:(boundedInt32(div(t[1],t[2]))-halfPel)|0;
     onPixel(x+i,y,{u,v,z:depthWord(zs[i],scanZ),...(emitQ?{q:constantQ?f(vertices[0].stq[2]):t[2]}:{})});
    }
    for(let i=0;i<8;i++){for(let k=0;k<3;k++)lanes[i][k]=constantQ?(lanes[i][k]+step[k])|0:add(lanes[i][k],step[k]);zs[i]+=zx*8;}
   }
  }
 }
 if(a.y===b.y) {
  const anchor=leftLong?a:b;
  section(a.y,c.y,anchor,Math.min(a.x,b.x),Math.max(a.x,b.x),leftLong?longSlope:lowerSlope,leftLong?lowerSlope:longSlope);
 } else {
  section(a.y,b.y,a,a.x,a.x,leftLong?longSlope:upperSlope,leftLong?upperSlope:longSlope);
  const longAtMid=fusedGSFloat32(longSlope,dy0,a.x);
  const upperAtMid=fusedGSFloat32(upperSlope,dy0,a.x);
  section(b.y,c.y,b,leftLong?longAtMid:upperAtMid,leftLong?upperAtMid:longAtMid,leftLong?longSlope:lowerSlope,leftLong?lowerSlope:longSlope);
 }
}

export function sampleGSFixedRGBA(image,u,v,wrap='repeat') {
 if(!Number.isInteger(u)||!Number.isInteger(v))throw Error('GS sampling needs signed 16.16 integers.');
 const {width,height,data}=image,x=u>>16,y=v>>16,fx=(u>>>12)&15,fy=(v>>>12)&15;
 const bound=(v,n)=>wrap==='clamp'?Math.max(0,Math.min(n-1,v)):((v%n)+n)%n;
 const at=(x,y,c)=>data[(bound(y,height)*width+bound(x,width))*4+c];
 return [0,1,2,3].map(c=>{
  const top=(at(x,y,c)*(16-fx)+at(x+1,y,c)*fx)>>4;
  const bottom=(at(x,y+1,c)*(16-fx)+at(x+1,y+1,c)*fx)>>4;
  return (top*(16-fy)+bottom*fy)>>4;
 });
}

// Native capture uses PSMZ16S. The selected software-GS clamps source depth
// before testing against the stored sixteen bits (GSRendererSW zclamp and
// GSDrawScanline ZTST), rather than wrapping an overflowing source value.
export function testGSDepth16(source,stored,test='gequal') {
 if(!Number.isInteger(source)||source<0||source>0x7fffffff
  ||!Number.isInteger(stored)||stored<0||stored>65535)throw Error('Invalid bounded GS depth.');
 const z=Math.min(source,65535);
 if(test==='always')return {pass:true,z};
 if(test==='gequal')return {pass:z>=stored,z};
 if(test==='greater')return {pass:z>stored,z};
 if(test==='never')return {pass:false,z};
 throw Error('Unsupported GS depth test.');
}
