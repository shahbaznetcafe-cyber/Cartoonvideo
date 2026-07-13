const POSE_KEYS = ['armL', 'armR', 'legL', 'legR', 'bodyX', 'bodyY', 'bodyZ'];
const POSITION_KEYS = ['x', 'y', 'z'];

const clamp = (value, minimum = 0, maximum = 1) =>
  Math.max(minimum, Math.min(maximum, Number(value) || 0));

export function smoothstep(value) {
  const x = clamp(value);
  return x * x * (3 - 2 * x);
}

function normalizedState(value = {}) {
  const pose = value.pose || {};
  const position = value.position || {};
  return {
    position: Object.fromEntries(POSITION_KEYS.map(key => [key, Number(position[key]) || 0])),
    pose: Object.fromEntries(POSE_KEYS.map(key => [key, Number(pose[key]) || 0])),
    scaleY: Number.isFinite(Number(value.scaleY)) ? Number(value.scaleY) : 1,
  };
}

export function sampleActingState(acting = {}, progress = 0) {
  const start = normalizedState(acting.start);
  const end = normalizedState(acting.end || acting.start);
  const amount = smoothstep(progress);
  const mix = (a, b) => a + (b - a) * amount;
  return {
    position: Object.fromEntries(POSITION_KEYS.map(key =>
      [key, mix(start.position[key], end.position[key])])),
    pose: Object.fromEntries(POSE_KEYS.map(key =>
      [key, mix(start.pose[key], end.pose[key])])),
    scaleY: mix(start.scaleY, end.scaleY),
  };
}

export function gestureEnvelope(progress) {
  const attack = smoothstep(clamp(progress / 0.16));
  const release = 1 - smoothstep(clamp((progress - 0.80) / 0.20));
  return attack * release;
}

export function listenerReaction(reaction, progress, time, strength = 0.45) {
  const amount = gestureEnvelope(progress) * clamp(strength, 0, 0.75);
  const beat = Math.sin((Number(time) || 0) * 4.2);
  const result = { armL: 0, armR: 0, bodyX: 0, bodyY: 0, bodyZ: 0, dy: 0 };
  if (reaction === 'encourage') {
    result.armL = 12 * amount; result.armR = -12 * amount;
    result.bodyX = -4 * amount + beat * 2 * amount;
  } else if (reaction === 'concern') {
    result.armL = -5 * amount; result.armR = 5 * amount;
    result.bodyX = 7 * amount; result.bodyZ = 4 * amount;
  } else if (reaction === 'surprise') {
    result.armL = 18 * amount; result.armR = -18 * amount;
    result.bodyX = -7 * amount; result.dy = 0.025 * amount;
  } else if (reaction === 'attend') {
    result.bodyX = beat * 2.5 * amount;
    result.bodyZ = Math.sin((Number(time) || 0) * 2.1) * 1.4 * amount;
  }
  return result;
}
