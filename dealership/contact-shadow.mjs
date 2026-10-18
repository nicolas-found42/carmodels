import * as THREE from './vendor/three.module.js';

// Issue #25: in Enhanced mode the car stands on a ground surface with a soft contact shadow.
// The technique is three.js's contact shadow (examples/webgl_shadow_contact.html): the car's depth
// is rendered with an orthographic camera under its floor, blurred, and painted on a plane. It is a
// flat, non-physical fake -- it cannot self-shadow -- and it is built only once Enhanced is
// selected: Original creates no ground, no shadow plane and no render target.
// The values below are a judgement call, recorded in research/enhanced-contact-shadow-2026-10-18.md.
export const CONTACT_SHADOW = Object.freeze({
  resolution: 1024, // depth and blur target, square, independent of the canvas and the car
  blur: 2.5, // three.js's blur unit: one tap step is this much over 256 of the shadow plane
  darkness: 1.6, // shadow alpha where a surface meets the ground, before the blur softens it
  opacity: .85, // the shadow plane's own opacity
  margin: .15, // the shadow plane extends this far past the car's footprint
  groundSpan: 24, // the ground's side as a multiple of the shadow plane's
  groundColour: 0x1e2735, // a floor a little lighter than the #151a22 backdrop
  groundDrop: .002, // ground below the car's lowest point, as a fraction of the plane's side
  planeDrop: .0005, // the shadow plane a hair below that point, same fraction: that point is the
  // lower of the framing box's floor and the recovered under-car shadow quad's own floor (issue #23,
  // the quad is flat at one height), which the page measures and passes to follow(). The plane is
  // therefore under the quad in every view rather than over it: on the shipped corpus it stands 2.0
  // to 3.7 mm below the quad (this drop at the plane's own side), and the quad draws over the shadow
  // instead of fighting it for depth
  cameraDrop: .01, // the depth camera sits this far below the ground, same fraction
  minimumFootprint: .1, // a degenerate record still gets a usable plane
});

// three.js's examples/jsm/shaders/HorizontalBlurShader.js and VerticalBlurShader.js (MIT, three.js
// authors), inlined so the vendored pin gains no file: 9 samples per pass, standard deviation 2.7,
// one horizontal and one vertical pass, the tap step being the blur amount over 256.
const BLUR_WEIGHTS = Object.freeze([.051, .0918, .12245, .1531, .1633, .1531, .12245, .0918, .051]);

