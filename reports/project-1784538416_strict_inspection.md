# Strict inspection — project-1784538416

## Evidence examined

- Final delivery: 1920x1080, 24 FPS, 48.917 seconds, H.264 + AAC stereo.
- Every one of the 1,174 decoded frames was processed with FFmpeg black-frame,
  freeze-frame and scene-change detectors.
- Audio integrated loudness: -15.1 LUFS; true peak: -4.0 dBFS.
- Quaternius runtime audit: 125 production-selectable characters, each with a
  valid GLB but SKELETAL_BASIC body-only capability (no verified facial rig,
  visemes, eye controls or lip-sync).

## Flaws found in this output

1. The script directed aerial characters (Dragon, Enemy Flying and Enemy
   ExtraSmall) to perform human hand/contact actions: pickup, point, pull,
   give, and grounded walk. Their real clip inventory does not support those
   actions. This is the primary cause of unconvincing body acting.
2. The story uses four body-only Quaternius characters in dialogue-heavy
   staging. Facial close-ups cannot make this read as natural dialogue.
3. All story beats remain in the same cave location, so visual progression is
   weak even though the dialogue is split into beats.
4. Detector found a short 0.083-second black interval at 46.750s and a
   final-tail freeze beginning at 47.042s. The closing hold is not treated as
   a failed render, but is recorded for review.
5. There are no fully facial-ready Quaternius characters in the installed
   runtime. A professional result must use body-led storytelling, medium/wide
   coverage and authored clips—not claimed lip-sync.

## Safeguards installed for future renders

- A 125-character trait report now classifies 85 humanoids, 23 ground
  creatures and 17 aerial characters.
- Aerial/creature rigs are clip-only: the legacy human arm/leg pose layer is
  disabled, aerial characters remain hovering, and grounded feet assumptions
  are not applied to them.
- Requested actions are resolved only to real clips on the exact character.
  Unsupported actions downgrade to a safe idle/listen state and are saved in
  `character_action_safety.json` for each project.
- Script guidance now states each selected Quaternius character's physical
  form and allowed directions before a script is generated.
- The character catalog exposes form, pose mode, ground mode and allowed
  actions so the UI and future planners can present accurate limitations.
- Facial close-ups remain restricted for body-only assets.

## Inventory reconciliation

- Quaternius Library shown in the app: 134 assets.
- Production-ready and audited: 125.
- Not integrated/selectable: 9 Pirate Kit assets, because their local license
  evidence is missing. They remain blocked rather than being silently used.

## Isolated renderer proof

A 24-frame Three.js capture completed successfully:

- Dragon requested `pickup` -> safely routed to real `Flying_Idle`, hover,
  clip-only.
- Farmer requested `pickup` -> retained real `Interact` clip, grounded
  humanoid mode.
