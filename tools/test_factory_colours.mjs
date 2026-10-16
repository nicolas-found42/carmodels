import assert from 'node:assert/strict';
import fs from 'node:fs';
import zlib from 'node:zlib';
import * as THREE from '../dealership/vendor/three.module.js';
import {readGLB} from '../dealership/model-load.mjs';
import {loadCar,disposeCar} from '../dealership/dealership.mjs';

// MC3's alpha shader needs real decoded pixels, including during preset changes.
// These producer PNGs use RGBA8 and filter0; unrelated games retain their stubs.
function mc3Texture(bytes) {
  const buf=Buffer.from(bytes);
  assert.deepEqual([...buf.subarray(0,8)],[137,80,78,71,13,10,26,10]);
  let offset=8,width,height;const idat=[];
  while(offset<buf.length) {
    const size=buf.readUInt32BE(offset),kind=buf.toString('latin1',offset+4,offset+8),body=buf.subarray(offset+8,offset+8+size);
    if(kind==='IHDR'){width=body.readUInt32BE(0);height=body.readUInt32BE(4);assert.deepEqual([...body.subarray(8,13)],[8,6,0,0,0]);}
    if(kind==='IDAT')idat.push(body);
    offset+=12+size;
  }
  const raw=zlib.inflateSync(Buffer.concat(idat)),stride=width*4,pixels=new Uint8Array(stride*height);
  assert.equal(raw.length,height*(stride+1));
  for(let y=0;y<height;y++){assert.equal(raw[y*(stride+1)],0);pixels.set(raw.subarray(y*(stride+1)+1,(y+1)*(stride+1)),y*stride);}
  const texture=new THREE.DataTexture(pixels,width,height,THREE.RGBAFormat);
  texture.colorSpace=THREE.SRGBColorSpace;texture.flipY=false;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.needsUpdate=true;
  return texture;
}

const cars=JSON.parse(fs.readFileSync(new URL('../dealership/public/dealership/cars.json',import.meta.url)));
const totals=new Map();
for(const car of cars) {
  const game=car.game??'ford-racing-2';
  const total=totals.get(game)??{cars:0,variants:0};totals.set(game,total);total.cars++;
  if(car.model.schema===3)continue;
  const bytes=fs.readFileSync(new URL('../dealership/'+car.model.source.glb,import.meta.url));
  const buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
  const {doc}=readGLB(buffer),variants=doc.extensions?.KHR_materials_variants?.variants??[];
  if(!variants.length && game!=='ford-racing-2')continue;
  total.variants+=variants.length;
  const textures=[];
  const model=await loadCar(car,{fetchImpl:async()=>buffer,textureImpl:async image=>{
    const texture=game==='midnight-club-3-remix'?mc3Texture(image):new THREE.Texture();textures.push(texture);return texture;
  }});
  try {
    assert.deepEqual(model.userData.colourVariants?.map(v=>v.name)??[],variants.map(v=>v.name),
      `${car.code}: working GLB variants must reach the dealership selector`);
    const primitives=[];
    function visit(index) {
      const node=doc.nodes[index];
      if(game==='ford-racing-2' && node.extras?.sourceNames?.includes('HELMET'))return;
      for(const p of node.mesh===undefined?[]:doc.meshes[node.mesh].primitives) {
        if(game==='ford-racing-2' && doc.materials[p.material].name==='UNDER_SHADOW')continue;
        primitives.push(p);
      }
      for(const child of node.children??[])visit(child);
    }
    for(const index of doc.scenes[doc.scene??0].nodes)visit(index);
    const meshes=[];model.traverse(node=>{if(node.isMesh)meshes.push(node);});
    assert.equal(meshes.length,primitives.length,`${car.code}: visible default assembly`);
    assert.equal(meshes.reduce((n,m)=>n+m.geometry.index.count/3,0),car.model.triangleCount,
      `${car.code}: factory materials retain the compiled visible geometry`);
    const geometry=meshes.map(m=>m.geometry);
    for(const index of [null,...variants.map((_,i)=>i),null]) {
      model.userData.setColourVariant(index);
      for(let i=0;i<meshes.length;i++) {
        const p=primitives[i],mapping=p.extensions?.KHR_materials_variants?.mappings?.find(m=>m.variants.includes(index));
        const material=doc.materials[index===null?p.material:mapping?.material??p.material];
        const pbr=material.pbrMetallicRoughness??{};
        assert.equal(meshes[i].material.map,pbr.baseColorTexture?textures[doc.textures[pbr.baseColorTexture.index].source]:null,
          `${car.code}: variant ${index}, primitive ${i} texture binding`);
        assert.deepEqual(meshes[i].material.color.toArray(),(pbr.baseColorFactor??[1,1,1,1]).slice(0,3),
          `${car.code}: variant ${index}, primitive ${i} paint factor`);
        assert.equal(meshes[i].geometry,geometry[i],`${car.code}: switching paint keeps geometry`);
        if(game==='midnight-club-3-remix' && material.extras?.shader_template==='tire') {
          assert(meshes[i].geometry.attributes.mc3NativeNormal,`${car.code}: native tire normal reaches preset renderer`);
          const shader={uniforms:{},vertexShader:THREE.ShaderLib.standard.vertexShader,fragmentShader:THREE.ShaderLib.standard.fragmentShader};
          meshes[i].material.onBeforeCompile(shader);
          assert(shader.uniforms.mc3NativeAlpha,`${car.code}: preset retains native reflection shader`);
          const alpha=shader.uniforms.mc3NativeAlpha.value.image.data,image=meshes[i].material.map.image.data;
          for(let pixel=0;pixel<image.length;pixel+=4)assert.equal(alpha[pixel],Math.floor((image[pixel+3]+1)/2));
        }
      }
    }
  } finally {disposeCar(model);}
}
console.log('PASS factory colour transfer: '+JSON.stringify(Object.fromEntries(totals)));
