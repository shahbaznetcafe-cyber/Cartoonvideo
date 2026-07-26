import json
import os
import tempfile
import time
import unittest
from unittest import mock

import app as app_module
import config
import projects_mgr
import providers
import story_parser
import voice_engine


class WorkflowReliabilityTests(unittest.TestCase):
    def test_hindi_emotion_and_supported_action_are_separated(self):
        parsed = story_parser.parse_structured_script(
            "[Scene: सड़क, शाम]\n"
            "आरव: (चौंका हुआ; stand) रुको!\n"
            "मीरा: (डरी हुई; run) जल्दी भागो!"
        )
        lines = parsed["scenes"][0]["lines"]
        self.assertEqual((lines[0]["emotion"], lines[0]["action"]),
                         ("surprised", "stand"))
        self.assertEqual((lines[1]["emotion"], lines[1]["action"]),
                         ("scared", "run"))
        meera = next(item for item in parsed["characters"] if item["name"] == "मीरा")
        self.assertEqual(meera["gender"], "female")

    def test_old_saved_hindi_direction_is_repaired_on_resume(self):
        saved = {"scenes": [{"lines": [{
            "speaker": "aarav", "text": "रुको!", "emotion": "neutral",
            "action": "चौंका हुआ; stand",
        }]}]}
        story_parser.normalize_parsed_directions(saved)
        line = saved["scenes"][0]["lines"][0]
        self.assertEqual((line["emotion"], line["action"]), ("surprised", "stand"))

    def test_job_file_is_atomic_and_stale_running_job_recovers(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.object(config, "PROJECTS_DIR", root):
            project = os.path.join(root, "project-test")
            projects_mgr.save_job(project, job_id="job-1", state="running",
                                  stage="voice", updated_at=time.time() - 500)
            # Force an old heartbeat after save_job's automatic timestamp.
            path = os.path.join(project, "job.json")
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            data["updated_at"] = time.time() - 500
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
            recovered = projects_mgr.recover_stale_jobs(stale_after=90)
            self.assertEqual(recovered, ["project-test"])
            job = projects_mgr.load_job("project-test")
            self.assertEqual(job["state"], "interrupted")
            self.assertIn("Resume", job["message"])
            self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(project)))

    def test_status_endpoint_falls_back_to_durable_job_state(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.object(config, "PROJECTS_DIR", root):
            project = os.path.join(root, "project-durable")
            projects_mgr.save_job(project, job_id="durable-1", project="project-durable",
                                  state="running", stage="voice", i=2, total=5,
                                  message="Voice 3/5", heartbeat_at=time.time())
            app_module.JOBS.pop("durable-1", None)
            response = app_module.app.test_client().get("/api/status/durable-1")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["durable"])
            self.assertEqual((payload["stage"], payload["i"], payload["total"]),
                             ("voice", 2, 5))

    def test_voice_progress_is_visible_before_provider_call(self):
        parsed = {
            "language": "hindi",
            "characters": [{"id": "hero", "name": "Hero", "gender": "male",
                            "voice": "hi-IN-MadhurNeural"}],
            "scenes": [{"id": 1, "location": "road", "lines": [
                {"speaker": "hero", "text": "रुको!", "emotion": "surprised",
                 "action": "stand"}
            ]}],
        }
        events = []

        def synthesize(_text, _voice, path, **_kwargs):
            self.assertTrue(any("via" in message for _, _, message in events))
            with open(path, "wb") as handle:
                handle.write(b"x" * 1000)
            return path

        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(providers, "tts_synthesize", side_effect=synthesize), \
                mock.patch.object(voice_engine, "_duration", return_value=1.0), \
                mock.patch("audiopost.clean_voice", return_value=(0.0, 0.0)), \
                mock.patch.object(voice_engine.viseme_timeline, "cached_viseme_timeline",
                                  return_value=({}, os.path.join(root, "v.json"), False)):
            timeline = voice_engine.generate_voices(
                parsed, root, on_progress=lambda i, total, msg: events.append((i, total, msg)))
        self.assertEqual(len(timeline), 1)
        self.assertIn("Voice queue ready", events[0][2])
        self.assertTrue(any("Voice 1/1" in message for _, _, message in events))

    def test_failed_tts_provider_opens_circuit_and_fallback_continues(self):
        calls = {"google": 0, "edge": 0}

        def google(*_args, **_kwargs):
            calls["google"] += 1
            raise TimeoutError("provider timeout")

        def edge(_text, _voice, path, *_args, **_kwargs):
            calls["edge"] += 1
            with open(path, "wb") as handle:
                handle.write(b"audio")
            return path

        fake = {"google": (lambda: True, google), "edge": (lambda: True, edge)}
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(providers, "_TTS", fake), \
                mock.patch.object(config, "TTS_PROVIDER", "google"), \
                mock.patch.object(config, "TTS_FALLBACK", ["edge"]):
            providers._TTS_CIRCUIT.clear()
            providers.tts_synthesize("one", "voice", os.path.join(root, "one.mp3"))
            providers.tts_synthesize("two", "voice", os.path.join(root, "two.mp3"))
        providers._TTS_CIRCUIT.clear()
        self.assertEqual(calls, {"google": 1, "edge": 2})

    def test_edge_retries_a_transient_line_failure_before_using_fallback(self):
        calls = {"edge": 0}

        def edge(_text, _voice, path, *_args, **_kwargs):
            calls["edge"] += 1
            if calls["edge"] == 1:
                raise TimeoutError("temporary network timeout")
            with open(path, "wb") as handle:
                handle.write(b"audio")
            return path

        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(providers, "_TTS", {"edge": (lambda: True, edge)}), \
                mock.patch.object(config, "TTS_PROVIDER", "edge"), \
                mock.patch.object(config, "TTS_FALLBACK", []), \
                mock.patch.object(providers.time, "sleep"):
            providers._TTS_CIRCUIT.clear()
            providers.tts_synthesize("one", "voice", os.path.join(root, "one.mp3"))
        providers._TTS_CIRCUIT.clear()
        self.assertEqual(calls["edge"], 2)

    def test_rejected_elevenlabs_credentials_are_not_retried_for_every_line(self):
        calls = {"elevenlabs": 0, "edge": 0}

        def eleven(*_args, **_kwargs):
            calls["elevenlabs"] += 1
            error = RuntimeError("401 Unauthorized")
            error.response = type("Response", (), {"status_code": 401})()
            raise error

        def edge(_text, _voice, path, *_args, **_kwargs):
            calls["edge"] += 1
            with open(path, "wb") as handle:
                handle.write(b"audio")
            return path

        fake = {"elevenlabs": (lambda: True, eleven), "edge": (lambda: True, edge)}
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(providers, "_TTS", fake), \
                mock.patch.object(config, "TTS_PROVIDER", "elevenlabs"), \
                mock.patch.object(config, "TTS_FALLBACK", ["edge"]):
            providers._TTS_CIRCUIT.clear()
            providers._TTS_DISABLED.clear()
            providers.tts_synthesize("one", "voice", os.path.join(root, "one.mp3"))
            providers.tts_synthesize("two", "voice", os.path.join(root, "two.mp3"))
        providers._TTS_CIRCUIT.clear()
        providers._TTS_DISABLED.clear()
        self.assertEqual(calls, {"elevenlabs": 1, "edge": 2})

if __name__ == "__main__":
    unittest.main()
