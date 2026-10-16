// Bounded PSMCT32/PSMT8/PSMT4 IMAGE and CSM1/CT32 CLUT profile.
// Addresses follow pinned PCSX2 GSTables and GSOffset; unsupported profiles fail closed.
const SIZE = 4 * 1024 * 1024;
const profiles = new Map([
  [0, {px:64, py:32, bx:8, by:8, bits:32, block:[1,4,16,2,8], col:[1,4,8,2,16,32]}],
  [19, {px:128, py:64, bx:16, by:16, bits:8, block:[1,4,16,2,8], col:[4,16,32,2,8,33,96,128]}],
  [20, {px:128, py:128, bx:32, by:16, bits:4, block:[2,8,1,4,16], col:[8,32,64,2,4,16,65,192,256]}],
]);
const field = (n, shift, bits) => Number((n >> BigInt(shift)) & ((1n << BigInt(bits)) - 1n));
function integer(v, max, name) { if (!Number.isInteger(v) || v < 0 || v > max) throw Error(`invalid ${name}`); }
function xorBits(x, y, width, basis) {
  let n = x | (y << Math.log2(width)), out = 0;
  for (let k=0; k<basis.length; k++) if (n & (1<<k)) out ^= basis[k];
  return out;
}
export function nativeGSPixelAddress(psm, x, y, bp, bw) {
  const p=profiles.get(psm); if (!p) throw Error('unsupported GS storage format');
  integer(x,2047,'GS x'); integer(y,2047,'GS y'); integer(bp,16383,'GS base'); integer(bw,63,'GS width');
  const block=xorBits(Math.floor(x%p.px/p.bx),Math.floor(y%p.py/p.by),p.px/p.bx,p.block);
  const col=xorBits(x%p.bx,y%p.by,p.bx,p.col);
  const address=(((bp*256+Math.floor(y/p.py)*Math.floor(bw*64/p.px)*8192)%SIZE)+Math.floor(x/p.px)*8192)*8 + block*2048 + col*p.bits;
  // Do not silently reinterpret address overflow outside this bounded VRAM profile.
  if (address < 0 || address+p.bits > SIZE*8) throw Error('GS address outside VRAM');
  return {byte:Math.floor(address/8), shift:address%8, bits:p.bits};
}
export function createNativeGSVRAM(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length!==SIZE) throw Error('GS VRAM must contain exactly 4 MiB');
  return {bytes:bytes.slice(), registers:new Map(), transfer:null, clut:new Uint8Array(1024), cbp:[0,0]};
}
export function readNativeGSPixel(state, psm, x, y, bp, bw) {
  const a=nativeGSPixelAddress(psm,x,y,bp,bw), b=state.bytes;
  if (a.bits===4) return (b[a.byte]>>a.shift)&15;
  if (a.bits===8) return b[a.byte];
  return new DataView(b.buffer,b.byteOffset,b.byteLength).getUint32(a.byte,true);
}
export function writeNativeGSPixel(state, psm, x, y, bp, bw, value) {
  const a=nativeGSPixelAddress(psm,x,y,bp,bw), b=state.bytes;
  integer(value,a.bits===32?0xffffffff:(1<<a.bits)-1,'GS pixel');
  if (a.bits===4) b[a.byte]=(b[a.byte]&~(15<<a.shift))|(value<<a.shift);
  else if (a.bits===8) b[a.byte]=value;
  else new DataView(b.buffer,b.byteOffset,b.byteLength).setUint32(a.byte,value,true);
}
function textureProfile(tex0) {
  const psm=field(tex0,20,6), width=2**field(tex0,26,4),height=2**field(tex0,30,4);
  if (!profiles.has(psm)||width>1024||height>1024) throw Error('unsupported GS texture profile');
  if (psm!==0 && (field(tex0,51,4)!==0 || field(tex0,55,1)!==0 || field(tex0,56,5)!==0)) throw Error('unsupported GS CLUT profile');
  return {psm,width,height,bp:field(tex0,0,14),bw:field(tex0,14,6),cbp:field(tex0,37,14)};
}
function loadCLUT(state,tex0) {
  const p=textureProfile(tex0); if (p.psm===0) return;
  const cld=field(tex0,61,3); if ([0,6,7].includes(cld)) return;
  const slot=(cld===3||cld===5)?1:0;
  if ((cld===4||cld===5)&&state.cbp[slot]===p.cbp) return;
  if (cld>=2) state.cbp[slot]=p.cbp;
  const count=p.psm===19?256:16, view=new DataView(state.bytes.buffer,state.bytes.byteOffset,state.bytes.byteLength);
  // CSM1 CT32 CLUT loads consume physical words, not a linear RGBA image.
  const small=[0,1,4,5,8,9,12,13,2,3,6,7,10,11,14,15];
  for (let i=0;i<count;i++) {
    const word=small[i&15]+((i&16)<<2)+((i&32)>>1)+((i&64)>>1)+(i&128);
    const offset=p.cbp*256+word*4;
    if (offset+4>SIZE) throw Error('GS CLUT outside VRAM');
    const value=view.getUint32(offset,true);
    for(let c=0;c<4;c++) state.clut[i*4+c]=(value>>>(c*8))&255;
  }
}
export function writeNativeGSRegister(state,address,value) {
  integer(address,127,'GS register'); if(typeof value!=='bigint'||value<0n||value>0xffffffffffffffffn) throw Error('invalid GS register value');
  if(address===6||address===7) loadCLUT(state,value);
  if(address===0x53) {
    if(value!==0n) throw Error('unsupported GS transfer direction');
    for(const reg of [0x50,0x51,0x52]) if(!state.registers.has(reg)) throw Error('missing GS transfer register');
    const blt=state.registers.get(0x50),pos=state.registers.get(0x51),size=state.registers.get(0x52);
    if(field(pos,59,2)!==0) throw Error('unsupported GS transfer traversal');
    const psm=field(blt,56,6),p=profiles.get(psm); if(!p) throw Error('unsupported GS IMAGE format');
    const width=field(size,0,12),height=field(size,32,12),x=field(pos,32,11),y=field(pos,48,11);
    if(!width||!height||x+width>2048||y+height>2048) throw Error('invalid GS transfer extent');
    state.transfer={psm,bp:field(blt,32,14),bw:field(blt,48,6),x,y,width,height,bits:p.bits,pixel:0,pending:[]};
  }
  state.registers.set(address,value);
}
export function uploadNativeGSImage(state,bytes) {
  const t=state.transfer; if(!t||!(bytes instanceof Uint8Array)||bytes.length%16) throw Error('invalid GS IMAGE payload');
  const total=t.width*t.height, data=new Uint8Array(t.pending.length+bytes.length); data.set(t.pending);data.set(bytes,t.pending.length);
  let bit=0;
  while(t.pixel<total&&bit+t.bits<=data.length*8) {
    let value;
    if(t.bits===32) value=new DataView(data.buffer).getUint32(bit/8,true);
    else value=(data[bit>>3]>>(bit&7))&((1<<t.bits)-1);
    writeNativeGSPixel(state,t.psm,t.x+t.pixel%t.width,t.y+Math.floor(t.pixel/t.width),t.bp,t.bw,value);
    t.pixel++;bit+=t.bits;
  }
  if(t.pixel===total) { if(data.length*8-bit>=128) throw Error('GS IMAGE exceeds transfer'); t.pending=[]; }
  else t.pending=Array.from(data.subarray(bit/8));
  return t.pixel===total;
}
export function readNativeGSTexture(state,tex0) {
  if(typeof tex0!=='bigint') throw Error('invalid GS TEX0');
  const p=textureProfile(tex0),data=new Uint8Array(p.width*p.height*4);
  for(let y=0;y<p.height;y++) for(let x=0;x<p.width;x++) {
    const pixel=readNativeGSPixel(state,p.psm,x,y,p.bp,p.bw),offset=(y*p.width+x)*4;
    if(p.psm===0) for(let c=0;c<4;c++)data[offset+c]=(pixel>>>(c*8))&255;
    else data.set(state.clut.subarray(pixel*4,pixel*4+4),offset);
  }
  return {width:p.width,height:p.height,data,readOnly:true};
}
