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

import actions
import beatsheets
import dialogue_style
import duration_planner
import hooklab
import retention_critic

LANG_NAME = dialogue_style.LANGUAGE_NAMES
LENGTH_LINES = {
    key: int(value["lines"])
    for key, value in duration_planner.DURATION_PRESETS.items()
}
LENGTH_LINES.update({"short": 6, "medium": 12, "long": 24})

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


def series_memory_block(memory):
    """Phase 5 — render structured series memory as prompt text.

    Pure and testable: turns ``series.series_memory()`` into an explicit block so
    recurring characters keep the same persona, speech style and catchphrase
    across episodes (recurring characters are what grow a channel).
    """
    if not memory:
        return ""
    lines = []
    if memory.get("name") or memory.get("premise"):
        lines.append(f"SERIES: {memory.get('name','')} — {memory.get('premise','')}".strip(" —"))
    characters = memory.get("characters") or {}
    if characters:
        lines.append("RECURRING CAST (keep persona, speech style and catchphrase EXACTLY consistent):")
        for cid, ch in characters.items():
            bits = [b for b in (ch.get("persona"), ch.get("role")) if b]
            if ch.get("speechStyle"):
                bits.append(f"speaks: {ch['speechStyle']}")
            if ch.get("catchphrase"):
                bits.append(f'catchphrase: "{ch["catchphrase"]}"')
            suffix = f" ({'; '.join(bits)})" if bits else ""
            lines.append(f"- {ch.get('name', cid)}{suffix}")
    events = memory.get("priorEvents") or []
    if events:
        lines.append("STORY SO FAR (stay consistent; you may reference these):")
        lines.extend(f"- {e}" for e in events)
    return "\n".join(lines)


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


def _plan(providers, idea, language, lang_name, n, duration_brief, genre, cast_rule, continuity,
          structure_hint, performance_rule=""):
    genre_rule = ("Auto-detect the single best genre." if genre in ("", "auto")
                  else f"Genre: {genre}.")
    struct = f"\nSTRUCTURE to follow: {structure_hint}" if structure_hint else ""
    cont = (f"\nSERIES CONTINUITY (later episode, stay consistent):\n{continuity}"
            if continuity else "")
    sysp = (
        "You are a world-class viral short-video story architect. Plan a script BEFORE writing it.\n"
        f"{genre_rule}\n{cast_rule}{struct}\n{performance_rule}\n"
        f"{dialogue_style.full_prompt_policy(language)}\n"
        f"{actions.prompt_policy()}\n"
        "Design a tight arc for a ~{}-line video: strong hook -> escalation -> turn -> "
        "satisfying payoff. The FIRST 2 seconds decide retention.\n".format(n) +
        "DURATION CONTRACT: Target {} ({}-{} spoken dialogue words; about {} words per line). "
        "Plan enough meaningful story beats to fill this natural speaking time; do not pad with repetition.\n".format(
            duration_brief["target_label"], duration_brief["minimum_words"],
            duration_brief["maximum_words"], duration_brief["average_words_per_line"]) +
        "Also write a one-line PROMISE: the single curiosity or benefit the title "
        "implies, which the ending MUST deliver (no clickbait the story can't pay off).\n"
        "Write 3 DISTINCT opening hook lines (different angles: shock / question / funny "
        "claim), then pick the single strongest as \"hook\" with a one-word reason.\n"
        "Reply with ONLY JSON (no markdown):\n"
        "{\"title\":\"catchy title in the story's language\",\"genre\":\"one word\","
        "\"logline\":\"one sentence\",\"promise\":\"the click promise the ending delivers\","
        "\"audience\":\"who this is for, 2-4 words\",\"coreMessage\":\"the takeaway in one short phrase\","
        "\"cast\":[{\"name\":\"..\",\"voice\":\"how they speak, 3-4 words\"}],"
        "\"hooks\":[\"h1\",\"h2\",\"h3\"],\"hook\":\"the chosen best hook line\","
        "\"cta\":\"a comment-bait / engagement line for the end in the story's language\"}")
    user = f"Idea: {idea}\nLanguage for all text: {lang_name}{cont}"
    return _json_obj(providers.llm_generate(sysp, user, max_tokens=900, temperature=0.9))


