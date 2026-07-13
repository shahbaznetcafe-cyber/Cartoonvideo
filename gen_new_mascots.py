"""
5 naye mascot characters — end-to-end: reference image (Runware FLUX) -> 3D (Rodin AI)
-> Blender auto-rig -> characters3d.json mein register.

Chalao (apne PC par, venv active karke):
    python gen_new_mascots.py            # sab 5
    python gen_new_mascots.py aalu_bhai  # sirf ek (slug se)
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import config
import providers
import add_character

OUT_DIR = os.path.join(config.BASE_DIR, "characters", "new_mascots")
os.makedirs(OUT_DIR, exist_ok=True)

NEG = ("No famous cartoon copy, no extra fingers, no blurry image, no text, "
       "no watermark, no scary face, no distorted body, low quality, deformed")

# slug, display name, keywords (script mein inn naamon se match hoga), image prompt
CHARACTERS = [
    ("aalu_bhai", "Aalu Bhai", ["aalu bhai", "aloo bhai"],
     "Cute original potato cartoon character, full body front view, big "
     "expressive eyes, funny smile, small arms and legs, desi waistcoat, kid-friendly "
     "3D mascot style, clean white background, ultra HD, sharp details, soft studio "
     "lighting, no text."),
    ("pyaz_uncle", "Pyaz Uncle", ["pyaz uncle", "pyaaz uncle", "onion uncle"],
     "Original onion cartoon uncle character, round onion body, kind "
     "emotional face, moustache, big watery eyes, simple kurta style outfit, full body "
     "front view, 3D cute mascot, clean background, HD quality, soft lighting, no text."),
    ("mango_king", "Mango King", ["mango king", "aam king"],
     "Cute mango king cartoon mascot, golden mango body, tiny crown, "
     "royal cape, happy confident face, big eyes, full body front view, kid-friendly 3D "
     "style, clean white background, ultra HD, sharp details, no text."),
    ("tamatar_reporter", "Tamatar Reporter", ["tamatar reporter", "tomato reporter"],
     "Funny tomato reporter cartoon character, red tomato body, "
     "holding small microphone, press jacket, excited face, big eyes, full body front "
     "view, 3D mascot style, clean background, high quality HD, soft shadows, no text."),
    ("mirchi_madam", "Mirchi Madam", ["mirchi madam", "mirch madam", "chili madam"],
     "Original green chili female cartoon character, angry but cute "
     "expression, stylish glasses, tiny handbag, full body front view, expressive eyes, "
     "3D kid-friendly mascot style, clean white background, ultra HD, sharp details, "
     "no text."),
]

W, H = 832, 1216  # portrait full-body, 64-multiple


def run_one(slug, name, keywords, prompt):
    img_path = os.path.join(OUT_DIR, f"{slug}.png")
    if not (os.path.exists(img_path) and os.path.getsize(img_path) > 10000):
        print(f"[{slug}] 1/2 reference image generate ho rahi (Runware FLUX)...", flush=True)
        providers.image_generate(prompt, W, H, img_path, negative=NEG)
    else:
        print(f"[{slug}] image pehle se maujood, skip", flush=True)

    print(f"[{slug}] 2/2 3D rig ho raha (Rodin AI + Blender)... (kaafi minute lag sakte)", flush=True)
    add_character.add(img_path, name, keywords,
                       on_progress=lambda m: print(f"  [{slug}] {m}", flush=True))
    print(f"[{slug}] ✅ DONE — library mein add ho gaya\n", flush=True)


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    results = []
    for slug, name, kws, prompt in CHARACTERS:
        if only and slug != only:
            continue
        try:
            run_one(slug, name, kws, prompt)
            results.append((slug, "OK"))
        except Exception as e:
            print(f"[{slug}] ❌ FAIL: {e}\n", flush=True)
            results.append((slug, f"FAIL: {e}"))

    print("=== SUMMARY ===")
    for slug, status in results:
        print(f"{slug}: {status}")
