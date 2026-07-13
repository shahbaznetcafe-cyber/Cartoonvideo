# SBZ AI Video Studio — MASTER PLAN
### Goal: ShaziVideoGen ke HAR feature ke saath, har feature BEHTAR andaz mein. Koi cheez nahi chhoot ti.

Legend: ✅ done · 🔨 partial · ⬜ todo · ⭐ "better than Shazi" improvement

---

## P0 — Foundation (ho chuka)
- ✅ Story parser (characters, scenes, emotion, dialogue)
- ✅ Voice engine (edge-tts, per-character, pitch/rate)
- ✅ Image gen (Runware FLUX)
- ✅ 2D compositor + render (1080p)
- ✅ Captions (basic) + music (basic)
- ✅ Flask UI
- ✅ Custom character library (rembg, auto-match) ⭐ (Shazi mein nahi)
- 🔨 Lip-sync R1 + procedural animation R2

---

## P1 — MOTION (PRIORITY — abhi) 🎯
Shazi: Ken Burns (zoom/pan) + speed. Hum: **Ken Burns + character animation + AI-video + transitions.**
- ✅ **Ken Burns 2.0** — per-scene directional zoom/pan (in/out/left/right/up/down) — TESTED
- ✅ **Scene transitions** — crossfade/dissolve (line-clips ke darmiyan) — TESTED
- ✅ **Character motion (R2-A)** — emotion-driven bounce/shake/sway/droop
- ✅ **Lip-sync (R1)** — amplitude mouth
- ✅ **AI-video motion (R2-B premium)** — Runware Kling cinematic mode + black-key compose — TESTED
- ✅ **Motion presets** — "subtle / dynamic / cinematic" toggle (config.MOTION_PRESET) — TESTED
- ✅ **Parallax / depth** — character vs background 2.5D drift — TESTED

### ✅ P1 — MOTION: MUKAMMAL (sab tested)

---

## ✅ P2 — Captions Pro (karaoke): MUKAMMAL (tested)
- ✅ **Whisper word-timing** — local faster-whisper (free, no API key) ⭐ (Shazi paid Groq)
- ✅ **Karaoke captions** — 3-words-at-a-time, current word highlight (Latin per-word; Urdu chunk)
- ✅ Highlight styles: color / box / scale-pop
- ✅ Font/color/size/outline/position (config.CAPTIONS) + custom font path
- ✅ Urdu RTL handling (reshape + chunk)
- ✅ **Animated caption entrance** (fade-in) ⭐
- ✅ Per-speaker caption color ⭐
- ⬜ (optional) transliterate toggle, more bundled fonts

---

## ✅ P3 — Multi-Provider Engine: MUKAMMAL (tested)
- ✅ **LLM providers:** Runware + OpenAI-compatible (Groq, Gemini, OpenAI, OpenRouter, Together) — key add karte hi chalega
- ✅ **Image providers:** Runware + FAL (Replicate framework ready)
- ✅ **TTS providers:** edge-tts (free) + ElevenLabs (Fish framework ready)
- ✅ **Auto-fallback** — ek provider fail/no-key ho to agla (groq→runware TESTED) ⭐
- ✅ **Cost estimate** (draft vs cinematic) — `providers.estimate_cost()`
- ✅ Provider **status** (`providers.status()` — kaunse available) — UI dropdown ke liye ready
- ✅ Consumers refactored: story_parser/assets/voice_engine ab provider layer use karte hain
- ⬜ (UI dropdowns → P8; aur providers: replicate/fish/genaipro easily add ho sakte)

---

## ✅ P4 — Style System: MUKAMMAL (tested)
- ✅ **Style library** — 159 art styles (prompt templates), popular ones ke detailed modifiers
- ✅ **Custom styles** — user apna style describe kare (`styles.add_custom` → styles_custom.json)
- ✅ **AI style suggest** — LLM script padh kar best style chune (horror→cinematic, kids→3d cartoon) ⭐
- ✅ **Per-scene style override** — scene.get("style") ya global config.STYLE
- ✅ Integrate — backgrounds style-aware (watercolor TESTED, visibly laga)
- ⬜ (Style preview thumbnails → P8 UI; characters lip-sync ke liye flat rakhe)

---

## ✅ P5 — Audio (music + SFX + overlays): MUKAMMAL (tested)
- ✅ **Mood-based music** — scene mood → music folder auto-select (comedy→happy TESTED) + ducking (0.12)
- ✅ **Music mood auto-select** (`audio.select_music`) ⭐
- ✅ **Video overlays** — procedural **vignette** (cinematic, TESTED) + file overlay support (sparks/light-leak)
- ✅ **SFX framework** — `audio.get_sfx()` (assets/sfx/ files daalte hi auto, transitions/ambient)
- ✅ **Voice settings** — volume + rate + pitch (edge) / stability+similarity+style (ElevenLabs via providers)
- ✅ **Per-character voice override** — characters.json "voice" field
- ⬜ (SFX files + overlay files user add kare; voice-mapping UI → P8)

