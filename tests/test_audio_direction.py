import unittest

import audio
import voice_profiles
import app as app_module


class AudioDirectionTests(unittest.TestCase):
    def test_local_catalog_has_unique_safe_ids(self):
        catalog = audio.music_catalog()
        ids = [track["id"] for track in catalog]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(".." not in track_id for track_id in ids))

    def test_manual_music_only_accepts_catalog_track(self):
        catalog = audio.music_catalog()
        if catalog:
            chosen = audio.select_music(["comedy"], catalog[0]["id"])
            self.assertEqual(chosen, catalog[0]["path"])
        self.assertIsNone(audio._manual_track("../outside.mp3"))

    def test_music_endpoint_returns_catalog(self):
        client = app_module.app.test_client()
        response = client.get("/api/music")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("tracks", payload)
        self.assertIn("selected", payload)
    def test_character_profiles_are_stable_and_distinct(self):
        playful = voice_profiles.profile_for_character({"name": "Quaternius Bunny"})
        mysterious = voice_profiles.profile_for_character({"name": "Quaternius BlueDemon"})
        self.assertEqual(playful["id"], "playful")
        self.assertEqual(mysterious["id"], "mysterious")
        self.assertNotEqual(playful["pitch"], mysterious["pitch"])

    def test_natural_pause_pass_preserves_words_and_terminal_mark(self):
        result = voice_profiles.add_natural_pauses("Aao phir chalte hain lekin dheere", "roman_urdu")
        self.assertIn("phir", result)
        self.assertIn("lekin", result)
        self.assertTrue(result.endswith("."))


if __name__ == "__main__":
    unittest.main()