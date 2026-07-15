"""
SBZ AI Video Studio — full pipeline (M1..M4).
    python build.py sample_script.txt

Script -> story.json -> voices -> assets -> final 1080p video.
"""
import json
import os
import sys
import time

import config
import story_parser
import voice_engine
import assets as assets_mod
import compositor

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _p(stage):
    def cb(i, t, m):
        print(f"  [{stage} {i}/{t}] {m}", flush=True)
    return cb


def apply_settings(s):
    """UI/dict se settings config par apply karo (per-run override). P8."""
    if not s:
        return
    # P9 — platform preset (youtube/shorts/tiktok/...) expand karo
    import export
    if s.get("platform") in export.PLATFORM_PRESETS:
        for k, v in export.PLATFORM_PRESETS[s["platform"]].items():
            s.setdefault(k, v)
    simple = {
        "style": ("STYLE", str), "quality": ("VIDEO_QUALITY", str),
        "aspect": ("ASPECT", str), "fps": ("FPS", int),
        "motion_preset": ("MOTION_PRESET", str), "render_mode": ("RENDER_MODE", str),
        "fast_preview": ("FAST_PREVIEW", bool), "gpu": ("GPU_ENCODE", str),
        "music_volume": ("MUSIC_VOLUME", float), "vignette": ("VIGNETTE", bool),
        "voice_volume": ("VOICE_VOLUME", str), "tts_provider": ("TTS_PROVIDER", str),
        "voice_speed": ("VOICE_SPEED", float), "edge_voice": ("EDGE_VOICE", str),
        "google_tts_voice": ("GOOGLE_TTS_VOICE", str),
        "elevenlabs_voice_id": ("ELEVENLABS_VOICE_ID", str),
        "llm_provider": ("LLM_PROVIDER", str), "llm_model": ("LLM_MODEL", str),
        "image_provider": ("IMAGE_PROVIDER", str),
        "render_workers": ("RENDER_WORKERS", int), "story_mode": ("STORY_MODE", str),
        "multi_char": ("BLENDER3D_MULTI", bool), "render_engine": ("RENDER_ENGINE", str),
        "subtitles_on": ("SUBTITLES_ON", bool), "intro_on": ("INTRO_ON", bool),
        "outro_on": ("OUTRO_ON", bool),
    }
    for k, (attr, typ) in simple.items():
        if k in s and s[k] not in (None, ""):
            try:
                setattr(config, attr, typ(s[k]))
            except Exception:
                pass
    config.VOICE_SPEED = max(0.7, min(1.2, float(getattr(config, "VOICE_SPEED", 1.0))))
    # Urdu accent (Indian ur-IN / Pakistani ur-PK) -> VOICE_MAP switch
    if s.get("urdu_accent"):
        try:
            config.set_urdu_accent(s["urdu_accent"])
        except Exception:
            pass
    cap = s.get("captions") or {}
    for k, v in cap.items():
        if v in (None, ""):
            continue
        if k in ("words_per_group", "font_size", "outline_size"):
            v = int(v)
        if k in ("enabled", "per_speaker_color"):
            v = bool(v)
        config.CAPTIONS[k] = v
    # One public subtitle switch drives both render pipelines.  Older projects
    # only stored captions.enabled, so preserve their choice when resumed.
    if "subtitles_on" in s:
        config.CAPTIONS["enabled"] = bool(config.SUBTITLES_ON)
    elif "enabled" in cap:
        config.SUBTITLES_ON = bool(config.CAPTIONS["enabled"])


def _cinematic_scene_images(parsed, timeline, proj_dir, on_progress=None):
    """Har timeline line ke liye ek full-scene AI image (parallel). scene_image attach."""
    import cinematic
    from concurrent.futures import ThreadPoolExecutor
    all_lines = [(sc, ln) for sc in parsed.get("scenes", []) for ln in sc.get("lines", [])]
    chars_by_id = {c["id"]: c for c in parsed.get("characters", [])}
    VW, VH = config.get_dimensions()
    sdir = os.path.join(proj_dir, "scenes")
    os.makedirs(sdir, exist_ok=True)
    total = min(len(all_lines), len(timeline))
    done = [0]

    def work(idx):
        sc, ln = all_lines[idx]
        e = timeline[idx]
        img = os.path.join(sdir, f"scene_{idx + 1}.png")
        if not (os.path.exists(img) and os.path.getsize(img) > 10000):
            try:
                cinematic.generate_scene(cinematic.scene_prompt(parsed, ln, chars_by_id),
                                         img, VW, VH)
            except Exception as ex:
                print(f"  [scene img {idx + 1} fail] {ex}", flush=True)
                return
        e["scene_image"] = img
        done[0] += 1
        if on_progress:
            on_progress(done[0], total, f"Scene image {done[0]}/{total}")

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(work, range(total)))


