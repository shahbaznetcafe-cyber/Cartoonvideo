"""
3D Character Library — general (koi bhi cartoon character, sirf fruits nahi).
Manifest: characters3d.json — har character ka {name, keywords, blend, thumb}.
Naya character add karo (add_character.py) -> manifest mein aa jata hai -> videos mein usable.
"""
import json
import os
from copy import deepcopy

import config
import character_validator

MANIFEST = os.path.join(config.BASE_DIR, "characters3d.json")
RIG_DIR = os.path.join(config.BASE_DIR, "blender", "rigged", "blend")
THREE_CHAR_DIR = os.path.join(config.BASE_DIR, "threejs_render", "assets", "chars")
_VALIDATION_CACHE = {}


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


def glb_path(entry):
    """Manifest entry -> exact GLB path used by threejs_render/render_scene.js."""
    source = str(entry.get("blend") or "")
    slug = os.path.splitext(os.path.basename(source))[0]
    return os.path.join(THREE_CHAR_DIR, slug + ".glb") if slug else ""


def validate_entry(entry, use_cache=True):
    """Validate one manifest character without loading or modifying its model."""
    path = glb_path(entry)
    try:
        stat = os.stat(path)
        file_fingerprint = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        file_fingerprint = (None, None)
    fingerprint = file_fingerprint + (
        str(entry.get("name") or ""),
        str(entry.get("blend") or ""),
        bool(entry.get("unregistered")),
    )
    cache_key = os.path.abspath(path) if path else "<missing>" + str(entry.get("name") or "")
    cached = _VALIDATION_CACHE.get(cache_key)
    if use_cache and cached and cached[0] == fingerprint:
        return deepcopy(cached[1])
    report = character_validator.validate_glb(path or "missing.glb", entry)
    if entry.get("unregistered"):
        report["warnings"].append({
            "code": "unregistered_glb",
            "message": "GLB exists in the Three.js character directory but is not registered in characters3d.json",
        })
    _VALIDATION_CACHE[cache_key] = (fingerprint, report)
    return deepcopy(report)


def validate_blend(blend, use_cache=True):
    """Validate the Three.js GLB corresponding to an assigned Blender path."""
    basename = os.path.basename(str(blend or ""))
    slug = os.path.splitext(basename)[0].lower()
    entry = next((item for item in load()
                  if os.path.splitext(os.path.basename(str(item.get("blend") or "")))[0].lower() == slug),
                 {"name": slug or "Unknown", "blend": basename})
    return validate_entry(entry, use_cache=use_cache)


def validate_assignments(assignments, use_cache=True):
    """Produce the project report for the character IDs selected for a render."""
    reports = []
    for character_id in sorted(assignments):
        report = validate_blend(assignments[character_id], use_cache=use_cache)
        report["character"]["id"] = character_id
        reports.append(report)
    return {"schema_version": character_validator.SCHEMA_VERSION, "characters": reports}


def validation_report(entries=None, use_cache=True):
    """Validate the complete 3D manifest and return UI/API-ready JSON data."""
    selected = list(entries) if entries is not None else list(load())
    if entries is None:
        registered = {
            os.path.splitext(os.path.basename(str(entry.get("blend") or "")))[0].lower()
            for entry in selected
        }
        try:
            for filename in sorted(os.listdir(THREE_CHAR_DIR), key=str.casefold):
                if not filename.lower().endswith(".glb"):
                    continue
                slug = os.path.splitext(filename)[0]
                if slug.lower() not in registered:
                    selected.append({
                        "name": slug,
                        "blend": filename,
                        "unregistered": True,
                    })
        except OSError:
            pass
    reports = [validate_entry(entry, use_cache=use_cache) for entry in selected]
    tiers = {tier: 0 for tier in ("LEGACY_JAW", "SKELETAL_BASIC", "VISEME_FACE", "FULL_FACIAL")}
    for report in reports:
        if report.get("tier") in tiers:
            tiers[report["tier"]] += 1
    compatible = sum(1 for report in reports if report.get("valid_glb") and report.get("tier"))
    average = round(sum(report.get("compatibility_percent", 0) for report in reports) / len(reports)) if reports else 0
    return {
        "schema_version": character_validator.SCHEMA_VERSION,
        "summary": {
            "total": len(reports),
            "supported": compatible,
            "invalid_or_unsupported": len(reports) - compatible,
            "average_compatibility_percent": average,
            "unregistered": sum(1 for report in reports if not report.get("character", {}).get("registered", True)),
            "tiers": tiers,
        },
        "characters": reports,
    }


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
