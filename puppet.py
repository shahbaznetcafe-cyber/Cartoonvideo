"""
Puppet Animation Engine — AI-rigged character animate karta hai.
Layers: MOUTH (lip-sync: closed/half/open) + EYES (blink + expression).
Sab local render = free. Yehi "After Effects-tier" 2D character animation.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import lipsync

EMOTION_EYES = {
    "happy": "happy", "excited": "happy", "laughing": "happy",
    "angry": "angry", "sad": "angry",
    "surprised": "surprised", "shocked": "surprised", "scared": "surprised",
}


def _load(path):
    return Image.open(path).convert("RGBA") if os.path.exists(path) else None


def _limb_angle(part, t, emotion):
    angry = (emotion or "").lower() == "angry"
    if part == "arm_right":
        return (-9 + 5 * math.sin(t * 8)) if angry else (7 * math.sin(t * 2.2))
    if part == "arm_left":
        return (10 * math.sin(t * 2.4)) if angry else (6 * math.sin(t * 1.8))
    if part == "leg_left":
        return 3 * math.sin(t * 3)
    if part == "leg_right":
        return 3 * math.sin(t * 3 + 1.6)
    return 0


def _sample_track(track, t):
    """Keyframe track (list of {t, rot, ty, ...}) se time t par values interpolate."""
    if not track:
        return {}
    if t <= track[0]["t"]:
        return {k: v for k, v in track[0].items() if k != "t"}
    if t >= track[-1]["t"]:
        return {k: v for k, v in track[-1].items() if k != "t"}
    for i in range(len(track) - 1):
        a, b = track[i], track[i + 1]
        if a["t"] <= t <= b["t"]:
            span = b["t"] - a["t"]
            f = (t - a["t"]) / span if span else 0.0
            keys = (set(a) | set(b)) - {"t"}
            return {k: a.get(k, 0) + (b.get(k, 0) - a.get(k, 0)) * f for k in keys}
    return {}


def _package_clip(rig_dir, audio_path, dur, target_h, fps, emotion):
    """
    Naya package_v1 format: body.png + alag limb/eye/mouth layers + animations.json.
    Compositing z-order: legs -> body -> arms -> eyes -> mouth. Limbs animations.json
    ('talk') se ghumte hain; mouth audio se; eyes blink+emotion.
    """
    from moviepy import VideoClip

    rig = json.load(open(f"{rig_dir}/rig.json"))
    anims = {}
    if os.path.exists(f"{rig_dir}/animations.json"):
        anims = json.load(open(f"{rig_dir}/animations.json"))

    # INTACT character base (kaat-tor NAHI -> koi seam/disconnected-limb nahi).
    # mouth_closed.png = poora original 3D render. Isi ko whole-body subtle motion se
    # "alive/3D" banate hain + mouth/eyes overlay. Yeh cut-out puppet se saaf lagta hai.
    base = _load(f"{rig_dir}/mouth_closed.png") or _load(f"{rig_dir}/body.png")
    H0 = base.size[1]
    sc = target_h / H0

    def rs(im):
        return im.resize((max(1, int(im.size[0] * sc)), max(1, int(im.size[1] * sc))), Image.LANCZOS) if im else None

    base = rs(base)
    W, H = base.size

    mouth_open = rs(_load(f"{rig_dir}/mouth_open.png"))
    eyes = {k: rs(_load(f"{rig_dir}/eyes_{k}.png")) for k in ("blink", "happy", "angry", "surprised")}

    eye_box = [int(v * sc) for v in rig.get("eye_box", [0, 0, 0, 0])]
    mouth_box = [int(v * sc) for v in rig.get("mouth_box", [0, 0, 0, 0])]

    def _mask(box, blur):
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle(box, fill=255)
        return m.filter(ImageFilter.GaussianBlur(blur))

    eye_mask = _mask(eye_box, int(target_h * 0.014)) if eye_box[2] else None
    mouth_mask = _mask(mouth_box, int(target_h * 0.014)) if mouth_box[2] else None
    expr = EMOTION_EYES.get((emotion or "").lower())

    openness, _ = lipsync.amplitude_envelope(audio_path, fps=fps)

    def is_blink(t):
        p = t % 3.3
        return p < 0.13 or (0.20 < p < 0.30)

    cx, cyb = W // 2, H - 1   # bottom-center pivot -> paon planted rahein

    def make(t):
        op = openness(t)
        # 1) mouth + eyes overlay INTACT base par (face region ke andar, feathered)
        eye_src = None
        if eyes["blink"] and is_blink(t):
            eye_src = eyes["blink"]
        elif expr and eyes.get(expr):
            eye_src = eyes[expr]
        talking = mouth_open is not None and mouth_mask is not None and op >= 0.16
        if eye_src is not None or talking:
            face = base.copy()
            if eye_src is not None and eye_mask is not None:
                face.paste(eye_src, (0, 0), eye_mask)
            if talking:
                face.paste(mouth_open, (0, 0), mouth_mask)
        else:
            face = base

        # 2) 3D-feel whole-body motion (poora intact -> koi seam nahi):
        #    breathing (vertical) + speech scale + halka sway-rotation + speech bob
        sy = 1.0 + 0.011 * math.sin(t * 1.6) + op * 0.014
        sx = 1.0 + 0.004 * math.sin(t * 1.6)
        nw, nh = max(1, int(W * sx)), max(1, int(H * sy))
        f2 = face.resize((nw, nh), Image.LANCZOS)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        img.paste(f2, ((W - nw) // 2, H - nh), f2)      # bottom-center anchor
        face = img

        ang = 1.5 * math.sin(t * 0.6)                    # gentle sway (paon par ghoomta)
        if abs(ang) > 0.02:
            face = face.rotate(ang, center=(cx, cyb), resample=Image.BICUBIC)

        dx = int(round(7 * math.sin(t * 0.5)))           # side sway
        dy = int(round(-op * 4))                         # bolte waqt halka uchaal
        if dx or dy:
            cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            cv.paste(face, (dx, dy), face)
            face = cv
        return np.array(face)

    # SPEED: moviepy rgb+mask ke liye make(t) 2 baar call hota hai — 1-frame memo se aadha kaam
    _memo = {"t": None, "f": None}

    def _frame(t):
        if _memo["t"] != t:
            _memo["t"] = t
            _memo["f"] = make(t)
        return _memo["f"]

    rgb = VideoClip(lambda t: _frame(t)[:, :, :3], duration=dur)
    mask = VideoClip(lambda t: _frame(t)[:, :, 3] / 255.0, duration=dur, is_mask=True)
    return rgb.with_mask(mask), openness


def puppet_clip(rig_dir, audio_path, dur, target_h=800, fps=30, emotion="neutral"):
    """
    AI-rigged character animate karta hai. package_v1 (body.png + layers + animations.json)
    -> naya renderer; warna body_base+limbs.json -> full rig; warna face-only.
    """
    from moviepy import VideoClip

    _meta_path = f"{rig_dir}/rig.json"
    if os.path.exists(_meta_path):
        try:
            if json.load(open(_meta_path)).get("format") == "package_v1":
                return _package_clip(rig_dir, audio_path, dur, target_h, fps, emotion)
        except Exception as e:
            print(f"  [puppet] package load fail, fallback: {e}")

    has_limbs = os.path.exists(f"{rig_dir}/body_base.png") and os.path.exists(f"{rig_dir}/limbs.json")

    mouth = {s: _load(f"{rig_dir}/mouth_{s}.png") for s in ("closed", "half", "open")}
    base_img = _load(f"{rig_dir}/body_base.png") if has_limbs else mouth["closed"]
    H0 = base_img.size[1]
    sc = target_h / H0

    def rs(im):
        return im.resize((max(1, int(im.size[0] * sc)), target_h), Image.LANCZOS) if im else None

    mouth = {k: rs(v) for k, v in mouth.items()}
    base_img = rs(base_img)
    W, H = base_img.size

    eyes = {k: rs(_load(f"{rig_dir}/eyes_{k}.png")) for k in ("blink", "happy", "angry", "surprised")}
    eye_box = mouth_box = None
    rig_meta = {}
    meta_path = f"{rig_dir}/rig.json"
    if os.path.exists(meta_path):
        rig_meta = json.load(open(meta_path))
        b = rig_meta.get("eye_box")
        if b:
            eye_box = [int(v * sc) for v in b]
    head_box = rig_meta.get("head_box")
    if head_box:
        head_box = [int(v * sc) for v in head_box]
    expr = EMOTION_EYES.get((emotion or "").lower())

    eye_mask = None
    if eye_box:
        eye_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(eye_mask).rectangle(eye_box, fill=255)
        eye_mask = eye_mask.filter(ImageFilter.GaussianBlur(int(target_h * 0.012)))

    # limbs (optional)
    limb_imgs, pivots = {}, {}
    if has_limbs:
        limbs_meta = json.load(open(f"{rig_dir}/limbs.json"))
        pivots = {k: (int(v[0] * sc), int(v[1] * sc)) for k, v in limbs_meta.get("pivots", {}).items()}
        for part in pivots:
            im = _load(f"{rig_dir}/{part}.png")
            limb_imgs[part] = rs(im) if im else None

    openness, _ = lipsync.amplitude_envelope(audio_path, fps=fps)

    def is_blink(t):
        p = t % 3.3
        return p < 0.13 or (0.20 < p < 0.30)   # double blink feel

    def face_layer(t):
        """Mouth state + eye state ka chehra (mouth_*.png se, jisme limbs nahi)."""
        op = openness(t)
        mstate = "closed" if op < 0.16 else ("half" if op < 0.45 else "open")
        face = mouth.get(mstate) or mouth["closed"]
        if eye_box:
            src = None
            if eyes["blink"] and is_blink(t):
                src = eyes["blink"]
            elif expr and eyes.get(expr):
                src = eyes[expr]
            if src is not None:
                face = face.copy()
                face.paste(src, (0, 0), eye_mask)
        return face, op

    def make(t):
        face, op = face_layer(t)

        if has_limbs:
            img = base_img.copy()
            if head_box:
                # sirf HEAD crop paste karo (body_base ka limb-area transparent rahe)
                hb = head_box
                crop = face.crop(hb)
                # bottom edge feather -> neck seam blend ho jaye
                cm = crop.split()[3]
                grad = Image.new("L", crop.size, 255)
                gh = max(2, int(crop.size[1] * 0.14))
                gd = ImageDraw.Draw(grad)
                for i in range(gh):
                    gd.line([(0, crop.size[1] - 1 - i), (crop.size[0], crop.size[1] - 1 - i)],
                            fill=int(255 * i / gh))
                cm = Image.composite(cm, Image.new("L", crop.size, 0), grad)
                img.paste(crop, (hb[0], hb[1]), cm)
            else:
                img.paste(face, (0, 0), face)
            for part, im in limb_imgs.items():
                if im is None:
                    continue
                ang = _limb_angle(part, t, emotion)
                rot = im.rotate(ang, center=pivots[part], resample=Image.BICUBIC)
                img.alpha_composite(rot)
        else:
            img = face.copy()

        # body talk-squash + breathing
        sq = 1.0 - op * 0.05 - max(0.0, 0.006 * math.sin(t * 2))
        if sq < 0.999:
            nh = max(1, int(H * sq))
            sm = img.resize((W, nh), Image.LANCZOS)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            canvas.paste(sm, (0, H - nh), sm)
            img = canvas
        return np.array(img)

    # SPEED: rgb+mask ke liye make(t) 2 baar call — 1-frame memo se aadha kaam
    _memo = {"t": None, "f": None}

    def _frame(t):
        if _memo["t"] != t:
            _memo["t"] = t
            _memo["f"] = make(t)
        return _memo["f"]

    rgb = VideoClip(lambda t: _frame(t)[:, :, :3], duration=dur)
    mask = VideoClip(lambda t: _frame(t)[:, :, 3] / 255.0, duration=dur, is_mask=True)
    return rgb.with_mask(mask), openness