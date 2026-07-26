"""One unrenderable line must not abort an otherwise-finished video.

Covers the static fallback clip and the validity floor that accepts it, without
invoking the 3D renderer (headless WebGL is environment-dependent).
"""
import os
import subprocess
import tempfile
import unittest

import blender3d


def _silent_audio(path, seconds=2.0):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=mono", "-t", f"{seconds}", path,
                    "-loglevel", "error"], check=True)


class StaticFallbackTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.audio = os.path.join(self.dir, "a.mp3")
        _silent_audio(self.audio, 2.0)

    def test_solid_fallback_clip_is_valid(self):
        out = os.path.join(self.dir, "solid.mp4")
        blender3d._static_line_clip(out, self.audio, None, 640, 360, 24, 2.0)
        self.assertTrue(os.path.exists(out))
        self.assertTrue(blender3d._clip_is_valid(out, self.audio, 24,
                                                 expected_size=(640, 360)))

    def test_background_fallback_clip_is_valid(self):
        bg = os.path.join(self.dir, "bg.png")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                        "-i", "color=c=green:s=1280x720", "-frames:v", "1", bg,
                        "-loglevel", "error"], check=True)
        out = os.path.join(self.dir, "bg.mp4")
        blender3d._static_line_clip(out, self.audio, bg, 640, 360, 24, 2.0)
        self.assertTrue(blender3d._clip_is_valid(out, self.audio, 24,
                                                 expected_size=(640, 360)))

    def test_fallback_matches_audio_duration(self):
        out = os.path.join(self.dir, "solid.mp4")
        blender3d._static_line_clip(out, self.audio, None, 640, 360, 24, 2.0)
        self.assertAlmostEqual(blender3d._probe_duration(out), 2.0, delta=0.15)

    def test_junk_file_still_rejected(self):
        junk = os.path.join(self.dir, "junk.mp4")
        with open(junk, "wb") as handle:
            handle.write(b"\x00" * 800)
        self.assertFalse(blender3d._clip_is_valid(junk, self.audio, 24,
                                                  expected_size=(640, 360)))

    def test_has_frames_detects_empty_and_populated(self):
        self.assertFalse(blender3d._has_frames(self.dir))
        open(os.path.join(self.dir, "frame_0001.png"), "wb").close()
        self.assertTrue(blender3d._has_frames(self.dir))


if __name__ == "__main__":
    unittest.main()
