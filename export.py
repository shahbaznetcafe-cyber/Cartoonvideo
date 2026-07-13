"""
P9 — Export & Publish.
Platform presets, SRT subtitles, audio-only, thumbnail, SEO (title/desc/hashtags).
"""
import json
import os
import subprocess

from PIL import Image, ImageEnhance, ImageFilter, ImageStat

import config
import text_render

# Platform presets -> settings (aspect/quality/fps)
PLATFORM_PRESETS = {
    "youtube":  {"aspect": "landscape", "quality": "1080p", "fps": 30},
    "shorts":   {"aspect": "portrait",  "quality": "1080p", "fps": 30},
    "tiktok":   {"aspect": "portrait",  "quality": "1080p", "fps": 30},
    "reels":    {"aspect": "portrait",  "quality": "1080p", "fps": 30},
    "facebook": {"aspect": "square",    "quality": "1080p", "fps": 30},
}


def _fmt(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def export_srt(timeline, out_path):
    """Timeline se .srt (har line ek cue, cumulative timing)."""
    lines, t = [], 0.0
    for i, e in enumerate(timeline, start=1):
        dur = float(e.get("duration", 2)) + 0.25
        lines += [str(i), f"{_fmt(t)} --> {_fmt(t + dur)}", e.get("text", ""), ""]
        t += dur
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def export_audio(video_path, out_path):
    """Sirf awaaz (mp3) nikaalo."""
    subprocess.run([config.FFMPEG_PATH if hasattr(config, "FFMPEG_PATH") else "ffmpeg",
                    "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2",
                    out_path], capture_output=True)
    return out_path


def _duration(path):
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path], text=True)
        return float(raw.strip())
    except Exception:
        return 10.0


def export_thumbnail(video_path, title, out_path, at=None):
    """Choose a detailed story frame and build a clean 16:9 YouTube thumbnail."""
    duration = _duration(video_path)
    times = [at] if at is not None else [duration * 0.12, duration * 0.42, duration * 0.72]
    candidates = []
    for idx, second in enumerate(times):
        tmp = f"{out_path}.frame{idx}.png"
        second = max(0.5, min(float(second), max(0.5, duration - 2.5)))
        subprocess.run(["ffmpeg", "-y", "-ss", f"{second:.2f}", "-i", video_path,
                        "-frames:v", "1", tmp], capture_output=True)
        if os.path.exists(tmp):
            image = Image.open(tmp).convert("RGB")
            gray = image.convert("L").resize((320, 180))
            # Flat wall/sky failures score poorly; detailed character frames score well.
            score = gray.entropy() + ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0] / 18
            candidates.append((score, image.copy(), tmp))
    if not candidates:
        return None
    _, best, _ = max(candidates, key=lambda item: item[0])
    for _, _, tmp in candidates:
        try:
            os.remove(tmp)
        except OSError:
            pass

    best = best.resize((1920, 1080), Image.Resampling.LANCZOS)
    best = ImageEnhance.Color(best).enhance(1.08)
    best = ImageEnhance.Contrast(best).enhance(1.06).convert("RGBA")
    W, H = best.size
    # Soft top shade protects large title text without turning the frame into a poster.
    shade = Image.new("RGBA", (W, int(H * 0.30)), (0, 0, 0, 0))
    alpha = shade.getchannel("A")
    for y in range(shade.height):
        value = int(145 * (1 - y / max(1, shade.height - 1)))
        for x in range(W):
            alpha.putpixel((x, y), value)
    shade.putalpha(alpha)
    best.alpha_composite(shade, (0, 0))
    if title:
        cap = text_render.render_caption(title, video_w=W, font_size=int(H * 0.085))
        cimg = Image.fromarray(cap)
        best.alpha_composite(cimg, ((W - cimg.width) // 2, int(H * 0.045)))
    best.convert("RGB").save(out_path, quality=94, subsampling=0)
    return out_path


def generate_seo(script_text, language="urdu"):
    """LLM se YouTube title + description + hashtags."""
    import providers
    sysp = ("You are a YouTube SEO expert. From the script, produce JSON with keys: "
            "title (catchy, <70 chars), description (2-3 lines), hashtags (array of 6-8). "
            "Reply ONLY JSON.")
    user = f"Language: {language}\nScript:\n{script_text[:600]}"
    try:
        raw = providers.llm_generate(sysp, user, max_tokens=400, temperature=0.7)
        raw = raw.strip().strip("`")
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e + 1])
    except Exception as ex:
        return {"title": "", "description": "", "hashtags": [], "error": str(ex)}


def export_all(proj_dir, timeline, parsed, script_text=None, want=("srt", "thumbnail")):
    """Project ke liye chuni hui export cheezein banao. return dict of paths."""
    out = {}
    final = os.path.join(proj_dir, "final.mp4")
    if "srt" in want:
        out["srt"] = export_srt(timeline, os.path.join(proj_dir, "subtitles.srt"))
    if "audio" in want and os.path.exists(final):
        out["audio"] = export_audio(final, os.path.join(proj_dir, "audio.mp3"))
    if "thumbnail" in want and os.path.exists(final):
        out["thumbnail"] = export_thumbnail(
            final, parsed.get("title", ""), os.path.join(proj_dir, "thumbnail.jpg"))
    if "seo" in want and script_text:
        seo = generate_seo(script_text, parsed.get("language", "urdu"))
        json.dump(seo, open(os.path.join(proj_dir, "seo.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        out["seo"] = seo
    return out
