"""
M3+M4 — 2D Compositor & Render (Phase 5(2D), 13, 15, 16, 17).
timeline + assets -> final 1920x1080 landscape video.

Har dialogue line ek clip:  scene background + bolne wale ka avatar (talk-bob) +
naam label + caption + us line ki awaaz.  Sab clips jod kar final video.

Lip-sync v0.1: avatar ka halka "talk bob" (bolte waqt). Asli phoneme lip-sync
(Rhubarb/SadTalker) baad ka upgrade hai.
"""
import glob
import json
import math
import os

import numpy as np
from PIL import Image

from moviepy import (ImageClip, AudioFileClip, CompositeVideoClip,
                     CompositeAudioClip, concatenate_videoclips,
                     VideoFileClip, VideoClip, vfx)

import config
import text_render
import lipsync
import motion
import transitions
import video_gen
import audio
import puppet
# captions_whisper (faster-whisper/torch — heavy) lazy import hota hai — sirf captions on ho to

# per-speaker caption highlight colors (P2)
_SPK_COLORS = ["#FFE000", "#4ADE80", "#60A5FA", "#F472B6", "#FBBF24", "#A78BFA"]

VW, VH = 1920, 1080      # render() mein config se set hote hain
FPS = 30

_NVENC = None


def _delivery_args(height, fps):
    rates = [(2160, 35), (1440, 16), (1080, 8), (720, 5), (0, 3)]
    mbps = next(rate for minimum, rate in rates if height >= minimum)
    if fps > 30:
        mbps = int(round(mbps * 1.5))
    return ["-profile:v", "high", "-bf", "2", "-g", str(max(12, int(fps))),
            "-b:v", f"{mbps}M", "-maxrate", f"{int(mbps * 1.5)}M",
            "-bufsize", f"{mbps * 2}M", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-colorspace", "bt709"]


def _codec():
    """GPU (NVENC) available ho to use, warna libx264 (P6)."""
    global _NVENC
    if config.GPU_ENCODE == "off":
        return "libx264"
    if _NVENC is None:
        try:
            import subprocess
            out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                                 capture_output=True, text=True).stdout
            _NVENC = "h264_nvenc" in out
        except Exception:
            _NVENC = False
    if config.GPU_ENCODE == "on":
        return "h264_nvenc"
    return "h264_nvenc" if _NVENC else "libx264"


def _write_clip(clip, out_path):
    codec = _codec()
    clip.write_videofile(
        out_path, fps=FPS, codec=codec, audio_codec="aac",
        preset=("medium" if codec == "libx264" else "fast"),
        bitrate=("8M" if VH >= 1080 else "5M"),
        audio_bitrate=getattr(config, "AUDIO_BITRATE", "384k"),
        ffmpeg_params=_delivery_args(VH, FPS) + ["-movflags", "+faststart"],
        threads=4, logger=None)


