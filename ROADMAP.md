# SBZ AI Video Studio — Roadmap

## ✅ Done — v0.1 (working end-to-end)
- [x] M1 — Story Parser (characters, scenes, emotion, dialogue)
- [x] M2 — Voice Engine (multi-character, pitch/rate variety)
- [x] M3 — Assets (AI backgrounds + character avatars) + 2D Compositor
- [x] M4 — Captions (Urdu/Eng) + Music + 1080p render
- [x] M5 — Flask UI (script → live progress → preview)

---

## 🔜 Remaining — R1..R12

### Group A — Quality (videos ko "professional" banane wale)
- [x] **R1 — Real Lip-Sync (2D)** · M
  - [x] v1: amplitude-driven jaw/head motion (speech ke saath synced)
  - [x] v2: flat-2D cartoon characters + amplitude mouth-swap (bolta hua mooh, believable)
  - [ ] v3 (optional): Rhubarb phoneme-accurate mouth shapes
  - Note: characters ab flat cartoon style mein generate hote hain (mouth-swap ke liye)
  - Multi-character speaking detection · *(Phase 10, part 5)* ✅
- [~] **R2 — Character Expressions & Animation** · L
  - [x] R2-A free procedural: emotion-driven motion (bounce/shake/sway/droop) + breathing + speech bob
  - [x] R2-B Runware video API VERIFIED: image→video (reference-quality animation) kaam karta hai
  - [ ] R2-B integration (HD mode): lipsync model + AI-video bg removal + compose
  - Findings: AI-video ~3min/clip, black bg (remove karna hoga), Kling = generic motion (lipsync model = audio-synced) · *(Phase 5, 11, 12)*
- [ ] **R3 — Camera Director** · M
  - Shot types, zoom, pan, speaker cuts, reaction shots · *(Phase 6, part 16)*
- [ ] **R4 — Audio Depth: Music + SFX** · M
  - Mood music + ducking, SFX library + auto-insert · *(Phase 13, 14)*
- [ ] **R5 — Subtitle Engine Pro** · S–M
  - Word-level timing, karaoke highlight, speaker colors · *(Phase 15 rest)*
- [ ] **R6 — Editing & Transitions** · M
  - Cuts, transitions, slow-mo, speed-ramp, B-roll · *(Phase 16 rest)*

### ✅ Bonus done — Custom Character Library (Phase 2 ka hissa)
- [x] User apni PNG characters de sakta hai (`characters/` + `characters.json`)
- [x] Auto background-removal (rembg) — Gemini ka checkerboard hat jata hai
- [x] Script-character → user image auto-match (Urdu/English keywords)
- [x] Per-character mouth-point (lip-sync) + circle/as-is layout
- [x] 20 fruit/veg characters added & tested ✅

### Group B — Infrastructure
- [ ] **R7 — Rendering Pro + Performance** · L
  - 2K/4K, 60fps, GPU (NVENC), chunk/resume, cache, parallel · *(Phase 17, 20)*
- [ ] **R8 — Offline Mode** · XL ⚠️ (GPU chahiye)
  - Offline TTS (Piper/Coqui), local SD images, local LLM · *(Phase 9 offline)*
- [ ] **R9 — AI Director** · XL
  - Auto pacing/camera/music/emotion/editing decisions · *(Phase 18)*

### Group C — Product
- [ ] **R10 — Desktop App + Foundation** · L
  - Electron+React+TS, Asset Manager, Project Manager, settings, logging, autosave · *(Phase 1, 2, 19)*
- [ ] **R11 — Export + Assistant + Plugins** · M
  - Multi-format export + presets, AI Assistant, Plugin system · *(Phase 21, 22, 23)*
- [ ] **R12 — Licensing & Release** · M
  - Offline activation, installer, docs, testing, benchmark, stable · *(Phase 24, 25)*

---

## Recommended order
`R1 → R2 → R3 → R4 → R5 → R6 → R10 → R7 → R9 → R11 → R12 → R8`

Effort: S=days · M=~week · L=weeks · XL=months
