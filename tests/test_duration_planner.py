import unittest

import duration_planner
import story_parser
import story_templates


class DurationPlannerTests(unittest.TestCase):
    def test_supported_presets_cover_thirty_seconds_to_fifteen_minutes(self):
        self.assertEqual(
            list(duration_planner.DURATION_PRESETS),
            ["30sec", "1min", "2min", "3min", "5min", "8min", "10min", "15min"],
        )
        self.assertEqual(duration_planner.preset("30sec")["seconds"], 30)
        self.assertEqual(duration_planner.preset("15min")["seconds"], 900)
        self.assertEqual(duration_planner.normalize_duration("short"), "30sec")
        self.assertEqual(duration_planner.normalize_duration("medium"), "1min")
        self.assertEqual(duration_planner.normalize_duration("long"), "2min")

    def test_longform_plans_have_target_line_budget(self):
        for key, definition in duration_planner.DURATION_PRESETS.items():
            scenes, lines_per_scene = story_templates.LONGFORM_PLANS[key]
            self.assertEqual(scenes * lines_per_scene, definition["lines"])

    def test_pasted_dialogue_is_split_by_natural_spoken_length(self):
        lines = ["Hero: (happy; walk) We need to cross the forest path quickly now."
                 if index % 2 == 0 else
                 "Friend: (thinking; look) I can hear something moving behind those trees."
                 for index in range(30)]
        script = "\n".join(lines)
        parsed = story_parser.parse_structured_script(script)
        planned, changed = duration_planner.auto_segment_scenes(parsed, script)
        self.assertTrue(changed)
        self.assertGreaterEqual(len(planned["scenes"]), 2)
        self.assertEqual(sum(len(scene["lines"]) for scene in planned["scenes"]), 30)
        self.assertEqual([scene["id"] for scene in planned["scenes"]],
                         list(range(1, len(planned["scenes"]) + 1)))
        self.assertTrue(all(scene["transition"] == "hard_cut" for scene in planned["scenes"]))

    def test_explicit_scene_headers_are_never_overwritten(self):
        script = """[Scene: Home]
Hero: First line.
Friend: Second line.
[Scene: Market]
Hero: Third line.
Friend: Fourth line."""
        parsed = story_parser.parse_structured_script(script)
        planned, changed = duration_planner.auto_segment_scenes(parsed, script)
        self.assertFalse(changed)
        self.assertEqual([scene["location"] for scene in planned["scenes"]],
                         ["Home", "Market"])
    def test_one_minute_target_creates_two_meaningful_beats_from_pasted_dialogue(self):
        script = "\n".join(
            f"Hero: (talk; walk) Story beat {index} moves the adventure forward."
            for index in range(6)
        )
        parsed = story_parser.parse_structured_script(script)
        planned, changed = duration_planner.auto_segment_scenes(
            parsed, script, selected="1min")
        self.assertTrue(changed)
        self.assertEqual(len(planned["scenes"]), 2)
        self.assertTrue(all(len(scene["lines"]) == 3 for scene in planned["scenes"]))

    def test_single_authored_scene_header_can_expand_into_duration_beats(self):
        script = "[Scene: Forest path]\n" + "\n".join(
            f"Hero: (talk; walk) Story beat {index} moves the adventure forward."
            for index in range(6)
        )
        parsed = story_parser.parse_structured_script(script)
        planned, changed = duration_planner.auto_segment_scenes(
            parsed, script, selected="1min")
        self.assertTrue(changed)
        self.assertEqual(len(planned["scenes"]), 2)
        self.assertTrue(all(scene["location"].startswith("Forest path")
                            for scene in planned["scenes"]))

    def test_flexible_dialogue_format_parsing_with_hyphen_and_quotes(self):
        script = """Hero - (happy) "Aaj bazaar mein bohat raunaq hai!"
Friend - (thinking) "Haan, chalo kuch khareedtay hain." """
        parsed = story_parser.parse_structured_script(script)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed["scenes"][0]["lines"]), 2)
        self.assertEqual(parsed["scenes"][0]["lines"][0]["text"], "Aaj bazaar mein bohat raunaq hai!")
        self.assertEqual(parsed["scenes"][0]["lines"][0]["emotion"], "happy")

    def test_parse_script_with_target_duration(self):
        lines = [f"Hero - Line {i} of long story." for i in range(24)]
        script = "\n".join(lines)
        parsed = story_parser.parse_script(script, target_duration="2min")
        self.assertIsNotNone(parsed)
        total_lines = sum(len(s["lines"]) for s in parsed["scenes"])
        self.assertEqual(total_lines, 24)
        self.assertGreaterEqual(len(parsed["scenes"]), 2)


if __name__ == "__main__":
    unittest.main()
