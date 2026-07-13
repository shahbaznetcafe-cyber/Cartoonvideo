"""Small, provider-neutral grapheme/phoneme/viseme fallback maps.

These rules are original SBZ heuristics.  They do not copy TalkingHead's
language rule tables and intentionally remain compact enough to audit.
"""

from __future__ import annotations

import re
import unicodedata


PHONEME_TO_VISEME = {
    "SIL": "viseme_sil",
    "PP": "viseme_PP",
    "FF": "viseme_FF",
    "TH": "viseme_TH",
    "DD": "viseme_DD",
    "KK": "viseme_kk",
    "CH": "viseme_CH",
    "SS": "viseme_SS",
    "NN": "viseme_nn",
    "RR": "viseme_RR",
    "AA": "viseme_aa",
    "E": "viseme_E",
    "I": "viseme_I",
    "O": "viseme_O",
    "U": "viseme_U",
}

VISEME_ORDER = tuple(PHONEME_TO_VISEME.values())

# Relative articulation time used when a word span is divided into frames.
PHONEME_DURATION = {
    "PP": 0.75, "FF": 0.85, "TH": 0.85, "DD": 0.70, "KK": 0.75,
    "CH": 0.85, "SS": 0.85, "NN": 0.80, "RR": 0.80,
    "AA": 1.25, "E": 1.10, "I": 1.10, "O": 1.20, "U": 1.20,
}

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u0600-\u06ff]+(?:['’][A-Za-z\u0600-\u06ff]+)*")
_URDU_RE = re.compile(r"[\u0600-\u06ff]")


ENGLISH_MULTI = (
    ("tion", ("SS", "AA", "NN")), ("sion", ("SS", "AA", "NN")),
    ("tch", ("CH",)), ("dge", ("CH",)), ("ch", ("CH",)),
    ("sh", ("SS",)), ("th", ("TH",)), ("ph", ("FF",)),
    ("ng", ("NN",)), ("qu", ("KK", "U")), ("ck", ("KK",)),
    ("ee", ("I",)), ("ea", ("E",)), ("oo", ("U",)),
    ("ou", ("O",)), ("ow", ("O",)), ("ai", ("E",)),
    ("ay", ("E",)), ("oi", ("O", "I")), ("oy", ("O", "I")),
)

ROMAN_URDU_MULTI = (
    ("kh", ("KK",)), ("gh", ("KK",)), ("ch", ("CH",)),
    ("sh", ("SS",)), ("zh", ("SS",)), ("th", ("TH",)),
    ("dh", ("DD",)), ("ph", ("FF",)), ("bh", ("PP",)),
    ("ng", ("NN",)), ("aa", ("AA",)), ("ee", ("I",)),
    ("ii", ("I",)), ("oo", ("U",)), ("uu", ("U",)),
    ("ai", ("E",)), ("ay", ("E",)), ("au", ("O",)),
)

LATIN_SINGLE = {
    "a": "AA", "e": "E", "i": "I", "o": "O", "u": "U", "y": "I",
    "p": "PP", "b": "PP", "m": "PP", "f": "FF", "v": "FF",
    "t": "DD", "d": "DD", "c": "KK", "k": "KK", "g": "KK", "q": "KK",
    "j": "CH", "s": "SS", "z": "SS", "x": "SS", "n": "NN", "l": "NN",
    "r": "RR", "w": "U",
}

# Urdu letters grouped by broad visible articulation, not linguistic identity.
URDU_SINGLE = {
    "ا": "AA", "آ": "AA", "ع": "AA", "ء": "AA",
    "و": "U", "ؤ": "U", "ی": "I", "ے": "E", "ئ": "I",
    "پ": "PP", "ب": "PP", "م": "PP",
    "ف": "FF",
    "ث": "TH", "ذ": "TH", "ظ": "TH",
    "ت": "DD", "ٹ": "DD", "د": "DD", "ڈ": "DD", "ط": "DD",
    "ک": "KK", "گ": "KK", "ق": "KK", "خ": "KK", "غ": "KK",
    "چ": "CH", "ج": "CH",
    "س": "SS", "ص": "SS", "ز": "SS", "ژ": "SS", "ش": "SS",
    "ن": "NN", "ں": "NN", "ل": "NN",
    "ر": "RR", "ڑ": "RR",
    "ہ": "AA", "ھ": "AA", "ح": "AA",
}

_ROMAN_URDU_HINTS = {
    "aap", "ab", "acha", "achha", "aur", "bohat", "hai", "hain", "ho",
    "hum", "ka", "kahan", "karo", "ke", "ki", "ko", "kya", "lekin",
    "main", "mein", "mera", "nahi", "ne", "se", "tha", "thi", "tum",
    "woh", "yeh",
}


def normalize_language(language: str | None, text: str = "") -> str:
    value = str(language or "").strip().lower().replace("-", "_").replace(" ", "_")
    if value in {"ur", "urdu", "ur_pk", "ur_in"}:
        return "urdu"
    if value in {"roman", "romanurdu", "roman_urdu", "urdu_roman"}:
        return "roman_urdu"
    if value in {"en", "eng", "english", "en_us", "en_gb"}:
        return "english"
    if _URDU_RE.search(text or ""):
        return "urdu"
    tokens = {match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")}
    return "roman_urdu" if len(tokens & _ROMAN_URDU_HINTS) >= 2 else "english"


def iter_tokens(text: str):
    """Yield text tokens with source character offsets."""
    for match in _TOKEN_RE.finditer(text or ""):
        yield {"text": match.group(0), "start": match.start(), "end": match.end()}


def _latin_text(token: str) -> str:
    decomposed = unicodedata.normalize("NFKD", token.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch) and ch.isalnum())


def _scan_latin(token: str, rules) -> list[str]:
    source = _latin_text(token)
    result: list[str] = []
    index = 0
    while index < len(source):
        matched = False
        for grapheme, phonemes in rules:
            if source.startswith(grapheme, index):
                result.extend(phonemes)
                index += len(grapheme)
                matched = True
                break
        if not matched:
            phoneme = LATIN_SINGLE.get(source[index])
            if phoneme:
                result.append(phoneme)
            index += 1
    return result


def token_to_phonemes(token: str, language: str | None = None) -> list[str]:
    """Convert one token to broad visual phoneme groups."""
    if _URDU_RE.search(token or ""):
        phonemes = [URDU_SINGLE[ch] for ch in token if ch in URDU_SINGLE]
    else:
        lang = normalize_language(language, token)
        rules = ROMAN_URDU_MULTI if lang == "roman_urdu" else ENGLISH_MULTI
        phonemes = _scan_latin(token, rules)

    # Repeated adjacent mouth shapes add no information and cause chatter.
    compact: list[str] = []
    for phoneme in phonemes:
        if not compact or compact[-1] != phoneme:
            compact.append(phoneme)
    return compact or (["AA"] if str(token or "").strip() else [])


def phonemes_to_visemes(phonemes) -> list[str]:
    return [PHONEME_TO_VISEME[p] for p in phonemes if p in PHONEME_TO_VISEME]


def token_to_visemes(token: str, language: str | None = None) -> list[str]:
    return phonemes_to_visemes(token_to_phonemes(token, language))
