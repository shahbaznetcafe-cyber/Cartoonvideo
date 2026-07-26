"""Safe, data-driven scene dressing selection for the Three.js renderer.

Only locally verified, non-character source assets are exposed here.  The
source files stay in the user's Quaternius inventory; the renderer serves them
read-only during a render, so textures and materials remain intact without
copying or bulk-converting the catalogue.
"""
from __future__ import annotations

from pathlib import Path

import config


ROOT = Path(config.BASE_DIR)
NATURE = ROOT / "work/quaternius/Stylized Nature MegaKit[Standard]/glTF"
SPACE = ROOT / "work/quaternius/Ultimate Space Kit - March 2023-20260715T070157Z-1-001/Ultimate Space Kit - March 2023/Environment/GLTF"
ZOMBIE = ROOT / "work/quaternius/Zombie Apocalypse Kit - March 2024-20260715T065801Z-1-001/Zombie Apocalypse Kit - March 2024/Environment/glTF"
PIRATE = ROOT / "work/quaternius/Pirate Kit - Nov 2023-20260715T065953Z-1-001/Pirate Kit - Nov 2023/glTF"


# Reusable, layered worlds made from the local 3D packs.  They are recipes,
# not baked scenes: a render loads just the small set of assets it needs and
# can still place story props and characters naturally within the world.
COMPOSED_BACKGROUNDS = (
    {"id": "forest_story_path", "name": "Forest Story Path", "preset": "forest",
     "variant": "forest_path", "pack": "Stylized Nature MegaKit",
     "description": "Tree-lined path with flowers, rocks and foreground foliage."},
    {"id": "forest_blooming_clearing", "name": "Blooming Forest Clearing", "preset": "forest",
     "variant": "blooming_farm", "pack": "Stylized Nature MegaKit",
     "description": "Warm flower clearing for gentle discoveries and dialogue."},
    {"id": "pirate_harbor", "name": "Pirate Harbor", "preset": "pirate",
     "variant": "pirate_harbor", "pack": "Quaternius Pirate Kit",
     "description": "Dock, ship, palms, cliff and barrels with a deep sea-side composition."},
    {"id": "pirate_treasure_cove", "name": "Treasure Cove", "preset": "pirate",
     "variant": "treasure_cove", "pack": "Quaternius Pirate Kit",
     "description": "Hidden cove with treasure chest, palms, rocks and a broken dock."},
    {"id": "space_outpost", "name": "Planetary Outpost", "preset": "space",
     "variant": "space_outpost", "pack": "Ultimate Space Kit",
     "description": "Science-fiction base, dome, solar panels and distant planet."},
    {"id": "apocalypse_street", "name": "Ruined City Street", "preset": "apocalypse",
     "variant": "apocalypse_street", "pack": "Zombie Apocalypse Kit",
     "description": "Cracked road, containers, streetlights and barriers for action beats."},
    # --- added worlds: presets that previously rendered with no dressing ---
    {"id": "village_square", "name": "Village Square", "preset": "village",
     "variant": "village_square", "pack": "Quaternius Pirate Kit + Nature MegaKit",
     "description": "Wooden houses, a shared path and trees — home for moral and family stories."},
    {"id": "town_street", "name": "Town Street", "preset": "town",
     "variant": "town_street", "pack": "Zombie Apocalypse Kit (clean props)",
     "description": "Tidy road, town sign, traffic light and a house for everyday city scenes."},
    {"id": "night_forest", "name": "Night Forest", "preset": "night",
     "variant": "night_forest", "pack": "Stylized Nature MegaKit",
     "description": "Pines, bare trees and mushrooms for night-time and suspense beats."},
    {"id": "magic_grove", "name": "Magic Mushroom Grove", "preset": "forest",
     "variant": "magic_grove", "pack": "Stylized Nature MegaKit",
     "description": "Oversized mushrooms and flower clusters for wonder and fantasy."},
    {"id": "open_meadow", "name": "Open Meadow", "preset": "meadow",
     "variant": "open_meadow", "pack": "Stylized Nature MegaKit",
     "description": "Grass, clover and flowers with a wide horizon for calm conversations."},
    {"id": "island_beach", "name": "Island Beach", "preset": "beach",
     "variant": "island_beach", "pack": "Quaternius Pirate Kit",
     "description": "Palms, sea rocks and buckets — a friendly beach without pirate danger."},
    {"id": "rocky_desert", "name": "Rocky Desert", "preset": "desert",
     "variant": "rocky_desert", "pack": "Stylized Nature MegaKit",
     "description": "Boulders, bare trees and pebbles for dry, hot journey scenes."},
    {"id": "chroma_green", "name": "Green Screen", "preset": "chroma_green",
     "variant": "chroma_green", "pack": "Procedural (no assets)",
     "description": "Flat, unlit green backdrop for background removal in an "
                    "external editor. Type \"green screen\" in a scene's "
                    "background to use it."},
    {"id": "chroma_blue", "name": "Blue Screen", "preset": "chroma_blue",
     "variant": "chroma_blue", "pack": "Procedural (no assets)",
     "description": "Flat, unlit blue backdrop for background removal in an "
                    "external editor. Type \"blue screen\" in a scene's "
                    "background to use it."},
)


