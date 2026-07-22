import unittest
import tempfile
from pathlib import Path

import blender3d
import character_traits


class QuaterniusCharacterTraitsTests(unittest.TestCase):
    def test_every_registered_quaternius_character_has_a_trait_record(self):
        report = character_traits.quaternius_trait_report()
        # 125 core + 9 Pirate Kit characters (license user-verified as CC0).
        self.assertEqual(report["summary"]["registered"], 134)
        self.assertEqual(len(report["characters"]), 134)
        self.assertTrue(all(item["poseMode"] in {"humanoid", "clip_only"}
                            for item in report["characters"]))

    def test_aerial_character_rejects_human_hand_action(self):
        directive = character_traits.render_directive(
            "blender/rigged/blend/quaternius_dragon.blend", "pickup")
        self.assertEqual(directive["traits"]["form"], "aerial")
        self.assertEqual(directive["traits"]["poseMode"], "clip_only")
        self.assertEqual(directive["traits"]["groundMode"], "hover")
        self.assertEqual(directive["action"], "idle")
        self.assertFalse(directive["actionSupported"])

    def test_humanoid_keeps_real_interaction_clip(self):
        directive = character_traits.render_directive(
            "blender/rigged/blend/quaternius_farmer.blend", "pickup")
        self.assertEqual(directive["traits"]["form"], "humanoid")
        self.assertEqual(directive["action"], "pickup")
        self.assertEqual(directive["sourceClip"], "Interact")
        self.assertTrue(directive["actionSupported"])

    def test_pre_render_safety_replaces_impossible_action_and_records_it(self):
        timeline = [{"speaker": "dragon", "action": "pickup"},
                    {"speaker": "farmer", "action": "pickup"}]
        assignment = {
            "dragon": "blender/rigged/blend/quaternius_dragon.blend",
            "farmer": "blender/rigged/blend/quaternius_farmer.blend",
        }
        with tempfile.TemporaryDirectory() as directory:
            blender3d._apply_character_action_safety(timeline, assignment, directory)
            self.assertEqual(timeline[0]["action"], "idle")
            self.assertIn("action_safety_note", timeline[0])
            self.assertEqual(timeline[1]["action"], "pickup")
            self.assertTrue((Path(directory) / "character_action_safety.json").exists())
    def test_renderer_directive_preserves_sbz_legacy_path(self):
        directive = blender3d._character_render_directive(
            "tamatar", "blender/rigged/blend/tamatar.blend", "point", "")
        self.assertEqual(directive["action"], "point")
        self.assertEqual(directive["traits"], {})


if __name__ == "__main__":
    unittest.main()