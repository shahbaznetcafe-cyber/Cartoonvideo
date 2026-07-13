"""
Sketchfab se free (commercial-safe) 3D cartoon characters -> library mein add.
Steps: download glb (Sketchfab API) -> Blender auto-rig (rig_all.py) -> manifest entry
+ attribution (CC-BY ke liye credit zaroori) sketchfab_credits.json mein.

Use: python sketchfab_add.py            # CAST list (neeche) sab add
     python sketchfab_add.py <uid> <name> <kw1,kw2>   # ek custom add
"""
import json
import os
import subprocess
import sys
import time

import requests

import config
import char3d_lib

sys.stdout.reconfigure(encoding="utf-8")

TOKEN = "7b14508b21db4e8c9467ade32655be9c"
H = {"Authorization": f"Token {TOKEN}"}
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
BL_DIR = os.path.join(config.BASE_DIR, "blender")
GLB_DIR = os.path.join(BL_DIR, "assets", "full3d")
RIG_DIR = os.path.join(BL_DIR, "rigged", "blend")
THUMB_DIR = os.path.join(BL_DIR, "rigged")
CREDITS = os.path.join(config.BASE_DIR, "sketchfab_credits.json")

# chuni hui commercial-safe (CC Attribution / CC0) low-poly cartoon cast
#   (uid, display name, [keywords])
CAST = [
    ("7d30845d69c4474ebeddd177df6b7f02", "Bunny",  ["bunny", "rabbit", "khargosh"]),
    ("88ed6191446749b9a9e24b995bcb5e1d", "Fox",    ["fox", "lomri", "lomdi"]),
    ("8ebffa958b6247d09b0c40f33f03bbae", "Dragon", ["dragon", "azdaha", "baby dragon"]),
    ("51418a4ce4b348beb2c6d24c21b2926f", "Onion Monster", ["onion", "pyaz", "monster"]),
    ("5b20ca71fe4f475e8838420fd66519d2", "Duck",   ["duck", "batakh", "rubber duck"]),
    ("821874cf3c05443d9f2f9815572cff1a", "Kid",    ["kid", "boy", "bacha", "child", "person"]),
]


def _slug(name):
    return "".join(c for c in name.lower().replace(" ", "_") if c.isalnum() or c == "_")


def _valid_glb(data):
    """glTF magic + header total-length == actual length (truncation pakdo)."""
    import struct
    if len(data) < 12 or data[:4] != b"glTF":
        return False
    total = struct.unpack("<I", data[8:12])[0]
    return total == len(data)


def download_glb(uid, slug, on_progress=None, tries=4):
    out = os.path.join(GLB_DIR, f"{slug}_full.glb")
    os.makedirs(GLB_DIR, exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) > 50000:
        return out
    if on_progress:
        on_progress(f"Sketchfab se '{slug}' download ho raha...")
    last = ""
    for attempt in range(tries):
        try:
            d = requests.get(f"https://api.sketchfab.com/v3/models/{uid}/download",
                             headers=H, timeout=60).json()
            if "glb" not in d:
                raise RuntimeError(f"glb link nahi: {list(d.keys())}")
            data = requests.get(d["glb"]["url"], timeout=300).content
            if not _valid_glb(data):
                raise RuntimeError(f"corrupt/truncated glb ({len(data)} bytes)")
            open(out, "wb").write(data)
            return out
        except Exception as e:
            last = str(e)[:120]
            time.sleep(3 + attempt*2)
    raise RuntimeError(f"download fail (uid={uid}) baad {tries} tries: {last}")


def save_credit(uid, name):
    """Model detail se author + license save (CC-BY attribution ke liye zaroori)."""
    try:
        m = requests.get(f"https://api.sketchfab.com/v3/models/{uid}", headers=H, timeout=40).json()
        cr = {}
        if os.path.exists(CREDITS):
            cr = json.load(open(CREDITS, encoding="utf-8"))
        cr[uid] = {
            "name": name, "model": m.get("name"),
            "author": (m.get("user") or {}).get("displayName"),
            "author_url": (m.get("user") or {}).get("profileUrl"),
            "model_url": m.get("viewerUrl"),
            "license": (m.get("license") or {}).get("fullName"),
            "license_url": (m.get("license") or {}).get("url"),
        }
        json.dump(cr, open(CREDITS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [credit warn] {e}", flush=True)


def rig_batch(glbs, on_progress=None):
    if on_progress:
        on_progress(f"Blender mein {len(glbs)} character rig ho rahe...")
    subprocess.run([BLENDER, "--background", "--python", os.path.join(BL_DIR, "rig_all.py"),
                    "--", THUMB_DIR, *glbs], check=True)


def add_cast(cast, on_progress=None):
    glbs, meta = [], []
    for uid, name, kws in cast:
        slug = _slug(name)
        try:
            glb = download_glb(uid, slug, on_progress)
            save_credit(uid, name)
            glbs.append(glb); meta.append((name, kws, slug))
            print(f"  ✓ downloaded {name} -> {os.path.basename(glb)}", flush=True)
        except Exception as e:
            print(f"  ✗ {name} download fail: {e}", flush=True)
    if not glbs:
        raise RuntimeError("Koi glb download nahi hua")
    rig_batch(glbs, on_progress)
    added = []
    for name, kws, slug in meta:
        blend = os.path.join(RIG_DIR, f"{slug}.blend")
        if os.path.exists(blend):
            char3d_lib.add(name, kws, f"{slug}.blend", thumb=f"{slug}.png")
            added.append(name)
            print(f"  ✓ rigged + manifest: {name}", flush=True)
        else:
            print(f"  ✗ rig missing: {name}", flush=True)
    return added


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        uid = sys.argv[1]; nm = sys.argv[2]
        kws = sys.argv[3].split(",") if len(sys.argv) > 3 else [nm.lower()]
        cast = [(uid, nm, kws)]
    else:
        cast = CAST
    added = add_cast(cast, on_progress=lambda m: print("  " + m, flush=True))
    print(f"DONE — added: {added}")
