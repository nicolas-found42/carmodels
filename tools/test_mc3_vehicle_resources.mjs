import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {loadNativeVehicleResources,bindNativeVehicleResources,nativeVehicleResources} from '../dealership/mc3-vehicle-resources.mjs';

const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
const data=new Uint8Array([0,17,255,128,80,20,10,64]);
const descriptor={bufferView:0,bytes:data.length,sha256:await hash(data)};
const identity='a'.repeat(64),key=identity+':16';
const reference=name=>({name,kind:'hash',source_offset:32,slot_offset:null,hash:42});
const references=['diffuse','__specular__','none','undecoded','missing'].map(reference);
const statuses=['resolved','runtime-unresolved','native-sentinel','retained-undecoded','unresolved'];
const doc={asset:{version:'2.0'},buffers:[{byteLength:data.length}],bufferViews:[{buffer:0,byteOffset:0,byteLength:data.length}],
 materials:[{extras:{native_material:{schema:1,source_carrier_sha256:identity,root:{kind:'material',passes:[{textures:references}]}},
  native_input_key:key,native_texture_bindings:references.map((ref,i)=>({graph_path:['root','passes',0,'textures',i],reference:ref,status:statuses[i],
   ...(i===0?{texture_key:'diffuse'}:i===3?{texture_key:'unknown'}:{})}))}}],
 extras:{source_profile:'mc3-ps2-static-preview-v1',nativeVertexInputs:'mc3-vif-vertex-inputs-v1',
  nativeMaterialInputs:{[key]:{schema:1,source_carrier_sha256:identity,collection_offset:16,inputs:[{index:0,name:'source',word:0x80000000}]}},
  nativeTextures:[{key:'diffuse',name:'diffuse',width:2,height:1,native:{levels:[{width:2,height:1,rgba:descriptor}],source_palette:descriptor}},
   {key:'unknown',name:'unknown',width:null,height:null,native:{decode_status:'unresolved-native-format',source_block:descriptor}}]}};
function glb(document=doc,bytes=data) {
 const json=Buffer.from(JSON.stringify(document)),padded=Buffer.alloc((json.length+3)&~3,32);json.copy(padded);
 const result=new ArrayBuffer(28+padded.length+bytes.length),view=new DataView(result),out=new Uint8Array(result);
 [0x46546c67,2,result.byteLength,padded.length,0x4e4f534a].forEach((n,i)=>view.setUint32(i*4,n,true));
 out.set(padded,20);view.setUint32(20+padded.length,bytes.length,true);view.setUint32(24+padded.length,0x004e4942,true);out.set(bytes,28+padded.length);return result;
}
const resources=await loadNativeVehicleResources(glb()),path=index=>['root','passes',0,'textures',index];
const root={},child={parent:root};bindNativeVehicleResources(root,resources);
assert.equal(nativeVehicleResources(child),resources);
assert.equal(nativeVehicleResources({}),null);
assert.equal(JSON.stringify(root),'{}','native buffers do not enter editable scene serialization');
assert.deepEqual(resources.resolveTexture(0,path(0)).levels[0].data,data);
assert.equal(resources.resolveTexture(0,path(0)).levels[0].data[3],128,'native alpha is not saturated PNG alpha');
assert.equal(resources.payloads.size,1,'identical payload descriptors share validated bytes');
assert.equal(resources.resolveTexture(0,path(1)).status,'runtime-unresolved');
const runtime=new Map([['__specular__',{width:2,height:1,data}]]);
assert.deepEqual(resources.resolveTexture(0,path(1),runtime).levels[0].data,data);
assert.equal(resources.resolveTexture(0,path(2)).status,'native-sentinel');
assert.equal(resources.resolveTexture(0,path(3)).status,'retained-undecoded');
assert.equal(resources.resolveTexture(0,path(4)).status,'unresolved');
assert.throws(()=>resources.resolveTexture(0,path(1),new Map([['__specular__',{width:2,height:1,data:data.slice(1)}]])),/runtime texture/);
const reject=async (mutate,reason)=>{const changed=structuredClone(doc);mutate(changed);await assert.rejects(()=>loadNativeVehicleResources(glb(changed)),reason);};
await reject(d=>d.bufferViews[0].byteOffset=4,/exceeds/);
await reject(d=>d.extras.nativeTextures[0].native.levels[0].rgba.sha256='b'.repeat(64),/hash mismatch/);
await reject(d=>d.extras.nativeTextures[0].native.levels[0].width=1,/extent/);
await reject(d=>d.extras.nativeTextures.push(d.extras.nativeTextures[0]),/identity/);
await reject(d=>d.materials[0].extras.native_texture_bindings[0].texture_key='absent',/resolved native texture/);
await reject(d=>d.materials[0].extras.native_texture_bindings[0].graph_path[4]=9,/does not exist/);
await reject(d=>d.materials[0].extras.native_texture_bindings[0].reference={...d.materials[0].extras.native_texture_bindings[0].reference,name:'different'},/identity differs/);
await reject(d=>d.materials[0].extras.native_texture_bindings.pop(),/has no binding/);
await reject(d=>d.extras.nativeMaterialInputs[key].source_carrier_sha256='b'.repeat(64),/input identity/);
await reject(d=>d.extras.nativeMaterialInputs[key].inputs[0].index=1,/ordered/);
await reject(d=>d.extras.nativeMaterialInputs[key].inputs[0].word=-1,/ordered/);
await reject(d=>delete d.extras.nativeVertexInputs,/source inputs/);
console.log('PASS native texture alpha, source identities, all binding statuses, runtime injection and 13 failure controls');

