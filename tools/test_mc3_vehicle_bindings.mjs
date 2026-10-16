import assert from 'node:assert/strict';
import fs from 'node:fs';
import {bindNativeVehicleMaterial,nativeVehicleInputWords,nativeVehiclePassState,nativeWordFloat} from '../dealership/mc3-vehicle-bindings.mjs';
import {nativeFloatWords} from '../dealership/mc3-vehicle-math.mjs';
const base=new URL('../research/evidence/midnight-club-3-remix/previews/',import.meta.url);
const read=name=>JSON.parse(fs.readFileSync(new URL(name,base),'utf8'));
const fixtures=read('vehicle-material-fragments.json'),inputs=read('vehicle-inputs-fragments.json'),probes=read('vehicle-bindings-native.json');
function* descendants(node){yield node;for(const child of node.children??[])yield* descendants(child);}
const root=(name,kind='material')=>structuredClone(kind==='composite'?fixtures.roots.find(r=>r.template===name&&r.expected_root.kind===kind).expected_root:fixtures.roots.flatMap(r=>[...descendants(r.expected_root)]).find(n=>n.template===name+'.shadert'&&n.kind===kind));
const context=()=>({state:{0:2,1:1,3:0,7:1,8:0x80ffffff,9:15},ambient:[.2,.3,.4],generationParameters:[Math.fround(.8),Math.fround(.2),Math.fround(.8),1],paintControlWord:3,paintControlByte:1,paintLightWords:Array(32).fill(0)});
for(const probe of probes.executed_probes){
 const template={paint:'carpaint',window:'car_window',glass:'colored_glass',chrome:'chrome',carbon:'carbon_fiber'}[probe.name],node=root(template);
 const raw=Buffer.from(probe.material_parameters_hex,'hex');node.parameter_words=Array.from({length:raw.length/4},(_,i)=>raw.readUInt32LE(i*4));
 if(probe.name==='glass')node.glass_light_mode=raw.readUInt32LE(16);
 const rows=inputs.expected_inputs.map((row,i)=>({...row,word:probe.input_words[i]}));
 const ctx=context();if(probe.name==='glass')ctx.generationParameters=probes.globals[String(0x618970)].map(nativeWordFloat);
 const result=bindNativeVehicleMaterial(node,rows,ctx);assert.equal(result.supported,true);
 assert.deepEqual(result.passes[0].materialRGBA,probe.rgba,probe.name+' original unchanged native binder RGBA');
 for(const address of ['52','53'])if(probe.uniform_words[address])assert.deepEqual(nativeFloatWords(result.vu[address]),probe.uniform_words[address],probe.name+' actual emitted native VU'+address);
 if(probe.uniform_words['31'])assert.deepEqual(nativeFloatWords([...result.ambient,1]),probe.uniform_words['31'],probe.name+' native ambient vector');
 if(probe.uniform_words['40'])assert.deepEqual(result.vu40Words,probe.uniform_words['40']);
 console.log('PASS actual original EE binder',probe.name);
}
const node=root('car_window'),snapshot=structuredClone(node),ctx=context(),ctxSnapshot=structuredClone(ctx);
const initial=bindNativeVehicleMaterial(node,inputs.expected_inputs,ctx);
assert.equal(initial.windowTexture.name,node.window_texture_variants[0].name);
const damaged=bindNativeVehicleMaterial(node,inputs.expected_inputs,{...ctx,inputOverrides:{WindowsBroken:1}});
assert.equal(damaged.windowTexture.name,node.window_texture_variants[1].name);assert.notDeepEqual(damaged.windowTexture,initial.windowTexture);
assert.deepEqual(node,snapshot);assert.deepEqual(ctx,ctxSnapshot);
assert.throws(()=>bindNativeVehicleMaterial(node,[],ctx),/parameter index/);
assert.throws(()=>bindNativeVehicleMaterial(node,inputs.expected_inputs,{...ctx,state:{}}),/RGBA/);
assert.throws(()=>nativeVehicleInputWords(inputs.expected_inputs,{invented:0}),/Unknown/);
const unordered=structuredClone(inputs.expected_inputs);unordered[0].index=1;assert.throws(()=>nativeVehicleInputWords(unordered),/order/);
assert.deepEqual(nativeVehiclePassState([{command:3,value:0x10048}],{0:2,8:0x80ffffff}),{0:2,3:0x10048,8:0x80ffffff});
const composite=root('carpaint','composite'),index=composite.parameter_words[3]&255,name=inputs.expected_inputs[index].name;
const chosen=bindNativeVehicleMaterial(composite,inputs.expected_inputs,{...ctx,inputOverrides:{[name]:0}});assert.equal(chosen.path[0].selected,0);
assert.throws(()=>bindNativeVehicleMaterial(composite,inputs.expected_inputs,{...ctx,inputOverrides:{[name]:999}}),/selector/);
const decal=root('car_decal','composite');
for(const child of decal.children){const delta=read('vehicle-material-decal-fragments.json').fragments.find(r=>r.offset===child.source_offset+48);const raw=Buffer.from(delta.hex,'hex');child.parameter_words=Array.from({length:4},(_,i)=>raw.readUInt32LE(i*4));}
const normal=bindNativeVehicleMaterial(decal,inputs.expected_inputs,ctx);assert.deepEqual(normal.materialRGBA,[255,255,255,102]);assert.deepEqual(normal.restoreRGBA,[255,255,255,128]);
const chromeDecal=bindNativeVehicleMaterial(decal,inputs.expected_inputs,{...ctx,decalChromeDepthMode:1,inputOverrides:{DecalShaderIdx:1}});assert.deepEqual(chromeDecal.materialRGBA,[255,255,255,128]);assert.equal(chromeDecal.path[0].selected,1);
const novinyl=bindNativeVehicleMaterial(root('carpaint_novinyl'),inputs.expected_inputs,ctx);assert.deepEqual(novinyl.vu[53],[0,Math.fround(.2),Math.fround(.9),Math.fround(.99)]);
const unknownDraw=root('lit_textured');unknownDraw.draw_address=123;assert.equal(bindNativeVehicleMaterial(unknownDraw,inputs.expected_inputs,ctx).supported,false);
const unknown=root('lit_textured');unknown.bind_address=123;assert.equal(bindNativeVehicleMaterial(unknown,inputs.expected_inputs,ctx).supported,false);
assert.throws(()=>nativeWordFloat(0x7f800000),/Nonfinite/);
console.log('PASS source indices, selector bounds, inherited state, glass damage, decal tint, explicit missing contexts and immutable input graphs');
