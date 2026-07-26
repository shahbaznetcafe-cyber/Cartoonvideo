# Adventurer Phase 3 — Remaining Limitations

- The Adventurer is `SKELETAL_INTERACTIVE`, not `FACIAL_READY`. It has no jaw, visemes, blink controls, independent eye controls, facial emotion morphs, or lip-sync.
- Dialogue facial close-ups are rejected. Body acting and medium/wide coverage are the only supported dialogue fallback.
- Hand IK is not implemented. The runtime aligns the grounded character holder to a named target, validates wrist distance and facing, and uses an oblique interaction shot. It does not claim exact hand locking.
- Foot IK and terrain adaptation are not implemented. Whole authored locomotion cycles, registered stride distance, grounded holder displacement, and mismatch tolerance reduce visible sliding but cannot guarantee perfect foot locking on uneven terrain.
- `Idle_Gun_Pointing` is the real authored source behind `warning_point`; it is disclosed as a semantic compromise rather than presented as a native warning clip.
- The forest and suspicious box are lightweight proof assets. They validate direction, interaction and environment motion but do not define final art direction.
- Only the Adventurer is registered. No other Quaternius character has been standardized, promoted, or visually validated by this phase.
- Peak-memory tracking excludes native allocations of Chrome child processes; the documented figure is a conservative tracked subset, not total machine memory.

