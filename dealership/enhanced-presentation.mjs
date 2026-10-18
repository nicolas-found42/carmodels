import * as THREE from './vendor/three.module.js';
import {createGT4Studio} from './gt4-studio.mjs';
import {isRecoveredUnderShadow} from './materials.mjs';

// Enhanced is a deliberate departure from the recovered game look, so its values are
// published as `enhanced`, never as a recovery claim. The numbers are a judgement call;
// the reasoning and sources are recorded in research/enhanced-presentation-2026-10-18.md.
export const ENHANCED_PRESENTATION = Object.freeze({
  environmentIntensity: .8, // the existing asset-free studio environment, at its own intensity
  exposure: 1,
  roughness: .35, // glossy paint: a broad, soft highlight over the recovered texture
  metalness: 0, // recovered albedo stays the pigment; the lacquer is the clearcoat
  clearcoat: 1,
  clearcoatRoughness: .06, // soft reflections rather than a mirror
  label: 'Enhanced presentation — not the original game\'s look: asset-free environment ' +
    'reflections, a glossy clearcoat on textured parts and neutral tone mapping. The recovered ' +
    'materials and the download are unchanged.',
});

const MODES = new Set(['original', 'enhanced']);

export function presentationMode(value) {
  if(!MODES.has(value))throw Error('Unknown presentation. Use original or enhanced.');
  return value;
}

// Only textured, opaque coverage takes the clearcoat. Untextured header-coloured parts
// keep their recovered appearance, and blended windows stay unglossed; tyres are
// textured, so they are glossier than the original until parts can be told apart
// (issue #22 records that gap). The recovered under-car shadow is excluded as well: its
// texture is an alpha coverage decal rather than an opaque surface, so a clearcoat would
// replace its candidate alpha blend with a reflective sheet. Its blend therefore reads the
// same in both presentation modes; only the scene's environment and tone mapping change
// (research/under-car-shadow.md).
export function isTexturedOpaque(source) {
  return source?.pbrMetallicRoughness?.baseColorTexture?.index !== undefined && source.alphaMode !== 'BLEND' &&
    !isRecoveredUnderShadow(source);
}

// Original is the default and leaves the renderer and the scene exactly as they were at
// construction. Enhanced reuses the existing asset-free studio environment
// (dealership/gt4-studio.mjs): no vendored helper, no HDRI and no network request.
export function createPresentation(renderer, scene, {studio=createGT4Studio(renderer)}={}) {
  const original = {
    toneMapping: renderer.toneMapping,
    toneMappingExposure: renderer.toneMappingExposure,
    environment: scene.environment,
    environmentIntensity: scene.environmentIntensity,
  };
  let mode = 'original';
  function setMode(value) {
    const next = presentationMode(value);
    // Original before any change is byte-for-byte today's state, so switching to the
    // mode already selected must not touch the renderer or the scene.
    if(next === mode)return mode;
    mode = next;
    const enhanced = mode === 'enhanced';
    studio.setEnabled(scene, enhanced);
    // The studio's ACES default is replaced by the neutral mapper so recovered liveries
    // keep their base hue (research/visual-fidelity-modern-pipeline-options.md §2).
    renderer.toneMapping = enhanced ? THREE.NeutralToneMapping : original.toneMapping;
    renderer.toneMappingExposure = enhanced ? ENHANCED_PRESENTATION.exposure : original.toneMappingExposure;
    scene.environmentIntensity = enhanced ? ENHANCED_PRESENTATION.environmentIntensity : original.environmentIntensity;
    if(!enhanced)scene.environment = original.environment;
    return mode;
  }
  // Called after every material update, because the paint pipeline rewrites roughness and
  // metalness from recovered factors and clears clearcoat. A material that already carries an
  // authored clearcoat (the GT4 refinement's) keeps it: Enhanced adds gloss where the
  // recovered material has none instead of replacing a deliberate finish.
  function finish(material, source) {
    if(mode !== 'enhanced' || !material.isMeshPhysicalMaterial || !isTexturedOpaque(source) || material.clearcoat > 0)return material;
    material.roughness = ENHANCED_PRESENTATION.roughness;
    material.metalness = ENHANCED_PRESENTATION.metalness;
    material.clearcoat = ENHANCED_PRESENTATION.clearcoat; // crossing zero rebuilds the program by itself
    material.clearcoatRoughness = ENHANCED_PRESENTATION.clearcoatRoughness;
    return material;
  }
  return {
    setMode, finish,
    get mode() {return mode;},
    get enhanced() {return mode === 'enhanced';},
    get label() {return mode === 'enhanced' ? ENHANCED_PRESENTATION.label : '';},
    dispose() {studio.dispose();},
  };
}
