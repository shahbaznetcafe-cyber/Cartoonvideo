/**
 * SBZ Three.js facial animation runtime.
 *
 * Morph baseline, acceleration, velocity-limit, blink, and gaze concepts were
 * informed by TalkingHead by Mika Suominen (MIT). This is an SBZ-specific
 * implementation; attribution is preserved in ../THIRD_PARTY_NOTICES.md.
 */

export const REQUIRED_VISEMES = [
  'viseme_sil', 'viseme_PP', 'viseme_FF', 'viseme_TH', 'viseme_DD',
  'viseme_kk', 'viseme_CH', 'viseme_SS', 'viseme_nn', 'viseme_RR',
  'viseme_aa', 'viseme_E', 'viseme_I', 'viseme_O', 'viseme_U',
];

export const REQUIRED_FACIAL = [
  'eyeBlinkLeft', 'eyeBlinkRight', 'browInnerUp', 'browDownLeft',
  'browDownRight', 'mouthSmileLeft', 'mouthSmileRight',
  'mouthFrownLeft', 'mouthFrownRight',
];

export const MIXAMO_CORE_BONES = [
  'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
  'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
  'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
  'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg', 'RightFoot',
];

const EYE_LOOK = [
  'eyeLookDownLeft', 'eyeLookDownRight', 'eyeLookInLeft', 'eyeLookInRight',
  'eyeLookOutLeft', 'eyeLookOutRight', 'eyeLookUpLeft', 'eyeLookUpRight',
];
const KNOWN_MORPHS = [...REQUIRED_VISEMES, ...REQUIRED_FACIAL, ...EYE_LOOK,
  'eyeSquintLeft', 'eyeSquintRight', 'eyeWideLeft', 'eyeWideRight', 'jawOpen'];
const MORPH_KEYS = [...KNOWN_MORPHS].sort((a, b) => normalizeName(b).length - normalizeName(a).length);
const DEG = Math.PI / 180;

export function clamp(value, minimum = 0, maximum = 1) {
  return Math.max(minimum, Math.min(maximum, Number.isFinite(value) ? value : minimum));
}

export function smoothstep(value) {
  const x = clamp(value);
  return x * x * (3 - 2 * x);
}

export function normalizeName(value) {
  let name = String(value || '').trim().replace(/^.*[|/:\\]/, '');
  name = name.replace(/^mixamorig[_:.-]*/i, '');
  return name.toLowerCase().replace(/[^a-z0-9]/g, '');
}

export function canonicalMorphName(rawName) {
  const key = normalizeName(rawName);
  for (const canonical of MORPH_KEYS) {
    const wanted = normalizeName(canonical);
    if (key === wanted || key.endsWith(wanted)) return canonical;
  }
  return null;
}

export function collectMorphTargets(root) {
  const result = new Map();
  if (!root || typeof root.traverse !== 'function') return result;
  root.traverse(object => {
    const dictionary = object && object.morphTargetDictionary;
    const influences = object && object.morphTargetInfluences;
    if (!dictionary || !influences) return;
    for (const [rawName, rawIndex] of Object.entries(dictionary)) {
      const canonical = canonicalMorphName(rawName);
      const index = Number(rawIndex);
      if (!canonical || !Number.isInteger(index) || index < 0 || index >= influences.length) continue;
      if (!result.has(canonical)) result.set(canonical, []);
      result.get(canonical).push({ object, influences, index, rawName });
    }
  });
  return result;
}

export function collectBones(root) {
  const result = new Map();
  if (!root || typeof root.traverse !== 'function') return result;
  root.traverse(object => {
    if (object && object.isBone && object.name) result.set(normalizeName(object.name), object);
  });
  return result;
}

export function boneByName(bones, name) {
  return bones instanceof Map ? bones.get(normalizeName(name)) || null : null;
}

export function detectAnimationTier(morphs, bones) {
  const has = name => morphs instanceof Map && morphs.has(name);
  const bone = name => bones instanceof Map && bones.has(normalizeName(name));
  const allVisemes = REQUIRED_VISEMES.every(has);
  const allFacial = REQUIRED_FACIAL.every(has);
  const mixamo = MIXAMO_CORE_BONES.every(bone);
  if (allVisemes && allFacial) return 'FULL_FACIAL';
  if (allVisemes) return 'VISEME_FACE';
  if (mixamo || ([...bones.values()].length > 0 && !bone('jaw'))) return 'SKELETAL_BASIC';
  if (bone('jaw')) return 'LEGACY_JAW';
  return null;
}

function hashUnit(seed) {
  const value = Math.sin((Number(seed) || 0) * 12.9898 + 78.233) * 43758.5453;
  return value - Math.floor(value);
}

