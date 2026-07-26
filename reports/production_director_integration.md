# Script-to-Screen Production Director Integration

Date: 2026-07-16

## Outcome

SBZ AI Video Studio now turns parsed script beats into deterministic production direction for the existing Three.js render pipeline. The user can provide a script and retain optional manual overrides; the default path automatically selects cast capability, body action, authored animation clip, movement, camera purpose, environment motion, lightweight props, and visible prop consequences.

## Automatic flow

1. Script generation asks for `Character: (emotion; action) dialogue` using a controlled action vocabulary.
2. Existing scripts that only contain `(emotion)` remain valid. Missing actions are inferred deterministically from dialogue.
3. Character requirements are classified as dialogue, skeletal action, or balanced.
4. Auto-casting prefers a character whose capability tier matches the role. User character overrides remain authoritative.
5. The production director resolves every action to a real authored source clip when available and records the resolution. It never presents a renamed alias as a real clip.
6. Every line receives a motivated camera shot, composition, environment preset, deterministic ambient motion, optional prop, transition, and persistent prop state.
7. Three.js renders body-only characters for the complete audio duration. Lip-sync remains capability-routed: facial rigs use facial controls; legacy rigs keep the jaw-openness fallback; listeners stay closed.

## Reproducibility artifacts

Each generated project can retain:

- `story.json`
- `timeline.json`
- `scene_animation_state.json`
- `production_direction.json`

`production_direction.json` records the real clip, shot purpose, camera direction, environment motion, prop target/state, and visible consequence for every line.

## Integrated direction features

- Walking, running, retreating, entering and exiting with world displacement
- Pointing, waving, reaching/picking up, interacting, listening, looking, sitting, standing, celebrating, punching, kicking, hit reaction, falling and dancing
- Establishing, tracking, dialogue, reaction, prop-detail/contact, two-shot and exit shots
- Forest, market, indoor, school/classroom, road, desert, snow, night, storm, mud/wash and stage-style environment routing
- Deterministic wind, leaves, clouds and ambient actors
- Lightweight box, ball, book, gift, cup, sign and rock props
- Persistent box opening, ball rolling and object movement/lift consequences
- Explicit source-clip provenance and safe procedural fallback
- Capability-aware close-up restrictions for body-only characters

## Verification

- Python regression suite: **107 passed, 0 failed**
- Three.js/Node regression suite: **26 passed, 0 failed**
- JavaScript syntax checks: passed
- `git diff --check`: passed (line-ending warnings only)
- Headless Three.js smoke: 48 frames at 960x540/24 FPS, real `Interact` clip, forest motion, directed camera, box-open consequence, no facial capability claim
- Smoke MP4: `outputs/production_director_runtime_smoke.mp4`, exactly 2.000 seconds, 48 frames, no black-frame interval detected
- Live `/api/preview` check: 2/2 missing actions inferred as `walk` and `run`; action-heavy `Hero` auto-cast to `quaternius_adventurer`

## Current honest limitations

- Existing Quaternius body characters are not facial-ready. The director uses body acting and camera restrictions; it does not claim facial lip-sync for them.
- True hand IK is not implemented. Prop contact is target-validated and small contact gaps are hidden through camera direction.
- Only the currently integrated environment assets can be loaded as full GLB sets. Procedural lightweight presets cover other script locations until additional environments are standardized.
- Final visual quality still depends on the source character rig, authored clips, environment assets and selected render quality.