def _load_meta(av_path):
    """char_<id>.json (mouth, circle, draw_mouth) — na ho to defaults."""
    p = av_path.replace(".png", ".json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"mouth": [0.5, 0.575], "circle": True, "draw_mouth": True}


def _bg_array(path):
    """Background ko exactly 1920x1080 cover-crop karo."""
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    scale = max(VW / iw, VH / ih)
    img = img.resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
    iw, ih = img.size
    left, top = (iw - VW) // 2, (ih - VH) // 2
    img = img.crop((left, top, left + VW, top + VH))
    return np.array(img)


def _line_clip(entry, scene_bg, char_avatar, char_names, preset, char_colors, char_rigs=None):
    dur = max(1.0, float(entry["duration"]) + 0.25)  # thora sa breathing gap
    audio_path = os.path.join(entry["_proj"], entry["audio"])

    # cinematic mode: har line ka apna full-scene AI image (character+costume+bg baked)
    scene_img = entry.get("scene_image")
    cinematic_line = bool(scene_img and os.path.exists(scene_img))

    # background — Ken Burns 2.0 (cinematic ho to scene image; warna per-scene bg)
    bg_path = scene_img if cinematic_line else scene_bg.get(entry["scene"])
    direction = motion.direction_for_scene(entry["scene"])
    bg = motion.kenburns_clip(bg_path, dur, VW, VH, fps=FPS,
                              direction=direction, zoom=preset["zoom"])
    layers = [bg]

    # speaker character
    av_path = char_avatar.get(entry["speaker"])
    rig_dir = (char_rigs or {}).get(entry["speaker"])
    emotion = entry.get("emotion", "neutral")
    name = char_names.get(entry["speaker"], entry["speaker"])
    lbl_xy = None

    if not cinematic_line and rig_dir and os.path.exists(os.path.join(rig_dir, "rig.json")):
        # PUPPET animation — AI-rigged: real lip-sync + blink + expression (local, free)
        target_h = int(VH * 0.74)
        av_x = VW // 2 - int(target_h * 0.42)
        av_y = VH - target_h - 8
        pclip, openness = puppet.puppet_clip(rig_dir, audio_path, dur,
                                             target_h=target_h, fps=FPS, emotion=emotion)
        amp = 26 if emotion == "angry" else 15
        freq = 2.3 if emotion == "angry" else 1.5
        avatar = pclip.with_position(
            lambda t, y=av_y: (av_x + int(amp * math.sin(t * freq)), y + int(7 * openness(t))))
        layers.append(avatar)
        lbl_xy = (av_x + 20, av_y)

    elif not cinematic_line and av_path and os.path.exists(av_path):
        meta = _load_meta(av_path)
        mouth = tuple(meta.get("mouth") or (0.5, 0.575))
        draw_mouth = meta.get("draw_mouth", True)
        circle = meta.get("circle", True)
        target_h = 360 if circle else int(VH * 0.72)
        av_x = 90
        av_y = VH - target_h - (90 if circle else 20)

        if config.RENDER_MODE == "cinematic":
            key = os.path.splitext(os.path.basename(entry["audio"]))[0]
            clip_path = os.path.join(entry["_proj"], "ai_clips", key + ".mp4")
            video_gen.animate_character(
                av_path, video_gen.char_prompt(name, emotion), dur, clip_path)
            vc = VideoFileClip(clip_path)
            vc = vc.subclipped(0, min(dur, vc.duration)).resized(height=target_h)
            vc = vc.with_effects([vfx.MaskColor(color=(0, 0, 0), threshold=70, stiffness=2)])
            avatar = vc.with_position((av_x, av_y))
        else:
            openness, _ = lipsync.amplitude_envelope(audio_path, fps=FPS)
            avatar = (lipsync.talking_avatar_clip(av_path, openness, dur,
                                                  target_h=target_h, mouth=mouth,
                                                  draw_mouth=draw_mouth, emotion=emotion)
                      .with_position(lipsync.motion_position(
                          emotion, openness, av_x, av_y,
                          intensity=preset["char"], parallax_dir=direction,
                          parallax_amt=preset["parallax"])))
        layers.append(avatar)
        lbl_xy = (av_x + 20, av_y)

    # naam label
    if lbl_xy:
        label = text_render.render_label(name)
        lbl = (ImageClip(label, transparent=True).with_duration(dur)
               .with_position((lbl_xy[0], lbl_xy[1] - label.shape[0] - 6)))
        layers.append(lbl)

    # caption — P2 karaoke (whisper word-timing) + per-speaker color
    cs = config.CAPTIONS
    if cs.get("enabled", True):
        words = entry.get("_words")
        if words is None:
            import captions_whisper
            words = captions_whisper.word_timings(audio_path)
        capH = int(cs["font_size"] * 2.4)
        if cs.get("position") == "top":
            cap_y = cs.get("margin", 110)
        elif cs.get("position") == "center":
            cap_y = (VH - capH) // 2
        else:
            cap_y = VH - capH - cs.get("margin", 110)

        hl = char_colors.get(entry["speaker"]) if cs.get("per_speaker_color") else None

        if words:
            def capframe(t):
                return text_render.render_karaoke_frame(words, t, VW, cs, hl)
            cap_rgb = VideoClip(lambda t: capframe(t)[:, :, :3], duration=dur)
            cap_mask = VideoClip(lambda t: capframe(t)[:, :, 3] / 255.0,
                                 duration=dur, is_mask=True)
            cap_clip = cap_rgb.with_mask(cap_mask).with_position((0, cap_y))
        else:
            # fallback: static phrase caption
            cap = text_render.render_caption(entry["text"], video_w=VW)
            cap_clip = (ImageClip(cap, transparent=True).with_duration(dur)
                        .with_position(("center", VH - cap.shape[0] - 60)))
        try:
            cap_clip = cap_clip.with_effects([vfx.CrossFadeIn(0.2)])  # entrance
        except Exception:
            pass
        layers.append(cap_clip)

    clip = CompositeVideoClip(layers, size=(VW, VH)).with_duration(dur)

    # audio
    audio = AudioFileClip(os.path.join(entry["_proj"], entry["audio"]))
    clip = clip.with_audio(audio)
    return clip


def _add_music(final, proj_dir, moods):
    """Mood-based music (assets/music/<mood>/) dialogue ke neeche (ducking volume)."""
    track = audio.select_music(moods)
    if not track:
        return final
    try:
        music = AudioFileClip(track)
        end = min(music.duration, final.duration)
        music = music.subclipped(0, end)
        try:
            music = music.with_volume_scaled(config.MUSIC_VOLUME)
        except Exception:
            pass
        mixed = CompositeAudioClip([final.audio, music])
        final = final.with_audio(mixed)
        print(f"  [music] {os.path.basename(track)} @ {config.MUSIC_VOLUME}")
    except Exception as e:
        print(f"  [music skip] {e}")
    return final


def _vignette_array(w, h):
    """Cinematic vignette (kinaron par halka andhera) — RGBA."""
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    alpha = np.clip((d - 0.6) / 0.7, 0, 1) * 150
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = alpha.astype(np.uint8)
    return rgba


def _apply_overlays(final):
    """Vignette + (optional) overlay video (sparks/light-leak) final par."""
    layers = [final]
    if config.VIGNETTE:
        vig = ImageClip(_vignette_array(VW, VH), transparent=True).with_duration(final.duration)
        layers.append(vig)
    ov = audio.overlay_file()
    if ov:
        try:
            oc = VideoFileClip(ov).without_audio()
            oc = oc.with_effects([vfx.Loop(duration=final.duration)])
            oc = oc.resized((VW, VH)).with_opacity(config.OVERLAY_OPACITY)
            layers.append(oc)
            print(f"  [overlay] {os.path.basename(ov)}")
        except Exception as e:
            print(f"  [overlay skip] {e}")
    if len(layers) == 1:
        return final
    return CompositeVideoClip(layers, size=(VW, VH)).with_audio(final.audio)


def _render_chunk(entry, scene_bg, char_avatar, char_names, pr, char_colors, out_path,
                  char_rigs=None):
    """Ek line ko chunk mp4 mein render karo (resume: pehle se ho to skip)."""
    if config.RESUME and os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        return out_path
    clip = _line_clip(entry, scene_bg, char_avatar, char_names, pr, char_colors, char_rigs)
    _write_clip(clip, out_path)
    try:
        clip.close()
    except Exception:
        pass
    return out_path


def _ffprobe_dur(path):
    import subprocess
    out = subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path])
    return float(json.loads(out)["format"]["duration"])


