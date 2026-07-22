"""Capability-aware writing and performance policy for integrated characters.

The renderer can only animate controls that genuinely exist in a character asset.
This module gives script generation, preview and rendering one shared policy so a
body-only humanoid is not written or framed like a facial performer.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

import config


REGISTRY_PATH = Path(config.BASE_DIR) / "assets" / "characters" / "capability_registry.json"

TIER_POLICIES = {
    "FULL_FACIAL": {
        "speech_mode": "viseme_facial", "lip_sync": "viseme",
        "facial_ready": True, "blink": True, "gaze": True,
        "direct_dialogue": True, "max_spoken_words": 18,
        "camera": "dialogue_close_up", "label": "Full facial + viseme lip-sync",
    },
    "VISEME_FACE": {
        "speech_mode": "viseme", "lip_sync": "viseme",
        "facial_ready": False, "blink": False, "gaze": False,
        "direct_dialogue": True, "max_spoken_words": 14,
        "camera": "medium_close", "label": "Viseme lip-sync",
    },
    "LEGACY_JAW": {
        "speech_mode": "jaw_openness", "lip_sync": "jaw_openness",
        "facial_ready": False, "blink": False, "gaze": False,
        "direct_dialogue": True, "max_spoken_words": 12,
        "camera": "medium", "label": "Jaw lip-sync",
    },
    "SKELETAL_INTERACTIVE": {
        "speech_mode": "body_only", "lip_sync": "none",
        "facial_ready": False, "blink": False, "gaze": False,
        "direct_dialogue": False, "max_spoken_words": 4,
        "camera": "body_reaction_medium_close", "label": "Body acting only",
    },
    "SKELETAL_BASIC": {
        "speech_mode": "body_only", "lip_sync": "none",
        "facial_ready": False, "blink": False, "gaze": False,
        "direct_dialogue": False, "max_spoken_words": 4,
        "camera": "medium", "label": "Body acting only",
    },
    "STATIC": {
        "speech_mode": "static", "lip_sync": "none",
        "facial_ready": False, "blink": False, "gaze": False,
        "direct_dialogue": False, "max_spoken_words": 0,
        "camera": "wide", "label": "Static visual character",
    },
}

_AUTHORED_ACTION_CLIPS = {
    "talk": ("TalkIdle",), "listen": ("Listen",), "look": ("Listen",),
    "walk": ("Walk",), "run": ("Run",), "exit": ("Run",),
    "wave": ("Wave",), "point": ("Point", "Idle_Gun_Pointing"),
    "reach": ("Interact",), "pickup": ("Interact",), "give": ("Interact",),
    "help": ("Interact",), "pull": ("Interact",), "hug": ("Interact",),
    "celebrate": ("Celebrate",), "jump": ("Celebrate",), "dance": ("Celebrate",),
    "kick": ("Kick_Right", "Kick_Left"), "punch": ("Punch_Right", "Punch_Left"),
    "slip": ("Roll", "HitRecieve_2"), "fall": ("Death", "HitRecieve_2"),
}


def _tier(value):
    name = str(value or "").upper()
    if name in TIER_POLICIES:
        return name
    if name in {"FACIAL_READY", "FULL_FACE"}:
        return "FULL_FACIAL"
    return "SKELETAL_BASIC"


def policy_for_tier(tier, *, character_id="", name="", library="sbz"):
    resolved = _tier(tier)
    result = dict(TIER_POLICIES[resolved])
    result.update({
        "tier": resolved,
        "character_id": str(character_id or ""),
        "name": str(name or character_id or "Character"),
        "library": str(library or "sbz"),
    })
    if result["speech_mode"] == "body_only":
        result["warning"] = (
            "No jaw, viseme, blink or expression controls: use action-led staging and avoid dialogue close-ups."
        )
    elif result["speech_mode"] == "jaw_openness":
        result["warning"] = (
            "Audio-driven jaw movement is available; blinking and detailed facial expressions are not."
        )
    elif result["speech_mode"] == "viseme":
        result["warning"] = "Viseme lip-sync is available; full emotion/blink controls are incomplete."
    else:
        result["warning"] = "" if result["facial_ready"] else "This character is not a dialogue performer."
    return result


@lru_cache(maxsize=2)
def _registry_document(fingerprint=None):
    del fingerprint
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"characters": {}}


def _registry():
    try:
        stat = REGISTRY_PATH.stat()
        fingerprint = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        fingerprint = None
    return _registry_document(fingerprint).get("characters", {})


def profile_for_entry(entry, use_cache=True):
    """Return one truthful renderer/writer profile for a manifest entry."""
    entry = entry or {}
    capability_id = str(entry.get("capability_id") or "")
    name = str(entry.get("name") or capability_id or "Character")
    if capability_id:
        capability = _registry().get(capability_id, {})
        tier = capability.get("tier") or entry.get("animation_tier") or "SKELETAL_BASIC"
        profile = policy_for_tier(tier, character_id=capability_id, name=name, library="quaternius")
        facial = capability.get("facial") or {}
        # Registry evidence may only reduce a claim, never upgrade it.
        profile["facial_ready"] = bool(profile["facial_ready"] and facial.get("ready"))
        profile["blink"] = bool(profile["blink"] and facial.get("blink"))
        profile["gaze"] = bool(profile["gaze"] and facial.get("gaze"))
        return profile

    import char3d_lib
    report = char3d_lib.validate_entry(entry, use_cache=use_cache)
    return policy_for_tier(report.get("tier"), name=name, library="sbz")


def profile_for_blend(blend, use_cache=True):
    import char3d_lib
    entry = char3d_lib.entry_for_blend(blend)
    if not entry:
        return policy_for_tier("SKELETAL_BASIC", name=Path(str(blend or "Character")).stem)
    return profile_for_entry(entry, use_cache=use_cache)


def profiles_for_names(names):
    """Resolve UI/template character names, IDs or package slugs."""
    import char3d_lib
    entries = char3d_lib.load()
    lookup = {}
    for entry in entries:
        package = Path(str(entry.get("blend") or "")).stem
        values = (entry.get("name"), entry.get("capability_id"), package)
        for value in values:
            if value:
                lookup[re.sub(r"[^a-z0-9]+", "", str(value).lower())] = entry
    result = []
    for value in names or []:
        key = re.sub(r"[^a-z0-9]+", "", str(value).lower())
        entry = lookup.get(key)
        if entry:
            result.append(profile_for_entry(entry))
    return result


def authored_action_names(profile):
    """Return semantic action names backed by real registered clips."""
    capability = _registry().get(str((profile or {}).get("character_id") or ""), {})
    clips = capability.get("authoredClips") or {}
    available = []
    for action, candidates in _AUTHORED_ACTION_CLIPS.items():
        if any(candidate in clips for candidate in candidates):
            available.append(action)
    return available


def script_guidance(character_names):
    """Compact cast-specific rules used by every script generation path."""
    profiles = profiles_for_names(character_names)
    if not profiles:
        return ""
    lines = [
        "CAST PERFORMANCE POLICY (follow this exactly; do not invent missing face controls):"
    ]
    for profile in profiles:
        if profile["speech_mode"] == "body_only":
            rule = (
                f"{profile['name']}: BODY-ONLY. Tell their story through visible actions and reactions. "
                f"If they must speak, use at most {profile['max_spoken_words']} words and never depend on visible lips."
            )
        elif profile["speech_mode"] == "static":
            rule = f"{profile['name']}: STATIC. Do not give spoken dialogue; use as a visual/background role."
        elif profile["speech_mode"] == "jaw_openness":
            rule = (
                f"{profile['name']}: JAW LIP-SYNC. Spoken lines may use at most "
                f"{profile['max_spoken_words']} words, with natural punctuation; stage in medium shots."
            )
        elif profile["speech_mode"] == "viseme":
            rule = (
                f"{profile['name']}: VISEME LIP-SYNC. Natural dialogue is allowed, but use body acting "
                "for emotion because blink/expression controls are incomplete."
            )
        else:
            rule = f"{profile['name']}: FULL FACIAL. Natural dialogue, emotions and motivated close-ups are allowed."
        lines.append("- " + rule)
        actions_for_character = authored_action_names(profile)
        if actions_for_character:
            lines.append(
                f"  Real authored body directions for {profile['name']}: "
                + ", ".join(actions_for_character)
                + ". Prefer these exact directions; do not invent a named animation clip."
            )
        # Quaternius has mixed humanoid, animal and aerial rigs. The clip
        # inventory is authoritative; never write hand interactions for flyers.
        try:
            import character_traits
            traits = character_traits.traits_for_entry({
                "capability_id": profile.get("character_id"), "name": profile.get("name")})
            if traits.get("character_id"):
                valid = ", ".join(traits.get("allowedActions") or ["idle"])
                if traits.get("form") == "aerial":
                    lines.append(
                        f"  {profile['name']}: AERIAL creature. Keep it airborne; never write hand/foot contact, "
                        f"pickup, point, pull, hug or grounded walk. Valid directions: {valid}."
                    )
                elif traits.get("form") == "creature":
                    lines.append(
                        f"  {profile['name']}: CREATURE body. Never assume human hands or a human facial performance. "
                        f"Valid directions: {valid}."
                    )
        except Exception:
            pass
    lines.extend([
        "- Prefer visual cause-and-effect over characters explaining what viewers can see.",
        "- Every spoken line must include natural punctuation for TTS rhythm and mouth closure at silence.",
        "- Do not write subtle eyebrow, eye or mouth acting for a character whose policy does not support it.",
    ])
    return "\n".join(lines)


def registry_performance_summary():
    """Provider-neutral compact prompt snapshot for the structured script engine."""
    characters = {}
    for character_id, capability in _registry().items():
        policy = policy_for_tier(capability.get("tier"), character_id=character_id,
                                 name=capability.get("displayName") or character_id,
                                 library="quaternius")
        characters[character_id] = {
            key: policy[key] for key in (
                "tier", "speech_mode", "lip_sync", "facial_ready",
                "direct_dialogue", "max_spoken_words", "camera"
            )
        }
    tier_policies = {
        name: {key: value for key, value in policy.items()
               if key in {"speech_mode", "lip_sync", "facial_ready", "direct_dialogue",
                          "max_spoken_words", "camera"}}
        for name, policy in TIER_POLICIES.items()
    }
    return {"tierPolicies": tier_policies, "characters": characters}


def dialogue_cast_recommendations(limit=3):
    """Return real installed dialogue-capable choices without changing a user's cast.

    This is deliberately a recommendation, not an automatic substitution.  A
    Quaternius body performer can still be the right choice for an action scene;
    the editor must make the facial limitation visible instead of replacing it
    behind the user's back.
    """
    import char3d_lib

    tier_rank = {"FULL_FACIAL": 0, "VISEME_FACE": 1, "LEGACY_JAW": 2}
    choices = []
    for entry in char3d_lib.load():
        profile = profile_for_entry(entry)
        if not profile.get("direct_dialogue") or profile.get("lip_sync") == "none":
            continue
        package = Path(str(entry.get("blend") or "")).stem
        choices.append({
            "name": profile["name"],
            "package": package,
            "tier": profile["tier"],
            "lip_sync": profile["lip_sync"],
            "camera": profile["camera"],
            "limitation": profile["warning"],
        })
    choices.sort(key=lambda choice: (tier_rank.get(choice["tier"], 99), choice["name"].lower()))
    return choices[:max(0, int(limit))]


def dialogue_route(profile, text):
    """Describe the safe presentation route for one line, using asset evidence."""
    profile = profile or policy_for_tier("SKELETAL_BASIC")
    words = len(re.findall(r"\S+", str(text or "")))
    maximum = int(profile.get("max_spoken_words") or 0)
    if profile.get("speech_mode") in {"body_only", "static"} and words > maximum:
        return {
            "status": "action_led_body_only",
            "words": words,
            "maxWords": maximum,
            "lipSync": "none",
            "camera": profile.get("camera") or "medium",
            "requiresActionLedStaging": True,
            "warning": (
                f"{profile.get('name', 'Character')} has no facial lip-sync controls; "
                "use a medium/body shot and visible action rather than a dialogue close-up."
            ),
        }
    return {
        "status": "direct_dialogue" if profile.get("direct_dialogue") else "brief_body_line",
        "words": words,
        "maxWords": maximum,
        "lipSync": profile.get("lip_sync") or "none",
        "camera": profile.get("camera") or "medium",
        "requiresActionLedStaging": not bool(profile.get("direct_dialogue")),
        "warning": profile.get("warning") or "",
    }


def casting_decision(character, profile):
    """Explain the selected asset's safe role in a story plan.

    The value is returned to Preview and saved alongside the parsed character,
    so a user can see why an action rig or jaw rig was selected.  It does not
    mutate the selected character or promise a capability the asset lacks.
    """
    character = character or {}
    profile = profile or policy_for_tier("SKELETAL_BASIC")
    need = str(character.get("performance_need") or "balanced")
    evidence = dict(character.get("performance_evidence") or {})
    if need == "hybrid":
        route = "body-led dialogue"
        message = (
            "This role needs both movement and dialogue. Keep action as the primary performance; "
            "use only short spoken beats unless a jaw-capable character is selected."
        )
    elif need == "skeletal_action":
        route = "body performance"
        message = "This role is action-led, so authored body animation and grounded movement take priority."
    elif need == "dialogue":
        route = "dialogue performance"
        message = "This role is dialogue-led, so the safest available lip-sync tier is preferred."
    else:
        route = "balanced performance"
        message = "This role has no dominant performance demand."
    if profile.get("lip_sync") == "none" and evidence.get("dialogue_words", 0) > profile.get("max_spoken_words", 0):
        message += " This selected asset remains body-only; the preview will use medium/action staging."
    return {
        "need": need,
        "route": route,
        "evidence": evidence,
        "selectedTier": profile.get("tier"),
        "lipSync": profile.get("lip_sync"),
        "message": message,
    }


def annotate_story_requirements(parsed):
    """Attach deterministic casting needs without changing story content."""
    import actions
    action_heavy = set(actions.SUPPORTED_ACTIONS) - {"idle", "look", "listen", "nod", "shake"}
    stats = {character.get("id"): {"dialogue_words": 0, "body_actions": 0, "locomotion": 0}
             for character in parsed.get("characters", [])}
    for scene in parsed.get("scenes", []):
        for line in scene.get("lines", []):
            speaker = line.get("speaker")
            if speaker not in stats:
                continue
            stats[speaker]["dialogue_words"] += len(str(line.get("text") or "").split())
            explicit = re.sub(r"[^a-z_]+", "_", str(line.get("action") or "").lower()).strip("_")
            action = explicit if explicit in actions.SUPPORTED_ACTIONS else actions.detect(
                f"{line.get('action', '')} {line.get('text', '')}", line.get("emotion"))
            if action in action_heavy:
                stats[speaker]["body_actions"] += 1
            if action in {"walk", "run", "approach", "exit"}:
                stats[speaker]["locomotion"] += 1
            if not line.get("action") and action != "none":
                line["action"] = action
                line["action_source"] = "automatic_story_direction"
    for character in parsed.get("characters", []):
        evidence = stats.get(character.get("id"), {})
        if ((evidence.get("locomotion", 0) or evidence.get("body_actions", 0) >= 2)
                and evidence.get("dialogue_words", 0) >= 5):
            need = "hybrid"
        elif evidence.get("locomotion", 0) or evidence.get("body_actions", 0) >= 2:
            need = "skeletal_action"
        elif evidence.get("dialogue_words", 0) >= 5:
            need = "dialogue"
        else:
            need = "balanced"
        character["performance_need"] = need
        character["performance_evidence"] = evidence
    return parsed
