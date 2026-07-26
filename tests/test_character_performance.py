import unittest
from unittest import mock

import app as app_module
import character_performance
from script_engine.prompts import build_prompt


class CharacterPerformanceTests(unittest.TestCase):
    def test_capability_tiers_have_truthful_speech_and_camera_policy(self):
        body = character_performance.policy_for_tier("SKELETAL_INTERACTIVE", name="Adventurer")
        jaw = character_performance.policy_for_tier("LEGACY_JAW", name="Mascot")
        face = character_performance.policy_for_tier("FULL_FACIAL", name="Future Face")
        self.assertEqual(body["lip_sync"], "none")
        self.assertFalse(body["direct_dialogue"])
        self.assertEqual(jaw["lip_sync"], "jaw_openness")
        self.assertEqual(jaw["camera"], "medium")
        self.assertEqual(face["lip_sync"], "viseme")
        self.assertTrue(face["facial_ready"])

    def test_cast_specific_script_guidance_prevents_fake_facial_writing(self):
        body = character_performance.policy_for_tier("SKELETAL_BASIC", name="Farmer")
        jaw = character_performance.policy_for_tier("LEGACY_JAW", name="PotatoWaistcoat")
        with mock.patch.object(character_performance, "profiles_for_names", return_value=[body, jaw]):
            guidance = character_performance.script_guidance(["Farmer", "PotatoWaistcoat"])
        self.assertIn("Farmer: BODY-ONLY", guidance)
        self.assertIn("PotatoWaistcoat: JAW LIP-SYNC", guidance)
        self.assertIn("natural punctuation", guidance)
        self.assertIn("do not invent missing face controls", guidance)

    def test_dialogue_writer_prompt_receives_performance_contract(self):
        schema = {"type": "object"}
        summary = {"tierPolicies": {"SKELETAL_BASIC": {"lip_sync": "none"}}}
        system, user = build_prompt("DIALOGUE_WRITER", "story", "roman_urdu", schema,
                                    capability_summary=summary)
        self.assertIn("Body-only characters", system)
        self.assertIn("CAPABILITY REGISTRY SNAPSHOT", user)

    def test_script_guidance_lists_only_registered_authored_actions(self):
        guidance = character_performance.script_guidance(["Quaternius Adventurer"])
        self.assertIn("Real authored body directions for Quaternius Adventurer", guidance)
        self.assertIn("walk, run", guidance)
        self.assertIn("reach", guidance)
        self.assertNotIn("wash,", guidance)

    def test_preview_reports_body_only_dialogue_risk(self):
        client = app_module.app.test_client()
        script = ("[Scene: Forest path]\n"
                  "Adventurer: This suspicious box is moving and I need to inspect it carefully!")
        response = client.post("/api/preview", json={"script": script, "character_library": "quaternius"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        adventurer = next(item for item in payload["characters"] if item["name"] == "Adventurer")
        self.assertEqual(adventurer["performance"]["speech_mode"], "body_only")
        self.assertEqual(adventurer["performance"]["lip_sync"], "none")
        self.assertTrue(payload["performance_warnings"])
        self.assertTrue(payload["dialogue_cast_recommendations"])
        self.assertTrue(all(item["lip_sync"] != "none"
                            for item in payload["dialogue_cast_recommendations"]))
        self.assertIn("motion_preflight", payload)
        self.assertTrue(payload["motion_preflight"]["ready"])

    def test_dialogue_route_never_claims_lip_sync_for_body_only_character(self):
        route = character_performance.dialogue_route(
            character_performance.policy_for_tier("SKELETAL_INTERACTIVE", name="Adventurer"),
            "This is a long spoken line that cannot be represented with facial animation.",
        )
        self.assertEqual(route["status"], "action_led_body_only")
        self.assertEqual(route["lipSync"], "none")
        self.assertTrue(route["requiresActionLedStaging"])

    def test_dialogue_recommendations_are_real_non_facial_alternatives(self):
        choices = character_performance.dialogue_cast_recommendations()
        self.assertTrue(choices)
        self.assertTrue(all(choice["tier"] == "LEGACY_JAW" for choice in choices))
        self.assertTrue(all(choice["lip_sync"] == "jaw_openness" for choice in choices))

    def test_mixed_motion_and_speech_is_classified_as_hybrid(self):
        parsed = {"characters": [{"id": "hero", "name": "Hero"}], "scenes": [{"lines": [
            {"speaker": "hero", "text": "I will run to the gate and explain the danger to everyone.",
             "action": "run", "emotion": "scared"},
        ]}]}
        character_performance.annotate_story_requirements(parsed)
        hero = parsed["characters"][0]
        self.assertEqual(hero["performance_need"], "hybrid")
        decision = character_performance.casting_decision(
            hero, character_performance.policy_for_tier("SKELETAL_INTERACTIVE", name="Adventurer"))
        self.assertEqual(decision["route"], "body-led dialogue")
        self.assertEqual(decision["lipSync"], "none")


if __name__ == "__main__":
    unittest.main()
