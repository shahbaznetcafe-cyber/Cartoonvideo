"""Defensive JSON, story, timing and character-capability validation."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


class OutputValidationError(ValueError):
    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or []


def extract_json(raw):
    if isinstance(raw, (dict, list)):
        return deepcopy(raw)
    text = str(raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    starts = [(text.find("{"), "{"), (text.find("["), "[")]
    starts = [(index, token) for index, token in starts if index >= 0]
    if not starts:
        raise OutputValidationError("Model response did not contain JSON")
    start, token = min(starts)
    end = text.rfind("}" if token == "{" else "]")
    if end < start:
        raise OutputValidationError("Model response contained incomplete JSON")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise OutputValidationError(f"Malformed JSON at line {exc.lineno}, column {exc.colno}") from exc


def load_schema(name):
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def validate_schema(value, schema, path="$", diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else []
    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        checks = {
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "string": lambda item: isinstance(item, str),
            "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "boolean": lambda item: isinstance(item, bool),
            "null": lambda item: item is None,
        }
        if not any(checks[item](value) for item in allowed if item in checks):
            diagnostics.append(f"{path}: expected {'|'.join(allowed)}")
            return diagnostics
    if "const" in schema and value != schema["const"]:
        diagnostics.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        diagnostics.append(f"{path}: unsupported value {value!r}")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        diagnostics.append(f"{path}: string is too short")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            diagnostics.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            diagnostics.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                diagnostics.append(f"{path}.{field}: mandatory field is missing")
        for field, child in schema.get("properties", {}).items():
            if field in value:
                validate_schema(value[field], child, f"{path}.{field}", diagnostics)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            diagnostics.append(f"{path}: too few items")
        child = schema.get("items")
        if child:
            for index, item in enumerate(value):
                validate_schema(item, child, f"{path}[{index}]", diagnostics)
    return diagnostics


def require_valid(value, schema):
    diagnostics = validate_schema(value, schema)
    if diagnostics:
        raise OutputValidationError("Structured output failed schema validation", diagnostics)
    return value


def validate_parsed_story(value):
    story = require_valid(value, load_schema("parsed_story.schema.json"))
    character_ids = {character["id"] for character in story["characters"]}
    diagnostics = []
    for scene_index, scene in enumerate(story["scenes"]):
        unknown = set(scene["characters"]) - character_ids
        if unknown:
            diagnostics.append(f"$.scenes[{scene_index}].characters: unknown IDs {sorted(unknown)}")
        total = sum(float(item["estimatedDuration"]) for item in scene["elements"])
        if abs(total - float(scene["estimatedDuration"])) > max(0.75, scene["estimatedDuration"] * 0.15):
            diagnostics.append(f"$.scenes[{scene_index}]: element timing does not match scene duration")
        for element_index, element in enumerate(scene["elements"]):
            if element["type"] == "dialogue":
                if not element.get("speaker") or not element.get("text"):
                    diagnostics.append(f"$.scenes[{scene_index}].elements[{element_index}]: dialogue needs speaker and text")
                elif element["speaker"] not in character_ids and element["speaker"] != "narrator":
                    diagnostics.append(f"$.scenes[{scene_index}].elements[{element_index}]: unknown speaker")
    if diagnostics:
        raise OutputValidationError("Parsed story failed semantic validation", diagnostics)
    return story


def _capability_registry(path=None):
    registry_path = Path(path or REPO / "assets" / "characters" / "capability_registry.json")
    if not registry_path.exists():
        return {}
    return json.loads(registry_path.read_text(encoding="utf-8")).get("characters", {})


def validate_storyboard(value, capability_registry_path=None, apply_safe_fallbacks=True):
    board = require_valid(value, load_schema("storyboard.schema.json"))
    diagnostics, fallbacks = [], []
    total_frames = round(float(board["durationSeconds"]) * int(board["fps"]))
    beats = sorted(board["beats"], key=lambda beat: beat["startFrame"])
    cursor = 0
    for index, beat in enumerate(beats):
        if beat["startFrame"] != cursor:
            diagnostics.append(f"$.beats[{index}]: timing gap/overlap; expected startFrame {cursor}")
        if beat["endFrame"] <= beat["startFrame"]:
            diagnostics.append(f"$.beats[{index}]: endFrame must be after startFrame")
        cursor = beat["endFrame"]
    if cursor != total_frames:
        diagnostics.append(f"$.beats: final frame {cursor} does not match timeline {total_frames}")

    registry = _capability_registry(capability_registry_path)
    board_characters = {item["id"]: item for item in board["characters"]}
    for character in board["characters"]:
        capability = registry.get(character["capabilityId"])
        if not capability:
            diagnostics.append(f"$.characters: capability {character['capabilityId']!r} is not registered")
            continue
        if capability.get("tier") != character["capabilityTier"]:
            diagnostics.append(f"$.characters: tier mismatch for {character['id']}")
    for index, beat in enumerate(beats):
        character_id = beat.get("characterId")
        if not character_id:
            continue
        board_character = board_characters.get(character_id)
        if not board_character:
            diagnostics.append(f"$.beats[{index}]: unknown character {character_id!r}")
            continue
        capability = registry.get(board_character["capabilityId"], {})
        source_clip = beat.get("sourceClip")
        if source_clip and source_clip not in capability.get("authoredClips", {}):
            diagnostics.append(f"$.beats[{index}]: source clip {source_clip!r} is not authored")
        camera = beat.get("cameraIntent", "")
        forbidden = set(capability.get("cameraPolicy", {}).get("reject", []))
        if camera in forbidden:
            if apply_safe_fallbacks and capability.get("cameraPolicy", {}).get("allowBodyReactionClose"):
                beat["cameraIntent"] = "body_reaction_medium_close"
                fallbacks.append({"beatId": beat["id"], "from": camera,
                                  "to": beat["cameraIntent"], "reason": "facial_controls_unavailable"})
            else:
                diagnostics.append(f"$.beats[{index}]: camera {camera!r} violates capability policy")
        if beat.get("type") == "dialogue":
            facial = capability.get("facial") or {}
            if not facial.get("dialogueLipSync"):
                beat["performanceMode"] = "voiceover_body_acting"
                beat["lipSyncMode"] = "none"
                fallbacks.append({
                    "beatId": beat["id"], "from": "character_lip_sync",
                    "to": "voiceover_body_acting", "reason": "dialogue_lip_sync_unavailable",
                })
            else:
                beat["performanceMode"] = "facial_dialogue"
                beat["lipSyncMode"] = "viseme"
    if diagnostics:
        raise OutputValidationError("Storyboard failed timing/capability validation", diagnostics)
    board["beats"] = beats
    return board, fallbacks
