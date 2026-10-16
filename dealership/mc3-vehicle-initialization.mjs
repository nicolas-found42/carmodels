const source='1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d';
const digest='4e5e3bbba00f103a9031c25a5caf20bb69aa67476df9645222d0d88b469b7be3';
const need=(ok,message)=>{if(!ok)throw Error(message);};
export async function decodeNativeVehicleInitialization(pack){
 need(pack?.schema===1&&pack.source_executable_sha256===source&&pack.vif_bytes===27144
  &&typeof pack.vif_base64==='string'&&/^[A-Za-z0-9+/]*={0,2}$/.test(pack.vif_base64)
  &&pack.vif_sha256===digest,'Invalid native VIF initialization pack.');
 const stream=Uint8Array.from(atob(pack.vif_base64),c=>c.charCodeAt(0));
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',stream)),n=>n.toString(16).padStart(2,'0')).join('');
 need(stream.length===pack.vif_bytes&&hash===pack.vif_sha256,'Native VIF initialization payload differs.');
 return stream;
}
