// Native values and bindings come from source-backed exporter metadata. Missing
// channels stay missing: material names or differences between variants are not masks.
function text(value) {return typeof value==='string' && value.trim() && value.length<=2000;}
function unit(value) {return Number.isFinite(value) && value>=0 && value<=1;}
function identifier(value) {return typeof value==='string' && /^[a-z0-9][a-z0-9_-]{0,80}$/i.test(value);}
export function colourId(colour) {return JSON.stringify([colour.source,colour.id]);}
function checkColour(colour) {
  if(!colour || !text(colour.id) || !text(colour.name) || !text(colour.source) ||
     !Array.isArray(colour.rgb) || colour.rgb.length!==3 || !colour.rgb.every(unit))throw Error('Invalid recovered paint colour.');
  return {...colour,rgb:[...colour.rgb],key:colourId(colour)};
}

export function readGamePaint(doc) {
  const data=doc.extras?.gamePaint;
  if(data===undefined)return {channels:[],colors:[],limits:['Paint channels and transferable game colours have not been recovered for this model.']};
  if(!data || data.schema!==1 || !Array.isArray(data.channels) || !Array.isArray(data.colors) ||
     !Array.isArray(data.limits??[]) || (data.limits??[]).some(value=>!text(value)))throw Error('Invalid recovered paint metadata.');
  const ids=new Set(),materials=new Set();
  const channels=data.channels.map(channel=>{
    if(!channel || !identifier(channel.id) || ids.has(channel.id) || !text(channel.name) ||
       !Array.isArray(channel.materials) || !channel.materials.length)throw Error('Invalid recovered paint channel.');
    ids.add(channel.id);
    for(const index of channel.materials) {
      if(!Number.isInteger(index) || index<0 || !doc.materials?.[index] || materials.has(index))throw Error('Invalid or overlapping paint material binding.');
      materials.add(index);
    }
    const finishes=channel.finishes??[],finishIds=new Set();
    if(!Array.isArray(finishes))throw Error('Invalid recovered paint finishes.');
    for(const finish of finishes) {
      if(!finish || !identifier(finish.id) || finishIds.has(finish.id) || !text(finish.name) || !text(finish.source) ||
         !unit(finish.roughness) || !unit(finish.metalness))throw Error('Invalid recovered paint finish.');
      finishIds.add(finish.id);
    }
    return {...channel,materials:[...channel.materials],finishes:finishes.map(finish=>({...finish}))};
  });
  return {channels,colors:data.colors.map(checkColour),limits:[...(data.limits??[])]};
}

export function createPaintSession(doc,{game,colors=[]}={}) {
  const native=readGamePaint(doc),byColour=new Map();
  // The caller selects exactly one game's palette. Foreign entries are never used.
  for(const value of [...native.colors,...colors.filter(value=>value.game===game)]) {
    const colour=checkColour(value),existing=byColour.get(colour.key);
    if(existing && JSON.stringify(existing.rgb)!==JSON.stringify(colour.rgb))throw Error('Conflicting native paint identity.');
    byColour.set(colour.key,colour);
  }
  const presets=(doc.extensions?.KHR_materials_variants?.variants??[]).map((preset,index)=>{
    const swatch=preset.extras?.nativeConfigColor,rgb=preset.extras?.nativeRGB;
    const sample=Array.isArray(rgb)&&rgb.length===3&&rgb.every(unit)?{rgb:[...rgb]}:
      Array.isArray(swatch)&&swatch.length===3&&swatch.every(unit)?{swatch:[...swatch]}:{};
    return {index,name:preset.name,...sample};
  });
  let preset=null,overrides={};
  function setPreset(index=null) {
    if(index!==null && (!Number.isInteger(index)||!presets[index]))throw Error('Invalid paint preset.');
    preset=index;
  }
  function channelFor(id) {
    const channel=native.channels.find(value=>value.id===id);
    if(!channel)throw Error('Unrecovered paint channel.');
    return channel;
  }
  function setChannel(id,colour=null) {
    channelFor(id);
    if(colour!==null && !byColour.has(colour))throw Error('Colour is not in this game palette.');
    overrides[id]={...overrides[id],color:colour};
  }
  function setFinish(id,finish=null) {
    const channel=channelFor(id);
    if(finish!==null && !channel.finishes.some(value=>value.id===finish))throw Error('Unrecovered paint finish.');
    overrides[id]={...overrides[id],finish};
  }
  function material(primitive) {
    const mappings=primitive.extensions?.KHR_materials_variants?.mappings??[];
    const index=preset===null?primitive.material:mappings.find(value=>value.variants.includes(preset))?.material??primitive.material;
    const original=doc.materials[index];
    if(!original)throw Error('Missing selected paint material.');
    // A preset may share one material across separate surfaces. Only the
    // primitive's recovered base binding establishes its paint channel.
    const channel=native.channels.find(value=>value.materials.includes(primitive.material));
    const override=channel && overrides[channel.id],colour=override?.color && byColour.get(override.color);
    const finish=override?.finish && channel.finishes.find(value=>value.id===override.finish);
    if(!colour && !finish)return {index,definition:original,changed:false,channelId:channel?.id};
    const definition={...original,pbrMetallicRoughness:{...original.pbrMetallicRoughness}};
    if(colour)definition.pbrMetallicRoughness.baseColorFactor=[...colour.rgb,original.pbrMetallicRoughness?.baseColorFactor?.[3]??1];
    if(finish)Object.assign(definition.pbrMetallicRoughness,{roughnessFactor:finish.roughness,metallicFactor:finish.metalness});
    return {index,definition,changed:true,channelId:channel?.id};
  }
  function reset(){preset=null;overrides={};}
  function selection(){return {schema:1,preset,channels:structuredClone(overrides)};}
  function restore(value) {
    reset();
    if(!value || value.schema!==1)return;
    // Save the name alongside its index; asset upgrades must not select a different preset.
    if(Number.isInteger(value.preset) && presets[value.preset]?.name===value.presetName)setPreset(value.preset);
    for(const channel of native.channels) {
      const saved=value.channels?.[channel.id];
      if(!saved || typeof saved!=='object')continue;
      if(byColour.has(saved.color))setChannel(channel.id,saved.color);
      if(channel.finishes.some(finish=>finish.id===saved.finish))setFinish(channel.id,saved.finish);
    }
  }
  return {game,channels:native.channels,colors:[...byColour.values()],presets,limits:native.limits,
    setPreset,setChannel,setFinish,material,reset,restore,
    get state(){return {...selection(),presetName:preset===null?null:presets[preset].name};}};
}

export function applyPaintMaterial(applyMaterial,material,doc,textures,primitive,session,options={}) {
  const {definition}=session.material(primitive);
  applyMaterial(material,{...doc,materials:[definition]},textures,0,options);
}

export async function fetchGamePalette(fetchImpl=fetch) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetchImpl('./public/game-paints.json',{cache:'no-store',signal:controller.signal});
    if(!response.ok)throw Error('The game colour library is unavailable.');
    const data=await response.json();
    if(data.schema!==1 || !Array.isArray(data.colors))throw Error('Invalid game colour library.');
    for(const colour of data.colors){checkColour(colour);if(!text(colour.game))throw Error('Missing paint game identity.');}
    return data.colors;
  } finally {clearTimeout(timer);}
}
