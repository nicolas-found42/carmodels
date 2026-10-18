import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../dealership/vendor/three.module.js';
import {createPaintSession,readGamePaint,colourId,applyPaintMaterial,fetchGamePalette} from '../dealership/game-paint.mjs';
import {createColourControls} from '../dealership/colour-controls.mjs';
import {exportPaintGLB,createPaintDownload} from '../dealership/paint-export.mjs';
import {readGLB} from '../dealership/model-load.mjs';
import {applyMaterial} from '../dealership/materials.mjs';

const red={id:'red',name:'Native red',rgb:[.5,.01,.02],source:'native/car-a/paint:1'};
const blue={id:'blue',name:'Native blue',rgb:[.01,.1,.8],source:'native/car-b/paint:2'};
const foreign={id:'foreign',name:'Foreign',rgb:[0,1,0],source:'other-game',game:'other'};
const doc={asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{mesh:0,translation:[2,3,4],extras:{edited:true}}],
 buffers:[{byteLength:8}],bufferViews:[{buffer:0,byteLength:8}],
 images:[{bufferView:0,mimeType:'image/png'}],textures:[{source:0}],
 materials:[{name:'body',pbrMetallicRoughness:{baseColorFactor:[0,0,0,1],roughnessFactor:.7,metallicFactor:0}},
 {name:'rim',pbrMetallicRoughness:{baseColorFactor:[.1,.1,.1,1]}},
 {name:'trim',pbrMetallicRoughness:{baseColorFactor:[.2,.2,.2,1],baseColorTexture:{index:0}}},
 {name:'glass',alphaMode:'BLEND',pbrMetallicRoughness:{baseColorFactor:[.2,.3,.4,.4]}},
 {name:'preset body',pbrMetallicRoughness:{baseColorFactor:[.9,.9,.9,1]}}],
 meshes:[{primitives:[{material:0,attributes:{POSITION:0},extensions:{KHR_materials_variants:{mappings:[{material:4,variants:[0]}]}}},
 {material:1,attributes:{POSITION:0}},{material:2,attributes:{POSITION:0}},{material:3,attributes:{POSITION:0}}]}],
 extensionsUsed:['KHR_materials_variants'],extensions:{KHR_materials_variants:{variants:[{name:'Native coordinated preset'}]}},
 extras:{original:{keep:true},gamePaint:{schema:1,channels:[{id:'body',name:'Body',materials:[0],
 finishes:[{id:'matte',name:'Native matte',roughness:1,metalness:0,source:'test native finish'}]},
 {id:'rims',name:'Rims',materials:[1]}],colors:[red],limits:['Test native bindings.']}}};
