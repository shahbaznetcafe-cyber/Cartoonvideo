import fs from 'node:fs';
import path from 'node:path';
import { CharacterCapabilityRegistry } from './character_capability_registry.js';
import { AnimationDirector } from './animation_director.js';

const repo = path.resolve(process.argv[2] || path.join(import.meta.dirname, '..', '..'));
const registryPath = path.join(repo, 'assets', 'characters', 'capability_registry.json');
const storyboardPath = path.join(repo, 'reports', 'sbz_adventurer_production_scene.json');
const registry = new CharacterCapabilityRegistry(JSON.parse(fs.readFileSync(registryPath)));
const storyboard = JSON.parse(fs.readFileSync(storyboardPath));
const plan = new AnimationDirector({ registry }).compile(storyboard);
const planPath = path.join(repo, 'reports', 'adventurer_directed_execution_plan.json');
const mappingPath = path.join(repo, 'reports', 'adventurer_production_clip_mapping.json');

const mapping = {
  schemaVersion: 1,
  characterId: storyboard.characterId,
  policy: 'Every semantic action resolves to a recorded authored GLB clip. Unknown actions fail closed.',
  facialReady: plan.character.facial.ready,
  eyeTargetClaimed: false,
  handIKApplied: false,
  beats: plan.beats.map(beat => ({
    beatId: beat.id,
    storyAction: beat.storyAction,
    realSourceClip: beat.sourceClip,
    sourceClipDurationSeconds: beat.sourceClipDurationSeconds,
    clipStartSeconds: beat.clipStartSeconds,
    clipEndSeconds: beat.clipEndSeconds,
    loopCount: beat.loopCount,
    crossfadeSeconds: beat.crossfadeSeconds,
    interruptible: beat.interruptible,
    disclosure: beat.clipDisclosure,
    movement: beat.movement,
    facingYawRadians: beat.facingYaw,
    lookMode: beat.lookMode,
    eyeTarget: beat.eyeTarget,
    propTarget: beat.interaction?.target || null,
    triggerTime: beat.interaction?.triggerTime ?? null,
    triggerFrame: beat.interaction?.triggerFrame ?? null,
    consequenceEvent: beat.interaction?.consequenceEvent || null,
    cameraIntent: beat.camera,
    environmentEvents: beat.environmentEvents,
  })),
};

fs.writeFileSync(planPath, `${JSON.stringify(plan, null, 2)}\n`);
fs.writeFileSync(mappingPath, `${JSON.stringify(mapping, null, 2)}\n`);
console.log(`PRODUCTION_PLAN_EXPORTED beats=${plan.beats.length} frames=${plan.totalFrames}`);
