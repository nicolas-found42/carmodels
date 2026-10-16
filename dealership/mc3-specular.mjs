import * as THREE from './vendor/three.module.js';

// Native sprite-copy coordinates from mc3_specular_native.py. Input rows must
// already use native target order; source acquisition and camera are separate.
export function copyNativeEnvironmentRGBA(source) {
 if(!(source instanceof Uint8Array||source instanceof Uint8ClampedArray)||source.length!==256*256*4)throw Error('Specular copy requires native 256x256 RGBA8.');
 const result=new Uint8Array(64*64*4);
 for(let y=0;y<64;y++)for(let x=0;x<64;x++) {
  const y0=Math.max(0,4*y-1),y1=4*y,x0=Math.max(0,4*x-1),x1=4*x;
  const a=(y0*256+x0)*4,b=(y0*256+x1)*4,c=(y1*256+x0)*4,d=(y1*256+x1)*4;
  for(let channel=0;channel<4;channel++) {
   const top=(source[a+channel]+source[b+channel])>>1;
   const bottom=(source[c+channel]+source[d+channel])>>1;
   const filtered=(top+bottom)>>1;
   result[(y*64+x)*4+channel]=(filtered*(channel===3?128:127))>>7;
  }
 }
 return result;
}

export function nativeRowsFromReadback(source,rowOrder) {
 if(rowOrder!=='native-first'&&rowOrder!=='native-last')throw Error('Native capture readback row order must be explicit.');
 if(!(source instanceof Uint8Array)||source.length!==256*256*4)throw Error('Native capture needs 256x256 RGBA8 readback.');
 if(rowOrder==='native-first')return source;
 const result=new Uint8Array(source.length),stride=256*4;
 for(let y=0;y<256;y++)result.set(source.subarray((255-y)*stride,(256-y)*stride),y*stride);
 return result;
}

// The caller must supply the recovered environment renderer, camera/context,
// and proved native row orientation. No scene, lighting or camera is invented.
// Optional GPU acquisition helper. The production original-garage provider
// uses the separately scoped portable CPU rasterizer in mc3-environment.mjs.
export function createNativeSpecularCapture({renderEnvironment,rowOrder}={}) {
 if(typeof renderEnvironment!=='function')throw Error('Native specular capture needs its recovered environment renderer.');
 if(rowOrder!=='native-first'&&rowOrder!=='native-last')throw Error('Native capture readback row order must be explicit.');
 const target=new THREE.WebGLRenderTarget(256,256,{format:THREE.RGBAFormat,type:THREE.UnsignedByteType,
  minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,colorSpace:THREE.NoColorSpace});
 const texture=new THREE.DataTexture(new Uint8Array(64*64*4),64,64);
 texture.colorSpace=THREE.NoColorSpace;texture.minFilter=texture.magFilter=THREE.LinearFilter;
 texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.flipY=false;
 const readback=new Uint8Array(256*256*4);let previousRevision,hasRevision=false,disposed=false;
 return {
  texture,
  update(renderer,context,revision) {
   if(disposed)throw Error('Native specular capture is disposed.');
   if(revision!==undefined&&hasRevision&&Object.is(revision,previousRevision))return false;
   const saved={target:renderer.getRenderTarget(),viewport:renderer.getViewport(new THREE.Vector4()),
    scissor:renderer.getScissor(new THREE.Vector4()),scissorTest:renderer.getScissorTest(),
    clear:renderer.getClearColor(new THREE.Color()),alpha:renderer.getClearAlpha(),
    autoClear:renderer.autoClear,toneMapping:renderer.toneMapping};
   try {
    renderer.setRenderTarget(target);renderer.setViewport(0,0,256,256);renderer.setScissor(0,0,256,256);
    renderer.setScissorTest(false);renderer.autoClear=false;renderer.toneMapping=THREE.NoToneMapping;
    const result=renderEnvironment(renderer,context);
    if(result?.then)throw Error('Native environment assets must finish loading before capture.');
    renderer.readRenderTargetPixels(target,0,0,256,256,readback);
    texture.image.data.set(copyNativeEnvironmentRGBA(nativeRowsFromReadback(readback,rowOrder)));texture.needsUpdate=true;
    previousRevision=revision;hasRevision=revision!==undefined;return true;
   } finally {
    renderer.setRenderTarget(saved.target);renderer.setViewport(saved.viewport);renderer.setScissor(saved.scissor);
    renderer.setScissorTest(saved.scissorTest);renderer.setClearColor(saved.clear,saved.alpha);
    renderer.autoClear=saved.autoClear;renderer.toneMapping=saved.toneMapping;
   }
  },
  dispose(){if(!disposed){disposed=true;target.dispose();texture.dispose();}}
 };
}
