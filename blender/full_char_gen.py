"""
new_images/ ke sab characters ko FULL 3D (fruit body + limbs) generate karo — Rodin Detail.
Output: blender/assets/full3d/<name>_full.glb. Resume (bane hue skip).
"""
import os, sys, time
import requests

sys.stdout.reconfigure(encoding="utf-8")
KEY = "vibecoding"
BASE = "https://hyperhuman.deemos.com/api/v2"
ROOT = r"D:\flayer\sbz-studio"
SRC = os.path.join(ROOT, "new_images")
OUT = os.path.join(ROOT, "blender", "assets", "full3d")
os.makedirs(OUT, exist_ok=True)


def gen(img_path, retries=3):
    b = open(img_path, "rb").read()
    files = [("images", ("0000.png", b, "image/png")),
             ("tier", (None, "Detail")), ("mesh_mode", (None, "Raw")),
             ("texture_mode", (None, "high"))]
    last = None
    for _ in range(retries):
        try:
            return requests.post(f"{BASE}/rodin", headers={"Authorization": f"Bearer {KEY}"},
                                 files=files, timeout=180).json()
        except Exception as e:
            last = e; time.sleep(5)
    return {"error": str(last)}


def wait_download(uuid, out_path, tries=80):
    for _ in range(tries):
        try:
            r = requests.post(f"{BASE}/download", headers={"Authorization": f"Bearer {KEY}"},
                              json={"task_uuid": uuid}, timeout=60).json()
            glb = [f for f in r.get("list", []) if f["name"].endswith(".glb")]
            if glb:
                open(out_path, "wb").write(requests.get(glb[0]["url"], timeout=200).content)
                return os.path.getsize(out_path)
        except Exception:
            pass
        time.sleep(7)
    return 0


imgs = sorted([f for f in os.listdir(SRC) if f.lower().endswith(".png")])
print(f"{len(imgs)} characters", flush=True)
done = 0
for f in imgs:
    name = os.path.splitext(f)[0]
    out = os.path.join(OUT, f"{name}_full.glb")
    if os.path.exists(out) and os.path.getsize(out) > 50000:
        print(f"[{name}] pehle se — skip", flush=True); done += 1; continue
    print(f"[{name}] generate...", flush=True)
    d = gen(os.path.join(SRC, f))
    uuid = d.get("uuid") or d.get("task_uuid")
    if not uuid:
        print(f"[{name}] FAIL: {str(d)[:150]}", flush=True); continue
    n = wait_download(uuid, out)
    if n:
        print(f"[{name}] DONE ({n} bytes)", flush=True); done += 1
    else:
        print(f"[{name}] download timeout", flush=True)
print(f"ALL_DONE {done}/{len(imgs)}", flush=True)