def build(script_text, proj_name=None, on_progress=None, settings=None, parsed=None,
          should_cancel=None):
    """
    on_progress(stage, i, total, msg) — stage: 'story'|'voice'|'asset'|'render'.
    settings: UI se per-run overrides (style, quality, aspect, captions, ...).
    parsed: agar diya ho (preview se edit hua plan) to LLM parse skip, seedha isi par render.
    """
    apply_settings(settings)
    def stage(name):
        def cb(i, t, m):
            if on_progress:
                on_progress(name, i, t, m)
            print(f"  [{name} {i}/{t}] {m}", flush=True)
        return cb

    proj_name = proj_name or f"project-{int(time.time())}"
    proj_dir = os.path.join(config.PROJECTS_DIR, proj_name)
    os.makedirs(proj_dir, exist_ok=True)

    print("\n[1/4] 🧠 Story parse...")
    stage("story")(0, 1, "Script analyze ho raha hai...")
    if parsed:
        parsed = story_parser._assign_voices(parsed)   # edited plan — voices ensure karo
    else:
        parsed = story_parser.parse_script(script_text)
    json.dump(parsed, open(os.path.join(proj_dir, "story.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    nc, ns, nl = story_parser.stats(parsed)
    stage("story")(1, 1, f"{nc} characters, {ns} scenes, {nl} lines")

    cinematic_mode = config.STORY_MODE == "cinematic"
    blender3d_mode = config.STORY_MODE == "blender3d"
    if cinematic_mode:
        import cinematic
        stage("story")(1, 1, "Cinematic tayyari: character bibles + costumes...")
        cinematic.prepare(parsed)

    print("[2/4] 🎙️  Voices...")
    timeline = voice_engine.generate_voices(parsed, proj_dir, on_progress=stage("voice"))
    json.dump(timeline, open(os.path.join(proj_dir, "timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    if should_cancel and should_cancel():
        import blender3d
        raise blender3d.Cancelled()

    out_path = os.path.join(proj_dir, "final.mp4")

    if blender3d_mode:
        # BLENDER 3D: character asal 3D ENVIRONMENT glb mein khada hota hai -> AI 2D
        # background use NAHI hota. Isliye background generation SKIP (tez + koi
        # Runware/network cost/crash nahi). Style ab 3D-look (rang/roshni) control karta.
        stage("asset")(1, 1, "3D environment (background gen skip — tez)")
        scene_bg = {}
        print("[4/4] 🧊 Blender 3D render (per line)...")
        import blender3d
        blender3d.render_3d_video(parsed, timeline, scene_bg, proj_dir, out_path,
                                  on_progress=stage("render"), should_cancel=should_cancel)
    else:
        if cinematic_mode:
            print("[3/4] 🎬 Cinematic scene images (per line)...")
            scene_bg, char_avatar, char_rigs = {}, {}, {}
            _cinematic_scene_images(parsed, timeline, proj_dir, on_progress=stage("asset"))
        else:
            print("[3/4] 🎨 Assets (backgrounds + characters + rigs)...")
            scene_bg, char_avatar, char_rigs = assets_mod.build_assets(
                parsed, proj_dir, on_progress=stage("asset"))

        print("[4/4] 🎬 Compositing + render...")
        compositor.render(timeline, scene_bg, char_avatar, parsed, proj_dir, out_path,
                          on_progress=stage("render"), char_rigs=char_rigs)

    # P7 — project metadata (list/load ke liye)
    try:
        import projects_mgr
        projects_mgr.save_metadata(proj_dir, parsed, settings, (nc, ns, nl))
    except Exception as e:
        print(f"  [metadata skip] {e}")

    # P9 — auto-export (srt + thumbnail; seo agar maanga)
    try:
        import export
        want = ["srt", "thumbnail"]
        if (settings or {}).get("seo"):
            want.append("seo")
        export.export_all(proj_dir, timeline, parsed, script_text, want=want)
    except Exception as e:
        print(f"  [export skip] {e}")

    print(f"\n✅ Video ready -> {out_path}\n")
    return {"video": out_path, "proj": proj_name,
            "video_rel": f"{proj_name}/final.mp4", "title": parsed.get("title")}


def main():
    if len(sys.argv) < 2:
        print("Istemaal: python build.py <script-file.txt>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        build(f.read())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        sys.exit(1)
