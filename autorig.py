"""
Auto-Rig Pipeline — koi bhi (closed-mouth) character image → poora puppet rig.
AI inpainting se mouth states (closed/half/open) + eye states (blink/happy/angry/surprised)
khud generate hote hain. One-time per character (~$0.07). Phir puppet engine animate karta hai.
"""
import base64
import io
import json
import os

import requests
from PIL import Image, ImageDraw, ImageFilter

from runware_client import post_tasks, new_uuid

INPAINT_MODEL = "runware:102@1"   # FLUX Fill


def _uri(im):
    b = io.BytesIO()
    im.convert("RGB").save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def _inpaint(orig, box, pos, neg, shape="ellipse"):
    W, H = orig.size
    mask = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(mask)
    (d.ellipse if shape == "ellipse" else d.rectangle)(box, fill=(255, 255, 255))
    task = {
        "taskType": "imageInference", "taskUUID": new_uuid(), "model": INPAINT_MODEL,
        "positivePrompt": pos, "negativePrompt": neg,
        "seedImage": _uri(orig), "maskImage": _uri(mask), "CFGScale": 17,
        "width": (W // 64) * 64, "height": (H // 64) * 64,
        "outputType": "URL", "outputFormat": "PNG",
    }
    url = post_tasks([task])[0]["imageURL"]
    ip = Image.open(io.BytesIO(requests.get(url, timeout=120).content)).convert("RGB").resize((W, H))
    # sirf region transparent original par paste
    out = orig.copy()
    mk = Image.new("L", (W, H), 0)
    (ImageDraw.Draw(mk).ellipse if shape == "ellipse" else ImageDraw.Draw(mk).rectangle)(box, fill=255)
    mk = mk.filter(ImageFilter.GaussianBlur(int(min(W, H) * 0.006)))
    out.paste(ip.convert("RGBA"), (0, 0), mk)
    return out


def auto_rig(image_path, rig_dir, mouth_xy=(0.5, 0.66), eye_xy=None, resume=True):
    """
    image_path: closed-mouth character (transparent PNG).
    rig_dir: output rig folder.
    return: rig_dir.
    """
    os.makedirs(rig_dir, exist_ok=True)
    if resume and os.path.exists(f"{rig_dir}/rig.json") and os.path.exists(f"{rig_dir}/mouth_open.png"):
        return rig_dir

    orig = Image.open(image_path).convert("RGBA")
    W, H = orig.size
    mx, my = int(mouth_xy[0] * W), int(mouth_xy[1] * H)
    mrw, mrh = int(W * 0.17), int(H * 0.10)
    mbox = [mx - mrw, my - mrh, mx + mrw, my + mrh]

    if eye_xy is None:
        eye_xy = (mouth_xy[0], max(0.30, mouth_xy[1] - 0.25))
    ex, ey = int(eye_xy[0] * W), int(eye_xy[1] * H)
    erw, erh = int(W * 0.34), int(H * 0.15)
    ebox = [ex - erw, ey - erh, ex + erw, ey + erh]

    # MOUTH states (closed = original)
    orig.save(f"{rig_dir}/mouth_closed.png")
    _inpaint(orig, mbox,
             "cartoon character with a WIDE OPEN mouth, mouth agape, talking, open mouth interior visible",
             "closed mouth, lips together, sealed lips").save(f"{rig_dir}/mouth_open.png")
    _inpaint(orig, mbox,
             "cartoon character with mouth slightly open mid-speech, small open mouth",
             "closed mouth, wide open mouth").save(f"{rig_dir}/mouth_half.png")

    # EYE states
    eye_states = {
        "blink": ("cartoon character with closed eyes, eyelids shut, blinking", "wide open eyes"),
        "happy": ("cartoon character with happy cheerful eyes, raised eyebrows", "angry, sad"),
        "angry": ("cartoon character with angry furrowed eyebrows, frowning mad eyes", "happy smiling eyes"),
        "surprised": ("cartoon character with wide shocked surprised eyes, raised eyebrows", "angry, sleepy"),
    }
    for nm, (p, n) in eye_states.items():
        _inpaint(orig, ebox, p, n, shape="rect").save(f"{rig_dir}/eyes_{nm}.png")

    json.dump({"eye_box": ebox, "mouth_xy": list(mouth_xy)},
              open(f"{rig_dir}/rig.json", "w"))
    return rig_dir


def auto_rig_psd(psd_path, rig_dir, mouth_xy=(0.5, 0.66), eye_xy=None):
    """
    Layered PSD se POORA rig:
    1) PSD se body + limbs (arms/legs) + pivots nikalo
    2) body par mouth (closed/half/open) + eyes (blink/expression) inpaint karo
    return: rig_dir (puppet engine isay animate karega — talk + blink + express + limbs).
    """
    import psd_rig
    psd_rig.rig_from_psd(psd_path, rig_dir)   # body.png + limb PNGs + limbs.json
    body = os.path.join(rig_dir, "body.png")
    # body par mouth/eyes (inpaint) — auto_rig wahi body use karega
    auto_rig(body, rig_dir, mouth_xy=mouth_xy, eye_xy=eye_xy, resume=False)
    return rig_dir


def rig_dir_for(char_id):
    import config
    return os.path.join(config.BASE_DIR, "characters", f"_rig_{char_id}")


def auto_rig_library_character(entry, char_id):
    """character_library entry (image + mouth) se auto-rig."""
    mouth = entry.get("mouth") or [0.5, 0.66]
    return auto_rig(entry["image"], rig_dir_for(char_id), mouth_xy=tuple(mouth))
