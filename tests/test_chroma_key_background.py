""""Green screen" / "blue screen" chroma-key background option.

Alongside the composed backgrounds (village, forest, beach...), a scene whose
location/background text says "green screen" or "blue screen" renders the cast
alone against ONE flat, unlit solid colour -- no baked GLB, no AI plate, no
ground texture, no decoration -- so the clip can be background-removed (keyed)
afterwards in an external editor (CapCut/Premiere/DaVinci).
"""
import unittest
from pathlib import Path
from unittest import mock

import blender3d
import production_director as pd
import scene_assets


class ScenePresetDetectionTests(unittest.TestCase):
    def _preset(self, location="", background_prompt=""):
        return pd._scene_preset({"location": location, "background_prompt": background_prompt})

    def test_common_english_phrasings(self):
        for phrase in ("Green screen", "green screen studio", "greenscreen",
                       "chroma green backdrop", "chroma key green"):
            self.assertEqual(self._preset(phrase), "chroma_green", phrase)
        for phrase in ("Blue screen", "blue screen studio", "bluescreen",
                       "chroma blue backdrop", "chroma key blue"):
            self.assertEqual(self._preset(phrase), "chroma_blue", phrase)

    def test_urdu_phrasings(self):
        self.assertEqual(self._preset("گرین اسکرین"), "chroma_green")
        self.assertEqual(self._preset("سبز اسکرین"), "chroma_green")
        self.assertEqual(self._preset("نیلی اسکرین"), "chroma_blue")

    def test_works_from_background_prompt_too(self):
        self.assertEqual(self._preset("", "chroma key green screen"), "chroma_green")

    def test_plain_colour_mentions_are_not_misdetected(self):
        # A colour word alone (no "screen"/"key") must never trigger chroma --
        # otherwise "green apple", "blue sky" story locations would misfire.
        self.assertNotIn(self._preset("green apple orchard"), ("chroma_green", "chroma_blue"))
        self.assertNotIn(self._preset("blue sky meadow"), ("chroma_green", "chroma_blue"))
        self.assertNotIn(self._preset("a key under the doormat"), ("chroma_green", "chroma_blue"))

    def test_unrelated_scenes_are_unaffected(self):
        self.assertEqual(self._preset("Jungle path"), "forest")
        self.assertEqual(self._preset("Gaon ka chowk"), "village")


class EnvironmentSettingsTests(unittest.TestCase):
    def test_chroma_environment_has_no_decoration_signals(self):
        for preset in ("chroma_green", "chroma_blue"):
            env = pd._environment({"location": {"chroma_green": "green screen",
                                                 "chroma_blue": "blue screen"}[preset]}, 0)
            self.assertEqual(env["preset"], preset)
            self.assertEqual(env["variant"], preset)
            self.assertEqual(env["leaves"], 0)
            self.assertEqual(env["clouds"], 0)
            self.assertEqual(env["ambientActors"], 0)
            self.assertFalse(env["instancedVegetation"])


class DressingAndAssetTests(unittest.TestCase):
    def test_no_dressings_for_chroma_presets(self):
        self.assertEqual(scene_assets.dressings_for({"preset": "chroma_green", "variant": "chroma_green"}), [])
        self.assertEqual(scene_assets.dressings_for({"preset": "chroma_blue", "variant": "chroma_blue"}), [])

    def test_no_baked_glb_environment_for_chroma(self):
        self.assertIsNone(blender3d._env_for({"location": "green screen"}, preset="chroma_green"))
        self.assertIsNone(blender3d._env_for({"location": "blue screen"}, preset="chroma_blue"))

    def test_scene_look_fallback_detects_chroma_phrases(self):
        self.assertEqual(blender3d._scene_look({"location": "green screen studio"}), "chroma_green")
        self.assertEqual(blender3d._scene_look({"location": "blue screen studio"}), "chroma_blue")

    def test_ai_background_plate_is_skipped_for_chroma_scenes_only(self):
        import assets
        parsed = {"scenes": [
            {"id": 1, "location": "Green screen", "background_prompt": "chroma key green"},
            {"id": 2, "location": "Jungle path", "background_prompt": "forest trees"},
        ]}
        calls = []
        def fake_reusable(prompt, style=None):
            calls.append(prompt)
            return f"/fake/{prompt}.png"
        with mock.patch.object(assets, "reusable_background", side_effect=fake_reusable):
            result = assets.build_scene_backgrounds(parsed)
        self.assertNotIn(1, result)          # no AI plate generated for the chroma scene
        self.assertIn(2, result)             # normal scenes are unaffected
        self.assertEqual(calls, ["forest trees"])


class RendererSourceTests(unittest.TestCase):
    """The WebGL render can't run in this sandbox (documented environment
    limitation); these assert the exact wiring a real render depends on."""

    def setUp(self):
        self.html = (Path(__file__).parents[1] / "threejs_render/render_scene.html").read_text(
            encoding="utf-8")

    def test_flat_unlit_colours_are_defined(self):
        self.assertIn("chroma_green: { sky: 0x00ff00, ground: 0x00ff00", self.html)
        self.assertIn("chroma_blue:  { sky: 0x0000ff, ground: 0x0000ff", self.html)

    def test_isChroma_flag_exists_and_gates_background_sources(self):
        self.assertIn("const isChroma = sceneLook === 'chroma_green' || sceneLook === 'chroma_blue';",
                      self.html)
        self.assertIn("if (backgroundImage && !isChroma)", self.html)
        self.assertIn("if (spec.env && !isChroma)", self.html)

    def test_ground_dressing_block_is_gated_and_chroma_gets_an_unlit_backdrop(self):
        guard_at = self.html.index("if (!isChroma) {")
        ground_at = self.html.index("const ground = new THREE.Mesh(")
        backdrop_at = self.html.index("MeshBasicMaterial({ color: LOOK.ground, fog: false })")
        self.assertLess(guard_at, ground_at,
                        "the decorated-ground block must be inside the !isChroma branch")
        self.assertGreater(backdrop_at, ground_at,
                           "the flat backdrop must be the chroma else-branch, after the normal ground")

    def test_js_syntax_is_valid(self):
        import re, subprocess, tempfile, os
        match = re.search(r'<script type="module">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(match)
        with tempfile.NamedTemporaryFile(suffix=".mjs", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write(match.group(1))
            path = handle.name
        try:
            result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
