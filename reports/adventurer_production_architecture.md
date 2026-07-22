# SBZ Character Production Architecture — Single Adventurer Integration

## Capability tiers

1. `STATIC` — renderable asset with no trusted animated skeleton.
2. `SKELETAL_BASIC` — validated authored body clips; no validated prop interaction or facial controls.
3. `SKELETAL_INTERACTIVE` — authored body clips, matched world movement, named prop interaction, contact validation, and body-safe camera direction.
4. `FACIAL_READY` — independently validated body, facial, blink, gaze, emotion, viseme, and dialogue capabilities.

Tier promotion is registry-driven and fail-closed. Body animation never implies facial readiness. The Quaternius Adventurer is registered only as `SKELETAL_INTERACTIVE`.

## Production flow

`SBZ storyboard JSON` → `Character Capability Registry` → `Animation Director` → `Shot Director + Interaction System + Environment Plan` → `Three.js scene runtime` → `headless Chrome frames` → `FFmpeg MP4 + metrics`

## Ownership boundaries

- Character Capability Registry owns asset facts, skeleton mapping, real embedded clip names, measured movement speeds, supported interaction modes, camera restrictions, facial capability, and limitations.
- Animation Director converts contiguous story beats into exact frames, real clips, holder displacement, crossfades, interruptible reactions, shots, prop events, and environment events.
- `THREE.AnimationMixer` exclusively owns animated bones. Directors may move or rotate the grounded character holder but do not overwrite animated limb bones.
- Shot Director maps story purpose to motivated, off-center compositions. Non-facial characters reject dialogue/facial close-ups; body-reaction medium-close framing remains available.
- Interaction System resolves named prop targets, aligns holder position/facing, records the real source clip, measures wrist-to-target distance, and recommends gap-masking angles. Hand IK is explicitly future capability and remains disabled.
- Environment plan owns deterministic wind/ambient configuration. Repeated path-edge grass and pebbles use `THREE.InstancedMesh`; larger hero vegetation retains lightweight reusable assets.
- Blender remains outside normal rendering and is permitted only for one-time asset standardization.

## Compatibility boundary

The integration is opt-in through `threejs_render/production_scene/index.html` and the `--production` capture flag. Existing Flask routing, Blender fallback, legacy jaw rigs, facial runtime, viseme path, persistent acting path, and `render_scene.html` remain unchanged.

## Current limitations

- No facial animation, lip-sync, blinking, eye targeting, or dialogue close-ups for the Adventurer.
- No hand IK; the validated contact distance is handled with an oblique contact shot.
- No terrain-aware foot IK. Locomotion uses authored full cycles, matched holder displacement, grounding, and planted-root validation.
- Only one character and one scene are registered. No bulk character conversion was performed.