// A unit quad in the XZ plane whose uv is the orthographic shadow camera's own mapping of it, so the
// blurred depth texture lands on the plane without a flip: with the camera looking up (+Y) and up
// (0,0,1), u runs with +X and v with +Z, and both are 0.5 + the local coordinate.
function footprintGeometry() {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([-.5, 0, -.5, .5, 0, -.5, .5, 0, .5, -.5, 0, .5], 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
  geometry.setIndex([0, 2, 1, 0, 3, 2]); // counter-clockwise seen from above
  return geometry;
}

function blurShader(axis, name) {
  const taps = BLUR_WEIGHTS.map((weight, tap) => `\n\t\tsum += texture2D( tDiffuse, vUv + ${axis} * ${(tap - 4).toFixed(1)} * h ) * ${weight};`).join('');
  return {
    name,
    uniforms: {tDiffuse: {value: null}, h: {value: 1 / 256}},
    vertexShader: 'varying vec2 vUv;\nvoid main() {\n\tvUv = uv;\n\tgl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );\n}',
    fragmentShader: `uniform sampler2D tDiffuse;\nuniform float h;\nvarying vec2 vUv;\nvoid main() {\n\tvec4 sum = vec4( 0.0 );${taps}\n\tgl_FragColor = sum;\n}`,
  };
}

export function createContactShadow(renderer, {resolution = CONTACT_SHADOW.resolution} = {}) {
  if (!Number.isInteger(resolution) || resolution < 2) throw Error('The contact shadow resolution must be an integer of at least 2.');
  let scene = null, geometry = null, group = null, ground = null, plane = null, blurPlane = null, camera = null;
  let depthMaterial = null, depthTarget = null, blurTarget = null, horizontal = null, vertical = null;
  let box = null, shadowFloor = null, enabled = false, dirty = false, renders = 0;
  const size = new THREE.Vector3(), centre = new THREE.Vector3(), darkness = {value: CONTACT_SHADOW.darkness};

  // Built on first use, so Original mode holds nothing at all.
  function build() {
    geometry = footprintGeometry();
    // The recovered corpus has no proven winding, and the depth pass needs both faces of every
    // panel, so the ground, the shadow plane and the depth material are all double-sided.
    ground = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: CONTACT_SHADOW.groundColour, metalness: 0, roughness: 1, side: THREE.DoubleSide}));
    ground.name = 'contact-shadow-ground';
    depthTarget = new THREE.WebGLRenderTarget(resolution, resolution);
    blurTarget = new THREE.WebGLRenderTarget(resolution, resolution);
    plane = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({map: depthTarget.texture, opacity: CONTACT_SHADOW.opacity, transparent: true, depthWrite: false, side: THREE.DoubleSide, toneMapped: false}));
    plane.name = 'contact-shadow-plane';
    plane.renderOrder = 1; // painted over the ground it darkens
    blurPlane = new THREE.Mesh(geometry); // the full-frustum target of the blur passes
    blurPlane.visible = false;
    horizontal = new THREE.ShaderMaterial({...blurShader('vec2( 1.0, 0.0 )', 'HorizontalBlurShader'), depthTest: false, depthWrite: false, side: THREE.DoubleSide});
    vertical = new THREE.ShaderMaterial({...blurShader('vec2( 0.0, 1.0 )', 'VerticalBlurShader'), depthTest: false, depthWrite: false, side: THREE.DoubleSide});
    // Like MeshDepthMaterial, but black where a surface is close to the floor instead of grey.
    depthMaterial = new THREE.MeshDepthMaterial({depthPacking: THREE.BasicDepthPacking, side: THREE.DoubleSide});
    depthMaterial.onBeforeCompile = shader => {
      shader.uniforms.darkness = darkness;
      shader.fragmentShader = 'uniform float darkness;\n' + shader.fragmentShader.replace(
        'gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );',
        'gl_FragColor = vec4( vec3( 0.0 ), ( 1.0 - fragCoordZ ) * darkness );');
    };
    // rotation.x = PI/2 looks straight up: the camera's local X is world +X and its local Y is
    // world +Z, which is exactly the mapping the footprint geometry's uv is written for.
    camera = new THREE.OrthographicCamera(-.5, .5, .5, -.5, 0, 1);
    camera.rotation.x = Math.PI / 2;
    group = new THREE.Group();
    group.name = 'contact-shadow';
    group.visible = false;
    group.add(camera); // the camera's world matrix follows the car when the group moves
    group.add(ground, plane, blurPlane);
  }

  // The car's bounding box is the only required input: the selected car and the geometry choice both
  // arrive as a fresh box, and an empty or absent box means there is nothing to stand on. The second
  // input is the floor of the recovered under-car shadow quad the selected view draws, when the
  // caller knows it (the page leaves that quad out of the framing box on purpose): the plane stands
  // under the lower of the two, so it is never above the quad.
  function place() {
    if (!group)return;
    const empty = !box || box.isEmpty();
    group.visible = enabled && !empty;
    if (empty)return;
    box.getSize(size);
    box.getCenter(centre);
    const footprint = Math.max(size.x, size.z, CONTACT_SHADOW.minimumFootprint);
    const side = footprint * (1 + CONTACT_SHADOW.margin);
    const floor = shadowFloor === null ? box.min.y : Math.min(box.min.y, shadowFloor);
    // the depth camera reaches the top of the framed box from that floor, not the box's own span
    const height = Math.max(box.max.y - floor, footprint * .05);
    group.position.set(centre.x, floor, centre.z);
    plane.scale.set(side, 1, side);
    blurPlane.scale.set(side, 1, side);
    plane.position.set(0, -side * CONTACT_SHADOW.planeDrop, 0);
    blurPlane.position.copy(plane.position); // the blur passes draw where the plane samples
    ground.scale.set(side * CONTACT_SHADOW.groundSpan, 1, side * CONTACT_SHADOW.groundSpan);
    ground.position.set(0, -side * CONTACT_SHADOW.groundDrop, 0);
    camera.position.set(0, -side * CONTACT_SHADOW.cameraDrop, 0);
    camera.left = -side / 2; camera.right = side / 2; camera.top = side / 2; camera.bottom = -side / 2;
    camera.near = 0; camera.far = side * CONTACT_SHADOW.cameraDrop + height * 1.05;
    camera.updateProjectionMatrix();
    // The blur passes render before the page's own scene update, so the group's world matrix must be
    // current now rather than after the next full render.
    group.updateMatrixWorld(true);
    dirty = true;
  }

  // renderTarget -> blurPlane (horizontal) -> blurTarget -> blurPlane (vertical) -> renderTarget
  function blur(material, texture, target, amount) {
    blurPlane.material = material;
    material.uniforms.tDiffuse.value = texture;
    material.uniforms.h.value = amount * 1 / 256;
    blurPlane.visible = true;
    renderer.setRenderTarget(target);
    renderer.render(blurPlane, camera);
    blurPlane.visible = false;
  }

  // The car is static in this viewer, so the depth texture only changes when the placement does and
  // a frame after the first draw does no work at all.
  function update(target) {
    if (!enabled || !group || !group.visible || !dirty)return false;
    const background = target.background, alpha = renderer.getClearAlpha(), visible = group.visible;
    renders++;
    group.visible = false; // the ground and the shadow are not part of the depth pass
    target.background = null; // the page's backdrop would otherwise fill the target
    target.overrideMaterial = depthMaterial; // a height field of the car, seen from under its floor
    renderer.setClearAlpha(0); // a texel the car does not cover casts no shadow
    renderer.setRenderTarget(depthTarget);
    renderer.render(target, camera);
    target.overrideMaterial = null;
    target.background = background;
    renderer.setClearAlpha(alpha);
    blur(horizontal, depthTarget.texture, blurTarget, CONTACT_SHADOW.blur);
    blur(vertical, blurTarget.texture, depthTarget, CONTACT_SHADOW.blur);
    // a second, narrower pass clears the edge artifacts the first one leaves
    blur(horizontal, depthTarget.texture, blurTarget, CONTACT_SHADOW.blur * .4);
    blur(vertical, blurTarget.texture, depthTarget, CONTACT_SHADOW.blur * .4);
    renderer.setRenderTarget(null);
    group.visible = visible;
    dirty = false;
    return true;
  }

  return {
    get ground() {return ground;},
    get plane() {return plane;},
    get camera() {return camera;},
    get enabled() {return enabled;},
    get renders() {return renders;},
    setEnabled(target, next) {
      enabled = !!next;
      if (!enabled) {
        if (group && group.parent === target)target.remove(group);
        return;
      }
      if (!group)build();
      scene = target;
      if (group.parent !== scene)scene.add(group);
      place();
    },
    follow(next, quadFloor = null) {
      box = next ?? null;
      shadowFloor = Number.isFinite(quadFloor) ? quadFloor : null;
      place();
    },
    update,
    dispose() {
      if (scene && group && group.parent === scene)scene.remove(group);
      for (const object of [ground, plane])object?.material.dispose();
      depthMaterial?.dispose();
      horizontal?.dispose();
      vertical?.dispose();
      geometry?.dispose();
      depthTarget?.dispose();
      blurTarget?.dispose();
      scene = geometry = group = ground = plane = blurPlane = camera = null;
      depthMaterial = depthTarget = blurTarget = horizontal = vertical = null;
      box = null;
      shadowFloor = null;
      enabled = dirty = false;
    },
  };
}
