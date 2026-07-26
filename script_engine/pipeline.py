"""Reviewable, stage-by-stage story and animation planning pipeline."""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path

import config

from .engine import StructuredTextEngine
from .prompts import SCRIPT_DOCTOR_MODES
from .validation import (load_schema, validate_parsed_story,
                         validate_storyboard)


STAGES = (
    "story_idea", "story_outline", "character_profiles", "scene_breakdown",
    "character_dialogue", "script_doctor", "visual_story_beats",
    "animation_plan", "storyboard",
)

STAGE_TASKS = {
    "story_idea": "STORY_ARCHITECT",
    "story_outline": "STORY_ARCHITECT",
    "character_profiles": "STORY_ARCHITECT",
    "scene_breakdown": "FAST_PARSER",
    "character_dialogue": "DIALOGUE_WRITER",
    "script_doctor": "SCRIPT_DOCTOR",
    "visual_story_beats": "FAST_PARSER",
    "animation_plan": "ANIMATION_PLANNER",
    "storyboard": "ANIMATION_PLANNER",
}


def _object_schema(title, required, properties):
    return {"$id": f"sbz://schemas/{title}-v1", "title": title, "type": "object",
            "required": required, "properties": properties}


STRING = {"type": "string", "minLength": 1}
STAGE_SCHEMAS = {
    "story_idea": _object_schema("story-idea", ["idea", "language", "genre", "audience"], {
        "idea": STRING, "language": STRING, "genre": STRING, "audience": STRING,
        "culturalSetting": {"type": "string"}, "coreMessage": {"type": "string"},
    }),
    "story_outline": _object_schema("story-outline", ["title", "logline", "beats"], {
        "title": STRING, "logline": STRING,
        "beats": {"type": "array", "minItems": 3, "items": STRING},
        "ending": {"type": "string"},
    }),
    "character_profiles": _object_schema("character-profiles", ["characters"], {
        "characters": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["id", "name", "role", "voice"],
            "properties": {"id": STRING, "name": STRING, "role": STRING,
                           "voice": STRING, "facts": {"type": "array", "items": STRING}}
        }}
    }),
    "scene_breakdown": load_schema("parsed_story.schema.json"),
    "character_dialogue": _object_schema("character-dialogue", ["language", "scenes"], {
        "language": STRING,
        "scenes": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["id", "lines"],
            "properties": {"id": STRING, "lines": {"type": "array", "minItems": 1,
                "items": {"type": "object", "required": ["speaker", "text", "emotion"],
                    "properties": {"speaker": STRING, "text": STRING, "emotion": STRING,
                                   "action": {"type": "string"}}}}}
        }}
    }),
    "script_doctor": _object_schema("script-doctor", ["script", "language", "changes"], {
        "script": STRING, "language": STRING,
        "changes": {"type": "array", "items": STRING},
        "preservedFacts": {"type": "array", "items": STRING},
    }),
    "visual_story_beats": _object_schema("visual-story-beats", ["beats"], {
        "beats": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["id", "purpose", "action", "cameraIntent"],
            "properties": {"id": STRING, "purpose": STRING, "action": STRING,
                           "cameraIntent": STRING, "prop": {"type": ["string", "null"]},
                           "environmentEvent": {"type": ["string", "null"]}}
        }}
    }),
    "animation_plan": load_schema("storyboard.schema.json"),
    "storyboard": load_schema("storyboard.schema.json"),
}


