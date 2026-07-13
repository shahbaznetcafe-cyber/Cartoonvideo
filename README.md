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
