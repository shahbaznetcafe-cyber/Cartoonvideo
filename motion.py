"""
P1 — Motion. Ken Burns 2.0: har scene par alag directional zoom/pan.
Background ab static nahi rahega — zinda lagega.
"""
import numpy as np
from PIL import Image
from moviepy import VideoClip

DIRECTIONS = ["in", "out", "left", "right", "up", "down"]

# ``trans`` is the preferred short-dissolve duration. Visible transitions are
# clamped to 0.15-0.50 seconds by transitions.py.
PRESETS = {
    "subtle":    {"zoom": 0.06, "char": 0.5, "trans": 0.3, "parallax": 4},
    "dynamic":   {"zoom": 0.12, "char": 1.0, "trans": 0.4, "parallax": 8},
    "cinematic": {"zoom": 0.18, "char": 1.3, "trans": 0.5, "parallax": 14},
}


def preset(name=None):
    import config
    return PRESETS.get(name or config.MOTION_PRESET, PRESETS["dynamic"])


def _cover(img, w, h):
    """Image ko (w,h) cover-crop karo (aspect fill)."""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((int(iw * scale) + 1, int(ih * scale) + 1), Image.LANCZOS)
    iw, ih = img.size
    left, top = (iw - w) // 2, (ih - h) // 2
    return img.crop((left, top, left + w, top + h))


def kenburns_clip(bg_path, dur, W, H, fps=30, direction="in", zoom=0.12):
    """
    Ken Burns motion clip (W x H) for a background image.
    direction: in | out | left | right | up | down
    """
    # base thora bara taake zoom/pan ki gunjaish ho
    BW, BH = int(W * (1 + zoom)), int(H * (1 + zoom))
    base = _cover(Image.open(bg_path).convert("RGB"), BW, BH)

    aspect = W / H

    def make(t):
        p = min(1.0, max(0.0, t / dur)) if dur > 0 else 0.0

        # view height (zoom): chhota = zyada zoomed in
        if direction == "in":
            vh = BH - (BH - H) * p
        elif direction == "out":
            vh = H + (BH - H) * p
        else:
            vh = (BH + H) / 2.0          # pan ke liye halka zoom thamba
        vw = vh * aspect
        vw = min(vw, BW)
        vh = min(vh, BH)

        # pan offset
        max_x, max_y = BW - vw, BH - vh
        cx, cy = max_x / 2.0, max_y / 2.0   # default center
        if direction == "left":
            cx = max_x * p
        elif direction == "right":
            cx = max_x * (1 - p)
        elif direction == "up":
            cy = max_y * p
        elif direction == "down":
            cy = max_y * (1 - p)

        x0, y0 = int(cx), int(cy)
        x1, y1 = int(cx + vw), int(cy + vh)
        x0 = max(0, min(x0, BW - 1)); y0 = max(0, min(y0, BH - 1))
        x1 = max(x0 + 1, min(x1, BW)); y1 = max(y0 + 1, min(y1, BH))

        view = base.crop((x0, y0, x1, y1)).resize((W, H), Image.LANCZOS)
        return np.array(view)

    return VideoClip(make, duration=dur)


def direction_for_scene(scene_id):
    """Har scene ko ek (consistent) direction do — variety ke liye."""
    return DIRECTIONS[int(scene_id) % len(DIRECTIONS)]
