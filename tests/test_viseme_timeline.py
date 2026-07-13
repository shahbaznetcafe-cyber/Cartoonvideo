import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import viseme_maps
import viseme_timeline
import voice_engine
import character_library


class VisemeMappingTests(unittest.TestCase):
    def test_english_phoneme_to_viseme_mapping(self):
        phonemes = viseme_maps.token_to_phonemes("think", "english")
        self.assertEqual(phonemes, ["TH", "I", "NN", "KK"])
        self.assertEqual(viseme_maps.phonemes_to_visemes(phonemes), [
            "viseme_TH", "viseme_I", "viseme_nn", "viseme_kk",
        ])

    def test_roman_urdu_and_urdu_fallbacks(self):
        self.assertEqual(viseme_maps.token_to_phonemes("khana", "roman_urdu"),
                         ["KK", "AA", "NN", "AA"])
        self.assertEqual(viseme_maps.token_to_phonemes("پیار", "urdu"),
                         ["PP", "I", "AA", "RR"])
        self.assertEqual(viseme_maps.normalize_language(None, "aap ka kya hai"),
                         "roman_urdu")
        self.assertEqual(viseme_maps.normalize_language(None, "یہ کیا ہے"), "urdu")
        self.assertEqual(viseme_maps.normalize_language(None, "hello world"), "english")


class VisemeTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audio = Path(self.temp.name, "voice.mp3")
        self.audio.write_bytes(b"deterministic fake audio" * 40)

    def generate(self, **overrides):
        args = {
            "dialogue_text": "pa ma",
            "audio_file": self.audio,
            "word_timestamps": [
                {"t": 0.10, "d": 0.25, "w": "pa"},
                {"t": 0.90, "d": 0.25, "w": "ma"},
            ],
            "language": "english",
            "fps": 20,
            "duration": 1.5,
            "use_audio_silence_gate": False,
        }
        args.update(overrides)
        return viseme_timeline.generate_viseme_timeline(**args)

    def test_output_is_frame_accurate_and_deterministic(self):
        first = self.generate()
        second = self.generate()
        self.assertEqual(first, second)
        self.assertEqual(first["frame_count"], 30)
        self.assertEqual(first["fps"], 20)
        self.assertTrue(all(event["start_frame"] < event["end_frame"]
                            for event in first["events"]))
        self.assertTrue(all(event["start"] == event["start_frame"] / 20
                            for event in first["events"]))

    def test_silence_closes_mouth_and_boundaries_are_closed(self):
        report = self.generate()
        self.assertEqual(report["frames"][0]["weights"], {"viseme_sil": 1.0})
        self.assertEqual(report["frames"][-1]["weights"], {"viseme_sil": 1.0})
        middle_gap = report["frames"][12]
        self.assertEqual(middle_gap["dominant"], "viseme_sil")
        mouth_total = sum(value for name, value in middle_gap["weights"].items()
                          if name != "viseme_sil")
        self.assertLess(mouth_total, 0.02)

    def test_attack_release_and_coarticulation_are_smoothed(self):
        report = self.generate()
        onset = report["frames"][2]["weights"]
        self.assertIn("viseme_sil", onset)
        self.assertTrue(any(name != "viseme_sil" for name in onset))
        blended = [frame for frame in report["frames"]
                   if len([name for name in frame["weights"] if name != "viseme_sil"]) >= 2]
        self.assertTrue(blended)
        for frame in report["frames"]:
            self.assertAlmostEqual(sum(frame["weights"].values()), 1.0, places=3)

    def test_text_fallback_works_without_word_timestamps(self):
        report = self.generate(dialogue_text="hello دنیا", word_timestamps=None,
                               language=None)
        self.assertEqual(report["timestamp_source"], "text_fallback")
        self.assertTrue(report["events"])
        self.assertEqual(report["language"], "urdu")

    def test_cache_is_keyed_by_audio_hash_and_request(self):
        cache = Path(self.temp.name, "cache")
        kwargs = dict(
            dialogue_text="hello", audio_file=self.audio, cache_dir=cache,
            language="english", fps=24, duration=1.0,
            use_audio_silence_gate=False,
        )
        first, first_path, first_hit = viseme_timeline.cached_viseme_timeline(**kwargs)
        second, second_path, second_hit = viseme_timeline.cached_viseme_timeline(**kwargs)
        self.assertFalse(first_hit)
        self.assertTrue(second_hit)
        self.assertEqual(first, second)
        self.assertEqual(first_path, second_path)
        self.assertTrue(Path(first_path).is_file())

        changed, changed_path, changed_hit = viseme_timeline.cached_viseme_timeline(
            **{**kwargs, "dialogue_text": "changed"})
        self.assertFalse(changed_hit)
        self.assertNotEqual(first_path, changed_path)
        self.assertNotEqual(first["request_sha256"], changed["request_sha256"])

        self.audio.write_bytes(b"new audio content" * 40)
        _, audio_path, audio_hit = viseme_timeline.cached_viseme_timeline(**kwargs)
        self.assertFalse(audio_hit)
        self.assertNotEqual(first_path, audio_path)

    def test_provider_neutral_timestamp_shapes_are_accepted(self):
        report = self.generate(word_timestamps={
            "level": "provider_words",
            "items": [{"start": 0.2, "end": 0.6, "text": "face"}],
        })
        self.assertEqual(report["timestamp_source"], "provider_words")
        self.assertTrue(report["events"])

    def test_audio_gate_closes_mouth_inside_a_timestamp_span(self):
        mask = [False] * 30
        mask[5:10] = [True] * 5
        with mock.patch.object(viseme_timeline, "_energy_speech_mask", return_value=mask):
            report = self.generate(
                dialogue_text="speaking",
                word_timestamps=[{"t": 0.0, "d": 1.5, "w": "speaking"}],
                use_audio_silence_gate=True,
            )
        self.assertEqual(report["frames"][18]["dominant"], "viseme_sil")
        self.assertTrue(report["settings"]["audio_silence_gate"])


