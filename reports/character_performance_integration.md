# Character-Aware Script, Facial and Lip-Sync Integration

## Integrated behavior

- Script generation now receives the real performance capability of every selected character.
- Template, quick/pro, long-form, structured Dialogue Writer and Script Doctor paths share the same policy.
- Body-only characters are written for visible actions, reactions and short utterances instead of facial-dependent dialogue.
- Jaw rigs receive short, naturally punctuated lines and audio-driven openness lip-sync.
- Viseme rigs receive provider-neutral phoneme/viseme timelines with smoothing and mouth-weight limits.
- Full-facial rigs may use blinking, gaze, emotion morphs and motivated dialogue close-ups.
- Preview cards show a plain-language performance badge and warn about dialogue that exceeds an asset's real ability.
- The renderer sends jaw/viseme inputs only to the current speaker and only when that character supports the input.
- Listeners remain mouth-closed. Unsupported facial close-ups are reframed as medium/body-reaction shots.
- Structured storyboards record `voiceover_body_acting` when a selected asset has no dialogue lip-sync controls.

## Current integrated inventory

- 43 SBZ Originals: `LEGACY_JAW` / jaw-openness lip-sync.
- 1 Quaternius Adventurer: `SKELETAL_INTERACTIVE` / body acting only.
- 120 integrated characters: `SKELETAL_BASIC` / body acting only.
- 5 integrated characters: `STATIC` / visual roles only.
- 0 current assets: `VISEME_FACE` or `FULL_FACIAL`.

## Verification

- Python regression suite: 101/101 passed.
- Three.js regression suite: 26/26 passed.
- JavaScript syntax check: passed.
- Capability-aware preview endpoint: passed.
- Body-only, jaw and viseme input-routing tests: passed.

## Asset limitation

The software path for professional visemes, blinking, gaze and facial emotion is implemented and tested, but none of the currently integrated GLBs contains the required facial morph set. Body-only Quaternius files cannot gain real lip-sync through code alone; their meshes must first be authored with jaw/viseme/blink controls and re-exported. The application therefore uses safe body acting and never reports them as facial-ready.
