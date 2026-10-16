import {readGLB} from './model-load.mjs';

function need(value,message){if(!value)throw Error(message);}
const digestPattern=/^[0-9a-f]{64}$/;
const integer=value=>Number.isSafeInteger(value)&&value>=0;
const pathKey=path=>JSON.stringify(path);
const sameReference=(a,b)=>['name','kind','source_offset','slot_offset','hash'].every(key=>a?.[key]===b?.[key]);
const attached=new WeakMap();
export function bindNativeVehicleResources(object,resources) {
 need(object&&typeof object==='object'&&resources?.materials&&resources?.textures instanceof Map,'Invalid native resource attachment.');
 attached.set(object,resources);
}
export function nativeVehicleResources(object) {
 for(let node=object;node;node=node.parent)if(attached.has(node))return attached.get(node);
 return null;
}

// Native texture bytes are separate from display PNGs: alpha must never be
// reconstructed from the saturated preview. Hash every retained payload,
// including currently undecoded profiles, before exposing any resource.
export async function loadNativeVehicleResources(buffer) {
 const {doc,bin}=readGLB(buffer),extras=doc.extras;
 need(extras?.source_profile==='mc3-ps2-static-preview-v1'
  && extras.nativeVertexInputs==='mc3-vif-vertex-inputs-v1','Missing native MC3 vehicle source inputs.');
 need(Array.isArray(extras.nativeTextures)&&extras.nativeMaterialInputs,'Missing native MC3 resources.');
 const payloads=new Map(),textures=new Map(),materials=[],packets=new Map();
 async function payload(descriptor) {
  need(integer(descriptor.bufferView)&&integer(descriptor.bytes)&&descriptor.bytes>0
   && digestPattern.test(descriptor.sha256),'Invalid native payload descriptor.');
  const view=doc.bufferViews?.[descriptor.bufferView],offset=view?.byteOffset??0;
  need(view?.buffer===0&&integer(offset)&&view.byteLength===descriptor.bytes
   && offset+descriptor.bytes<=bin.byteLength,'Native payload exceeds GLB buffer.');
  const key=descriptor.bufferView+':'+descriptor.sha256;
  if(!payloads.has(key)) {
   const bytes=new Uint8Array(bin,offset,descriptor.bytes).slice();
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
   need(hash===descriptor.sha256,'Native resource payload hash mismatch.');payloads.set(key,bytes);
  }
  return payloads.get(key);
 }
 async function verifyPayloads(value) {
  if(!value||typeof value!=='object')return;
  if(Object.hasOwn(value,'bufferView')){await payload(value);return;}
  for(const child of Object.values(value))await verifyPayloads(child);
 }
 for(const source of extras.nativeTextures) {
  need(typeof source.key==='string'&&source.key.length&&!textures.has(source.key)
   && typeof source.name==='string'&&source.native,'Invalid native texture identity.');
  const undecoded=source.native.decode_status==='unresolved-native-format';
  need(undecoded&&source.width===null&&source.height===null
   ||integer(source.width)&&source.width>0&&integer(source.height)&&source.height>0,'Invalid native texture dimensions.');
  await verifyPayloads(source.native);
  const levels=[];
  for(const level of source.native.levels??[]) {
   need(integer(level.width)&&level.width>0&&integer(level.height)&&level.height>0,'Invalid native texture level.');
   if(!level.rgba)continue;
   need(level.rgba.bytes===level.width*level.height*4,'Native RGBA level extent mismatch.');
   levels.push({width:level.width,height:level.height,data:await payload(level.rgba)});
  }
  if(levels.length)need(levels[0].width===source.width&&levels[0].height===source.height,'Native texture base level differs.');
  textures.set(source.key,{source,levels,status:levels.length?'decoded':'retained-undecoded'});
 }
 for(const definition of doc.materials??[]) {
  const source=definition.extras,graph=source?.native_material,table=extras.nativeMaterialInputs[source?.native_input_key];
  need(graph?.schema===1&&digestPattern.test(graph.source_carrier_sha256)&&graph.root
   && table?.schema===1&&table.source_carrier_sha256===graph.source_carrier_sha256
   && source.native_input_key===table.source_carrier_sha256+':'+table.collection_offset
   && integer(table.collection_offset)&&Array.isArray(table.inputs),'Invalid native material input identity.');
  for(const [index,row] of table.inputs.entries())need(row.index===index&&typeof row.name==='string'
   && integer(row.word)&&row.word<=0xffffffff,'Invalid ordered native material inputs.');
  const bindings=new Map();
  need(Array.isArray(source.native_texture_bindings),'Missing native texture bindings.');
  for(const binding of source.native_texture_bindings) {
   need(Array.isArray(binding.graph_path)&&binding.graph_path.length>0,'Invalid native texture graph path.');
   let reference=graph;
   for(const key of binding.graph_path) {
    need((typeof key==='string'||integer(key))&&reference&&Object.hasOwn(reference,key),'Native texture graph path does not exist.');
    reference=reference[key];
   }
   const key=pathKey(binding.graph_path);
   need(!bindings.has(key)&&sameReference(binding.reference,reference),'Native texture binding identity differs.');
   if(binding.status==='resolved')need(textures.has(binding.texture_key),'Missing resolved native texture.');
   else need(['runtime-unresolved','native-sentinel','retained-undecoded','unresolved'].includes(binding.status),'Unknown native texture binding status.');
   if(binding.status==='retained-undecoded')need(textures.has(binding.texture_key),'Missing retained native texture.');
   bindings.set(key,binding);
  }
  function verifyBindings(value,path=[]) {
   if(!value||typeof value!=='object')return;
   if(['hash','slot','inline-slot'].includes(value.kind)&&Object.hasOwn(value,'name')) {
    need(bindings.has(pathKey(path)),'Native graph texture has no binding.');return;
   }
   if(Array.isArray(value))value.forEach((child,index)=>verifyBindings(child,[...path,index]));
   else for(const [key,child] of Object.entries(value))verifyBindings(child,[...path,key]);
  }
  verifyBindings(graph);
  materials.push({graph,table,bindings});
 }
 for(const [meshIndex,mesh] of (doc.meshes??[]).entries())for(const [primitiveIndex,primitive] of mesh.primitives.entries()) {
  const source=primitive.extras?.native_vif;
  if(!source){need(extras.nativeVifPackets!=='mc3-original-vif-packets-v1','Missing original native VIF packet.');continue;}
  // An attachment may inherit a material from the vehicle PCK while its
  // geometry lives in a separate PPF. Join geometry provenance independently.
  const nodes=(doc.nodes??[]).filter(node=>node.mesh===meshIndex);
  const records=nodes.flatMap(node=>(extras.records??[]).filter(record=>
   record.role===node.name&&record.bone===node.extras?.nativeBone));
  records.push(...(extras.nativeEffects??[]).filter(effect=>effect.mesh===meshIndex).map(effect=>effect.record));
  need(extras.nativeVifPackets==='mc3-original-vif-packets-v1'&&digestPattern.test(source.source_carrier_sha256)
   &&records.length>0&&records.every(record=>record?.native_sha256===source.source_carrier_sha256)
   &&integer(source.source_packet_offset)&&Array.isArray(source.batch_offsets)&&source.batch_offsets.length>0
   &&source.batch_offsets.length===primitive.extras.native_batches?.length,'Invalid native VIF source identity.');
  const bytes=await payload(source.packet);
  need(bytes.length%16===0&&source.batch_offsets.every(offset=>integer(offset)&&offset<bytes.length),'Invalid native VIF packet extent.');
  packets.set(meshIndex+':'+primitiveIndex,{source,data:bytes});
 }
 return {doc,textures,materials,payloads,packets,
  resolveTexture(materialIndex,path,runtimeTextures=new Map()) {
   const material=materials[materialIndex];need(material,'Invalid native material index.');
   const binding=material.bindings.get(pathKey(path));need(binding,'Missing native texture graph binding.');
   if(binding.status==='native-sentinel')return {status:'native-sentinel',reference:binding.reference};
   if(binding.status==='unresolved')return {status:'unresolved',reference:binding.reference,reason:binding.reason};
   if(binding.status==='runtime-unresolved') {
    const image=runtimeTextures.get(binding.reference.name);
    if(!image)return {status:'runtime-unresolved',reference:binding.reference};
    need(integer(image.width)&&image.width>0&&integer(image.height)&&image.height>0
     && image.data instanceof Uint8Array&&image.data.length===image.width*image.height*4,'Invalid native runtime texture.');
    return {status:'decoded',levels:[image],reference:binding.reference};
   }
   return textures.get(binding.texture_key);
  }};
}
