"""
3D Character Library — general (koi bhi cartoon character, sirf fruits nahi).
Manifest: characters3d.json — har character ka {name, keywords, blend, thumb}.
Naya character add karo (add_character.py) -> manifest mein aa jata hai -> videos mein usable.
"""
import json
import os

import config

MANIFEST = os.path.join(config.BASE_DIR, "characters3d.json")
RIG_DIR = os.path.join(config.BASE_DIR, "blender", "rigged", "blend")


def load():
    if os.path.exists(MANIFEST):
        try:
            return json.load(open(MANIFEST, encoding="utf-8"))
        except Exception:
            pass
    return []


def save(entries):
    json.dump(entries, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def blend_path(entry):
    b = entry.get("blend", "")
    if not os.path.isabs(b):
        b = os.path.join(RIG_DIR, b)
    return b if os.path.exists(b) else None


def add(name, keywords, blend_file, thumb=None):
    entries = load()
    entries = [e for e in entries if e.get("blend") != blend_file]   # dedupe
    entries.append({"name": name, "keywords": keywords, "blend": blend_file, "thumb": thumb})
    save(entries)
    return entries


def all_valid():
    return [e for e in load() if blend_path(e)]


def resolve_blend(value):
    """Ek character naam/id (picker se) -> blend path. Mascot naam ya roman-fruit naam."""
    v = (value or "").strip().lower()
    if not v:
        return None
    for e in load():
        if e.get("name", "").lower() == v and blend_path(e):
            return blend_path(e)
    # roman-fruit naam (Aloo -> potato) -> blend
    try:
        import story_templates
        for lc in story_templates.LIBRARY_CHARACTERS:
            if lc["name"].lower() == v or lc["id"].lower() == v:
                p = os.path.join(RIG_DIR, lc["package"] + ".blend")
                return p if os.path.exists(p) else None
    except Exception:
        pass
    return None


def assign(parsed_chars, overrides=None):
    """Har script character ko ek 3D character.
    overrides {char_id: naam} pehle (user ka intekhab), warna keyword match, warna round-robin."""
    entries = all_valid()
    if not entries:
        return {}
    overrides = overrides or {}
    result, used = {}, set()
    # 1) user overrides (preview dropdown) — sabse pehle, exact
    for ch in parsed_chars:
        ov = overrides.get(ch["id"])
        if ov:
            b = resolve_blend(ov)
            if b:
                result[ch["id"]] = b; used.add(os.path.basename(b))
    # 2) keyword match — sabse specific (longest matching keyword) jeette (collision se bacho)
    import re as _re
    for ch in parsed_chars:
        if ch["id"] in result:
            continue
        raw = f"{ch.get('id','')} {ch.get('name','')} {ch.get('role','')}".lower()
        # compact (space/underscore hata) taake "onion uncle" -> "onionuncle" match kare
        hay = raw + " " + _re.sub(r"[^a-z0-9]", "", raw)
        best, best_len = None, 0
        for e in entries:
            if e["blend"] in used:
                continue
            kws = [str(k).lower() for k in e.get("keywords", [])] + [e.get("name", "").lower()]
            m = max((len(k) for k in kws if k and k in hay), default=0)
            if m > best_len:
                best_len, best = m, e
        if best:
            result[ch["id"]] = blend_path(best); used.add(best["blend"])
    # 3) round-robin baqi
    pi = 0
    for ch in parsed_chars:
        if ch["id"] not in result:
            pool = [e for e in entries if e["blend"] not in used] or entries
            e = pool[pi % len(pool)]; pi += 1
            result[ch["id"]] = blend_path(e); used.add(e["blend"])
    return result
