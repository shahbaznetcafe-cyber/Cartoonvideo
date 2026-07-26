"""Characters picked in the Script step must be the ones actually cast.

Without an explicit override the assigner falls back to keyword matching and
then alphabetical round-robin, which is why a pasted script showed a completely
different cast than the cards the user selected.
"""
import unittest

import char3d_lib


class ExplicitCastTests(unittest.TestCase):
    def _chars(self):
        return [{"id": "gajar", "name": "Gajar"}, {"id": "aloo", "name": "Aloo"},
                {"id": "baba", "name": "Baba"}, {"id": "ammi", "name": "Ammi"}]

    def _slugs(self, assignment):
        import os
        return {cid: os.path.splitext(os.path.basename(path))[0]
                for cid, path in assignment.items()}

    def test_picked_characters_win_over_round_robin(self):
        chars = self._chars()
        picked = ["Quaternius Alien", "Quaternius Astronaut FinnTheFrog",
                  "Quaternius Bunny", "Quaternius Casual2 Female"]
        overrides = {c["id"]: n for c, n in zip(chars, picked)}
        slugs = self._slugs(char3d_lib.assign(chars, overrides, library="quaternius"))
        self.assertEqual(slugs["gajar"], "quaternius_alien")
        self.assertEqual(slugs["aloo"], "quaternius_astronaut_finnthefrog")
        self.assertEqual(slugs["baba"], "quaternius_bunny")
        self.assertEqual(slugs["ammi"], "quaternius_casual2_female")

    def test_partial_picks_leave_the_rest_to_matching(self):
        chars = self._chars()
        overrides = {"gajar": "Quaternius Bunny"}
        slugs = self._slugs(char3d_lib.assign(chars, overrides, library="quaternius"))
        self.assertEqual(slugs["gajar"], "quaternius_bunny")
        # the others still get a character, and never duplicate the picked one
        self.assertEqual(len(slugs), 4)
        self.assertEqual(sum(1 for s in slugs.values() if s == "quaternius_bunny"), 1)

    def test_picks_from_the_other_library_are_ignored(self):
        chars = self._chars()[:1]
        # an SBZ name while the quaternius library is selected must not leak in
        overrides = {"gajar": "AngryChili"}
        slugs = self._slugs(char3d_lib.assign(chars, overrides, library="quaternius"))
        self.assertTrue(slugs["gajar"].startswith("quaternius_"))


class PreviewPayloadTests(unittest.TestCase):
    def test_preview_sends_selected_cast(self):
        from pathlib import Path
        js = (Path(__file__).parents[1] / "static/js/studio.js").read_text(encoding="utf-8")
        self.assertIn("function explicitStoryCast", js)
        self.assertIn("selected_cast:explicitStoryCast()", js)

    def test_backend_reads_selected_cast(self):
        from pathlib import Path
        py = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn('data.get("selected_cast")', py)


if __name__ == "__main__":
    unittest.main()
