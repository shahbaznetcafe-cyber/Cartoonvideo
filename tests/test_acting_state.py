import json
import os
import tempfile
import unittest

import acting_state


class ActingStateTests(unittest.TestCase):
    def _inputs(self):
        timeline = [
            {"scene": "garden", "speaker": "hero", "text": "Walk with me",
             "emotion": "neutral", "duration": 2.0},
            {"scene": "garden", "speaker": "friend", "text": "Wonderful!",
             "emotion": "happy", "duration": 1.5},
            {"scene": "garden", "speaker": "hero", "text": "Are you ready?",
             "emotion": "surprise", "duration": 1.0},
        ]
        contexts = [
            {"cast": ["hero", "friend"], "action": "walk", "target": 1},
            {"cast": ["hero", "friend"], "action": "celebrate", "target": 0},
            {"cast": ["hero", "friend"], "action": "none", "target": 1},
        ]
        return timeline, contexts

    def test_previous_end_is_next_start_and_position_persists(self):
        timeline, contexts = self._inputs()
        plan = acting_state.build_plan(timeline, contexts, fps=24)
        first_end = plan["lines"][0]["characters"]["hero"]["end"]
        next_start = plan["lines"][1]["characters"]["hero"]["start"]
        third_start = plan["lines"][2]["characters"]["hero"]["start"]
        self.assertEqual(first_end, next_start)
        self.assertEqual(first_end["position"]["x"], 0.34)
        self.assertEqual(third_start["position"]["x"], 0.34)

    def test_listeners_receive_story_motivated_reactions(self):
        timeline, contexts = self._inputs()
        plan = acting_state.build_plan(timeline, contexts)
        first_listener = plan["lines"][0]["characters"]["friend"]
        happy_listener = plan["lines"][1]["characters"]["hero"]
        question_listener = plan["lines"][2]["characters"]["friend"]
        self.assertEqual(first_listener["role"], "listener")
        self.assertEqual(first_listener["reaction"], "attend")
        self.assertEqual(happy_listener["reaction"], "encourage")
        self.assertEqual(question_listener["reaction"], "surprise")
        self.assertGreater(first_listener["reactionStrength"], 0)

    def test_plan_and_saved_json_are_deterministic(self):
        timeline, contexts = self._inputs()
        first = acting_state.build_plan(timeline, contexts, fps=24)
        second = acting_state.build_plan(timeline, contexts, fps=24)
        self.assertEqual(first, second)
        self.assertEqual([line["timeOffset"] for line in first["lines"]], [0.0, 2.0, 3.5])
        with tempfile.TemporaryDirectory() as directory:
            path = acting_state.write_plan(directory, first)
            with open(path, encoding="utf-8") as handle:
                saved = json.load(handle)
            self.assertEqual(saved, first)
            self.assertFalse(os.path.exists(path + ".tmp"))

    def test_invalid_context_count_is_rejected(self):
        timeline, _ = self._inputs()
        with self.assertRaises(ValueError):
            acting_state.build_plan(timeline, [])


if __name__ == "__main__":
    unittest.main()
