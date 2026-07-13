"""
R1 — Lip-Sync (2D), v1: audio-amplitude driven.
Har line ki awaaz ki loudness se mooh ki openness nikalta hai, aur avatar par
ek animated mooh + halki jaw-motion lagata hai. Asli speech ke saath synced.

(v2 upgrade: Rhubarb se phoneme-accurate mouth shapes.)
"""
import math
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from moviepy import VideoClip


def amplitude_envelope(audio_path, fps=30, sr=8000):
    """Audio -> per-frame openness (0..1) ka function + duration."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", audio_path,
         "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True,
    )
    data = np.frombuffer(out.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if data.size == 0:
        return (lambda t: 0.0), 0.0

    dur = data.size / sr
    win = max(1, sr // fps)
    n = int(np.ceil(data.size / win))
    env = np.zeros(n, dtype=np.float32)
    for i in range(n):
        chunk = data[i * win:(i + 1) * win]
        if chunk.size:
            env[i] = np.sqrt(np.mean(chunk ** 2))

    if env.max() > 0:
        env = env / env.max()
    # halka smooth (jhatke kam) + thori boost
    if n >= 3:
        env = np.convolve(env, np.ones(3) / 3, mode="same")
    env = np.clip(env * 1.25, 0.0, 1.0)

    def openness(t):
        idx = int(t * fps)
        idx = 0 if idx < 0 else (n - 1 if idx >= n else idx)
        return float(env[idx])

    return openness, dur


def _energy_frames(audio_path, fps=24, sr=16000):
    """Audio -> per-frame RMS energy array (0..1 normalized), n, duration."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", audio_path,
         "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True,
    )
    data = np.frombuffer(out.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if data.size == 0:
        return np.zeros(1, dtype=np.float32), 1, 0.0
    dur = data.size / sr
    win = max(1, sr // fps)
    n = max(1, int(np.ceil(data.size / win)))
    env = np.zeros(n, dtype=np.float32)
    for i in range(n):
        chunk = data[i * win:(i + 1) * win]
        if chunk.size:
            env[i] = np.sqrt(np.mean(chunk ** 2))
    return env, n, dur


def openness_track(audio_path, fps=24, words_path=None):
    """
    Best lip-sync current assets (sirf jaw bone) ke saath. Returns (values[0..1], n).

    Tier 1: agar edge-tts word timestamps (words_path) hon -> speech-mask (mooh SIRF
      words ke doraan khule, gaps/silence + sentence-end par band).
    Fallback: word timings na hon -> energy threshold gate (silence par band).
    Amplitude se open AMOUNT (band/mid/wide = graded shapes). Attack/release smoothing
    (tez khulna, dheere band) flicker/jhatke khatam karta + smooth transitions.
    """
    import json
    import os
    env, n, dur = _energy_frames(audio_path, fps)
    if env.max() > 0:
        env = env / env.max()

    # ---- speech mask (kahan awaaz hai) ----
    mask = np.zeros(n, dtype=np.float32)
    words = None
    if words_path and os.path.exists(words_path):
        try:
            words = json.load(open(words_path, encoding="utf-8")).get("words") or None
        except Exception:
            words = None
    if words:
        pad = 0.04                                     # 40ms: mooh word se thoda pehle khule
        for w in words:
            a = max(0, int((w["t"] - pad) * fps))
            b = min(n, int((w["t"] + w["d"] + pad) * fps) + 1)
            mask[a:b] = 1.0
    else:
        # Tier 3 fallback: energy threshold se speech detect (silence gate)
        thr = 0.06
        mask = (env > thr).astype(np.float32)

    raw = env * mask
    # span ke andar bhi low-energy dips (pauses) par mooh band — sentence-level spans
    # (Urdu voices) ke liye zaroori taake mid-sentence pause par bhi band ho. Speech par
    # halka floor (+0.12) taake mooh "band-band" na lage (visible movement).
    speech = (raw > 0.05) & (mask > 0)
    op = np.where(speech, np.clip(raw * 1.35 + 0.12, 0.0, 1.0), 0.0)

    # ---- attack/release smoothing (flicker guard) ----
    attack, release = 0.55, 0.18                       # tez khulna, dheere band (natural)
    y = np.zeros(n, dtype=np.float32)
    prev = 0.0
    for i in range(n):
        t = op[i]
        if t > prev:
            prev = min(t, prev + attack)
        else:
            prev = max(t, prev - release)
        y[i] = prev
    # shuru aur aakhir yaqeeni band (speech ke saath shuru/khatam)
    y[0] = 0.0
    if n > 1:
        y[-1] = 0.0
    return [round(float(v), 4) for v in y], n


def motion_position(emotion, openness, base_x, base_y,
                    intensity=1.0, parallax_dir=None, parallax_amt=8.0):
    """
    R2-A: emotion ke hisab se poore character ki motion (position offset).
    intensity: motion preset scaling. parallax_dir: bg ke against 2.5D drift.
    """
    e = (emotion or "neutral").lower()

    def pos(t):
        dx = 3.0 * math.sin(t * 1.5)            # halki idle sway
        dy = 0.0
        if e in ("happy", "excited", "laughing"):
            dy -= abs(math.sin(t * 6.0)) * 14    # khushi se uchhalna
        elif e in ("angry",):
            dx += math.sin(t * 28.0) * 6          # gusse se kaapna
        elif e in ("sad",):
            dy += 10.0                            # udaasi se jhukna
        elif e in ("surprised", "shocked", "scared"):
            dy -= max(0.0, 16.0 - t * 36.0)       # shuru mein chaunk
        elif e in ("thinking", "confused"):
            dx += 4.0 * math.sin(t * 2.2)
        dx *= intensity
        dy *= intensity
        # parallax (2.5D): character background ke against halka drift (depth feel)
        if parallax_dir in ("left", "right"):
            s = 1.0 if parallax_dir == "left" else -1.0
            dx += s * parallax_amt * math.sin(t * 0.5)
        dy += 5.0 * openness(t)                   # bolne par bob (lip-sync, scale nahi)
        return (base_x + dx, base_y + dy)

    return pos


def talking_avatar_clip(avatar_path, openness, dur, target_h=360,
                        mouth=(0.5, 0.575), draw_mouth=True, emotion="neutral"):
    """
    Bolta hua avatar/character clip (transparency ke saath).
    target_h: pixel height (aspect preserve hota hai — circle ya as-is dono chalte).
    mouth: (x_frac, y_frac) 0..1 — mooh ki jagah lip-sync ke liye.
    Amplitude se mooh + jaw squash + halki saans (breathing).
    """
    base = Image.open(avatar_path).convert("RGBA")
    w0, h0 = base.size
    scale = target_h / h0
    W, H = max(1, int(w0 * scale)), target_h
    base = base.resize((W, H), Image.LANCZOS)

    mx, my = int(mouth[0] * W), int(mouth[1] * H)
    mw = int(H * 0.14)
    max_mh = int(H * 0.10)

    def make(t):
        op = openness(t)
        img = base.copy()
        if draw_mouth and op > 0.12:
            d = ImageDraw.Draw(img)
            mh = int(5 + op * max_mh)
            d.rounded_rectangle(
                [mx - mw // 2, my - mh // 2, mx + mw // 2, my + mh // 2],
                radius=min(mw, mh) // 2, fill=(74, 38, 40, 255),
            )
            if mh > 12:
                d.ellipse([mx - mw // 3, my + 1, mx + mw // 3, my + mh // 2],
                          fill=(196, 96, 100, 255))
        breath = max(0.0, 0.006 * math.sin(t * 2.0))   # halki saans
        sq = 1.0 - op * 0.05 - breath
        if sq < 0.999:
            nh = max(1, int(H * sq))
            squashed = img.resize((W, nh), Image.LANCZOS)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            canvas.paste(squashed, (0, H - nh), squashed)
            img = canvas
        return np.array(img)

    rgb = VideoClip(lambda t: make(t)[:, :, :3], duration=dur)
    mask = VideoClip(lambda t: make(t)[:, :, 3] / 255.0, duration=dur, is_mask=True)
    return rgb.with_mask(mask)
