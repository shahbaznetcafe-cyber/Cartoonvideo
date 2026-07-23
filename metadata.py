"""
Track C — Packaging / Monetization. Script se publish-ready YouTube metadata:
titles (SEO + click), description (hook+summary+hashtags+CTA), tags, thumbnail text,
pinned comment, aur (long-form ke liye) chapters.

generate(script, language, platform) -> dict.
"""
import json
import re

LANG_NAME = {"urdu": "Urdu (Urdu script)", "roman_urdu": "Roman Urdu", "english": "English"}


def _json_obj(raw):
    raw = (raw or "").strip().strip("`")
    s, e = raw.find("{"), raw.rfind("}")
    return json.loads(raw[s:e + 1])


def _speakers(script):
    names = []
    for ln in (script or "").splitlines():
        m = re.match(r"\s*([A-Za-z][\w' ]{0,24}?):", ln)
        if m and not ln.strip().lower().startswith("[scene"):
            nm = m.group(1).strip()
            if nm and nm.lower() != "narrator" and nm not in names:
                names.append(nm)
    return names


def generate(script, language="roman_urdu", platform="youtube", promise="", title_hint=""):
    """Script -> YouTube package (titles/description/tags/thumbnail/pinned/chapters).

    ``promise`` and ``title_hint`` (from the script engine) tie the packaging to
    the story's intended click-promise so the title/thumbnail and the payoff are
    one coherent contract — no clickbait the script cannot deliver.
    """
    import providers
    lang_name = LANG_NAME.get(language, "Roman Urdu")
    plat = (platform or "youtube").lower()
    short = plat in ("shorts", "tiktok", "reels")
    kind = ("YouTube Shorts / TikTok / Reels (vertical, <60s)" if short
            else "YouTube (long-form / standard)")

    contract = ""
    if promise:
        contract += (f"\nSTORY PROMISE (the payoff delivers this — titles/thumbnail must "
                     f"tease exactly this, no clickbait beyond it): {promise}")
    if title_hint:
        contract += f"\nPREFERRED TITLE DIRECTION (align with, refine, keep the promise): {title_hint}"

    sysp = (
        "You are a YouTube growth strategist + copywriter for an animated cartoon channel. "
        f"From the script, produce publish-ready packaging for {kind}.{contract}\n"
        "Rules:\n"
        "- TITLES: 5 options. Click-worthy + SEO. Mix curiosity, emotion, and a clear keyword. "
        "Keep under ~70 chars. No clickbait lies.\n"
        "- DESCRIPTION: 2-4 lines — a hook line, one-line summary, then a call-to-action "
        "(subscribe + comment). End with 4-6 relevant #hashtags.\n"
        "- TAGS: 12-18 search keywords (comma list), mix broad + specific + the theme.\n"
        "- THUMBNAIL_TEXT: 2-4 BIG bold words for the thumbnail (super short, punchy).\n"
        "- PINNED_COMMENT: one engaging question to drive comments.\n"
        + ("- CHAPTERS: [] (short video, skip).\n" if short else
           "- CHAPTERS: 3-6 'mm:ss Title' style markers if the story has clear scenes, else [].\n") +
        f"Write titles/description/thumbnail/pinned in {lang_name} (tags can mix English for reach).\n"
        "Reply with ONLY JSON: {\"titles\":[..5..],\"description\":\"..\",\"tags\":[..],"
        "\"thumbnail_text\":\"..\",\"pinned_comment\":\"..\",\"chapters\":[..]}")
    user = f"Characters: {', '.join(_speakers(script)) or 'n/a'}\nScript:\n{script[:2600]}"
    try:
        d = _json_obj(providers.llm_generate(sysp, user, max_tokens=800, temperature=0.75))
    except Exception as e:
        return {"error": str(e)[:200]}
    # normalize
    d.setdefault("titles", [])
    d.setdefault("tags", [])
    d.setdefault("chapters", [])
    if isinstance(d.get("tags"), str):
        d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]
    for k in ("description", "thumbnail_text", "pinned_comment"):
        d.setdefault(k, "")
    d["platform"] = plat
    return d