---

## ✅ P6 — Resolution & Render Engine: MUKAMMAL (tested)
- ✅ **Resolutions:** 720p, 1080p, 2K, 4K (`config.VIDEO_QUALITY`)
- ✅ **Aspect:** landscape 16:9, portrait 9:16, square 1:1 (Shorts/Reels/TikTok) — bg bhi aspect-aware
- ✅ **Parallel render workers** — ThreadPoolExecutor (RENDER_WORKERS)
- ✅ **GPU encode (NVENC)** — K620 par bhi chala! (auto-detect, libx264 fallback) ⭐
- ✅ **Chunk render + resume** — har line cached chunk; re-run skip (105s→71s TESTED) ⭐
- ✅ **FPS** option (30/60)
- ✅ **Fast preview** (480p low-res draft)

---

## ✅ P7 — Batch & Project Management: MUKAMMAL (tested)
- ✅ **Batch mode** — folder ke saare .txt → alag videos (`batch.py` / /api/batch)
- ✅ **Projects** — list/load/delete + metadata (`projects_mgr.py`, /api/projects) — TESTED 7 projects
- ✅ **Re-render single scene** — `regenerate_scene()` (chunk cache delete → fresh)
- ✅ **Templates** (preset settings) — save/list/load ⭐ TESTED
- ✅ Project metadata auto-save (build ke baad)

---

## ✅ P8 — Desktop App & UI: MUKAMMAL (browser mein verify)
- ✅ **3-column dark UI** (Shazi-style: nav + controls + settings) — TESTED live
- ✅ **Electron wrapper** (`electron/main.js` + package.json) → `.exe` ke liye (npm install electron)
- ✅ All settings wired: style + AI-suggest, resolution/aspect/fps, motion preset, render mode, captions (karaoke), voice/audio
- ✅ Live progress (4 stages) + result video preview + download
- ✅ Provider status in topbar, cost estimate endpoint
- ✅ Settings flow → backend (`build.apply_settings`)
- ⬜ (per-scene live preview, in-UI console log, full .exe packaging → P12)

---

## ✅ P9 — Export & Publish: MUKAMMAL (tested)
- ✅ **Platform presets** — YouTube, Shorts, TikTok, Reels, FB (aspect/quality/fps auto)
- ✅ **SRT** subtitle file export
- ✅ **Audio-only** export (mp3)
- ✅ **Thumbnail** auto-generate (frame + title overlay) ⭐ TESTED
- ✅ **SEO** — LLM se title + description + hashtags (Urdu) ⭐ TESTED
- ✅ Auto-export build ke baad (srt + thumbnail) + /api/export endpoint
- ⬜ (H.265 toggle, image-sequence export — minor)

---

## ✅ BONUS — AI Assistant + Plugin System: MUKAMMAL (tested)
- ✅ **AI Assistant** — script analyze (hook score, pacing, title ideas, improvements) + improve script ⭐
- ✅ **Plugin system** — character/music/style/template packs (`plugins/` folder, install) ⭐
- ✅ Endpoints: /api/analyze, /api/improve, /api/plugins

---

## ✅ PUPPET ANIMATION ENGINE: MUKAMMAL (game-changer — Shazi mein nahi)
Real 2D character animation (After Effects-tier) @ minimum cost — AI rig + local puppet.
- ✅ **AI-rigging** (`autorig.py`) — closed-mouth character → mouth (closed/half/open) + eyes (blink/happy/angry/surprised) inpaint se auto-generate (~$0.07 one-time/char)
- ✅ **Puppet engine** (`puppet.py`) — lip-sync (mouth swap) + blink + emotion expression + body motion (local render = FREE)
- ✅ **Integrated** — assets auto-rig + compositor puppet branch (config.PUPPET_ANIMATION)
- ✅ TESTED — angry apple puppet, full scene + captions + music
- Per-video cost ~$0.01 · consistent character (AI-video drift nahi) · monetizable
- ⬜ Closed-mouth base for all 20 chars · phoneme lip-sync (Rhubarb) · blink-state polish

---

## P10 — Premium Cinematic Mode (1111.mp4 tier)
- ⬜ **AI-video per shot** (Runware Kling/Veo) — cinematic quality
- ⬜ Lip-sync model (image + audio → synced) 
- ⬜ Auto bg-removal on AI-video output + compose
- ⬜ Camera director (shot types) ⭐
- ⬜ "Draft (fast/free) ↔ Cinematic (paid)" toggle ⭐

---

## P11 — Polish & Release
- ⬜ Error handling + retry (har API)
- ⬜ Performance (cache, low-memory)
- ⬜ Installer (Windows), portable
- ⬜ Docs, sample projects, testing

---

## Tajweez-karda order (motion pehle, jaisa aap ne kaha)
```
P1 Motion → P2 Captions → P4 Styles → P3 Providers → P5 Audio
   → P6 Resolution/Render → P7 Batch → P8 Desktop → P9 Export
   → P10 Cinematic → P11 Release
```