function glb(document) {
 const json=Buffer.from(JSON.stringify(document)),length=(json.length+3)&~3;
 const bytes=Buffer.alloc(28+length+8);bytes.writeUInt32LE(0x46546c67,0);bytes.writeUInt32LE(2,4);bytes.writeUInt32LE(bytes.length,8);
 bytes.writeUInt32LE(length,12);bytes.writeUInt32LE(0x4e4f534a,16);bytes.fill(32,20,20+length);json.copy(bytes,20);
 bytes.writeUInt32LE(8,20+length);bytes.writeUInt32LE(0x004e4942,24+length);bytes.fill(73,28+length);
 return bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
}
const source=glb(doc),before=structuredClone(doc),primitives=doc.meshes[0].primitives;
const session=createPaintSession(doc,{game:'game',colors:[{...blue,game:'game'},foreign]});
assert.equal(session.colors.length,2,'same-game union excludes foreign colours');
assert.throws(()=>session.setChannel('body',colourId(foreign)),/not in this game/);
assert.throws(()=>session.setChannel('trim',colourId(red)),/Unrecovered/);
assert.throws(()=>session.setFinish('rims','matte'),/Unrecovered/);
session.setPreset(0);session.setChannel('body',colourId(red));session.setChannel('rims',colourId(blue));session.setFinish('body','matte');
assert.deepEqual(session.material(primitives[0]).definition.pbrMetallicRoughness.baseColorFactor,[...red.rgb,1],'paint replaces black rather than multiplying it');
assert.deepEqual(session.material(primitives[1]).definition.pbrMetallicRoughness.baseColorFactor,[...blue.rgb,1]);
assert.equal(session.material(primitives[2]).definition,doc.materials[2]);
assert.equal(session.material(primitives[3]).definition,doc.materials[3]);
assert.deepEqual(doc,before,'preview never edits original document');
const meshMaterial=new THREE.MeshStandardMaterial(),texture=new THREE.Texture();
applyPaintMaterial(applyMaterial,meshMaterial,doc,[texture],primitives[2],session,{wireframe:true,sharp:true});
assert.equal(meshMaterial.map,texture);assert.equal(meshMaterial.wireframe,true);
applyPaintMaterial(applyMaterial,meshMaterial,doc,[texture],primitives[0],session);
assert.deepEqual(meshMaterial.color.toArray(),red.rgb);assert.equal(meshMaterial.roughness,1);
const encoded=exportPaintGLB(source,session),result=readGLB(encoded);
assert.deepEqual(new Uint8Array(result.bin),new Uint8Array(readGLB(source).bin),'geometry and embedded texture bytes unchanged');
assert.deepEqual(result.doc.nodes,doc.nodes);assert.deepEqual(result.doc.extensions,doc.extensions);
assert.deepEqual(result.doc.materials.slice(0,doc.materials.length),doc.materials,'all original native materials remain selectable');
assert.deepEqual(result.doc.meshes[0].primitives.map(p=>result.doc.materials[p.material].pbrMetallicRoughness.baseColorFactor),[[...red.rgb,1],[...blue.rgb,1],[.2,.2,.2,1],[.2,.3,.4,.4]]);
const reopened=createPaintSession(result.doc,{game:'game',colors:[{...blue,game:'game'}]});
reopened.setChannel('body',colourId(red));assert(reopened.material(result.doc.meshes[0].primitives[0]).changed,'export retains channel bindings');
// Identical material definitions and shared preset targets must not merge
// independent channels in the exported default or after reopening.
{
 const shared=structuredClone(doc);
 shared.materials[1]=structuredClone(shared.materials[0]);
 for(const primitive of shared.meshes[0].primitives.slice(0,2))primitive.extensions={KHR_materials_variants:{mappings:[{material:0,variants:[0]}]}};
 shared.meshes[0].primitives[2].extensions={KHR_materials_variants:{mappings:[{material:0,variants:[0]}]}};
 const makeSession=()=>createPaintSession(shared,{game:'game',colors:[{...blue,game:'game'}]});
 for(const override of [false,true]) {
  const paint=makeSession();paint.setPreset(0);
  assert.equal(paint.material(shared.meshes[0].primitives[1]).channelId,'rims','base channel wins over shared preset material');
  if(override)for(const channel of ['body','rims'])paint.setChannel(channel,colourId(red));
  assert.equal(paint.material(shared.meshes[0].primitives[2]).channelId,undefined,'a shared preset material does not invent paint ownership on trim');
  const exported=readGLB(exportPaintGLB(glb(shared),paint)).doc;
  const bindings=exported.extras.gamePaint.channels;
  assert(!bindings[0].materials.some(index=>bindings[1].materials.includes(index)),'exported channel bindings remain disjoint');
  const reopened=createPaintSession(exported,{game:'game',colors:[{...blue,game:'game'}]});
  const parts=exported.meshes[0].primitives;
  assert.equal(reopened.material(parts[2]).channelId,undefined,'export never gives shared-target trim a paint channel');
  const trimBefore=reopened.material(parts[2]).definition;
  const bodyBefore=reopened.material(parts[0]).definition;
  reopened.setChannel('rims',colourId(blue));
  assert.deepEqual(reopened.material(parts[0]).definition,bodyBefore,'changing rims leaves body default intact');
  assert.deepEqual(reopened.material(parts[1]).definition.pbrMetallicRoughness.baseColorFactor,[...blue.rgb,1]);
  reopened.setChannel('body',colourId(red));
  assert.deepEqual(reopened.material(parts[2]).definition,trimBefore,'changing body after reimport leaves unowned trim intact');
  reopened.setPreset(0);
  assert.equal(reopened.material(parts[1]).channelId,'rims');
  assert.deepEqual(reopened.material(parts[1]).definition.pbrMetallicRoughness.baseColorFactor,[...blue.rgb,1]);
 }
 const chips=structuredClone(doc);
 chips.extensions.KHR_materials_variants.variants[0].extras={nativeRGB:[.2,0,0]};
 const paint=createPaintSession(chips);
 assert.deepEqual(paint.presets[0].rgb,[.2,0,0],'recovered native preset vectors provide real swatches');
 assert.equal(paint.colors.length,1,'preset swatches do not manufacture transferable palette entries');
}
const state=session.state;session.reset();session.restore(state);assert.deepEqual(session.state,state);
session.restore({...state,presetName:'a different preset',channels:{body:{color:'fabricated RGB'}}});
assert.equal(session.state.preset,null);assert.deepEqual(session.state.channels,{});
for(const mutation of [d=>d.extras.gamePaint.colors[0].rgb=[2,0,0],d=>d.extras.gamePaint.channels[1].materials=[0],
 d=>d.extras.gamePaint.channels[0].materials=[900],d=>d.extras.gamePaint.channels[0].finishes[0].roughness=NaN]) {
 const bad=structuredClone(doc);mutation(bad);assert.throws(()=>readGamePaint(bad),/Invalid/);
}
assert.equal(createPaintSession({materials:[]}).channels.length,0);
let objects=0,revoked=[];const link={};
const download=createPaintDownload(link,{url:{createObjectURL(){return 'blob:'+ ++objects;},revokeObjectURL(url){revoked.push(url);}}});
download.update(source,session,'edited.glb');download.update(source,session,'edited.glb');download.clear();
assert.deepEqual(revoked,['blob:1','blob:2']);assert.equal(link.download,'edited.glb');
await assert.rejects(fetchGamePalette(async()=>({ok:false})),/unavailable/);

