/** Deterministic selection/timing for embedded humanoid animation clips. */

const ACTION_TERMS = {
  walk: ['walk', 'walking'],
  run: ['run', 'running', 'jog'],
  wave: ['wave', 'waving', 'greet'],
  greet: ['wave', 'waving', 'greet'],
  point: ['point', 'pointing'],
  pointing: ['point', 'pointing'],
  celebrate: ['celebrate', 'cheer', 'excited'],
  cheer: ['celebrate', 'cheer', 'excited'],
};

function normalized(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function findClip(clips, terms) {
  for (const term of terms) {
    const exact = clips.find(clip => normalized(clip && clip.name) === term);
    if (exact) return exact;
  }
  for (const term of terms) {
    const partial = clips.find(clip => normalized(clip && clip.name).includes(term));
    if (partial) return partial;
  }
  return null;
}

export function selectHumanoidClip(clips = [], state = {}) {
  if (!Array.isArray(clips) || clips.length === 0) return null;
  const action = normalized(state.action);
  if (action && ACTION_TERMS[action]) {
    const actionClip = findClip(clips, ACTION_TERMS[action]);
    if (actionClip) return actionClip;
  }
  if (state.speaking) {
    return findClip(clips, ['talking', 'speaking', 'conversation', 'talk'])
      || findClip(clips, ['idle', 'standing idle'])
      || clips[0];
  }
  return findClip(clips, ['idle', 'standing idle', 'listening']) || clips[0];
}

export function humanoidClipTime(timeSeconds, durationSeconds, phaseSeconds = 0) {
  const duration = Number(durationSeconds);
  if (!Number.isFinite(duration) || duration <= 0) return 0;
  const value = (Number(timeSeconds) || 0) + (Number(phaseSeconds) || 0);
  return ((value % duration) + duration) % duration;
}

export function isHumanoidPositionTrack(trackName) {
  const name = String(trackName || '').replace(/\s+/g, '');
  return /\.position$/i.test(name);
}