export function computeBlinkWeight(time, seed = 0) {
  const random = hashUnit(seed + 1.37);
  const period = 3.1 + random * 2.2;
  const firstDelay = 1.0 + random * 1.5;
  const phase = ((Math.max(0, time) + period - firstDelay) % period + period) % period;
  const close = 0.060, hold = 0.035, open = 0.105;
  if (phase < close) return smoothstep(phase / close);
  if (phase < close + hold) return 1;
  if (phase < close + hold + open) return 1 - smoothstep((phase - close - hold) / open);
  return 0;
}

export function emotionTargets(emotion, speaking = false) {
  const aliases = { excited: 'happy', joy: 'happy', cheerful: 'happy', scared: 'fear',
    afraid: 'fear', worried: 'fear', shocked: 'surprise', amazed: 'surprise',
    mad: 'angry', upset: 'sad', crying: 'sad' };
  const name = aliases[String(emotion || 'neutral').toLowerCase()] || String(emotion || 'neutral').toLowerCase();
  const amount = speaking ? 0.58 : 1;
  const table = {
    happy: { mouthSmileLeft: .48 * amount, mouthSmileRight: .48 * amount, browInnerUp: .08 },
    sad: { mouthFrownLeft: .44 * amount, mouthFrownRight: .44 * amount, browInnerUp: .34 },
    angry: { browDownLeft: .55, browDownRight: .55, mouthFrownLeft: .18 * amount, mouthFrownRight: .18 * amount },
    surprise: { browInnerUp: .68, eyeWideLeft: .32, eyeWideRight: .32 },
    fear: { browInnerUp: .46, mouthFrownLeft: .26 * amount, mouthFrownRight: .26 * amount, eyeWideLeft: .20, eyeWideRight: .20 },
  };
  return { ...(table[name] || {}) };
}

export function gazeTargets(gazeX = 0, gazeY = 0) {
  const x = clamp(gazeX, -1, 1), y = clamp(gazeY, -1, 1);
  const result = {};
  if (x > 0.01) {
    result.eyeLookInLeft = x * .32; result.eyeLookOutRight = x * .32;
  } else if (x < -0.01) {
    result.eyeLookOutLeft = -x * .32; result.eyeLookInRight = -x * .32;
  }
  if (y > 0.01) {
    result.eyeLookUpLeft = y * .28; result.eyeLookUpRight = y * .28;
  } else if (y < -0.01) {
    result.eyeLookDownLeft = -y * .28; result.eyeLookDownRight = -y * .28;
  }
  return result;
}

export function sampleTimeline(timeline, frame) {
  if (!timeline || !Array.isArray(timeline.frames) || !timeline.frames.length) return {};
  const index = Math.max(0, Math.min(timeline.frames.length - 1, Math.floor(frame)));
  const weights = timeline.frames[index] && timeline.frames[index].weights;
  if (!weights || typeof weights !== 'object') return {};
  const result = {};
  for (const name of REQUIRED_VISEMES) {
    if (Number.isFinite(Number(weights[name]))) result[name] = clamp(Number(weights[name]));
  }
  return result;
}

export function normalizeMouthWeights(weights, maximum = 0.92) {
  const result = {};
  let total = 0;
  for (const name of REQUIRED_VISEMES) {
    const value = clamp(Number(weights && weights[name]) || 0);
    result[name] = value;
    total += value;
  }
  const scale = total > maximum && total > 0 ? maximum / total : 1;
  for (const name of REQUIRED_VISEMES) result[name] = result[name] * scale;
  return result;
}

export function useJawFallback(facialRuntime, speaking) {
  return Boolean(speaking && !(facialRuntime && facialRuntime.canDriveVisemes));
}

function morphDynamics(name) {
  if (name.startsWith('eyeBlink')) return { acceleration: 220, maxVelocity: 28 };
  if (name.startsWith('viseme_')) return { acceleration: 95, maxVelocity: 15 };
  if (name.startsWith('eyeLook')) return { acceleration: 55, maxVelocity: 8 };
  return { acceleration: 35, maxVelocity: 5 };
}

function stepState(state, target, dt) {
  const delta = target - state.value;
  if (Math.abs(delta) < 0.00005 || dt <= 0) {
    state.value = target; state.velocity = 0; return;
  }
  const desiredVelocity = clamp(delta / dt, -state.maxVelocity, state.maxVelocity);
  const maxChange = state.acceleration * dt;
  state.velocity += clamp(desiredVelocity - state.velocity, -maxChange, maxChange);
  let next = state.value + state.velocity * dt;
  if ((delta > 0 && next >= target) || (delta < 0 && next <= target)) {
    next = target; state.velocity = 0;
  }
  state.value = clamp(next, state.minimum, state.maximum);
}