def _assemble_ffmpeg(tasks, proj_dir, moods, transition_plan, out_path):
    """
    Final video ffmpeg se jodo (native xfade+acrossfade+music+vignette) — moviepy ke
    frame-by-frame compose se ~10x tez. Fail ho to False return (moviepy fallback).
    """
    import subprocess
    paths = [cp for _, cp in tasks]
    if not paths:
        return False
    durs = [_ffprobe_dur(p) for p in paths]
    n = len(paths)
    fc, vlabel, alabel, total = transitions.build_av_filter_graph(
        durs, transition_plan)

    inputs = []
    for p in paths:
        inputs += ["-i", p]

    # vignette (static png, looped)
    vig_idx = None
    vig_png = None
    if config.VIGNETTE:
        vig_png = os.path.join(proj_dir, "_vignette.png")
        Image.fromarray(_vignette_array(VW, VH), "RGBA").save(vig_png)
        inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", vig_png]
        vig_idx = n

    # music
    music_idx = None
    track = audio.select_music(moods)
    if track:
        inputs += ["-i", track]
        music_idx = n + (1 if vig_idx is not None else 0)

    # vignette overlay
    if vig_idx is not None:
        fc.append(f"[{vlabel}][{vig_idx}:v]overlay=0:0:shortest=1[vout]")
        vlabel = "vout"
    # music mix (dialogue full + music low)
    if music_idx is not None:
        fc.append(f"[{music_idx}:a]volume={config.MUSIC_VOLUME}[mus]")
        fc.append(f"[{alabel}][mus]amix=inputs=2:duration=first:normalize=0[aout]")
        alabel = "aout"

    codec = _codec()
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", f"[{vlabel}]", "-map", f"[{alabel}]",
           "-c:v", codec, "-pix_fmt", "yuv420p",
           "-preset", ("medium" if codec == "libx264" else "fast"),
           *_delivery_args(VH, FPS), "-c:a", "aac",
           "-b:a", getattr(config, "AUDIO_BITRATE", "384k"),
           "-r", str(FPS), "-movflags", "+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ffmpeg assemble fail] {r.stderr[-500:]}", flush=True)
        return False
    return True


def _chunk_worker(payload):
    """ProcessPool worker — alag process, isliye module globals (VW/VH/FPS) yahan set karo."""
    global VW, VH, FPS
    (entry, scene_bg, char_avatar, char_names, pr, char_colors, cp, char_rigs, dims) = payload
    VW, VH, FPS = dims
    _render_chunk(entry, scene_bg, char_avatar, char_names, pr, char_colors, cp, char_rigs)
    return cp


