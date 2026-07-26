import unittest
from pathlib import Path
from unittest import mock

import app as app_module
import asset_catalog
import blender3d
import char3d_lib
import character_catalog
import character_performance


class CharacterCatalogTests(unittest.TestCase):
    def test_runtime_metadata_exposes_body_face_and_lip_sync_tiers(self):
        entries = [
            {"name": "Adventurer", "blend": "quaternius_adventurer.blend",
             "capability_id": "quaternius_adventurer",
             "animation_tier": "SKELETAL_INTERACTIVE"},
            {"name": "SBZ Mascot", "blend": "mascot.blend"},
        ]
        profiles = [
            character_performance.policy_for_tier(
                "SKELETAL_INTERACTIVE", character_id="quaternius_adventurer",
                name="Adventurer", library="quaternius"),
            character_performance.policy_for_tier("LEGACY_JAW", name="SBZ Mascot"),
        ]
        with mock.patch.object(char3d_lib, "load", return_value=entries), \
                mock.patch.object(character_performance, "profile_for_entry", side_effect=profiles):
            adventurer = char3d_lib.runtime_metadata("D:/any/quaternius_adventurer.blend")
            mascot = char3d_lib.runtime_metadata("mascot.blend")
        self.assertEqual(adventurer["animationTier"], "SKELETAL_INTERACTIVE")
        self.assertEqual(adventurer["speechMode"], "body_only")
        self.assertEqual(adventurer["lipSyncMode"], "none")
        self.assertFalse(adventurer["facialReady"])
        self.assertEqual(adventurer["library"], "quaternius")
        self.assertEqual(mascot["animationTier"], "LEGACY_JAW")
        self.assertEqual(mascot["lipSyncMode"], "jaw_openness")
        self.assertEqual(mascot["library"], "sbz")

    def test_body_only_quaternius_closeup_is_reframed(self):
        with mock.patch.object(blender3d, "_character_runtime_metadata", return_value={
            "capabilityId": "quaternius_farmer",
            "animationTier": "SKELETAL_BASIC",
            "facialReady": False,
            "library": "quaternius",
        }):
            self.assertEqual(blender3d._capability_safe_shot("closeup", "farmer.blend"), "medium")
            self.assertEqual(blender3d._capability_safe_shot("wide", "farmer.blend"), "wide")

    def test_only_validated_facial_character_keeps_closeup(self):
        with mock.patch.object(blender3d, "_character_runtime_metadata", return_value={
            "capabilityId": "future_face", "animationTier": "FACIAL_READY",
            "facialReady": True,
            "library": "quaternius",
        }):
            self.assertEqual(blender3d._capability_safe_shot("closeup", "face.blend"), "closeup")
        with mock.patch.object(blender3d, "_character_runtime_metadata", return_value={
            "capabilityId": "", "animationTier": "LEGACY_JAW",
            "facialReady": False, "library": "sbz",
        }):
            self.assertEqual(blender3d._capability_safe_shot("closeup", "mascot.blend"), "medium")

    def test_local_manifest_has_separate_complete_runtime_libraries(self):
        entries = char3d_lib.load()
        quaternius = [entry for entry in entries
                      if str(entry.get("capability_id") or "").startswith("quaternius_")]
        originals = [entry for entry in entries if entry not in quaternius]
        self.assertEqual(len(originals), 44)
        # 125 core + 9 Pirate Kit (license user-verified as CC0, re-registered).
        self.assertEqual(len(quaternius), 134)
        self.assertEqual(sum(entry.get("animation_tier") == "SKELETAL_INTERACTIVE"
                             for entry in quaternius), 1)
        # The five former STATIC humans carry clips grafted by bone name from
        # quaternius_casual_male (tools/graft_donor_clips.py).
        self.assertEqual(sum(entry.get("animation_tier") == "SKELETAL_BASIC"
                             for entry in quaternius), 133)
        self.assertEqual(sum(entry.get("animation_tier") == "STATIC"
                             for entry in quaternius), 0)
        for entry in quaternius:
            self.assertTrue(char3d_lib.blend_path(entry), entry["name"])
            self.assertTrue(Path(char3d_lib.glb_path(entry)).is_file(), entry["name"])

    def test_catalog_endpoints_return_ui_ready_payloads(self):
        client = app_module.app.test_client()
        characters = client.get("/api/character-catalog")
        assets = client.get("/api/asset-catalog")
        self.assertEqual(characters.status_code, 200)
        self.assertEqual(assets.status_code, 200)
        character_payload = characters.get_json()
        asset_payload = assets.get_json()
        self.assertEqual(character_payload["summary"]["sbz"], 44)
        self.assertEqual(character_payload["summary"]["quaternius_ready"], 134)
        self.assertEqual(character_payload["summary"]["license_blocked"], 0)
        self.assertEqual({item["id"] for item in character_payload["libraries"]},
                         {"sbz", "quaternius"})
        self.assertEqual(set(asset_payload["summary"]),
                         {"backgrounds", "props", "vehicles", "weapons"})
        self.assertGreaterEqual(asset_payload["integrated"], 3)


if __name__ == "__main__":
    unittest.main()
