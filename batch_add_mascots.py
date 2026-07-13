"""
Downloads/characters/*.webp (custom mascot images) -> batch 3D characters.
Har image: webp->png -> Rodin Detail 3D -> Blender rig -> char3d_lib manifest.
Resumable (glb/blend cache); errors par continue.

Run: python batch_add_mascots.py [SRC_DIR]
"""
import os
import re
import sys

from PIL import Image

import add_character

sys.stdout.reconfigure(encoding="utf-8")

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\shahbaz\Downloads\characters"
STAGE = os.path.join(add_character.config.BASE_DIR, "new_images", "mascots_png")
os.makedirs(STAGE, exist_ok=True)

# roman-urdu keyword hints (filename word -> extra match words)
HINTS = {
    "biryani": ["chawal", "food"], "samosa": ["food"], "sipahi": ["soldier", "fauji"],
    "ladoo": ["mithai", "sweet"], "mango": ["aam"], "king": ["badshah", "raja"],
    "onion": ["pyaz"], "uncle": ["chacha"], "lion": ["sher"], "tomato": ["tamatar"],
    "reporter": ["news", "sahafi"], "chili": ["mirch"], "potato": ["aloo"],
    "rabbit": ["khargosh"], "bunny": ["khargosh"], "astronaut": ["space"],
    "robot": ["mashine"], "cat": ["billi"], "fox": ["lomri"], "panda": [],
    "police": ["pulis"], "puppy": ["kutta", "dog"], "teacher": ["ustad"],
    "pencil": ["qalam"], "goat": ["bakri"], "parrot": ["tota"], "traffic": [],
    "cricket": ["ball"], "burger": ["food"], "tea": ["chai"], "cup": ["chai"],
    "chacha": ["uncle"], "naan": ["roti", "food"], "ninja": [], "dahi": ["food"],
    "bhalay": ["food"], "kite": ["patang"], "kaptan": ["captain"], "pizza": ["food"],
    "pilot": [], "drone": [], "dost": ["friend"], "lantern": ["chirag"],
    "lala": [], "moon": ["chand"], "baby": ["bacha"], "cloud": ["baadal"],
    "kid": ["bacha"], "water": ["pani"], "drop": ["pani"], "solar": ["suraj"],
    "battery": [], "bot": ["robot"], "camera": [], "book": ["kitab"],
    "backpack": ["bag"], "helmet": [], "hero": ["bahadur"], "keyboard": [],
    "kaka": ["uncle"], "mouse": ["chuha"], "dustbin": ["kachra"], "marker": ["qalam"],
    "magic": ["jadu"], "tiger": ["sher", "cheeta"], "time": [], "table": [],
    "toothbrush": ["brush"], "tinku": [], "cyber": ["robot"], "goat": ["bakri"],
    "tech": [], "confident": [], "cheerful": [], "cute": [], "playful": [],
    "friendly": [], "green": [], "teal": [], "rainbow": [], "sparkles": [],
    "sleepy": [], "pillow": [], "plush": [], "waistcoat": [], "full": [], "body": [],
    "microphone": ["mic"], "rickshaw": [], "driver": [], "angry": [], "mascot": [],
    "jump": [], "hero": ["bahadur"],
}
SKIP_WORDS = {"mascot", "full", "body", "cheerful", "confident", "playful", "friendly",
              "cute", "sleepy", "angry", "jump", "hero"}


def clean_name(fn):
    base = re.sub(r"\(\d+\)", "", fn).strip()
    base = re.sub(r"\.(webp|png|jpg|jpeg)$", "", base, flags=re.I)
    words = [w for w in re.split(r"[_\s\-]+", base) if w]
    name = "".join(w.capitalize() for w in words if w.lower() != "mascot")[:28] or "Char"
    # keywords: content words + hints
    kws = []
    for w in words:
        wl = w.lower()
        if wl in SKIP_WORDS:
            continue
        kws.append(wl)
        kws.extend(HINTS.get(wl, []))
    seen = set(); kws = [k for k in kws if not (k in seen or seen.add(k))]
    return name, (kws or [words[0].lower()])


def main():
    files = [f for f in os.listdir(SRC) if f.lower().endswith(".webp")]
    # dedupe: prefer non-"(1)" version; skip pure generic image*.webp
    seen_base = {}
    for f in sorted(files):
        base = re.sub(r"\s*\(\d+\)", "", f)
        if re.match(r"^image[\s_]*\d*\.webp$", base, re.I):
            continue                       # generic (koi keyword nahi) — skip
        seen_base.setdefault(base, f)
    todo = list(seen_base.items())
    limit = int(os.environ.get("MASCOT_LIMIT", "0"))    # 0 = all; warna itne naye process
    print(f"Total unique mascots: {len(todo)} (limit={limit or 'all'})\n", flush=True)

    done, fail, skip = [], [], []
    for i, (base, fn) in enumerate(todo, 1):
        name, kws = clean_name(base)
        png = os.path.join(STAGE, re.sub(r"\.webp$", ".png", base, flags=re.I))
        slug = add_character._slug(name)
        blend = os.path.join(add_character.RIG_DIR, f"{slug}.blend")
        if os.path.exists(blend):
            skip.append(name); continue          # pehle se rigged
        if limit and len(done) + len(fail) >= limit:
            break                                # chunk limit (loadshedding-safe)
        try:
            if not os.path.exists(png):
                im = Image.open(os.path.join(SRC, fn)).convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                bg.save(png)
            print(f"[{i}/{len(todo)}] {name}  kws={kws[:5]}", flush=True)
            add_character.add(png, name, kws, on_progress=lambda m: None)
            done.append(name)
        except Exception as e:
            print(f"  ✗ {name} FAIL: {str(e)[:150]}", flush=True)
            fail.append(name)
    print(f"\n=== DONE: {len(done)} added, {len(fail)} failed, {len(skip)} skipped(already) ===", flush=True)
    if fail:
        print("failed:", fail, flush=True)


if __name__ == "__main__":
    main()
