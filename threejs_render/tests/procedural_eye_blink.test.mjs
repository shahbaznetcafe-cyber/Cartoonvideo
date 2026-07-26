import assert from 'node:assert';
import { eyeBlinkBlend, collectEyeMaterials, ProceduralEyeBlink }
  from '../facial_runtime.js';

// --- eyeBlinkBlend: deterministic, bounded, emotion squint floor ---
for (let t = 0; t < 20; t += 0.1) {
  const w = eyeBlinkBlend(t, 5, 'neutral');
  assert.ok(w >= 0 && w <= 1, `blend in range at ${t}`);
}
// Same seed+time is reproducible; different seeds diverge somewhere.
assert.equal(eyeBlinkBlend(4.2, 7, 'neutral'), eyeBlinkBlend(4.2, 7, 'neutral'));
// Angry keeps a persistent squint floor even between blinks.
const anyOpenNeutral = [];
const anyOpenAngry = [];
for (let t = 0; t < 6; t += 0.05) {
  anyOpenNeutral.push(eyeBlinkBlend(t, 3, 'neutral'));
  anyOpenAngry.push(eyeBlinkBlend(t, 3, 'angry'));
}
assert.equal(Math.min(...anyOpenNeutral), 0, 'neutral fully opens between blinks');
assert.ok(Math.min(...anyOpenAngry) >= 0.34, 'angry never fully opens (squint)');

// --- fake three.js material/mesh graph ---
function color(r, g, b) {
  return { r, g, b, clone() { return color(this.r, this.g, this.b); } };
}
function material(name, c) {
  return { name, color: c, clone() { return material(this.name, this.color.clone()); } };
}
function root(materials) {
  const meshes = materials.map(m => ({ isMesh: true, material: m }));
  return { traverse(fn) { meshes.forEach(fn); }, _meshes: meshes };
}

const skin = material('Skin', color(0.62, 0.42, 0.24));
const eye = material('Eye', color(0.03, 0.02, 0.01));
const graph = root([skin, eye]);

const found = collectEyeMaterials(graph);
assert.equal(found.eyes.length, 1, 'eye material detected');
assert.ok(found.skin, 'skin material detected');

const blink = new ProceduralEyeBlink({ root: graph, seed: 3, emotion: 'neutral' });
assert.ok(blink.enabled, 'blink enabled when eyes present');
blink.attach(graph);
// Cloned material replaced the original on the mesh (no cross-character tint).
const eyeMesh = graph._meshes.find(m => m.material.name === 'Eye');
assert.notStrictEqual(eyeMesh.material, eye, 'eye material was cloned & swapped');

// At a fully-closed blink frame the eye colour blends toward skin.
let maxTowardSkin = 0;
for (let t = 0; t < 6; t += 0.02) {
  blink.update(t);
  maxTowardSkin = Math.max(maxTowardSkin, eyeMesh.material.color.r);
}
assert.ok(maxTowardSkin > 0.4, 'eye reddens toward skin tone during a blink');

// A rig with no eye material disables cleanly.
const noEyes = new ProceduralEyeBlink({ root: root([skin]), seed: 1 });
assert.equal(noEyes.enabled, false, 'disabled without eye material');
assert.equal(noEyes.update(1), 0, 'no-op update returns 0');

console.log('procedural_eye_blink tests passed');
