export const CAPABILITY_TIERS = Object.freeze({
  STATIC: 'STATIC',
  SKELETAL_BASIC: 'SKELETAL_BASIC',
  SKELETAL_INTERACTIVE: 'SKELETAL_INTERACTIVE',
  FACIAL_READY: 'FACIAL_READY',
});

const FACIAL_SHOTS = new Set(['dialogue_close_up', 'facial_close_up']);

export function validateCapabilityDocument(document) {
  if (!document || document.schemaVersion !== 1) throw new Error('Capability registry schemaVersion must be 1');
  for (const tier of Object.values(CAPABILITY_TIERS)) {
    if (!document.tiers?.[tier]) throw new Error(`Capability registry is missing tier: ${tier}`);
  }
  for (const [id, character] of Object.entries(document.characters || {})) {
    if (!Object.values(CAPABILITY_TIERS).includes(character.tier)) throw new Error(`${id} has invalid tier: ${character.tier}`);
    if (!character.authoredClips || typeof character.authoredClips !== 'object') {
      throw new Error(`${id} must declare authoredClips`);
    }
    for (const [clipName, clip] of Object.entries(character.authoredClips)) {
      if (!clipName || !Number.isFinite(Number(clip.durationSeconds)) || clip.durationSeconds <= 0) {
        throw new Error(`${id} has invalid authored clip metadata: ${clipName}`);
      }
      if (!['once', 'repeat'].includes(clip.recommendedLoop)) {
        throw new Error(`${id}.${clipName} has invalid recommendedLoop`);
      }
    }
    for (const [storyAction, mapping] of Object.entries(character.storyActionClips || {})) {
      if (!mapping.realClip || !character.authoredClips[mapping.realClip]) {
        throw new Error(`${id}.${storyAction} does not resolve to a declared real clip`);
      }
    }
    if (character.tier === CAPABILITY_TIERS.FACIAL_READY && !character.facial?.ready) {
      throw new Error(`${id} cannot be FACIAL_READY without validated facial capability`);
    }
  }
  return true;
}

export class CharacterCapabilityRegistry {
  constructor(document) {
    validateCapabilityDocument(document);
    this.document = structuredClone(document);
  }

  get(characterId) {
    const character = this.document.characters?.[characterId];
    if (!character) throw new Error(`Unregistered character: ${characterId}`);
    return structuredClone({ id: characterId, ...character });
  }

  resolveStoryAction(characterId, storyAction) {
    const character = this.get(characterId);
    const mapping = character.storyActionClips?.[storyAction];
    if (!mapping) throw new Error(`No recorded real-clip mapping for ${characterId}:${storyAction}`);
    if (!character.authoredClips[mapping.realClip]) {
      throw new Error(`Mapped clip is not present in authoredClips: ${mapping.realClip}`);
    }
    return { storyAction, realClip: mapping.realClip, authored: mapping.authored === true,
      disclosure: mapping.disclosure || null };
  }

  assertShotAllowed(characterId, shot, { dialogue = false } = {}) {
    const character = this.get(characterId);
    const rejected = new Set(character.cameraPolicy?.reject || []);
    if (rejected.has(shot) || (!character.facial?.ready && FACIAL_SHOTS.has(shot))) {
      throw new Error(`${shot} is not allowed for non-facial character ${characterId}`);
    }
    if (dialogue && !character.facial?.ready && shot.includes('close_up')) {
      throw new Error(`Dialogue close-up rejected: ${characterId} has no facial controls`);
    }
    return true;
  }
}

export async function loadCapabilityRegistry(url = '/assets/characters/capability_registry.json') {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Capability registry load failed: HTTP ${response.status}`);
  return new CharacterCapabilityRegistry(await response.json());
}
