"""Shared dialogue-language and YouTube storytelling policy.

Prompt rules live here so quick, pro, template, long-form, series, improve,
and parser flows do not slowly drift into different writing styles.
"""
from __future__ import annotations

import re


LANGUAGE_NAMES = {
    "urdu": "Urdu (Urdu script)",
    "roman_urdu": "Roman Urdu",
    "english": "English",
    "hindi": "Hindi (Devanagari script)",
    "hinglish": "Hindi + English / Hinglish (about 85% Hindi, 15% English)",
}

YOUTUBE_STORY_RULES = """YOUTUBE STORYTELLING:
- Start with conflict, surprise, danger, a funny contradiction, or an unanswered question; no greeting or channel intro.
- Create one clear open loop in the opening and resolve it in the payoff.
- Every scene must add a new action, clue, complication, decision, or consequence; remove filler and repeated recaps.
- For long stories, introduce a meaningful turn every 20-35 seconds and a stronger midpoint reversal.
- Escalate emotional stakes, then deliver a visual climax and a satisfying earned resolution.
- Put any short engagement question after the payoff; never interrupt the story for a call-to-action.
"""

NATURAL_DIALOGUE_RULES = """NATURAL SPOKEN FLOW:
- Write contractions, reactions, interruptions, and sentence lengths the way people actually speak; avoid formal essay language.
- Give every character a distinct rhythm and vocabulary.
- Add purposeful punctuation to every spoken line: commas for light pauses, ellipses only for hesitation/drama, and ? or ! only when earned.
- End every complete sentence with punctuation. Avoid comma splices, repeated exclamation marks, and decorative ellipses.
- Keep one speakable thought per dialogue line and read it mentally aloud before returning it.
"""


def language_name(language: str | None) -> str:
    return LANGUAGE_NAMES.get(str(language or "").lower(), "Roman Urdu")


def language_prompt(language: str | None) -> str:
    language = str(language or "roman_urdu").lower()
    if language == "hinglish":
        return (
            "Write natural Indian Hinglish: approximately 85% of spoken words must be "
            "everyday Hindi in Devanagari and approximately 15% must be simple, familiar "
            "English in Latin script. Code-switch only where a real Hindi speaker naturally "
            "would; do not alternate languages mechanically, translate the same thought twice, "
            "or fill lines with English jargon. Keep names unchanged."
        )
    if language == "hindi":
        return "Write natural conversational Hindi in Devanagari; keep only unavoidable names or common technical terms in Latin script."
    if language == "urdu":
        return "Write natural conversational Urdu in Urdu script and use Urdu punctuation (، ۔ ؟)."
    if language == "english":
        return "Write natural conversational English."
    return "Write natural conversational Roman Urdu in Latin script; do not silently convert it to Hindi or Urdu script."


def full_prompt_policy(language: str | None, *, youtube: bool = True) -> str:
    parts = [f"LANGUAGE POLICY: {language_prompt(language)}", NATURAL_DIALOGUE_RULES]
    if youtube:
        parts.append(YOUTUBE_STORY_RULES)
    return "\n".join(parts)


_END_MARKS = (".", "?", "!", "…", "۔", "؟", "।")


def normalize_spoken_punctuation(text: str, language: str | None = None) -> str:
    """Conservative TTS cleanup that never rewrites the speaker's words."""
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = re.sub(r"\s+([,.;:!?،۔؟।])", r"\1", value)
    value = re.sub(r"([,،])([^\s])", r"\1 \2", value)
    value = re.sub(r"!{2,}", "!", value)
    value = re.sub(r"\?{2,}", "?", value)
    value = re.sub(r"\.{4,}", "...", value)
    if value and not value.endswith(_END_MARKS):
        lang = str(language or "").lower()
        value += "۔" if lang == "urdu" else ("।" if lang == "hindi" else ".")
    return value
