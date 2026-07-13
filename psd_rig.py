"""
PSD Rig Loader — ek layered PSD se character rig khud bana le.
User Photoshop mein layers banaye (naam: body, arm_left, arm_right, leg_left, leg_right)
aur EK PSD de. App har layer + position + pivot automatically nikaal leta hai.
Mouth/eyes phir AI inpaint se body par ban jate hain (autorig).
"""
import json
import os

from PIL import Image
from psd_tools import PSDImage

# layer naam keywords -> part (flexible matching)
PART_KEYWORDS = {
    "arm_left":  ["arm_left", "left_arm", "left arm", "arm left", "baazu_left", "l_arm"],
    "arm_right": ["arm_right", "right_arm", "right arm", "arm right", "baazu_right", "r_arm"],
    "leg_left":  ["leg_left", "left_leg", "left leg", "leg left", "taang_left", "l_leg"],
    "leg_right": ["leg_right", "right_leg", "right leg", "leg right", "taang_right", "r_leg"],
    "body":      ["body", "jism", "torso", "base"],
}


def _match(name):
    n = (name or "").lower().strip()
    for part, kws in PART_KEYWORDS.items():
        if any(k in n for k in kws):
            return part
    return None


def rig_from_psd(psd_path, out_dir):
    """PSD -> body.png + limb PNGs (full-canvas) + limbs.json (pivots). return (out_dir, parts)."""
    psd = PSDImage.open(psd_path)
    W, H = psd.width, psd.height
    os.makedirs(out_dir, exist_ok=True)

    found, bboxes = {}, {}
    for layer in psd.descendants():
        try:
            if not layer.is_visible():
                continue
        except Exception:
            pass
        part = _match(layer.name)
        if not part or part in found:
            continue
        img = layer.composite()
        if img is None:
            continue
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        l, t = layer.offset
        full.paste(img.convert("RGBA"), (int(l), int(t)))
        full.save(os.path.join(out_dir, f"{part}.png"))
        found[part] = True
        # pivot ke liye ASLI content bbox (alpha>0) — full-canvas ya tight dono robust
        ab = full.split()[3].getbbox()
        bboxes[part] = ab if ab else (int(l), int(t), int(l) + img.width, int(t) + img.height)

    # body na mile to poora composite (fallback)
    if "body" not in found:
        psd.composite().convert("RGBA").save(os.path.join(out_dir, "body.png"))

    # auto pivots (limb attach points)
    pivots = {}
    for part in ("arm_left", "arm_right", "leg_left", "leg_right"):
        if part in bboxes:
            l, t, r, b = bboxes[part]
            if "arm" in part:
                px = r if part == "arm_left" else l   # shoulder = body ki taraf wala edge
                py = t + (b - t) * 0.15
            else:
                px = (l + r) / 2; py = t + (b - t) * 0.05   # hip = leg ka top
            pivots[part] = [int(px), int(py)]
    json.dump({"pivots": pivots, "size": [W, H], "from_psd": True},
              open(os.path.join(out_dir, "limbs.json"), "w"))
    return out_dir, list(found.keys())
