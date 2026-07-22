# Adventurer Production-Director Integration Diff

## Scope

This is an opt-in, single-scene production integration. It registers only the validated Quaternius Adventurer and does not bulk-convert or register the remaining characters. It does not implement or claim facial animation.

## Added production contracts

- `assets/characters/capability_registry.json` — explicit `STATIC`, `SKELETAL_BASIC`, `SKELETAL_INTERACTIVE`, and `FACIAL_READY` tiers; Adventurer is `SKELETAL_INTERACTIVE` with facial readiness set to false.
- `threejs_render/production/character_capability_registry.js` — validated registry access, fail-closed real-clip resolution, and dialogue/facial close-up rejection.
- `threejs_render/production/animation_director.js` — beat compilation, real clips, cycle-matched displacement, crossfades, interruptible reactions, interaction events, and exclusive `AnimationMixer` bone ownership.
- `threejs_render/production/shot_director.js` — purpose-driven, off-center shot selection with non-facial restrictions.
- `threejs_render/production/interaction_system.js` — named prop targets, holder alignment, wrist-distance and facing validation, exact trigger timing, camera gap masking, and explicit future IK capability.
- `threejs_render/production/environment_motion.js` — deterministic configurable motion and instancing plan.
- `threejs_render/production/export_production_plan.mjs` — exports the resolved real-clip, locomotion, shot and interaction plan.
- `threejs_render/production/extract_encoded_milestones.mjs` — extracts and hashes review frames directly from the final MP4.
- `threejs_render/production_scene/index.html` — opt-in browser entry point for the single directed scene.
- `reports/sbz_adventurer_production_scene.json` — structured SBZ scene input consumed by the directors.
- `threejs_render/tests/production_directors.test.mjs` — capability, clip, camera, interaction, timing, locomotion and environment regression coverage.
- `threejs_render/production/validate_production_scene.mjs` — media, runtime, encoded evidence, regression, interaction and legacy-file validation.

The production executor resolves the character asset, bone mapping, authored clips, locomotion profiles and restrictions from the registry. The production branch contains no Adventurer-ID-specific behavior.

## Reused with a narrow opt-in

- `threejs_render/quaternius_phase2/story.js` detects the isolated production-scene entry point, compiles the structured scene through the directors and executes the returned plan. The approved Phase 2 page remains available.
- `threejs_render/quaternius_phase2/capture.mjs` accepts `--production` to select separate output, metrics, encoded milestones, hashes and runtime assertions.

## Deliberately untouched

The Flask/Blender orchestration and the existing legacy/facial Three.js renderer were not edited. Byte-level Git evidence is recorded in `reports/adventurer_production_untouched_legacy_files.json`.

## Runtime boundary

Blender remains an asset-standardization tool only. Normal scene rendering uses Three.js, headless Chrome and FFmpeg. No new CDN, framework, model, character conversion or facial runtime was introduced.