class VoiceEngineVisemeIntegrationTests(unittest.TestCase):
    def _parsed(self):
        return {
            "language": "english",
            "characters": [{"id": "hero", "gender": "male", "voice": "en-US-GuyNeural"}],
            "scenes": [{
                "id": 1,
                "lines": [{"speaker": "hero", "text": "Hello", "emotion": "happy"}],
            }],
        }

    def test_voice_timeline_references_cached_viseme_json(self):
        with tempfile.TemporaryDirectory() as project:
            voices = Path(project, "voices")
            voices.mkdir()
            Path(voices, "s1_l1.mp3").write_bytes(b"audio" * 200)
            expected = str(Path(project, "visemes", "hash.visemes.json"))
            with (mock.patch.object(voice_engine, "_duration", return_value=1.25),
                  mock.patch.object(character_library, "find_for", return_value=None),
                  mock.patch.object(viseme_timeline, "cached_viseme_timeline",
                                    return_value=({}, expected, False))):
                timeline = voice_engine.generate_voices(self._parsed(), project)
            self.assertEqual(timeline[0]["visemes"], os.path.relpath(expected, project))
            self.assertEqual(timeline[0]["viseme_schema"], 1)
            self.assertEqual(timeline[0]["audio"], os.path.join("voices", "s1_l1.mp3"))

    def test_viseme_failure_preserves_legacy_voice_timeline(self):
        with tempfile.TemporaryDirectory() as project:
            voices = Path(project, "voices")
            voices.mkdir()
            Path(voices, "s1_l1.mp3").write_bytes(b"audio" * 200)
            with (mock.patch.object(voice_engine, "_duration", return_value=1.25),
                  mock.patch.object(character_library, "find_for", return_value=None),
                  mock.patch.object(viseme_timeline, "cached_viseme_timeline",
                                    side_effect=RuntimeError("test failure"))):
                timeline = voice_engine.generate_voices(self._parsed(), project)
            self.assertNotIn("visemes", timeline[0])
            self.assertEqual(timeline[0]["duration"], 1.25)


if __name__ == "__main__":
    unittest.main()
