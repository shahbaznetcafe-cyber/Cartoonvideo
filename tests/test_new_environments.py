"""New composed backgrounds must resolve to real local CC0 assets and route.

Presets like village/town/night/desert previously produced no dressing at all,
so those scenes rendered as an empty procedural stage.
"""
import unittest

import production_director
import scene_assets


class DressingCoverageTests(unittest.TestCase):
    NEW = ["village", "town", "night", "meadow", "desert", "beach"]

    def test_every_new_preset_has_real_dressings(self):
        for preset in self.NEW:
            items = scene_assets.dressings_for({"preset": preset, "variant": preset})
            self.assertTrue(items, f"{preset} produced no dressing")
            for item in items:
                self.assertTrue(item["source"], f"{preset}: empty source")
                self.assertTrue(item["readOnlySource"])
                self.assertGreater(item["targetHeight"], 0)

    def test_magic_grove_variant_has_dressings(self):
        items = scene_assets.dressings_for({"preset": "forest", "variant": "magic_grove"})
        self.assertTrue(items)

    def test_existing_presets_still_work(self):
        for preset in ("forest", "pirate", "space", "apocalypse"):
            self.assertTrue(scene_assets.dressings_for({"preset": preset, "variant": preset}))

    def test_catalog_lists_the_new_worlds(self):
        ids = {item["id"] for item in scene_assets.composed_backgrounds()}
        for expected in ("village_square", "town_street", "night_forest",
                         "magic_grove", "open_meadow", "island_beach", "rocky_desert"):
            self.assertIn(expected, ids)


class RoutingTests(unittest.TestCase):
    def _preset(self, location, prompt=""):
        return production_director._environment(
            {"location": location, "background_prompt": prompt})["preset"]

    def test_urdu_and_english_words_route_to_the_new_presets(self):
        self.assertEqual(self._preset("Gaon ka chowk"), "village")
        self.assertEqual(self._preset("Sarak par", "city street traffic"), "town")
        self.assertEqual(self._preset("Raat ka jungle", "andhera raat"), "night")
        self.assertEqual(self._preset("Maidan", "khula meadow"), "meadow")
        self.assertEqual(self._preset("Sahil", "beach kinare ret"), "beach")
        self.assertEqual(self._preset("Sehra", "desert ret garmi"), "desert")

    def test_a_village_farm_is_still_a_farm_scene(self):
        env = production_director._environment({"location": "Village farm, morning"})
        self.assertEqual(env["preset"], "forest")
        self.assertEqual(env["variant"], "village_farm")

    def test_generic_city_words_no_longer_mean_apocalypse(self):
        self.assertEqual(self._preset("Street", "city road traffic"), "town")
        self.assertEqual(self._preset("Tabah shehar", "zombie ruins abandoned"), "apocalypse")

    def test_plain_beach_is_not_a_pirate_scene(self):
        self.assertEqual(self._preset("Sahil", "beach ret"), "beach")
        self.assertEqual(self._preset("Jazeera", "pirate ship treasure"), "pirate")


class RendererLookTests(unittest.TestCase):
    def test_renderer_defines_colours_for_every_new_world(self):
        from pathlib import Path
        html = (Path(__file__).parents[1] / "threejs_render/render_scene.html").read_text(
            encoding="utf-8")
        for preset in ("village:", "town:", "meadow:", "beach:"):
            self.assertIn(preset, html, f"BASE_LOOK missing {preset}")
        for variant in ("village_square:", "town_street:", "night_forest:",
                        "magic_grove:", "open_meadow:", "island_beach:", "rocky_desert:"):
            self.assertIn(variant, html, f"VARIANT_LOOK missing {variant}")


class UrduScriptRoutingTests(unittest.TestCase):
    """Urdu-script locations must reach the same presets as their roman forms."""

    def _preset(self, location):
        return production_director._environment({"location": location})["preset"]

    def test_urdu_script_words_are_tokenised(self):
        tokens = production_director._tokens("گاؤں کا چوک")
        self.assertTrue(tokens, "Urdu text produced no tokens")

    def test_urdu_locations_route_to_the_right_worlds(self):
        self.assertEqual(self._preset("گاؤں کا چوک"), "village")
        self.assertEqual(self._preset("ساحل کے کنارے"), "beach")
        self.assertEqual(self._preset("رات کا جنگل"), "night")
        self.assertEqual(self._preset("کھلا میدان"), "meadow")
        self.assertEqual(self._preset("صحرا"), "desert")
        self.assertEqual(self._preset("شہر کی سڑک"), "town")

    def test_roman_routing_still_works(self):
        self.assertEqual(self._preset("Gaon ka chowk"), "village")
        self.assertEqual(self._preset("Sahil"), "beach")


if __name__ == "__main__":
    unittest.main()