def _draft(providers, plan, idea, language, lang_name, n, duration_brief, cast_rule,
           performance_rule="", max_tokens=1400, beatsheet_text="", emotion_arc=None):
    beats = beatsheet_text or " -> ".join(plan.get("beats", []))
    voices = "; ".join(f"{c.get('name')}: {c.get('voice','')}" for c in plan.get("cast", []))
    arc_line = (f"EMOTION ARC (make the mood move, don't stay flat): "
                f"{' -> '.join(emotion_arc)}\n" if emotion_arc else "")
    promise_line = (f"TITLE PROMISE the ending must deliver: {plan.get('promise','')}\n"
                    if plan.get("promise") else "")
    sysp = (
        "You are a professional cartoon dialogue writer. Write the FULL script from this plan.\n"
        f"{EXEMPLAR}\n"
        f"LANGUAGE: write ALL dialogue in {lang_name}.\n"
        f"{dialogue_style.full_prompt_policy(language)}\n"
        f"{actions.prompt_policy()}\n"
        f"{cast_rule}\n"
        f"{performance_rule}\n"
        f"CHARACTER VOICES (keep each DISTINCT): {voices}\n"
        f"{promise_line}"
        f"BEAT SHEET — write the story beat by beat, honoring each beat's job and "
        f"rough word budget:\n{beats}\n"
        f"{arc_line}"
        f"OPENING HOOK (use as line 1, punchy): {plan.get('hook','')}\n"
        f"ENDING: land the payoff, then this engagement line: {plan.get('cta','')}\n"
        f"LENGTH: about {n} dialogue lines and {duration_brief['minimum_words']}-{duration_brief['maximum_words']} spoken words "
        f"(target {duration_brief['target_label']}; roughly {duration_brief['average_words_per_line']} words per line). "
        "Every line must remain natural to speak aloud; add story detail, reactions and scene progress instead of filler.\n"
        "FORMAT (strict):\n- First line: [Scene: <short place>]\n"
        "- Every other line: 'Name: (emotion; action; location) spoken line'.\n"
        "Reply with ONLY the script text.")
    user = f"Idea: {idea}\nTitle: {plan.get('title','')}"
    return _clean(providers.llm_generate(sysp, user, max_tokens=max_tokens, temperature=0.85))


def _polish(providers, draft, language, lang_name, duration_brief, performance_rule="",
            max_tokens=1400, targeted_fixes=""):
    # Phase 2: the deterministic retention critic supplies targeted fixes; if it
    # found no structural problems, targeted_fixes is empty and we skip below.
    targeted = (f"RETENTION FIXES (apply these specifically):\n{targeted_fixes}\n"
                if targeted_fixes else "")
    sysp = (
        "You are a ruthless script editor. Improve this cartoon script. Silently CHECK:\n"
        "- Is line 1 an instant, scroll-stopping hook? If weak, make it punchier.\n"
        "- Does EACH character have a clearly distinct voice? Fix sameness.\n"
        "- Any repeated words/phrases/ideas across lines? Remove repetition.\n"
        "- Is the pacing tight (no filler) and the ending a satisfying payoff?\n"
        "- Does every line sound natural spoken aloud in " + lang_name + "?\n"
        + targeted
        + "Preserve a total spoken-word range of {}-{} words for the {} target; never shorten it below range just to make it punchy.\n".format(
            duration_brief["minimum_words"], duration_brief["maximum_words"], duration_brief["target_label"])
        + dialogue_style.full_prompt_policy(language) + "\n"
        + actions.prompt_policy() + "\n"
        + performance_rule + "\n"
        "Keep the SAME characters, language, scene headers, and 'Name: (emotion; action; location) line' format.\n"
        "Output ONLY the final improved script text — no commentary.")
    return _clean(providers.llm_generate(sysp, f"Script:\n{draft}", max_tokens=max_tokens, temperature=0.7))


