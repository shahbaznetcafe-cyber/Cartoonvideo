"""Editorial transition planning and FFmpeg filter-graph helpers.

The planner is deliberately conservative: dialogue stays on clean cuts unless the
story contains a clear temporal, action, or camera cue. Decorative transitions are
therefore limited to motivated scene boundaries.
"""
from __future__ import annotations

from typing import Iterable, Sequence


MIN_DURATION = 0.15
MAX_DURATION = 0.50

_ALIASES = {
    "cut": "hard_cut", "clean_cut": "hard_cut", "hardcut": "hard_cut",
    "hard_cut": "hard_cut", "dissolve": "short_dissolve",
    "crossfade": "short_dissolve", "short_dissolve": "short_dissolve",
    "whip": "whip_pan", "whip_pan": "whip_pan", "match": "match_cut",
    "match_cut": "match_cut", "fade": "fade", "fade_black": "fade",
    "camera": "camera_motivated", "camera_motivated": "camera_motivated",
    "wipe": "camera_motivated",
}

_DEFAULT_DURATIONS = {
    "hard_cut": 0.0, "match_cut": 0.0, "short_dissolve": 0.30,
    "whip_pan": 0.20, "fade": 0.45, "camera_motivated": 0.25,
}

_XFADE = {
    "short_dissolve": "fade", "whip_pan": "slideleft",
    "fade": "fadeblack", "camera_motivated": "wipeleft",
}


def normalize_type(value) -> str | None:
    if value is None:
        return None
    key = str(value).strip().lower().replace("-", " ").replace(" ", "_")
    return _ALIASES.get(key)


def decision(kind: str, duration=None, reason: str = "editorial") -> dict:
    """Return a normalized, JSON-safe transition decision."""
    kind = normalize_type(kind) or "hard_cut"
    if kind in ("hard_cut", "match_cut"):
        seconds = 0.0
    else:
        try:
            seconds = float(duration)
        except (TypeError, ValueError):
            seconds = _DEFAULT_DURATIONS[kind]
        seconds = max(MIN_DURATION, min(MAX_DURATION, seconds))
    return {
        "type": kind,
        "duration": round(seconds, 3),
        "ffmpeg": _XFADE.get(kind),
        "reason": reason,
    }


def _cue_text(*entries: dict) -> str:
    fields = ("action", "camera", "shot_motion", "transition")
    return " ".join(
        str(entry.get(field) or "")
        for entry in entries
        for field in fields
    ).lower()


def _explicit_transition(entry: dict):
    value = entry.get("transition")
    if isinstance(value, dict):
        return normalize_type(value.get("type")), value.get("duration")
    return normalize_type(value), entry.get("transition_duration")


def choose_transition(previous: dict, current: dict, default_duration=0.30) -> dict:
    """Choose the boundary transition before ``current``."""
    explicit, explicit_duration = _explicit_transition(current)
    if explicit:
        return decision(explicit, explicit_duration, "explicit story direction")

    if previous.get("scene") == current.get("scene"):
        return decision("hard_cut", reason="dialogue continuity")

    cues = _cue_text(previous, current)
    if "match cut" in cues or "match_cut" in cues:
        return decision("match_cut", reason="match-cut cue")
    if any(word in cues for word in ("whip", "swish", "fast pan", "snap pan")):
        return decision("whip_pan", reason="rapid camera/action cue")
    if any(word in cues for word in ("fade to", "fade out", "fade in", "fade black")):
        return decision("fade", reason="fade cue")
    if any(word in cues for word in ("dissolve", "memory", "dream", "flashback")):
        return decision("short_dissolve", default_duration, "soft/time-shift cue")
    if any(word in cues for word in
           ("camera pan", "camera follows", "tracking shot", "tilt up", "tilt down")):
        return decision("camera_motivated", reason="camera movement cue")

    previous_time = str(previous.get("time") or "").lower()
    current_time = str(current.get("time") or "").lower()
    if previous_time and current_time and previous_time != current_time:
        return decision("fade", reason="clear time change")

    action_words = ("runs", "run ", "chase", "rushes", "spins", "swings", "jumps past")
    if any(word in cues for word in action_words):
        return decision("whip_pan", reason="fast action carries the cut")

    speakers = {str(previous.get("speaker") or ""), str(current.get("speaker") or "")}
    moods = {str(previous.get("mood") or "").lower(),
             str(current.get("mood") or "").lower()}
    if "narrator" in speakers and moods.intersection({"emotional", "drama", "calm"}):
        return decision("short_dissolve", default_duration,
                        "narrated emotional scene change")

    return decision("hard_cut", reason="clean dialogue/scene cut")