class ScriptPipeline:
    def __init__(self, engine=None):
        self.engine = engine or StructuredTextEngine()

    @staticmethod
    def _project_stage_dir(project):
        if not project:
            return None
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(project))[:100]
        root = Path(config.PROJECTS_DIR).resolve()
        path = (root / safe / "script_pipeline").resolve()
        if root not in path.parents:
            raise ValueError("Invalid project path")
        return path

    @staticmethod
    def capability_summary(performance_only=False):
        if performance_only:
            import character_performance
            return character_performance.registry_performance_summary()
        path = Path(config.BASE_DIR) / "assets" / "characters" / "capability_registry.json"
        if not path.exists():
            return {"characters": {}}
        data = json.loads(path.read_text(encoding="utf-8"))
        summary = {}
        for character_id, character in data.get("characters", {}).items():
            summary[character_id] = {
                "tier": character.get("tier"),
                "authoredClips": sorted((character.get("authoredClips") or {}).keys()),
                "storyActionClips": character.get("storyActionClips") or {},
                "cameraPolicy": character.get("cameraPolicy") or {},
                "interaction": character.get("interaction") or {},
                "facial": character.get("facial") or {},
                "limitations": character.get("limitations") or [],
            }
        return {"characters": summary}

    @staticmethod
    def _semantic_validator(stage):
        if stage == "scene_breakdown":
            return validate_parsed_story
        if stage in {"animation_plan", "storyboard"}:
            def validate(value):
                board, fallbacks = validate_storyboard(value)
                if fallbacks:
                    board["safeFallbacks"] = fallbacks
                return board
            return validate
        return None

    def run_stage(self, stage, content, *, language="roman_urdu", mode=None,
                  requested_model=None, allow_fallback=True, use_cache=True,
                  cancel_event=None, project=None):
        if stage not in STAGES:
            raise ValueError(f"Unsupported pipeline stage: {stage}")
        if stage == "script_doctor" and mode not in SCRIPT_DOCTOR_MODES:
            raise ValueError("A valid Script Doctor mode is required")
        task = STAGE_TASKS[stage]
        result = self.engine.generate(
            task, content, language=language, schema=STAGE_SCHEMAS[stage], mode=mode,
            requested_model=requested_model, allow_fallback=allow_fallback,
            use_cache=use_cache, cancel_event=cancel_event,
            capability_summary=(
                self.capability_summary() if task == "ANIMATION_PLANNER" else
                self.capability_summary(performance_only=True)
                if task in {"DIALOGUE_WRITER", "SCRIPT_DOCTOR"} else None
            ),
            semantic_validator=self._semantic_validator(stage),
            generation_settings={"stage": stage},
        )
        record = {
            "schemaVersion": 1,
            "stage": stage,
            "approved": False,
            "output": result["output"],
            "metadata": result["metadata"],
            "diagnostics": result.get("diagnostics", []),
        }
        stage_dir = self._project_stage_dir(project)
        if stage_dir:
            stage_dir.mkdir(parents=True, exist_ok=True)
            path = stage_dir / f"{STAGES.index(stage) + 1:02d}_{stage}.json"
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, path)
            record["savedAs"] = str(path.relative_to(Path(config.BASE_DIR))).replace("\\", "/")
        return record

    def approve_stage(self, project, stage, edited_output=None):
        stage_dir = self._project_stage_dir(project)
        if not stage_dir or stage not in STAGES:
            raise ValueError("Project and valid stage are required")
        path = stage_dir / f"{STAGES.index(stage) + 1:02d}_{stage}.json"
        if not path.exists():
            raise FileNotFoundError("Pipeline stage has not been generated")
        record = json.loads(path.read_text(encoding="utf-8"))
        if edited_output is not None:
            output = edited_output if isinstance(edited_output, dict) else json.loads(edited_output)
            from .validation import require_valid
            require_valid(output, STAGE_SCHEMAS[stage])
            validator = self._semantic_validator(stage)
            record["output"] = validator(output) if validator else output
            record["editedByUser"] = True
        record["approved"] = True
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
        return record

    def workflow(self, project):
        stage_dir = self._project_stage_dir(project)
        records = []
        if stage_dir and stage_dir.exists():
            for path in sorted(stage_dir.glob("*.json")):
                records.append(json.loads(path.read_text(encoding="utf-8")))
        return {"project": project, "stages": records,
                "availableStages": list(STAGES)}
