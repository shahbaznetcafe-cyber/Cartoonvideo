"""An unrecognised emotion/action word must not fragment scenes.

parse_structured_script() used to graft EVERY cue token that failed emotion/
action recognition onto the scene's "location" string, comparing that noisy
per-line string against the current scene on every line. A script that used
rich emotion words (e.g. "nervous", "playful") or action verbs (e.g. "hop",
"read") outside the small built-in vocabularies fragmented one intended scene
into a new "scene" almost every line -- a real 8-scene, 53-line script turned
into 48 scenes.
"""
import unittest

import story_parser


def _scenes_for(script):
    parsed = story_parser.parse_structured_script(script)
    return parsed["scenes"]


class UnrecognisedCueWordTests(unittest.TestCase):
    def test_unrecognised_emotion_and_action_do_not_split_the_scene(self):
        script = (
            "[Scene: Market]\n"
            "Ali: (nervous; hop; Market) Line one here today.\n"
            "Sara: (playful; read; Market) Line two here today.\n"
            "Ali: (skeptical; freeze; Market) Line three here today.\n"
        )
        scenes = _scenes_for(script)
        self.assertEqual(len(scenes), 1, f"got {len(scenes)} scenes: "
                         f"{[s['location'] for s in scenes]}")
        self.assertEqual(scenes[0]["location"], "market")
        self.assertEqual(len(scenes[0]["lines"]), 3)

    def test_recognised_action_still_applies_despite_unrecognised_emotion(self):
        script = "[Scene: X]\nAli: (nervous; walk; X) Hello there today.\n"
        scenes = _scenes_for(script)
        self.assertEqual(scenes[0]["lines"][0]["action"], "walk")

    def test_a_real_new_location_still_starts_a_new_scene(self):
        script = (
            "[Scene: Market]\n"
            "Ali: (happy; walk; Market) Line one here today.\n"
            "Sara: (happy; walk; Forest) Line two here today.\n"
        )
        scenes = _scenes_for(script)
        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[1]["location"], "forest")

    def test_two_part_cue_never_gets_a_location_scavenged(self):
        # Historical "(emotion; action)" cues must behave exactly as before:
        # no location component at all, regardless of recognition.
        script = "[Scene: X]\nAli: (nervous; hop) Hello there today.\n"
        scenes = _scenes_for(script)
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0]["location"], "X")

    def test_one_part_cue_is_unaffected(self):
        script = "[Scene: X]\nAli: (happy) Hello there today.\n"
        scenes = _scenes_for(script)
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0]["lines"][0]["emotion"], "happy")

    def test_real_world_urdu_script_produces_a_sane_scene_count(self):
        """Regression for the exact script that exposed this: 8 authored
        [Scene:] blocks (one long one legitimately auto-splits into pacing
        beats later) must never balloon into dozens of scenes."""
        script = (
            "[Scene: Village]\n"
            "خرگوش: (excited; point; Village) "
            "Line one spoken here clearly today.\n"
            "بلی: (curious; approach; Village) "
            "Line two spoken here clearly today.\n"
            "کتا: (nervous; jump; Village) "
            "Line three spoken here clearly today.\n"
        )
        scenes = _scenes_for(script)
        self.assertEqual(len(scenes), 1)
        self.assertEqual(len(scenes[0]["lines"]), 3)


if __name__ == "__main__":
    unittest.main()
