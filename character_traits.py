"""Evidence-backed movement traits for the registered Quaternius library.

This module never invents an animation. It reads the real clip names recorded in
the capability registry and converts a requested story action to either a real
clip-backed action or a safe idle/listen fallback.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from functools import lru_cache

import config

REGISTRY_PATH = Path(config.BASE_DIR) / "assets" / "characters" / "capability_registry.json"
MANIFEST_PATH = Path(config.BASE_DIR) / "characters3d.json"

_ACTION_CLIPS = {
    "idle": ("Idle", "Flying_Idle"),
    "talk": ("TalkIdle", "Talk", "Idle", "Flying_Idle"),
    "listen": ("Listen", "Idle", "Flying_Idle"),
    "look": ("Listen", "Idle", "Flying_Idle"),
    "walk": ("Walk",),
    "approach": ("Walk", "Run", "Fast_Flying"),
    "run": ("Run", "Fast_Flying"),
    "exit": ("Run", "Fast_Flying"),
    "jump": ("Jump",),
    "wave": ("Wave",),
    "point": ("Point", "Idle_Gun_Pointing"),
    "reach": ("Interact",),
    "pickup": ("Interact",),
    "give": ("Interact",),
    "help": ("Interact",),
    "pull": ("Interact",),
    "hug": ("Interact",),
    "celebrate": ("Celebrate",),
    "dance": ("Dance", "Celebrate"),
    "punch": ("Punch_Right", "Punch_Left"),
    "kick": ("Kick_Right", "Kick_Left"),
    "fall": ("Death", "HitRecieve_2", "HitReact"),
    "sit": ("Sit",),
    "stand": ("Stand",),
    "nod": ("Yes", "Idle"),
    "shake": ("No", "Idle"),
}

# These families cannot safely receive the legacy human bone-pose layer.
_ANIMAL_TOKENS = ("alpaking", "armabee", "birb", "bunny", "cat", "chicken", "cow", "dino", "dog", "dragon", "fish", "frog", "germanshepherd", "monkroose", "pigeon", "pug", "shark", "squidle", "yeti")
_NON_HUMANOID_TOKENS = _ANIMAL_TOKENS + ("blob", "goleling", "ghost", "glub", "hywirl", "mushnub", "squidle")
_COMPACT_TOKENS = ("extrasmall", "small", "birb", "blob", "frog", "chicken", "pigeon", "fish", "squidle")
_LARGE_TOKENS = ("large", "dragon", "yeti", "goleling", "orc", "dino")


def _read(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


@lru_cache(maxsize=2)
def _registry(fingerprint=None):
    del fingerprint
    return _read(REGISTRY_PATH, {}).get("characters", {})


def _registry_data():
    try:
        stat = REGISTRY_PATH.stat(); token = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        token = None
    return _registry(token)


def _entry_for_blend(blend):
    slug = Path(str(blend or "")).stem.lower()
    for entry in _read(MANIFEST_PATH, []):
        if Path(str(entry.get("blend") or "")).stem.lower() == slug:
            return entry
    return {}


def traits_for_entry(entry):
    entry = entry or {}
    cid = str(entry.get("capability_id") or "")
    name = str(entry.get("name") or cid)
    key = f"{cid} {name}".lower()
    capability = _registry_data().get(cid, {})
    clips = capability.get("authoredClips") or {}
    clip_names = tuple(sorted(str(value) for value in clips.keys()))
    aerial = any(name in clips for name in ("Flying_Idle", "Fast_Flying"))
    non_humanoid = aerial or any(token in key for token in _NON_HUMANOID_TOKENS)
    form = "aerial" if aerial else ("creature" if non_humanoid else "humanoid")
    size_class = "compact" if any(token in key for token in _COMPACT_TOKENS) else ("large" if any(token in key for token in _LARGE_TOKENS) else "regular")
    return {
        "schema_version": 1,
        "character_id": cid,
        "name": name,
        "form": form,
        "poseMode": "clip_only" if non_humanoid else "humanoid",
        "groundMode": "hover" if aerial else "grounded",
        "hoverHeight": 0.42 if aerial else 0.0,
        "sizeClass": size_class,
        "authoredClips": list(clip_names),
        "facialReady": False,
        "allowedActions": [action for action in _ACTION_CLIPS if resolve_action({"authoredClips": clip_names}, action)["supported"]],
    }


def traits_for_blend(blend):
    return traits_for_entry(_entry_for_blend(blend))


_SEMANTIC_SUBSTITUTES = {
    "wash": ("Interact",),
    "splash": ("Interact",),
    "slip": ("Roll", "HitRecieve_2", "HitReact"),
}


def resolve_action(traits, requested):
    requested = re.sub(r"[^a-z_]+", "_", str(requested or "idle").lower()).strip("_") or "idle"
    clips = set((traits or {}).get("authoredClips") or ())
    if requested in _SEMANTIC_SUBSTITUTES:
        sub_candidates = _SEMANTIC_SUBSTITUTES[requested]
        actual = next((candidate for candidate in sub_candidates if candidate in clips), "")
        if actual:
            return {"action": requested, "sourceClip": actual, "supported": True, "semantic": True}
    candidates = _ACTION_CLIPS.get(requested, _ACTION_CLIPS["idle"])
    actual = next((candidate for candidate in candidates if candidate in clips), "")
    if actual:
        return {"action": requested, "sourceClip": actual, "supported": True, "semantic": False}
    fallback = next((candidate for candidate in _ACTION_CLIPS["idle"] if candidate in clips), "")
    return {"action": "idle", "sourceClip": fallback, "supported": False, "semantic": False}


def render_directive(blend, requested_action, requested_clip=""):
    traits = traits_for_blend(blend)
    resolved = resolve_action(traits, requested_action)
    # A caller-provided clip is honored only when it is a real clip on this exact asset.
    if requested_clip and requested_clip in set(traits["authoredClips"]):
        resolved["sourceClip"] = requested_clip
    return {"traits": traits, "action": resolved["action"], "sourceClip": resolved["sourceClip"],
            "actionSupported": resolved["supported"], "semantic": resolved.get("semantic", False)}


def quaternius_trait_report():
    entries = [entry for entry in _read(MANIFEST_PATH, [])
               if str(entry.get("capability_id") or "").startswith("quaternius_")]
    characters = [traits_for_entry(entry) for entry in entries]
    return {"schema_version": 1, "summary": {"registered": len(characters),
            "humanoid": sum(item["form"] == "humanoid" for item in characters),
            "creature": sum(item["form"] == "creature" for item in characters),
            "aerial": sum(item["form"] == "aerial" for item in characters)},
            "characters": characters}