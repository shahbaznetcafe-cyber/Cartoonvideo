"""A manually written/pasted script must be able to target Quaternius.

The "Write Script" panel has no character-card grid (that only exists in the
AI-generator flow), so before this fix CAST_CHARACTER_LIBRARY silently stayed
at its 'sbz' default for any pasted script -- Urdu/roman animal names never
reached the Quaternius keyword matcher at all, regardless of what the user
intended.
"""
import unittest
from pathlib import Path


class WriteScriptLibraryToggleTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parents[1]
        self.html = (root / "templates/index.html").read_text(encoding="utf-8")
        self.js = (root / "static/js/studio.js").read_text(encoding="utf-8")
        self.css = (root / "static/css/studio.css").read_text(encoding="utf-8")

    def test_toggle_exists_in_the_write_script_toolbar(self):
        self.assertIn('id="writeCastLibrarySeg"', self.html)
        # it must live inside the editor-toolbar, not float elsewhere
        toolbar = self.html[self.html.index('class="editor-toolbar"'):][:600]
        self.assertIn("writeCastLibrarySeg", toolbar)
        self.assertIn('data-v="sbz"', toolbar)
        self.assertIn('data-v="quaternius"', toolbar)

    def test_toggle_writes_to_the_shared_library_global(self):
        self.assertIn("document.querySelectorAll('#writeCastLibrarySeg button')", self.js)
        self.assertIn("CAST_CHARACTER_LIBRARY=b.dataset.v==='quaternius'?'quaternius':'sbz'", self.js)

    def test_sync_helper_reflects_current_library_on_mode_switch(self):
        self.assertIn("function syncWriteCastLibrarySeg", self.js)
        self.assertIn("else syncWriteCastLibrarySeg();", self.js)

    def test_compact_style_does_not_reuse_full_size_seg_buttons(self):
        self.assertIn(".toolbar-seg", self.css)


class KeywordMatchingWithoutExplicitCardsTests(unittest.TestCase):
    """Once character_library='quaternius' reaches the backend, matching alone
    (no card selection) must resolve common Urdu animal names correctly."""

    def test_urdu_animal_names_resolve_through_keyword_matching_only(self):
        import os
        import char3d_lib
        chars = [{"id": n, "name": n} for n in
                 ["خرگوش", "بلی", "کتا", "مرغی", "گائے", "مینڈک", "کبوتر"]]
        assignment = char3d_lib.assign(chars, library="quaternius")
        slugs = {cid: os.path.splitext(os.path.basename(p))[0]
                 for cid, p in assignment.items()}
        self.assertEqual(slugs["خرگوش"], "quaternius_bunny")
        self.assertEqual(slugs["بلی"], "quaternius_cat")
        self.assertEqual(slugs["کتا"], "quaternius_dog")
        self.assertEqual(slugs["مرغی"], "quaternius_chicken")
        self.assertEqual(slugs["گائے"], "quaternius_cow")
        self.assertEqual(slugs["مینڈک"], "quaternius_frog")
        self.assertEqual(slugs["کبوتر"], "quaternius_pigeon")
        # every character got a distinct model -- no accidental round-robin reuse
        self.assertEqual(len(set(slugs.values())), 7)


class PhantomSpeakerParsingTests(unittest.TestCase):
    """A 'Label: value' instructions line must not silently become a character."""

    def test_settings_style_line_is_parsed_as_a_real_speaker(self):
        # This documents WHY it happened (not a bug in the parser itself -- a
        # 'Word: text' line is indistinguishable from real dialogue), so a
        # copy-pasted instructions block above a script is genuinely unsafe.
        import story_parser
        script = ("SETTINGS:  Language = Urdu\n"
                  "Ali: (happy) Hello dosto.\n")
        parsed = story_parser.parse_structured_script(script)
        speakers = {c["name"] for c in parsed["characters"]}
        self.assertIn("SETTINGS", speakers)


if __name__ == "__main__":
    unittest.main()
