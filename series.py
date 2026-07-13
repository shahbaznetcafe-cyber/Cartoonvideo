"""
Phase 4 — Recurring Characters + Series/Episode continuity.

- Characters: fixed personality + voice, dobara istemaal ho (channel ka apna cast).
- Series: ek show (premise + cast + episodes ki history).
- generate_episode(): agla episode likho — cast ki personalities + pichhle
  episodes ka recap (continuity) inject karke. Phir episode ka summary bana kar
  series history mein save (taake agle episode ki continuity ban sake).

Data ek hi JSON file mein: series_data.json  ({characters:{}, series:{}}).
"""
import json
import os
import time

import config

DATA_PATH = os.path.join(config.BASE_DIR, "series_data.json")


# ---------------- storage ----------------
def load():
    if os.path.exists(DATA_PATH):
        try:
            d = json.load(open(DATA_PATH, encoding="utf-8"))
        except Exception:
            d = {}
    else:
        d = {}
    d.setdefault("characters", {})
    d.setdefault("series", {})
    return d


def save(d):
    json.dump(d, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return d


def _slug(name):
    s = "".join(c.lower() if c.isalnum() else "-" for c in (name or "")).strip("-")
    return s or f"id-{int(time.time())}"


# ---------------- characters ----------------
def list_characters():
    return list(load()["characters"].values())


def add_character(name, trait="", gender="male", catchphrase="", role="", cid=None):
    """Recurring character banao/update karo. Returns character dict."""
    d = load()
    name = (name or "").strip()
    if not name:
        raise ValueError("Character ka naam chahiye")
    cid = cid or _slug(name)
    d["characters"][cid] = {
        "id": cid, "name": name, "trait": (trait or "").strip(),
        "gender": (gender or "male").lower(),
        "catchphrase": (catchphrase or "").strip(), "role": (role or "").strip(),
    }
    save(d)
    return d["characters"][cid]


def delete_character(cid):
    d = load()
    existed = d["characters"].pop(cid, None) is not None
    # cast se bhi hatao
    for s in d["series"].values():
        s["cast"] = [c for c in s.get("cast", []) if c != cid]
    save(d)
    return existed


def _bio(ch):
    """Character -> ek line 'Name (trait; catchphrase: "...")' prompt ke liye."""
    parts = [ch["name"]]
    inner = []
    if ch.get("trait"):
        inner.append(ch["trait"])
    if ch.get("role"):
        inner.append(ch["role"])
    if ch.get("catchphrase"):
        inner.append(f'catchphrase: "{ch["catchphrase"]}"')
    if inner:
        parts.append("(" + "; ".join(inner) + ")")
    return " ".join(parts)


# ---------------- series ----------------
def list_series():
    out = []
    for s in load()["series"].values():
        out.append({k: s[k] for k in ("id", "name", "premise", "genre", "language", "cast")}
                   | {"episodes": len(s.get("episodes", []))})
    return out


def get_series(sid):
    return load()["series"].get(sid)


def create_series(name, premise="", genre="auto", language="roman_urdu", cast=None, sid=None):
    d = load()
    name = (name or "").strip()
    if not name:
        raise ValueError("Series ka naam chahiye")
    sid = sid or _slug(name)
    cast = [c for c in (cast or []) if c in d["characters"]]
    d["series"][sid] = {
        "id": sid, "name": name, "premise": (premise or "").strip(),
        "genre": (genre or "auto").lower(), "language": language,
        "cast": cast, "episodes": [],
    }
    save(d)
    return d["series"][sid]


def update_series(sid, **fields):
    d = load()
    s = d["series"].get(sid)
    if not s:
        raise ValueError("Series nahi mili")
    for k in ("name", "premise", "genre", "language"):
        if k in fields and fields[k] is not None:
            s[k] = fields[k]
    if "cast" in fields and fields["cast"] is not None:
        s["cast"] = [c for c in fields["cast"] if c in d["characters"]]
    save(d)
    return s


def delete_series(sid):
    d = load()
    existed = d["series"].pop(sid, None) is not None
    save(d)
    return existed


def _continuity_text(s):
    """Pichhle episodes ka recap (continuity ke liye)."""
    eps = s.get("episodes", [])
    if not eps:
        return ""
    lines = []
    for e in eps[-6:]:  # aakhri 6 episodes
        lines.append(f"Episode {e['num']} — \"{e.get('title','')}\": {e.get('summary','')}")
    return "\n".join(lines)


def _summarize(script, language):
    """Episode ka 1-2 line summary (agle episode ki continuity ke liye)."""
    import providers
    try:
        sysp = ("Summarize this cartoon episode script in ONE or TWO short sentences "
                "capturing the key events and where the characters end up. "
                "Reply with ONLY the summary, in the script's language.")
        return providers.llm_generate(sysp, script[:3000], max_tokens=180,
                                       temperature=0.4).strip()
    except Exception:
        return ""


def generate_episode(sid, idea="", length="medium", save_episode=True, on_progress=None):
    """
    Series ka AGLA episode likho — cast personalities + pichhle episodes ka recap
    inject karke. length: short|medium|long (single-scene) YA 3min|5min|8min (long-form).
    Returns: {script, title, episode_num, summary, genre, cast, logline?, scenes?}.
    """
    import story_templates
    d = load()
    s = d["series"].get(sid)
    if not s:
        raise ValueError("Series nahi mili")
    cast_ids = s.get("cast", [])
    cast_chars = [d["characters"][c] for c in cast_ids if c in d["characters"]]
    if len(cast_chars) < 1:
        raise ValueError("Series mein kam az kam 1 character add karein")
    cast_bios = [_bio(c) for c in cast_chars]
    cast_names = [c["name"] for c in cast_chars]
    continuity = _continuity_text(s)
    ep_num = len(s.get("episodes", [])) + 1
    lang = s.get("language", "roman_urdu")
    genre = s.get("genre", "auto")
    # premise idea ke sath jodo
    full_idea = idea.strip()
    if s.get("premise"):
        full_idea = (f"Series premise: {s['premise']}\nThis episode's idea: "
                     f"{full_idea or 'continue the story naturally'}")

    is_long = length in story_templates.LONGFORM_PLANS
    if is_long:
        res = story_templates.generate_longform(
            full_idea, language=lang, characters=cast_names, minutes=length,
            genre=genre, on_progress=on_progress, cast_bios=cast_bios,
            continuity=continuity)
    else:
        res = story_templates.generate_freeform(
            full_idea, language=lang, characters=cast_names, length=length,
            genre=genre, cast_bios=cast_bios, continuity=continuity)

    script = res.get("script", "")
    summary = _summarize(script, lang)
    title = res.get("title") or f"Episode {ep_num}"
    if save_episode:
        s.setdefault("episodes", []).append({
            "num": ep_num, "title": title, "summary": summary,
            "created": time.strftime("%Y-%m-%d %H:%M"),
        })
        save(d)
    out = {
        "script": script, "title": title, "episode_num": ep_num,
        "summary": summary, "genre": res.get("genre", genre),
        "cast": cast_names,
    }
    if is_long:
        out["logline"] = res.get("logline", "")
        out["scenes"] = res.get("scenes", [])
    return out