def craft(idea, language="roman_urdu", characters=None, length="medium", lines=None,
          genre="auto", cast_bios=None, continuity="", structure_hint="", polish=True,
          series_memory=None):
    """Multi-pass professional script. Returns dict."""
    import providers
    idea = (idea or "").strip()
    if not idea:
        raise ValueError("Idea chahiye")
    seen_cast, chars = set(), []
    for value in characters or []:
        name = str(value or "").strip()
        if name and name.casefold() not in seen_cast:
            chars.append(name)
            seen_cast.add(name.casefold())
    import character_performance
    performance_rule = character_performance.script_guidance(chars)
    length = duration_planner.normalize_duration(length)
    n = int(lines) if lines else LENGTH_LINES.get(length, 12)
    duration_brief = duration_planner.writing_brief(length, language)
    lang_name = LANG_NAME.get(language, "Roman Urdu")
    g = (genre or "auto").lower()

    memory_block = series_memory_block(series_memory)
    if memory_block:
        # Structured series memory supersedes free-text bios: it pins persona,
        # speech style and catchphrase so episodes stay recognisably the same show.
        cast_rule = (memory_block + "\nUse ONLY this cast, every one at least once. "
                     "Do NOT invent others.")
        if not continuity and series_memory.get("priorEvents"):
            continuity = "\n".join(series_memory["priorEvents"])
    elif cast_bios:
        cast_rule = ("CAST: use ONLY these recurring characters, personalities CONSISTENT, "
                     "har ek kam az kam ek baar:\n" + "\n".join(f"- {b}" for b in cast_bios)
                     + "\nDo NOT invent others.")
    elif chars:
        cast_rule = ("CAST: use ONLY these characters, use EVERY one: "
                     f"{', '.join(c.title() for c in chars)}. Do NOT invent others.")
    else:
        cast_rule = ("CAST: choose 2-3 characters that fit the idea (animals, food, people, "
                     "mascots, objects). Short memorable names. Keep cast small.")

    plan = _plan(providers, idea, language, lang_name, n, duration_brief, g, cast_rule, continuity,
                 structure_hint, performance_rule)

    # Phase 1 — retention beat sheet (genre-tuned, duration-scaled) + Hook Lab.
    # Genre comes from the caller, else the planner's auto-detected genre.
    resolved_genre = g if g not in ("", "auto") else plan.get("genre", "")
    built_sheet = beatsheets.build(resolved_genre, duration_brief)
    beatsheet_text = beatsheets.as_prompt_lines(built_sheet)
    hook_result = hooklab.generate_and_score(
        providers, idea, plan.get("promise", "") or plan.get("logline", ""),
        lang_name, fallback_hook=plan.get("hook", ""))
    # Hook Lab wins over the planner's blind pick; keep planner hook as fallback.
    plan["hook"] = hook_result["hook"] or plan.get("hook", "")

    token_budget = min(6000, max(1400, int(duration_brief["maximum_words"] * 2.2)))
    draft = _draft(providers, plan, idea, language, lang_name, n, duration_brief, cast_rule,
                   performance_rule, max_tokens=token_budget,
                   beatsheet_text=beatsheet_text, emotion_arc=built_sheet["emotionArc"])

    # Phase 2 — deterministic retention critic drives a targeted polish. If the
    # draft already passes every structural check, the rewrite is skipped.
    chosen_cta = plan.get("cta", "")
    chosen_promise = plan.get("promise", "")
    critic_args = {
        "hook": plan.get("hook", ""), "cta": chosen_cta, "promise": chosen_promise,
        "planned_arc": built_sheet["emotionArc"],
        "cta_anchor": built_sheet.get("ctaAnchor", "after_payoff"),
        # Series episodes must stay on-cast; one-off scripts have no fixed cast.
        "expected_cast": (series_memory or {}).get("castNames") or None,
    }
    if polish:
        report = retention_critic.analyze(draft, **critic_args)
        fixes = retention_critic.fix_instructions(report)
        script = _polish(providers, draft, language, lang_name, duration_brief,
                         performance_rule, max_tokens=token_budget, targeted_fixes=fixes) \
            if fixes else draft
    else:
        script = draft
    # Re-analyze the final script so the review UI shows the shipped state.
    retention_report = retention_critic.analyze(script, **critic_args)
    retention_report["notes"] = retention_critic.flag_notes(retention_report)

    return {
        "script": script,
        "title": plan.get("title", ""),
        "genre": built_sheet["genre"],
        "logline": plan.get("logline", ""),
        "promise": plan.get("promise", ""),
        "audience": plan.get("audience", ""),
        "coreMessage": plan.get("coreMessage", ""),
        "cast": [c.get("name") for c in plan.get("cast", [])] or chars,
        "hook": plan.get("hook", ""),
        "hooks": hook_result["hooks"] or plan.get("hooks", []),
        "hookRanking": hook_result["ranking"],
        "beats": [b["id"] for b in built_sheet["beats"]],
        "beatSheet": built_sheet["beats"],
        "emotionArc": built_sheet["emotionArc"],
        "ctaAnchor": built_sheet.get("ctaAnchor", "after_payoff"),
        "retentionReport": retention_report,
        "cta": plan.get("cta", ""),
        "character_performance": [
            {key: profile.get(key) for key in (
                "name", "tier", "speech_mode", "lip_sync", "facial_ready", "camera"
            )}
            for profile in character_performance.profiles_for_names(chars)
        ],
    }
