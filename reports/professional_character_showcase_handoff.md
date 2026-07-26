# SBZ Professional Character Showcase — Final Handoff

## Deliverable

- Final MP4: `outputs/sbz_professional_character_showcase.mp4`
- Contact sheet: `outputs/sbz_professional_character_showcase_contact_sheet.jpg`
- Media validation: `reports/professional_character_showcase_validation.json`
- Build metrics: `reports/professional_character_showcase_metrics.json`

## Media contract

- Resolution: 1920x1080
- Frame rate: deterministic 24 FPS
- Duration: 37.458 seconds / 899 frames
- Video: H.264, yuv420p
- Audio: AAC, 48 kHz, stereo
- Audio analysis: -21.1 dB mean, -6.6 dB peak
- Black-frame scan: no black segments detected
- Transition policy: two motivated 0.35-second short dissolves; story coverage uses clean cuts

## Features demonstrated

- Data-driven capability routing with explicit body-animation limitations
- Authored real animation clips, not invented semantic clip claims
- Character entry, locomotion, approach, interaction, reaction, pointing and exit
- Named prop target with visible box movement, glow and particle consequence
- Motivated establishing, tracking, detail, reaction and exit camera shots
- Deterministic wind, vegetation, leaves, birds and layered environment depth
- Grounded locomotion and planted poses without random reset
- Three simultaneous characters with independent roots, skeletons and AnimationMixer instances
- Correct per-character materials, grounding and proportion-aware framing
- Intentional title/lower-third graphics, local music, transition cues and mastered delivery audio

## Verification results

- Python regression suite: 96/96 passed
- Three.js regression suite: 26/26 passed
- Directed production scene: 28/28 checks passed
- Final showcase media validation: 12/12 checks passed
- Phase 4 multi-character proof: PASS, zero page errors and zero request errors

## Honest limitations

- The showcased Quaternius characters are body-animation characters, not `FACIAL_READY`.
- Dialogue and lip-sync are intentionally absent; this output makes no facial-animation claim.
- Blender is not used during runtime rendering.
- The output is a production-quality character-animation proof, not a claim that every application generation mode is represented in one clip.

## Reproduce

```powershell
node threejs_render\quaternius_phase2\capture.mjs D:\flayer\sbz-studio --production
node threejs_render\phase4_multi_character\capture.mjs D:\flayer\sbz-studio --capture
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\build_character_showcase.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\validate_character_showcase.ps1
```
