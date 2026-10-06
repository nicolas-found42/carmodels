// Scene choices describe the geometry actually present in the exported GLB.
export function sceneLabel(name) {
 const m=name.match(/^(Candidate )?tree (\d+) — (.+)$/i);
 if(!m)return name;
 const state={'all states':'all states (every panel kept)','Low-speed wheels, lights off':'standard wheels, headlights off','Moving wheels, lights off':'wheels turning, headlights off'}[m[3]]||m[3];
 return `${m[1]?'Candidate':'Assembly'} ${m[2]} — ${state}`;
}

export function sceneHasGeometry(doc, scene) {
 function hasGeometry(index) {
  const node=doc.nodes[index];
  const mesh=node.mesh===undefined?null:doc.meshes[node.mesh];
  return Boolean(mesh?.primitives.some(p=>doc.accessors[p.attributes.POSITION].count>0 &&
   (p.indices===undefined || doc.accessors[p.indices].count>0))) || (node.children||[]).some(hasGeometry);
 }
 return scene.nodes.some(hasGeometry);
}

export function geometryOptions(doc, records) {
 return [...doc.scenes.slice(1).map((s,i)=>{
  const disabled=!sceneHasGeometry(doc,s);
  return {value:'scene'+(i+1),textContent:sceneLabel(s.name)+(disabled?' (no geometry)':''),
   title:s.name+(disabled?' — this source tree contains no drawable geometry':''),disabled};
 }),...records.map(r=>({value:String(r.record),textContent:`Assembly part ${r.record}: ${r.triangles.toLocaleString()} candidate triangles`,disabled:false}))];
}

export function defaultGeometryValue(doc, options) {
 const desired='scene'+doc.scene;
 return options.find(o=>o.value===desired&&!o.disabled)?.value || options.find(o=>!o.disabled)?.value || '';
}
