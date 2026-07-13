"""
2D animated face frames banao (audio se lip-sync + emotion se eyes) — ye baad mein
3D head ke front par project honge. Package ki mouth/eye states reuse.

Run (veggie-tool venv): python face_seq.py <slug> <audio.mp3> <out_dir> <dur> <fps> [emotion]
"""
import sys, os, json, math
sys.path.insert(0, r"D:\flayer\sbz-studio")
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import lipsync

slug = sys.argv[1]; audio = sys.argv[2]; out_dir = sys.argv[3]
dur = float(sys.argv[4]); fps = int(sys.argv[5])
emotion = sys.argv[6] if len(sys.argv) > 6 else "neutral"
os.makedirs(out_dir, exist_ok=True)

PKG = os.path.join(r"D:\flayer\sbz-studio", "characters", slug)
base = Image.open(os.path.join(PKG, "mouth_closed.png")).convert("RGBA")
W, H = base.size
mouth_open = Image.open(os.path.join(PKG, "mouth_open.png")).convert("RGBA")
eyes = {}
for k in ("blink", "happy", "angry", "surprised"):
    p = os.path.join(PKG, f"eyes_{k}.png")
    if os.path.exists(p):
        eyes[k] = Image.open(p).convert("RGBA")
rig = json.load(open(os.path.join(PKG, "rig.json")))
eye_box = rig.get("eye_box"); mouth_box = rig.get("mouth_box")

EMO_EYES = {"happy": "happy", "excited": "happy", "angry": "angry", "sad": "angry",
            "surprised": "surprised", "shocked": "surprised", "scared": "surprised"}
expr = EMO_EYES.get(emotion.lower())

def mask_for(box, blur):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle(box, fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))

eye_mask = mask_for(eye_box, int(H * 0.014)) if eye_box else None
mouth_mask = mask_for(mouth_box, int(H * 0.014)) if mouth_box else None

openness, _ = lipsync.amplitude_envelope(audio, fps=fps)

def is_blink(t):
    p = t % 3.3
    return p < 0.13 or (0.20 < p < 0.30)

# sirf HEAD region (face) — poora character nahi
head_box = rig.get("head_box") or [0, 0, W, int(0.34 * H)]
hx0, hy0, hx1, hy1 = head_box

n = int(dur * fps)
for f in range(1, n + 1):
    t = (f - 1) / fps
    face = base.copy()
    # eyes
    src = None
    if eyes.get("blink") and is_blink(t):
        src = eyes["blink"]
    elif expr and eyes.get(expr):
        src = eyes[expr]
    if src is not None and eye_mask is not None:
        face.paste(src, (0, 0), eye_mask)
    # mouth (audio-driven)
    if openness(t) >= 0.16 and mouth_mask is not None:
        face.paste(mouth_open, (0, 0), mouth_mask)
    # HEAD crop -> sirf chehra project ho
    face.crop((hx0, hy0, hx1, hy1)).save(os.path.join(out_dir, f"face_{f:04d}.png"))

print(f"FACE_SEQ_DONE {n} frames -> {out_dir}", flush=True)