def render(timeline, scene_bg, char_avatar, parsed, proj_dir, out_path,
           on_progress=None, char_rigs=None):
    global VW, VH, FPS
    VW, VH = config.get_dimensions()
    FPS = config.FPS

    char_names = {c["id"]: c.get("name", c["id"]) for c in parsed.get("characters", [])}
    char_colors = {c["id"]: _SPK_COLORS[i % len(_SPK_COLORS)]
                   for i, c in enumerate(parsed.get("characters", []))}
    for e in timeline:
        e["_proj"] = proj_dir

    pr = motion.preset()
    total = len(timeline)

    # 1) Whisper word-timings pehle (sequential, singleton — parallel-safe)
    if config.CAPTIONS.get("enabled", True):
        import captions_whisper
        for i, e in enumerate(timeline, start=1):
            if on_progress:
                on_progress(i, total, f"Caption timing {i}/{total}")
            e["_words"] = captions_whisper.word_timings(
                os.path.join(proj_dir, e["audio"]))

    # 2) Chunks render (parallel + resume + GPU)
    chunks_dir = os.path.join(proj_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)
    tasks = []
    for e in timeline:
        key = os.path.splitext(os.path.basename(e["audio"]))[0]
        cp = os.path.join(chunks_dir, f"{key}_{VW}x{VH}.mp4")
        tasks.append((e, cp))

    done = [0]

    def work(args):
        e, cp = args
        _render_chunk(e, scene_bg, char_avatar, char_names, pr, char_colors, cp, char_rigs)
        done[0] += 1
        if on_progress:
            on_progress(done[0], total, f"Render chunk {done[0]}/{total}")
        return cp

    n_par = min(config.RENDER_WORKERS, len(tasks))
    parallel = n_par > 1 and len(tasks) > 1
    used_process = False

    # PROCESS backend: asli parallelism (GIL bypass) — CPU-bound PIL/render tez
    if parallel and config.RENDER_BACKEND == "process":
        try:
            from concurrent.futures import ProcessPoolExecutor
            dims = (VW, VH, FPS)
            payloads = [(e, scene_bg, char_avatar, char_names, pr, char_colors, cp, char_rigs, dims)
                        for e, cp in tasks]
            with ProcessPoolExecutor(max_workers=n_par) as ex:
                for _cp in ex.map(_chunk_worker, payloads):
                    done[0] += 1
                    if on_progress:
                        on_progress(done[0], total, f"Render chunk {done[0]}/{total}")
            used_process = True
        except Exception as e:
            print(f"  [render] process pool fail ({e}) -> thread fallback", flush=True)
            done[0] = 0

    if not used_process:
        if parallel:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=n_par) as ex:
                list(ex.map(work, tasks))
        else:
            for t in tasks:
                work(t)

    # 3) Chunks jodo + transitions + music + overlays
    transition_plan = transitions.plan_transitions(timeline, pr["trans"])
    try:
        json.dump(transition_plan,
                  open(os.path.join(proj_dir, "transitions.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception:
        pass
    print(f"  [transitions] {transitions.summarize(transition_plan)}", flush=True)
    moods = [e.get("mood") for e in timeline]
    if on_progress:
        on_progress(total, total, "Final render (FFmpeg)...")

    # FAST PATH: native ffmpeg assembly (~10x tez); fail ho to moviepy fallback
    if config.RENDER_BACKEND != "thread":   # 'thread' = purana behaviour force
        try:
            if _assemble_ffmpeg(tasks, proj_dir, moods, transition_plan, out_path):
                return out_path
        except Exception as e:
            print(f"  [ffmpeg assemble error] {e} -> moviepy fallback", flush=True)

    clips = [VideoFileClip(cp) for _, cp in tasks]
    try:
        final = clips[0]
        for clip, item in zip(clips[1:], transition_plan):
            seconds = transitions.overlap(item)
            if seconds > 0:
                clip = clip.with_effects([vfx.CrossFadeIn(seconds)])
                final = concatenate_videoclips([final, clip], method="compose",
                                               padding=-seconds)
            else:
                final = concatenate_videoclips([final, clip], method="compose")
    except Exception as e:
        print(f"  [transition fallback] {e}")
        final = concatenate_videoclips(clips, method="compose")

    final = _add_music(final, proj_dir, moods)
    final = _apply_overlays(final)
    _write_clip(final, out_path)

    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    try:
        final.close()
    except Exception:
        pass
    return out_path
