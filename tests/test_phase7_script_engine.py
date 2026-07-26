import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import config
import providers
import runware_client
import story_parser
from app import app
from script_engine.cache import RequestCache
from script_engine.engine import GenerationCancelled, StructuredTextEngine
from script_engine.pipeline import ScriptPipeline
from script_engine.providers import (
    AnimationPlanningProvider, DialogueGenerationProvider,
    ScriptEnhancementProvider, StoryGenerationProvider,
    TextParserProvider, TranslationProvider,
)
from script_engine.registry import ModelRegistry, TaskRouter
from script_engine.validation import (
    OutputValidationError, extract_json, load_schema, require_valid,
    validate_parsed_story, validate_storyboard,
)


PARSED_STORY = {
    "schemaVersion": 1,
    "title": "جنگل کا صندوق",
    "language": "urdu",
    "characters": [{"id": "hero", "name": "علی", "role": "بہادر بچہ",
                    "voiceNotes": "نرم مگر پراعتماد", "capabilityId": "quaternius_adventurer"}],
    "scenes": [{
        "id": "scene_1", "location": "جنگل کا راستہ", "timeOfDay": "day",
        "characters": ["hero"], "estimatedDuration": 4.0,
        "continuityReferences": [],
        "elements": [
            {"type": "narration", "speaker": "narrator", "text": "علی راستے پر چل رہا تھا۔",
             "language": "urdu", "emotion": "neutral", "physicalAction": None,
             "actionTarget": None, "prop": None, "entranceExit": "none",
             "cameraIntent": "establishing_wide", "soundCue": None,
             "environmentalEvent": "wind", "estimatedDuration": 2.0,
             "continuityReferences": []},
            {"type": "dialogue", "speaker": "hero", "text": "یہ صندوق یہاں کیسے آیا؟",
             "language": "urdu", "emotion": "curious", "physicalAction": "points",
             "actionTarget": "box", "prop": "box", "entranceExit": "none",
             "cameraIntent": "medium", "soundCue": None,
             "environmentalEvent": None, "estimatedDuration": 2.0,
             "continuityReferences": []}
        ]
    }]
}


def simple_schema():
    return {"$id": "test://result-v1", "type": "object", "required": ["value"],
            "properties": {"value": {"type": "string", "minLength": 1}}}


