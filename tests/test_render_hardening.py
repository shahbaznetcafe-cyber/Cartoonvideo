import os
import tempfile
import unittest
from unittest import mock

import blender3d
import build
import config


class RenderHardeningTests(unittest.TestCase):
    def test_speaker_is_never_dropped_from_full_cast(self):
        cast = blender3d._cast_with_speaker(["a", "b", "c"], "d")
        self.assertEqual(len(cast), 3)
        self.assertIn("d", cast)
        self.assertEqual(cast, ["a", "b", "d"])

    def test_washroom_does_not_match_room_environment(self):
        path = blender3d._env_for({
            "location": "outside washroom",
            "background_prompt": "handwashing station outside a washroom",
        })
        self.assertEqual(os.path.basename(path), "garden.glb")

    def test_scene_look_exposes_story_condition(self):
        self.assertEqual(blender3d._scene_look({"background_prompt": "dark storm and rain"}),
                         "storm")
        self.assertEqual(blender3d._scene_look({"background_prompt": "muddy puddles"}),
                         "mud")
        self.assertEqual(blender3d._scene_look({"location": "handwashing station"}),
                         "wash")

    def test_truncated_clip_is_rejected(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"0" * 12000)
            path = handle.name
        try:
            with (mock.patch.object(blender3d, "_clip_probe", return_value=(0.04, 1, 1920, 1080)),
                  mock.patch.object(blender3d, "_probe_duration", return_value=4.0)):
                self.assertFalse(blender3d._clip_is_valid(path, "voice.mp3", 24))
            with (mock.patch.object(blender3d, "_clip_probe", return_value=(4.0, 96, 1920, 1080)),
                  mock.patch.object(blender3d, "_probe_duration", return_value=4.0)):
                self.assertTrue(blender3d._clip_is_valid(
                    path, "voice.mp3", 24, expected_size=(1920, 1080)))
                self.assertFalse(blender3d._clip_is_valid(
                    path, "voice.mp3", 24, expected_size=(960, 540)))
        finally:
            os.remove(path)

    def test_subtitle_wraps_to_two_lines(self):
        wrapped = blender3d._wrap_subtitle(
            "one two three four five six seven eight nine ten eleven twelve", target=24)
        self.assertEqual(len(wrapped.splitlines()), 2)

    def test_ui_settings_control_burned_subtitles(self):
        old_subtitles, old_intro = config.SUBTITLES_ON, config.INTRO_ON
        old_caption = config.CAPTIONS.get("enabled")
        try:
            build.apply_settings({"subtitles_on": False, "intro_on": True})
            self.assertFalse(config.SUBTITLES_ON)
            self.assertFalse(config.CAPTIONS["enabled"])
            self.assertTrue(config.INTRO_ON)
            build.apply_settings({"captions": {"enabled": True}})
            self.assertTrue(config.SUBTITLES_ON)
        finally:
            config.SUBTITLES_ON, config.INTRO_ON = old_subtitles, old_intro
            config.CAPTIONS["enabled"] = old_caption


if __name__ == "__main__":
    unittest.main()
