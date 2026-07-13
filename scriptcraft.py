"""
Track A — Quality Engine. Professional multi-pass script generation:
  1) PLAN   — genre/cast/logline/beats + 3 hook variants -> best hook chuna jaye
  2) DRAFT  — plan + best hook par poora script (few-shot exemplars se floor uncha)
  3) POLISH — khud critique (hook/pacing/voice-distinct/repetition/payoff) -> final

Single-call generation ka ceiling amateur hota; ye pipeline har script professional banata.
Returns dict: {script, title, genre, cast, hook, logline, beats, cta, plan}.
"""
import json
import re

LANG_NAME = {"urdu": "Urdu (Urdu script)", "roman_urdu": "Roman Urdu", "english": "English"}
LENGTH_LINES = {"short": 6, "medium": 10, "long": 16}

# Few-shot: ye "kaisा GREAT lagta hai" ka floor set karta hai (Roman Urdu exemplar)
EXEMPLAR = """--- EXAMPLE of a GREAT short script (study the craft: instant hook, distinct
voices, escalation, punchy payoff, comment-bait) ---
[Scene: Chai ka dhaba, shaam]
Aloo: (excited) Ruko! Jis ne aaj meri chai mein cheeni daali, wo hero hai!
Tamatar: (smug) Cheeni? Maine to namak daala tha... "healthy" wali.
Aloo: (surprised) Namak?! Isi liye chai ne mujhe "acha beta" bola!
Tamatar: (deadpan) Chai nahi, wo main tha. Peeche se.
Aloo: (angry) Tamatar! Aaj ke baad chai main khud banaunga.
Tamatar: (grinning) Zaroor... bartan bhi tum hi dho lena, hero.
Aloo: (to camera) Aap batao — namak wali chai piyoge? Comment karo!
--- END EXAMPLE ---"""


def _clean(raw):
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        nl = raw.find("\n")
        if nl != -1 and len(raw[:nl].split()) <= 1:
            raw = raw[nl + 1:]
    return raw.strip()


def _json_obj(raw):
    raw = _clean(raw)
    s, e = raw.find("{"), raw.rfind("}")
    return json.loads(raw[s:e + 1])


def _plan(providers, idea, lang_name, n, genre, cast_rule, continuity, structure_hint):
    genre_rule = ("Auto-detect the single best genre." if genre in ("", "auto")
                  else f"Genre: {genre}.")
    struct = f"\nSTRUCTURE to follow: {structure_hint}" if structure_hint else ""
    cont = (f"\nSERIES CONTINUITY (later episode, stay consistent):\n{continuity}"
            if continuity else "")
    sysp = (
        "You are a world-class viral short-video story architect. Plan a script BEFORE writing it.\n"
        f"{genre_rule}\n{cast_rule}{struct}\n"
        "Design a tight arc for a ~{}-line video: strong hook -> escalation -> turn -> "
        "satisfying payoff. The FIRST 2 seconds decide retention.\n".format(n) +
        "Write 3 DISTINCT opening hook lines (different angles: shock / question / funny "
        "claim), then pick the single strongest as \"hook\" with a one-word reason.\n"
        "Reply with ONLY JSON (no markdown):\n"
        "{\"title\":\"catchy title in the story's language\",\"genre\":\"one word\","
        "\"logline\":\"one sentence\",\"cast\":[{\"name\":\"..\",\"voice\":\"how they speak, 3-4 words\"}],"
        "\"hooks\":[\"h1\",\"h2\",\"h3\"],\"hook\":\"the chosen best hook line\","
        "\"beats\":[\"setup\",\"escalation\",\"turn\",\"payoff\"],"
        "\"cta\":\"a comment-bait / engagement line for the end in the story's language\"}")
    user = f"Idea: {idea}\nLanguage for all text: {lang_name}{cont}"
    return _json_obj(providers.llm_generate(sysp, user, max_tokens=900, temperature=0.9))


