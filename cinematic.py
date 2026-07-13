"""
Cinematic Story Mode — reference viral videos jaisा look.
Har dialogue line ke liye ek MUKAMMAL AI scene image (character + costume + action +
background sab ek saath). Consistency ke liye "Character Bible" (fixed tafseeli description)
har prompt mein. Voiceover-driven (precise lip-sync ki zaroorat nahi).
"""
import io
import os

import requests
from PIL import Image

import config
from runware_client import post_tasks, new_uuid

GEN_MODEL = "runware:101@1"

# Har veggie ki FIXED visual identity (har scene mein same rahe). "fruit/veg HEAD" explicit.
CHARACTER_BIBLES = {
    "potato":    "whose head is a giant brown potato (not a human head) with small friendly eyes and a warm smile",
    "tomato":    "whose head is a giant round shiny red tomato with a small green leafy top and big expressive eyes",
    "onion":     "whose head is a giant purple-red onion with papery skin and a small green sprout on top, big eyes",
    "carrot":    "whose head is a giant orange carrot with a green leafy top, cheerful face",
    "chilli":    "whose head is a long curved red chili pepper with a green stem, fiery expressive face",
    "banana":    "whose head is a giant yellow banana with a playful cartoon face",
    "eggplant":  "whose head is a giant glossy purple eggplant with a green cap and big eyes",
    "ladyfinger": "whose head is a giant green okra ladyfinger, slim and ridged, with a cartoon face",
    "radish":    "whose head is a giant white radish with a green leafy top and big eyes",
    "pineapple": "whose head is a giant golden pineapple with a spiky green crown, friendly face",
}

# name/keyword -> package (bible key)
_NAME2PKG = {
    "aloo": "potato", "potato": "potato",
    "tamatar": "tomato", "tomato": "tomato",
    "pyaz": "onion", "onion": "onion",
    "gajar": "carrot", "carrot": "carrot",
    "mirch": "chilli", "chilli": "chilli", "chili": "chilli",
    "kela": "banana", "banana": "banana",
    "baingan": "eggplant", "eggplant": "eggplant", "brinjal": "eggplant",
    "bhindi": "ladyfinger", "okra": "ladyfinger", "ladyfinger": "ladyfinger",
    "mooli": "radish", "radish": "radish",
    "ananas": "pineapple", "pineapple": "pineapple",
}

STYLE = ("Pixar 3D animation style, cinematic lighting, highly detailed, shallow depth of "
         "field, warm atmosphere, 4k, professional render")


def veggie_for(name):
    n = (name or "").lower()
    for kw, pkg in _NAME2PKG.items():
        if kw in n:
            return pkg
    return None


def assign_costumes(parsed):
    """Har character ke role se ek chhota costume phrase (LLM, ek batch call). Fail -> role text."""
    import providers
    chars = parsed.get("characters", [])
    roles = [f"{c.get('name','')}: {c.get('role','')}" for c in chars]
    if not roles:
        return
    sysp = ("For each character give ONLY a short visual costume/clothing description (5-10 words) "
            "that matches their role, for a cartoon fruit/vegetable character with a human body. "
            "Example: 'white chef hat and apron' or 'black police uniform with cap and badge'. "
            "Reply with ONLY a JSON array of strings, same order and length as input.")
    import json
    try:
        raw = providers.llm_generate(sysp, json.dumps(roles, ensure_ascii=False),
                                     max_tokens=600, temperature=0.5)
        s, e = raw.find("["), raw.rfind("]")
        arr = json.loads(raw[s:e + 1])
    except Exception as ex:
        print(f"  [costume fail] {ex}")
        arr = []
    for i, c in enumerate(chars):
        c["costume"] = (arr[i] if i < len(arr) else "") or "casual clothes"


def character_bible(ch):
    """Ek character ka poora fixed bible string (veggie identity + costume)."""
    veg = ch.get("_veggie") or veggie_for(ch.get("name", "")) or "potato"
    ident = CHARACTER_BIBLES.get(veg, CHARACTER_BIBLES["potato"])
    costume = ch.get("costume", "casual clothes")
    return f"a cartoon character {ident}, on a human body wearing {costume}"


def scene_prompt(parsed, line, chars_by_id):
    """Ek line ke liye full cinematic scene prompt (speaker + action + setting)."""
    spk = line.get("speaker", "narrator")
    ch = chars_by_id.get(spk, {})
    setting = line.get("_setting") or "a busy Pakistani street market"
    emotion = line.get("emotion", "neutral")
    action = line.get("action") or ""

    if spk == "narrator" or not ch:
        # narration -> establishing shot (koi khaas character nahi)
        return f"{setting}, cartoon fruit and vegetable characters, {STYLE}"

    bible = character_bible(ch)
    parts = [bible]
    if action:
        parts.append(action)
    if emotion and emotion != "neutral":
        parts.append(f"{emotion} expression")
    parts.append(f"in {setting}")
    parts.append(STYLE)
    return ", ".join(parts)


def generate_scene(prompt, out_path, w, h):
    """FLUX se ek cinematic scene image. 64-multiple dimensions."""
    w = (w // 64) * 64
    h = (h // 64) * 64
    task = {
        "taskType": "imageInference", "taskUUID": new_uuid(), "model": GEN_MODEL,
        "positivePrompt": prompt,
        "negativePrompt": "flat, 2d, low quality, blurry, deformed, extra limbs, text, watermark",
        "width": w, "height": h, "numberResults": 1,
        "outputType": "URL", "outputFormat": "PNG",
    }
    for attempt in range(4):
        try:
            url = post_tasks([task])[0]["imageURL"]
            img = Image.open(io.BytesIO(requests.get(url, timeout=120).content)).convert("RGB")
            img.save(out_path)
            return out_path
        except Exception as e:
            import time
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def prepare(parsed):
    """Story ko cinematic ke liye tayyar karo: veggie assign + costume + per-line setting."""
    chars = parsed.get("characters", [])
    # veggie assign (name se, warna round-robin library)
    pool = list(CHARACTER_BIBLES.keys())
    pi = 0
    used = set()
    for c in chars:
        v = veggie_for(c.get("name", "")) or veggie_for(c.get("role", ""))
        if not v or v in used:
            v = pool[pi % len(pool)]
            pi += 1
        c["_veggie"] = v
        used.add(v)
    assign_costumes(parsed)
    # per-line setting (scene ka background_prompt / location)
    for sc in parsed.get("scenes", []):
        setting = sc.get("background_prompt") or sc.get("location") or "a busy street market"
        for ln in sc.get("lines", []):
            ln["_setting"] = setting
    return parsed
