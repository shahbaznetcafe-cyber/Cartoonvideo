"""
Close the duration loop with REAL measurement instead of a words-per-second guess.

Word budgets are only an estimate: the measured speaking rate varies from about
1.5 to 3.3 words/second across languages, voices and line lengths, so a script
written to a "2 minute" budget can still synthesize to 83 seconds.  The renderer
used to hide that gap behind a frozen final frame.

After voices exist we know the exact duration, so this module asks the writer to
extend the script by the measured shortfall, re-parses it, and lets the caller
re-synthesize (already-voiced lines stay cached).  Deterministic helpers here are
unit tested; only ``extend_script`` calls a provider.
"""
from __future__ import annotations

import re

import duration_planner

# Stop when we are within this fraction of the target, and never loop forever.
ACCEPTABLE_RATIO = 0.92
MAX_ROUNDS = 2
MIN_SHORTFALL_SECONDS = 4.0


def timeline_duration(timeline):
    """Total spoken duration of a generated timeline, in seconds."""
    return sum(float(entry.get("duration") or 0) for entry in timeline or [])


def spoken_words(timeline):
    return sum(len(re.findall(r"\S+", str(entry.get("text") or "")))
               for entry in timeline or [])


def measured_rate(timeline):
    """Words per second actually achieved, or None when there is no signal."""
    seconds = timeline_duration(timeline)
    words = spoken_words(timeline)
    if seconds <= 0 or words <= 0:
        return None
    return words / seconds


def shortfall(timeline, target_seconds):
    """Seconds still missing against the target (0 when long enough)."""
    target = float(target_seconds or 0)
    if target <= 0:
        return 0.0
    return max(0.0, target - timeline_duration(timeline))


def needs_extension(timeline, target_seconds):
    """True when the script is short enough to be worth extending."""
    target = float(target_seconds or 0)
    if target <= 0:
        return False
    actual = timeline_duration(timeline)
    if actual <= 0:
        return False
    gap = target - actual
    return gap >= MIN_SHORTFALL_SECONDS and (actual / target) < ACCEPTABLE_RATIO


def words_needed(timeline, target_seconds, language=None):
    """How many extra spoken words the shortfall represents.

    Uses the rate this project actually achieved when available, which is far
    more accurate than the language default.
    """
    gap = shortfall(timeline, target_seconds)
    if gap <= 0:
        return 0
    rate = measured_rate(timeline) or duration_planner.words_per_second(language)
    return max(1, int(round(gap * rate)))


def build_prompt(script_text, extra_words, target_label, language_name):
    """System/user prompt for the extension pass (kept pure for testing)."""
    system = (
        "You are a professional cartoon script editor. The script below is TOO SHORT "
        f"for its {target_label} target when spoken aloud.\n"
        f"Add approximately {extra_words} MORE spoken words in {language_name}.\n"
        "RULES:\n"
        "- Keep every existing line, character and scene exactly as they are.\n"
        "- Add NEW dialogue lines (and reactions) that deepen the same story: more "
        "cause and effect, richer reactions, small obstacles — never filler or repetition.\n"
        "- Keep the opening hook as the first line and the payoff/CTA at the end; "
        "insert the new material in the MIDDLE.\n"
        "- Keep the exact format: '[Scene: location]' headers and "
        "'Name: (emotion; action; location) spoken line'.\n"
        "Reply with ONLY the complete extended script text."
    )
    user = f"Script to extend:\n{script_text}"
    return system, user


def script_from_parsed(parsed):
    """Render a parsed story back into script text for the extension pass."""
    out = []
    for scene in (parsed or {}).get("scenes", []) or []:
        location = scene.get("location") or scene.get("background_prompt") or "scene"
        out.append(f"[Scene: {location}]")
        for line in scene.get("lines", []) or []:
            emotion = line.get("emotion", "neutral")
            action = line.get("action", "") or "none"
            out.append(f"{line.get('speaker','')}: ({emotion}; {action}; {location}) "
                       f"{line.get('text','')}")
    return "\n".join(out)


def extend_script(providers, script_text, extra_words, target_label, language,
                  language_name):
    """Ask the writer for a longer script. Returns text (original on failure)."""
    try:
        system, user = build_prompt(script_text, extra_words, target_label, language_name)
        budget = min(6000, max(1200, int(extra_words * 6)))
        raw = providers.llm_generate(system, user, max_tokens=budget, temperature=0.7)
        text = (raw or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            newline = text.find("\n")
            if newline != -1 and len(text[:newline].split()) <= 1:
                text = text[newline + 1:]
        return text.strip() or script_text
    except Exception as exc:
        print(f"  [duration extend skip] {str(exc)[:140]}", flush=True)
        return script_text
