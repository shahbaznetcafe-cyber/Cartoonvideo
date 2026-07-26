"""Deterministic character voice direction for SBZ AI Video Studio.

Profiles are deliberately descriptive and provider-neutral: the selected TTS
provider supplies the timbre, while pitch/rate/pause choices make a cast sound
consistent without claiming unsupported voice-cloning.
"""
from __future__ import annotations

import re


_ARCHETYPES = (
    ("playful", ("baby", "bunny", "kid", "child", "chibi", "plush", "cat", "frog", "chicken", "panda", "fruit", "tamatar", "mirch", "kela", "potato", "onion", "mango"), "+28Hz", "+7%", "bright, playful cartoon energy"),
    ("robotic", ("robot", "bot", "drone", "cyber", "alien"), "+8Hz", "-2%", "clear, curious cartoon-tech delivery"),
    ("mysterious", ("witch", "ghost", "demon", "skull", "zombie", "vampire"), "-32Hz", "-7%", "soft, deliberate mysterious delivery"),
    ("regal", ("king", "queen", "knight", "hero", "captain", "adventurer"), "-12Hz", "-3%", "confident, warm storybook delivery"),
    ("grounded", ("farmer", "worker", "teacher", "doctor", "chef", "casual", "baba", "uncle"), "-8Hz", "-2%", "natural, friendly conversational delivery"),
)


def _haystack(character):
    if not character:
        return ""
    return " ".join(str(character.get(key, "")) for key in ("id", "name", "role", "description", "tags")).lower()


def profile_for_character(character, ordinal=0):
    """Return a stable, explainable voice profile for one character."""
    text = _haystack(character)
    gender = str((character or {}).get("gender") or "male").lower()
    for key, needles, pitch, rate, description in _ARCHETYPES:
        if any(needle in text for needle in needles):
            return {"id": key, "pitch": pitch, "rate": rate, "description": description,
                    "pause_style": "expressive" if key == "playful" else "measured"}
    # Small stable variation stops same-gender casts becoming indistinguishable.
    variants = [("+0Hz", "+0%"), ("-18Hz", "-3%"), ("+18Hz", "+4%"), ("-8Hz", "+2%")]
    pitch, rate = variants[ordinal % len(variants)]
    label = "warm feminine" if gender == "female" else "warm masculine"
    return {"id": "neutral", "pitch": pitch, "rate": rate,
            "description": f"{label} natural cartoon narration", "pause_style": "natural"}


def add_natural_pauses(text, language=None):
    """Conservative punctuation pass; works offline and never fabricates dialogue."""
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return value
    # Roman Urdu and English connective clauses sound more natural with a breath.
    value = re.sub(r"(?<![,،])\s+(lekin|magar|phir|aur|because|but|so)\s+", r", \1 ", value,
                   flags=re.IGNORECASE)
    # Do not stack pauses or alter already authored Urdu punctuation.
    value = re.sub(r",\s*,+", ",", value)
    if value[-1] not in ".!?؟۔…":
        value += "۔" if str(language or "").lower() == "urdu" else "."
    return value