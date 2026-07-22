"""Deterministic scene-level acting continuity for the Three.js renderer.

Each dialogue line is rendered as an independent clip.  This module gives those
clips explicit start/end states so position and resting pose survive the cut.
The generated plan contains no model-specific data and is safe to regenerate on
resume.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os


SCHEMA_VERSION = 2
STATE_FILENAME = "scene_animation_state.json"

_EMOTION_ALIASES = {
    "excited": "happy", "joy": "happy", "cheerful": "happy",
    "scared": "fear", "afraid": "fear", "worried": "fear",
    "shocked": "surprise", "surprised": "surprise", "amazed": "surprise",
    "mad": "angry", "upset": "sad", "crying": "sad",
}

_REST_POSES = {
    "neutral":  (8.0, -8.0, 0.0, 1.0),
    "happy":    (38.0, -38.0, -4.0, 1.0),
    "sad":      (-2.0, 2.0, 13.0, 0.97),
    "angry":    (35.0, -35.0, 11.0, 1.0),
    "surprise": (54.0, -54.0, -13.0, 1.03),
    "fear":     (11.0, -11.0, 15.0, 0.95),
}

_LOCOMOTION = {"walk": 0.9, "come": 0.8, "go": 0.8,
               "approach": 0.58, "run": 1.45, "exit": 2.4,
               "retreat": -0.8}
_ASSIST = {"help", "rescue", "pull", "save", "guide", "lift"}


def _stable_seed(scene_id, character_id):
    raw = f"{scene_id!s}\0{character_id!s}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big") & 0x7FFFFFFF


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _pose(emotion="neutral", body_y=0.0):
    key = _EMOTION_ALIASES.get(str(emotion or "neutral").lower(),
                               str(emotion or "neutral").lower())
    arm_l, arm_r, body_x, scale_y = _REST_POSES.get(key, _REST_POSES["neutral"])
    return {
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "pose": {
            "armL": arm_l, "armR": arm_r,
            "legL": 0.0, "legR": 0.0,
            "bodyX": body_x, "bodyY": float(body_y), "bodyZ": 0.0,
        },
        "scaleY": scale_y,
    }


def _reaction_for(entry, action):
    emotion = _EMOTION_ALIASES.get(str(entry.get("emotion") or "neutral").lower(),
                                   str(entry.get("emotion") or "neutral").lower())
    text = str(entry.get("text") or "")
    if emotion == "surprise" or "?" in text or "؟" in text:
        return "surprise"
    if emotion in {"sad", "fear", "angry"} or action in _ASSIST:
        return "concern"
    if emotion == "happy" or action in {"celebrate", "cheer", "win", "jump"}:
        return "encourage"
    return "attend"


def _copy_state(state):
    return copy.deepcopy(state)


def _target_direction(slot, target_slot, cast_size):
    if isinstance(target_slot, int) and 0 <= target_slot < cast_size and target_slot != slot:
        return 1.0 if target_slot > slot else -1.0
    midpoint = (cast_size - 1) / 2.0
    return 1.0 if slot <= midpoint else -1.0


def build_plan(timeline, line_contexts, fps=24):
    """Build a deterministic state plan from prepared cast/action contexts."""
    if len(timeline) != len(line_contexts):
        raise ValueError("timeline and line_contexts must have equal length")

    scene_states = {}
    lines = []
    time_offset = 0.0

    for index, (entry, context) in enumerate(zip(timeline, line_contexts), 1):
        scene_id = entry.get("scene")
        scene_key = str(scene_id)
        cast = list(context.get("cast") or [entry.get("speaker")])
        cast = [cid for cid in cast if cid]
        speaker = entry.get("speaker")
        action = str(context.get("action") or "none").lower()
        target_slot = context.get("target", -1)
        duration = max(1.0 / max(1, int(fps or 24)), float(entry.get("duration") or 0.0))
        current = scene_states.setdefault(scene_key, {})
        reaction = _reaction_for(entry, action)
        char_states = {}

        for slot, cid in enumerate(cast):
            start = _copy_state(current.get(cid) or _pose())
            if cid == speaker:
                end = _pose(entry.get("emotion", "neutral"))
                role = "speaker"
                char_reaction = "none"
            else:
                speaker_slot = cast.index(speaker) if speaker in cast else slot
                direction = 1.0 if speaker_slot > slot else -1.0 if speaker_slot < slot else 0.0
                end = _pose("neutral", body_y=direction * 7.0)
                role = "listener"
                char_reaction = reaction
            end["position"] = _copy_state(start["position"])
            seed = _stable_seed(scene_id, cid)
            strength = round(0.36 + ((seed % 1000) / 1000.0) * 0.18, 6)
            char_states[cid] = {
                "slot": slot,
                "seed": seed,
                "role": role,
                "reaction": char_reaction,
                "reactionStrength": strength if role == "listener" else 0.0,
                "start": start,
                "end": end,
            }

        if speaker in char_states:
            speaker_slot = cast.index(speaker)
            direction = _target_direction(speaker_slot, target_slot, len(cast))
            if action == "exit":
                # Exit must cross toward the nearest frame edge, not toward the
                # dialogue partner.  The shot director only partially follows.
                direction = -1.0 if speaker_slot <= (len(cast) - 1) / 2.0 else 1.0
            if action in _LOCOMOTION:
                end_x = char_states[speaker]["end"]["position"]["x"] + direction * _LOCOMOTION[action]
                char_states[speaker]["end"]["position"]["x"] = round(_clamp(end_x, -2.8, 2.8), 6)
            elif action == "slip":
                end_x = char_states[speaker]["end"]["position"]["x"] + direction * 0.12
                char_states[speaker]["end"]["position"]["x"] = round(_clamp(end_x, -2.8, 2.8), 6)
            elif action in _ASSIST and isinstance(target_slot, int) and 0 <= target_slot < len(cast):
                target_id = cast[target_slot]
                if target_id in char_states and target_id != speaker:
                    speaker_x = char_states[speaker]["end"]["position"]["x"] + direction * 0.18
                    target_x = char_states[target_id]["end"]["position"]["x"] - direction * 0.14
                    char_states[speaker]["end"]["position"]["x"] = round(_clamp(speaker_x, -2.8, 2.8), 6)
                    char_states[target_id]["end"]["position"]["x"] = round(_clamp(target_x, -2.8, 2.8), 6)

        for cid, data in char_states.items():
            current[cid] = _copy_state(data["end"])

        lines.append({
            "line": index,
            "scene": scene_id,
            "duration": round(duration, 6),
            "timeOffset": round(time_offset, 6),
            "speaker": speaker,
            "action": action,
            "target": target_slot,
            "characters": char_states,
        })
        time_offset += duration

    return {
        "schema_version": SCHEMA_VERSION,
        "generator": "sbz-acting-state",
        "fps": int(fps or 24),
        "lines": lines,
    }


def write_plan(project_dir, plan):
    """Atomically save reproducible scene animation state JSON."""
    path = os.path.join(project_dir, STATE_FILENAME)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp_path, path)
    return path


def line_character_state(plan, line_index, character_id):
    """Return one character's state payload, or an empty mapping for fallbacks."""
    try:
        return plan["lines"][line_index]["characters"].get(character_id, {})
    except (IndexError, KeyError, TypeError):
        return {}
