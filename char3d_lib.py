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

# Story characters aksar Urdu/Hindi script ya roman mein aate hain ("خرگوش",
# "khargosh"), jabke library keywords angrezi mein hain ("bunny", "rabbit").
# Yeh map har concept ke Urdu-script + roman forms ko un angrezi keywords se
# jorta hai jo library characters ke paas pehle se hain — taake sahi character
# assign ho, na ke round-robin se koi bhi.  Keys lowercase; Urdu bila-case.
CHARACTER_CONCEPTS = {
    # animals
    "rabbit": "rabbit bunny", "bunny": "rabbit bunny", "khargosh": "rabbit bunny",
    "خرگوش": "rabbit bunny", "خرگوش": "rabbit bunny",
    "cat": "cat", "billi": "cat", "بلی": "cat", "بلّی": "cat",
    "dog": "dog", "kutta": "dog", "کتا": "dog", "کتّا": "dog",
    "puppy": "dog pug", "pug": "dog pug",
    "monkey": "monkey", "bandar": "monkey", "بندر": "monkey",
    "cow": "cow", "gaaye": "cow", "gaay": "cow", "گائے": "cow",
    "chicken": "chicken", "hen": "chicken", "murghi": "chicken", "مرغی": "chicken",
    "bird": "bird pigeon birb", "pigeon": "pigeon", "kabootar": "pigeon", "کبوتر": "pigeon",
    "fish": "fish", "machli": "fish", "مچھلی": "fish",
    "shark": "shark", "sharky": "shark",
    "frog": "frog", "maindak": "frog", "مینڈک": "frog",
    "dragon": "dragon", "azhdaha": "dragon", "اژدہا": "dragon", "ڈریگن": "dragon",
    "dino": "dino dinosaur", "dinosaur": "dino dinosaur", "ڈائنوسار": "dino dinosaur",
    "yeti": "yeti", "shark2": "shark",
    # roles / people
    "captain": "captain pirate", "kaptaan": "captain pirate", "کپتان": "captain pirate",
    "pirate": "pirate", "qazaq": "pirate", "قزاق": "pirate",
    "king": "king", "badshah": "king", "بادشاہ": "king",
    "soldier": "soldier", "sipahi": "soldier", "فوجی": "soldier", "سپاہی": "soldier",
    "farmer": "farmer", "kisan": "farmer", "کسان": "farmer",
    "doctor": "doctor", "hakeem": "doctor", "ڈاکٹر": "doctor",
    "chef": "chef", "cook": "chef", "bawarchi": "chef", "باورچی": "chef",
    "ninja": "ninja", "نینجا": "ninja",
    "wizard": "wizard witch", "jadugar": "wizard witch", "جادوگر": "wizard witch",
    "witch": "witch", "dayan": "witch", "ڈائن": "witch",
    "viking": "viking", "cowboy": "cowboy",
    "astronaut": "astronaut spacesuit", "spaceman": "astronaut spacesuit",
    "khalabaz": "astronaut spacesuit", "خلاباز": "astronaut spacesuit",
    "robot": "robot bot", "روبوٹ": "robot bot",
    "ghost": "ghost skeleton", "bhoot": "ghost skeleton", "بھوت": "ghost skeleton",
    "skeleton": "skeleton", "dhancha": "skeleton", "ڈھانچہ": "skeleton",
    "zombie": "zombie", "adventurer": "adventurer explorer", "hero": "adventurer explorer",
    "elf": "elf", "goblin": "goblin", "knight": "knight",
    # generic humans -> plain casual/adventurer humans (round-robin friendly)
    "boy": "casual boy", "larka": "casual boy", "لڑکا": "casual boy",
    "girl": "casual girl", "larki": "casual girl", "لڑکی": "casual girl",
    "man": "casual man", "aadmi": "casual man", "آدمی": "casual man",
    "woman": "casual woman", "aurat": "casual woman", "عورت": "casual woman",
}


def concept_keywords(*texts):
    """Return English keyword tokens implied by any Urdu/roman/English character
    word found in the given texts (id/name/role).  Longest keys first so
    multi-word forms win before their substrings."""
    blob = " ".join(str(t or "") for t in texts)
    low = blob.lower()
    tokens = []
    for key, mapped in CHARACTER_CONCEPTS.items():
        is_urdu = any(ord(c) > 0x600 for c in key)
        hit = key in blob if is_urdu else key.lower() in low
        if hit:
            tokens.append(mapped)
    return " ".join(dict.fromkeys(tokens))   # de-dupe, keep order


def load():
    if os.path.exists(MANIFEST):
        try:
            with open(MANIFEST, encoding="utf-8") as manifest_file:
                return json.load(manifest_file)
        except Exception:
            pass
    return []


def save(entries):
    with open(MANIFEST, "w", encoding="utf-8") as manifest_file:
        json.dump(entries, manifest_file, ensure_ascii=False, indent=2)


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


def entry_for_blend(blend):
    """Return manifest metadata for an assigned Blender path/package."""
    slug = os.path.splitext(os.path.basename(str(blend or "")))[0].lower()
    if not slug:
        return None
    return next((entry for entry in load()
                 if os.path.splitext(os.path.basename(str(entry.get("blend") or "")))[0].lower() == slug),
                None)


