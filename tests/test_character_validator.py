import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
import character_validator as validator
import char3d_lib


def _write_glb(path, bones=(), morphs=(), *, skinned=True, mesh=True):
    nodes = [{"name": name} for name in bones]
    meshes = []
    skins = []
    if mesh:
        target_names = list(morphs)
        primitive = {"attributes": {}}
        if target_names:
            primitive["targets"] = [{} for _ in target_names]
        meshes.append({
            "name": "FaceMesh",
            "primitives": [primitive],
            "extras": {"targetNames": target_names},
        })
        mesh_node = {"name": "CharacterMesh", "mesh": 0}
        if skinned:
            skins.append({"name": "Armature", "joints": list(range(len(bones)))})
            mesh_node["skin"] = 0
        nodes.append(mesh_node)

    document = {
        "asset": {"version": "2.0", "generator": "SBZ unit test"},
        "scene": 0,
        "scenes": [{"nodes": [len(nodes) - 1] if nodes else []}],
        "nodes": nodes,
        "meshes": meshes,
        "skins": skins,
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    chunk = struct.pack("<II", len(payload), 0x4E4F534A) + payload
    data = struct.pack("<4sII", b"glTF", 2, 12 + len(chunk)) + chunk
    Path(path).write_bytes(data)


class CharacterValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def path(self, name="character.glb"):
        return Path(self.temp.name, name)

    def test_invalid_glb_is_detected_without_supported_tier(self):
        path = self.path()
        path.write_bytes(b"not a glb")
        report = validator.validate_glb(path)
        self.assertFalse(report["valid_glb"])
        self.assertIsNone(report["tier"])
        self.assertEqual(report["compatibility_percent"], 0)
        self.assertEqual(report["errors"][0]["code"], "truncated_header")

    def test_legacy_six_bone_character_keeps_jaw_fallback(self):
        path = self.path()
        _write_glb(path, validator.LEGACY_BODY_BONES)
        report = validator.validate_glb(path)
        self.assertTrue(report["valid_glb"])
        self.assertEqual(report["tier"], "LEGACY_JAW")
        self.assertEqual(report["body"]["legacy"]["missing"], [])
        self.assertIn("legacy_jaw_fallback", [w["code"] for w in report["warnings"]])

    def test_mixamo_skeleton_without_visemes_is_skeletal_basic(self):
        path = self.path()
        _write_glb(path, validator.MIXAMO_CORE_BONES)
        report = validator.validate_glb(path)
        self.assertEqual(report["tier"], "SKELETAL_BASIC")
        self.assertTrue(report["mixamo_compatible"])
        self.assertEqual(report["visemes"]["present"], [])

    def test_complete_visemes_without_facial_set_is_viseme_face(self):
        path = self.path()
        _write_glb(path, validator.MIXAMO_CORE_BONES, validator.REQUIRED_VISEMES)
        report = validator.validate_glb(path)
        self.assertEqual(report["tier"], "VISEME_FACE")
        self.assertEqual(report["visemes"]["missing"], [])
        self.assertTrue(report["facial"]["missing"])

    def test_required_visemes_and_facial_controls_are_full_facial(self):
        path = self.path()
        morphs = validator.REQUIRED_VISEMES + validator.REQUIRED_FACIAL
        _write_glb(path, validator.MIXAMO_CORE_BONES, morphs)
        report = validator.validate_glb(path)
        self.assertEqual(report["tier"], "FULL_FACIAL")
        self.assertEqual(report["facial"]["missing"], [])
        self.assertFalse(report["talkinghead_compatible"])

    def test_talkinghead_strict_requires_full_body_arkit_and_visemes(self):
        path = self.path()
        morphs = validator.REQUIRED_VISEMES + validator.ARKIT_MORPHS
        _write_glb(path, validator.TALKINGHEAD_BODY_BONES, morphs)
        report = validator.validate_glb(path)
        self.assertTrue(report["talkinghead_compatible"])
        self.assertEqual(report["compatibility_percent"], 100)

    def test_mixamorig_and_exporter_namespaces_are_normalized(self):
        path = self.path()
        bones = tuple("mixamorig:" + name for name in validator.MIXAMO_CORE_BONES)
        morphs = tuple("Face|" + name for name in validator.REQUIRED_VISEMES)
        _write_glb(path, bones, morphs)
        report = validator.validate_glb(path)
        self.assertTrue(report["mixamo_compatible"])
        self.assertEqual(report["visemes"]["missing"], [])

    def test_report_is_deterministic(self):
        path = self.path()
        _write_glb(path, validator.LEGACY_BODY_BONES)
        first = validator.validate_glb(path, {"name": "Test", "blend": "test.blend"})
        second = validator.validate_glb(path, {"name": "Test", "blend": "test.blend"})
        self.assertEqual(first, second)
        self.assertIn("LEGACY_JAW", validator.format_human_report(first))

    def test_manifest_validation_uses_threejs_glb_and_summarizes_tiers(self):
        chars_dir = Path(self.temp.name, "chars")
        chars_dir.mkdir()
        _write_glb(chars_dir / "legacy.glb", validator.LEGACY_BODY_BONES)
        entries = [
            {"name": "Legacy", "blend": "legacy.blend"},
            {"name": "Missing", "blend": "missing.blend"},
        ]
        with mock.patch.object(char3d_lib, "THREE_CHAR_DIR", str(chars_dir)):
            report = char3d_lib.validation_report(entries, use_cache=False)
        self.assertEqual(report["summary"]["total"], 2)
        self.assertEqual(report["summary"]["supported"], 1)
        self.assertEqual(report["summary"]["tiers"]["LEGACY_JAW"], 1)
        self.assertEqual(report["characters"][1]["errors"][0]["code"], "file_not_found")

    def test_flask_validation_api_returns_validator_payload(self):
        payload = {"schema_version": 1, "summary": {"total": 0}, "characters": []}
        with mock.patch.object(char3d_lib, "validation_report", return_value=payload):
            response = app_module.app.test_client().get("/api/characters3d/validation")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), payload)

    def test_unregistered_glb_is_included_in_complete_library_scan(self):
        chars_dir = Path(self.temp.name, "chars")
        chars_dir.mkdir()
        _write_glb(chars_dir / "orphan.glb", validator.LEGACY_BODY_BONES)
        with (mock.patch.object(char3d_lib, "THREE_CHAR_DIR", str(chars_dir)),
              mock.patch.object(char3d_lib, "load", return_value=[])):
            report = char3d_lib.validation_report(use_cache=False)
        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["summary"]["unregistered"], 1)
        self.assertFalse(report["characters"][0]["character"]["registered"])
        self.assertIn("unregistered_glb", [w["code"] for w in report["characters"][0]["warnings"]])


if __name__ == "__main__":
    unittest.main()
