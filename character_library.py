"""
Custom Character Library (Phase 2 ka chhota hissa).
User apni PNG characters/ folder mein daalta hai + characters.json manifest.
Parser jo character detect karta hai, usse manifest se match kar ke user ki image deta hai.
Agar match na ho to assets.py AI se generate kar leta hai.

characters.json misaal:
[
  {
    "names": ["ali", "علی", "boy"],   // in mein se koi bhi character ke id/name/role mein ho to match
    "file": "ali.png",                 // characters/ folder ke andar
    "mouth": [0.5, 0.62],              // mooh ki jagah (0..1) lip-sync ke liye (optional)
    "circle": true                     // true = circle avatar, false = as-is (transparent)
  }
]
"""
import json
import os

import config

LIB_DIR = os.path.join(config.BASE_DIR, "characters")
MANIFEST = os.path.join(LIB_DIR, "characters.json")

os.makedirs(LIB_DIR, exist_ok=True)


def _load_manifest():
    if not os.path.exists(MANIFEST):
        return []
    try:
        return json.load(open(MANIFEST, encoding="utf-8"))
    except Exception as e:
        print(f"  [character_library] manifest parse error: {e}")
        return []


def find_for(character):
    """
    character: parsed dict (id, name, role).
    return: dict {image, mouth, circle} agar user image mile, warna None.
    """
    entries = _load_manifest()
    if not entries:
        return None

    haystack = " ".join([
        str(character.get("id", "")),
        str(character.get("name", "")),
        str(character.get("role", "")),
    ]).lower()

    for e in entries:
        names = [str(n).lower() for n in e.get("names", [])]
        if any(n and n in haystack for n in names):
            img = e.get("file", "")
            if not os.path.isabs(img):
                img = os.path.join(LIB_DIR, img)
            if os.path.exists(img):
                return {
                    "image": img,
                    "mouth": e.get("mouth"),          # [x,y] frac ya None
                    "circle": e.get("circle", True),
                    "voice": e.get("voice"),          # per-character voice override (optional)
                    "package": e.get("package"),      # folder-package (rigged layers) — optional
                }
            else:
                print(f"  [character_library] file nahi mili: {img}")
    return None


def all_entries():
    """Manifest ke saare valid (file maujood) characters — normalized."""
    out = []
    for e in _load_manifest():
        img = e.get("file", "")
        if not os.path.isabs(img):
            img = os.path.join(LIB_DIR, img)
        if os.path.exists(img):
            out.append({
                "image": img, "mouth": e.get("mouth"),
                "circle": e.get("circle", True), "voice": e.get("voice"),
                "names": e.get("names", []), "package": e.get("package"),
            })
    return out


def assign(parsed_chars):
    """
    Har script-character ko ek LIBRARY character do (auto-choose).
    1) pehle keyword-match (e.g. 'tamatar' -> tomato)
    2) baqi ko unused library characters round-robin se
    Sirf library characters use hote hain — koi AI character nahi.
    return: dict {char_id: entry}
    """
    entries = all_entries()
    if not entries:
        return {}
    used, result = set(), {}

    # pass 1: direct keyword match
    for ch in parsed_chars:
        e = find_for(ch)
        if e and e["image"] not in used:
            result[ch["id"]] = e
            used.add(e["image"])

    # pass 2: baqi characters ko unused (warna cycle) assign karo
    pi = 0
    for ch in parsed_chars:
        if ch["id"] in result:
            continue
        pool = [e for e in entries if e["image"] not in used] or entries
        e = pool[pi % len(pool)]
        result[ch["id"]] = e
        used.add(e["image"])
        pi += 1
    return result
