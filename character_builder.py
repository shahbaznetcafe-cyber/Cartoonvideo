"""
Character Builder — ek fruit/veg ko GENERATOR-READY package banata hai (aap ki spec):

  characters/<slug>/
    body.png                      (trunk+head, limbs removed, face intact)
    eye_left.png  eye_right.png    (individual eye sprites)
    mouth_closed.png  mouth_open.png
    arm_left.png  arm_right.png    (poora arm incl hand — shoulder pivot)
    hand_left.png hand_right.png   (hand sub-sprite)
    leg_left.png  leg_right.png    (poora leg incl foot — hip pivot)
    foot_left.png foot_right.png   (foot sub-sprite)
    eyes_blink/happy/angry/surprised.png   (engine expressions)
    rig.json                       (size, pivots, anchors, boxes, z-order)
    animations.json                (idle / talk / wave / walk keyframes)

Ek baar rig -> hazaron videos mein reuse. Yehi software ki jaan.
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# build_character se proven helpers reuse (generate + inpaint + retry + cleanup)
from build_character import (generate_character, _inpaint_head, _clean_islands,
                             _px, HEAD_CROP_FRAC)

# --- part regions (character W/H ke fraction) — A-pose front ---
HEAD_F = HEAD_CROP_FRAC  # 0.34
BOXES = {
    "arm_left":  (0.00, 0.30, 0.37, 0.62),
    "arm_right": (0.63, 0.30, 1.00, 0.62),
    "leg_left":  (0.31, 0.63, 0.50, 1.00),
    "leg_right": (0.50, 0.63, 0.69, 1.00),
    "hand_left":  (0.00, 0.46, 0.17, 0.62),
    "hand_right": (0.83, 0.46, 1.00, 0.62),
    "foot_left":  (0.31, 0.90, 0.50, 1.00),
    "foot_right": (0.50, 0.90, 0.69, 1.00),
}


def _crop_layer(orig, box, feather=3):
    """Full-canvas alpha-masked layer (asli image ke andar us region ke pixels)."""
    W, H = orig.size
    b = _px(box, W, H)
    mk = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mk).rectangle(b, fill=255)
    if feather:
        mk = mk.filter(ImageFilter.GaussianBlur(feather))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    combined = Image.composite(orig.split()[3], Image.new("L", (W, H), 0), mk)
    layer.paste(orig, (0, 0), combined)
    return layer, b


def _tight(layer):
    """Layer ko content bbox tak crop + offset return (sprite + jagah)."""
    bb = layer.split()[3].getbbox()
    if not bb:
        return layer, (0, 0)
    return layer.crop(bb), (bb[0], bb[1])


def build_package(slug, fruit, resume=True):
    out = os.path.join("characters", slug)
    os.makedirs(out, exist_ok=True)
    if resume and os.path.exists(f"{out}/rig.json") and os.path.exists(f"{out}/body.png"):
        print(f"  [{slug}] pehle se bana — skip")
        return out

    print(f"  [{slug}] 1/5 generate ({fruit})...")
    orig = generate_character(fruit, f"{out}/_source.png")
    W, H = orig.size

    print(f"  [{slug}] 2/5 limb/hand/foot layers...")
    pivots, anchors = {}, {}
    for part, box in BOXES.items():
        layer, b = _crop_layer(orig, box)
        layer = _clean_islands(layer, min_frac=0.05)
        layer.save(f"{out}/{part}.png")
        if part.startswith("arm"):
            px_ = b[2] if part == "arm_left" else b[0]        # shoulder = inner edge
            py_ = b[1] + int((b[3] - b[1]) * 0.05)
            pivots[part] = [px_, py_]
        elif part.startswith("leg"):
            px_ = (b[0] + b[2]) // 2; py_ = b[1] + int((b[3] - b[1]) * 0.02)  # hip
            pivots[part] = [px_, py_]
        else:  # hand/foot anchors (sub-sprite)
            anchors[part] = [(b[0] + b[2]) // 2, (b[1] + b[3]) // 2]

    print(f"  [{slug}] 3/5 body.png (limbs removed, face intact)...")
    body = orig.copy()
    for part in ("arm_left", "arm_right", "leg_left", "leg_right"):
        x0, y0, x1, y1 = _px(BOXES[part], W, H)
        stub = int((y1 - y0) * (0.28 if "arm" in part else 0.16))
        body.paste(Image.new("RGBA", (x1 - x0, y1 - y0 - stub), (0, 0, 0, 0)), (x0, y0 + stub))
    body = _clean_islands(body)
    body.save(f"{out}/body.png")

    print(f"  [{slug}] 4/5 face: mouth + eyes (AI inpaint)...")
    # 64-mult white canvas
    Wp, Hp = (W // 64) * 64 + 64, (H // 64) * 64 + 64
    canvas = Image.new("RGBA", (Wp, Hp), (255, 255, 255, 255))
    canvas.alpha_composite(orig, (0, 0)); canvas = canvas.convert("RGB")
    orig_alpha = np.array(orig.split()[3])

    hf = HEAD_F
    mouth_box = [int(0.33 * W), int(hf * 0.68 * H), int(0.67 * W), int(hf * 0.90 * H)]
    eye_box = [int(0.20 * W), int(hf * 0.30 * H), int(0.80 * W), int(hf * 0.58 * H)]
    head_box = [0, 0, W, int(hf * H)]

    def comp(ip, box):
        o = orig.copy()
        crop_ip = ip.crop((0, 0, W, H)).convert("RGBA")
        mk = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mk).rectangle(box, fill=255)
        mk = mk.filter(ImageFilter.GaussianBlur(5))
        mk_arr = np.array(mk).astype(np.float32) / 255.0
        final = (mk_arr * (orig_alpha.astype(np.float32) / 255.0) * 255).astype(np.uint8)
        o.paste(crop_ip, (0, 0), Image.fromarray(final))
        return o

    orig.save(f"{out}/mouth_closed.png")
    comp(_inpaint_head(canvas, mouth_box,
        "cartoon character face with wide open mouth, mouth agape, talking, dark open mouth interior",
        "closed mouth, sealed lips, smile"), mouth_box).save(f"{out}/mouth_open.png")
    for nm, (p, n) in {
        "blink": ("eyes tightly shut, closed eyelids, blinking", "open eyes"),
        "happy": ("squinting happy joyful eyes, raised cheerful eyebrows", "sad, angry"),
        "angry": ("angry eyebrows pushed down, glaring mad narrow eyes", "happy eyes"),
        "surprised": ("eyes wide open extremely shocked, eyebrows raised high", "sleepy, angry"),
    }.items():
        comp(_inpaint_head(canvas, eye_box, p, n), eye_box).save(f"{out}/eyes_{nm}.png")

    # individual eye sprites (spec format) — open eyes ke L/R halve
    exl = [eye_box[0], eye_box[1], (eye_box[0] + eye_box[2]) // 2, eye_box[3]]
    exr = [(eye_box[0] + eye_box[2]) // 2, eye_box[1], eye_box[2], eye_box[3]]
    for nm, bx in (("eye_left", exl), ("eye_right", exr)):
        lyr, _ = _crop_layer(orig, [bx[0] / W, bx[1] / H, bx[2] / W, bx[3] / H], feather=1)
        lyr.save(f"{out}/{nm}.png")
        anchors[nm] = [(bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2]

    print(f"  [{slug}] 5/5 rig.json + animations.json...")
    rig = {
        "size": [W, H],
        "pivots": pivots,          # arm/leg joints
        "anchors": anchors,        # hand/foot/eye placement
        "eye_box": eye_box, "mouth_box": mouth_box, "head_box": head_box,
        "z_order": ["leg_left", "leg_right", "arm_left", "arm_right", "body",
                    "eyes", "mouth"],
        "format": "package_v1",
    }
    json.dump(rig, open(f"{out}/rig.json", "w"), indent=2)
    json.dump(_default_animations(), open(f"{out}/animations.json", "w"), indent=2)
    print(f"  [{slug}] DONE -> {out}")
    return out


def _default_animations():
    """Named reusable animations — per-part keyframe tracks (rot degrees, ty=vertical %)."""
    return {
        "idle": {"duration": 3.2, "loop": True, "tracks": {
            "body": [{"t": 0, "ty": 0}, {"t": 1.6, "ty": 0.006}, {"t": 3.2, "ty": 0}],
            "arm_left":  [{"t": 0, "rot": 0}, {"t": 1.6, "rot": 4}, {"t": 3.2, "rot": 0}],
            "arm_right": [{"t": 0, "rot": 0}, {"t": 1.6, "rot": -4}, {"t": 3.2, "rot": 0}],
        }},
        "talk": {"duration": 2.4, "loop": True, "tracks": {
            "body": [{"t": 0, "ty": 0}, {"t": 1.2, "ty": 0.008}, {"t": 2.4, "ty": 0}],
            "arm_left":  [{"t": 0, "rot": 0}, {"t": 0.8, "rot": 7}, {"t": 1.6, "rot": 2}, {"t": 2.4, "rot": 0}],
            "arm_right": [{"t": 0, "rot": 0}, {"t": 0.8, "rot": -6}, {"t": 1.6, "rot": -2}, {"t": 2.4, "rot": 0}],
        }},
        "wave": {"duration": 1.4, "loop": False, "tracks": {
            "arm_right": [{"t": 0, "rot": 0}, {"t": 0.3, "rot": -45}, {"t": 0.6, "rot": -25},
                          {"t": 0.9, "rot": -45}, {"t": 1.2, "rot": -25}, {"t": 1.4, "rot": 0}],
        }},
        "walk": {"duration": 1.0, "loop": True, "tracks": {
            "leg_left":  [{"t": 0, "rot": 15}, {"t": 0.5, "rot": -15}, {"t": 1.0, "rot": 15}],
            "leg_right": [{"t": 0, "rot": -15}, {"t": 0.5, "rot": 15}, {"t": 1.0, "rot": -15}],
            "arm_left":  [{"t": 0, "rot": -12}, {"t": 0.5, "rot": 12}, {"t": 1.0, "rot": -12}],
            "arm_right": [{"t": 0, "rot": 12}, {"t": 0.5, "rot": -12}, {"t": 1.0, "rot": 12}],
        }},
    }
