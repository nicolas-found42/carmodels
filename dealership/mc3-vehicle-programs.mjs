const SOURCE='1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d';
function need(value,message){if(!value)throw Error(message);}
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
export function nativeVehicleProgramsURL(moduleURL=import.meta.url) {
 return new URL('./public/midnight-club-3-remix/rendering/native-vehicle-programs.json',moduleURL).href;
}

// Registry IDs are executable-derived; a template name is never used as a
// substitute. Program zero also needs the caller's native builtin selector.
export async function decodeNativeVehiclePrograms(pack) {
 need(pack?.schema===1&&pack.source_executable_sha256===SOURCE&&Array.isArray(pack.programs)
  &&pack.programs.length===14,'Invalid native vehicle program pack.');
 const programs=new Map();
 for(const source of pack.programs) {
  need(Number.isInteger(source.index)&&source.index>=0&&source.index<=12
   &&typeof source.name==='string'&&Number.isInteger(source.instructions)&&source.instructions>0&&source.instructions<=2048
   &&/^[0-9a-f]{64}$/.test(source.microcode_sha256),'Invalid native vehicle program descriptor.');
  const key=source.index===0?'0:'+source.variant:String(source.index);
  need(!programs.has(key)&&(source.index!==0||['normal','alternate'].includes(source.variant)),'Duplicate or invalid native program binding.');
  need(typeof source.microcode_base64==='string'&&/^[A-Za-z0-9+/]*={0,2}$/.test(source.microcode_base64),'Invalid native microcode encoding.');
  const bytes=Uint8Array.from(atob(source.microcode_base64),c=>c.charCodeAt(0));
  need(bytes.byteLength===source.instructions*8&&await hash(bytes)===source.microcode_sha256,'Native microcode payload differs.');
  const code=new Uint32Array(4096),view=new DataView(bytes.buffer);
  for(let i=0;i<bytes.length/4;i++)code[i]=view.getUint32(i*4,true);
  programs.set(key,{source,code});
 }
 need(programs.has('0:normal')&&programs.has('0:alternate')&&Array.from({length:12},(_,i)=>String(i+1)).every(key=>programs.has(key)),'Incomplete native program registry.');
 return {sourceExecutable:SOURCE,program(index,builtinSelector) {
  need(Number.isInteger(index)&&index>=0&&index<=12,'Invalid native shader program index.');
  if(index===0)need(Number.isInteger(builtinSelector)&&builtinSelector>=0&&builtinSelector<=0xffffffff,'Native builtin selector is required.');
  const entry=programs.get(index===0?'0:'+(builtinSelector===0?'normal':'alternate'):String(index));
  return {source:entry.source,code:entry.code.slice()};
 }};
}
