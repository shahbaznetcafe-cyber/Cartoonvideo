import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { loadCapabilityRegistry } from '../production/character_capability_registry.js';

window.__ready = false;
window.__error = null;
window.addEventListener('error', event => {
  window.__error = String(event.error?.stack || event.message || event.error || 'Unknown scene error');
});
window.addEventListener('unhandledrejection', event => {
  window.__error = String(event.reason?.stack || event.reason || 'Unhandled scene rejection');
});

const FPS = 24;
const TOTAL_FRAMES = 144;
const CHARACTER_CONFIG = [
  { id: 'quaternius_casual_2', url: '/assets/characters/quaternius_representative/casual_2/casual_2.glb',
    clip: 'Walk', position: [-1.58, 0, 0.18], yaw: 0.12, phase: 0.0, color: 0x4f8cff },
  { id: 'quaternius_farmer', url: '/assets/characters/quaternius_representative/farmer/farmer.glb',
    clip: 'Wave', position: [0, 0, -0.08], yaw: 0, phase: 0.37, color: 0x22c55e },
  { id: 'quaternius_king', url: '/assets/characters/quaternius_representative/king/king.glb',
    clip: 'Listen', position: [1.58, 0, 0.12], yaw: -0.12, phase: 0.71, color: 0xf59e0b },
];

const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('stage'), antialias: true,
  preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(1920, 1080, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.03;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9bc5dc);
scene.fog = new THREE.Fog(0x9bc5dc, 8, 20);
const camera = new THREE.PerspectiveCamera(35, 16 / 9, 0.05, 40);

scene.add(new THREE.HemisphereLight(0xdff2ff, 0x52603b, 1.65));
const key = new THREE.DirectionalLight(0xffe3bd, 2.25);
key.position.set(-4.5, 7, 5.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -6;
key.shadow.camera.right = 6;
key.shadow.camera.top = 5;
key.shadow.camera.bottom = -5;
scene.add(key, key.target);
const fill = new THREE.DirectionalLight(0x9ac5ff, 0.7);
fill.position.set(4, 3, 2);
scene.add(fill);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(18, 12),
  new THREE.MeshStandardMaterial({ color: 0x668d55, roughness: 0.96 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.012;
ground.receiveShadow = true;
scene.add(ground);

for (let index = 0; index < 4; index += 1) {
  const hill = new THREE.Mesh(new THREE.SphereGeometry(3.4 + index * 0.35, 24, 12),
    new THREE.MeshStandardMaterial({ color: index % 2 ? 0x557e50 : 0x4a7448, roughness: 1 }));
  hill.scale.y = 0.28;
  hill.position.set(-5.4 + index * 3.8, -0.45, -6.7 - (index % 2) * 0.7);
  scene.add(hill);
}

const path = new THREE.Mesh(new THREE.PlaneGeometry(7.2, 2.25),
  new THREE.MeshStandardMaterial({ color: 0xa28a69, roughness: 1 }));
path.rotation.x = -Math.PI / 2;
path.position.set(0, -0.004, 0.05);
path.receiveShadow = true;
scene.add(path);

const environmentActors = [];
for (let index = 0; index < 18; index += 1) {
  const tree = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.14, 1.15, 7),
    new THREE.MeshStandardMaterial({ color: 0x67472f, roughness: 1 }));
  const crown = new THREE.Mesh(new THREE.DodecahedronGeometry(0.52, 1),
    new THREE.MeshStandardMaterial({ color: index % 2 ? 0x416e3b : 0x4e7d42, roughness: 1 }));
  trunk.position.y = 0.575;
  crown.position.y = 1.42;
  tree.add(trunk, crown);
  const side = index % 2 ? 1 : -1;
  const x = -5.8 + (index % 9) * 1.45;
  const foreground = side > 0 && Math.abs(x) > 3.35;
  tree.position.set(x, 0, foreground ? 2.7 + (index % 3) * 0.25 : -2.55 - (index % 3) * 0.32);
  tree.scale.setScalar(0.85 + (index % 4) * 0.08);
  scene.add(tree);
  environmentActors.push({ tree, crown, phase: index * 0.61, baseRotation: tree.rotation.z });
}

for (let index = 0; index < 16; index += 1) {
  const bush = new THREE.Mesh(new THREE.DodecahedronGeometry(0.18 + (index % 3) * 0.035, 1),
    new THREE.MeshStandardMaterial({ color: index % 2 ? 0x47783f : 0x6b8f43, roughness: 1 }));
  const side = index % 2 ? 1 : -1;
  bush.position.set(-4.8 + (index % 8) * 1.38, 0.15, side * 1.52);
  scene.add(bush);
  environmentActors.push({ tree: bush, crown: bush, phase: 2 + index * 0.39, baseRotation: 0 });
}

const registry = await loadCapabilityRegistry('/assets/characters/capability_registry.json');
const loader = new GLTFLoader();
const performers = [];

function materialSignature(root) {
  const rows = [];
  root.traverse(node => {
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials.filter(Boolean)) {
      rows.push(`${material.name}:${material.color?.getHexString?.() || 'none'}`);
    }
  });
  return [...new Set(rows)].sort();
}

function skeletonIds(root) {
  const ids = [];
  root.traverse(node => {
    if (node.isSkinnedMesh && node.skeleton) ids.push(node.skeleton.uuid);
  });
  return [...new Set(ids)].sort();
}

function boneIds(root) {
  const ids = [];
  root.traverse(node => { if (node.isBone) ids.push(node.uuid); });
  return ids;
}

