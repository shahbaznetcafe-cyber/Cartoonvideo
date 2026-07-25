"""Deterministic script-to-screen direction for the main SBZ render pipeline.

This module sits after story parsing and before frame rendering.  It converts
story meaning into renderer-safe shots, real authored clips, world movement,
lightweight props and environmental motion.  AI may describe the story, but
only this validated plan reaches the renderer.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path

import config
import actions
import character_performance
import scene_assets
import transitions


SCHEMA_VERSION = 4
PLAN_FILENAME = "production_direction.json"
REGISTRY_PATH = Path(config.BASE_DIR) / "assets" / "characters" / "capability_registry.json"

ACTION_CLIP_CANDIDATES = {
    "none": ("TalkIdle", "Idle_Neutral", "Idle"),
    "idle": ("Idle_Neutral", "Idle"),
    "listen": ("Listen", "Idle_Neutral", "Idle"),
    "look": ("Listen", "Idle_Neutral", "Idle"),
    "walk": ("Walk",), "come": ("Walk",), "go": ("Walk",),
    "approach": ("Walk",), "exit": ("Run", "Walk"),
    "run": ("Run",), "retreat": ("Run_Back", "Run"),
    "wave": ("Wave",), "greet": ("Wave",),
    "point": ("Point", "Idle_Gun_Pointing"),
    "reach": ("Interact",), "pickup": ("Interact",),
    "give": ("Interact",), "offer": ("Interact",), "interact": ("Interact",),
    "celebrate": ("Celebrate",), "jump": ("Celebrate",), "dance": ("Celebrate",),
    "nod": ("Listen", "Idle_Neutral"), "shake": ("Listen", "Idle_Neutral"),
    "hug": ("Interact",), "help": ("Interact",), "pull": ("Interact",),
    "punch": ("Punch_Right", "Punch_Left"), "kick": ("Kick_Right", "Kick_Left"),
    "hit": ("HitRecieve_2", "HitRecieve"), "fall": ("Death", "HitRecieve_2"),
    "sit": ("Idle_Neutral", "Idle"), "stand": ("Idle_Neutral", "Idle"),
    "talk": ("TalkIdle", "Idle_Neutral", "Idle"),
}

# These are transparent story-action substitutions, never renamed clips.  They
# are used only when the requested semantic action has no authored clip but a
# registered body performance can communicate the beat more honestly than an
# idle/listen fallback.  The saved direction retains both requestedAction and
# sourceClip so an editor can review the compromise.
SEMANTIC_CLIP_SUBSTITUTES = {
    "wash": ("Interact",),
    "splash": ("Interact",),
    "slip": ("Roll", "HitRecieve_2"),
    "fall": ("Death", "HitRecieve_2"),
}

PROP_RULES = (
    ("box", ("box", "crate", "sandook", "sandooq", "dabba", "parcel")),
    ("seed", ("seed", "seeds", "beej", "magic seed", "golden seed")),
    ("plant", ("plant", "plants", "pauda", "pauday", "paudon", "phool", "flower", "flowers")),
    ("ball", ("ball", "football", "cricket ball", "gend", "gainD")),
    ("book", ("book", "kitab", "kitaab", "copy")),
    ("gift", ("gift", "tohfa", "present")),
    ("cup", ("cup", "glass", "mug", "chai", "tea")),
    ("sign", ("sign", "board", "nishan", "notice")),
    ("rock", ("rock", "stone", "pathar", "patthar")),
)

INTERACTION_ACTIONS = {"reach", "pickup", "give", "offer", "interact", "point", "kick", "hit"}
CONTACT_ACTIONS = {"reach", "pickup", "give", "offer", "interact"}
LOCOMOTION_ACTIONS = {"walk", "come", "go", "approach", "run", "retreat", "exit"}
REACTION_EMOTIONS = {"surprised", "scared", "sad", "angry", "confused", "fear"}
CONTINUITY_PURPOSES = {"relationship", "dialogue"}


def _tokens(value):
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _stable_seed(*values):
    raw = "\0".join(str(value) for value in values).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big") & 0x7FFFFFFF


@lru_cache(maxsize=2)
def _registry(fingerprint=None):
    del fingerprint
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8")).get("characters", {})
    except (OSError, ValueError, TypeError):
        return {}


def _registry_data():
    try:
        stat = REGISTRY_PATH.stat()
        fingerprint = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        fingerprint = None
    return _registry(fingerprint)


def _real_clip(blend, action, speaking):
    import char3d_lib
    metadata = char3d_lib.runtime_metadata(blend)
    # Quaternius assets have a per-character, verified clip registry.  Resolve
    # every story action through it before the generic legacy candidates; this
    # keeps creatures/aerial characters on real clips and removes false
    # "fallback" warnings for automatically safe staging.
    if str(metadata.get("library") or "").lower() == "quaternius":
        try:
            import character_traits
            directive = character_traits.render_directive(blend, action)
            source = str(directive.get("sourceClip") or "")
            if source:
                supported = bool(directive.get("actionSupported"))
                semantic = bool(directive.get("semantic"))
                if semantic:
                    return {
                        "sourceClip": source,
                        "resolution": "semantic_authored_substitute",
                        "requestedAction": action,
                        "motionQuality": "semantic_substitute",
                        "warning": f"{action} is staged with the real authored {source} clip",
                    }
                return {
                    "sourceClip": source,
                    "resolution": "exact_authored_clip" if supported else "automatic_safe_staging",
                    "requestedAction": action,
                    "motionQuality": "authored_action" if supported else "safe_staging",
                    "warning": None if supported else f"{action} has no authored clip; using {source}",
                }
        except Exception:
            # Generic registry logic below remains a safe fallback if a local
            # trait sidecar is unavailable.
            pass
    capability = _registry_data().get(metadata.get("capabilityId"), {})
    authored = capability.get("authoredClips") or {}
    if not authored:
        return {"sourceClip": "", "resolution": "procedural_legacy_fallback",
                "requestedAction": action, "motionQuality": "legacy_procedural", "warning": None}
    candidates = list(ACTION_CLIP_CANDIDATES.get(action, ()))
    if speaking and action in {"none", "idle", "listen", "look"}:
        candidates = ["TalkIdle", *candidates]
    primary = candidates[0] if candidates else ""
    if primary in authored:
        return {"sourceClip": primary, "resolution": "exact_authored_clip",
                "requestedAction": action, "motionQuality": "authored_action",
                "warning": None}
    for candidate in candidates[1:]:
        if candidate in authored:
            return {"sourceClip": candidate, "resolution": "registered_safe_fallback",
                    "requestedAction": action, "motionQuality": "safe_fallback",
                    "warning": f"{action} has no authored {primary} clip; using {candidate}"}
    for candidate in SEMANTIC_CLIP_SUBSTITUTES.get(action, ()):
        if candidate in authored:
            return {"sourceClip": candidate, "resolution": "semantic_authored_substitute",
                    "requestedAction": action, "motionQuality": "semantic_substitute",
                    "warning": f"{action} is staged with the real authored {candidate} clip"}
    for candidate in ("Listen", "Idle_Neutral", "Idle"):
        if candidate in authored:
            return {"sourceClip": candidate, "resolution": "registered_safe_fallback",
                    "requestedAction": action, "motionQuality": "safe_fallback",
                    "warning": f"{action} has no authored clip; using {candidate}"}
    fallback = next(iter(authored), "")
    return {"sourceClip": fallback, "resolution": "first_registered_fallback",
            "requestedAction": action, "motionQuality": "unsafe_fallback",
            "warning": f"{action} has no safe authored clip; using {fallback}"}


def _capability_for_blend(blend):
    import char3d_lib
    metadata = char3d_lib.runtime_metadata(blend)
    return _registry_data().get(metadata.get("capabilityId"), {})


def _base_clip(blend, speaking):
    return _real_clip(blend, "talk" if speaking else "listen", speaking).get("sourceClip", "")


def _layout_for(cast):
    """Asymmetric depth-aware starting marks; never a flat presentation row."""
    layouts = {
        1: ((-0.28, 0.36, -0.06),),
        2: ((-1.35, 0.52, 0.10), (1.35, 0.12, -0.10)),
        3: ((-2.20, 0.58, 0.12), (0.00, 0.10, 0.0), (2.20, 0.42, -0.12)),
    }
    marks = layouts.get(len(cast), layouts[3])
    return {cid: {"x": marks[index][0], "z": marks[index][1], "yaw": marks[index][2]}
            for index, cid in enumerate(cast[:len(marks)])}


def _prop_target(prop, state):
    heights = {"box": 0.43, "seed": 0.08, "plant": 0.54, "ball": 0.18,
               "book": 0.09, "cup": 0.24, "sign": 0.58, "rock": 0.18}
    return {"name": f"{prop['id']}.contact", "propId": prop["id"],
            "position": [float(state.get("x", 0.0)), heights.get(prop["type"], 0.22),
                         float(state.get("z", 0.0))]}


def _scene_preset(scene):
    text = " ".join(str(scene.get(key) or "") for key in
                    ("location", "background_prompt", "mood", "time")).lower()
    words = _tokens(text)
    if words & {"night", "raat", "midnight", "moon"}:
        return "night"
    if words & {"storm", "rain", "barish", "baarish", "thunder", "windy"}:
        return "storm"
    if words & {"mud", "puddle", "slip", "phisal"}:
        return "mud"
    if words & {"wash", "soap", "clean", "hygiene"}:
        return "wash"
    # "beach" alone is an ordinary seaside, not a pirate story; it routes to the
    # friendlier beach preset below.
    if words & {"pirate", "ship", "island", "dock", "harbor", "harbour", "treasure", "sea"}:
        return "pirate"
    # Generic city/street words belong to the ordinary town preset; keep this
    # branch for genuinely post-apocalyptic scenes.
    if words & {"zombie", "apocalypse", "ruins", "abandoned", "survival", "wasteland"}:
        return "apocalypse"
    if words & {"space", "planet", "rocket", "astronaut", "alien", "galaxy", "moon", "mars"}:
        return "space"
    if words & {"stage", "party", "celebration", "festival"}:
        return "stage"
    if words & {"snow", "winter", "baraf", "ice"}:
        return "snow"
    if words & {"desert", "sehra", "sand", "dunes"}:
        return "desert"
    if words & {"beach", "sahil", "kinara", "island", "jazeera", "sand", "seaside"}:
        return "beach"
    # A "village farm" is still a farm scene: only treat a village as a built-up
    # square when no farm/field/garden word is present.
    if (words & {"village", "gaon", "gaun", "mohalla", "basti", "chowk", "dehat"}
            and not words & {"farm", "field", "khet", "garden", "bagh", "orchard"}):
        return "village"
    if words & {"town", "city", "street", "road", "sarak", "shehar", "traffic", "crossing"}:
        return "town"
    if words & {"market", "bazaar", "shop", "store", "stall", "dukan", "mandi"}:
        return "market"
    if words & {"kitchen", "room", "house", "home", "school", "classroom", "office",
                "ghar", "kamra", "rasoi", "madrasa"}:
        return "indoor"
    if words & {"meadow", "maidan", "grassland", "lawn", "clearing", "pasture"}:
        return "meadow"
    if words & {"forest", "jungle", "garden", "park", "farm", "field", "path",
                "bagh", "khet", "raasta"}:
        return "forest"
    return "sunny"


def _environment(scene, scene_index=0):
    preset = _scene_preset(scene)
    text = " ".join(str(scene.get(key) or "") for key in
                    ("location", "background_prompt", "mood", "time"))
    words = _tokens(text)
    variant = preset
    if preset == "forest":
        if words & {"glowing", "glow", "magic", "magical", "roshan", "chamak"}:
            variant = "glowing_field"
        elif words & {"blooming", "bloom", "flowers", "phool", "afternoon", "shaam"}:
            variant = "blooming_farm"
        elif words & {"village", "farm", "morning", "subah"}:
            variant = "village_farm"
        else:
            # A generic "forest" in consecutive scenes must not become the
            # same set with a different dialogue track.  These lightweight
            # beats keep the location coherent while giving the shot director
            # an observable progression through the world.
            variant = ("forest_path", "forest_clearing", "forest_grove")[int(scene_index) % 3]
    elif preset == "pirate":
        if words & {"treasure", "chest", "gold", "map", "khazana"}:
            variant = "treasure_cove"
        elif words & {"ship", "sail", "sea", "harbor", "harbour", "dock"}:
            variant = "pirate_harbor"
        else:
            variant = ("pirate_harbor", "treasure_cove")[int(scene_index) % 2]
    elif preset == "space":
        variant = "space_outpost"
    elif preset == "apocalypse":
        variant = "apocalypse_street"
    elif preset == "village":
        variant = "village_square"
    elif preset in {"town", "market"}:
        variant = "town_street"
    elif preset == "night":
        variant = "night_forest"
    elif preset == "meadow":
        variant = "open_meadow"
    elif preset == "beach":
        variant = "island_beach"
    elif preset == "desert":
        variant = "rocky_desert"
    if preset == "forest" and words & {"mushroom", "magic", "magical", "fairy",
                                       "jadoo", "jadui", "khayali"}:
        variant = "magic_grove"
    outdoors = preset in {"sunny", "forest", "market", "storm", "mud", "night", "snow",
                          "desert", "pirate", "space", "apocalypse", "village", "town",
                          "meadow", "beach"}
    mood = str(scene.get("mood") or "neutral").lower()
    wind = 0.18 if outdoors else 0.04
    if preset == "storm":
        wind = 0.78
    elif mood in {"action", "suspense"}:
        wind += 0.18
    return {
        "preset": preset,
        "variant": variant,
        "seed": _stable_seed(scene.get("id"), scene.get("location")),
        "windStrength": round(min(1.0, wind), 3),
        "leaves": 24 if preset in {"forest", "storm"} else 12 if preset == "pirate" else 8 if outdoors else 0,
        "clouds": 4 if outdoors and preset not in {"space", "apocalypse"} else 0,
        "ambientActors": 3 if preset in {"forest", "market", "sunny", "pirate"} else 1 if preset == "space" else 0,
        "instancedVegetation": outdoors,
    }


def _detect_props(scene):
    text = " ".join([
        str(scene.get("location") or ""), str(scene.get("background_prompt") or ""),
        *[str(line.get("text") or "") + " " + str(line.get("action") or "")
          for line in scene.get("lines", [])],
    ]).lower()
    result = []
    for prop_type, keywords in PROP_RULES:
        if any(actions.keyword_present(text, keyword) for keyword in keywords):
            index = len(result)
            result.append({
                "id": f"{prop_type}_{index + 1}", "type": prop_type,
                "color": {"box": "#6f4325", "ball": "#e05c35", "book": "#4267a9",
                          "gift": "#a83d6e", "cup": "#d6dbe5", "sign": "#d7b46a",
                          "rock": "#747b80", "seed": "#f4c542",
                          "plant": "#42a84b"}.get(prop_type, "#8b6b4b"),
                "semanticTerms": list(keywords),
                "position": [1.15 - index * 0.8, 0.0, 0.25 + index * 0.14],
            })
    return result[:3]


def _shot_for(performance, action, emotion, scene_line, cast_size, prop, text):
    if scene_line == 0:
        return "establishing_wide", "establish"
    if action in LOCOMOTION_ACTIONS:
        return ("tracking_exit_wide", "exit") if action == "exit" else ("tracking_medium", "locomotion")
    if prop and action in INTERACTION_ACTIONS:
        return "contact_oblique_medium", "contact"
    if prop and action in {"none", "idle", "talk", "look", "listen"}:
        return "prop_detail_close", "prop_reveal"
    if str(emotion or "").lower() in REACTION_EMOTIONS or "?" in str(text or ""):
        if performance.get("facial_ready"):
            return "dialogue_close_up", "facial_reaction"
        return "body_reaction_medium_close", "body_reaction"
    if cast_size > 1:
        return "motivated_two_shot", "relationship"
    if performance.get("facial_ready"):
        return "dialogue_close_up", "dialogue"
    # Body-only and jaw rigs need cinematic variation without pretending that
    # a face close-up is meaningful.  The two side-medium angles are spaced
    # across the scene rather than applied as decorative transitions on every
    # line.  Each remains a clean, readable dialogue shot.
    if scene_line % 3 == 2:
        return "body_medium_left", "dialogue"
    if scene_line % 3 == 0 and scene_line:
        return "body_medium_right", "dialogue"
    return "dialogue_medium", "dialogue"


def _prop_state(prop):
    x, y, z = prop["position"]
    return {"x": x, "y": y, "z": z, "rotationY": 0.0, "open": 0.0,
            "growth": 0.3 if prop["type"] == "plant" else 1.0, "glow": 0.0}


def _prop_consequence(prop, action, start, text=""):
    end = copy.deepcopy(start)
    consequence = "none"
    growth_cue = prop["type"] == "plant" and any(actions.keyword_present(text, keyword) for keyword in (
        "grow", "grows", "growing", "bloom", "blooming", "glow", "glowing",
        "magic", "magical", "khil", "khilta", "ugta", "roshan", "chamak",
    ))
    if action not in INTERACTION_ACTIONS and not growth_cue:
        return end, consequence
    if prop["type"] == "box":
        end["open"] = 1.0
        end["rotationY"] += 0.08
        consequence = "lid_opens"
    elif prop["type"] == "ball":
        end["x"] += 0.72
        end["rotationY"] += 2.6
        consequence = "rolls"
    elif prop["type"] == "seed":
        end["y"] += 0.48
        end["rotationY"] += 0.8
        end["glow"] = 0.8
        consequence = "seed_lifts_and_glows"
    elif prop["type"] == "plant":
        end["growth"] = 1.0
        end["glow"] = 0.72
        consequence = "plant_grows_and_glows"
    else:
        end["y"] += 0.24
        end["rotationY"] += 0.35
        consequence = "moves"
    return end, consequence


def preview_motion_audit(parsed, assignments):
    """Fast, render-free motion audit used by the Cast & Scenes preview.

    The final renderer performs the same resolution again while compiling its
    full plan.  This lightweight pass lets an editor fix an unsupported action
    or choose another character before voices and frames are created.
    """
    counts = {"authored_action": 0, "semantic_substitute": 0, "safe_fallback": 0,
              "unsafe_fallback": 0, "legacy_procedural": 0}
    warnings = []
    planned = []
    for scene in parsed.get("scenes", []):
        for line_number, line in enumerate(scene.get("lines", []), 1):
            speaker = str(line.get("speaker") or "")
            action = str(line.get("action") or "talk").lower()
            clip = _real_clip(assignments.get(speaker) or "", action, True)
            quality = clip.get("motionQuality") or "legacy_procedural"
            counts[quality] = counts.get(quality, 0) + 1
            planned.append({
                "scene": scene.get("id"), "line": line_number, "speaker": speaker,
                "action": action, "sourceClip": clip.get("sourceClip") or "",
                "quality": quality,
            })
            if clip.get("warning"):
                warnings.append({
                    "scene": scene.get("id"), "line": line_number, "speaker": speaker,
                    "action": action, "message": clip["warning"],
                })
    return {
        "counts": counts,
        "plannedLines": planned,
        "warnings": warnings,
        "ready": counts.get("safe_fallback", 0) == 0 and counts.get("unsafe_fallback", 0) == 0,
        "message": ("All planned speaking actions resolve to real authored clips."
                    if not warnings else "Some planned actions use an explicit real-clip substitute or fallback; review them before rendering."),
    }


def build_plan(parsed, timeline, assignments, line_contexts, fps=24, acting_plan=None):
    """Compile a complete deterministic plan for the main per-line renderer."""
    if len(timeline) != len(line_contexts):
        raise ValueError("timeline and line contexts must have equal length")
    scenes_by_id = {str(scene.get("id")): scene for scene in parsed.get("scenes", [])}
    scene_profiles = {}
    prop_states = {}
    for scene_index, (scene_id, scene) in enumerate(scenes_by_id.items()):
        props = _detect_props(scene)
        environment = _environment(scene, scene_index)
        # Real, locally verified scenery is added as static dressing.  Stateful
        # story props keep their existing procedural meshes so an open box,
        # rolling ball or growing plant cannot silently lose its consequence.
        props.extend(scene_assets.renderer_props(environment, scene_index))
        scene_profiles[scene_id] = {
            "id": scene.get("id"), "location": scene.get("location"),
            "environment": environment, "props": props,
        }
        prop_states[scene_id] = {prop["id"]: _prop_state(prop) for prop in props}

    scene_line_counts = {}
    blocking_states = {}
    shot_states = {}
    warnings = []
    lines = []
    transition_decisions = [transitions.decision("hard_cut", reason="first story beat")]
    transition_decisions.extend(transitions.plan_transitions(timeline, 0.30))
    for index, (entry, context) in enumerate(zip(timeline, line_contexts), 1):
        scene_id = str(entry.get("scene"))
        scene_profile = scene_profiles.get(scene_id, {
            "id": entry.get("scene"), "location": entry.get("location"),
            "environment": _environment(entry), "props": [],
        })
        scene_line = scene_line_counts.get(scene_id, 0)
        scene_line_counts[scene_id] = scene_line + 1
        speaker = entry.get("speaker")
        action = str(context.get("action") or "none").lower()
        cast = list(context.get("cast") or [speaker])
        blend = assignments.get(speaker) or ""
        performance = character_performance.profile_for_blend(blend)
        line_semantics = (str(entry.get("action") or "") + " " +
                          str(entry.get("text") or "")).lower()
        prop = next((item for item in scene_profile["props"]
                     if any(actions.keyword_present(line_semantics, term)
                            for term in item.get("semanticTerms", (item["type"],)))), None)
        if prop is None and action in INTERACTION_ACTIONS and scene_profile["props"]:
            prop = scene_profile["props"][0]
        shot, purpose = _shot_for(performance, action, entry.get("emotion"), scene_line,
                                  len(cast), prop, entry.get("text"))
        previous_shot = shot_states.get(scene_id)
        continues_shot = bool(len(cast) > 1 and previous_shot and purpose in CONTINUITY_PURPOSES
                              and previous_shot["purpose"] in CONTINUITY_PURPOSES)
        if continues_shot:
            shot = previous_shot["shot"]
            shot_id = previous_shot["id"]
            shot_number = previous_shot["number"]
        else:
            shot_number = (previous_shot or {}).get("number", 0) + 1
            shot_id = f"scene_{scene_id}_shot_{shot_number}"
        shot_states[scene_id] = {"shot": shot, "purpose": purpose, "id": shot_id,
                                 "number": shot_number}
        directed_props = []
        for item in scene_profile["props"]:
            start = copy.deepcopy(prop_states.setdefault(scene_id, {}).setdefault(
                item["id"], _prop_state(item)))
            end, consequence = (_prop_consequence(item, action, start, entry.get("text") or "")
                                if prop and item["id"] == prop["id"] else (copy.deepcopy(start), "none"))
            prop_states[scene_id][item["id"]] = copy.deepcopy(end)
            directed_props.append({**item, "stateStart": start, "stateEnd": end,
                                   "consequence": consequence})

        defaults = _layout_for(cast)
        scene_blocking = blocking_states.setdefault(scene_id, {})
        for cid in cast:
            scene_blocking.setdefault(cid, copy.deepcopy(defaults.get(cid, {"x": 0.0, "z": 0.4, "yaw": 0.0})))
        blocking = {cid: {"start": copy.deepcopy(scene_blocking[cid]),
                          "end": copy.deepcopy(scene_blocking[cid])} for cid in cast}
        interaction = None
        if prop and action in CONTACT_ACTIONS and speaker in blocking:
            selected_prop = next(item for item in directed_props if item["id"] == prop["id"])
            target = _prop_target(prop, selected_prop["stateStart"])
            capability = _capability_for_blend(blend)
            interaction_capability = capability.get("interaction") or {}
            supported = (interaction_capability.get("supported") or {}).get("right_hand_reach") or {}
            interaction_enabled = bool(interaction_capability.get("enabled") and supported)
            stand_off = float(supported.get("preferredStandOff") or 0.72)
            acting_character = (((acting_plan or {}).get("lines") or [{}])[index - 1]
                                .get("characters", {}).get(speaker, {})
                                if index <= len((acting_plan or {}).get("lines") or []) else {})
            acting_end_x = float((((acting_character.get("end") or {}).get("position") or {}).get("x") or 0.0))
            current_world_x = blocking[speaker]["start"]["x"] + acting_end_x
            side = 1.0 if current_world_x <= target["position"][0] else -1.0
            desired_world_x = target["position"][0] - side * stand_off
            blocking[speaker]["end"]["x"] = round(max(-2.2, min(2.2, desired_world_x - acting_end_x)), 6)
            blocking[speaker]["end"]["z"] = round(target["position"][2] + 0.16, 6)
            blocking[speaker]["end"]["yaw"] = round(side * 0.28, 6)
            estimated_gap = round(max(0.0, stand_off - 0.72), 6)
            maximum_gap = float(supported.get("maximumContactDistance") or 0.2)
            interaction = {
                "target": target,
                "characterStart": copy.deepcopy(blocking[speaker]["start"]),
                "characterEnd": copy.deepcopy(blocking[speaker]["end"]),
                "triggerProgress": 0.58,
                "wristBone": supported.get("wristBone") or "",
                "handIK": False,
                "cameraGapMasking": bool(supported.get("cameraGapMasking", True)),
                "estimatedWristGap": estimated_gap,
                "maximumContactDistance": maximum_gap,
                "consequence": selected_prop.get("consequence") or "none",
                "status": "planned_camera_masked_contact" if interaction_enabled and estimated_gap <= maximum_gap
                          else "unvalidated_body_hint",
            }
            if not interaction_enabled:
                warnings.append({
                    "line": index, "character": speaker, "code": "interaction_not_calibrated",
                    "message": f"{speaker} has no validated hand interaction; using body acting and an oblique camera",
                })
        for cid in cast:
            scene_blocking[cid] = copy.deepcopy(blocking[cid]["end"])

        character_directions = {}
        for cid in cast:
            speaking = cid == speaker
            char_action = action if speaking else "listen"
            clip = _real_clip(assignments.get(cid) or "", char_action, speaking)
            performance_profile = character_performance.profile_for_blend(assignments.get(cid) or "")
            dialogue_presentation = character_performance.dialogue_route(
                performance_profile, entry.get("text") if speaking else ""
            )
            if speaking and dialogue_presentation["status"] == "action_led_body_only":
                warnings.append({
                    "line": index, "character": cid, "code": "body_only_dialogue_route",
                    "message": dialogue_presentation["warning"],
                })
            if clip.get("warning") and char_action not in {"none", "idle", "talk", "listen", "look"}:
                warnings.append({"line": index, "character": cid,
                                 "code": "authored_action_unavailable",
                                 "message": clip["warning"]})
            character_directions[cid] = {
                "action": char_action, **clip,
                "baseClip": _base_clip(assignments.get(cid) or "", speaking),
                "crossfadeSeconds": 0.22,
                "blocking": blocking[cid],
                "interaction": interaction if cid == speaker else None,
                "speaking": speaking,
                "performance": performance_profile,
                "dialoguePresentation": dialogue_presentation,
            }
        transition = transition_decisions[index - 1]
        lines.append({
            "line": index, "scene": entry.get("scene"), "sceneLine": scene_line,
            "speaker": speaker, "action": action, "purpose": purpose, "shot": shot,
            "shotId": shot_id, "continuesPreviousShot": continues_shot,
            "targetSlot": context.get("target", -1),
            "transition": transition["type"],
            "transitionDuration": transition["duration"],
            "transitionReason": transition["reason"],
            "camera": {
                "composition": "prop_weighted_rule_of_thirds" if prop else "off_center_rule_of_thirds",
                "motion": "lead_follow" if action in LOCOMOTION_ACTIONS else
                          "subtle_push" if purpose in {"dialogue", "body_reaction", "facial_reaction"} else "locked",
                "followStrength": 0.35 if action in LOCOMOTION_ACTIONS else 0.0,
                "focusProp": prop["id"] if prop and purpose in {"contact", "prop_reveal"} else None,
                "contactMasking": bool(interaction and interaction.get("cameraGapMasking")),
            },
            "environment": copy.deepcopy(scene_profile["environment"]),
            "props": directed_props,
            "interaction": interaction,
            "characters": character_directions,
        })

    motion_counts = {"authored_action": 0, "semantic_substitute": 0, "safe_fallback": 0,
                     "unsafe_fallback": 0, "legacy_procedural": 0}
    for line in lines:
        for direction in line["characters"].values():
            quality = direction.get("motionQuality") or "legacy_procedural"
            motion_counts[quality] = motion_counts.get(quality, 0) + 1
    plan = {
        "schema_version": SCHEMA_VERSION,
        "generator": "SBZ Production Director",
        "deterministic": True,
        "fps": int(fps or 24),
        "scenes": list(scene_profiles.values()),
        "lines": lines,
        "warnings": warnings,
        "motionAudit": {
            "counts": motion_counts,
            "fullyAuthored": motion_counts.get("safe_fallback", 0) == 0
            and motion_counts.get("unsafe_fallback", 0) == 0
            and motion_counts.get("legacy_procedural", 0) == 0,
        },
        "facialAvailability": {
            "fullFacialRegistered": 0,
            "visemeRegistered": 0,
            "jawDialogueRecommendations": character_performance.dialogue_cast_recommendations(),
            "status": "jaw_only_dialogue_library",
            "message": "No facial-ready character is registered. Available dialogue choices use jaw-openness only.",
        },
    }
    validate_plan(plan, timeline)
    return plan


def validate_plan(plan, timeline):
    diagnostics = []
    if len(plan.get("lines", [])) != len(timeline):
        diagnostics.append("direction line count does not match dialogue timeline")
    for index, line in enumerate(plan.get("lines", []), 1):
        if line.get("line") != index:
            diagnostics.append(f"line {index}: non-contiguous direction index")
        if not line.get("shot") or not line.get("purpose"):
            diagnostics.append(f"line {index}: shot purpose is incomplete")
        if not line.get("shotId"):
            diagnostics.append(f"line {index}: shot continuity id is missing")
        for character_id, direction in line.get("characters", {}).items():
            if direction.get("resolution") == "exact_authored_clip" and not direction.get("sourceClip"):
                diagnostics.append(f"line {index}: {character_id} exact clip is empty")
            blocking = direction.get("blocking") or {}
            if not blocking.get("start") or not blocking.get("end"):
                diagnostics.append(f"line {index}: {character_id} blocking marks are incomplete")
        if line.get("camera", {}).get("focusProp") and not any(
                prop.get("id") == line["camera"]["focusProp"] for prop in line.get("props", [])):
            diagnostics.append(f"line {index}: camera references an unknown prop")
        interaction = line.get("interaction")
        if interaction and not any(prop.get("id") == interaction.get("target", {}).get("propId")
                                   for prop in line.get("props", [])):
            diagnostics.append(f"line {index}: interaction references an unknown prop")
    if diagnostics:
        raise ValueError("Production direction validation failed: " + "; ".join(diagnostics))
    return plan


def write_plan(project_dir, plan):
    path = os.path.join(project_dir, PLAN_FILENAME)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)
    return path
