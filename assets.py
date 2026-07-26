"""
M3 (asset part) — Reusable AI scene background plates (Runware image gen) for the
3D Three.js pipeline. Landscape scene, no people. Cache mein save (dobara generate nahi).
"""
import json
import os
import time
import hashlib
from pathlib import Path

import config

BACKGROUND_LIBRARY = Path(config.BASE_DIR) / "assets" / "generated_backgrounds"
BACKGROUND_MANIFEST = BACKGROUND_LIBRARY / "manifest.json"


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
    base = (
        f"{prompt}, low-poly 3D game environment compatible with Quaternius cartoon characters, "
        f"clean stylized geometry, cohesive material palette, {shot} establishing shot, "
        "clear foreground and midground depth, no depth-of-field blur, no people, no characters"
    )
    full = styles.apply_style(base, style or config.STYLE)
    return _runware_image(full, w, h, out_path,
                          negative="people, person, characters, text, watermark, photorealism, bokeh, blurry background")


def reusable_background(prompt, style=None):
    """Generate a scene plate once, then reuse it across future projects.

    The cache key includes the final style/aspect/prompt so images are never
    reused for a materially different scene.  The manifest makes the saved
    library understandable without putting provider credentials in it.
    """
    import styles
    raw_prompt = str(prompt or "stylized story environment").strip()
    style_name = style or config.STYLE
    key_source = json.dumps({"prompt": raw_prompt, "style": style_name,
                             "aspect": config.ASPECT}, sort_keys=True)
    key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:20]
    BACKGROUND_LIBRARY.mkdir(parents=True, exist_ok=True)
    path = BACKGROUND_LIBRARY / f"{key}.png"
    if not path.exists():
        generate_background(raw_prompt, str(path), style=style_name)
    manifest = {}
    try:
        manifest = json.loads(BACKGROUND_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        pass
    manifest[key] = {"file": path.name, "prompt": raw_prompt, "style": style_name,
                     "aspect": config.ASPECT, "updated_at": int(time.time())}
    temp = BACKGROUND_MANIFEST.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    os.replace(temp, BACKGROUND_MANIFEST)
    return str(path)


def build_scene_backgrounds(parsed, proj_dir=None, on_progress=None):
    """Return reusable AI scene plates for the Three.js pipeline only."""
    del proj_dir
    import production_director
    result = {}
    scenes = list(parsed.get("scenes") or [])
    total = max(1, len(scenes))
    for index, scene in enumerate(scenes, 1):
        if on_progress:
            on_progress(index, total, f"Reusable AI background: scene {scene.get('id')}")
        # A chroma-key scene is a flat colour by design; an AI plate would
        # both waste the API call and defeat the point of the key.
        if production_director._scene_preset(scene) in {"chroma_green", "chroma_blue"}:
            continue
        prompt = scene.get("background_prompt") or scene.get("location") or "stylized story environment"
        try:
            result[scene.get("id")] = reusable_background(prompt, style=scene.get("style"))
        except Exception as exc:
            # A local Three.js environment is still a valid no-network fallback.
            # Do not fail a video just because a provider is temporarily unavailable.
            print(f"  [AI background fallback] scene {scene.get('id')}: {exc}")
    return result
