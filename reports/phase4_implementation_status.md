# Phase 4 Multi-Character Support

## Implemented

- The representative proof remains exactly three characters: Casual_2, Farmer and King.
- Original glTF, FBX and Blend source files remain untouched.
- The official Quaternius pack license was verified as CC0 1.0.
- All sources were inspected before conversion: one 62-bone armature, five source meshes, 24 common authored clips and flat-color materials with no external image dependency.
- One manifest drives the existing reusable Blender standardizer. No per-character Blender scripts were created.
- Three normalized GLB 2.0 assets and preserved working Blend copies were generated.
- Character height is normalized to approximately 1.718 m and Blender ground offset is zero.
- All source clips are preserved. Four deterministic aliases remain explicitly recorded with their real source clip and are not presented as genuine authored semantic clips.
- Each character has an enriched validation JSON and a generated `SKELETAL_BASIC` capability entry.
- The isolated Three.js scene loads three separate object graphs, constructs three AnimationMixer instances and assigns Walk, Wave and Listen independently.
- The scene computes combined character bounds for proportion-aware camera framing and exposes skeleton UUID, grounding, material and animation-state evidence.
- A deterministic 1080p/24 FPS six-second capture and validation script is implemented.

## Inventory-ready expansion

- The same reusable standardization process was applied to the seven remaining directly-ready humanoids from the verified pack: Beach, Casual_Hoodie, Punk, Spacesuit, Suit, Swat and Worker.
- Adventurer and all ten additional ready humanoids are registered in `assets/characters/capability_registry.json`.
- Adventurer remains `SKELETAL_INTERACTIVE`; the other ten are conservatively registered as `SKELETAL_BASIC` and are not classified as facial-ready.
- All eleven are registered in `characters3d.json`, so they appear in the existing SBZ character picker.
- Backward-compatible runtime copies are available in `blender/rigged/blend` and `threejs_render/assets/chars`, preserving both Blender and Three.js render paths without changing existing routes or payloads.
- The original downloaded source assets and standardized source outputs remain untouched.
- Non-humanoid, incomplete-rig and non-ready inventory assets were not promoted into the production picker.

## Final verification pass

The Three.js preflight, deterministic MP4 capture, performance measurement and regression suite are complete. The runtime preserves the scale of the already-standardized GLBs, grounds each model independently, and uses conservative performance framing because static SkinnedMesh bounds do not include every posed vertex.

- Result: PASS
- Output: `outputs/phase4_multi_character_proof.mp4`
- Metrics: `reports/phase4_multi_character_metrics.json`
- Format: 1920x1080, 24 FPS, 144 frames, 6 seconds
- Render time: 37.654 seconds
- Independent mixers: 3/3
- Independent skeletons: 3/3
- Shared-skeleton corruption: none
- Page/runtime errors: none
