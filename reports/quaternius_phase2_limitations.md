# Quaternius Animation POC Phase 2 — Remaining Limitations

This is an isolated visual proof for review. It is not production-ready and it has not been connected to the main SBZ rendering pipeline.

## Character and performance

- The Adventurer has no jaw control, eye controls, facial morph targets, facial animation, or lip-sync. The proof uses body acting, head direction, shot size, and camera angle to compensate.
- The suspicious-box reach uses the real embedded `Interact` clip, but there is no runtime hand IK. Contact is blocked to a measured minimum wrist-to-contact distance of 0.1403 world units and is visually readable in the milestone frame; the hand is not constrained to the prop across the full motion.
- Locomotion uses complete authored `Walk`, `Run_Back`, and `Run` cycles with matched world displacement. There is no per-foot IK lock or terrain adaptation. Sampled planted beats have zero holder drift and remain on the ground plane, but clip-internal micro-sliding may still be visible under close inspection.
- `HitRecieve_2` is the real source clip used for the surprise recoil. `Idle_Gun_Pointing` is the real source clip used for the warning pose. These are disclosed compromises, not renamed semantic animations.
- The head-look and breathing offsets are deliberately conservative. Eye targeting is unavailable.

## Scene and presentation

- The box is a lightweight procedural Three.js prop, not a production art asset. Its lid, light, shake, and particle burst exist to validate interaction consequence.
- The forest uses lightweight Quaternius-compatible low-poly assets and procedural ground dressing. It is suitable for this POC, but it does not establish final production art direction.
- The proof has no dialogue or audio. This is intentional because the source GLB has no facial controls and the requested phase is a body-animation story proof.
- Camera changes are motivated hard cuts. No decorative transitions were added.

## Runtime and measurement

- Peak tracked memory is 733.56 MiB. The measurement includes Node RSS, Chrome main-process working set, page JavaScript heap, and FFmpeg working set; Chrome child-process native allocations are not included.
- Capture is deterministic for the recorded source hashes and seed, but GPU driver and encoder implementation differences can still change encoded bytes across machines.
- Visual validation was performed on the 11 milestone frames plus automated timeline samples. A human review of the complete MP4 remains the approval gate.

