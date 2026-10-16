import {readGLB} from './model-load.mjs';

// Re-encode JSON only. Binary geometry, embedded images, scenes and variant
// mappings are retained; default material bindings carry the selected appearance.
export function exportPaintGLB(buffer,session) {
  const {doc}=readGLB(buffer),materials=new Map();
  const paintMaterials=new Set((doc.extras?.gamePaint?.channels??[]).flatMap(channel=>channel.materials));
  for(const mesh of doc.meshes??[])for(const primitive of mesh.primitives) {
    const chosen=session.material(primitive);
    const channel=doc.extras?.gamePaint?.channels?.find(value=>value.id===chosen.channelId);
    if(!chosen.changed && !channel && !paintMaterials.has(chosen.index))primitive.material=chosen.index;
    else {
      // Even an unchanged preset can share a target across two paint channels.
      // Keep channel defaults and unowned trim separate on reimport, retaining
      // original variant targets without inventing paint ownership.
      const key=JSON.stringify([channel?.id,chosen.index,chosen.definition]);
      if(!materials.has(key)) {materials.set(key,doc.materials.length);doc.materials.push(chosen.definition);}
      primitive.material=materials.get(key);
    }
    // Newly appended defaults remain part of their recovered channel after import.
    if(channel && !channel.materials.includes(primitive.material))channel.materials.push(primitive.material);
  }
  doc.extras={...doc.extras,gamePaintSelection:session.state};
  const json=new TextEncoder().encode(JSON.stringify(doc)),jsonLength=(json.length+3)&~3;
  const chunks=[],original=new DataView(buffer);let cursor=12,jsonChunks=0;
  while(cursor<buffer.byteLength) {
    const size=original.getUint32(cursor,true);
    if(original.getUint32(cursor+4,true)===0x4e4f534a)jsonChunks++;
    else chunks.push(new Uint8Array(buffer,cursor,size+8));
    cursor+=size+8;
  }
  if(jsonChunks!==1)throw Error('Paint export needs exactly one GLB JSON chunk.');
  const result=new ArrayBuffer(20+jsonLength+chunks.reduce((sum,chunk)=>sum+chunk.length,0)),view=new DataView(result),bytes=new Uint8Array(result);
  view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,result.byteLength,true);
  view.setUint32(12,jsonLength,true);view.setUint32(16,0x4e4f534a,true);
  bytes.fill(32,20,20+jsonLength);bytes.set(json,20);
  cursor=20+jsonLength;for(const chunk of chunks){bytes.set(chunk,cursor);cursor+=chunk.length;}
  return result;
}

export function createPaintDownload(link,{url=URL,BlobImpl=Blob}={}) {
  let objectURL=null;
  function clear(){if(objectURL!==null){url.revokeObjectURL(objectURL);if(link.href===objectURL)link.removeAttribute?.('href');}objectURL=null;}
  return {
    clear,
    update(buffer,session,filename) {
      const data=exportPaintGLB(buffer,session),next=url.createObjectURL(new BlobImpl([data],{type:'model/gltf-binary'}));
      clear();objectURL=next;link.href=next;link.download=filename;
      link.title='GLB with the selected paint as its default appearance; recovered variants and geometry are retained.';
    }
  };
}
