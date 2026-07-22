import assert from 'node:assert/strict';
import {
  humanoidClipTime,
  isHumanoidPositionTrack,
  selectHumanoidClip,
  isProneClip,
} from '../humanoid_motion_runtime.js';

const clips = [
  { name: 'Idle', duration: 6 },
  { name: 'Talking', duration: 10 },
  { name: 'Walking', duration: 2 },
  { name: 'Wave', duration: 1.5 },
  { name: 'Victory', duration: 1.8 },
  { name: 'Pickup', duration: 1.2 },
  { name: 'Yes', duration: 1.0 },
];

assert.equal(selectHumanoidClip(clips, { speaking: false }).name, 'Idle');
assert.equal(selectHumanoidClip(clips, { speaking: true }).name, 'Talking');
assert.equal(selectHumanoidClip(clips, { action: 'walk' }).name, 'Walking');
assert.equal(selectHumanoidClip(clips, { action: 'hello' }).name, 'Wave');
assert.equal(selectHumanoidClip(clips, { action: 'win' }).name, 'Victory');
assert.equal(selectHumanoidClip(clips, { action: 'reach' }).name, 'Pickup');
assert.equal(selectHumanoidClip(clips, { action: 'nod' }).name, 'Yes');
assert.equal(selectHumanoidClip(clips, { action: 'walk', sourceClip: 'Wave' }).name, 'Wave');
assert.equal(selectHumanoidClip([], { speaking: true }), null);
assert.equal(humanoidClipTime(12.5, 10), 2.5);
assert.equal(humanoidClipTime(-1, 10), 9);
assert.equal(humanoidClipTime(5, 0), 0);
assert.equal(isHumanoidPositionTrack('mixamorig:Hips.position'), true);
assert.equal(isHumanoidPositionTrack('mixamorigHips.position'), true);
assert.equal(isHumanoidPositionTrack('mixamorig:Spine.position'), true);
assert.equal(isHumanoidPositionTrack('mixamorig:Head.quaternion'), false);

// --- prone-clip guard: a speaking character must never lie down ---
const grafted = [
  { name: 'Idle', duration: 6 },
  { name: 'Talking', duration: 10 },
  { name: 'Death', duration: 3 },
  { name: 'Defeat', duration: 3 },
  { name: 'Roll', duration: 1.5 },
  { name: 'RecieveHit', duration: 1 },
];
assert.equal(isProneClip({ name: 'Death' }), true);
assert.equal(isProneClip({ name: 'RecieveHit' }), true);
assert.equal(isProneClip({ name: 'Talking' }), false);
// Speaking: an explicit prone sourceClip is ignored, upright clip chosen.
assert.equal(selectHumanoidClip(grafted, { speaking: true, sourceClip: 'Death' }).name, 'Talking');
// Speaking: a fall/hit action can no longer floor the narrator.
assert.equal(selectHumanoidClip(grafted, { speaking: true, action: 'fall' }).name, 'Talking');
assert.equal(selectHumanoidClip(grafted, { speaking: true, action: 'hit' }).name, 'Talking');
// Non-speaking: a directed hit reaction still resolves to the real clip.
assert.equal(selectHumanoidClip(grafted, { speaking: false, action: 'hit' }).name, 'RecieveHit');
// A clip-less-of-upright edge case falls back rather than returning null.
assert.ok(selectHumanoidClip([{ name: 'Death', duration: 3 }], { speaking: true }));

console.log('humanoid_motion_runtime tests passed');
