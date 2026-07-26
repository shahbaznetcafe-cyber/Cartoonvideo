import base64
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
import build
import config
import dialogue_style
import providers


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DialogueStyleTests(unittest.TestCase):
    def test_hinglish_policy_is_explicit_and_youtube_ready(self):
        policy = dialogue_style.full_prompt_policy("hinglish")
        self.assertIn("85%", policy)
        self.assertIn("15%", policy)
        self.assertIn("YOUTUBE", policy)
        self.assertIn("punctuation", policy.lower())

    def test_spoken_punctuation_adds_closure_without_rewriting_words(self):
        self.assertEqual(
            dialogue_style.normalize_spoken_punctuation("Aray wah ye kamaal hai", "hinglish"),
            "Aray wah ye kamaal hai.",
        )
        self.assertEqual(
            dialogue_style.normalize_spoken_punctuation("Kya tum ready ho?", "hinglish"),
            "Kya tum ready ho?",
        )


class VoiceAndModelTests(unittest.TestCase):
    def test_hindi_language_uses_hindi_voices(self):
        voices = config.voice_map_for_language("hinglish")
        self.assertTrue(voices["male"].startswith("hi-IN-"))
        self.assertTrue(voices["female"].startswith("hi-IN-"))

    def test_requested_and_low_cost_models_are_exposed(self):
        catalog = {(item["provider"], item["model"]) for item in providers.llm_model_options()}
        self.assertIn(("runware", "deepseek-v4-pro"), catalog)
        self.assertIn(("runware", "zai-glm-5-1"), catalog)
        self.assertIn(("runware", "openai-gpt-5-4-mini"), catalog)
        self.assertIn(("runware", "google-gemini-3-5-flash"), catalog)
        self.assertEqual({item["provider"] for item in providers.llm_model_options()}, {"runware"})

    def test_legacy_runware_model_id_is_migrated(self):
        old_model = config.LLM_MODEL
        try:
            config.LLM_MODEL = "openai:gpt@5.4-mini"
            self.assertEqual(
                providers._selected_model("runware", config.TEXT_MODEL),
                "openai-gpt-5-4-mini",
            )
        finally:
            config.LLM_MODEL = old_model

    def test_voice_speed_is_clamped_and_applied_to_edge_rate(self):
        self.assertEqual(providers._edge_rate("+6%", 0.9), "-4%")
        self.assertEqual(providers._edge_rate("+0%", 5), "+20%")
        old = config.VOICE_SPEED
        try:
            build.apply_settings({"voice_speed": 9})
            self.assertEqual(config.VOICE_SPEED, 1.2)
        finally:
            config.VOICE_SPEED = old

    def test_google_hindi_synthesis_decodes_audio_and_sends_speed(self):
        old_voice = config.GOOGLE_TTS_VOICE
        try:
            config.GOOGLE_TTS_VOICE = "hi-IN-Standard-B"
            payload = {"audioContent": base64.b64encode(b"mp3-data").decode("ascii")}
            with tempfile.TemporaryDirectory() as directory, \
                    mock.patch.object(providers, "_google_tts_key", return_value="test-key"), \
                    mock.patch.object(providers.requests, "post", return_value=_Response(payload)) as post:
                output = Path(directory, "voice.mp3")
                providers._tts_google("Namaste, dost!", "", str(output), "+0%", "+0Hz", "+0%", 0.9)
                self.assertEqual(output.read_bytes(), b"mp3-data")
            request_json = post.call_args.kwargs["json"]
            self.assertEqual(request_json["voice"]["languageCode"], "hi-IN")
            self.assertEqual(request_json["audioConfig"]["speakingRate"], 0.9)
        finally:
            config.GOOGLE_TTS_VOICE = old_voice

    def test_options_endpoint_contains_voice_and_model_catalogs(self):
        response = app_module.app.test_client().get("/api/options")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["edge_voices"])
        self.assertTrue(payload["google_voices"])
        self.assertTrue(payload["llm_models"])


if __name__ == "__main__":
    unittest.main()
