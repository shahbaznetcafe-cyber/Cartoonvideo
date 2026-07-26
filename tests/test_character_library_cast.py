import unittest
from unittest import mock

import story_templates


class CharacterLibraryCastTests(unittest.TestCase):
    @mock.patch.object(story_templates, "available_characters")
    def test_quaternius_library_never_falls_back_to_sbz_originals(self, available):
        available.return_value = [
            {"name": "Tamatar", "library": "sbz"},
            {"name": "Mirch", "library": "sbz"},
            {"name": "Quaternius BlueDemon", "library": "quaternius"},
            {"name": "Quaternius Witch", "library": "quaternius"},
        ]
        cast = story_templates.resolve_script_cast(
            ["Tamatar", "Mirch"], library="quaternius")
        self.assertEqual(cast, ["Quaternius BlueDemon", "Quaternius Witch"])

    @mock.patch.object(story_templates, "available_characters")
    def test_selected_quaternius_character_is_preserved(self, available):
        available.return_value = [
            {"name": "Tamatar", "library": "sbz"},
            {"name": "Quaternius BlueDemon", "library": "quaternius"},
            {"name": "Quaternius Witch", "library": "quaternius"},
        ]
        cast = story_templates.resolve_script_cast(
            ["Quaternius BlueDemon", "Tamatar"], library="quaternius")
        self.assertEqual(cast, ["Quaternius BlueDemon"])


if __name__ == "__main__":
    unittest.main()