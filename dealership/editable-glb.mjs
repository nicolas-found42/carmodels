import * as THREE from './vendor/three.module.js';
import {fetchModel, readGLB} from './model-load.mjs';
import {createMaterial} from './materials.mjs';

// Decode only embedded, static triangle GLBs. Bounds and accessor extents are
// checked before allocating meshes; texture failures dispose all prior resources.
export function parseEditableGLB(buffer) {
  const {doc, bin} = readGLB(buffer);
  if (doc.animations?.length || doc.skins?.length || doc.extensionsRequired?.length ||
      doc.buffers?.length !== 1 || doc.buffers[0].uri || !Array.isArray(doc.nodes) ||
      !doc.scenes?.[doc.scene ?? 0] || doc.nodes.length > 10000) throw Error('Unsupported editable static GLB.');
  function view(index) {
    const v=doc.bufferViews?.[index];
    if(!v || v.buffer!==0 || !Number.isInteger(v.byteLength) || v.byteLength<=0 ||
       !Number.isInteger(v.byteOffset??0) || (v.byteOffset??0)<0 || (v.byteOffset??0)+v.byteLength>bin.byteLength) throw Error('Invalid embedded GLB buffer view.');
    return v;
  }
  function values(index, width, integer=false) {
    const a=doc.accessors?.[index], Type={5121:Uint8Array,5123:Uint16Array,5125:Uint32Array,5126:Float32Array}[a?.componentType];
    if(!a || !Type || a.type!=={1:'SCALAR',2:'VEC2',3:'VEC3',4:'VEC4'}[width] || a.sparse || a.normalized ||
       !Number.isInteger(a.count) || a.count<=0 || a.count>1000000 || (integer ? a.componentType===5126 : a.componentType!==5126)) throw Error('Invalid GLB accessor.');
    const v=view(a.bufferView), step=width*Type.BYTES_PER_ELEMENT, stride=v.byteStride??step, offset=a.byteOffset??0;
    if(!Number.isInteger(offset) || offset<0 || !Number.isInteger(stride) || stride<step || offset+(a.count-1)*stride+step>v.byteLength) throw Error('GLB accessor exceeds buffer.');
    const data=new DataView(bin), out=new Type(a.count*width), method={5121:'getUint8',5123:'getUint16',5125:'getUint32',5126:'getFloat32'}[a.componentType];
    for(let i=0;i<a.count;i++)for(let j=0;j<width;j++) {
      const value=data[method]((v.byteOffset??0)+offset+i*stride+j*Type.BYTES_PER_ELEMENT,true);
      if(!Number.isFinite(value)) throw Error('Non-finite GLB attribute.');
      out[i*width+j]=value;
    }
    return out;
  }
  const images=(doc.images??[]).map(image=>{
    if(image.uri || image.mimeType!=='image/png')throw Error('Editable textures must be embedded PNG.');
    const v=view(image.bufferView);return new Uint8Array(bin,v.byteOffset??0,v.byteLength);
  });
  const meshes=(doc.meshes??[]).map(mesh=>mesh.primitives.map(p=>{
    if((p.mode??4)!==4 || p.extensions)throw Error('Editable mesh must use static triangles.');
    const positions=values(p.attributes?.POSITION,3), normals=values(p.attributes?.NORMAL,3), indices=values(p.indices,1,true);
    const uv=p.attributes.TEXCOORD_0===undefined?null:values(p.attributes.TEXCOORD_0,2);
    const colorWidth=doc.accessors?.[p.attributes.COLOR_0]?.type==='VEC4'?4:3;
    const colors=p.attributes.COLOR_0===undefined?null:values(p.attributes.COLOR_0,colorWidth);
    if(normals.length!==positions.length || uv && uv.length!==positions.length/3*2 || indices.length%3 ||
       indices.some(i=>i>=positions.length/3))throw Error('GLB mesh attribute/index mismatch.');
    if(colors && (colors.length!==positions.length/3*colorWidth || colors.some(v=>v<0 || v>1)))throw Error('Invalid GLB vertex colours.');
    for(let i=0;i<normals.length;i+=3)if(Math.hypot(...normals.subarray(i,i+3))<1e-8)throw Error('GLB normal is zero.');
    const material=doc.materials?.[p.material];
    if(!material)throw Error('Missing GLB material.');
    const texture=material.pbrMetallicRoughness?.baseColorTexture;
    if(texture && (!uv || !doc.textures?.[texture.index] || !images[doc.textures[texture.index].source]))throw Error('Invalid GLB texture mapping.');
    return {positions,normals,indices,uv,colors,colorWidth,material:p.material};
  }));
  const seen=new Set(), active=new Set();
  function walk(index) {
    if(!Number.isInteger(index) || !doc.nodes[index] || active.has(index) || seen.has(index))throw Error('Invalid or cyclic GLB scene.');
    active.add(index);seen.add(index);const node=doc.nodes[index];
    if(node.skin!==undefined || node.mesh!==undefined&&!meshes[node.mesh])throw Error('Invalid GLB scene mesh.');
    for(const [key,width] of [['translation',3],['scale',3],['rotation',4],['matrix',16]])if(node[key]!==undefined &&
      (!Array.isArray(node[key]) || node[key].length!==width || !node[key].every(Number.isFinite)))throw Error('Invalid GLB transform.');
    if(node.matrix && (node.matrix[3]!==0 || node.matrix[7]!==0 || node.matrix[11]!==0 || node.matrix[15]!==1))throw Error('Invalid GLB affine matrix.');
    if(node.rotation && Math.abs(node.rotation.reduce((s,v)=>s+v*v,0)-1)>1e-5)throw Error('Invalid GLB quaternion.');
    if(node.scale?.some(v=>Math.abs(v)<1e-12))throw Error('Singular GLB transform.');
    for(const child of node.children??[])walk(child);active.delete(index);
  }
  for(const node of doc.scenes[doc.scene??0].nodes??[])walk(node);
  if(!seen.size || ![...seen].some(i=>doc.nodes[i].mesh!==undefined))throw Error('Editable scene has no geometry.');
  return {doc,images,meshes};
}

