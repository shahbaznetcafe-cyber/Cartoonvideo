# Adventurer Single-Scene Production Integration — Review Handoff

## Status

**Ready for the Phase 3 single-scene human review gate.** This is not a bulk rollout, not a production-readiness claim, and does not make the Adventurer facial-ready.

## Output

- Video: `outputs/adventurer_directed_production_scene.mp4`
- Metrics: `reports/adventurer_directed_production_metrics.json`
- Regression report: `reports/adventurer_directed_production_regression.json`
- Encoded milestone manifest: `reports/adventurer_encoded_milestone_manifest.json`
- Encoded visual review: `reports/adventurer_encoded_visual_review.json`
- Encoded milestones: `outputs/adventurer_directed_production_encoded_milestones/`

## Verified result

- Exactly 30.000 seconds, 1920×1080, 24 FPS, 720 H.264/YUV420p frames.
- Render/encode time: 188.392 seconds.
- Peak tracked memory: 740.72 MiB.
- Capability route: `SKELETAL_INTERACTIVE`; facial-ready: false.
- All observed animations are real registered GLB clips.
- Named `suspicious_box.reach_handle` target used; minimum wrist distance 0.1901 world units at trigger frame 330 against a 0.2 limit; facing error 0 degrees; hand IK false.
- Four locomotion spans use whole authored cycles and remain inside the registered 8% displacement mismatch tolerance.
- No black frames, page errors, console errors, or Blender runtime use.
- All 11 review images were extracted from the final encoded MP4 and visually inspected.
- Repeated path-edge grass uses 52 instances; repeated pebbles use 48 instances.
- Three.js regressions: 26/26 passed. Python regressions: 96/96 passed.
- Eight critical legacy/facial production files are byte-identical to Git HEAD.

## Review gate

Review the MP4 for animation continuity, contact readability, shot motivation, foot behavior and environmental motion. Do not register other Quaternius characters or start facial implementation until this single-scene integration is approved.
