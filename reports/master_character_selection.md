# Master Character Selection

## Decision

- **Selected character:** Adventurer
- **Pack:** Quaternius Ultimate Modular Men Pack
- **Selected source:** `D:\flayer\sbz-studio\work\quaternius\Individual Characters-20260715T071335Z-1-001\Individual Characters\glTF\Adventurer.gltf`
- **Selected skeleton:** `CharacterArmature`, 62 bones
- **Selected animation source:** the same `Adventurer.gltf` (24 embedded actions)
- **License:** CC0 1.0 / public domain. The partial archive does not include its parent license file; the official Quaternius [Ultimate Modular Men Pack page](https://quaternius.com/packs/ultimatemodularcharacters.html) identifies the pack as CC0 and free for personal and commercial use.

## Why Adventurer was selected

Adventurer is the strongest proof candidate because the preferred glTF source imports cleanly with one complete humanoid armature, existing skin weights, five character mesh parts, eleven materials, finger bones, and 24 embedded full-body animation clips. The measured geometry is game-ready at approximately 10,202 triangles. Its skeleton includes Hips, multi-segment torso, Chest, Neck, Head, shoulders, upper/lower arms, wrists/hands, upper/lower legs, feet, toe/end controls, and full finger chains.

The source already contains the proof's native `Idle`, `Walk`, `Run`, and `Wave` clips. `Idle_Gun_Pointing` is the nearest authored full-body source for the deterministic `Point` alias. `Interact` is used as the nearest authored emote source for the deterministic `Celebrate` alias. These are copied animation actions on the same skeleton; no retargeting and no procedural six-bone motion are used.

## Known facial limitations

The source has no facial morph targets, jaw control, visemes, blink controls, or independently animated eyes. This body-animation proof intentionally contains no dialogue or lip-sync. Its expected runtime tier is `SKELETAL_BASIC`, not `VISEME_FACE` or `FULL_FACIAL`.

## Rejected alternatives

- **Other Ultimate Modular Men characters (Beach, Casual, Farmer, King, Punk, Spacesuit, Suit, Swat, Worker):** technically compatible and contain the same 24-clip/62-bone rig, but Adventurer provides the clearest general-purpose silhouette and includes a useful backpack for visible body motion.
- **Zombie Apocalypse humans:** animated and textured, but the automated required-body mapping does not expose explicit Chest and hand equivalents as clearly as the selected rig; also substantially higher triangle counts in full variants.
- **Ultimate Space astronauts:** usable animation sets, but their specialized silhouettes and smaller 18-clip sets make them weaker general cartoon proof characters.
- **Pirate characters:** animated and useful, but the supplied partial Pirate ZIP's license is not embedded and the rigs expose fewer bones/clips than Adventurer.
- **Ultimate Monsters humanoids:** many are animated, but stylized/non-human anatomy makes humanoid compatibility less reliable for a production body-animation standard.
- **Blob, flying monster, animal and mech rigs:** not complete human skeletons.
- **All FBX/BLEND-only candidates:** lower priority because an already animated, self-contained glTF with validated skin and clips is available.
- **OBJ-only assets:** rejected because OBJ cannot contain a usable skeletal animation rig.

## Selection status

**SELECTED FOR ISOLATED PROOF.** Production renderer integration remains out of scope until the 20-second Three.js proof passes.
