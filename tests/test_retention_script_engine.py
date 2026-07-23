"""Phase 1 retention engine: deterministic tests for beat sheets + hook scoring.

These prove the machinery (word-budget math, genre routing, hook combiner) is
correct.  They do NOT and cannot prove real-world retention — only YouTube
Analytics on real uploads can.  No LLM or network is touched here.
"""
import unittest

import beatsheets
import hooklab
import duration_planner


class BeatSheetTests(unittest.TestCase):
    def test_genre_routing_covers_aliases_and_templates(self):
        self.assertEqual(beatsheets.resolve_genre("moral"), "moral_story")
        self.assertEqual(beatsheets.resolve_genre("funny_mixup"), "comedy_skit")
        self.assertEqual(beatsheets.resolve_genre("pirate_treasure"), "adventure")
        self.assertEqual(beatsheets.resolve_genre("mystery_case"), "mystery")
        self.assertEqual(beatsheets.resolve_genre("teamwork_challenge"), "friendship")
        self.assertEqual(beatsheets.resolve_genre("learning_by_doing"), "learning")
        # unknown -> default, never crash
        self.assertEqual(beatsheets.resolve_genre("zzz"), beatsheets.DEFAULT_GENRE)
        self.assertEqual(beatsheets.resolve_genre(None), beatsheets.DEFAULT_GENRE)
        # substring fallback
        self.assertEqual(beatsheets.resolve_genre("space adventure quest"), "adventure")

    def test_word_budget_sums_exactly_to_brief_for_every_genre_and_length(self):
        for length in ("30sec", "1min", "2min", "5min"):
            brief = duration_planner.writing_brief(length)
            for genre in beatsheets.BEAT_SHEETS:
                built = beatsheets.build(genre, brief)
                self.assertEqual(
                    built["totalWords"], brief["target_words"],
                    f"{genre}/{length}: {built['totalWords']} != {brief['target_words']}")
                # every beat keeps a usable minimum
                self.assertTrue(all(b["words"] >= 3 for b in built["beats"]))

    def test_allocator_is_deterministic_and_floored(self):
        a = beatsheets._allocate_words([1, 1, 1], 10)
        b = beatsheets._allocate_words([1, 1, 1], 10)
        self.assertEqual(a, b)
        self.assertEqual(sum(a), 10)
        # tiny budget still respects the floor and exact sum
        c = beatsheets._allocate_words([1, 2, 3, 4], 12, floor=3)
        self.assertEqual(sum(c), 12)
        self.assertTrue(all(x >= 3 for x in c))

    def test_built_sheet_exposes_emotion_arc_and_prompt_text(self):
        brief = duration_planner.writing_brief("1min")
        built = beatsheets.build("moral_story", brief)
        self.assertEqual(len(built["emotionArc"]), len(built["beats"]))
        self.assertIn("cold_open", built["beats"][0]["type"])
        text = beatsheets.as_prompt_lines(built)
        self.assertIn("[cold_open]", text)
        self.assertIn("words", text)


class HookScoringTests(unittest.TestCase):
    def _hook(self, text, angle, **scores):
        return {"text": text, "angle": angle, "scores": scores}

    def test_higher_rubric_scores_rank_first(self):
        hooks = [
            self._hook("weak", "question", curiosity=2, clarity=3, emotion=2,
                       promiseMatch=2, sayable=5, childSafe=10),
            self._hook("strong", "shock", curiosity=9, clarity=9, emotion=9,
                       promiseMatch=8, sayable=9, childSafe=10),
        ]
        ranked = hooklab.score_hooks(hooks)
        self.assertEqual(ranked[0]["text"], "strong")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertGreater(ranked[0]["total"], ranked[1]["total"])

    def test_child_unsafe_hook_is_deprioritised_even_if_catchy(self):
        hooks = [
            self._hook("catchy but unsafe", "shock", curiosity=10, clarity=10,
                       emotion=10, promiseMatch=10, sayable=10, childSafe=1),
            self._hook("safe and decent", "question", curiosity=6, clarity=6,
                       emotion=6, promiseMatch=6, sayable=6, childSafe=10),
        ]
        ranked = hooklab.score_hooks(hooks)
        self.assertEqual(ranked[0]["text"], "safe and decent")

    def test_perfect_scores_on_ten_scale_give_total_one(self):
        hooks = [self._hook("h", "question", curiosity=10, clarity=10,
                            emotion=10, promiseMatch=10, sayable=10, childSafe=10)]
        ranked = hooklab.score_hooks(hooks)
        self.assertAlmostEqual(ranked[0]["total"], 1.0, places=4)

    def test_out_of_range_scores_are_clamped(self):
        hooks = [self._hook("h", "question", curiosity=99, clarity=-5,
                            emotion=10, promiseMatch=10, sayable=10, childSafe=10)]
        ranked = hooklab.score_hooks(hooks)
        self.assertLessEqual(ranked[0]["total"], 1.0)
        self.assertGreaterEqual(ranked[0]["total"], 0.0)

    def test_ties_break_by_original_order(self):
        s = dict(curiosity=5, clarity=5, emotion=5, promiseMatch=5, sayable=5, childSafe=10)
        hooks = [self._hook("first", "question", **s), self._hook("second", "shock", **s)]
        ranked = hooklab.score_hooks(hooks)
        self.assertEqual([h["text"] for h in ranked], ["first", "second"])

    def test_generate_and_score_falls_back_without_provider(self):
        class BoomProvider:
            def llm_generate(self, *a, **k):
                raise RuntimeError("no network")
        result = hooklab.generate_and_score(
            BoomProvider(), "a kind rabbit", "kindness wins", "Roman Urdu",
            fallback_hook="Ek din...")
        self.assertEqual(result["hook"], "Ek din...")
        self.assertEqual(result["ranking"], [])

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(hooklab.RUBRIC_WEIGHTS.values()), 1.0, places=6)


