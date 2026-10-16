import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createNativeGSVRAM, writeNativeGSRegister, uploadNativeGSImage, readNativeGSTexture,
  nativeGSPixelAddress, readNativeGSPixel, writeNativeGSPixel} from '../dealership/mc3-gs-vram.mjs';
import {decodeNativeVehicleGIF, renderNativeVehicleGIF} from '../dealership/mc3-vehicle-gif.mjs';
const fixture=process.argv[2]??new URL('../research/evidence/midnight-club-3-remix/previews/vehicle-vram.json',import.meta.url);
const proof=JSON.parse(readFileSync(fixture)), sha=b=>createHash('sha256').update(b).digest('hex');
for(const row of proof.controls) {
  const vram=createNativeGSVRAM(new Uint8Array(4*1024*1024));
  for(const upload of row.case.uploads) {
    for(const [r,v] of upload.registers)writeNativeGSRegister(vram,r,BigInt(v));
    const bytes=new Uint8Array(Buffer.from(upload.hex,'hex'));
    // Split IMAGE payloads without restarting the native transfer cursor.
    for(let i=0;i<bytes.length;i+=16)uploadNativeGSImage(vram,bytes.subarray(i,i+16));
  }
  const tex0=BigInt(row.case.tex0);writeNativeGSRegister(vram,6,tex0);
  const image=readNativeGSTexture(vram,tex0);
  const decoded=decodeNativeVehicleGIF(row.draw_chunks.map(p=>new Uint8Array(Buffer.from(p,'hex'))),{initialRegisters:new Map([[0x1a,1n]])});
  const target={fbp:0,fbw:4,zbp:128,width:256,height:256,rgba:new Uint8Array(256*256*4),depth:new Uint16Array(256*256)};
  renderNativeVehicleGIF(decoded,{target,resolveTexture:()=>image});
  for(const [field,stride] of [['frames',4],['depth_frames',2]]) {
    const frames=row.execution[field], [w,h]=frames[0].size,bytes=new Uint8Array(w*h*stride),view=new DataView(bytes.buffer);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
      if(stride===4)bytes.set(target.rgba.subarray((y*256+x)*4,(y*256+x)*4+4),(y*w+x)*4);
      else view.setUint16((y*w+x)*2,target.depth[y*256+x],true);
    }
    assert.equal(frames.length,3);assert.ok(frames.every(f=>f.sha256===sha(bytes)),row.case.name+' '+field);
  }
  console.log('PASS original GS IMAGE '+row.case.name+' RGBA/Z16 in three frames');
}
const original=new Uint8Array(4*1024*1024);original.fill(0x5a);const s=createNativeGSVRAM(original);
writeNativeGSPixel(s,20,0,0,0,1,3);assert.equal(readNativeGSPixel(s,20,0,0,0,1),3);assert.equal(s.bytes[0],0x53);assert.equal(original[0],0x5a);
assert.throws(()=>createNativeGSVRAM(),/4 MiB/);
assert.throws(()=>createNativeGSVRAM(new Uint8Array(1)),/4 MiB/);
assert.throws(()=>nativeGSPixelAddress(1,0,0,0,1),/format/);
assert.throws(()=>nativeGSPixelAddress(0,2048,0,0,1),/GS x/);
assert.throws(()=>nativeGSPixelAddress(0,64,0,16383,1),/outside/);
assert.throws(()=>uploadNativeGSImage(s,new Uint8Array(16)),/payload/);
assert.throws(()=>writeNativeGSRegister(s,0x53,1n),/direction/);
assert.throws(()=>writeNativeGSRegister(s,0x53,0n),/missing/);
assert.throws(()=>readNativeGSTexture(s,19n<<20n|1n<<55n),/CLUT/);
assert.throws(()=>readNativeGSTexture(s,19n<<20n|1n<<56n),/CLUT/);
// CLD0 preserves the cached original RGBA (including alpha), despite a later VRAM write.
const u=proof.controls[1].case;const c=createNativeGSVRAM(new Uint8Array(4*1024*1024));
for(const item of u.uploads){for(const [r,v]of item.registers)writeNativeGSRegister(c,r,BigInt(v));uploadNativeGSImage(c,new Uint8Array(Buffer.from(item.hex,'hex')));}
writeNativeGSRegister(c,6,BigInt(u.tex0));const before=readNativeGSTexture(c,BigInt(u.tex0)).data;
c.bytes.fill(255,0x3000*256,0x3000*256+1024);writeNativeGSRegister(c,6,BigInt(u.tex0)&~(7n<<61n));
assert.deepEqual(readNativeGSTexture(c,BigInt(u.tex0)).data,before);
writeNativeGSRegister(c,6,BigInt(u.tex0));assert.notDeepEqual(readNativeGSTexture(c,BigInt(u.tex0)).data,before);
console.log('PASS explicit VRAM ownership, unsupported profiles, transfer bounds, nibble preservation and CLUT cache');
const transfer=createNativeGSVRAM(new Uint8Array(4*1024*1024));
for(const [r,v]of [[0x50,0n],[0x51,0n],[0x52,1n|1n<<32n]])writeNativeGSRegister(transfer,r,v);
writeNativeGSRegister(transfer,0x50,1n<<56n);assert.throws(()=>writeNativeGSRegister(transfer,0x53,0n),/IMAGE format/);
writeNativeGSRegister(transfer,0x50,0n);writeNativeGSRegister(transfer,0x51,1n<<59n);assert.throws(()=>writeNativeGSRegister(transfer,0x53,0n),/traversal/);
writeNativeGSRegister(transfer,0x51,0n);writeNativeGSRegister(transfer,0x52,0n);assert.throws(()=>writeNativeGSRegister(transfer,0x53,0n),/extent/);
writeNativeGSRegister(transfer,0x52,1n|1n<<32n);writeNativeGSRegister(transfer,0x53,0n);
assert.throws(()=>uploadNativeGSImage(transfer,new Uint8Array(32)),/exceeds/);
assert.throws(()=>uploadNativeGSImage(transfer,new Uint8Array(1)),/payload/);
for(const mode of [2,3,4,5,6,7]) {
  const cache=createNativeGSVRAM(new Uint8Array(4*1024*1024));cache.bytes.fill(19,0x3000*256,0x3000*256+1024);
  const word=(BigInt(u.tex0)&~(7n<<61n))|BigInt(mode)<<61n;
  writeNativeGSRegister(cache,6,word);
  assert.equal(cache.clut[0],mode>=6?0:19,'original CLD '+mode+' reset predicate');
  if(mode<6){cache.bytes.fill(27,0x3000*256,0x3000*256+1024);writeNativeGSRegister(cache,6,word);assert.equal(cache.clut[0],mode<4?27:19,'original CLD '+mode+' repeated CBP predicate');}
}
console.log('PASS source-derived CLD conditional loads and malformed transfer controls');
