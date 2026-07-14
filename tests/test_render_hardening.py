import os
from pathlib import Path
import tempfile
import unittest
import json
from unittest import mock

import blender3d
import build
import config


class RenderHardeningTests(unittest.TestCase):
    def test_threejs_restores_bind_pose_before_grounding_and_animation(self):
        html = (Path(__file__).parents[1] / "threejs_render" / "render_scene.html").read_text(
            encoding="utf-8"
        )
        bind_pose = html.index("o.skeleton.pose()")
        grounding = html.index("new THREE.Box3().setFromObject(root)")
        capture = html.index("captureBoneBases(bones)")
        self.assertLess(bind_pose, grounding)
        self.assertLess(grounding, capture)
        self.assertIn("applyLegacyPose(b, c.boneBases", html)
        self.assertNotIn("b.leg_L.rotation.x =", html)
        self.assertNotIn("b.jaw.rotation.x =", html)

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

    def test_final_duration_must_match_assembled_timeline(self):
        self.assertTrue(blender3d._duration_matches(10.08, 10.0, 24))
        self.assertFalse(blender3d._duration_matches(9.70, 10.0, 24))
        with mock.patch.object(blender3d, "_probe_duration", return_value=7.5):
            with self.assertRaisesRegex(RuntimeError, "final duration mismatch"):
                blender3d._validate_final_duration("final.mp4", 8.0, 24)
        with mock.patch.object(blender3d, "_probe_duration", return_value=8.04):
            self.assertEqual(blender3d._validate_final_duration("final.mp4", 8.0, 24), 8.04)

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

    def test_pre_render_validation_is_advisory_and_preserves_assignment(self):
        assignment = {"hero": r"D:\characters\hero.blend"}
        original = dict(assignment)
        payload = {
            "schema_version": 1,
            "characters": [{
                "character": {"id": "hero", "name": "Hero"},
                "tier": "LEGACY_JAW",
                "compatibility_percent": 33,
                "warnings": [{"code": "legacy_jaw_fallback", "message": "jaw fallback"}],
                "errors": [],
            }],
        }
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch("char3d_lib.validate_assignments", return_value=payload):
            result = blender3d._pre_render_character_validation(assignment, directory)
            with open(os.path.join(directory, "character_validation.json"),
                      encoding="utf-8") as handle:
                saved = json.load(handle)
        self.assertEqual(result, payload)
        self.assertEqual(saved, payload)
        self.assertEqual(assignment, original)

    def test_only_current_speaker_receives_lip_sync_inputs(self):
        speaker = blender3d._lip_sync_inputs("hero", "hero", "open.json", "face.json")
        listener = blender3d._lip_sync_inputs("friend", "hero", "open.json", "face.json")
        self.assertEqual(speaker, {"openness": "open.json", "visemes": "face.json"})
        self.assertEqual(listener, {"openness": "", "visemes": ""})

    def test_missing_viseme_timeline_resolves_to_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = os.path.join(directory, "face.json")
            with open(existing, "w", encoding="utf-8") as handle:
                handle.write("{}")
            self.assertEqual(blender3d._resolve_viseme_path(directory, "face.json"), existing)
            self.assertEqual(blender3d._resolve_viseme_path(directory, "missing.json"), "")


if __name__ == "__main__":
    unittest.main()
