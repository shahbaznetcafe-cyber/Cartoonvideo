import test from 'node:test';
import assert from 'node:assert/strict';

import {
  FacialRuntime,
  MIXAMO_CORE_BONES,
  REQUIRED_FACIAL,
  REQUIRED_VISEMES,
  canonicalMorphName,
  computeBlinkWeight,
  gazeTargets,
  normalizeMouthWeights,
  useJawFallback,
} from '../facial_runtime.js';


function mockRoot({ morphs = [], bones = [], initial = 0 } = {}) {
  const influences = morphs.map(() => initial);
  const mesh = {
    isMesh: true,
    morphTargetDictionary: Object.fromEntries(morphs.map((name, index) => [name, index])),
    morphTargetInfluences: influences,
  };
  const boneObjects = bones.map(name => ({
    isBone: true, name, rotation: { x: 0, y: 0, z: 0 },
  }));
  return {
    mesh, boneObjects,
    traverse(callback) { callback(mesh); boneObjects.forEach(callback); },
  };
}

function timeline(weights, frames = 12) {
  return { frames: Array.from({ length: frames }, (_, frame) => ({ frame, weights })) };
}


test('normalizes exporter prefixes without confusing canonical morphs', () => {
  assert.equal(canonicalMorphName('Face|blendShape.viseme_PP'), 'viseme_PP');
  assert.equal(canonicalMorphName('Wolf3D_Head:mouthSmileLeft'), 'mouthSmileLeft');
  assert.equal(canonicalMorphName('unknownShape'), null);
});

test('detects legacy jaw rigs and full facial rigs', () => {
  const legacy = new FacialRuntime({ root: mockRoot({
    bones: ['body', 'jaw', 'arm_L', 'arm_R', 'leg_L', 'leg_R'],
  }) });
  assert.equal(legacy.tier, 'LEGACY_JAW');
  assert.equal(legacy.usesVisemes, false);
  assert.equal(legacy.blinkMode, 'none');
  assert.equal(legacy.gazeMode, 'none');

  const full = new FacialRuntime({ root: mockRoot({
    morphs: [...REQUIRED_VISEMES, ...REQUIRED_FACIAL],
    bones: MIXAMO_CORE_BONES,
  }), timeline: timeline({ viseme_sil: 1 }) });
  assert.equal(full.tier, 'FULL_FACIAL');
  assert.equal(full.usesVisemes, true);
  assert.equal(full.hasBlink, true);
  assert.equal(useJawFallback(legacy, true), true);
  assert.equal(useJawFallback(full, true), false);
  assert.equal(useJawFallback(legacy, false), false);
});

test('viseme rig falls back to jaw when its timeline is unavailable', () => {
  const runtime = new FacialRuntime({
    root: mockRoot({ morphs: REQUIRED_VISEMES, bones: ['jaw'] }),
    speaking: true,
    timeline: null,
  });
  assert.equal(runtime.usesVisemes, true);
  assert.equal(runtime.canDriveVisemes, false);
  assert.equal(useJawFallback(runtime, true), true);
});

test('listener visemes remain hard-closed even when a speech timeline exists', () => {
  const root = mockRoot({ morphs: REQUIRED_VISEMES, initial: 0.7 });
  const runtime = new FacialRuntime({
    root,
    speaking: false,
    timeline: timeline({ viseme_PP: 1 }),
  });
  for (let frame = 0; frame < 12; frame++) runtime.update(frame, 1 / 24);
  for (const name of REQUIRED_VISEMES) {
    const index = root.mesh.morphTargetDictionary[name];
    assert.equal(root.mesh.morphTargetInfluences[index], 0);
  }
});

test('speaker uses smoothed bounded visemes with a total deformation cap', () => {
  const root = mockRoot({ morphs: REQUIRED_VISEMES });
  const runtime = new FacialRuntime({
    root,
    speaking: true,
    timeline: timeline({ viseme_PP: 0.8, viseme_aa: 0.8 }),
  });
  const targets = runtime.update(1, 1 / 24);
  const targetTotal = REQUIRED_VISEMES.reduce((sum, name) => sum + (targets[name] || 0), 0);
  const appliedTotal = REQUIRED_VISEMES.reduce(
    (sum, name) => sum + root.mesh.morphTargetInfluences[root.mesh.morphTargetDictionary[name]], 0);
  assert.ok(Math.abs(targetTotal - 0.92) < 1e-8);
  assert.ok(appliedTotal > 0 && appliedTotal < targetTotal);
  assert.ok(root.mesh.morphTargetInfluences.every(value => value >= 0 && value <= 1));
});

test('blink is deterministic, paired, bounded, and combined by max', () => {
  let peakTime = 0, peak = 0;
  for (let time = 0; time < 8; time += 0.01) {
    const value = computeBlinkWeight(time, 2.3);
    if (value > peak) { peak = value; peakTime = time; }
  }
  assert.ok(peak > 0.99);
  const runtime = new FacialRuntime({
    root: mockRoot({ morphs: [...REQUIRED_VISEMES, ...REQUIRED_FACIAL] }),
    emotion: 'surprise', seed: 2.3,
  });
  const targets = runtime.composeTargets(0, peakTime);
  assert.equal(targets.eyeBlinkLeft, targets.eyeBlinkRight);
  assert.ok(targets.eyeBlinkLeft <= 1);
  assert.equal(targets.eyeBlinkLeft, peak);
});

test('gaze mapping is bounded and drives eye bones smoothly', () => {
  const gaze = gazeTargets(3, -2);
  assert.equal(gaze.eyeLookInLeft, 0.32);
  assert.equal(gaze.eyeLookDownLeft, 0.28);
  const root = mockRoot({ bones: ['LeftEye', 'RightEye', 'Head'] });
  const runtime = new FacialRuntime({ root });
  assert.equal(runtime.gazeMode, 'bones');
  runtime.update(0, 1 / 24, { gazeX: 1, gazeY: -1 });
  assert.ok(Math.abs(root.boneObjects[0].rotation.y) <= 6 * Math.PI / 180);
  assert.ok(Math.abs(root.boneObjects[2].rotation.y) <= 2.5 * Math.PI / 180);
});

test('mouth normalization is deterministic and never exceeds its limit', () => {
  const first = normalizeMouthWeights({ viseme_PP: 1, viseme_FF: 1, viseme_aa: 1 });
  const second = normalizeMouthWeights({ viseme_PP: 1, viseme_FF: 1, viseme_aa: 1 });
  assert.deepEqual(first, second);
  assert.ok(REQUIRED_VISEMES.reduce((sum, name) => sum + first[name], 0) <= 0.9200001);
});
