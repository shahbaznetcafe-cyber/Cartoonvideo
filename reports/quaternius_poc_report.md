# Quaternius Three.js Body-Animation Proof

## Verdict

**PROOF PASSED — safe to integrate into production.**

The proof establishes the requested boundary: Blender standardized the selected source once, and the completed 20-second video was then rendered by the isolated Three.js runtime without Blender running during capture. No production renderer files were changed.

## Selected asset

- Character: **Adventurer**
- Pack: **Quaternius Ultimate Modular Men Pack**
- Source: `D:\flayer\sbz-studio\work\quaternius\Individual Characters-20260715T071335Z-1-001\Individual Characters\glTF\Adventurer.gltf`
- Source license: **CC0 1.0 / public domain**, verified on the official Quaternius Ultimate Modular Men Pack page: <https://quaternius.com/packs/ultimatemodularcharacters.html>
- Selection rationale: one complete 62-bone humanoid skin, 24 authored source clips, five skinned character mesh parts, eleven materials, self-contained glTF data, and approximately 10,202 triangles.

The supplied partial archive did not contain its parent license file. That absence remains recorded in the inventory; the selected pack's license was verified against the official publisher page rather than inferred.

## One-time Blender standardization

- Blender executable: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`
- Blender version: **5.1.2**
- Reusable script: `D:\flayer\sbz-studio\blender\standardize_quaternius_master.py`
- Launcher: `D:\flayer\sbz-studio\tools\run_quaternius_standardize.ps1`
- Command:

  ```powershell
  powershell -ExecutionPolicy Bypass -File D:\flayer\sbz-studio\tools\run_quaternius_standardize.ps1 -Repository D:\flayer\sbz-studio
  ```

- Conversion time: **13.7603 seconds**
- Exported GLB: `D:\flayer\sbz-studio\assets\characters\quaternius_master\master_character.glb`
- Intermediate working copy: `D:\flayer\sbz-studio\work\character_poc\master_character.blend`
- Original extracted asset: unchanged

The conversion starts from a clean scene, imports the source glTF, removes only the unrelated `Icosphere` helper, preserves the original skin/weights/materials/actions, normalizes height to **1.71846 units**, centers the character, places its feet at ground level, and exports one production armature as GLB 2.0.

## Exported character validation

- GLB 2.0: valid
- SHA-256: `da7728ee425af38456ef0e97f28dfbafcdcd853b528638b07174c2b81235a958`
- Production armature: `QuaterniusMasterRig`
- Bones: **62**
- Skins: **1**
- Skinned source mesh nodes: **5**
- Materials: **11**
- Triangles: **10,202**
- Morph targets: **0**
- Runtime tier: **SKELETAL_BASIC**
- Required humanoid body mappings: **17/17 present**
- Body-animation compatibility: **verified true by Three.js playback**
- Body-animation compatibility score: **100%**
- Overall score including facial capability: **80%** (80% body / 20% facial weighting)

Full machine-readable results are in `D:\flayer\sbz-studio\assets\characters\quaternius_master\validation.json`.

### Skeleton summary

The hierarchy includes Root, Body, Hips, Abdomen, Torso, Chest, Neck, Head, left/right shoulders, upper/lower arms, wrists, full finger chains, upper/lower legs, feet, and toe/end controls. The validator maps all required hips, spine/chest, head/neck, arm/hand, leg, and foot capabilities.

### Exported animation clips

`Celebrate`, `Death`, `Gun_Shoot`, `HitRecieve`, `HitRecieve_2`, `Idle`, `Idle_Gun`, `Idle_Gun_Pointing`, `Idle_Gun_Shoot`, `Idle_Neutral`, `Idle_Sword`, `Interact`, `Kick_Left`, `Kick_Right`, `Listen`, `Point`, `Punch_Left`, `Punch_Right`, `Roll`, `Run`, `Run_Back`, `Run_Left`, `Run_Right`, `Run_Shoot`, `Sword_Slash`, `TalkIdle`, `Walk`, `Wave`.

There are **28 exported clips**. Four deterministic aliases preserve authored same-rig movement: `Point <- Idle_Gun_Pointing`, `Celebrate <- Interact`, `TalkIdle <- Idle`, and `Listen <- Idle_Neutral`. No six-bone procedural animation or cross-skeleton retargeting was used.

## Isolated Three.js runtime

- Location: `D:\flayer\sbz-studio\threejs_render\quaternius_poc`
- Loader: local `GLTFLoader`; no CDN dependency
- Animation: `THREE.AnimationMixer` with a clip-name dictionary
- Crossfades: **0.28 seconds**
- Skeleton ownership: mixer-controlled bones are not overwritten
- Locomotion: the character holder moves analytically only during the Walk section; the authored Walk clip drives the skeleton
- Lighting: hemisphere fill plus directional key light
- Shadows: `PCFSoftShadowMap`, character cast shadows, ground receives shadows
- Color: sRGB output with ACES filmic tone mapping
- Environment: lightweight Quaternius trees, rocks, bushes, and flowers with a grounded path and depth
- Camera: continuous interpolated tracking, medium framing, target shifts, and ending pull-back
- Blender used at runtime: **false**

Runtime sampling observed five timeline clips (`Idle`, `Walk`, `Wave`, `Point`, `Celebrate`) and a bone-transform checksum range of **27.991267–566.437180**, proving that the skeleton was changing rather than the character remaining static. The embedded `Run` clip also loads and validates, though the required exact 20-second timeline does not call for a Run segment.

## Capture and FFmpeg

- Capture: headless Chrome at **1920x1080**, **24 FPS**, exactly **480 frames**
- Frame transport: PNG screenshots are piped directly to FFmpeg stdin; no encoding-frame sequence is accumulated on disk
- FFmpeg executable: `C:\Program Files\ffmpeg\bin\ffmpeg.exe`
- Effective command:

  ```text
  ffmpeg -hide_banner -loglevel warning -y -fflags +genpts -f image2pipe -vcodec png -framerate 24 -i - -frames:v 480 -vf scale=1920:1080:flags=lanczos,setsar=1 -an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 24 -fps_mode cfr -movflags +faststart D:\flayer\sbz-studio\outputs\quaternius_poc.mp4
  ```

- Three.js capture/render time: **105.3727 seconds**
- Output: `D:\flayer\sbz-studio\outputs\quaternius_poc.mp4`

## Automated and visual quality checks

| Check | Result | Evidence |
|---|---|---|
| MP4 exists and is playable | PASS | FFprobe parsed H.264 stream and container without error |
| Exact duration | PASS | 20.000000 seconds |
| Resolution | PASS | 1920x1080 |
| Frame rate / count | PASS | 24/1 FPS, 480 frames |
| Pixel format | PASS | yuv420p |
| More than one real clip changes skeleton | PASS | Five timeline clips observed; bone checksum span 538.445914 |
| Character is not static | PASS | Walk locomotion plus Wave, Point, and Celebrate poses visible in encoded milestone frames |
| Mesh deformation | PASS | No collapse, torso pull, detached backpack, broken limbs, or extreme weight artifacts in eight encoded milestone checks |
| Materials / textures | PASS | All eleven flat-color materials render; this character intentionally references zero external image textures |
| All-black frames | PASS | FFmpeg `blackdetect` found no black segments |
| Black top/bottom regions | PASS | One-second crop scan at black threshold reports `crop=1920:1080:0:0` |
| Feet near ground | PASS | Sampled animated bounds minimum Y stayed between -0.013112 and +0.017108 units |
| Camera continuity | PASS | Camera position is interpolated every frame; encoded milestones show continuous framing without cuts or black transitions |
| Contact shadow | PASS | Visible beneath character and props in encoded milestones |
| Blender absent from normal capture | PASS | Capture process used Chrome, Three.js, and FFmpeg only; runtime metric is `blenderUsedAtRuntime=false` |
| JavaScript syntax | PASS | `poc.js` and `capture.mjs` pass `node --check` |
| Existing Three.js regression tests | PASS | 18 passed, 0 failed |

## Remaining limitations

- The selected asset has no viseme morphs, jaw control, blink morphs, independent eye controls, or facial emotion morphs.
- `TalkIdle` and `Listen` are explicit body-motion fallbacks; they do not provide mouth animation.
- `Point` and `Celebrate` are semantically normalized aliases of the nearest authored same-rig clips, not custom motion-capture actions.
- This proof validates full-body animation, blocking, environment, camera, grounding, shadows, and direct Three.js playback only. Facial/lip-sync production work remains a separate compatibility tier.

## Recommendation

**PROCEED** with a small, reviewable production integration for this 62-bone Quaternius body-animation profile. Keep the current legacy and facial tiers intact, route this master character through `SKELETAL_BASIC`, and do not begin bulk conversion until one production-scene integration reproduces the same grounding, mixer ownership, clip crossfades, and deterministic capture checks.
