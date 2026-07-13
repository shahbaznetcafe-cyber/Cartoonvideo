"""
Professional Character Builder — ek fruit/veg human-body character ka POORA rig
automatically banata hai:
  1. Generate (Runware FLUX) — front-facing full-body fruit-head human, T-pose
  2. Background remove (rembg) + content crop
  3. Limb extract (arms/legs) + pivots  → rigging ke liye
  4. body_base (limbs erased)
  5. Face rig: mouth (closed/half/open) + eyes (blink/happy/angry/surprised) — AI inpaint
  6. rig.json (pivots, eye_box, head_box, size)

Output: characters/<slug>.png + characters/_rig_<slug>/  (puppet engine isay animate karta hai)
"""
import base64
import io
import json
import os

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter
from rembg import remove

from runware_client import post_tasks as _post_raw, new_uuid


def post_tasks(tasks, tries=4):
    """SSL/network hiccups par retry (Runware API kabhi kabhi drop karta hai)."""
    import time
    last = None
    for a in range(tries):
        try:
            return _post_raw(tasks)
        except Exception as e:
            last = e
            time.sleep(2.0 * (a + 1))
    raise RuntimeError(f"post_tasks fail: {last}")

GEN_MODEL = "runware:101@1"     # FLUX dev — character generation
INPAINT_MODEL = "runware:102@1"  # FLUX Fill — mouth/eye states

# Head fruit-head human characters mein predictable proportions par hota hai.
# (front-facing full-body generate karne se face top ~26% mein aata hai)
HEAD_CROP_FRAC = 0.34    # head region: top 34% of character height

# Limb boxes (character width/height ke fraction) — human-anatomy front pose
LIMB_BOXES = {
    "arm_left":  (0.00, 0.30, 0.37, 0.62),
    "arm_right": (0.63, 0.30, 1.00, 0.62),
    "leg_left":  (0.31, 0.63, 0.50, 1.00),
    "leg_right": (0.50, 0.63, 0.69, 1.00),
}


def _uri(im):
    b = io.BytesIO()
    im.convert("RGB").save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def _download(url, tries=5):
    import time
    last = None
    for a in range(tries):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content))
        except Exception as e:
            last = e
            time.sleep(1.5 * (a + 1))
    raise RuntimeError(f"download fail: {last}")


def generate_character(fruit, out_path):
    """Front-facing full-body fruit-head human character (T-pose)."""
    prompt = (
        f"full body 3D cartoon character, {fruit} head on human body, "
        f"beige long-sleeve shirt, dark jeans, brown boots, brown belt, "
        f"friendly cartoon face with big expressive eyes and closed smiling mouth, "
        f"front facing, symmetrical A-pose, both arms stretched out away from the body "
        f"at 45 degrees with clear gap between arms and torso, legs apart shoulder width, "
        f"studio lighting, high detail, Pixar style, white background")
    neg = ("multiple characters, cropped, blurry, extra limbs, text, watermark, "
           "low quality, side view, back view, sitting, arms down at sides, "
           "arms touching body, crossed arms, hands in pockets, legs together")
    task = {
        "taskType": "imageInference", "taskUUID": new_uuid(), "model": GEN_MODEL,
        "positivePrompt": prompt, "negativePrompt": neg,
        "width": 832, "height": 1216, "numberResults": 1,
        "outputType": "URL", "outputFormat": "PNG",
    }
    url = post_tasks([task])[0]["imageURL"]
    img = _download(url).convert("RGBA")
    # background remove + content crop
    cut = remove(img)
    a = np.array(cut)
    ys, xs = np.where(a[:, :, 3] > 20)
    cut = cut.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    cut.save(out_path)
    return cut


def _px(box, W, H):
    return [int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)]


def extract_limbs(orig, rig_dir):
    """Limbs alag PNG (full-canvas, alpha-masked) + body_base (limbs erased) + pivots."""
    W, H = orig.size
    pivots = {}
    for k, box in LIMB_BOXES.items():
        b = _px(box, W, H)
        mk = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mk).rectangle(b, fill=255)
        mk = mk.filter(ImageFilter.GaussianBlur(4))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        combined = Image.composite(orig.split()[3], Image.new("L", (W, H), 0), mk)
        layer.paste(orig, (0, 0), combined)
        layer.save(f"{rig_dir}/{k}.png")
        # pivot = SHOULDER (arm inner-top) / HIP (leg top-center) — joint idhar ghumta hai
        if "arm" in k:
            px_ = b[2] if k == "arm_left" else b[0]
            py_ = b[1] + int((b[3] - b[1]) * 0.05)
        else:
            px_ = (b[0] + b[2]) // 2
            py_ = b[1] + int((b[3] - b[1]) * 0.02)
        pivots[k] = [px_, py_]

    base = orig.copy()
    for k, box in LIMB_BOXES.items():
        x0, y0, x1, y1 = _px(box, W, H)
        # top stub chhodo (arm=shoulder, leg=hip) — swing ke waqt gap us stub ke neeche chhup jata hai
        stub = int((y1 - y0) * (0.28 if "arm" in k else 0.16))
        base.paste(Image.new("RGBA", (x1 - x0, y1 - y0 - stub), (0, 0, 0, 0)), (x0, y0 + stub))
    # body_base ke chhote floating tukde hatao (sirf largest component = torso+head rakho)
    base = _clean_islands(base)
    base.save(f"{rig_dir}/body_base.png")
    return pivots


