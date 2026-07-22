const FACIAL_CLOSE_SHOTS = new Set(['dialogue_close_up', 'facial_close_up']);

export const SHOT_PURPOSES = Object.freeze({
  ESTABLISH: 'establish',
  LOCOMOTION: 'locomotion',
  PROP_REVEAL: 'prop_reveal',
  RELATIONSHIP: 'relationship',
  CONTACT: 'contact',
  BODY_REACTION: 'body_reaction',
  RETREAT: 'retreat',
  WARNING: 'warning',
  EXIT: 'exit',
  AFTERMATH: 'aftermath',
  DIALOGUE: 'dialogue',
});

const PURPOSE_SHOTS = Object.freeze({
  establish: 'establishing_wide',
  locomotion: 'tracking_medium',
  prop_reveal: 'prop_detail_close',
  relationship: 'motivated_two_shot',
  contact: 'contact_oblique_close',
  body_reaction: 'body_reaction_medium_close',
  retreat: 'reverse_medium',
  warning: 'over_shoulder_prop',
  exit: 'tracking_exit_wide',
  aftermath: 'prop_aftermath_close',
  dialogue: 'dialogue_medium',
});

export class ShotDirector {
  select({ purpose, requestedShot = null, dialogue = false }, character, registry) {
    let shot = requestedShot || PURPOSE_SHOTS[purpose];
    if (!shot) throw new Error(`No shot policy for story purpose: ${purpose}`);
    if (character.tier === 'SKELETAL_BASIC' && FACIAL_CLOSE_SHOTS.has(shot)) shot = 'body_medium';
    registry.assertShotAllowed(character.id, shot, { dialogue });
    return {
      type: shot,
      purpose,
      composition: shot.includes('prop') || shot.includes('over_shoulder')
        ? 'prop_weighted_rule_of_thirds'
        : 'off_center_rule_of_thirds',
      permanentlyCentered: false,
      facialCloseUp: FACIAL_CLOSE_SHOTS.has(shot),
      transition: 'hard_cut',
    };
  }
}

export function isFacialCloseShot(shot) {
  return FACIAL_CLOSE_SHOTS.has(String(shot || ''));
}