def plan_transitions(timeline: Sequence[dict], default_duration=0.30) -> list[dict]:
    """Return one decision for each boundary in ``timeline``."""
    return [choose_transition(timeline[i - 1], timeline[i], default_duration)
            for i in range(1, len(timeline))]


def overlap(item: dict) -> float:
    try:
        value = float(item.get("duration") or 0.0)
    except (TypeError, ValueError, AttributeError):
        return 0.0
    return value if item.get("type") not in ("hard_cut", "match_cut") else 0.0


def timeline_starts(durations: Sequence[float], plan: Sequence[dict], offset=0.0) -> list[float]:
    if len(plan) != max(0, len(durations) - 1):
        raise ValueError("transition plan must contain one item per clip boundary")
    if not durations:
        return []
    starts = [float(offset)]
    for i in range(1, len(durations)):
        starts.append(starts[-1] + float(durations[i - 1]) - overlap(plan[i - 1]))
    return starts


def build_av_filter_graph(durations: Sequence[float], plan: Sequence[dict]):
    """Build a mixed concat/xfade graph for numbered FFmpeg A/V inputs."""
    if not durations:
        raise ValueError("at least one clip is required")
    if len(plan) != len(durations) - 1:
        raise ValueError("transition plan must contain one item per clip boundary")

    filters = []
    for i, raw_duration in enumerate(durations):
        # MP4/AAC line clips commonly have audio a few milliseconds longer than
        # their last video frame.  Xfade offsets are calculated from container
        # durations, so normalize both streams first; otherwise a late xfade can
        # start after the video stream has ended and silently discard every shot
        # after that boundary.
        duration = max(0.05, float(raw_duration))
        filters.append(
            f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,"
            f"tpad=stop_mode=clone:stop_duration=1,"
            f"trim=duration={duration:.6f},setpts=PTS-STARTPTS[vin{i}]"
        )
        filters.append(
            f"[{i}:a]asetpts=PTS-STARTPTS,apad=pad_dur=1,"
            f"atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[ain{i}]"
        )

    video_label, audio_label = "vin0", "ain0"
    current_duration = float(durations[0])
    for i, item in enumerate(plan, start=1):
        seconds = min(overlap(item), max(0.0, float(durations[i]) - 0.05),
                      max(0.0, current_duration - 0.05))
        next_video, next_audio = f"vstep{i}", f"astep{i}"
        if seconds > 0.0 and item.get("ffmpeg"):
            offset = max(0.0, current_duration - seconds)
            filters.append(
                f"[{video_label}][vin{i}]xfade=transition={item['ffmpeg']}:"
                f"duration={seconds:.3f}:offset={offset:.3f}[{next_video}]"
            )
            filters.append(
                f"[{audio_label}][ain{i}]acrossfade=d={seconds:.3f}[{next_audio}]"
            )
            current_duration += float(durations[i]) - seconds
        else:
            filters.append(f"[{video_label}][vin{i}]concat=n=2:v=1:a=0[{next_video}]")
            filters.append(f"[{audio_label}][ain{i}]concat=n=2:v=0:a=1[{next_audio}]")
            current_duration += float(durations[i])
        video_label, audio_label = next_video, next_audio

    return filters, video_label, audio_label, current_duration


def summarize(plan: Iterable[dict]) -> dict:
    counts = {}
    for item in plan:
        kind = item.get("type", "hard_cut")
        counts[kind] = counts.get(kind, 0) + 1
    return counts