def _clean_islands(im, min_frac=0.02):
    """Alpha ke chhote alag-thalag blobs remove (sirf bade components rakho)."""
    try:
        from scipy import ndimage
    except Exception:
        return im
    a = np.array(im)
    alpha = a[:, :, 3] > 20
    lbl, n = ndimage.label(alpha)
    if n <= 1:
        return im
    sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1))
    thresh = alpha.sum() * min_frac
    keep = np.zeros_like(alpha)
    for i, s in enumerate(sizes, start=1):
        if s >= thresh:
            keep |= (lbl == i)
    a[:, :, 3] = (a[:, :, 3] * keep).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def _inpaint_head(canvas, box, pos, neg):
    """strength=1.0 zaroori (warna change nahi hota). canvas = white-bg padded 64-mult."""
    iw, ih = canvas.size
    m = Image.new("RGB", (iw, ih), (0, 0, 0))
    ImageDraw.Draw(m).rectangle(box, fill=(255, 255, 255))
    task = {
        "taskType": "imageInference", "taskUUID": new_uuid(), "model": INPAINT_MODEL,
        "positivePrompt": pos, "negativePrompt": neg,
        "seedImage": _uri(canvas), "maskImage": _uri(m), "strength": 1.0,
        "width": iw, "height": ih, "outputType": "URL", "outputFormat": "PNG",
    }
    url = post_tasks([task])[0]["imageURL"]
    return _download(url).convert("RGB")


def rig_face(orig, rig_dir):
    """Mouth + eye states (AI inpaint). Face top HEAD_CROP_FRAC mein hota hai."""
    W0, H0 = orig.size
    orig_alpha = np.array(orig.split()[3])
    # 64-multiple padded white canvas (mask/image size match zaroori)
    Wp, Hp = (W0 // 64) * 64 + 64, (H0 // 64) * 64 + 64
    canvas = Image.new("RGBA", (Wp, Hp), (255, 255, 255, 255))
    canvas.alpha_composite(orig, (0, 0))
    canvas = canvas.convert("RGB")

    # face boxes (ORIG fraction) — head top region
    hf = HEAD_CROP_FRAC
    mouth_box = [int(0.33 * W0), int(hf * 0.68 * H0), int(0.67 * W0), int(hf * 0.90 * H0)]
    eye_box = [int(0.20 * W0), int(hf * 0.30 * H0), int(0.80 * W0), int(hf * 0.58 * H0)]
    head_box = [0, 0, W0, int(hf * H0)]

    def comp(ip, box):
        out = orig.copy()
        crop_ip = ip.crop((0, 0, W0, H0)).convert("RGBA")
        mk = Image.new("L", (W0, H0), 0)
        ImageDraw.Draw(mk).rectangle(box, fill=255)
        mk = mk.filter(ImageFilter.GaussianBlur(5))
        mk_arr = np.array(mk).astype(np.float32) / 255.0
        final = (mk_arr * (orig_alpha.astype(np.float32) / 255.0) * 255).astype(np.uint8)
        out.paste(crop_ip, (0, 0), Image.fromarray(final))
        return out

    orig.save(f"{rig_dir}/mouth_closed.png")
    comp(_inpaint_head(canvas, mouth_box,
         "cartoon character face with wide open mouth, mouth agape, talking, dark open mouth interior",
         "closed mouth, sealed lips, smile"), mouth_box).save(f"{rig_dir}/mouth_open.png")
    comp(_inpaint_head(canvas, mouth_box,
         "cartoon character face with mouth slightly open, small gap between lips, speaking",
         "closed mouth, wide open mouth"), mouth_box).save(f"{rig_dir}/mouth_half.png")

    eye_states = {
        "blink": ("eyes tightly shut, closed eyelids, blinking", "open eyes"),
        "happy": ("squinting happy joyful eyes, raised cheerful eyebrows", "sad, angry"),
        "angry": ("angry eyebrows pushed down, glaring mad narrow eyes", "happy eyes"),
        "surprised": ("eyes wide open extremely shocked, eyebrows raised high", "sleepy, angry"),
    }
    for nm, (p, n) in eye_states.items():
        comp(_inpaint_head(canvas, eye_box, p, n), eye_box).save(f"{rig_dir}/eyes_{nm}.png")

    return {"eye_box": eye_box, "head_box": head_box, "mouth_box": mouth_box}


def build(slug, fruit, resume=True):
    """Poora character banao. return: rig_dir."""
    char_path = os.path.join("characters", f"{slug}.png")
    rig_dir = os.path.join("characters", f"_rig_{slug}")
    os.makedirs(rig_dir, exist_ok=True)
    if resume and os.path.exists(f"{rig_dir}/rig.json") and os.path.exists(char_path):
        print(f"  [{slug}] pehle se bana — skip")
        return rig_dir

    print(f"  [{slug}] 1/4 generate ({fruit})...")
    orig = generate_character(fruit, char_path)
    W, H = orig.size

    print(f"  [{slug}] 2/4 limbs extract...")
    pivots = extract_limbs(orig, rig_dir)

    print(f"  [{slug}] 3/4 face rig (mouth+eyes)...")
    face_meta = rig_face(orig, rig_dir)

    print(f"  [{slug}] 4/4 rig.json...")
    meta = {"pivots": pivots, "size": [W, H], **face_meta}
    json.dump(meta, open(f"{rig_dir}/rig.json", "w"))
    json.dump(meta, open(f"{rig_dir}/limbs.json", "w"))
    print(f"  [{slug}] DONE -> {rig_dir}")
    return rig_dir
