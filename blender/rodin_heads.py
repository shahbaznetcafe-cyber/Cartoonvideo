"""
Rodin (Hyper3D) se fruit heads ke 3D models generate karo — headless, apni Python se.
Har package se head crop -> Rodin image-to-3D -> glb download -> blender/assets/head_<slug>_3d.glb
Free trial key: vibecoding.
"""
import json, os, sys, time, io
import requests
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
KEY = "vibecoding"
BASE = "https://hyperhuman.deemos.com/api/v2"
ROOT = r"D:\flayer\sbz-studio"
ASSETS = os.path.join(ROOT, "blender", "assets")

FRUITS = sys.argv[1:] or ["tomato", "onion", "carrot", "chilli", "banana"]


def crop_head(slug):
    """Package se head crop (transparent PNG)."""
    rig = json.load(open(os.path.join(ROOT, "characters", slug, "rig.json")))
    hb = rig["head_box"]
    im = Image.open(os.path.join(ROOT, "characters", slug, "mouth_closed.png")).convert("RGBA")
    head = im.crop(hb)
    bb = head.split()[3].getbbox()
    if bb:
        head = head.crop(bb)
    p = os.path.join(ASSETS, f"head_{slug}.png")
    head.save(p)
    return p


def gen(img_path, retries=3):
    b = open(img_path, "rb").read()
    files = [
        ("images", ("0000.png", b, "image/png")),
        ("tier", (None, "Detail")),      # Detail = behtar quality (free key allow karta hai)
        ("mesh_mode", (None, "Raw")),
        ("texture_mode", (None, "high")),
    ]
    last = None
    for _ in range(retries):
        try:
            r = requests.post(f"{BASE}/rodin", headers={"Authorization": f"Bearer {KEY}"},
                              files=files, timeout=180)
            return r.json()
        except Exception as e:
            last = e; time.sleep(5)
    return {"error": str(last)}


def wait_download(uuid, out_path, tries=70):
    """Download endpoint ko poll karo jab tak .glb ready na ho (status ki zaroorat nahi)."""
    for _ in range(tries):
        try:
            r = requests.post(f"{BASE}/download", headers={"Authorization": f"Bearer {KEY}"},
                              json={"task_uuid": uuid}, timeout=60).json()
            glb = [f for f in r.get("list", []) if f["name"].endswith(".glb")]
            if glb:
                content = requests.get(glb[0]["url"], timeout=180).content
                open(out_path, "wb").write(content)
                return len(content)
        except Exception:
            pass
        time.sleep(7)
    return 0


for slug in FRUITS:
    out = os.path.join(ASSETS, f"head_{slug}_3d.glb")
    if os.path.exists(out) and os.path.getsize(out) > 10000:
        print(f"[{slug}] pehle se hai — skip", flush=True); continue
    print(f"[{slug}] crop + generate...", flush=True)
    try:
        img = crop_head(slug)
        d = gen(img)
        tu = d.get("uuid") or d.get("task_uuid")
        if not tu:
            print(f"[{slug}] gen fail: {str(d)[:200]}", flush=True); continue
        print(f"[{slug}] submitted (uuid {tu}), waiting for glb...", flush=True)
        n = wait_download(tu, out)
        if n:
            print(f"[{slug}] DONE -> {out} ({n} bytes)", flush=True)
        else:
            print(f"[{slug}] download timeout", flush=True)
    except Exception as e:
        print(f"[{slug}] ERROR {e}", flush=True)

print("ALL_HEADS_DONE", flush=True)