class FakeOpenAI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, payload, **kwargs):
        self.calls.append((payload, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return dict({"transport": "openai_compatible", "attempts": 1,
                     "usage": {"total_tokens": 12}, "cost": 0.0001,
                     "finishReason": "stop"}, **response)


class FakeNative:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, tasks, **kwargs):
        self.calls.append((tasks, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        item = dict({"taskUUID": tasks[0]["taskUUID"], "finishReason": "stop",
                     "usage": {"totalTokens": 12}, "cost": 0.0001}, **response)
        return {"data": [item], "attempts": 1}


class Phase7RegistryTests(unittest.TestCase):
    def test_verified_registry_separates_ui_ids_from_real_air_ids(self):
        registry = ModelRegistry()
        expected = {
            "deepseek-v4-pro": "deepseek:v4@pro",
            "zai-glm-5-1": "zai:glm@5.1",
            "openai-gpt-5-4-mini": "openai:gpt@5.4-mini",
            "google-gemini-3-5-flash": "google:gemini@3.5-flash",
        }
        for legacy, air in expected.items():
            self.assertEqual(registry.resolve(legacy)["runwareAir"], air)
        self.assertTrue(registry.data["verification"]["credentialsStored"] is False)

    def test_task_routes_are_editable_and_not_bound_to_one_family(self):
        router = TaskRouter()
        families = {router.route(task)["models"][0]["family"] for task in router.task_names}
        self.assertGreaterEqual(len(families), 4)
        self.assertTrue(router.data["editable"])
        self.assertEqual(router.data["maxProviderFallbacks"], 1)
        self.assertEqual(router.data["maxTransportRetries"], 1)

    def test_existing_provider_catalog_keeps_legacy_ids_but_exposes_air(self):
        entry = next(item for item in providers.llm_model_options()
                     if item["model"] == "deepseek-v4-pro")
        self.assertEqual(entry["runware_air"], "deepseek:v4@pro")
        self.assertTrue(entry["verified"])
        old = config.LLM_MODEL
        try:
            config.LLM_MODEL = "deepseek:v4@pro"
            self.assertEqual(providers._selected_model("runware", config.TEXT_MODEL),
                             "deepseek-v4-pro")
        finally:
            config.LLM_MODEL = old

    def test_normalized_provider_interfaces_share_engine_contract(self):
        tasks = [TextParserProvider.task, StoryGenerationProvider.task,
                 DialogueGenerationProvider.task, ScriptEnhancementProvider.task,
                 TranslationProvider.task, AnimationPlanningProvider.task]
        self.assertEqual(tasks, ["FAST_PARSER", "STORY_ARCHITECT", "DIALOGUE_WRITER",
                                 "SCRIPT_DOCTOR", "TRANSLATION", "ANIMATION_PLANNER"])


class Phase7ValidationTests(unittest.TestCase):
    def test_code_fenced_json_is_parsed_defensively(self):
        self.assertEqual(extract_json("```json\n{\"value\":\"ok\"}\n```"), {"value": "ok"})
        with self.assertRaises(OutputValidationError):
            extract_json("no structured value")

    def test_missing_mandatory_fields_are_not_fabricated(self):
        with self.assertRaises(OutputValidationError) as context:
            require_valid({}, simple_schema())
        self.assertIn("mandatory field is missing", " ".join(context.exception.diagnostics))

    def test_urdu_parser_schema_and_semantics_pass(self):
        self.assertEqual(validate_parsed_story(PARSED_STORY)["language"], "urdu")

    def test_storyboard_rejects_unregistered_clip_and_safely_routes_camera(self):
        board = {
            "schemaVersion": 1, "title": "Box", "fps": 24, "durationSeconds": 1,
            "characters": [{"id": "hero", "capabilityId": "quaternius_adventurer",
                            "capabilityTier": "SKELETAL_INTERACTIVE"}],
            "beats": [{"id": "b1", "startFrame": 0, "endFrame": 24,
                       "type": "dialogue", "characterId": "hero",
                       "animationAction": "offscreen_hold", "sourceClip": "Idle",
                       "fallbackAction": None, "target": None,
                       "cameraIntent": "dialogue_close_up", "dialogueText": "Ruko!",
                       "soundCue": None, "environmentalEvent": None}]
        }
        validated, fallbacks = validate_storyboard(board)
        self.assertEqual(validated["beats"][0]["cameraIntent"], "body_reaction_medium_close")
        self.assertEqual(fallbacks[0]["reason"], "facial_controls_unavailable")
        self.assertEqual(validated["beats"][0]["performanceMode"], "voiceover_body_acting")
        self.assertEqual(validated["beats"][0]["lipSyncMode"], "none")
        self.assertEqual(fallbacks[1]["reason"], "dialogue_lip_sync_unavailable")
        board["beats"][0]["sourceClip"] = "Invented_Wave"
        with self.assertRaises(OutputValidationError):
            validate_storyboard(board)


class Phase7ReliabilityTests(unittest.TestCase):
    def make_engine(self, temp, native, openai):
        return StructuredTextEngine(cache=RequestCache(Path(temp) / "cache"),
                                    native_transport=native, openai_transport=openai)

    def test_cache_records_hit_without_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            native = FakeNative([{"text": '{"value":"ok"}'}])
            engine = self.make_engine(temp, native, FakeOpenAI([]))
            first = engine.generate("FAST_PARSER", "content", schema=simple_schema())
            second = engine.generate("FAST_PARSER", "content", schema=simple_schema())
            self.assertEqual(first["metadata"]["cache"], "miss")
            self.assertEqual(second["metadata"]["cache"], "hit")
            cache_text = next((Path(temp) / "cache").glob("*.json")).read_text(encoding="utf-8")
            self.assertNotIn(config.RUNWARE_API_KEY, cache_text)

    def test_controlled_model_fallback_is_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            native = FakeNative([runware_client.RunwareError("rate limited", retryable=True)])
            openai = FakeOpenAI([{"text": '{"value":"fallback"}'}])
            engine = self.make_engine(temp, native, openai)
            result = engine.generate("FAST_PARSER", "content", schema=simple_schema(),
                                     use_cache=False)
            self.assertTrue(result["metadata"]["fallbackUsed"])
            self.assertEqual(result["metadata"]["modelAir"], "deepseek:v4@flash")
            self.assertEqual(len(result["diagnostics"]), 1)

    def test_malformed_output_gets_one_repair_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            openai = FakeOpenAI([{"text": "not json"}, {"text": '{"value":"repaired"}'}])
            engine = self.make_engine(temp, FakeNative([]), openai)
            result = engine.generate("FAST_PARSER", "content", schema=simple_schema(),
                                     requested_model="deepseek-v4-flash", allow_fallback=False,
                                     use_cache=False)
            self.assertEqual(result["output"]["value"], "repaired")
            self.assertEqual(result["metadata"]["repairCount"], 1)
            self.assertEqual(len(openai.calls), 2)

    def test_cancellation_prevents_billable_request(self):
        with tempfile.TemporaryDirectory() as temp:
            event = threading.Event(); event.set()
            native = FakeNative([])
            engine = self.make_engine(temp, native, FakeOpenAI([]))
            with self.assertRaises(GenerationCancelled):
                engine.generate("FAST_PARSER", "content", schema=simple_schema(),
                                cancel_event=event, use_cache=False)
            self.assertEqual(native.calls, [])

    def test_transport_retry_is_bounded_and_error_redacts_key(self):
        class Response:
            status_code = 429
            text = "Authorization: Bearer " + config.RUNWARE_API_KEY
            headers = {}
            def json(self): return {}
        class Session:
            def __init__(self): self.calls = 0
            def post(self, *args, **kwargs): self.calls += 1; return Response()
        session = Session()
        with self.assertRaises(runware_client.RunwareError) as context:
            runware_client.chat_completion_detailed(
                {"model": "deepseek:v4@flash", "messages": [{"role": "user", "content": "x"}]},
                retries=1, session=session)
        self.assertEqual(session.calls, 2)
        self.assertNotIn(config.RUNWARE_API_KEY, str(context.exception))
        self.assertIn("[REDACTED]", str(context.exception))

    def test_stream_cancellation_closes_the_response(self):
        event = threading.Event()

        class Response:
            status_code = 200
            text = ""
            closed = False

            def iter_lines(self, decode_unicode=True):
                yield 'data: {"choices":[{"delta":{"content":"first"}}]}'
                event.set()
                yield 'data: {"choices":[{"delta":{"content":"second"}}]}'

            def close(self):
                self.closed = True

        response = Response()

        class Session:
            def post(self, *args, **kwargs):
                return response

        stream = runware_client.stream_chat_completion(
            {"model": "deepseek:v4@flash", "messages": []},
            cancel_event=event, session=Session())
        self.assertEqual(next(stream), "first")
        with self.assertRaises(runware_client.RunwareCancelled):
            next(stream)
        self.assertTrue(response.closed)

    def test_native_json_schema_envelope_is_valid_runware_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            native = FakeNative([{"text": '{"value":"ok"}'}])
            engine = self.make_engine(temp, native, FakeOpenAI([]))
            engine.generate("FAST_PARSER", "content", schema=simple_schema(),
                            requested_model="google-gemini-3-5-flash",
                            allow_fallback=False, use_cache=False)
            task = native.calls[0][0][0]
            self.assertEqual(task["jsonSchema"]["schema"], simple_schema())
            self.assertFalse(task["jsonSchema"]["strict"])


class Phase7ApplicationContractTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_options_are_backend_safe_and_routes_exist(self):
        payload = self.client.get("/api/script-engine/options").get_json()
        self.assertTrue(payload["credentialsBackendOnly"])
        serialized = json.dumps(payload)
        self.assertNotIn(config.RUNWARE_API_KEY, serialized)
        self.assertIn("script_doctor", payload["stages"])
        self.assertIn("natural_urdu", payload["scriptDoctorModes"])

    def test_animation_planning_requires_approved_input(self):
        response = self.client.post("/api/script-engine/start", json={
            "stage": "animation_plan", "content": "approved-looking text",
            "language": "roman_urdu", "model": "runware.google.gemini.3.5.flash",
        })
        self.assertEqual(response.status_code, 409)

    def test_existing_structured_parser_behavior_remains_available(self):
        parsed = story_parser.parse_script("[Scene: Park]\nAam: Salam dost!")
        self.assertEqual(parsed["scenes"][0]["lines"][0]["speaker"], "aam")

    def test_frontend_exposes_explicit_paid_comparison_and_stage_controls(self):
        template = Path("templates/index.html").read_text(encoding="utf-8")
        javascript = Path("static/js/studio.js").read_text(encoding="utf-8")
        for element_id in ("scriptEngineStage", "scriptEngineModel",
                           "scriptEngineCompare", "scriptEngineComparisonModel",
                           "scriptEngineCancelBtn", "scriptEngineApproveBtn"):
            self.assertIn(f'id="{element_id}"', template)
        self.assertIn("/api/script-engine/cancel/", javascript)
        self.assertIn("approved_input:SCRIPT_ENGINE_APPROVED", javascript)


if __name__ == "__main__":
    unittest.main()
