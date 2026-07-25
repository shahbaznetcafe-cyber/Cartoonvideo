"""Duration presets and deterministic scene planning for pasted scripts.

The rendered duration is ultimately driven by synthesized speech.  These
helpers keep AI writing targets, UI estimates, and manual-script scene counts
aligned without stretching audio or duplicating dialogue.
"""
from __future__ import annotations

import copy
import math
import re
from collections import OrderedDict


DURATION_PRESETS = OrderedDict([
    ("30sec", {"label": "30 sec", "seconds": 30, "lines": 6, "scenes": 1}),
    ("1min", {"label": "1 min", "seconds": 60, "lines": 12, "scenes": 2}),
    ("2min", {"label": "2 min", "seconds": 120, "lines": 24, "scenes": 3}),
    ("3min", {"label": "3 min", "seconds": 180, "lines": 36, "scenes": 4}),
    ("5min", {"label": "5 min", "seconds": 300, "lines": 60, "scenes": 6}),
    ("8min", {"label": "8 min", "seconds": 480, "lines": 96, "scenes": 8}),
    ("10min", {"label": "10 min", "seconds": 600, "lines": 120, "scenes": 10}),
    ("15min", {"label": "15 min", "seconds": 900, "lines": 180, "scenes": 15}),
])

_ALIASES = {
    "short": "30sec", "medium": "1min", "long": "2min",
    "30s": "30sec", "30sec": "30sec", "30seconds": "30sec",
    "1m": "1min", "2m": "2min", "3m": "3min", "5m": "5min",
    "8m": "8min", "10m": "10min", "15m": "15min",
}

_SCENE_HEADER_RE = re.compile(r"^\s*\[\s*scene\s*:", re.IGNORECASE | re.MULTILINE)

# Spoken words per second, MEASURED from this project's own rendered timelines
# (words in timeline.json vs the synthesized line durations, which include the
# configured inter-line pauses).  A single global 2.05 under-counted Urdu and
# Roman Urdu by roughly 17%, so every video came out short and then got padded.
# Re-measure with tools/measure_speech_rate.py after changing voices or pauses.
WORDS_PER_SECOND = {
    "hinglish": 2.07,
    "roman_hindi": 2.07,
    "hindi": 2.07,
    "roman_urdu": 2.39,
    "urdu": 2.42,
    "english": 2.30,
}
DEFAULT_WORDS_PER_SECOND = 2.20


def words_per_second(language=None):
    """Measured speaking rate for a language (falls back to the global mean)."""
    return WORDS_PER_SECOND.get(
        str(language or "").strip().lower(), DEFAULT_WORDS_PER_SECOND)

_LOCATION_RULES = (
    ("forest path", ("forest", "jungle", "jangal", "park", "garden", "bagh", "jنگل", "جنگل", "जंगल", "बगीचा")),
    ("market", ("market", "bazaar", "bazar", "shop", "dukan", "stall", "بازار", "दुकान", "बाज़ार")),
    ("kitchen", ("kitchen", "rasoi", "cooking", "چولہا", "باورچی", "रसोई")),
    ("school", ("school", "classroom", "teacher", "ustad", "विद्यालय", "स्कूल", "استاد")),
    ("home", ("home", "house", "ghar", "room", "कमरा", "घर", "گھر", "کمرہ")),
    ("village", ("village", "gaon", "gaun", "गाँव", "गांव", "گاؤں")),
    ("farm field", ("farm", "field", "khet", "खेत", "کھیت")),
    ("road", ("road", "street", "rasta", "sarak", "रास्ता", "सड़क", "راستہ", "سڑک")),
    ("stage", ("stage", "party", "festival", "celebration", "मंच", "تقریب")),
)


def normalize_duration(value, default="1min"):
    key = str(value or "").strip().lower().replace(" ", "")
    key = _ALIASES.get(key, key)
    return key if key in DURATION_PRESETS else default


def preset(value):
    return dict(DURATION_PRESETS[normalize_duration(value)])


def target_lines(value):
    return int(preset(value)["lines"])


def writing_brief(value, language=None):
    """Return an honest spoken-word budget for AI writers.

    Line count alone is not a duration contract: short dialogue lines can make a
    two-minute script render as one minute.  The budget uses the MEASURED
    speaking rate for the language (see WORDS_PER_SECOND) so the script is long
    enough before any voices are generated.
    """
    info = preset(value)
    target = int(info["seconds"])
    words = max(36, round(target * words_per_second(language)))
    minimum = max(30, round(words * 0.92))
    maximum = round(words * 1.08)
    return {
        "target_seconds": target,
        "target_label": info["label"],
        "target_words": words,
        "minimum_words": minimum,
        "maximum_words": maximum,
        "average_words_per_line": round(words / max(1, int(info["lines"])), 1),
    }


def use_longform(value):
    return int(preset(value)["seconds"]) >= 180


def closest_preset(seconds):
    seconds = max(1, float(seconds or 0))
    return min(DURATION_PRESETS, key=lambda key: abs(DURATION_PRESETS[key]["seconds"] - seconds))


_AUTO_ALIASES = {"auto", "automatic", "auto-detect", "autodetect"}


def is_auto(value):
    return str(value or "").strip().lower().replace(" ", "") in _AUTO_ALIASES


