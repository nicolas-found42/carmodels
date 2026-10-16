// Bounded original vehicle VU arithmetic. Inputs are explicit native uniforms;
// this module supplies neither invented lights nor default gameplay state.
// Pinned interpreter uses separate MUL/ADD with round toward zero, DAZ/FTZ.
const bits=new DataView(new ArrayBuffer(4));
export function nativeFloatWords(values) {
 return values.map(value=>{bits.setFloat32(0,value,true);return bits.getUint32(0,true);});
}
function parts(value) {
 bits.setFloat32(0,value,true);const word=bits.getUint32(0,true),exponent=(word>>>23)&255;
 if(exponent===255)throw Error('Nonfinite native VU input.');
 return {n:exponent?BigInt((word&0x7fffff)|0x800000)*(word>>>31?-1n:1n):0n,e:exponent-150,negative:!!(word>>>31)};
}
function roundRatio(n,d,e) {
 if(!n)return 0;
 const negative=(n<0n)!==(d<0n);if(n<0n)n=-n;if(d<0n)d=-d;
 let order=n.toString(2).length-d.toString(2).length;
 if(order>=0?n<(d<<BigInt(order)):(n<<BigInt(-order))<d)order--;
 const power=e+order;
 if(power< -126)return negative?-0:0;
 if(power>127)throw Error('Native VU arithmetic outside bounded finite profile.');
 const unit=power-23,shift=e-unit;
 const significand=shift>=0?(n<<BigInt(shift))/d:n/(d<<BigInt(-shift));
 return (negative?-1:1)*Number(significand)*2**unit;
}
export function nativeVUAdd(a,b) {
 const x=parts(a),y=parts(b),e=Math.min(x.e,y.e);
 if(!x.n&&!y.n)return x.negative&&y.negative?-0:0;
 return roundRatio((x.n<<BigInt(x.e-e))+(y.n<<BigInt(y.e-e)),1n,e);
}
export function nativeVUMultiply(a,b) {
 const x=parts(a),y=parts(b);if(!x.n||!y.n)return x.negative!==y.negative?-0:0;
 return roundRatio(x.n*y.n,1n,x.e+y.e);
}
export function nativeVUDivide(a,b) {
 const x=parts(a),y=parts(b);if(!y.n)throw Error('Native VU division by zero.');
 if(!x.n)return x.negative!==y.negative?-0:0;
 return roundRatio(x.n,y.n,x.e-y.e);
}
const add=nativeVUAdd,mul=nativeVUMultiply;
function vector(value,length,label) {
 if(!Array.isArray(value)||value.length!==length||!value.every(Number.isFinite))throw Error('Invalid native '+label+'.');
 return value.map(Math.fround);
}
function rows(value,count,width,label) {
 if(!Array.isArray(value)||value.length!==count)throw Error('Invalid native '+label+'.');
 return value.map(row=>vector(row,width,label));
}
function sumProducts(columns,lanes,width) {
 return Array.from({length:width},(_,i)=>{
  let sum=mul(columns[0][i],lanes[0]);
  for(let k=1;k<lanes.length;k++)sum=add(sum,mul(columns[k][i],lanes[k]));
  return sum;
 });
}

export function nativeVehicleLighting(normal,lightRows,lightColors,material) {
 normal=vector(normal,3,'raw normal');lightRows=rows(lightRows,3,3,'light coefficients');
 lightColors=rows(lightColors,4,4,'light colors');material=vector(material,4,'material RGBA');
 const coefficients=sumProducts(lightRows,normal,3).map(value=>Math.max(0,value));
 const light=sumProducts(lightColors,[...coefficients,1],4).map(value=>Math.min(1,value));
 return light.map((value,i)=>Math.trunc(mul(value,material[i])));
}

// These are contiguous source kernels, not a whole draw or framebuffer claim.
// ST is retained with Q; the GS performs the later perspective division.
export function nativeVehicleVertex(input) {
 const {program}=input;
 if(!['carpaint_3pass_dc','carbon_fiber_dc','light_texgen_dc','texgen_fresnel_dc'].includes(program))throw Error('Unsupported native vehicle kernel.');
 const normal=vector(input.normal,3,'raw normal'),material=vector(input.material,4,'material RGBA');
 const mvp=rows(input.mvp,4,4,'MVP'),uv=rows(input.uvMatrix,3,4,'UV matrix');
 const parameters=vector(input.parameters,4,'generation parameters'),position=vector(input.position,3,'position');
 const n=sumProducts(mvp,normal.map(value=>mul(value,1/128)),4);
 const p=Array.from({length:4},(_,i)=>{
  let sum=mvp[3][i];
  for(let k=0;k<3;k++)sum=add(sum,mul(mvp[k][i],position[k]));
  return sum;
 }),q=nativeVUDivide(1,p[3]);
 let rgba;
 if(program==='texgen_fresnel_dc') {
  const alpha=Math.min(parameters[2],Math.max(parameters[1],mul(add(n[3],1),parameters[3])));
  rgba=material.map((value,i)=>Math.trunc(mul(i===3?alpha:1,value)));
 } else rgba=nativeVehicleLighting(normal,input.lightRows,input.lightColors,material);
 const result={rgba};
 if(program!=='carbon_fiber_dc') {
  const generated=(scale,projective=true)=>{
   const xy=n.slice(0,2).map((value,i)=>add(mul(p[i],scale),value));
   const mapped=sumProducts(uv,[...xy,1],3);
   return [mul(mapped[0],q),mul(mapped[1],q),projective?mul(mapped[2],q):q];
  };
  result.stq=generated(parameters[0],program!=='carpaint_3pass_dc');
  if(program==='carpaint_3pass_dc')result.secondStq=generated(Math.fround(.2));
 }
 return result;
}