for (const config of CHARACTER_CONFIG) {
  const capability = registry.get(config.id);
  if (capability.tier !== 'SKELETAL_BASIC') throw new Error(`${config.id} must remain SKELETAL_BASIC`);
  if (capability.facial?.ready) throw new Error(`${config.id} must not claim facial readiness`);
  const gltf = await loader.loadAsync(`${config.url}?phase4=${encodeURIComponent(config.id)}`);
  const model = gltf.scene;
  const holder = new THREE.Group();
  holder.name = `${config.id}_holder`;
  holder.add(model);
  model.traverse(node => {
    if (node.isMesh) { node.castShadow = true; node.receiveShadow = true; }
  });
  const localBounds = new THREE.Box3().setFromObject(model);
  // These GLBs are already standardized. SkinnedMesh bounds under-report the
  // posed visual height, so never derive a second runtime scale from them.
  const normalizationScale = 1;
  model.position.y -= localBounds.min.y;
  model.updateMatrixWorld(true);
  holder.position.fromArray(config.position);
  holder.rotation.y = config.yaw;
  scene.add(holder);
  const clip = THREE.AnimationClip.findByName(gltf.animations, config.clip);
  if (!clip) throw new Error(`${config.id} is missing real clip ${config.clip}`);
  const mixer = new THREE.AnimationMixer(model);
  const action = mixer.clipAction(clip);
  action.setLoop(THREE.LoopRepeat, Infinity).play();
  performers.push({ config, capability, gltf, model, holder, mixer, action, clip,
    rootUuid: model.uuid, skeletonUuids: skeletonIds(model), boneUuids: boneIds(model),
    materials: materialSignature(model), normalizationScale });
}

const allBounds = new THREE.Box3();
for (const performer of performers) allBounds.union(new THREE.Box3().setFromObject(performer.holder));
const center = allBounds.getCenter(new THREE.Vector3());
const size = allBounds.getSize(new THREE.Vector3());
// Skinned low-poly bounds under-report posed upper-body reach. Reserve extra
// vertical performance space so heads and raised arms never leave frame.
const performanceHeight = Math.max(size.y * 2.9, 1.45);
const fitHeightDistance = performanceHeight / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)));
const fitWidthDistance = size.x / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)) * camera.aspect);
const cameraDistance = Math.max(fitHeightDistance, fitWidthDistance) * 1.7;
const performanceTargetY = size.y * 0.75;
camera.position.set(center.x + 0.15, performanceTargetY + 0.1, center.z + cameraDistance);
camera.lookAt(center.x, performanceTargetY, center.z);

const sharedBonePairs = [];
for (let left = 0; left < performers.length; left += 1) {
  for (let right = left + 1; right < performers.length; right += 1) {
    const overlap = performers[left].boneUuids.filter(uuid => performers[right].boneUuids.includes(uuid));
    if (overlap.length) sharedBonePairs.push([performers[left].config.id, performers[right].config.id]);
  }
}

window.__meta = {
  phase: 4,
  fps: FPS,
  totalFrames: TOTAL_FRAMES,
  characterCount: performers.length,
  mixerCount: performers.length,
  uniqueRootCount: new Set(performers.map(item => item.rootUuid)).size,
  uniqueSkeletonCount: new Set(performers.flatMap(item => item.skeletonUuids)).size,
  sharedSkeletonCorruption: sharedBonePairs.length > 0,
  sharedBonePairs,
  combinedBounds: { min: allBounds.min.toArray(), max: allBounds.max.toArray(), size: size.toArray() },
  cameraFit: { position: camera.position.toArray(), target: [center.x, performanceTargetY, center.z],
    performanceHeight, proportionAware: true },
  characters: performers.map(item => ({ id: item.config.id, tier: item.capability.tier,
    clip: item.clip.name, mixerRootUuid: item.mixer.getRoot().uuid, rootUuid: item.rootUuid,
    skeletonUuids: item.skeletonUuids, materials: item.materials,
    normalizationScale: item.normalizationScale, position: item.holder.position.toArray() })),
  blenderUsedAtRuntime: false,
  facialAnimationClaimed: false,
};

window.__renderFrame = frame => {
  const time = Math.max(0, Math.min(TOTAL_FRAMES - 1, Number(frame))) / FPS;
  for (const performer of performers) {
    const localTime = (time + performer.config.phase) % performer.clip.duration;
    performer.mixer.setTime(localTime);
    if (performer.config.id === 'quaternius_casual_2') {
      const travel = THREE.MathUtils.smoothstep(Math.min(time / 4.5, 1), 0, 1);
      performer.holder.position.x = performer.config.position[0] - 0.7 + travel * 0.7;
    }
  }
  for (const actor of environmentActors) {
    actor.tree.rotation.z = actor.baseRotation + Math.sin(time * 1.15 + actor.phase) * 0.018;
    actor.crown.rotation.y = Math.sin(time * 0.72 + actor.phase) * 0.025;
  }
  renderer.render(scene, camera);
};

window.__sample = () => ({
  characters: performers.map(item => {
    const bounds = new THREE.Box3().setFromObject(item.holder);
    let checksum = 0;
    item.model.traverse(node => {
      if (node.isBone) checksum += node.matrixWorld.elements.reduce((sum, value) => sum + Math.abs(value), 0);
    });
    return { id: item.config.id, clip: item.clip.name, rootUuid: item.rootUuid,
      groundY: bounds.min.y, height: bounds.max.y - bounds.min.y, boneChecksum: checksum };
  }),
});

window.__renderFrame(0);
window.__ready = true;
