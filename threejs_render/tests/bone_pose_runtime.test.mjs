import test from 'node:test';
import assert from 'node:assert/strict';

import {
  applyBoneDelta,
  applyLegacyPose,
  captureBoneBases,
  jawOpenDelta,
} from '../bone_pose_runtime.js';

function bone(x = 0, y = 0, z = 0) {
  return {
    rotation: {
      x, y, z, order: 'XYZ',
      set(nx, ny, nz, order) { this.x = nx; this.y = ny; this.z = nz; this.order = order; },
    },
  };
}

test('captures and preserves non-zero imported rest rotations', () => {
  const bones = { jaw: bone(1.98, 0.03, -0.02), leg_L: bone(2.82, 0.14, 0.11) };
  const bases = captureBoneBases(bones);
  applyBoneDelta(bones.jaw, bases.jaw, { x: -0.1 });
  applyBoneDelta(bones.leg_L, bases.leg_L, { x: 3 * Math.PI / 180 });
  assert.ok(Math.abs(bones.jaw.rotation.x - 1.88) < 1e-10);
  assert.equal(bones.jaw.rotation.y, 0.03);
  assert.ok(Math.abs(bones.leg_L.rotation.x - (2.82 + 3 * Math.PI / 180)) < 1e-10);
  assert.equal(bones.leg_L.rotation.y, 0.14);
  assert.equal(bones.leg_L.rotation.z, 0.11);
});

test('legacy pose values are deltas and listener jaw returns to its base', () => {
  const bones = {
    jaw: bone(2.04), arm_L: bone(0.1, 0.2, 0.3), arm_R: bone(-0.1, 0.2, -0.3),
    leg_L: bone(2.8, 0.1, 0.2), leg_R: bone(2.9, -0.1, -0.2), body: bone(0.2, 0.3, 0.4),
  };
  const bases = captureBoneBases(bones);
  applyLegacyPose(bones, bases, { armL: 8, armR: -8, legL: 3, legR: -3,
    bodyX: 2, bodyY: 4, bodyZ: 1, jaw: jawOpenDelta(1) });
  assert.ok(bones.jaw.rotation.x < bases.jaw.x);
  applyLegacyPose(bones, bases, {});
  for (const [name, base] of Object.entries(bases)) {
    assert.equal(bones[name].rotation.x, base.x, name);
    assert.equal(bones[name].rotation.y, base.y, name);
    assert.equal(bones[name].rotation.z, base.z, name);
  }
});

test('jaw curve is closed at silence and bounded at maximum speech', () => {
  assert.equal(jawOpenDelta(0), 0);
  assert.equal(jawOpenDelta(-1), 0);
  assert.ok(Math.abs(jawOpenDelta(1) + 0.19) < 1e-10);
  assert.ok(jawOpenDelta(0.5) < 0 && jawOpenDelta(0.5) > -0.19);
});