class RetentionCriticTests(unittest.TestCase):
    def _rc(self):
        import retention_critic
        return retention_critic

    def test_parse_extracts_speaker_emotion_action(self):
        rc = self._rc()
        script = ("[Scene: Jungle]\n"
                  "Kachwa: (calm; walk; path) Main dheere chalta hoon.\n"
                  "Khargosh: (proud; none; path) Main tez hoon!")
        parsed = rc.parse_script(script)
        self.assertEqual(parsed["scene"].lower().startswith("[scene"), True)
        self.assertEqual(len(parsed["lines"]), 2)
        self.assertEqual(parsed["lines"][0]["speaker"], "Kachwa")
        self.assertEqual(parsed["lines"][0]["emotion"], "calm")
        self.assertTrue(parsed["lines"][0]["hasAction"])
        self.assertFalse(parsed["lines"][1]["hasAction"])   # action 'none'

    def test_hook_not_first_is_flagged(self):
        rc = self._rc()
        script = ("Aloo: (calm; walk; dhaba) Aaj mausam acha hai.\n"
                  "Tamatar: (happy; point; dhaba) Chalo khelte hain.")
        report = rc.analyze(script, hook="Ruko! Kisne meri chai mein cheeni daali?")
        self.assertIn("hook_not_first", report["flags"])
        self.assertEqual(report["lineJudgements"][0]["retentionRisk"], "high")

    def test_hook_present_first_passes(self):
        rc = self._rc()
        hook = "Ruko! Kisne meri chai mein cheeni daali?"
        script = (f"Aloo: (excited; point; dhaba) {hook}\n"
                  "Tamatar: (smug; walk; dhaba) Maine namak daala tha.")
        report = rc.analyze(script, hook=hook)
        self.assertNotIn("hook_not_first", report["flags"])

    def test_static_talking_heads_flagged(self):
        rc = self._rc()
        script = ("A: (calm; none; room) Line one alag baat.\n"
                  "B: (happy; none; room) Line two doosri baat.")
        report = rc.analyze(script)
        self.assertIn("static_talking_heads", report["flags"])

    def test_flat_arc_flagged(self):
        rc = self._rc()
        script = ("A: (calm; walk; x) Pehli alag baat idhar.\n"
                  "B: (calm; point; x) Doosri nayi baat udhar.\n"
                  "A: (calm; reach; x) Teesri aur baat yahan.")
        report = rc.analyze(script)
        self.assertTrue(report["arcFlatness"])
        self.assertIn("flat_arc", report["flags"])

    def test_duplicate_lines_flagged_high_risk(self):
        rc = self._rc()
        script = ("A: (calm; walk; x) Chalo ghar chalte hain abhi.\n"
                  "B: (happy; point; x) Chalo ghar chalte hain abhi.")
        report = rc.analyze(script)
        self.assertIn("duplicate_lines", report["flags"])
        self.assertEqual(report["lineJudgements"][1]["retentionRisk"], "high")

    def test_cta_too_early_flagged(self):
        rc = self._rc()
        cta = "Comment karo apna jawab!"
        script = (f"A: (excited; point; x) {cta}\n"
                  "B: (calm; walk; x) Phir kahani shuru hoti hai.\n"
                  "A: (happy; reach; x) Aur aage badhti hai yahan.\n"
                  "B: (proud; celebrate; x) Aakhir mein sab khush hain.")
        report = rc.analyze(script, cta=cta)
        self.assertIn("cta_too_early", report["flags"])

    def test_clean_script_has_no_flags_and_empty_fixes(self):
        rc = self._rc()
        hook = "Ruko! Aaj kuch ajeeb hone wala hai."
        cta = "Aap batao, comment karo!"
        script = (f"Aloo: (excited; point; dhaba) {hook}\n"
                  "Tamatar: (surprised; walk; dhaba) Kya matlab, dikhao mujhe.\n"
                  "Aloo: (worried; reach; market) Dekho wahan kuch gir gaya.\n"
                  "Tamatar: (shocked; run; market) Jaldi chalo bachane!\n"
                  "Aloo: (relieved; celebrate; market) Bach gaya, shukar hai.\n"
                  f"Tamatar: (happy; wave; market) {cta}")
        report = rc.analyze(script, hook=hook, cta=cta)
        self.assertEqual(report["flags"], [])
        self.assertEqual(rc.fix_instructions(report), "")

    def test_fix_instructions_are_targeted(self):
        rc = self._rc()
        script = ("A: (calm; none; x) Aaj mausam acha hai bilkul.\n"
                  "B: (calm; none; x) Aaj mausam acha hai bilkul.")
        report = rc.analyze(script, hook="Ruko! Dhamaka hone wala hai.")
        fixes = rc.fix_instructions(report)
        self.assertIn("hook", fixes.lower())
        self.assertIn("-", fixes)   # bulleted directives


if __name__ == "__main__":
    unittest.main()
