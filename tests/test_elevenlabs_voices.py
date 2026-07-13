import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
import build
import config
import providers


class _Response:
    def __init__(self, payload=None, content=b"audio" * 200):
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class ElevenLabsVoiceTests(unittest.TestCase):
    def setUp(self):
        providers._ELEVEN_VOICE_CACHE.update(at=0.0, payload=None)

    def test_story_and_child_voices_are_ranked_before_generic_voices(self):
        voices = providers._format_elevenlabs_voices([
            {"voice_id": "generic1234567890123", "name": "Office Voice",
             "labels": {"use_case": "conversational"}},
            {"voice_id": "story12345678901234", "name": "Maya",
             "description": "Young, playful children storytelling narrator",
             "labels": {"gender": "female", "age": "young"}},
        ])
        self.assertEqual(voices[0]["name"], "Maya")
        self.assertTrue(voices[0]["recommended"])
        self.assertFalse(voices[1]["recommended"])

    def test_account_voice_endpoint_is_paginated_sanitized_and_cached(self):
        payload = {"voices": [{
            "voice_id": "story12345678901234", "name": "Story Kid",
            "description": "Warm child narrator", "category": "premade",
            "labels": {"age": "young", "gender": "female"},
        }], "has_more": False, "next_page_token": None}
        with (mock.patch.object(providers, "_eleven_key", return_value="test-key"),
              mock.patch.object(providers.requests, "get", return_value=_Response(payload)) as get):
            first = providers.elevenlabs_voice_options(force=True)
            second = providers.elevenlabs_voice_options()
        self.assertEqual(first, second)
        self.assertEqual(first["recommended_count"], 1)
        self.assertEqual(first["voices"][0]["voice_id"], "story12345678901234")
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.args[0], "https://api.elevenlabs.io/v2/voices")
        self.assertEqual(get.call_args.kwargs["headers"], {"xi-api-key": "test-key"})
        self.assertEqual(get.call_args.kwargs["params"]["page_size"], 100)

    def test_selected_voice_id_and_urdu_capable_model_reach_synthesis(self):
        old_voice, old_model = config.ELEVENLABS_VOICE_ID, config.ELEVENLABS_MODEL
        try:
            config.ELEVENLABS_VOICE_ID = "ABCDEF1234567890abcd"
            config.ELEVENLABS_MODEL = "eleven_v3"
            with tempfile.TemporaryDirectory() as directory, \
                    mock.patch.object(providers, "_eleven_key", return_value="test-key"), \
                    mock.patch.object(providers.requests, "post", return_value=_Response()) as post:
                output = str(Path(directory, "voice.mp3"))
                providers._tts_eleven("Urdu story", "ur-PK-AsadNeural", output,
                                      "+0%", "+0Hz", "+0%")
                self.assertGreater(Path(output).stat().st_size, 500)
            self.assertTrue(post.call_args.args[0].endswith("/ABCDEF1234567890abcd"))
            self.assertEqual(post.call_args.kwargs["json"]["model_id"], "eleven_v3")
        finally:
            config.ELEVENLABS_VOICE_ID, config.ELEVENLABS_MODEL = old_voice, old_model

    def test_ui_setting_persists_selected_elevenlabs_voice(self):
        old_provider, old_voice = config.TTS_PROVIDER, config.ELEVENLABS_VOICE_ID
        try:
            build.apply_settings({"tts_provider": "elevenlabs",
                                  "elevenlabs_voice_id": "ABCDEF1234567890abcd"})
            self.assertEqual(config.TTS_PROVIDER, "elevenlabs")
            self.assertEqual(config.ELEVENLABS_VOICE_ID, "ABCDEF1234567890abcd")
        finally:
            config.TTS_PROVIDER, config.ELEVENLABS_VOICE_ID = old_provider, old_voice

    def test_flask_route_returns_sanitized_voice_payload(self):
        payload = {"available": True, "voices": [], "recommended_count": 0,
                   "selected": "", "model": "eleven_v3"}
        with mock.patch.object(providers, "elevenlabs_voice_options", return_value=payload):
            response = app_module.app.test_client().get("/api/voices/elevenlabs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), payload)


if __name__ == "__main__":
    unittest.main()
