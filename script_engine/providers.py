"""Normalized task interfaces sharing the same Runware text engine."""
from __future__ import annotations

from .engine import StructuredTextEngine


class _Provider:
    task = None

    def __init__(self, engine=None):
        self.engine = engine or StructuredTextEngine()

    def generate(self, content, **kwargs):
        return self.engine.generate(self.task, content, **kwargs)


class TextParserProvider(_Provider):
    task = "FAST_PARSER"


class StoryGenerationProvider(_Provider):
    task = "STORY_ARCHITECT"


class DialogueGenerationProvider(_Provider):
    task = "DIALOGUE_WRITER"


class ScriptEnhancementProvider(_Provider):
    task = "SCRIPT_DOCTOR"


class TranslationProvider(_Provider):
    task = "TRANSLATION"


class AnimationPlanningProvider(_Provider):
    task = "ANIMATION_PLANNER"
