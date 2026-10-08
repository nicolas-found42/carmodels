// Bound network/body reads and cancel obsolete selections without extra dependencies.
export async function fetchModel(url, signal, timeoutMs=15000) {
 const controller=new AbortController();
 const cancel=()=>controller.abort();
 signal?.addEventListener('abort',cancel,{once:true});
 if(signal?.aborted)cancel();
 let timedOut=false;
 const timer=setTimeout(()=>{timedOut=true;controller.abort();},timeoutMs);
 try {
  const response=await fetch(url,{signal:controller.signal});
  if(!response.ok)throw Error(`Geometry file unavailable (HTTP ${response.status})`);
  return await response.arrayBuffer();
 } catch(error) {
  if(timedOut)throw Error('Request timed out; retry or choose another car');
  throw error;
 } finally {
  clearTimeout(timer);
  signal?.removeEventListener('abort',cancel);
 }
}

export function readGLB(buffer) {
 if(buffer.byteLength<20)throw Error('Truncated GLB header');
 const head=new DataView(buffer);
 if(head.getUint32(0,true)!==0x46546c67||head.getUint32(4,true)!==2||head.getUint32(8,true)!==buffer.byteLength)throw Error('Invalid GLB header');
 let cursor=12,doc,bin;
 while(cursor<buffer.byteLength) {
  if(cursor+8>buffer.byteLength)throw Error('Truncated GLB chunk header');
  const size=head.getUint32(cursor,true),kind=head.getUint32(cursor+4,true);
  if(size%4!==0||cursor+8+size>buffer.byteLength)throw Error('Truncated or unaligned GLB chunk');
  if(kind===0x4e4f534a)doc=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,cursor+8,size)));
  if(kind===0x004e4942)bin=buffer.slice(cursor+8,cursor+8+size);
  cursor+=8+size;
 }
 if(!doc||!bin)throw Error('Missing GLB chunks');
 return {doc,bin};
}
