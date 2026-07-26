const vector3 = value => {
  if (!Array.isArray(value) || value.length !== 3 || value.some(item => !Number.isFinite(Number(item)))) {
    throw new Error('Interaction positions must be finite [x,y,z] arrays');
  }
  return value.map(Number);
};

export function distance3(a, b) {
  const av = vector3(a), bv = vector3(b);
  return Math.hypot(av[0] - bv[0], av[1] - bv[1], av[2] - bv[2]);
}

export class InteractionSystem {
  constructor(props = []) {
    this.targets = new Map();
    for (const prop of props) {
      for (const target of prop.targets || []) {
        const key = `${prop.id}.${target.name}`;
        if (this.targets.has(key)) throw new Error(`Duplicate interaction target: ${key}`);
        this.targets.set(key, { propId: prop.id, ...target, position: vector3(target.position) });
      }
    }
  }

  getTarget(name) {
    const target = this.targets.get(name);
    if (!target) throw new Error(`Unknown interaction target: ${name}`);
    return structuredClone(target);
  }

  plan(character, interaction) {
    const target = this.getTarget(interaction.target);
    const capability = character.interaction?.supported?.[interaction.capability];
    if (!character.interaction?.enabled || !capability) {
      throw new Error(`${character.id} does not support interaction: ${interaction.capability}`);
    }
    if (!Number.isFinite(Number(interaction.triggerTime)) || !Number.isInteger(Number(interaction.triggerFrame)) ||
      !interaction.consequenceEvent) {
      throw new Error(`Interaction ${interaction.target} requires triggerTime, triggerFrame and consequenceEvent`);
    }
    const facingYaw = Math.atan2(target.position[0] - interaction.characterPosition[0],
      target.position[2] - interaction.characterPosition[2]);
    return {
      target,
      capability: interaction.capability,
      wristBone: capability.wristBone,
      realClip: capability.realClip,
      characterPosition: vector3(interaction.characterPosition),
      facingYaw,
      maximumContactDistance: capability.maximumContactDistance,
      acceptableFacingErrorDegrees: Number(interaction.acceptableFacingErrorDegrees) || 12,
      triggerTime: Number(interaction.triggerTime),
      triggerFrame: Number(interaction.triggerFrame),
      consequenceEvent: interaction.consequenceEvent || null,
      handIK: false,
      futureCapability: 'optional_hand_ik',
      cameraGapMasking: capability.cameraGapMasking === true,
    };
  }

  validateContact(plan, wristPosition) {
    const measuredDistance = distance3(wristPosition, plan.target.position);
    return {
      valid: measuredDistance <= plan.maximumContactDistance,
      measuredDistance,
      maximumContactDistance: plan.maximumContactDistance,
      recommendedShot: measuredDistance <= plan.maximumContactDistance * 0.65
        ? 'contact_detail'
        : 'contact_oblique_masked',
      handIKApplied: false,
    };
  }

  validateFacing(plan, characterYaw) {
    const delta = Math.atan2(Math.sin(characterYaw - plan.facingYaw), Math.cos(characterYaw - plan.facingYaw));
    const measuredErrorDegrees = Math.abs(delta) * 180 / Math.PI;
    return { valid: measuredErrorDegrees <= plan.acceptableFacingErrorDegrees,
      measuredErrorDegrees, maximumErrorDegrees: plan.acceptableFacingErrorDegrees };
  }
}
