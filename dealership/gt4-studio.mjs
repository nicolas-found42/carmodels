import * as THREE from './vendor/three.module.js';

// An offline studio environment: broad neutral softboxes make curvature visible
// without a network HDRI or guessed native GT4 reflection pass.
export function createGT4Studio(renderer) {
 let target=null;
 const previous={toneMapping:renderer.toneMapping,exposure:renderer.toneMappingExposure};
 function environment() {
  if(target)return target.texture;
  const room=new THREE.Scene();room.background=new THREE.Color(.13,.13,.13);
  const resources=[];
  function box(size,position,intensity) {
   const geometry=new THREE.BoxGeometry(...size),material=new THREE.MeshBasicMaterial({color:new THREE.Color(intensity,intensity,intensity),side:THREE.DoubleSide});
   const mesh=new THREE.Mesh(geometry,material);mesh.position.set(...position);room.add(mesh);resources.push(geometry,material);
  }
  box([4,.05,10],[0,5,0],5);
  box([.05,3,8],[-6,2,0],3);
  box([.05,2,6],[6,3,-1],2);
  box([6,2,.05],[0,2,-7],1.5);
  const generator=new THREE.PMREMGenerator(renderer);
  try {target=generator.fromScene(room,.04,.1,100,{size:512});}
  finally {generator.dispose();resources.forEach(r=>r.dispose());}
  return target.texture;
 }
 return {
  setEnabled(scene,enabled) {
   scene.environment=enabled?environment():null;
   scene.environmentIntensity=enabled ? .8 : 1;
   renderer.toneMapping=enabled?THREE.ACESFilmicToneMapping:previous.toneMapping;
   renderer.toneMappingExposure=enabled?1:previous.exposure;
  },
  dispose(){target?.dispose();target=null;}
 };
}
