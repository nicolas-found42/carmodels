import * as THREE from 'three';
import {pickRecord,formatMC3Value} from './mc3-record-inspection.mjs';

const shown=object=>{for(let node=object;node;node=node.parent)if(!node.visible)return false;return true;};

// Selection owns only disposable line overlays. Source materials and visibility stay intact.
export function createMC3RecordInspector({container,canvas,camera,onChange=()=>{}}) {
 const doc=container.ownerDocument,make=(tag,text)=>{const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const title=make('h2','Pilot native records'),label=make('label','Native record '),list=make('select');
 list.id='source-record-list';list.size=2;list.setAttribute('aria-label','Native record');label.append(list);
 const note=make('p','Select a record here or click its visible geometry. Arrow keys and Enter work in the list. Selection never reveals hidden geometry.');
 const status=make('p');status.id='source-record-status';status.setAttribute('role','status');
 const details=make('dl');details.id='source-record-details';const fields={};
 for(const [field,name] of Object.entries({identity:'Native record identity',sourceOccurrence:'Source occurrence',sourceHash:'Source SHA-256',parentIdentity:'Native parent identity',localMatrix:'Local rest matrix (column-major)',worldMatrix:'World rest matrix (column-major)'})){
  const value=make('dd','Unknown');value.dataset.field=field;value.style.overflowWrap='anywhere';fields[field]=value;details.append(make('dt',name),value);
 }
 container.append(title,label,note,status,details);container.hidden=true;
 let records=[],groups=[],selected=null,overlays=[],down=null;
 function clearOverlays(){for(const overlay of overlays){overlay.removeFromParent();overlay.geometry.dispose();overlay.material.dispose();}overlays=[];}
 function meshes(record){const found=[];for(const root of groups)root.traverse(node=>{if(!node.isMesh||!shown(node))return;for(let owner=node;owner;owner=owner.parent){if(owner.userData.sourceNodeIndex===record.nodeIndex){found.push(node);break;}}});return found;}
 function refresh(){
  clearOverlays();const record=records.find(record=>record.identity===selected);
  if(!record)return;
  for(const mesh of meshes(record)){
   const overlay=new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry),new THREE.LineBasicMaterial({color:0xffc766,depthTest:true,depthWrite:false}));
   overlay.userData.inspectorHighlight=record.identity;overlay.raycast=()=>{};mesh.add(overlay);overlays.push(overlay);
  }
  list.value=record.identity;
  for(const [field,node] of Object.entries(fields)){const value=record[field];node.textContent=Array.isArray(value)?JSON.stringify(value):formatMC3Value(value);}
  status.textContent=overlays.length?`Selected ${record.identity}; ${overlays.length} visible mesh(es) highlighted.`:`Selected ${record.identity}; hidden in this geometry view. No geometry was revealed.`;
 }
 function select(identity){if(!records.some(record=>record.identity===identity))return;selected=identity;refresh();onChange();}
 list.addEventListener('change',()=>select(list.value));
 list.addEventListener('keydown',event=>{
  if(!['ArrowDown','ArrowUp','Enter'].includes(event.key)||!records.length)return;event.preventDefault();
  let index=Math.max(0,records.findIndex(record=>record.identity===list.value));
  if(event.key!=='Enter')index=Math.max(0,Math.min(records.length-1,index+(event.key==='ArrowDown'?1:-1)));
  list.value=records[index].identity;select(list.value);
 });
 canvas.addEventListener('pointerdown',event=>{down=event.button===0?[event.clientX,event.clientY]:null;});
 canvas.addEventListener('pointerup',event=>{
  const start=down;down=null;if(!start||event.button!==0||Math.hypot(event.clientX-start[0],event.clientY-start[1])>4||!records.length)return;
  const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
  camera.updateMatrixWorld();for(const group of groups)group.updateWorldMatrix(true,true);
  const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);
  const hits=ray.intersectObjects(groups,true).flatMap(hit=>{
   if(!hit.object.isMesh||!shown(hit.object))return [];
   for(let owner=hit.object;owner;owner=owner.parent){const record=records.find(record=>record.nodeIndex===owner.userData.sourceNodeIndex);if(record)return [{identity:record.identity,distance:hit.distance}];}
   return [];
  });
  const identity=pickRecord(hits);if(identity)select(identity);
 });
 return {
  bind(next,nextGroups){clearOverlays();records=next;groups=nextGroups;selected=null;container.hidden=!records.length;list.replaceChildren(...records.map(record=>{const option=make('option',record.identity);option.value=record.identity;return option;}));for(const node of Object.values(fields))node.textContent='Unknown';status.textContent='Choose a native record. Inspection describes retained static rest placement, not runtime animation.';if(records.length)select(records[0].identity);},
  clear(){clearOverlays();records=[];groups=[];selected=null;list.replaceChildren();container.hidden=true;},
  refresh,
  snapshot(){return {selected,records:records.map(record=>({...record,visibleMeshes:meshes(record).length,highlightedMeshes:overlays.filter(overlay=>overlay.userData.inspectorHighlight===record.identity&&shown(overlay)).length})),details:records.find(record=>record.identity===selected)??null};},
 };
}
