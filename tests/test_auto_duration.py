""""Auto" duration: match the preset to whatever the script actually is.

Before this, "Target video duration" only offered fixed presets, so a script
that didn't match the selected preset showed a mismatch warning instead of
just working. "Auto" estimates the script's own natural spoken length and
resolves to the closest preset -- no forced mismatch possible by definition.
"""
import unittest
from pathlib import Path

import duration_planner as dp


def _script(word_count, dialogue_lines=1):
    words_per_line = max(1, word_count // dialogue_lines)
    lines = [f"Ali: (happy) " + " ".join(["word"] * words_per_line)
             for _ in range(dialogue_lines)]
    return "\n".join(lines)


class ResolveDurationTests(unittest.TestCase):
    def test_is_auto_recognises_common_spellings(self):
        for value in ("auto", "Auto", " AUTO ", "automatic", "auto-detect", "autodetect"):
            self.assertTrue(dp.is_auto(value), value)
        for value in ("1min", "2min", "", None, "automated"):
            self.assertFalse(dp.is_auto(value), value)

    def test_auto_resolves_to_the_closest_preset_for_a_long_script(self):
        # ~700 words at the estimator's ~2.2 words/sec -> roughly 5 minutes.
        script = _script(700, dialogue_lines=50)
        key, was_auto = dp.resolve_duration("auto", script_text=script)
        self.assertTrue(was_auto)
        self.assertEqual(key, "5min")

    def test_auto_resolves_to_a_short_preset_for_a_short_script(self):
        script = _script(20, dialogue_lines=3)
        key, was_auto = dp.resolve_duration("auto", script_text=script)
        self.assertTrue(was_auto)
        self.assertEqual(key, "30sec")

    def test_explicit_value_is_never_treated_as_auto(self):
        script = _script(700, dialogue_lines=50)
        key, was_auto = dp.resolve_duration("2min", script_text=script)
        self.assertFalse(was_auto)
        self.assertEqual(key, "2min")

    def test_empty_value_falls_back_to_normalize_default_not_auto(self):
        key, was_auto = dp.resolve_duration("", script_text=_script(700, 50))
        self.assertFalse(was_auto)
        self.assertEqual(key, "1min")

    def test_resolve_duration_accepts_an_already_parsed_story(self):
        parsed = {"scenes": [{"lines": [
            {"text": "word " * 700},
        ]}]}
        key, was_auto = dp.resolve_duration("auto", parsed=parsed)
        self.assertTrue(was_auto)
        self.assertEqual(key, "5min")


class PreviewEndpointAutoTests(unittest.TestCase):
    def setUp(self):
        import app as app_module
        self.client = app_module.app.test_client()

    def test_auto_target_resolves_and_is_flagged_in_the_response(self):
        script = "[Scene: X]\n" + "\n".join(
            f"Ali: (happy; walk; X) " + " ".join(["word"] * 14) + "."
            for _ in range(50))
        resp = self.client.post("/api/preview", json={
            "script": script, "target_duration": "auto"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        analysis = body.get("duration_analysis", {})
        self.assertTrue(analysis.get("auto_selected"))
        # A ~700-word script should not resolve to a 30-second preset.
        self.assertNotEqual(analysis.get("selected_preset"), "30sec")

    def test_fixed_target_is_not_flagged_as_auto(self):
        script = "[Scene: X]\nAli: (happy; walk; X) Hello dosto kaise ho aaj.\n"
        resp = self.client.post("/api/preview", json={
            "script": script, "target_duration": "2min"})
        self.assertEqual(resp.status_code, 200)
        analysis = resp.get_json().get("duration_analysis", {})
        self.assertFalse(analysis.get("auto_selected"))
        self.assertEqual(analysis.get("selected_preset"), "2min")


class BuildWiringTests(unittest.TestCase):
    """Guards the exact regression this fix required: build() used to
    re-fetch the raw (unresolved) value from settings a second time inside
    the else-branch, silently undoing the "auto" resolution done just above."""

    def test_target_dur_is_resolved_before_its_first_use(self):
        src = (Path(__file__).parents[1] / "build.py").read_text(encoding="utf-8")
        resolve_at = src.index("duration_planner.resolve_duration(target_dur")
        first_use_at = src.index('parse_script(script_text, target_duration=target_dur)')
        self.assertLess(resolve_at, first_use_at,
                        "resolve_duration must run before parse_script uses target_dur")
        # The old duplicate re-fetch inside the else-branch must be gone --
        # it would silently overwrite the resolved value with the raw one.
        self.assertEqual(
            src.count('target_dur = (settings or {}).get("target_duration")'), 1)


class FrontendAutoOptionTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parents[1]
        self.html = (root / "templates/index.html").read_text(encoding="utf-8")
        self.js = (root / "static/js/studio.js").read_text(encoding="utf-8")

    def test_auto_button_exists_and_is_the_default_selection(self):
        seg = self.html[self.html.index('id="ffLenSeg"'):][:400]
        self.assertIn('data-v="auto"', seg)
        auto_button = seg[seg.index('data-v="auto"'):seg.index('data-v="30sec"')]
        self.assertIn('class="on"', auto_button)

    def test_js_default_matches_the_new_auto_button(self):
        self.assertIn("selectedVideoDuration(){ return segVal('ffLenSeg')||'auto'; }", self.js)

    def test_mismatch_warning_is_suppressed_when_auto_selected(self):
        self.assertIn("!duration.auto_selected&&duration.estimated_seconds", self.js)


if __name__ == "__main__":
    unittest.main()
