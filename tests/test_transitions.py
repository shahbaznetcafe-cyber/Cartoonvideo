import unittest

import transitions


def entry(scene, speaker="a", **values):
    data = {"scene": scene, "speaker": speaker, "text": "A line", "mood": "comedy"}
    data.update(values)
    return data


class TransitionTests(unittest.TestCase):
    def test_dialogue_uses_clean_cuts_by_default(self):
        plan = transitions.plan_transitions([
            entry(1, "a"),
            entry(1, "b"),
            entry(2, "a"),
        ])
        self.assertEqual([item["type"] for item in plan], ["hard_cut", "hard_cut"])
        self.assertTrue(all(item["duration"] == 0.0 for item in plan))

    def test_visible_transitions_are_motivated_and_duration_is_clamped(self):
        whip = transitions.choose_transition(
            entry(1), entry(2, transition="whip_pan", transition_duration=2.0))
        fade = transitions.choose_transition(
            entry(1, time="day"), entry(2, time="night"))
        dissolve = transitions.choose_transition(
            entry(1, "narrator", mood="emotional"),
            entry(2, "a", mood="emotional"),
            default_duration=0.4,
        )

        self.assertEqual(whip["type"], "whip_pan")
        self.assertEqual(whip["duration"], transitions.MAX_DURATION)
        self.assertEqual(fade["type"], "fade")
        self.assertEqual(dissolve["type"], "short_dissolve")
        self.assertLessEqual(dissolve["duration"], transitions.MAX_DURATION)
        self.assertGreaterEqual(dissolve["duration"], transitions.MIN_DURATION)

    def test_match_cut_remains_an_instant_cut(self):
        item = transitions.choose_transition(
            entry(1), entry(2, transition="match cut", transition_duration=0.5))
        self.assertEqual(item["type"], "match_cut")
        self.assertEqual(item["duration"], 0.0)
        self.assertIsNone(item["ffmpeg"])

    def test_mixed_filter_graph_and_timeline_starts(self):
        plan = [
            transitions.decision("hard_cut"),
            transitions.decision("whip_pan", 0.2),
        ]
        filters, video, audio, total = transitions.build_av_filter_graph(
            [2.0, 3.0, 4.0], plan)
        graph = ";".join(filters)

        self.assertIn("concat=n=2:v=1:a=0", graph)
        self.assertIn("xfade=transition=slideleft:duration=0.200", graph)
        self.assertIn("acrossfade=d=0.200", graph)
        self.assertEqual(video, "vstep2")
        self.assertEqual(audio, "astep2")
        self.assertAlmostEqual(total, 8.8)
        starts = transitions.timeline_starts([2.0, 3.0, 4.0], plan, 1.0)
        for actual, expected in zip(starts, [1.0, 3.0, 5.8]):
            self.assertAlmostEqual(actual, expected)

    def test_plan_length_is_validated(self):
        with self.assertRaises(ValueError):
            transitions.build_av_filter_graph([1.0, 1.0], [])


if __name__ == "__main__":
    unittest.main()
