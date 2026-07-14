/**
 * Bind-pose-relative animation helpers for SBZ legacy and skeletal characters.
 *
 * glTF bone rotations are the character's local rest transforms. Animation
 * values in SBZ are deltas and must never replace those imported transforms.
 */

const CONTROLLED_BONES = ['jaw', 'arm_L', 'arm_R', 'leg_L', 'leg_R', 'body'];

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function captureBoneBases(bones = {}) {
  const result = {};
  for (const name of CONTROLLED_BONES) {
    const bone = bones[name];
    if (!bone || !bone.rotation) continue;
    result[name] = {
      x: finite(bone.rotation.x),
      y: finite(bone.rotation.y),
      z: finite(bone.rotation.z),
      order: bone.rotation.order || 'XYZ',
    };
  }
  return result;
}

export function applyBoneDelta(bone, base, delta = {}) {
  if (!bone || !bone.rotation || !base) return false;
  const x = base.x + finite(delta.x);
  const y = base.y + finite(delta.y);
  const z = base.z + finite(delta.z);
  if (typeof bone.rotation.set === 'function') bone.rotation.set(x, y, z, base.order);
  else {
    bone.rotation.x = x;
    bone.rotation.y = y;
    bone.rotation.z = z;
    if ('order' in bone.rotation) bone.rotation.order = base.order;
  }
  return true;
}

export function jawOpenDelta(openness, maximumRadians = 0.19) {
  const amount = Math.max(0, Math.min(1, finite(openness)));
  if (amount === 0) return 0;
  return -Math.max(0, finite(maximumRadians)) * Math.pow(amount, 0.85);
}

export function applyLegacyPose(bones, bases, pose = {}) {
  const DEG = Math.PI / 180;
  applyBoneDelta(bones.arm_L, bases.arm_L, { z: finite(pose.armL) * DEG });
  applyBoneDelta(bones.arm_R, bases.arm_R, { z: finite(pose.armR) * DEG });
  applyBoneDelta(bones.leg_L, bases.leg_L, { x: finite(pose.legL) * DEG });
  applyBoneDelta(bones.leg_R, bases.leg_R, { x: finite(pose.legR) * DEG });
  applyBoneDelta(bones.body, bases.body, {
    x: finite(pose.bodyX) * DEG,
    y: finite(pose.bodyY) * DEG,
    z: finite(pose.bodyZ) * DEG,
  });
  applyBoneDelta(bones.jaw, bases.jaw, { x: finite(pose.jaw) });
}