def runtime_metadata(blend):
    """Small renderer-safe body, face and lip-sync capability payload."""
    entry = entry_for_blend(blend) or {}
    capability_id = str(entry.get("capability_id") or "")
    try:
        import character_performance
        performance = character_performance.profile_for_entry(entry)
    except Exception:
        performance = {
            "tier": str(entry.get("animation_tier") or "SKELETAL_BASIC"),
            "speech_mode": "body_only", "lip_sync": "none", "facial_ready": False,
        }
    return {
        "capabilityId": capability_id,
        "animationTier": str(entry.get("animation_tier") or performance.get("tier") or "LEGACY"),
        "facialTier": str(performance.get("tier") or "SKELETAL_BASIC"),
        "speechMode": str(performance.get("speech_mode") or "body_only"),
        "lipSyncMode": str(performance.get("lip_sync") or "none"),
        "facialReady": bool(performance.get("facial_ready")),
        "library": "quaternius" if capability_id.startswith("quaternius_") else "sbz",
    }


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


def assign(parsed_chars, overrides=None, library=None):
    """Har script character ko ek 3D character.
    overrides {char_id: naam} pehle (user ka intekhab), warna keyword match, warna round-robin."""
    entries = all_valid()
    selected_library = str(library or "").strip().lower()
    if selected_library in {"sbz", "quaternius"}:
        entries = [entry for entry in entries
                   if runtime_metadata(blend_path(entry) or "").get("library") == selected_library]
    if not entries:
        raise ValueError(f"No ready characters are available in the selected {selected_library or 'requested'} library")
    generic_keywords = {"character", "animated", "humanoid", "quaternius", "human",
                        "humans", "monster", "monsters", "person", "figure"}
    if not entries:
        return {}
    overrides = overrides or {}
    result, used = {}, set()
    # 1) user overrides (preview dropdown) — sabse pehle, exact
    for ch in parsed_chars:
        ov = overrides.get(ch["id"])
        if ov:
            b = resolve_blend(ov)
            if b and (selected_library not in {"sbz", "quaternius"}
                      or runtime_metadata(b).get("library") == selected_library):
                result[ch["id"]] = b; used.add(os.path.basename(b))
    # 2) keyword match — sabse specific (longest matching keyword) jeette (collision se bacho)
    def fit_rank(entry, need):
        try:
            import character_performance
            profile = character_performance.profile_for_entry(entry)
        except Exception:
            profile = {"tier": entry.get("animation_tier") or "SKELETAL_BASIC"}
        tier = profile.get("tier")
        if need == "skeletal_action":
            return {"SKELETAL_INTERACTIVE": 0, "SKELETAL_BASIC": 1,
                    "FULL_FACIAL": 2, "VISEME_FACE": 3, "LEGACY_JAW": 4,
                    "STATIC": 9}.get(tier, 8)
        if need == "dialogue":
            return {"FULL_FACIAL": 0, "VISEME_FACE": 1, "LEGACY_JAW": 2,
                    "SKELETAL_INTERACTIVE": 5, "SKELETAL_BASIC": 6,
                    "STATIC": 9}.get(tier, 8)
        if need == "hybrid":
            # A hybrid scene must not sacrifice locomotion for a jaw-only
            # character.  The director will still warn and stage long speech
            # as body-led until a facial-ready asset is installed.
            return {"SKELETAL_INTERACTIVE": 0, "SKELETAL_BASIC": 1,
                    "FULL_FACIAL": 2, "VISEME_FACE": 3, "LEGACY_JAW": 4,
                    "STATIC": 9}.get(tier, 8)
        return {"FULL_FACIAL": 0, "VISEME_FACE": 1, "SKELETAL_INTERACTIVE": 2,
                "SKELETAL_BASIC": 3, "LEGACY_JAW": 4, "STATIC": 9}.get(tier, 8)

    import re as _re
    for ch in parsed_chars:
        if ch["id"] in result:
            continue
        raw = f"{ch.get('id','')} {ch.get('name','')} {ch.get('role','')}".lower()
        # compact (space/underscore hata) taake "onion uncle" -> "onionuncle" match kare
        hay = raw + " " + _re.sub(r"[^a-z0-9]", "", raw)
        # Urdu/Hindi/roman character words -> angrezi keywords (khargosh -> bunny)
        concepts = concept_keywords(ch.get("id"), ch.get("name"), ch.get("role"))
        if concepts:
            hay += " " + concepts
        best, best_len, best_fit = None, 0, 99
        for e in entries:
            if e["blend"] in used:
                continue
            kws = [str(k).lower() for k in e.get("keywords", [])
                   if str(k).lower() not in generic_keywords] + [e.get("name", "").lower()]
            m = max((len(k) for k in kws if k and k in hay), default=0)
            rank = fit_rank(e, ch.get("performance_need"))
            if m > best_len or (m and m == best_len and rank < best_fit):
                best_len, best_fit, best = m, rank, e
        if (best and ch.get("performance_need") == "skeletal_action"
                and best_len <= 4 and best_fit > 1):
            best = None
        if best:
            result[ch["id"]] = blend_path(best); used.add(best["blend"])
    # 3) capability-aware round-robin baqi
    pi = 0
    for ch in parsed_chars:
        if ch["id"] not in result:
            pool = [e for e in entries if e["blend"] not in used] or entries
            pool = sorted(pool, key=lambda entry: (fit_rank(entry, ch.get("performance_need")),
                                                   str(entry.get("name") or "").casefold()))
            e = pool[pi % len(pool)]; pi += 1
            result[ch["id"]] = blend_path(e); used.add(e["blend"])
    return result
