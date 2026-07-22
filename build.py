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
        "fast_preview": ("FAST_PREVIEW", bool), "gpu": ("GPU_ENCODE", str),
        "music_volume": ("MUSIC_VOLUME", float), "music_track": ("MUSIC_TRACK", str), "vignette": ("VIGNETTE", bool),
        "voice_volume": ("VOICE_VOLUME", str), "tts_provider": ("TTS_PROVIDER", str),
        "voice_speed": ("VOICE_SPEED", float), "edge_voice": ("EDGE_VOICE", str),
        "google_tts_voice": ("GOOGLE_TTS_VOICE", str),
        "elevenlabs_voice_id": ("ELEVENLABS_VOICE_ID", str),
        "llm_provider": ("LLM_PROVIDER", str), "llm_model": ("LLM_MODEL", str),
        "image_provider": ("IMAGE_PROVIDER", str),
        "render_workers": ("RENDER_WORKERS", int),
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


def build(script_text, proj_name=None, on_progress=None, settings=None, parsed=None,
          should_cancel=None):
    """
    on_progress(stage, i, total, msg) — stage: 'story'|'voice'|'asset'|'render'.
    settings: UI se per-run overrides (style, quality, aspect, captions, ...).
    parsed: agar diya ho (preview se edit hua plan) to LLM parse skip, seedha isi par render.
    """
    apply_settings(settings)
    target_dur = (settings or {}).get("target_duration") or (settings or {}).get("length")
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
        target_dur = (settings or {}).get("target_duration") or (settings or {}).get("length")
        parsed = story_parser.parse_script(script_text, target_duration=target_dur)
    story_parser.normalize_parsed_directions(parsed)
    import character_performance
    character_performance.annotate_story_requirements(parsed)
    json.dump(parsed, open(os.path.join(proj_dir, "story.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    nc, ns, nl = story_parser.stats(parsed)
    stage("story")(1, 1, f"{nc} characters, {ns} scenes, {nl} lines")

    print("[2/4] 🎙️  Voices...")
    timeline = voice_engine.generate_voices(
        parsed, proj_dir, on_progress=stage("voice"), should_cancel=should_cancel)
    json.dump(timeline, open(os.path.join(proj_dir, "timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    if should_cancel and should_cancel():
        import blender3d
        raise blender3d.Cancelled()

    out_path = os.path.join(proj_dir, "final.mp4")

    # 3D pipeline: character asal 3D ENVIRONMENT glb mein khada hota hai. AI 2D
    # background sirf threejs engine ke reusable plates ke liye generate hota hai.
    stage("asset")(1, 1, "3D environment")
    # The selected renderer comes from apply_settings(); resolve it before the background gate.
    engine = getattr(config, "RENDER_ENGINE", "threejs")
    if getattr(config, "THREEJS_AI_BACKGROUNDS", True) and engine == "threejs":
        print("[3/4] Reusable AI background plates...")
        scene_bg = assets_mod.build_scene_backgrounds(
            parsed, proj_dir, on_progress=stage("asset"))
    else:
        scene_bg = {}
    print("[4/4] 🧊 3D render (per line)...")
    import blender3d
    blender3d.render_3d_video(parsed, timeline, scene_bg, proj_dir, out_path,
                              on_progress=stage("render"), should_cancel=should_cancel,
                              target_duration=target_dur)

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