def _draft(providers, plan, idea, lang_name, n, cast_rule):
    beats = " -> ".join(plan.get("beats", []))
    voices = "; ".join(f"{c.get('name')}: {c.get('voice','')}" for c in plan.get("cast", []))
    sysp = (
        "You are a professional cartoon dialogue writer. Write the FULL script from this plan.\n"
        f"{EXEMPLAR}\n"
        f"LANGUAGE: write ALL dialogue in {lang_name}.\n"
        f"{cast_rule}\n"
        f"CHARACTER VOICES (keep each DISTINCT): {voices}\n"
        f"ARC (beats): {beats}\n"
        f"OPENING HOOK (use as line 1, punchy): {plan.get('hook','')}\n"
        f"ENDING: land the payoff, then this engagement line: {plan.get('cta','')}\n"
        f"LENGTH: about {n} dialogue lines. Every line short, punchy, natural to speak aloud.\n"
        "FORMAT (strict):\n- First line: [Scene: <short place>]\n"
        "- Every other line: 'Name: (emotion) spoken line' (emotion one of "
        "happy|sad|angry|excited|surprised|neutral, optional).\n"
        "Reply with ONLY the script text.")
    user = f"Idea: {idea}\nTitle: {plan.get('title','')}"
    return _clean(providers.llm_generate(sysp, user, max_tokens=1400, temperature=0.85))


def _polish(providers, draft, lang_name):
    sysp = (
        "You are a ruthless script editor. Improve this cartoon script. Silently CHECK:\n"
        "- Is line 1 an instant, scroll-stopping hook? If weak, make it punchier.\n"
        "- Does EACH character have a clearly distinct voice? Fix sameness.\n"
        "- Any repeated words/phrases/ideas across lines? Remove repetition.\n"
        "- Is the pacing tight (no filler) and the ending a satisfying payoff?\n"
        "- Does every line sound natural spoken aloud in " + lang_name + "?\n"
        "Keep the SAME characters, language, scene headers, and 'Name: (emotion) line' format.\n"
        "Output ONLY the final improved script text — no commentary.")
    return _clean(providers.llm_generate(sysp, f"Script:\n{draft}", max_tokens=1400, temperature=0.7))


def craft(idea, language="roman_urdu", characters=None, length="medium", lines=None,
          genre="auto", cast_bios=None, continuity="", structure_hint="", polish=True):
    """Multi-pass professional script. Returns dict."""
    import providers
    idea = (idea or "").strip()
    if not idea:
        raise ValueError("Idea chahiye")
    chars = [c for c in (characters or []) if c and c.strip()]
    n = int(lines) if lines else LENGTH_LINES.get(length, 10)
    lang_name = LANG_NAME.get(language, "Roman Urdu")
    g = (genre or "auto").lower()

    if cast_bios:
        cast_rule = ("CAST: use ONLY these recurring characters, personalities CONSISTENT, "
                     "har ek kam az kam ek baar:\n" + "\n".join(f"- {b}" for b in cast_bios)
                     + "\nDo NOT invent others.")
    elif chars:
        cast_rule = ("CAST: use ONLY these characters, use EVERY one: "
                     f"{', '.join(c.title() for c in chars)}. Do NOT invent others.")
    else:
        cast_rule = ("CAST: choose 2-3 characters that fit the idea (animals, food, people, "
                     "mascots, objects). Short memorable names. Keep cast small.")

    plan = _plan(providers, idea, lang_name, n, g, cast_rule, continuity, structure_hint)
    draft = _draft(providers, plan, idea, lang_name, n, cast_rule)
    script = _polish(providers, draft, lang_name) if polish else draft

    return {
        "script": script,
        "title": plan.get("title", ""),
        "genre": plan.get("genre", g if g != "auto" else ""),
        "logline": plan.get("logline", ""),
        "cast": [c.get("name") for c in plan.get("cast", [])] or chars,
        "hook": plan.get("hook", ""),
        "hooks": plan.get("hooks", []),
        "beats": plan.get("beats", []),
        "cta": plan.get("cta", ""),
    }