async function loadTexture(bytes, signal) {
  const url=URL.createObjectURL(new Blob([bytes],{type:'image/png'}));
  let image;
  try {
    image=new Image();
    await new Promise((resolve,reject)=>{
      const finish=(error)=>{clearTimeout(timer);signal?.removeEventListener('abort',cancel);image.onload=image.onerror=null;error?reject(error):resolve();};
      const cancel=()=>{image.src='';finish(Error('Model selection cancelled.'));};
      const timer=setTimeout(()=>{image.src='';finish(Error('Embedded texture decode timed out.'));},15000);
      image.onload=()=>finish();image.onerror=()=>finish(Error('Embedded texture failed to decode.'));
      signal?.addEventListener('abort',cancel,{once:true});
      if(signal?.aborted)cancel();else image.src=url;
    });
    const texture=new THREE.Texture(image);texture.colorSpace=THREE.SRGBColorSpace;texture.flipY=false;
    texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.needsUpdate=true;return texture;
  } finally {URL.revokeObjectURL(url);}
}

export async function loadEditableGLB(car, {signal,fetchImpl=fetchModel,textureImpl=loadTexture}={}) {
  const buffer=await fetchImpl('./'+car.model.source.glb,signal);
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),v=>v.toString(16).padStart(2,'0')).join('');
  if(hash!==car.model.source.sha256)throw Error('Editable model changed; rebuild the dealership data.');
  const {doc,images,meshes}=parseEditableGLB(buffer), textures=[], group=new THREE.Group();
  group.userData.textures=textures;group.userData.wheels=[];group.userData.source=car.model.source;
  try {
    for(const image of images)textures.push(await textureImpl(image,signal));
    if(signal?.aborted)throw Error('Model selection cancelled.');
    function node(index) {
      const source=doc.nodes[index], g=new THREE.Group();
      if(source.matrix){g.matrix.fromArray(source.matrix);g.matrixAutoUpdate=false;}
      else {g.position.fromArray(source.translation??[0,0,0]);g.quaternion.fromArray(source.rotation??[0,0,0,1]);g.scale.fromArray(source.scale??[1,1,1]);}
      for(const p of source.mesh===undefined?[]:meshes[source.mesh]) {
        const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(p.positions,3));geometry.setAttribute('normal',new THREE.BufferAttribute(p.normals,3));
        if(p.uv)geometry.setAttribute('uv',new THREE.BufferAttribute(p.uv,2));geometry.setIndex(new THREE.BufferAttribute(p.indices,1));
        if(p.colors)geometry.setAttribute('color',new THREE.BufferAttribute(p.colors,p.colorWidth));
        const material=createMaterial(doc,textures,p.material), definition=doc.materials[p.material];
        material.vertexColors=!!p.colors;
        material.alphaTest=definition.alphaMode==='MASK'?(definition.alphaCutoff??0.5):0;
        const mesh=new THREE.Mesh(geometry,material);mesh.castShadow=mesh.receiveShadow=true;g.add(mesh);
      }
      for(const child of source.children??[])g.add(node(child));return g;
    }
    for(const root of doc.scenes[doc.scene??0].nodes)group.add(node(root));
    const bounds=new THREE.Box3().setFromObject(group);
    if(bounds.isEmpty())throw Error('Editable scene has no visible geometry.');
    group.position.set(-(bounds.min.x+bounds.max.x)/2,-bounds.min.y,-(bounds.min.z+bounds.max.z)/2);
    return group;
  } catch(error) {
    group.traverse(n=>{n.geometry?.dispose();for(const material of [n.material??[]].flat())material.dispose();});
    textures.forEach(t=>t.dispose());throw error;
  }
}
