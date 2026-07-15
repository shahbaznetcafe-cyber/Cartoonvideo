# 🎬 SBZ AI Video Studio — v0.1

Script → multi-character **2D talking video** (1080p landscape), automatically.
Story analysis + per-character voices + AI backgrounds/characters + captions + render.

> v0.1 milestone. Bara vision (3D, AI director, voice cloning) V2/V3 ke liye hai.

---

## Pipeline (modules)

| Module | Kaam | Phase |
|---|---|---|
| `story_parser.py` | Script → characters + scenes + dialogue + emotion JSON | 3, 8 |
| `voice_engine.py` | Per-character voices (pitch/rate variety), timeline | 9 |
| `assets.py` | Scene backgrounds + character avatars (Runware) | 4, 7 |
| `text_render.py` | Urdu/English captions + labels (PIL, RTL) | 15 |
| `compositor.py` | bg + speaker avatar (talk-bob) + captions + music → render | 5(2D),13,16,17 |
| `build.py` | poora pipeline orchestrator | — |
| `app.py` | Flask UI | 1 |

**Lip-sync v0.1:** avatar ka "talk-bob" (bolte waqt). Asli phoneme lip-sync (Rhubarb/SadTalker) baad ka upgrade.

---

## Setup

1. **`start.bat`** par double-click — pehli dafa khud venv banata + packages install karta hai, phir UI kholta hai.
2. **FFmpeg** PATH mein hona chahiye (https://ffmpeg.org).
3. **`.env`** mein Runware key (pehle se mojood).

Manual:
```powershell
python -m venv .venv ; .\.venv\Scripts\activate
pip install -r requirements.txt
python app.py          # UI  ->  http://127.0.0.1:5050
# ya CLI:
python build.py sample_script.txt
```

---

## Istemaal (UI)
1. `start.bat` chalayein → browser khulega.
2. Script likhein (speaker ke naam ke saath), e.g.:
   ```
   راوی: صبح علی منڈی پہنچا۔
   علی: یہ ٹماٹر کیسے دیے؟
   دکاندار: اسی روپے کلو۔
   ```
3. **Generate** → live progress → final 1080p video preview + download.

Output: `projects/<project>/final.mp4` (+ story.json, timeline.json, voices/, assets/).

---

## 3D character capability validation

The Three.js character library is validated before rendering without loading or
modifying model assets. The validator reports GLB integrity, skeleton bones,
skinned meshes, morph targets, required visemes/facial controls, Mixamo and
strict TalkingHead compatibility, and one supported animation tier:

- `LEGACY_JAW` — existing six-bone/jaw-openness fallback.
- `SKELETAL_BASIC` — usable skinned skeleton without the complete viseme set.
- `VISEME_FACE` — complete 15-viseme set with incomplete facial controls.
- `FULL_FACIAL` — complete required viseme, blink, brow and emotion controls.

The UI shows the human-readable report in Preview. The complete library report
is available from `GET /api/characters3d/validation`. Each Three.js project also
writes an ignored `projects/<project>/character_validation.json` report before
rendering. Validation is warning-only in Phase 1, so legacy characters keep the
existing jaw-openness behaviour.

Validate one or more local models from the command line:

```powershell
python character_validator.py path\to\character.glb
python character_validator.py first.glb second.glb --output report.json
```

## Local Mixamo humanoid import

Mixamo FBX characters and animations can be converted into one Three.js GLB
with named animation clips. Raw/downloaded character media stays inside ignored
local asset folders and must not be committed or redistributed.

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  --python blender\import_mixamo_humanoid.py -- `
  assets\humanoids\amy\source\Amy_TPose.fbx `
  threejs_render\assets\chars\amy_humanoid.glb `
  blender\rigged\blend\amy_humanoid.blend `
  "Idle=assets\humanoids\amy\animations\Idle.fbx" `
  "Talking=assets\humanoids\amy\animations\Talking.fbx"
```

The renderer selects `Talking` for the current speaker and `Idle` for listeners.
Mixamo body rigs validate as `SKELETAL_BASIC`; professional facial lip-sync,
blinking, gaze and emotions still require the configured facial morph targets.

TalkingHead attribution and the preserved MIT license are recorded in
`THIRD_PARTY_NOTICES.md`. Character/model files and generated reports must not
be committed.

### Provider-neutral viseme timeline

After each dialogue voice is generated, `viseme_timeline.py` creates a
deterministic, frame-quantized JSON timeline containing:

- Oculus-compatible 15-viseme events and per-frame sparse morph weights.
- English, Urdu and Roman-Urdu grapheme/phoneme fallbacks.
- Optional provider word/sentence timestamp alignment.
- Audio-energy silence closure when FFmpeg decoding is available.
- Attack/release smoothing and adjacent-viseme coarticulation.
- Audio SHA-256, request SHA-256, language, FPS and duration metadata.

Results are cached under `projects/<project>/visemes/` using the audio hash and
request identity. `timeline.json` references the matching `.visemes.json` file.
If timeline creation fails or a character has no viseme morphs, the existing
openness JSON and jaw-bone renderer remain the fallback. Phase 2 does not apply
the morph weights in Three.js yet; that runtime integration belongs to Phase 3.

### Three.js facial runtime

`threejs_render/facial_runtime.js` inspects every loaded GLB at runtime and
selects its animation tier. Complete viseme rigs consume the Phase 2 per-frame
weights; incomplete or legacy rigs continue through jaw openness. A missing or
invalid viseme sidecar also returns to jaw motion automatically.

The runtime provides deterministic natural blinking, bounded eye/head look-at,
emotion-driven brows and smile/frown morphs, baseline-aware acceleration and
velocity-limited interpolation. Concurrent viseme weights are normalized to a
safe total to prevent mouth over-deformation. Only the current speaker receives
openness and viseme inputs; listeners keep all viseme morphs at zero while still
blinking and looking toward the speaker.

Run the standalone facial tests with:

```powershell
cd threejs_render
cmd /c npm test
```

### Persistent acting state

Three.js dialogue clips share a deterministic scene acting plan instead of resetting
characters at every cut. The plan preserves position and resting pose between lines,
uses smooth gesture attack/release, gives listeners mood-aware reactions, and keeps
idle/blink timing continuous through a stable character seed and global time offset.

Every 3D project writes `scene_animation_state.json`. This file records each visible
character's line-level start/end state, role, reaction, seed, and timing so resumed or
repeated renders reproduce the same acting choices. Legacy specs without acting-state
data continue to use the previous renderer defaults.

### Phase 5 verification and benchmark

The regression suite covers invalid GLBs, legacy jaw fallback, viseme-capable rigs,
silence mouth closure, speaker isolation, blink/emotion composition, pose continuity,
deterministic state/timeline output, truncated clip rejection, and final assembled
duration validation.

Run the same-scene 10-second Three.js benchmark with local, code-excluded GLBs:

```powershell
cd threejs_render
cmd /c npm run benchmark
```

The recorded 960x540, 24 fps, two-character result is in
`benchmarks/phase5_benchmark.json`. On the verification machine, the enhanced facial
and acting runtime added 0.325 ms/frame (1.51%) and 2.25 MB JavaScript heap versus the
baseline path. Benchmark frames are created in a temporary directory and deleted when
the run finishes; no characters or generated media are committed.

---

## Background music (optional)
`assets/music/` mein koi `.mp3` daal dein — woh halki awaaz mein video ke neeche lag jayega.

---

## v0.1 status
- [x] M1 Story Parser
- [x] M2 Voice Engine (multi-character)
- [x] M3 Assets + 2D Compositor (talk-bob lip-sync)
- [x] M4 Captions + Music + Render (1080p)
- [x] M5 Flask UI

## Roadmap (next)
- Asli phoneme **lip-sync** (Rhubarb 2D / SadTalker GPU)
- Per-scene **music by mood** + **SFX** library (Phase 14)
- **Camera moves** (pan/zoom/cuts) — Phase 6/16
- **Character expressions** by emotion (Phase 5/12)
- **Electron** desktop wrap (.exe) — Phase 1/25
