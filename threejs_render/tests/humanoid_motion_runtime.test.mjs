import assert from 'node:assert/strict';
import {
  humanoidClipTime,
  isHumanoidPositionTrack,
  selectHumanoidClip,
} from '../humanoid_motion_runtime.js';

const clips = [
  { name: 'Idle', duration: 6 },
  { name: 'Talking', duration: 10 },
  { name: 'Walking', duration: 2 },
];

assert.equal(selectHumanoidClip(clips, { speaking: false }).name, 'Idle');
assert.equal(selectHumanoidClip(clips, { speaking: true }).name, 'Talking');
assert.equal(selectHumanoidClip(clips, { action: 'walk' }).name, 'Walking');
assert.equal(selectHumanoidClip([], { speaking: true }), null);
assert.equal(humanoidClipTime(12.5, 10), 2.5);
assert.equal(humanoidClipTime(-1, 10), 9);
assert.equal(humanoidClipTime(5, 0), 0);
assert.equal(isHumanoidPositionTrack('mixamorig:Hips.position'), true);
assert.equal(isHumanoidPositionTrack('mixamorigHips.position'), true);
assert.equal(isHumanoidPositionTrack('mixamorig:Spine.position'), true);
assert.equal(isHumanoidPositionTrack('mixamorig:Head.quaternion'), false);

console.log('humanoid_motion_runtime tests passed');