def resolve_duration(value, script_text="", parsed=None):
    """Resolve a duration selection to a concrete preset key.

    "auto" estimates the script's own natural spoken length (from script_text
    or an already-parsed story) and returns the closest preset, instead of
    forcing a fixed choice that may not match what was actually written.
    Any other value normalizes exactly as before.  Returns (preset_key, was_auto).
    """
    if is_auto(value):
        estimated, _, _ = estimate_text_seconds(script_text, parsed)
        return closest_preset(estimated), True
    return normalize_duration(value), False


def estimate_text_seconds(script_text, parsed=None):
    """Estimate natural speech time without pretending it is the final TTS duration."""
    if parsed:
        dialogue = [str(line.get("text") or "")
                    for scene in parsed.get("scenes", [])
                    for line in scene.get("lines", [])]
    else:
        dialogue = [line.split(":", 1)[-1] for line in str(script_text or "").splitlines()
                    if line.strip() and not line.lstrip().lower().startswith("[scene")]
    text = " ".join(dialogue) if dialogue else str(script_text or "")
    words = len(re.findall(r"\S+", text))
    line_count = max(1, len(dialogue))
    punctuation_pauses = len(re.findall(r"[.!?…،؛]+", text))
    seconds = words / 2.2 + line_count * 0.35 + punctuation_pauses * 0.12
    return max(3, round(seconds, 1)), words, len(dialogue)


def duration_analysis(script_text, parsed=None, selected="1min"):
    estimated, words, lines = estimate_text_seconds(script_text, parsed)
    selected_key = normalize_duration(selected)
    selected_info = DURATION_PRESETS[selected_key]
    nearest = closest_preset(estimated)
    difference = round(estimated - selected_info["seconds"], 1)
    tolerance = max(8, selected_info["seconds"] * 0.18)
    writing = writing_brief(selected_key)
    return {
        "estimated_seconds": estimated,
        "word_count": words,
        "recommended_words": writing["target_words"],
        "minimum_words": writing["minimum_words"],
        "maximum_words": writing["maximum_words"],
        "average_words_per_line": writing["average_words_per_line"],
        "dialogue_lines": lines,
        "closest_preset": nearest,
        "closest_label": DURATION_PRESETS[nearest]["label"],
        "selected_preset": selected_key,
        "selected_label": selected_info["label"],
        "target_seconds": selected_info["seconds"],
        "difference_seconds": difference,
        "within_target_tolerance": abs(difference) <= tolerance,
    }


def _infer_location(lines, index):
    text = " ".join(str(line.get("text") or "") for line in lines).casefold()
    for location, markers in _LOCATION_RULES:
        if any(marker.casefold() in text for marker in markers):
            return location
    return f"story location {index}"


def _scene_target_count(parsed, script_text, selected):
    """Choose a meaningful scene count from both the selected duration and content.

    A duration setting must influence the storyboard, but we never fabricate empty
    scenes: every automatic scene needs at least three dialogue lines.
    """
    lines = [line for scene in (parsed.get("scenes") or [])
             for line in (scene.get("lines") or [])]
    if len(lines) < 3:
        return 1
    estimated, _, _ = estimate_text_seconds(script_text, parsed)
    natural_scenes = max(1, int(math.ceil(estimated / 40.0)))
    requested_scenes = int(preset(selected).get("scenes", 1))
    max_meaningful_scenes = max(1, len(lines) // 3)
    return min(15, max_meaningful_scenes, max(natural_scenes, requested_scenes))


def _split_scene(scene, count, first_id):
    """Split one authored scene into sequential story beats without losing context."""
    lines = list(scene.get("lines") or [])
    base, extra = divmod(len(lines), count)
    chunks, cursor = [], 0
    for offset in range(count):
        size = base + (1 if offset < extra else 0)
        chunk = lines[cursor:cursor + size]
        cursor += size
        index = first_id + offset
        location = scene.get("location") or _infer_location(chunk, index)
        beat_label = "" if count == 1 else f" · beat {offset + 1}"
        chunks.append({
            "id": index,
            "location": f"{location}{beat_label}",
            "time": scene.get("time", "day"),
            "mood": scene.get("mood", "neutral"),
            "transition": "hard_cut",
            "transition_duration": 0.0,
            "background_prompt": f"{location}, story beat {offset + 1}: " +
                                 " ".join(str(line.get("text") or "") for line in chunk[:2])[:180],
            "lines": chunk,
        })
    return chunks


def auto_segment_scenes(parsed, script_text="", selected="1min"):
    """Build an editable, duration-aware storyboard from pasted dialogue.

    Existing scene headers remain the parent context.  When their number is too
    small for the requested duration, only oversized parent scenes are divided
    into sequential beats; no dialogue is invented or duplicated.
    """
    result = copy.deepcopy(parsed or {})
    scenes = [scene for scene in (result.get("scenes") or []) if scene.get("lines")]
    if not scenes:
        return result, False
    desired = _scene_target_count(result, script_text, selected)
    if desired <= len(scenes):
        return result, False

    allocations = [1] * len(scenes)
    # Give extra beats to the scene with the most unsplit dialogue first.
    while sum(allocations) < desired:
        candidates = [index for index, scene in enumerate(scenes)
                      if len(scene.get("lines") or []) >= (allocations[index] + 1) * 3]
        if not candidates:
            break
        chosen = max(candidates,
                     key=lambda index: len(scenes[index].get("lines") or []) / allocations[index])
        allocations[chosen] += 1

    if sum(allocations) <= len(scenes):
        return result, False
    planned, next_id = [], 1
    for scene, count in zip(scenes, allocations):
        beats = _split_scene(scene, count, next_id)
        planned.extend(beats)
        next_id += len(beats)
    result["scenes"] = planned
    return result, True
