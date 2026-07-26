import json
import os
import tempfile
import unittest
from pathlib import Path

import blender3d
import actions
import char3d_lib
import character_performance
import production_director
import scene_assets
import story_parser


class ProductionDirectorTests(unittest.TestCase):
    @staticmethod
    def _fixture():
        entry = next(item for item in char3d_lib.load()
                     if item.get("capability_id") == "quaternius_adventurer")
        blend = char3d_lib.blend_path(entry)
        parsed = {
            "title": "Suspicious Box", "language": "english",
            "characters": [{"id": "hero", "name": "Quaternius Adventurer"}],
            "scenes": [{
                "id": 1, "location": "forest path", "time": "day", "mood": "suspense",
                "background_prompt": "layered forest path with a suspicious wooden box",
                "lines": [
                    {"speaker": "hero", "text": "I will walk closer.", "emotion": "neutral", "action": "walk"},
                    {"speaker": "hero", "text": "Let me open this box.", "emotion": "thinking", "action": "reach"},
                    {"speaker": "hero", "text": "It moved?", "emotion": "surprised", "action": "retreat"},
                ],
            }],
        }
        timeline = [
            {"scene": 1, "speaker": "hero", "text": line["text"],
             "emotion": line["emotion"], "action": line["action"], "duration": 2.0,
             "transition": "hard_cut", "transition_duration": 0.0}
            for line in parsed["scenes"][0]["lines"]
        ]
        contexts = [
            {"cast": ["hero"], "action": "walk", "target": -1},
            {"cast": ["hero"], "action": "reach", "target": -1},
            {"cast": ["hero"], "action": "retreat", "target": -1},
        ]
        return parsed, timeline, {"hero": blend}, contexts

    def test_script_becomes_real_clips_shots_props_and_environment(self):
        parsed, timeline, assignments, contexts = self._fixture()
        plan = production_director.build_plan(parsed, timeline, assignments, contexts, fps=24)
        self.assertEqual(plan["generator"], "SBZ Production Director")
        self.assertTrue(plan["deterministic"])
        self.assertEqual(plan["lines"][0]["shot"], "establishing_wide")
        self.assertEqual(plan["lines"][0]["characters"]["hero"]["sourceClip"], "Walk")
        self.assertEqual(plan["lines"][0]["characters"]["hero"]["motionQuality"], "authored_action")
        self.assertEqual(plan["lines"][1]["shot"], "contact_oblique_medium")
        self.assertEqual(plan["lines"][1]["characters"]["hero"]["sourceClip"], "Interact")
        self.assertEqual(plan["lines"][1]["characters"]["hero"]["baseClip"], "TalkIdle")
        self.assertEqual(plan["lines"][1]["characters"]["hero"]["crossfadeSeconds"], 0.22)
        self.assertEqual(plan["lines"][1]["interaction"]["target"]["propId"], "box_1")
        self.assertEqual(plan["lines"][1]["interaction"]["status"], "planned_camera_masked_contact")
        self.assertTrue(plan["lines"][1]["camera"]["contactMasking"])
        self.assertNotEqual(
            plan["lines"][1]["characters"]["hero"]["blocking"]["start"],
            plan["lines"][1]["characters"]["hero"]["blocking"]["end"],
        )
        box = next(prop for prop in plan["lines"][1]["props"] if prop["type"] == "box")
        self.assertEqual(box["consequence"], "lid_opens")
        self.assertEqual(box["stateEnd"]["open"], 1.0)
        next_box = next(prop for prop in plan["lines"][2]["props"] if prop["type"] == "box")
        self.assertEqual(next_box["stateStart"]["open"], 1.0)
        self.assertEqual(plan["lines"][0]["environment"]["preset"], "forest")
        self.assertEqual(plan["lines"][0]["environment"]["variant"], "forest_path")
        self.assertGreater(plan["lines"][0]["environment"]["leaves"], 0)
        self.assertTrue(plan["motionAudit"]["fullyAuthored"])

    def test_plan_and_saved_json_are_deterministic(self):
        inputs = self._fixture()
        first = production_director.build_plan(*inputs, fps=24)
        second = production_director.build_plan(*inputs, fps=24)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            path = production_director.write_plan(directory, first)
            self.assertEqual(json.loads(Path(path).read_text(encoding="utf-8")), first)

    def test_generated_action_cue_is_backward_compatible(self):
        parsed = story_parser.parse_structured_script(
            "[Scene: Forest]\nHero: (surprised; run) The box moved!"
        )
        line = parsed["scenes"][0]["lines"][0]
        self.assertEqual(line["emotion"], "surprised")
        self.assertEqual(line["action"], "run")
        legacy = story_parser.parse_structured_script(
            "[Scene: Forest]\nHero: (happy) We found it!"
        )["scenes"][0]["lines"][0]
        self.assertEqual(legacy["emotion"], "happy")
        self.assertEqual(legacy["action"], "")

    def test_explicit_supported_action_beats_keyword_guessing(self):
        entry = {"speaker": "hero", "text": "I am ready.",
                 "emotion": "neutral", "action": "approach"}
        action, target = blender3d._line_action(entry, ["hero"], "hero",
                                               {"characters": [{"id": "hero", "name": "Hero"}]})
        self.assertEqual(action, "approach")
        self.assertEqual(target, -1)

    def test_locomotion_does_not_invent_another_character_target(self):
        entry = {"speaker": "hero", "text": "Main raste par walk karta hoon.",
                 "emotion": "neutral", "action": "walk"}
        action, target = blender3d._line_action(
            entry, ["hero", "friend"], "hero",
            {"characters": [{"id": "hero", "name": "Hero"},
                            {"id": "friend", "name": "Friend"}]})
        self.assertEqual(action, "walk")
        self.assertEqual(target, -1)

    def test_adjacent_dialogue_reuses_one_motivated_shot(self):
        parsed, _, assignments, _ = self._fixture()
        parsed["characters"].append({"id": "friend", "name": "Friend"})
        parsed["scenes"][0]["lines"] = [
            {"speaker": "hero", "text": "Hum yahan hain.", "emotion": "neutral", "action": "talk"},
            {"speaker": "friend", "text": "Plan tayar hai.", "emotion": "neutral", "action": "talk"},
            {"speaker": "hero", "text": "Pehle dekhte hain.", "emotion": "neutral", "action": "talk"},
        ]
        timeline = [{"scene": 1, "speaker": line["speaker"], "text": line["text"],
                     "emotion": line["emotion"], "action": line["action"], "duration": 2.0}
                    for line in parsed["scenes"][0]["lines"]]
        contexts = [{"cast": ["hero", "friend"], "action": "talk", "target": -1}
                    for _ in timeline]
        assignments["friend"] = assignments["hero"]
        plan = production_director.build_plan(parsed, timeline, assignments, contexts, fps=24)
        self.assertEqual(plan["lines"][1]["shot"], "motivated_two_shot")
        self.assertEqual(plan["lines"][1]["shotId"], plan["lines"][2]["shotId"])
        self.assertTrue(plan["lines"][2]["continuesPreviousShot"])

    def test_single_body_performer_uses_safe_medium_angle_variation(self):
        parsed, _, assignments, _ = self._fixture()
        parsed["scenes"][0]["lines"] = [
            {"speaker": "hero", "text": "First beat.", "emotion": "neutral", "action": "talk"},
            {"speaker": "hero", "text": "Second beat.", "emotion": "neutral", "action": "talk"},
            {"speaker": "hero", "text": "Third beat.", "emotion": "neutral", "action": "talk"},
            {"speaker": "hero", "text": "Fourth beat.", "emotion": "neutral", "action": "talk"},
        ]
        timeline = [{"scene": 1, "speaker": line["speaker"], "text": line["text"],
                     "emotion": line["emotion"], "action": line["action"], "duration": 2.0}
                    for line in parsed["scenes"][0]["lines"]]
        contexts = [{"cast": ["hero"], "action": "talk", "target": -1} for _ in timeline]
        plan = production_director.build_plan(parsed, timeline, assignments, contexts)
        self.assertEqual([line["shot"] for line in plan["lines"]], [
            "establishing_wide", "dialogue_medium", "body_medium_left", "body_medium_right",
        ])
        self.assertFalse(any(line["continuesPreviousShot"] for line in plan["lines"]))

    def test_direction_plan_uses_the_same_clamped_transition_policy_as_final_assembly(self):
        parsed, timeline, assignments, contexts = self._fixture()
        parsed["scenes"].append({
            "id": 2, "location": "forest clearing", "lines": [{
                "speaker": "hero", "text": "Now I run ahead.", "emotion": "neutral", "action": "run",
                "transition": "camera_motivated", "transition_duration": 2.0,
            }],
        })
        timeline.append({"scene": 2, "speaker": "hero", "text": "Now I run ahead.",
                         "emotion": "neutral", "action": "run", "duration": 2.0,
                         "transition": "camera_motivated", "transition_duration": 2.0})
        contexts.append({"cast": ["hero"], "action": "run", "target": -1})
        plan = production_director.build_plan(parsed, timeline, assignments, contexts)
        self.assertEqual(plan["lines"][0]["transition"], "hard_cut")
        self.assertEqual(plan["lines"][-1]["transition"], "camera_motivated")
        self.assertEqual(plan["lines"][-1]["transitionDuration"], 0.5)
        self.assertEqual(plan["lines"][-1]["transitionReason"], "explicit story direction")

    def test_uncalibrated_interaction_and_missing_action_clip_emit_warnings(self):
        farmer = next(item for item in char3d_lib.load()
                      if item.get("capability_id") == "quaternius_farmer")
        blend = char3d_lib.blend_path(farmer)
        parsed = {"characters": [{"id": "farmer", "name": "Farmer"}], "scenes": [{
            "id": 1, "location": "farm with a box", "lines": [
                {"speaker": "farmer", "text": "I reach for the box.", "emotion": "neutral", "action": "reach"},
                {"speaker": "farmer", "text": "I wash it.", "emotion": "neutral", "action": "wash"},
            ]}]}
        timeline = [{"scene": 1, "speaker": "farmer", "text": line["text"],
                     "emotion": line["emotion"], "action": line["action"], "duration": 1.5}
                    for line in parsed["scenes"][0]["lines"]]
        contexts = [{"cast": ["farmer"], "action": "reach", "target": -1},
                    {"cast": ["farmer"], "action": "wash", "target": -1}]
        plan = production_director.build_plan(parsed, timeline, {"farmer": blend}, contexts)
        codes = {warning["code"] for warning in plan["warnings"]}
        self.assertIn("interaction_not_calibrated", codes)
        self.assertIn("authored_action_unavailable", codes)
        self.assertEqual(plan["lines"][0]["interaction"]["status"], "unvalidated_body_hint")
        self.assertEqual(plan["lines"][1]["characters"]["farmer"]["motionQuality"], "semantic_substitute")
        self.assertGreater(plan["motionAudit"]["counts"]["semantic_substitute"], 0)

    def test_preview_motion_audit_reports_exact_and_transparent_semantic_clip_mapping(self):
        parsed, _, assignments, _ = self._fixture()
        audit = production_director.preview_motion_audit(parsed, assignments)
        self.assertTrue(audit["ready"])
        self.assertEqual(audit["counts"]["authored_action"], 3)
        parsed["scenes"][0]["lines"][0]["action"] = "wash"
        substitute = production_director.preview_motion_audit(parsed, assignments)
        self.assertTrue(substitute["ready"])
        self.assertEqual(substitute["counts"]["semantic_substitute"], 1)
        self.assertEqual(substitute["plannedLines"][0]["sourceClip"], "Interact")
        self.assertTrue(substitute["warnings"])

    def test_body_only_dialogue_is_saved_as_action_led_without_fake_facial_route(self):
        farmer = next(item for item in char3d_lib.load()
                      if item.get("capability_id") == "quaternius_farmer")
        blend = char3d_lib.blend_path(farmer)
        parsed = {"characters": [{"id": "farmer", "name": "Farmer"}], "scenes": [{
            "id": 1, "location": "farm", "lines": [{
                "speaker": "farmer",
                "text": "This very long line describes the plan while the farmer works beside the field.",
                "emotion": "neutral", "action": "talk",
            }],
        }]}
        timeline = [{"scene": 1, "speaker": "farmer", "text": parsed["scenes"][0]["lines"][0]["text"],
                     "emotion": "neutral", "action": "talk", "duration": 2.0}]
        plan = production_director.build_plan(
            parsed, timeline, {"farmer": blend},
            [{"cast": ["farmer"], "action": "talk", "target": -1}],
        )
        direction = plan["lines"][0]["characters"]["farmer"]
        self.assertEqual(direction["dialoguePresentation"]["status"], "action_led_body_only")
        self.assertEqual(direction["dialoguePresentation"]["lipSync"], "none")
        self.assertIn("body_only_dialogue_route", {warning["code"] for warning in plan["warnings"]})
        self.assertEqual(plan["facialAvailability"]["status"], "jaw_only_dialogue_library")

    def test_token_safe_detection_preserves_talk_and_avoids_roman_urdu_substrings(self):
        self.assertEqual(actions.detect("Main har pauday ki dekhbhal karunga."), "none")
        self.assertEqual(actions.detect("I will run toward the gate."), "run")
        entry = {"speaker": "hero", "text": "Main care karunga.",
                 "emotion": "happy", "action": "talk"}
        action, _ = blender3d._line_action(entry, ["hero"], "hero",
                                           {"characters": [{"id": "hero", "name": "Hero"}]})
        self.assertEqual(action, "talk")

    def test_prop_detection_uses_words_and_supports_magic_growth(self):
        false_props = production_director._detect_props({
            "location": "farm", "lines": [{"text": "Tumhari achai ne farm bacha liya."}],
        })
        self.assertNotIn("cup", {item["type"] for item in false_props})
        magic_scene = {
            "location": "Glowing field, morning",
            "lines": [{"text": "Golden seed uthao."},
                      {"text": "Pauday bloom aur glow karte hain."}],
        }
        props = production_director._detect_props(magic_scene)
        self.assertEqual({item["type"] for item in props}, {"seed", "plant"})
        plant = next(item for item in props if item["type"] == "plant")
        start = production_director._prop_state(plant)
        end, consequence = production_director._prop_consequence(
            plant, "celebrate", start, "The plants bloom and glow.")
        self.assertEqual(consequence, "plant_grows_and_glows")
        self.assertEqual(end["growth"], 1.0)
        self.assertGreater(end["glow"], 0)

    def test_farm_story_beats_receive_distinct_visual_variants(self):
        variants = [production_director._environment(scene)["variant"] for scene in (
            {"id": 1, "location": "Village farm, morning"},
            {"id": 2, "location": "Glowing field, morning"},
            {"id": 3, "location": "Blooming farm, afternoon"},
        )]
        self.assertEqual(variants, ["village_farm", "glowing_field", "blooming_farm"])

    def test_verified_nature_dressing_preserves_stateful_story_props(self):
        environment = {"preset": "forest", "variant": "forest_path"}
        dressing = scene_assets.renderer_props(environment, 0)
        self.assertTrue(dressing)
        self.assertTrue(all(item["assetRole"] == "environment_dressing" for item in dressing))
        self.assertTrue(all(item["asset"]["readOnlySource"] for item in dressing))
        # A story interaction remains a stateful renderer prop; imported
        # scenery is additive and never substitutes its animation behaviour.
        scene = {"id": 1, "location": "forest path", "lines": [
            {"text": "A box opens.", "action": "reach"},
        ]}
        self.assertEqual(production_director._detect_props(scene)[0]["type"], "box")

    def test_generic_forest_scenes_progress_through_distinct_world_beats(self):
        scene = {"location": "Forest", "background_prompt": "A forest adventure"}
        variants = [production_director._environment(scene, index)["variant"] for index in range(3)]
        self.assertEqual(variants, ["forest_path", "forest_clearing", "forest_grove"])

    def test_body_only_frame_count_is_audio_driven(self):
        renderer = Path("threejs_render/render_scene.js").read_text(encoding="utf-8")
        page = Path("threejs_render/render_scene.html").read_text(encoding="utf-8")
        self.assertIn("frameCount: Math.max(2", renderer)
        self.assertIn("Number(spec.frameCount) || 0", page)
        self.assertIn("followStrength", page)
        self.assertIn("if (!directedTravel)", page)
        self.assertIn("if (sceneLook === 'indoor')", page)
        self.assertIn("baseMotionClips", page)
        self.assertIn("setEffectiveWeight", page)
        self.assertIn("triggerProgress", page)
        self.assertIn("forest_clearing", page)
        self.assertIn("forest_grove", page)

    def test_threejs_cache_revision_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            video = os.path.join(directory, "line_1.mp4")
            self.assertFalse(blender3d._render_revision_matches(video))
            sidecar = blender3d._write_render_revision(video)
            self.assertTrue(os.path.exists(sidecar))
            self.assertTrue(blender3d._render_revision_matches(video))

    def test_automatic_cast_matches_performance_need(self):
        action_story = story_parser.parse_structured_script(
            "[Scene: Forest]\nHero: (neutral; walk) I will walk ahead.\n"
            "Hero: (excited; run) Now I must run!"
        )
        character_performance.annotate_story_requirements(action_story)
        action_cast = char3d_lib.assign(action_story["characters"])
        self.assertEqual(os.path.basename(action_cast["hero"]), "quaternius_adventurer.blend")

        dialogue_story = story_parser.parse_structured_script(
            "[Scene: Class]\nTeacher: This is an important lesson for everyone today."
        )
        character_performance.annotate_story_requirements(dialogue_story)
        dialogue_cast = char3d_lib.assign(dialogue_story["characters"])
        self.assertEqual(os.path.basename(dialogue_cast["teacher"]), "pencilteacher.blend")

        hybrid_story = story_parser.parse_structured_script(
            "[Scene: Forest]\nHero: (scared; run) I must run to the gate and warn everyone now."
        )
        character_performance.annotate_story_requirements(hybrid_story)
        self.assertEqual(hybrid_story["characters"][0]["performance_need"], "hybrid")
        hybrid_cast = char3d_lib.assign(hybrid_story["characters"])
        self.assertEqual(os.path.basename(hybrid_cast["hero"]), "quaternius_adventurer.blend")


if __name__ == "__main__":
    unittest.main()
