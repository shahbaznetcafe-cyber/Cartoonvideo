/** Deterministic selection/timing for embedded humanoid animation clips. */

const ACTION_TERMS = {
  walk: ['walk', 'walking'],
  come: ['walk', 'walking'],
  go: ['walk', 'walking'],
  approach: ['walk', 'walking'],
  run: ['run', 'running', 'jog'],
  wave: ['wave', 'waving', 'greet'],
  greet: ['wave', 'waving', 'greet'],
  hello: ['wave', 'waving', 'greet'],
  point: ['point', 'pointing'],
  pointing: ['point', 'pointing'],
  reach: ['interact', 'pickup', 'pick up'],
  reaching: ['interact', 'pickup', 'pick up'],
  give: ['interact', 'pickup', 'pick up'],
  offer: ['interact', 'pickup', 'pick up'],
  pickup: ['interact', 'pickup', 'pick up'],
  interact: ['interact', 'pickup', 'pick up'],
  nod: ['yes', 'nod'],
  agree: ['yes', 'nod'],
  yes: ['yes', 'nod'],
  shake: ['no', 'deny'],
  deny: ['no', 'deny'],
  no: ['no', 'deny'],
  jump: ['jump'],
  celebrate: ['celebrate', 'cheer', 'excited'],
  cheer: ['celebrate', 'cheer', 'excited'],
  win: ['victory', 'celebrate', 'cheer'],
  happy: ['victory', 'celebrate', 'cheer'],
  punch: ['punch'],
  kick: ['kick'],
  dance: ['dance'],
  exit: ['run', 'running', 'walk'],
  retreat: ['run back', 'backward', 'run'],
  hit: ['recievehit', 'receivehit', 'hitrecieve 2', 'hitrecieve', 'hit receive', 'hit'],
  fall: ['death', 'defeat', 'recievehit', 'receivehit', 'hitrecieve 2', 'hitrecieve'],
  listen: ['listen', 'idle neutral', 'idle'],
  look: ['listen', 'idle neutral', 'idle'],
  sit: ['idle neutral', 'idle'],
  stand: ['idle neutral', 'idle'],
};

function normalized(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

// Clips that leave the character prone/off-feet. A speaking character must never
// play these — a narrator lying face-down mid-dialogue reads as a broken render.
const PRONE_TERMS = ['death', 'defeat', 'die', 'dead', 'ko', 'knockout',
  'faint', 'lie', 'lying', 'sleep', 'roll', 'recievehit', 'receivehit',
  'hitrecieve', 'hit recieve', 'fall'];

export function isProneClip(clip) {
  const name = normalized(clip && clip.name);
  if (!name) return false;
  return PRONE_TERMS.some(term => name.includes(term));
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
  // A speaking character must stay upright; hide prone clips from every branch
  // below so an explicit sourceClip/action can never lay the narrator down.
  const pool = state.speaking ? clips.filter(clip => !isProneClip(clip)) : clips;
  const usable = pool.length ? pool : clips;
  const requested = normalized(state.sourceClip);
  if (requested) {
    const exact = usable.find(clip => normalized(clip && clip.name) === requested);
    if (exact) return exact;
  }
  const action = normalized(state.action);
  if (action && ACTION_TERMS[action]) {
    const actionClip = findClip(usable, ACTION_TERMS[action]);
    if (actionClip) return actionClip;
  }
  if (state.speaking) {
    return findClip(usable, ['talking', 'speaking', 'conversation', 'talk'])
      || findClip(usable, ['idle', 'standing idle'])
      || findClip(usable, ['idle'])
      || usable[0];
  }
  return findClip(usable, ['idle', 'standing idle', 'listening']) || usable[0];
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