const vifBytes=new Uint8Array(16);vifBytes.set(data);
const vifDoc=structuredClone(doc);vifDoc.buffers[0].byteLength=16;
vifDoc.bufferViews.push({buffer:0,byteOffset:0,byteLength:16});
vifDoc.extras.nativeVifPackets='mc3-original-vif-packets-v1';
vifDoc.nodes=[{name:'original',mesh:0,extras:{nativeBone:2}}];
vifDoc.extras.records=[{role:'original',bone:2,native_sha256:identity}];
vifDoc.meshes=[{primitives:[{material:0,extras:{native_batches:[{}],native_vif:{
 source_carrier_sha256:identity,source_packet_offset:8192,batch_offsets:[0],
 packet:{bufferView:1,bytes:16,sha256:await hash(vifBytes)}}}}]}];
const withVif=await loadNativeVehicleResources(glb(vifDoc,vifBytes));
assert.deepEqual(withVif.packets.get('0:0').data,vifBytes);
assert.equal(withVif.packets.get('0:0').source.source_packet_offset,8192);
const attachment=structuredClone(vifDoc),geometryIdentity='c'.repeat(64);
attachment.extras.records[0].native_sha256=geometryIdentity;
attachment.meshes[0].primitives[0].extras.native_vif.source_carrier_sha256=geometryIdentity;
assert.equal((await loadNativeVehicleResources(glb(attachment,vifBytes))).packets.size,1,
 'attachment geometry may inherit a material from a different source carrier');
for(const [mutate,reason] of [
 [d=>delete d.meshes[0].primitives[0].extras.native_vif,/Missing original/],
 [d=>d.meshes[0].primitives[0].extras.native_vif.batch_offsets[0]=16,/extent/],
 [d=>d.meshes[0].primitives[0].extras.native_vif.source_carrier_sha256='b'.repeat(64),/identity/],
 [d=>d.extras.records[0].bone=3,/identity/],
 [d=>d.meshes[0].primitives[0].extras.native_vif.packet.sha256='b'.repeat(64),/hash mismatch/],
]) {const changed=structuredClone(vifDoc);mutate(changed);await assert.rejects(()=>loadNativeVehicleResources(glb(changed,vifBytes)),reason);}
console.log('PASS original VIF bytes, source carrier/offset and missing/corrupt/extent controls');

// Optional full candidate audit; production models are deliberately not
// upgraded as a side effect of this resource-loader check.
if(process.argv[2]) {
 let models=0,textures=0,materials=0,payloads=0;
 for(const name of readdirSync(process.argv[2]).filter(name=>name.endsWith('.glb'))) {
  const bytes=readFileSync(process.argv[2]+'/'+name),resource=await loadNativeVehicleResources(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
  models++;textures+=resource.textures.size;materials+=resource.materials.length;payloads+=resource.payloads.size;
 }
 console.log(JSON.stringify({models,textures,materials,payloads}));
}