export class FacialRuntime {
  constructor({ root, speaking = false, timeline = null, emotion = 'neutral', seed = 0, fps = 24 } = {}) {
    this.root = root;
    this.speaking = Boolean(speaking);
    this.timeline = timeline;
    this.emotion = emotion || 'neutral';
    this.seed = Number(seed) || 0;
    this.fps = Math.max(1, Number(fps) || 24);
    this.morphs = collectMorphTargets(root);
    this.bones = collectBones(root);
    this.tier = detectAnimationTier(this.morphs, this.bones);
    this.usesVisemes = REQUIRED_VISEMES.every(name => this.morphs.has(name));
    this.canDriveVisemes = this.usesVisemes && Boolean(
      this.timeline && Array.isArray(this.timeline.frames) && this.timeline.frames.length);
    this.hasBlink = this.morphs.has('eyeBlinkLeft') && this.morphs.has('eyeBlinkRight');
    this.states = new Map();
    for (const [name, bindings] of this.morphs) {
      const initial = clamp(Number(bindings[0].influences[bindings[0].index]) || 0);
      const isViseme = name.startsWith('viseme_');
      const dynamics = morphDynamics(name);
      const state = { name, bindings, baseline: isViseme ? 0 : initial,
        value: isViseme ? 0 : initial, velocity: 0, minimum: 0, maximum: 1, ...dynamics };
      this.states.set(name, state);
      this._write(state);
    }
    this.boneBases = new Map();
    for (const name of ['LeftEye', 'RightEye', 'Head', 'Neck']) {
      const bone = boneByName(this.bones, name);
      if (bone && bone.rotation) this.boneBases.set(name, {
        bone, x: bone.rotation.x, y: bone.rotation.y, z: bone.rotation.z,
      });
    }
  }

  get frameCount() {
    if (!this.timeline || !Array.isArray(this.timeline.frames)) return 0;
    const timelineFps = Math.max(1, Number(this.timeline.fps) || this.fps);
    return Math.ceil(this.timeline.frames.length * this.fps / timelineFps);
  }

  _write(state) {
    for (const binding of state.bindings) binding.influences[binding.index] = state.value;
  }

  composeTargets(frame, time, { gazeX = 0, gazeY = 0 } = {}) {
    const result = {};
    const timelineFps = Math.max(1, Number(this.timeline && this.timeline.fps) || this.fps);
    const timelineFrame = Math.round(frame * timelineFps / this.fps);
    const mouth = this.speaking && this.canDriveVisemes
      ? normalizeMouthWeights(sampleTimeline(this.timeline, timelineFrame))
      : normalizeMouthWeights({});
    Object.assign(result, mouth);
    Object.assign(result, emotionTargets(this.emotion, this.speaking));
    Object.assign(result, gazeTargets(gazeX, gazeY));
    if (this.hasBlink) {
      const blink = computeBlinkWeight(time, this.seed);
      result.eyeBlinkLeft = Math.max(result.eyeBlinkLeft || 0, blink);
      result.eyeBlinkRight = Math.max(result.eyeBlinkRight || 0, blink);
    }
    return result;
  }

  _applyLookAt(gazeX, gazeY, dt) {
    const factor = 1 - Math.exp(-Math.max(0, dt) * 10);
    for (const name of ['LeftEye', 'RightEye']) {
      const base = this.boneBases.get(name);
      if (!base) continue;
      base.bone.rotation.x += (base.x - gazeY * 4 * DEG - base.bone.rotation.x) * factor;
      base.bone.rotation.y += (base.y + gazeX * 6 * DEG - base.bone.rotation.y) * factor;
    }
    const head = this.boneBases.get('Head') || this.boneBases.get('Neck');
    if (head) {
      head.bone.rotation.x += (head.x - gazeY * 1.5 * DEG - head.bone.rotation.x) * factor;
      head.bone.rotation.y += (head.y + gazeX * 2.5 * DEG - head.bone.rotation.y) * factor;
    }
  }

  update(frame, dt, context = {}) {
    const gazeX = clamp(context.gazeX || 0, -1, 1);
    const gazeY = clamp(context.gazeY || 0, -1, 1);
    const time = Number.isFinite(Number(context.time)) ? Number(context.time) : frame * dt;
    const targets = this.composeTargets(frame, time, { gazeX, gazeY });
    for (const [name, state] of this.states) {
      const amount = clamp(Number(targets[name]) || 0);
      const target = clamp(state.baseline + (1 - state.baseline) * amount);
      stepState(state, target, dt);
      this._write(state);
    }
    this._applyLookAt(gazeX, gazeY, dt);
    return targets;
  }
}
