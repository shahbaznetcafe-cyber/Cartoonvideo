"""
M3 (asset part) — Scene backgrounds + character avatars (Runware image gen).
Backgrounds: landscape scene (no people). Characters: portrait -> circle avatar.
Sab proj/assets/ mein cache hote hain (dobara generate nahi).
"""
import json
import os
import time

import requests
from PIL import Image, ImageDraw

import config
import character_library
from runware_client import post_tasks, new_uuid

# har character ko ek ring color
_RING_COLORS = [(34, 197, 94), (59, 130, 246), (244, 114, 182),
                (251, 191, 36), (167, 139, 250), (248, 113, 113)]


def _runware_image(prompt, width, height, out_path, negative=""):
    # P3: multi-provider (runware/fal/...) + fallback
    import providers
    return providers.image_generate(prompt, width, height, out_path,
                                    negative or "text, watermark, low quality, blurry")


def generate_background(prompt, out_path, style=None):
    if os.path.exists(out_path):
        return out_path
    import styles
    a = config.ASPECT.lower()
    if a == "portrait":
        w, h, shot = 768, 1344, "vertical"
    elif a == "square":
        w, h, shot = 1024, 1024, "square"
    else:
        w, h, shot = 1344, 768, "wide"
    base = f"{prompt}, {shot} establishing shot, no people, no characters"
    full = styles.apply_style(base, style or config.STYLE)
    return _runware_image(full, w, h, out_path,
                          negative="people, person, characters, text, watermark")


def _circle_avatar(portrait_path, out_path, ring_color, size=512):
    img = Image.open(portrait_path).convert("RGBA")
    # square center-crop
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    img = img.resize((size, size), Image.LANCZOS)

    # circular mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    # ring
    ring = max(8, size // 28)
    ImageDraw.Draw(out).ellipse(
        [ring // 2, ring // 2, size - ring // 2, size - ring // 2],
        outline=ring_color + (255,), width=ring,
    )
    out.save(out_path)
    return out_path


def _write_meta(out_path, mouth, circle, draw_mouth):
    meta = {"mouth": mouth, "circle": circle, "draw_mouth": draw_mouth}
    json.dump(meta, open(out_path.replace(".png", ".json"), "w", encoding="utf-8"))


def generate_character_avatar(character, idx, out_path, lib_override=None):
    meta_path = out_path.replace(".png", ".json")
    if os.path.exists(out_path) and os.path.exists(meta_path):
        return out_path

    color = _RING_COLORS[idx % len(_RING_COLORS)]

    # 1) Library character (auto-assigned ya keyword-match)
    lib = lib_override or character_library.find_for(character)
    if lib:
        print(f"      (user image: {os.path.basename(lib['image'])})")
        if lib.get("circle", True):
            _circle_avatar(lib["image"], out_path, color)
            mouth = lib.get("mouth") or [0.5, 0.62]
        else:
            # as-is: transparent character jaisa hai waisa rakho
            Image.open(lib["image"]).convert("RGBA").save(out_path)
            mouth = lib.get("mouth") or [0.5, 0.66]
        _write_meta(out_path, mouth, lib.get("circle", True),
                    draw_mouth=lib.get("mouth") is not None)
        return out_path

    # LIBRARY_ONLY: AI se naye character mat banao
    if config.LIBRARY_ONLY:
        raise RuntimeError(
            f"LIBRARY_ONLY on hai aur '{character.get('name')}' ke liye koi "
            f"library character nahi mila. characters/ mein character add karein.")

    # 2) Warna AI se flat cartoon generate karo
    role = character.get("role", "")
    gender = character.get("gender", "person")
    prompt = (f"flat 2D cartoon character, simple vector illustration, bold clean outlines, "
              f"flat solid colors, minimal shading, big friendly round head, front-facing, "
              f"looking straight at camera, neutral closed mouth, calm expression, "
              f"{gender}, {role}, centered face, head and shoulders, solid pastel background")
    portrait = out_path.replace(".png", "_portrait.png")
    _runware_image(prompt, 768, 768, portrait,
                   negative=("3D, realistic, photorealistic, detailed shading, gradient, "
                             "open mouth, teeth, smiling wide, full body, multiple people, "
                             "side profile, text, watermark, blurry"))
    _circle_avatar(portrait, out_path, color)
    _write_meta(out_path, [0.5, 0.575], circle=True, draw_mouth=True)
    return out_path


def build_assets(parsed, proj_dir, on_progress=None):
    assets_dir = os.path.join(proj_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # backgrounds (per scene)
    scene_bg = {}
    scenes = parsed.get("scenes", [])
    chars = parsed.get("characters", [])
    total = len(scenes) + len(chars)
    step = 0

    for sc in scenes:
        step += 1
        path = os.path.join(assets_dir, f"bg_scene{sc['id']}.png")
        if on_progress:
            on_progress(step, total, f"Background: scene {sc['id']} ({sc.get('location')})")
        generate_background(sc.get("background_prompt", sc.get("location", "room")),
                            path, style=sc.get("style"))
        scene_bg[sc["id"]] = path

    # avatars — library characters auto-assign (scene/script ke hisab se)
    assignment = character_library.assign(chars)
    # preview se user ka veggie override (char_id -> veggie naam/package)
    overrides = parsed.get("char_overrides") or {}
    for cid, veg in overrides.items():
        if not veg:
            continue
        e = character_library.find_for({"name": str(veg)})
        if e:
            assignment[cid] = e
    char_avatar = {}
    char_rigs = {}
    for idx, ch in enumerate(chars):
        step += 1
        path = os.path.join(assets_dir, f"char_{ch['id']}.png")
        lib = assignment.get(ch["id"])
        if on_progress:
            chosen = "AI"
            if lib:
                chosen = lib.get("package") or os.path.splitext(os.path.basename(lib["image"]))[0]
            on_progress(step, total, f"Character: {ch.get('name')} -> {chosen}")
        generate_character_avatar(ch, idx, path, lib_override=lib)
        char_avatar[ch["id"]] = path

        # PUPPET: rig se real animation
        if config.PUPPET_ANIMATION and lib:
            try:
                pkg = lib.get("package")
                if pkg:
                    # pre-built folder-package (rigged layers + animations.json)
                    rig_path = os.path.join(config.BASE_DIR, "characters", pkg)
                    if os.path.exists(os.path.join(rig_path, "rig.json")):
                        char_rigs[ch["id"]] = rig_path
                    else:
                        print(f"  [rig skip {ch.get('name')}] package missing: {pkg}")
                else:
                    import autorig
                    slug = os.path.splitext(os.path.basename(lib["image"]))[0]
                    rig = autorig.auto_rig(lib["image"], autorig.rig_dir_for(slug),
                                           mouth_xy=tuple(lib.get("mouth") or (0.5, 0.66)))
                    char_rigs[ch["id"]] = rig
            except Exception as e:
                print(f"  [rig skip {ch.get('name')}] {e}")

    return scene_bg, char_avatar, char_rigs
