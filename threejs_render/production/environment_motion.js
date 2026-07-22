function seededUnit(seed) {
  let state = Number(seed) >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

export function normalizeEnvironmentConfig(input = {}) {
  return {
    enabled: input.enabled !== false,
    seed: Number(input.seed) || 20260715,
    windStrength: Math.max(0, Math.min(1, Number(input.windStrength) || 0)),
    leaves: Math.max(0, Math.floor(Number(input.leaves) || 0)),
    clouds: Math.max(0, Math.floor(Number(input.clouds) || 0)),
    ambientActors: Math.max(0, Math.floor(Number(input.ambientActors) || 0)),
    instancedVegetation: input.instancedVegetation !== false,
  };
}

export function environmentMotionSample(configInput, time, index = 0, kind = 'foliage') {
  const config = normalizeEnvironmentConfig(configInput);
  if (!config.enabled) return { swayX: 0, swayZ: 0, drift: 0 };
  const random = seededUnit(config.seed + index * 7919 + kind.length * 101);
  const phase = random() * Math.PI * 2;
  const speed = 0.55 + random() * 0.8;
  const strength = config.windStrength * (kind === 'tree' ? 0.012 : 0.035);
  return {
    swayX: Math.sin(time * speed * 0.63 + phase) * strength * 0.35,
    swayZ: Math.sin(time * speed + phase) * strength,
    drift: Math.sin(time * 0.31 + phase) * config.windStrength,
  };
}

export function buildEnvironmentPlan(input = {}) {
  const config = normalizeEnvironmentConfig(input);
  return {
    config,
    deterministic: true,
    instancing: {
      enabled: config.instancedVegetation,
      groups: [
        { id: 'path_edge_grass', instances: 52, useInstancedMesh: true },
        { id: 'path_pebbles', instances: 48, useInstancedMesh: true }
      ]
    },
    ambient: { leaves: config.leaves, clouds: config.clouds, actors: config.ambientActors },
  };
}
