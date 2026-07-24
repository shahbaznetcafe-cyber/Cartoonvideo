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


class PayoffAndTitleContractTests(unittest.TestCase):
    def _rc(self):
        import retention_critic
        return retention_critic

    def test_unresolved_ending_flags_weak_payoff(self):
        rc = self._rc()
        # Ends on 'worried' — no resolution.
        script = ("A: (excited; point; x) Ruko! Kuch ajeeb hone wala hai abhi.\n"
                  "B: (surprised; walk; x) Kya matlab, dikhao mujhe zara.\n"
                  "A: (worried; reach; x) Pata nahi ye kaise hoga aage.")
        report = rc.analyze(script, hook="Ruko! Kuch ajeeb hone wala hai abhi.")
        self.assertIn("weak_payoff", report["flags"])

    def test_resolved_ending_passes_payoff(self):
        rc = self._rc()
        script = ("A: (excited; point; x) Ruko! Kuch ajeeb hone wala hai abhi.\n"
                  "B: (surprised; walk; x) Kya matlab, dikhao mujhe zara.\n"
                  "A: (relief; celebrate; x) Sab theek ho gaya, shukar hai.")
        report = rc.analyze(script, hook="Ruko! Kuch ajeeb hone wala hai abhi.")
        self.assertNotIn("weak_payoff", report["flags"])

    def test_payoff_check_ignores_cta_line(self):
        rc = self._rc()
        cta = "Comment karo doston abhi!"
        # Real ending is 'proud' (resolved); the CTA after it is 'excited'.
        script = ("A: (excited; point; x) Ruko! Kuch ajeeb hone wala hai abhi.\n"
                  "B: (surprised; walk; x) Kya matlab, dikhao mujhe zara.\n"
                  "A: (proud; celebrate; x) Humne mil kar ye kar dikhaya.\n"
                  f"B: (excited; wave; x) {cta}")
        report = rc.analyze(script, cta=cta,
                            hook="Ruko! Kuch ajeeb hone wala hai abhi.")
        self.assertNotIn("weak_payoff", report["flags"])


class MetadataContractTests(unittest.TestCase):
    def test_promise_and_title_are_injected_into_prompt(self):
        import metadata, providers
        captured = {}
        def fake(system, user, **kw):
            captured["system"] = system
            return ('{"titles":["T1"],"description":"d","tags":["a"],'
                    '"thumbnail_text":"WOW","pinned_comment":"?","chapters":[]}')
        orig = providers.llm_generate
        providers.llm_generate = fake
        try:
            out = metadata.generate("A: (happy; wave; x) Hello dosto kaise ho.",
                                    language="roman_urdu", promise="why kindness wins",
                                    title_hint="The Kind Rabbit")
        finally:
            providers.llm_generate = orig
        self.assertIn("why kindness wins", captured["system"])
        self.assertIn("The Kind Rabbit", captured["system"])
        self.assertEqual(out["titles"], ["T1"])

    def test_metadata_still_works_without_contract(self):
        import metadata, providers
        captured = {}
        def fake(system, user, **kw):
            captured["system"] = system
            return '{"titles":["T"],"description":"d","tags":[],"thumbnail_text":"","pinned_comment":"","chapters":[]}'
        orig = providers.llm_generate
        providers.llm_generate = fake
        try:
            out = metadata.generate("A: (happy; wave; x) Hi.", language="roman_urdu")
        finally:
            providers.llm_generate = orig
        self.assertNotIn("STORY PROMISE", captured["system"])
        self.assertEqual(out["titles"], ["T"])