def composed_backgrounds():
    """Return UI-friendly production background recipes without duplicating assets."""
    return [dict(item, status="integrated", production_selectable=True) for item in COMPOSED_BACKGROUNDS]


def _asset(asset_id, root, filename, *, target_height, position, rotation_y=0.0):
    """Create a renderer-safe asset declaration only when its source exists."""
    source = root / filename
    if not source.is_file():
        return None
    return {
        "id": asset_id,
        "source": str(source),
        "targetHeight": float(target_height),
        "position": [float(position[0]), float(position[1]), float(position[2])],
        "rotationY": float(rotation_y),
        "readOnlySource": True,
    }


def _available(candidates):
    return [item for item in candidates if item is not None]


def dressings_for(environment, scene_index=0):
    """Return a deterministic, layered set of real local 3D assets.

    Each recipe has foreground, midground and background scale references so
    the generated video reads as a location, rather than a flat stage.
    """
    environment = environment or {}
    preset = str(environment.get("preset") or "sunny").lower()
    variant = str(environment.get("variant") or "").lower()
    phase = int(scene_index or 0) % 3

    # --- village: wooden houses around a shared path (moral/family stories) ---
    if preset == "village" or "village" in variant:
        return _available([
            _asset("village_house_left", PIRATE, "Environment_House1.gltf", target_height=3.1, position=(-3.7, 0, -3.0), rotation_y=.42),
            _asset("village_house_right", PIRATE, "Environment_House2.gltf", target_height=2.8, position=(3.6, 0, -3.2), rotation_y=-.38),
            _asset("village_house_back", PIRATE, "Environment_House3.gltf", target_height=2.6, position=(.6, 0, -5.1), rotation_y=.08),
            _asset("village_tree", NATURE, "CommonTree_2.gltf", target_height=4.0, position=(-2.4, 0, -1.6), rotation_y=.2),
            _asset("village_path", NATURE, "RockPath_Square_Wide.gltf", target_height=.13, position=(.3, 0, 1.0), rotation_y=0),
            _asset("village_bush", NATURE, "Bush_Common.gltf", target_height=.66, position=(2.5, 0, -.4), rotation_y=-.3),
        ])

    # --- town: tidy street furniture, no apocalypse damage ---
    if preset in {"town", "market"} or "town" in variant:
        return _available([
            _asset("town_street", ZOMBIE, "Street_Straight.gltf", target_height=.10, position=(0, 0, -1.5), rotation_y=0),
            _asset("town_sign", ZOMBIE, "TownSign.gltf", target_height=2.3, position=(-3.0, 0, -1.9), rotation_y=.16),
            _asset("town_light", ZOMBIE, "TrafficLight_1.gltf", target_height=2.9, position=(2.9, 0, -2.1), rotation_y=-.14),
            _asset("town_hydrant", ZOMBIE, "FireHydrant.gltf", target_height=.72, position=(-2.3, 0, .5), rotation_y=.1),
            _asset("town_house", PIRATE, "Environment_House2.gltf", target_height=3.0, position=(3.7, 0, -3.6), rotation_y=-.3),
            _asset("town_tree", NATURE, "CommonTree_5.gltf", target_height=3.6, position=(-3.8, 0, -3.2), rotation_y=.24),
        ])

    # --- night forest: pines and bare trees for suspense ---
    if preset == "night" or "night" in variant:
        return _available([
            _asset("night_pine_back", NATURE, "Pine_1.gltf", target_height=5.0, position=(-3.4, 0, -2.6), rotation_y=.18),
            _asset("night_pine_side", NATURE, "Pine_3.gltf", target_height=4.2, position=(3.5, 0, -2.2), rotation_y=-.2),
            _asset("night_deadtree", NATURE, "DeadTree_1.gltf", target_height=3.6, position=(2.1, 0, -.9), rotation_y=.3),
            _asset("night_mushroom", NATURE, "Mushroom_Common.gltf", target_height=.42, position=(-1.9, 0, .5), rotation_y=.1),
            _asset("night_rock", NATURE, "Rock_Medium_1.gltf", target_height=.55, position=(1.3, 0, .8), rotation_y=-.15),
            _asset("night_fern", NATURE, "Fern_1.gltf", target_height=.58, position=(-3.0, 0, 1.3), rotation_y=.2),
        ])

    # --- magic grove: oversized mushrooms for wonder beats ---
    if "magic" in variant or "glowing" in variant:
        return _available([
            _asset("magic_mushroom_big", NATURE, "Mushroom_Laetiporus.gltf", target_height=1.5, position=(-2.7, 0, -1.8), rotation_y=.2),
            _asset("magic_mushroom_mid", NATURE, "Mushroom_Common.gltf", target_height=.95, position=(2.6, 0, -1.5), rotation_y=-.25),
            _asset("magic_tree", NATURE, "CommonTree_2.gltf", target_height=4.3, position=(3.5, 0, -3.0), rotation_y=-.2),
            _asset("magic_flowers", NATURE, "Flower_4_Group.gltf", target_height=.5, position=(-1.6, 0, .6), rotation_y=.1),
            _asset("magic_clover", NATURE, "Clover_1.gltf", target_height=.3, position=(1.5, 0, .9), rotation_y=.15),
            _asset("magic_fern", NATURE, "Fern_1.gltf", target_height=.62, position=(-3.2, 0, 1.2), rotation_y=.22),
        ])

    # --- meadow: open, low horizon for calm dialogue ---
    if preset == "meadow" or "meadow" in variant:
        return _available([
            _asset("meadow_bush_left", NATURE, "Bush_Common_Flowers.gltf", target_height=.8, position=(-3.3, 0, -1.7), rotation_y=.2),
            _asset("meadow_bush_right", NATURE, "Bush_Common.gltf", target_height=.72, position=(3.2, 0, -1.5), rotation_y=-.22),
            _asset("meadow_grass_tall", NATURE, "Grass_Common_Tall.gltf", target_height=.5, position=(-1.7, 0, .7), rotation_y=.1),
            _asset("meadow_clover", NATURE, "Clover_1.gltf", target_height=.28, position=(1.4, 0, .8), rotation_y=-.1),
            _asset("meadow_flowers", NATURE, "Flower_4_Group.gltf", target_height=.46, position=(2.2, 0, -.3), rotation_y=.12),
            _asset("meadow_tree_far", NATURE, "CommonTree_5.gltf", target_height=3.8, position=(-4.0, 0, -4.2), rotation_y=.3),
        ])

    # --- rocky desert: dry journey scenes ---
    if preset == "desert" or "desert" in variant:
        return _available([
            _asset("desert_rock_big", NATURE, "Rock_Medium_3.gltf", target_height=1.6, position=(-3.2, 0, -2.4), rotation_y=.24),
            _asset("desert_rock_mid", NATURE, "Rock_Medium_1.gltf", target_height=.95, position=(3.1, 0, -1.9), rotation_y=-.2),
            _asset("desert_deadtree", NATURE, "DeadTree_3.gltf", target_height=3.2, position=(2.4, 0, -3.4), rotation_y=.16),
            _asset("desert_pebble_a", NATURE, "Pebble_Round_1.gltf", target_height=.22, position=(-1.5, 0, .8), rotation_y=.1),
            _asset("desert_pebble_b", NATURE, "Pebble_Round_1.gltf", target_height=.16, position=(1.2, 0, 1.0), rotation_y=-.3),
            _asset("desert_plant", NATURE, "Plant_1_Big.gltf", target_height=.7, position=(-2.6, 0, .4), rotation_y=.2),
        ])

    # --- friendly beach (island without the pirate threat) ---
    if preset == "beach" or "beach" in variant or "island" in variant:
        return _available([
            _asset("beach_palm_left", PIRATE, "Environment_PalmTree_1.gltf", target_height=4.3, position=(-3.4, 0, -2.2), rotation_y=.22),
            _asset("beach_palm_right", PIRATE, "Environment_PalmTree_3.gltf", target_height=3.8, position=(3.3, 0, -2.6), rotation_y=-.24),
            _asset("beach_rock", PIRATE, "Environment_Rock_2.gltf", target_height=1.1, position=(2.4, 0, -.8), rotation_y=.15),
            _asset("beach_rock_small", PIRATE, "Environment_Rock_4.gltf", target_height=.6, position=(-2.2, 0, .6), rotation_y=-.18),
            _asset("beach_bucket", PIRATE, "Prop_Bucket.gltf", target_height=.42, position=(1.1, 0, .9), rotation_y=.1),
            _asset("beach_bottle", PIRATE, "Prop_Bottle_1.gltf", target_height=.3, position=(-1.2, 0, 1.0), rotation_y=.2),
        ])

    if preset in {"forest", "sunny", "storm", "mud"} or "farm" in variant:
        tree = ("CommonTree_1.gltf", "CommonTree_3.gltf", "Pine_2.gltf")[phase]
        return _available([
            _asset("nature_back_tree", NATURE, tree, target_height=4.4, position=(-3.55, 0, -2.45), rotation_y=.22),
            _asset("nature_side_tree", NATURE, "CommonTree_4.gltf", target_height=3.25, position=(3.4, 0, -1.85), rotation_y=-.22),
            _asset("nature_bush", NATURE, "Bush_Common_Flowers.gltf", target_height=.70, position=(2.55, 0, -.45), rotation_y=-.35),
            _asset("nature_flowers", NATURE, "Flower_3_Group.gltf", target_height=.46, position=(-1.85, 0, .42), rotation_y=.1),
            _asset("nature_rockpath", NATURE, "RockPath_Round_Wide.gltf", target_height=.13, position=(.35, 0, 1.05), rotation_y=.04),
            _asset("nature_foreground_fern", NATURE, "Fern_1.gltf", target_height=.58, position=(-3.05, 0, 1.35), rotation_y=.18),
        ])

    if preset in {"space", "sci_fi"} or any(word in variant for word in ("space", "planet", "rocket")):
        return _available([
            _asset("space_base", SPACE, "Base_Large.gltf", target_height=.58, position=(0, 0, -2.05), rotation_y=0),
            _asset("space_building", SPACE, "Building_L.gltf", target_height=2.75, position=(-2.8, 0, -2.15), rotation_y=.18),
            _asset("space_dome", SPACE, "GeodesicDome.gltf", target_height=1.7, position=(2.5, 0, -1.75), rotation_y=-.26),
            _asset("space_planet", SPACE, "Planet_3.gltf", target_height=2.3, position=(3.7, 2.65, -5.5), rotation_y=.08),
            _asset("space_solar", SPACE, "SolarPanel_Ground.gltf", target_height=.82, position=(-1.5, 0, .45), rotation_y=.14),
            _asset("space_rock", SPACE, "Rock_Large_2.gltf", target_height=.56, position=(3.05, 0, .72), rotation_y=-.18),
        ])

    if preset in {"pirate", "island", "beach"} or any(word in variant for word in ("pirate", "island", "dock", "treasure", "cove")):
        treasure = "Prop_Chest_Gold.gltf" if "treasure" in variant or phase == 1 else "Prop_Chest_Closed.gltf"
        dock = "Environment_Dock_Broken.gltf" if "cove" in variant else "Environment_Dock.gltf"
        return _available([
            _asset("pirate_ship", PIRATE, "Ship_Large.gltf", target_height=3.9, position=(-3.8, 0, -3.7), rotation_y=.18),
            _asset("pirate_dock", PIRATE, dock, target_height=1.3, position=(-1.9, 0, -1.55), rotation_y=.08),
            _asset("pirate_cliff", PIRATE, "Environment_Cliff2.gltf", target_height=3.35, position=(3.55, 0, -2.85), rotation_y=-.2),
            _asset("pirate_palm", PIRATE, "Environment_PalmTree_2.gltf", target_height=4.15, position=(-3.25, 0, .35), rotation_y=.24),
            _asset("pirate_chest", PIRATE, treasure, target_height=.62, position=(1.35, 0, .55), rotation_y=.12),
            _asset("pirate_barrel", PIRATE, "Prop_Barrel.gltf", target_height=.66, position=(2.12, 0, .44), rotation_y=.16),
        ])

    if preset in {"apocalypse", "city", "urban"} or any(word in variant for word in ("apocalypse", "zombie", "city", "street")):
        return _available([
            _asset("city_street", ZOMBIE, "Street_Straight_Crack1.gltf", target_height=.10, position=(0, 0, -1.55), rotation_y=0),
            _asset("city_container", ZOMBIE, "Container_Green.gltf", target_height=1.32, position=(-2.65, 0, -1.85), rotation_y=.12),
            _asset("city_light", ZOMBIE, "StreetLights.gltf", target_height=3.05, position=(2.85, 0, -2.2), rotation_y=-.12),
            _asset("city_barrier", ZOMBIE, "TrafficBarrier_1.gltf", target_height=.64, position=(1.25, 0, .56), rotation_y=.1),
            _asset("city_tower", ZOMBIE, "WaterTower.gltf", target_height=3.8, position=(3.85, 0, -4.1), rotation_y=0),
            _asset("city_barrel", ZOMBIE, "Barrel.gltf", target_height=.62, position=(-2.25, 0, .55), rotation_y=.18),
        ])
    return []


def renderer_props(environment, scene_index=0):
    """Convert static asset dressings into existing renderer prop records."""
    props = []
    for asset in dressings_for(environment, scene_index):
        props.append({
            "id": f"dressing_{asset['id']}", "type": "dressing",
            "asset": asset,
            "position": asset["position"],
            "stateStart": {"x": asset["position"][0], "y": asset["position"][1],
                           "z": asset["position"][2], "rotationY": asset["rotationY"],
                           "growth": 1.0, "open": 0.0, "glow": 0.0},
            "stateEnd": {"x": asset["position"][0], "y": asset["position"][1],
                         "z": asset["position"][2], "rotationY": asset["rotationY"],
                         "growth": 1.0, "open": 0.0, "glow": 0.0},
            "consequence": "static_environment_dressing",
            "assetRole": "environment_dressing",
        })
    return props
