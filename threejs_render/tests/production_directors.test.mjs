import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { CharacterCapabilityRegistry, CAPABILITY_TIERS } from '../production/character_capability_registry.js';
import { AnimationDirector } from '../production/animation_director.js';
import { ShotDirector } from '../production/shot_director.js';
import { InteractionSystem } from '../production/interaction_system.js';
import { buildEnvironmentPlan, environmentMotionSample } from '../production/environment_motion.js';

const repo = path.resolve(import.meta.dirname, '..', '..');
const registryDocument = JSON.parse(fs.readFileSync(path.join(repo, 'assets', 'characters', 'capability_registry.json')));
const storyboard = JSON.parse(fs.readFileSync(path.join(repo, 'reports', 'sbz_adventurer_production_scene.json')));
const registry = new CharacterCapabilityRegistry(registryDocument);

test('capability tiers are explicit and Adventurer is interactive but not facial-ready', () => {
  assert.deepEqual(Object.keys(CAPABILITY_TIERS), ['STATIC', 'SKELETAL_BASIC', 'SKELETAL_INTERACTIVE', 'FACIAL_READY']);
  const character = registry.get('quaternius_adventurer');
  assert.equal(character.tier, 'SKELETAL_INTERACTIVE');
  assert.equal(character.facial.ready, false);
  assert.equal(character.facial.dialogueLipSync, false);
  assert.equal(character.skeleton.armatureName, 'QuaterniusMasterRig');
  assert.equal(character.skeleton.boneCount, 62);
  assert.equal(Object.keys(character.authoredClips).length, 28);
  assert.equal(character.license.status, 'verified');
});

test('real clip resolution is recorded and unknown semantic aliases fail closed', () => {
  const resolved = registry.resolveStoryAction('quaternius_adventurer', 'warning_point');
  assert.equal(resolved.realClip, 'Idle_Gun_Pointing');
  assert.match(resolved.disclosure, /source clip/i);
  assert.throws(() => registry.resolveStoryAction('quaternius_adventurer', 'invented_celebration'), /No recorded/);
});

test('non-facial characters reject dialogue and facial close-ups', () => {
  assert.throws(() => registry.assertShotAllowed('quaternius_adventurer', 'dialogue_close_up', { dialogue: true }), /not allowed/);
  assert.throws(() => registry.assertShotAllowed('quaternius_adventurer', 'facial_close_up'), /not allowed/);
});

test('shot director uses story purpose and never centers the character permanently', () => {
  const character = registry.get('quaternius_adventurer');
  const shot = new ShotDirector().select({ purpose: 'body_reaction' }, character, registry);
  assert.equal(shot.type, 'body_reaction_medium_close');
  assert.equal(shot.facialCloseUp, false);
  assert.equal(shot.permanentlyCentered, false);
});

test('animation director produces exact timing, real clips, displacement and camera plans', () => {
  const plan = new AnimationDirector({ registry }).compile(storyboard);
  assert.equal(plan.totalFrames, 720);
  assert.equal(plan.beats.length, 10);
  assert.equal(plan.beats.find(beat => beat.id === 'reach_and_contact').sourceClip, 'Interact');
  assert.equal(plan.beats.find(beat => beat.id === 'surprised_reaction').interruptible, true);
  assert.ok(plan.beats.find(beat => beat.id === 'quick_exit').movement.distance > 7.8);
  assert.ok(plan.beats.filter(beat => beat.movement).every(beat => beat.movement.cycleMatched));
  assert.ok(plan.beats.filter(beat => beat.movement).every(beat => beat.movement.mismatchRatio < 0.08));
  assert.equal(plan.beats.find(beat => beat.id === 'enter_path').loopCount, 3);
  assert.equal(plan.beats.find(beat => beat.id === 'reach_and_contact').interaction.triggerFrame, 330);
  assert.equal(plan.beats.find(beat => beat.id === 'notice_box').lookMode, 'head_only');
  assert.equal(plan.beats.find(beat => beat.id === 'notice_box').eyeTarget, false);
  assert.ok(plan.beats.every(beat => beat.camera.permanentlyCentered === false));
  assert.match(plan.mixerPolicy, /AnimationMixer owns animated bones/);
});

test('named interaction target validates contact without claiming hand IK', () => {
  const system = new InteractionSystem(storyboard.props);
  const character = registry.get('quaternius_adventurer');
  const plan = system.plan(character, storyboard.beats.find(beat => beat.interaction).interaction);
  const result = system.validateContact(plan, [0.78, 1.1, 0.4]);
  assert.equal(result.valid, true);
  assert.equal(result.handIKApplied, false);
  assert.equal(system.validateFacing(plan, plan.facingYaw).valid, true);
  assert.throws(() => system.getTarget('suspicious_box.missing'), /Unknown interaction target/);
});

test('locomotion mismatch and incomplete interactions fail with diagnostics', () => {
  const brokenMovement = structuredClone(storyboard);
  brokenMovement.beats.find(beat => beat.id === 'enter_path').movement.to = [4, 0, 0];
  assert.throws(() => new AnimationDirector({ registry }).compile(brokenMovement), /locomotion distance mismatch/);
  const brokenInteraction = structuredClone(storyboard);
  delete brokenInteraction.beats.find(beat => beat.interaction).interaction.triggerTime;
  assert.throws(() => new AnimationDirector({ registry }).compile(brokenInteraction), /requires triggerTime/);
});

test('environment motion is deterministic and repeated vegetation is instanced', () => {
  assert.deepEqual(environmentMotionSample(storyboard.environment, 4.25, 3, 'tree'),
    environmentMotionSample(storyboard.environment, 4.25, 3, 'tree'));
  const plan = buildEnvironmentPlan(storyboard.environment);
  assert.equal(plan.deterministic, true);
  assert.ok(plan.instancing.groups.every(group => group.useInstancedMesh));
});
