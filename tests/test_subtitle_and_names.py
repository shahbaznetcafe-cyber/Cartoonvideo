"""Burned subtitles must be readable, and asset labels must not become names.

Two defects seen in a rendered video:
  * captions covered most of the frame (force_style FontSize is interpreted in
    the subtitle script's resolution, not video pixels);
  * a character was literally called "Quaternius Chicken".
"""
import os
import re
import subprocess
import tempfile
import unittest

import blender3d
import scriptcraft


class AssSubtitleTests(unittest.TestCase):
    def _timeline(self):
        return [{"text": "Warning? Kya likha hai? Koi bomb ka joke toh nahi?", "duration": 4.0},
                {"text": "Mujhe dar lag raha hai.", "duration": 3.0}]

    def test_ass_declares_the_real_video_resolution(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.ass")
            blender3d._build_ass(self._timeline(), path, 1920, 1080, "Arial", 41)
            text = open(path, encoding="utf-8").read()
            # Without these, libass scales FontSize by height/288 (~3.75x).
            self.assertIn("PlayResX: 1920", text)
            self.assertIn("PlayResY: 1080", text)
            self.assertIn("Fontsize", text)
            self.assertIn("Style: Default,Arial,41,", text)

    def test_events_are_written_with_ass_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.ass")
            blender3d._build_ass(self._timeline(), path, 1280, 720, "Arial", 27)
            text = open(path, encoding="utf-8").read()
            self.assertEqual(text.count("Dialogue: "), 2)
            self.assertIn("0:00:00.00,0:00:04.00", text)

    def test_braces_and_newlines_are_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.ass")
            blender3d._build_ass([{"text": "a {b} c", "duration": 2.0}], path,
                                 1280, 720, "Arial", 27)
            text = open(path, encoding="utf-8").read()
            self.assertNotIn("{b}", text)   # would be read as an ASS override tag

    def _text_coverage(self, font_size):
        """Fraction of a 1080p frame covered by white caption pixels."""
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            blender3d._build_ass(self._timeline(), os.path.join(d, "s.ass"),
                                 1920, 1080, "Arial", font_size)
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                            "-i", "color=c=black:s=1920x1080:r=24", "-t", "3",
                            "-vf", "subtitles=s.ass", "-frames:v", "1", "f.png",
                            "-loglevel", "error"], cwd=d, check=True)
            with Image.open(os.path.join(d, "f.png")) as image:
                pixels = list(image.convert("L").getdata())
            return sum(1 for value in pixels if value > 128) / len(pixels)

    def test_caption_occupies_a_small_share_of_the_frame(self):
        coverage = self._text_coverage(max(20, 1080 // 26))
        self.assertGreater(coverage, 0, "captions did not render at all")
        self.assertLess(coverage, 0.02,
                        f"captions cover {coverage:.2%} of the frame")

    def test_the_measurement_would_catch_the_old_oversized_caption(self):
        """Guard the guard: the old ~184px effective size must fail the check."""
        self.assertGreater(self._text_coverage(184), 0.05)


class StoryNameTests(unittest.TestCase):
    def test_library_prefix_is_stripped(self):
        self.assertEqual(scriptcraft.story_name("Quaternius Chicken"), "Chicken")
        self.assertEqual(scriptcraft.story_name("Quaternius Cow"), "Cow")
        self.assertEqual(scriptcraft.story_name("SBZ Originals AngryChili"), "AngryChili")

    def test_asset_numbering_is_removed(self):
        self.assertEqual(scriptcraft.story_name("Quaternius Casual2 Female"), "Casual Female")

    def test_plain_names_are_untouched(self):
        self.assertEqual(scriptcraft.story_name("BiryaniBaba"), "BiryaniBaba")

    def test_blank_input_is_safe(self):
        self.assertEqual(scriptcraft.story_name(""), "")
        self.assertEqual(scriptcraft.story_name(None), "")


if __name__ == "__main__":
    unittest.main()
