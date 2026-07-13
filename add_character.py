"""
Koi bhi cartoon character (2D image) -> 3D rigged character library mein add.
Steps: Rodin AI se full 3D (Detail) -> Blender auto-rig -> .blend save -> manifest entry.

Use: python add_character.py <image_path> <name> [keyword1,keyword2,...]
General hai — fruits, animals, insaan, mascots, kuch bhi.
"""
import os
import sys
import time
import subprocess

import requests

import config
import char3d_lib

sys.stdout.reconfigure(encoding="utf-8")

KEY = "vibecoding"
BASE = "https://hyperhuman.deemos.com/api/v2"
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
BL_DIR = os.path.join(config.BASE_DIR, "blender")
GLB_DIR = os.path.join(BL_DIR, "assets", "full3d")
RIG_DIR = os.path.join(BL_DIR, "rigged", "blend")
THUMB_DIR = os.path.join(BL_DIR, "rigged")


def _slug(name):
    return "".join(c for c in name.lower().replace(" ", "_") if c.isalnum() or c == "_")


def generate_3d(image_path, slug, on_progress=None):
    """Rodin Detail se full 3D glb (network-flaky ke liye robust: retries)."""
    out = os.path.join(GLB_DIR, f"{slug}_full.glb")
    os.makedirs(GLB_DIR, exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) > 50000:
        return out
    b = open(image_path, "rb").read()
    hdr = {"Authorization": f"Bearer {KEY}"}

    # 1) submit (retry transient network errors)
    uuid = None
    for attempt in range(5):
        try:
            files = [("images", ("0000.png", b, "image/png")), ("tier", (None, "Detail")),
                     ("mesh_mode", (None, "Raw")), ("texture_mode", (None, "high"))]
            r = requests.post(f"{BASE}/rodin", headers=hdr, files=files, timeout=180).json()
            uuid = r.get("uuid") or r.get("task_uuid")
            if uuid:
                break
            raise RuntimeError(f"no uuid: {str(r)[:120]}")
        except Exception as e:
            if on_progress:
                on_progress(f"Rodin submit retry {attempt+1}...")
            time.sleep(5 + attempt*4)
    if not uuid:
        raise RuntimeError("Rodin submit fail (network) baad 5 tries")

    # 2) poll download (transient errors tolerate karo)
    for _ in range(90):
        if on_progress:
            on_progress("3D generate ho raha (Rodin AI)...")
        try:
            d = requests.post(f"{BASE}/download", headers=hdr,
                              json={"task_uuid": uuid}, timeout=60).json()
            glb = [f for f in d.get("list", []) if f["name"].endswith(".glb")]
            if glb:
                data = requests.get(glb[0]["url"], timeout=200).content
                if len(data) > 50000:
                    open(out, "wb").write(data)
                    return out
        except Exception:
            pass
        time.sleep(7)
    raise RuntimeError("3D generate timeout")


def rig(glb, on_progress=None):
    """Blender auto-rig -> .blend + thumbnail."""
    if on_progress:
        on_progress("Blender mein rig ho raha (bones + weights)...")
    out = os.path.join(RIG_DIR, "..")
    subprocess.run([BLENDER, "--background", "--python", os.path.join(BL_DIR, "rig_all.py"),
                    "--", THUMB_DIR, glb], check=True, capture_output=True)
    slug = os.path.splitext(os.path.basename(glb))[0].replace("_full", "")
    blend = os.path.join(RIG_DIR, f"{slug}.blend")
    return blend if os.path.exists(blend) else None


def add(image_path, name, keywords=None, on_progress=None):
    slug = _slug(name)
    if on_progress:
        on_progress(f"'{name}' add ho raha...")
    glb = generate_3d(image_path, slug, on_progress)
    blend = rig(glb, on_progress)
    if not blend:
        raise RuntimeError("Rig fail")
    kws = keywords or [slug]
    char3d_lib.add(name, kws, f"{slug}.blend", thumb=f"{slug}.png")
    if on_progress:
        on_progress(f"✅ '{name}' library mein add ho gaya")
    return blend


if __name__ == "__main__":
    img = sys.argv[1]; nm = sys.argv[2]
    kws = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    add(img, nm, kws, on_progress=lambda m: print("  " + m, flush=True))
    print("DONE")