class EmotionArcAndCtaAnchorTests(unittest.TestCase):
    def _rc(self):
        import retention_critic
        return retention_critic

    def test_beatsheet_exposes_cta_anchor(self):
        brief = duration_planner.writing_brief("1min")
        for genre in beatsheets.BEAT_SHEETS:
            built = beatsheets.build(genre, brief)
            self.assertIn(built["ctaAnchor"], {"after_payoff", "mid_cliffhanger"})

    def test_story_without_any_tension_is_flagged(self):
        rc = self._rc()
        script = ("A: (happy; point; x) Aaj bohat acha din hai yahan.\n"
                  "B: (warm; walk; x) Haan chalo bagh mein chalte hain.\n"
                  "A: (cheerful; reach; x) Phool bohat khoobsurat lag rahe.\n"
                  "B: (proud; celebrate; x) Sab kuch perfect hai bilkul.")
        report = rc.analyze(script)
        self.assertIn("no_tension_beat", report["flags"])

    def test_story_with_tension_passes(self):
        rc = self._rc()
        script = ("A: (happy; point; x) Aaj bohat acha din hai yahan.\n"
                  "B: (worried; walk; x) Lekin raasta band ho gaya hai.\n"
                  "A: (tense; reach; x) Jaldi koi hal nikalna hoga abhi.\n"
                  "B: (relief; celebrate; x) Shukar hai, mil gaya raasta.")
        report = rc.analyze(script)
        self.assertNotIn("no_tension_beat", report["flags"])

    def test_collapsed_arc_flagged_against_plan(self):
        rc = self._rc()
        planned = ["curious", "intrigued", "warm", "worried", "surprised",
                   "tense", "tense", "relief", "warm"]
        script = ("A: (calm; point; x) Pehli baat yahan par hai.\n"
                  "B: (calm; walk; x) Doosri baat udhar par hai.\n"
                  "A: (worried; reach; x) Teesri baat idhar par hai.\n"
                  "B: (calm; celebrate; x) Chauthi baat wahan par hai.")
        report = rc.analyze(script, planned_arc=planned)
        self.assertIn("arc_off_plan", report["flags"])

    def test_arc_following_plan_passes(self):
        rc = self._rc()
        planned = ["curious", "worried", "tense", "relief"]
        script = ("A: (curious; point; x) Ye kya cheez hai yahan par.\n"
                  "B: (worried; walk; x) Mujhe dar lag raha hai ab.\n"
                  "A: (tense; reach; x) Jaldi karo warna der ho jayegi.\n"
                  "B: (relief; celebrate; x) Shukar hai sab theek hua.")
        report = rc.analyze(script, planned_arc=planned)
        self.assertNotIn("arc_off_plan", report["flags"])

    def test_mid_cliffhanger_anchor_flags_cta_at_very_end(self):
        rc = self._rc()
        cta = "Agla part dekhna mat bhoolna!"
        script = ("A: (curious; point; x) Ye kya cheez hai yahan par.\n"
                  "B: (worried; walk; x) Mujhe dar lag raha hai ab.\n"
                  "A: (tense; reach; x) Jaldi karo warna der ho jayegi.\n"
                  "B: (relief; celebrate; x) " + cta)
        report = rc.analyze(script, cta=cta, cta_anchor="mid_cliffhanger")
        self.assertIn("cta_off_anchor", report["flags"])

    def test_after_payoff_anchor_accepts_end_cta(self):
        rc = self._rc()
        cta = "Comment karo doston abhi!"
        script = ("A: (curious; point; x) Ye kya cheez hai yahan par.\n"
                  "B: (worried; walk; x) Mujhe dar lag raha hai ab.\n"
                  "A: (tense; reach; x) Jaldi karo warna der ho jayegi.\n"
                  "B: (relief; celebrate; x) " + cta)
        report = rc.analyze(script, cta=cta, cta_anchor="after_payoff")
        self.assertNotIn("cta_off_anchor", report["flags"])
        self.assertNotIn("cta_too_early", report["flags"])


class SeriesMemoryTests(unittest.TestCase):
    def _data(self):
        return {
            "characters": {
                "aloo": {"id": "aloo", "name": "Aloo", "trait": "brave but silly",
                         "catchphrase": "Aloo zindabad!", "role": "hero",
                         "speech_style": "fast and loud"},
                "tam": {"id": "tam", "name": "Tamatar", "trait": "deadpan",
                        "catchphrase": "", "role": "rival"},
            },
            "series": {
                "sbz": {"id": "sbz", "name": "Sabzi Squad", "premise": "Veg heroes",
                        "genre": "comedy", "language": "roman_urdu",
                        "cast": ["aloo", "tam"],
                        "episodes": [{"num": 1, "title": "Start", "summary": "They met."}]},
            },
        }

    def test_series_memory_is_structured(self):
        import series
        mem = series.series_memory("sbz", data=self._data())
        self.assertEqual(mem["name"], "Sabzi Squad")
        self.assertEqual(sorted(mem["castNames"]), ["Aloo", "Tamatar"])
        self.assertEqual(mem["characters"]["aloo"]["catchphrase"], "Aloo zindabad!")
        self.assertEqual(mem["characters"]["aloo"]["speechStyle"], "fast and loud")
        self.assertEqual(mem["episodeCount"], 1)
        self.assertIn("Episode 1", mem["priorEvents"][0])

    def test_unknown_series_returns_none(self):
        import series
        self.assertIsNone(series.series_memory("nope", data=self._data()))

    def test_memory_block_pins_persona_and_catchphrase(self):
        import series, scriptcraft
        mem = series.series_memory("sbz", data=self._data())
        block = scriptcraft.series_memory_block(mem)
        self.assertIn("Sabzi Squad", block)
        self.assertIn("Aloo", block)
        self.assertIn("Aloo zindabad!", block)
        self.assertIn("fast and loud", block)
        self.assertIn("STORY SO FAR", block)

    def test_memory_block_empty_without_memory(self):
        import scriptcraft
        self.assertEqual(scriptcraft.series_memory_block(None), "")
        self.assertEqual(scriptcraft.series_memory_block({}), "")

    def test_cast_drift_flags_invented_speaker(self):
        import retention_critic as rc
        script = ("Aloo: (excited; point; x) Chalo shuru karte hain abhi.\n"
                  "Gajar: (calm; walk; x) Main naya character hoon yahan.\n"
                  "Tamatar: (relief; celebrate; x) Sab theek ho gaya.")
        report = rc.analyze(script, expected_cast=["Aloo", "Tamatar"])
        self.assertIn("cast_drift", report["flags"])
        self.assertEqual(report["lineJudgements"][1]["retentionRisk"], "high")

    def test_cast_unused_flagged_when_member_silent(self):
        import retention_critic as rc
        script = ("Aloo: (excited; point; x) Chalo shuru karte hain abhi.\n"
                  "Aloo: (relief; celebrate; x) Sab theek ho gaya yaar.")
        report = rc.analyze(script, expected_cast=["Aloo", "Tamatar"])
        self.assertIn("cast_unused", report["flags"])

    def test_on_cast_script_has_no_drift_flags(self):
        import retention_critic as rc
        script = ("Aloo: (excited; point; x) Chalo shuru karte hain abhi.\n"
                  "Tamatar: (worried; walk; x) Lekin raasta band hai yahan.\n"
                  "Aloo: (relief; celebrate; x) Shukar hai hal mil gaya.")
        report = rc.analyze(script, expected_cast=["Aloo", "Tamatar"])
        self.assertNotIn("cast_drift", report["flags"])
        self.assertNotIn("cast_unused", report["flags"])


