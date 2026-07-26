# SBZ / Quaternius Character Catalog Implementation

## Implemented

- Added a unified, data-driven character catalog without replacing `characters3d.json` as the render authority.
- Added separate **SBZ Originals** and **Quaternius Library** tabs to the Characters workspace.
- Added library tabs to the AI template cast picker and grouped the Cast & Scenes 3D dropdown by library.
- Added search, category filters, ready-only filtering, capability tiers, clip counts and explicit blocked/pending states.
- Added an Asset Library catalog for backgrounds, props, vehicles and weapons.
- Preserved every existing character name/selection payload and backend render route.
- Changed full-library GLB validation to lazy per-character validation in the preview editor, avoiding a 169-model validation pass before every preview.
- Propagated the manifest capability ID and animation tier into the Three.js scene specification.
- Decoupled body-animation routing from facial capability detection: registered skeletal characters use real embedded GLB clips, static characters do not receive a mixer, and legacy SBZ rigs retain their existing procedural/jaw path.
- Enforced the body-only camera policy at render-spec creation: non-facial Quaternius speakers are reframed from dialogue/facial close-up to a medium body-performance shot.
- Added capability IDs, animation tiers and resolved real clip names to Three.js render debug metadata for the final consolidated verification pass.

## Runtime character status

- SBZ Originals: **44**
- Quaternius production-selectable: **125**
- Quaternius `SKELETAL_INTERACTIVE`: **1**
- Quaternius `SKELETAL_BASIC`: **119**
- Quaternius `STATIC`: **5**
- Quaternius facial-ready: **0**
- Pirate characters held for license review: **9**

The initial 11 ready humanoids remain registered. A shared, data-driven Blender process additionally standardized:

- 64 animated Monster, Space and Zombie characters: 64 successful, 0 failed.
- 50 modular Blend/FBX characters: 50 successful, 0 failed; 45 skeletal and 5 static based on actual source actions.

## Asset catalog status

- Existing production backgrounds remain Market, Kitchen and Garden.
- Nature, Space, Zombie City, Pirate, vehicle, prop and weapon source assets are browsable in Asset Library.
- Modular assets are not falsely presented as complete scene presets.
- Pirate assets remain disabled until their pack license is verified.

## Safety and limitations

- No new character is classified as facial-ready.
- Non-facial characters reject dialogue/facial close-up intent through the capability registry policy.
- Story actions resolve only against real clip names embedded in each GLB; fallback selection remains the real Idle/TalkIdle/first authored clip and is never presented as a newly authored semantic animation.
- Original downloaded sources were not modified.
- Generated character binaries remain local and Git-ignored.
- Per the user's instruction, runtime render captures, visual deformation review and regression tests are deferred until the final consolidated test pass.

## Machine-readable evidence

- `reports/quaternius_animated_integration.json`
- `reports/quaternius_modular_integration.json`
- `reports/quaternius_runtime_library.json`
- `assets/characters/capability_registry.json`
