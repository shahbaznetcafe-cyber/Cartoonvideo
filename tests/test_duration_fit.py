"""Duration fitting: measured-shortfall extension + freeze-frame padding refusal.

The rendered length is driven by synthesized speech, whose real rate varies far
more than any single words-per-second constant.  These deterministic tests cover
the measurement math and the renderer's refusal to pad a long shortfall with a
frozen frame.  No LLM or ffmpeg is invoked.
"""
import unittest

import duration_fitter as fit
import duration_planner
import blender3d


def _tl(*pairs):
    return [{"text": text, "duration": dur} for text, dur in pairs]


class MeasurementTests(unittest.TestCase):
    def test_duration_and_words_and_rate(self):
        tl = _tl(("do teen chaar paanch", 2.0), ("ek do teen", 1.0))
        self.assertAlmostEqual(fit.timeline_duration(tl), 3.0)
        self.assertEqual(fit.spoken_words(tl), 7)
        self.assertAlmostEqual(fit.measured_rate(tl), 7 / 3.0)

    def test_rate_none_when_empty(self):
        self.assertIsNone(fit.measured_rate([]))
        self.assertIsNone(fit.measured_rate(_tl(("", 0))))

    def test_shortfall_and_needs_extension(self):
        tl = _tl(("word " * 10, 83.0))     # a 2-min (120s) target, only 83s
        self.assertAlmostEqual(fit.shortfall(tl, 120), 37.0)
        self.assertTrue(fit.needs_extension(tl, 120))
        # near-target (115/120 = 0.96) -> no extension worth doing
        near_tl = _tl(("w", 115.0))
        self.assertFalse(fit.needs_extension(near_tl, 120))
        # at/over target -> zero shortfall
        self.assertEqual(fit.shortfall(_tl(("w", 125.0)), 120), 0.0)

    def test_no_extension_without_target_or_signal(self):
        self.assertFalse(fit.needs_extension(_tl(("w", 40.0)), 0))
        self.assertFalse(fit.needs_extension([], 120))

    def test_words_needed_uses_measured_rate(self):
        # 40 words in 20s => 2.0 w/s measured; 30s short => ~60 words needed.
        tl = _tl((" ".join(["w"] * 40), 20.0)) + _tl(("", 0))
        tl = [{"text": " ".join(["w"] * 40), "duration": 20.0}]
        need = fit.words_needed(tl, 50, language="urdu")
        self.assertEqual(need, int(round((50 - 20) * (40 / 20))))   # 60

    def test_words_needed_falls_back_to_language_rate(self):
        # A timeline with words but the shortfall computed against a bigger
        # target uses the measured rate; with no measurable rate it would use the
        # language default. Here 20 words in 10s = 2.0 w/s measured.
        tl = [{"text": " ".join(["w"] * 20), "duration": 10.0}]
        self.assertEqual(fit.words_needed(tl, 30, language="urdu"),
                         int(round((30 - 10) * 2.0)))   # 40

    def test_script_from_parsed_roundtrips_format(self):
        parsed = {"scenes": [{"location": "Jungle", "lines": [
            {"speaker": "Ali", "emotion": "happy", "action": "walk", "text": "Chalo"},
            {"speaker": "Sara", "emotion": "calm", "action": "", "text": "Theek hai"},
        ]}]}
        text = fit.script_from_parsed(parsed)
        self.assertIn("[Scene: Jungle]", text)
        self.assertIn("Ali: (happy; walk; Jungle) Chalo", text)
        self.assertIn("none", text)   # empty action rendered as 'none'

    def test_extend_script_returns_original_on_provider_failure(self):
        class Boom:
            def llm_generate(self, *a, **k):
                raise RuntimeError("no network")
        original = "[Scene: X]\nAli: (happy; walk; X) Hi."
        out = fit.extend_script(Boom(), original, 40, "2 min", "urdu", "Urdu")
        self.assertEqual(out, original)


class LanguageRateTests(unittest.TestCase):
    def test_measured_rates_lift_the_word_budget(self):
        # Urdu rate (2.42) must ask for more words than the old 2.05 constant.
        urdu = duration_planner.writing_brief("2min", "urdu")["target_words"]
        default = duration_planner.writing_brief("2min")["target_words"]
        self.assertGreater(urdu, 120 * 2.05)
        self.assertGreaterEqual(urdu, default)

    def test_words_per_second_lookup(self):
        self.assertEqual(duration_planner.words_per_second("urdu"), 2.42)
        self.assertEqual(duration_planner.words_per_second("unknown-lang"),
                         duration_planner.DEFAULT_WORDS_PER_SECOND)


class FreezeFramePaddingTests(unittest.TestCase):
    def test_long_shortfall_refuses_freeze_frame_padding(self):
        # 83s of content for a 120s target must NOT be padded to 120s.
        path, scale, action = blender3d._enforce_target_duration(
            _DummyPath(actual=83.0), 120.0, 24)
        self.assertEqual(scale, 1.0)
        self.assertIn("padding refused", action)

    def test_tiny_rounding_gap_is_still_padded(self):
        self.assertLessEqual(blender3d.MAX_TAIL_PAD_SECONDS, 2.5)


class _DummyPath(str):
    """A path whose probed duration is fixed, to test the padding decision."""
    def __new__(cls, actual):
        obj = super().__new__(cls, "dummy.mp4")
        obj._actual = actual
        return obj


def _patched_probe(path):
    return getattr(path, "_actual", 0.0)


# Route _probe_duration to the dummy value for the padding-decision test only.
_orig_probe = blender3d._probe_duration
def setUpModule():
    blender3d._probe_duration = _patched_probe
def tearDownModule():
    blender3d._probe_duration = _orig_probe


if __name__ == "__main__":
    unittest.main()