class ReviewPanelContractTests(unittest.TestCase):
    """Phase 6 — the review UI must be wired end to end (markup, styles, JS)."""

    def _read(self, rel):
        from pathlib import Path
        return (Path(__file__).parents[1] / rel).read_text(encoding="utf-8")

    def test_flag_notes_pair_flags_with_human_wording(self):
        import retention_critic as rc
        report = {"flags": ["hook_not_first", "cta_missing", "unknown_flag"]}
        notes = rc.flag_notes(report)
        self.assertEqual([n["flag"] for n in notes], ["hook_not_first", "cta_missing"])
        self.assertTrue(all(n["note"] for n in notes))

    def test_template_has_retention_panel(self):
        html = self._read("templates/index.html")
        self.assertIn('id="retentionPanel"', html)

    def test_styles_define_panel_and_hook_option(self):
        css = self._read("static/css/studio.css")
        self.assertIn(".retention-panel", css)
        self.assertIn(".hook-option", css)

    def test_js_renders_panel_and_applies_hook(self):
        js = self._read("static/js/studio.js")
        self.assertIn("function renderRetentionPanel", js)
        self.assertIn("function applyHookChoice", js)
        # every generator surfaces the review data
        self.assertGreaterEqual(js.count("renderRetentionPanel(j)"), 4)
        # honesty note shown to the creator
        self.assertIn("YouTube Analytics", js)


class LongformSmokeTests(unittest.TestCase):
    """Regression: the long-form path must not blow up on a missing import."""

    def test_generate_longform_runs_with_stub_provider(self):
        import providers, story_templates
        def fake(system, user, **kw):
            s = (system or "").lower()
            if "outline" in s or "plan" in s or "scenes" in s:
                return ('{"title":"T","logline":"L","genre":"adventure",'
                        '"cast":[{"name":"Ali","voice":"brave"}],'
                        '"scenes":[{"location":"Street","goal":"g1"},'
                        '{"location":"Market","goal":"g2"}]}')
            return ("[Scene: Street]\n"
                    "Ali: (excited; walk; street) Aaj main sab ki madad karunga zaroor.\n"
                    "Ali: (proud; run; street) Chalo jaldi chalte hain unko bachane.")
        original = providers.llm_generate
        providers.llm_generate = fake
        try:
            result = story_templates.generate_longform(
                "a hero helps the city", language="urdu", minutes="2min", genre="auto")
        finally:
            providers.llm_generate = original
        self.assertTrue(result.get("script"))
        self.assertIn("title", result)

    def test_key_modules_import_every_stdlib_name_they_use(self):
        import ast, importlib
        watched = {"re", "json", "os", "sys", "time", "hashlib", "subprocess"}
        for name in ("story_templates", "scriptcraft", "beatsheets", "hooklab",
                     "retention_critic", "series", "metadata"):
            module = importlib.import_module(name)
            tree = ast.parse(open(module.__file__, encoding="utf-8").read())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add((alias.asname or alias.name).split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imported.add(alias.asname or alias.name)
            local = {n.name for n in tree.body
                     if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            missing = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    used = node.value.id
                    if used in watched and used not in imported and used not in local:
                        missing.add(used)
            self.assertFalse(missing, f"{name} uses {sorted(missing)} without importing it")


if __name__ == "__main__":
    unittest.main()
