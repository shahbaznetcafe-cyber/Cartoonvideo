import os
from pathlib import Path
import tempfile
import unittest
import json
from unittest import mock

import blender3d
import build
import config
import assets


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

    def test_threejs_uses_background_plate_and_calibrated_world_scale(self):
        html = (Path(__file__).parents[1] / "threejs_render" / "render_scene.html").read_text(
            encoding="utf-8"
        )
        renderer = (Path(__file__).parents[1] / "threejs_render" / "render_scene.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("backgroundImage", html)
        self.assertIn("new THREE.TextureLoader().loadAsync", html)
        self.assertIn("12.5 / Math.max", html)
        self.assertIn("const TH = 1.18", html)
        self.assertIn("backgroundImage: backgroundSource ? '/background-image.png' : ''", renderer)
        self.assertIn("requestPath === '/background-image.png'", renderer)

    def test_threejs_serves_scoped_external_scene_assets_with_fallback(self):
        root = Path(__file__).parents[1]
        renderer = (root / "threejs_render" / "render_scene.js").read_text(encoding="utf-8")
        html = (root / "threejs_render" / "render_scene.html").read_text(encoding="utf-8")
        self.assertIn("sceneAssetRoots", renderer)
        self.assertIn("/scene-assets/", renderer)
        self.assertIn("candidate.startsWith(root + path.sep)", renderer)
        self.assertIn("externalAsset", html)
        self.assertIn("Scene asset unavailable; using procedural fallback", html)

    def test_reusable_background_library_generates_once_per_scene_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory) / "backgrounds"
            manifest = library / "manifest.json"
            def fake_generate(prompt, out_path, style=None):
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                Path(out_path).write_bytes(b"fake image")
                return out_path
            with mock.patch.object(assets, "BACKGROUND_LIBRARY", library), \
                    mock.patch.object(assets, "BACKGROUND_MANIFEST", manifest), \
                    mock.patch.object(assets, "generate_background", side_effect=fake_generate) as generated:
                first = assets.reusable_background("sunny village path", "3d cartoon")
                second = assets.reusable_background("sunny village path", "3d cartoon")
            self.assertEqual(first, second)
            self.assertEqual(generated.call_count, 1)
            saved = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 1)

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
        # "washroom" must not token-match the indoor "room" set; outdoor scenes
        # now use composed dressings + AI plate instead of a baked env glb.
        self.assertIsNone(path)

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

    def test_valid_short_dialogue_clip_is_not_rejected_by_a_fixed_half_second_floor(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"0" * 12000)
            path = handle.name
        try:
            # 9 frames at 24 FPS is 0.375s: sufficient for a 0.396s spoken line.
            with (mock.patch.object(blender3d, "_clip_probe", return_value=(0.375, 9, 1920, 1080)),
                  mock.patch.object(blender3d, "_probe_duration", return_value=0.396)):
                self.assertTrue(blender3d._clip_is_valid(
                    path, "voice.mp3", 24, expected_size=(1920, 1080)))
        finally:
            os.remove(path)
    def test_final_duration_must_match_assembled_timeline(self):
        self.assertTrue(blender3d._duration_matches(10.08, 10.0, 24))
        self.assertFalse(blender3d._duration_matches(9.70, 10.0, 24))
        with (mock.patch.object(blender3d, "_probe_duration", return_value=7.5),
              mock.patch.object(blender3d, "_stream_duration", return_value=7.5)):
            with self.assertRaisesRegex(RuntimeError, "duration mismatch"):
                blender3d._validate_final_duration("final.mp4", 8.0, 24)
        with (mock.patch.object(blender3d, "_probe_duration", return_value=8.24),
              mock.patch.object(blender3d, "_stream_duration",
                                side_effect=[8.04, 8.24])):
            self.assertEqual(blender3d._validate_final_duration("final.mp4", 8.0, 24), 8.24)
        with (mock.patch.object(blender3d, "_probe_duration", return_value=8.0),
              mock.patch.object(blender3d, "_stream_duration",
                                side_effect=[7.5, 8.0])):
            with self.assertRaisesRegex(RuntimeError, "video stream duration mismatch"):
                blender3d._validate_final_duration("final.mp4", 8.0, 24)
        with mock.patch.object(blender3d, "_probe_duration", return_value=8.04), \
                mock.patch.object(blender3d, "_stream_duration", return_value=0.0):
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

    def test_lip_sync_inputs_follow_real_character_capability(self):
        body = {"lipSyncMode": "none"}
        jaw = {"lipSyncMode": "jaw_openness"}
        face = {"lipSyncMode": "viseme"}
        self.assertEqual(
            blender3d._lip_sync_inputs("hero", "hero", "open.json", "face.json", body),
            {"openness": "", "visemes": ""},
        )
        self.assertEqual(
            blender3d._lip_sync_inputs("hero", "hero", "open.json", "face.json", jaw),
            {"openness": "open.json", "visemes": ""},
        )
        self.assertEqual(
            blender3d._lip_sync_inputs("hero", "hero", "open.json", "face.json", face),
            {"openness": "open.json", "visemes": "face.json"},
        )

    def test_missing_viseme_timeline_resolves_to_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = os.path.join(directory, "face.json")
            with open(existing, "w", encoding="utf-8") as handle:
                handle.write("{}")
            self.assertEqual(blender3d._resolve_viseme_path(directory, "face.json"), existing)
            self.assertEqual(blender3d._resolve_viseme_path(directory, "missing.json"), "")


if __name__ == "__main__":
    unittest.main()
