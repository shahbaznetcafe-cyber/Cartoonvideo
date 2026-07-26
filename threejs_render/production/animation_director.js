import { ShotDirector } from './shot_director.js';
import { InteractionSystem, distance3 } from './interaction_system.js';
import { buildEnvironmentPlan } from './environment_motion.js';

const finite = value => Number.isFinite(Number(value));

export class AnimationDirector {
  constructor({ registry, shotDirector = new ShotDirector() } = {}) {
    if (!registry) throw new Error('AnimationDirector requires a capability registry');
    this.registry = registry;
    this.shotDirector = shotDirector;
  }

  compile(storyboard) {
    if (!storyboard || !Array.isArray(storyboard.beats) || !storyboard.beats.length) {
      throw new Error('Storyboard must contain beats');
    }
    const fps = Number(storyboard.fps);
    const durationSeconds = Number(storyboard.durationSeconds);
    if (!finite(fps) || !finite(durationSeconds) || fps <= 0 || durationSeconds <= 0) {
      throw new Error('Storyboard timing is invalid');
    }
    const character = this.registry.get(storyboard.characterId);
    const interactions = new InteractionSystem(storyboard.props || []);
    const beats = storyboard.beats.map((beat, index) => {
      const clip = this.registry.resolveStoryAction(character.id, beat.storyAction);
      const clipMetadata = character.authoredClips[clip.realClip];
      const camera = this.shotDirector.select({ purpose: beat.purpose,
        requestedShot: beat.requestedShot || null, dialogue: Boolean(beat.dialogue) }, character, this.registry);
      let movement = null;
      if (beat.movement) {
        const profile = character.locomotionProfiles?.[clip.realClip];
        const clipCycles = Number(beat.movement.clipCycles);
        if (!profile || !Number.isInteger(clipCycles) || clipCycles < 1) {
          throw new Error(`${beat.id} requires a registered locomotion profile and whole clipCycles`);
        }
        const from = beat.movement.from.map(Number);
        const to = beat.movement.to.map(Number);
        const distance = distance3(from, to);
        const expectedDistance = profile.worldUnitsPerCycle * clipCycles;
        const mismatchRatio = Math.abs(distance - expectedDistance) / Math.max(0.001, expectedDistance);
        if (mismatchRatio > profile.maximumDistanceMismatchRatio) {
          throw new Error(`${beat.id} locomotion distance mismatch ${(mismatchRatio * 100).toFixed(2)}% exceeds registered tolerance`);
        }
        const beatDuration = Math.max(0.001, Number(beat.end) - Number(beat.start));
        movement = { from, to, distance, expectedDistance, mismatchRatio,
          maximumMismatchRatio: profile.maximumDistanceMismatchRatio,
          worldUnitsPerSecond: distance / beatDuration,
          worldUnitsPerCycle: distance / clipCycles,
          registeredWorldUnitsPerCycle: profile.worldUnitsPerCycle,
          clipCycles,
          clipTimeScale: clipMetadata.durationSeconds * clipCycles / beatDuration,
          cycleMatched: true,
          rootMotionTreatment: character.rootMotion.treatment };
      }
      const interaction = beat.interaction ? interactions.plan(character, beat.interaction) : null;
      if (interaction && interaction.realClip !== clip.realClip) {
        throw new Error(`${beat.id} interaction requires ${interaction.realClip}, got ${clip.realClip}`);
      }
      const reaction = beat.purpose === 'body_reaction';
      return {
        ...beat,
        index,
        startFrame: Math.round(Number(beat.start) * fps),
        endFrame: Math.round(Number(beat.end) * fps),
        clipStartSeconds: Number(beat.start),
        clipEndSeconds: Number(beat.end),
        sourceClip: clip.realClip,
        sourceClipDurationSeconds: clipMetadata.durationSeconds,
        clipDisclosure: clip.disclosure,
        loop: beat.loop !== false && !reaction && !interaction,
        clampWhenFinished: reaction || Boolean(interaction),
        crossfadeSeconds: Number(beat.crossfadeSeconds) || 0.24,
        interruptible: reaction || beat.interruptible === true,
        loopCount: movement?.clipCycles || (beat.loop === false || reaction || interaction ? 1
          : Math.max(1, Math.ceil((Number(beat.end) - Number(beat.start)) / clipMetadata.durationSeconds))),
        movement,
        camera,
        interaction,
        environmentEvents: structuredClone(beat.environmentEvents || []),
      };
    });
    for (let index = 0; index < beats.length; index++) {
      const beat = beats[index];
      if (beat.startFrame !== (index ? beats[index - 1].endFrame : 0)) {
        throw new Error(`Non-contiguous storyboard beat: ${beat.id}`);
      }
    }
    if (beats.at(-1).endFrame !== Math.round(durationSeconds * fps)) {
      throw new Error('Storyboard beats do not cover the exact scene duration');
    }
    let cursor = beats.find(beat => beat.movement)?.movement?.from || [0, 0, 0];
    let previousYaw = 0;
    for (const beat of beats) {
      const startPosition = beat.movement?.from || beat.interaction?.characterPosition || cursor;
      const endPosition = beat.movement?.to || beat.interaction?.characterPosition || startPosition;
      const facingTarget = beat.facingTarget || beat.interaction?.target?.position || beat.movement?.to || null;
      const facingOrigin = beat.movement ? beat.movement.from : endPosition;
      const facingYaw = facingTarget
        ? Math.atan2(facingTarget[0] - facingOrigin[0], facingTarget[2] - facingOrigin[2])
        : previousYaw;
      beat.startPosition = [...startPosition];
      beat.endPosition = [...endPosition];
      beat.startFacingYaw = previousYaw;
      beat.facingYaw = facingYaw;
      beat.lookTarget = beat.lookTarget ? [...beat.lookTarget] : null;
      beat.lookMode = beat.lookTarget && character.skeletonMapping?.head ? 'head_only' : 'none';
      beat.eyeTarget = false;
      cursor = [...endPosition];
      previousYaw = facingYaw;
    }
    return {
      schemaVersion: 1,
      generatedBy: 'SBZ Animation Director',
      fps,
      durationSeconds,
      totalFrames: Math.round(durationSeconds * fps),
      character,
      beats,
      environment: buildEnvironmentPlan(storyboard.environment),
      mixerPolicy: 'AnimationMixer owns animated bones; directors modify holder/world transforms only.',
      handIKImplemented: false,
    };
  }
}

export class MixerClipController {
  constructor({ mixer, clips, three }) {
    this.mixer = mixer;
    this.clips = clips;
    this.three = three;
    this.currentAction = null;
    this.currentBeat = null;
  }

  play(beat, timeScale = 1) {
    const clip = this.clips[beat.sourceClip];
    if (!clip) throw new Error(`Real source clip missing from GLB: ${beat.sourceClip}`);
    const next = this.mixer.clipAction(clip);
    next.enabled = true;
    next.reset();
    next.setEffectiveWeight(1);
    next.setEffectiveTimeScale(timeScale);
    next.clampWhenFinished = beat.clampWhenFinished;
    next.setLoop(beat.loop ? this.three.LoopRepeat : this.three.LoopOnce, beat.loop ? Infinity : 1);
    next.play();
    if (this.currentAction && this.currentAction !== next) {
      this.currentAction.crossFadeTo(next, beat.crossfadeSeconds, true);
    }
    this.currentAction = next;
    this.currentBeat = beat;
    return next;
  }

  interruptWith(beat, timeScale = 1) {
    if (!beat.interruptible) throw new Error(`Beat is not interruptible: ${beat.id}`);
    return this.play(beat, timeScale);
  }
}