// Exercise the real controls, storage and source-viewer material callback.
function element(tag='div') {return {tag,value:'',children:[],style:{},attributes:{},listeners:{},
 setAttribute(k,v){this.attributes[k]=v;},replaceChildren(...nodes){this.children=nodes;},append(...nodes){this.children.push(...nodes);},
 prepend(...nodes){this.children.unshift(...nodes);},addEventListener(event,fn){this.listeners[event]=fn;}};}
const container=element(),document={createElement:element,querySelector:()=>container};container.ownerDocument=document;
const saved=new Map(),storage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
let changed=0;const presets=element('select');
const controls=createColourControls({root:document,storage,presetSelect:presets,onChange:()=>changed++});
controls.setEnabled(true);controls.bind({model:doc,game:'game',carId:'car',colors:[{...blue,game:'game'}]});
const [channel,search,reset,choices]=container.children;
channel.value='body';channel.listeners.change();
let button=choices.children.find(n=>n.title===blue.source);assert(button);button.listeners.click();
assert.equal(controls.session.state.channels.body.color,colourId(blue));assert(changed>=2);
search.value='no such colour';search.listeners.input();assert.equal(choices.children.length,2,'only preset colour and native finish controls remain');
controls.setEnabled(false);controls.setEnabled(true);controls.bind({model:doc,game:'game',carId:'car',colors:[{...blue,game:'game'}]});
assert.equal(controls.session.state.channels.body.color,colourId(blue),'per-car selection restored');
controls.bind({model:doc,game:'game',carId:'another',colors:[{...blue,game:'game'}]});assert.deepEqual(controls.session.state.channels,{});
controls.bind({model:doc,game:'game',carId:'car',colors:[{...blue,game:'game'}]});reset.listeners.click();assert.deepEqual(controls.session.state.channels,{});assert.equal(saved.size,0);
const sourcePage=fs.readFileSync(new URL('../dealership/recovered.html',import.meta.url),'utf8');
const materialStart=sourcePage.indexOf('function updateMaterials()'),materialEnd=sourcePage.indexOf('// Keep the fitted',materialStart);
const toggles=Object.fromEntries(['textures','wire','sharp','flip'].map(id=>['#'+id,{checked:true}]));
const sourceMaterial=new THREE.MeshStandardMaterial();
const sourceState={doc,textures:[texture],meshes:[{material:sourceMaterial,userData:{paintPrimitive:primitives[2]}}]};
const update=new Function('loaded','document','applyMaterial','applyPaintMaterial','colourControls','presentation',sourcePage.slice(materialStart,materialEnd)+'return updateMaterials;')(
 sourceState,{querySelector:id=>toggles[id]},applyMaterial,applyPaintMaterial,{session},{finish(material){return material;}});
update();assert.equal(sourceMaterial.map,texture);assert.equal(sourceMaterial.wireframe,true);assert.equal(texture.magFilter,THREE.NearestFilter);
toggles['#textures'].checked=false;update();assert.equal(sourceMaterial.map,null);
sourceMaterial.dispose();meshMaterial.dispose();texture.dispose();
console.log('PASS native paint: same-game palette isolation, independent channels, trim/glass protection, native finishes, safe restore/reset, edited GLB/BIN/variants preservation, export rebinding and URL cleanup, real controls/storage/search and source material callback');
