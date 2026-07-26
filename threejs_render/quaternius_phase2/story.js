import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { loadCapabilityRegistry } from '../production/character_capability_registry.js';
import { AnimationDirector, MixerClipController } from '../production/animation_director.js';

const FPS = 24;
const TOTAL_FRAMES = 720;
const BOX_POSITION = new THREE.Vector3(1.05, 0, 0.24);
const ENTER_START = new THREE.Vector3(-6.65, 0, 0.58);
const NOTICE_POSITION = new THREE.Vector3(-2.45, 0, 0.34);
const APPROACH_POSITION = new THREE.Vector3(0.16, 0, 0.29);
const BACK_POSITION = new THREE.Vector3(-1.22, 0, 0.43);
const EXIT_POSITION = new THREE.Vector3(-9.0, 0, -0.22);
const loader = new GLTFLoader();
const productionMode = location.pathname.includes('/production_scene/');
const storyboardUrl = productionMode
  ? '/reports/sbz_adventurer_production_scene.json'
  : '/reports/quaternius_phase2_storyboard.json';
const storyboard = await fetch(storyboardUrl).then(response => {
  if (!response.ok) throw new Error(`Storyboard load failed: HTTP ${response.status}`);
  return response.json();
});
const capabilityRegistry = productionMode ? await loadCapabilityRegistry() : null;
const directorPlan = productionMode
  ? new AnimationDirector({ registry: capabilityRegistry }).compile(storyboard)
  : null;

const declaredFrames = directorPlan?.totalFrames ?? storyboard.totalFrames;
if (declaredFrames !== TOTAL_FRAMES || storyboard.fps !== FPS || storyboard.durationSeconds !== 30) {
  throw new Error('Storyboard timing contract must be exactly 720 frames at 24 FPS');
}

const canvas = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(1920, 1080, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.98;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8fb5ad);
scene.fog = new THREE.FogExp2(0x789887, 0.024);
const camera = new THREE.PerspectiveCamera(36, 16 / 9, 0.05, 80);

const sky = new THREE.Mesh(
  new THREE.SphereGeometry(34, 32, 20),
  new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      topColor: { value: new THREE.Color(0x648f91) },
      horizonColor: { value: new THREE.Color(0xc1c99f) },
      warmColor: { value: new THREE.Color(0xe5c78e) },
    },
    vertexShader: 'varying vec3 vWorld; void main(){ vec4 world=modelMatrix*vec4(position,1.0); vWorld=world.xyz; gl_Position=projectionMatrix*viewMatrix*world; }',
    fragmentShader: 'varying vec3 vWorld; uniform vec3 topColor; uniform vec3 horizonColor; uniform vec3 warmColor; void main(){ float h=clamp(normalize(vWorld).y*0.72+0.35,0.0,1.0); vec3 c=mix(horizonColor,topColor,smoothstep(0.08,0.95,h)); float glow=pow(max(0.0,normalize(vWorld).x*0.55+normalize(vWorld).y*0.35),5.0); gl_FragColor=vec4(mix(c,warmColor,glow*0.22),1.0); }',
  }),
);
scene.add(sky);

const hemi = new THREE.HemisphereLight(0xcfe5d8, 0x324531, 1.38);
scene.add(hemi);
const fill = new THREE.DirectionalLight(0x9ab8bd, 0.72);
fill.position.set(4, 3.5, -5);
scene.add(fill);
const sun = new THREE.DirectionalLight(0xffe6bd, 2.15);
sun.position.set(-5.5, 8.5, 5.2);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -9;
sun.shadow.camera.right = 9;
sun.shadow.camera.top = 8;
sun.shadow.camera.bottom = -8;
sun.shadow.camera.near = 0.1;
sun.shadow.camera.far = 28;
sun.shadow.bias = -0.00022;
sun.shadow.normalBias = 0.025;
scene.add(sun, sun.target);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(28, 20),
  new THREE.MeshStandardMaterial({ color: 0x496c3f, roughness: 1, metalness: 0 }),
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.025;
ground.receiveShadow = true;
scene.add(ground);

function seeded(seed) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 4294967296;
  };
}
const random = seeded(20260715);

function addPath() {
  const shape = new THREE.Shape();
  const upper = [];
  const lower = [];
  for (let i = 0; i <= 18; i++) {
    const x = -9 + i;
    const center = 0.16 * Math.sin(x * 0.48) + 0.05 * Math.sin(x * 1.3);
    const half = 0.78 + 0.09 * Math.sin(x * 0.83 + 1.2);
    upper.push([x, center + half]);
    lower.push([x, center - half]);
  }
  shape.moveTo(...upper[0]);
  for (const point of upper.slice(1)) shape.lineTo(...point);
  for (const point of lower.reverse()) shape.lineTo(...point);
  shape.closePath();
  const path = new THREE.Mesh(
    new THREE.ShapeGeometry(shape),
    new THREE.MeshStandardMaterial({ color: 0x9b8060, roughness: 1, metalness: 0 }),
  );
  path.rotation.x = -Math.PI / 2;
  path.position.y = -0.004;
  path.receiveShadow = true;
  scene.add(path);

  const pebbleMaterial = new THREE.MeshStandardMaterial({ color: 0x6a6656, roughness: 1 });
  const pebbles = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.08, 0), pebbleMaterial, 48);
  pebbles.name = 'path_pebbles_instanced';
  const pebbleMatrix = new THREE.Matrix4();
  const pebbleQuaternion = new THREE.Quaternion();
  const pebbleScale = new THREE.Vector3();
  for (let i = 0; i < 48; i++) {
    const x = -8.5 + random() * 17;
    const side = i % 2 ? 1 : -1;
    const z = side * (0.82 + random() * 0.23) + Math.sin(x * 0.48) * 0.16;
    const size = 0.56 + random() * 0.69;
    pebbleQuaternion.setFromEuler(new THREE.Euler(random(), random() * Math.PI, random()));
    pebbleScale.set(size, size * (0.45 + random() * 0.25), size);
    pebbleMatrix.compose(new THREE.Vector3(x, 0.01, z), pebbleQuaternion, pebbleScale);
    pebbles.setMatrixAt(i, pebbleMatrix);
  }
  pebbles.instanceMatrix.needsUpdate = true;
  pebbles.castShadow = true;
  pebbles.receiveShadow = true;
  scene.add(pebbles);
}
addPath();

function addInstancedVegetation() {
  const grass = new THREE.InstancedMesh(
    new THREE.ConeGeometry(0.055, 0.34, 5),
    new THREE.MeshStandardMaterial({ color: 0x6f8c45, roughness: 1 }),
    52,
  );
  grass.name = 'path_edge_grass_instanced';
  const matrix = new THREE.Matrix4();
  for (let i = 0; i < grass.count; i++) {
    const x = -8.3 + random() * 16.6;
    const side = i % 2 ? 1 : -1;
    const z = side * (1.03 + random() * 0.62) + Math.sin(x * 0.48) * 0.16;
    const scale = 0.65 + random() * 0.7;
    matrix.compose(new THREE.Vector3(x, 0.15 * scale, z),
      new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), random() * Math.PI * 2),
      new THREE.Vector3(scale, scale, scale));
    grass.setMatrixAt(i, matrix);
  }
  grass.instanceMatrix.needsUpdate = true;
  grass.castShadow = true;
  grass.receiveShadow = true;
  scene.add(grass);
}
addInstancedVegetation();

function addGroundVariation() {
  const colors = [0x3e6539, 0x557848, 0x365a36, 0x607f4b];
  for (let i = 0; i < 32; i++) {
    const patch = new THREE.Mesh(
      new THREE.CircleGeometry(0.3 + random() * 1.0, 12),
      new THREE.MeshStandardMaterial({ color: colors[i % colors.length], roughness: 1 }),
    );
    patch.rotation.x = -Math.PI / 2;
    patch.position.set(-8 + random() * 16, -0.015, -6 + random() * 12);
    patch.scale.x = 1.4 + random() * 1.5;
    scene.add(patch);
  }
  const hillMaterialA = new THREE.MeshStandardMaterial({ color: 0x385f42, roughness: 1 });
  const hillMaterialB = new THREE.MeshStandardMaterial({ color: 0x2e5140, roughness: 1 });
  for (let i = 0; i < 7; i++) {
    const hill = new THREE.Mesh(new THREE.SphereGeometry(2.8, 16, 10), i % 2 ? hillMaterialA : hillMaterialB);
    hill.scale.set(1.8 + random(), 0.55 + random() * 0.25, 1);
    hill.position.set(-11 + i * 3.7, -1.7, -9.5 - (i % 2) * 1.8);
    hill.receiveShadow = true;
    scene.add(hill);
  }
}
addGroundVariation();

function load(url) {
  return new Promise((resolve, reject) => loader.load(url, resolve, undefined, reject));
}

function enableShadows(root) {
  root.traverse(object => {
    if (object.isMesh || object.isSkinnedMesh) {
      object.castShadow = true;
      object.receiveShadow = true;
      object.frustumCulled = false;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      for (const material of materials) if (material) material.side = THREE.FrontSide;
    }
  });
}

function groundAndScale(root, targetHeight, position, yaw = 0) {
  root.updateMatrixWorld(true);
  let box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3();
  box.getSize(size);
  root.scale.multiplyScalar(targetHeight / Math.max(0.001, size.y));
  root.updateMatrixWorld(true);
  box = new THREE.Box3().setFromObject(root);
  const center = new THREE.Vector3();
  box.getCenter(center);
  root.position.x -= center.x;
  root.position.y -= box.min.y;
  root.position.z -= center.z;
  const holder = new THREE.Group();
  holder.position.copy(position);
  holder.rotation.y = yaw;
  holder.add(root);
  scene.add(holder);
  return holder;
}

const windObjects = [];
async function placeNature(url, targetHeight, placements, kind) {
  const gltf = await load(url);
  for (let i = 0; i < placements.length; i++) {
    const [x, z, scale = 1, yaw = 0, foreground = false] = placements[i];
    const clone = gltf.scene.clone(true);
    enableShadows(clone);
    const holder = groundAndScale(clone, targetHeight * scale, new THREE.Vector3(x, 0, z), yaw);
    holder.userData.foreground = foreground;
    windObjects.push({
      holder,
      kind,
      amplitude: kind === 'tree' ? 0.008 : (kind === 'bush' ? 0.022 : 0.035),
      speed: 0.72 + (i % 4) * 0.11,
      phase: i * 1.73 + (kind === 'tree' ? 0 : 0.8),
    });
  }
}

function makeCloud(x, y, z, scale, phase) {
  const group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({ color: 0xc9d7c8, roughness: 1, transparent: true, opacity: 0.72 });
  for (const [dx, dy, size] of [[0,0,1],[-.52,-.05,.68],[.52,-.08,.74],[.12,.2,.55]]) {
    const puff = new THREE.Mesh(new THREE.SphereGeometry(0.58 * size, 14, 9), material);
    puff.position.set(dx, dy, 0);
    group.add(puff);
  }
  group.position.set(x, y, z);
  group.scale.setScalar(scale);
  group.userData.baseX = x;
  group.userData.phase = phase;
  scene.add(group);
  return group;
}
const clouds = [makeCloud(-5, 5.2, -10, 1.2, 0), makeCloud(3.8, 4.7, -12, 0.9, 2.4)];

function createBox() {
  const anchor = new THREE.Group();
  anchor.position.copy(BOX_POSITION);
  const visual = new THREE.Group();
  anchor.add(visual);

  const wood = new THREE.MeshStandardMaterial({ color: 0x51402f, roughness: 0.78, metalness: 0 });
  const edge = new THREE.MeshStandardMaterial({ color: 0x252c27, roughness: 0.52, metalness: 0.3 });
  const rune = new THREE.MeshStandardMaterial({ color: 0xc8793b, emissive: 0x6d220d, emissiveIntensity: 0.75, roughness: 0.5 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.58, 0.64), wood);
  body.position.y = 0.31;
  body.castShadow = true;
  body.receiveShadow = true;
  visual.add(body);

  for (const x of [-0.33, 0.33]) {
    const band = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.6, 0.67), edge);
    band.position.set(x, 0.31, 0);
    band.castShadow = true;
    visual.add(band);
  }
  const lock = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.18, 0.05), rune);
  lock.position.set(0, 0.36, 0.345);
  lock.castShadow = true;
  visual.add(lock);

  const contactPost = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.035, 0.4, 8), edge);
  contactPost.position.set(-0.28, 0.88, 0.16);
  contactPost.castShadow = true;
  visual.add(contactPost);
  const contactKnob = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 8), rune);
  contactKnob.position.set(-0.28, 1.1, 0.16);
  contactKnob.castShadow = true;
  visual.add(contactKnob);

  const lidPivot = new THREE.Group();
  lidPivot.position.set(0, 0.63, -0.27);
  const lid = new THREE.Mesh(new THREE.BoxGeometry(0.84, 0.14, 0.68), wood);
  lid.position.set(0, 0, 0.27);
  lid.castShadow = true;
  lid.receiveShadow = true;
  lidPivot.add(lid);
  const lidBand = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.16, 0.7), edge);
  lidBand.position.set(0, 0.01, 0.27);
  lidBand.castShadow = true;
  lidPivot.add(lidBand);
  visual.add(lidPivot);

  const contactGlow = new THREE.PointLight(0xe98545, 0, 2.2, 2);
  contactGlow.position.set(0, 0.8, 0.15);
  anchor.add(contactGlow);
  scene.add(anchor);
  return { anchor, visual, lidPivot, rune, contactGlow, contactKnob };
}
const suspiciousBox = createBox();

const burstParticles = [];
function createBurstParticles() {
  const colors = [0xd38b3f, 0xe7b85b, 0x789848, 0x9d5937];
  for (let i = 0; i < 28; i++) {
    const material = new THREE.MeshBasicMaterial({ color: colors[i % colors.length], transparent: true, opacity: 0, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(new THREE.CircleGeometry(0.025 + random() * 0.025, 5), material);
    mesh.visible = false;
    scene.add(mesh);
    burstParticles.push({
      mesh,
      velocity: new THREE.Vector3((random() - 0.5) * 1.25, 0.7 + random() * 1.0, (random() - 0.5) * 1.15),
      spin: (random() - 0.5) * 13,
      delay: random() * 0.18,
    });
  }
}
createBurstParticles();

const ambientLeaves = [];
function createAmbientLeaves() {
  const materialColors = [0x8c6239, 0xb0783d, 0x738d3f, 0xc29754];
  for (let i = 0; i < 28; i++) {
    const material = new THREE.MeshStandardMaterial({ color: materialColors[i % materialColors.length], roughness: 1, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(new THREE.CircleGeometry(0.022 + random() * 0.022, 5), material);
    mesh.castShadow = true;
    scene.add(mesh);
    ambientLeaves.push({
      mesh,
      x: -8 + random() * 16,
      y: 0.6 + random() * 3.4,
      z: -4 + random() * 8,
      drift: 0.12 + random() * 0.2,
      fall: 0.055 + random() * 0.07,
      phase: random() * Math.PI * 2,
      spin: 0.8 + random() * 1.8,
    });
  }
}
createAmbientLeaves();

const birds = [];
function createBirds() {
  const geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-0.12, 0, 0), new THREE.Vector3(0, 0.06, 0),
    new THREE.Vector3(0, 0.06, 0), new THREE.Vector3(0.12, 0, 0),
  ]);
  const material = new THREE.LineBasicMaterial({ color: 0x263932, transparent: true, opacity: 0.76 });
  for (let i = 0; i < 3; i++) {
    const bird = new THREE.LineSegments(geometry, material);
    bird.position.set(-6 - i * 1.4, 3.7 + i * 0.27, -6.5 - i * 0.8);
    bird.scale.setScalar(0.8 + i * 0.12);
    scene.add(bird);
    birds.push({ mesh: bird, phase: i * 2.1, baseY: bird.position.y, baseZ: bird.position.z });
  }
}
createBirds();

let characterRoot;
let characterHolder;
let mixer;
let mixerController;
let clips = {};
let currentAction = null;
let currentClip = '';
let currentStage = -1;
let lastFrame = -1;
let bones = [];
let boneByName = new Map();
let headBone = null;
let chestBone = null;
let leftWrist = null;
let rightWrist = null;
let propMotionAmount = 0;
let visibleBurstParticles = 0;
let lastShot = '';

const STAGES = (directorPlan?.beats || storyboard.beats).map(beat => ({
  ...beat,
  loop: beat.loop ?? !['reach_and_contact', 'surprised_reaction'].includes(beat.id),
  shot: beat.camera?.type || beat.shot,
}));
const CONTACT_STAGE = STAGES.find(stage => stage.interaction) || STAGES.find(stage => stage.id === 'reach_and_contact');
const AFTERMATH_STAGE = STAGES.find(stage => stage.environmentEvents?.includes('box_lid_twitch'))
  || STAGES.find(stage => stage.id === 'box_aftermath');
const PROP_TRIGGER_TIME = CONTACT_STAGE?.interaction?.triggerTime ??
  (CONTACT_STAGE && CONTACT_STAGE.environmentEvents?.includes('box_lid_pop')
  ? CONTACT_STAGE.start + 1
  : 13.75);
const PROP_AFTERMATH_TIME = AFTERMATH_STAGE && AFTERMATH_STAGE.environmentEvents?.includes('box_lid_twitch')
  ? AFTERMATH_STAGE.start + 0.85
  : 28.35;

function normalizeBoneName(name) {
  return String(name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function ease(value) {
  const t = THREE.MathUtils.clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function stageIndex(time) {
  const found = STAGES.findIndex(stage => time >= stage.start && time < stage.end);
  return found < 0 ? STAGES.length - 1 : found;
}

function stageProgress(time, stage = STAGES[currentStage]) {
  return THREE.MathUtils.clamp((time - stage.start) / Math.max(0.001, stage.end - stage.start), 0, 1);
}

function clipTimeScale(stage) {
  const clip = clips[stage.sourceClip];
  if (!clip) return 1;
  if (Number.isFinite(stage.movement?.clipTimeScale)) return stage.movement.clipTimeScale;
  const duration = stage.end - stage.start;
  if (stage.clipCycles) return clip.duration * stage.clipCycles / duration;
  if (stage.id === 'reach_and_contact') return clip.duration / 1.8;
  if (stage.id === 'surprised_reaction') return clip.duration / 1.05;
  if (stage.id === 'point_warning') return 0.72;
  if (stage.id === 'notice_box') return 0.72;
  return 1;
}

function playStage(stage, fade = 0.24) {
  const clip = clips[stage.sourceClip];
  if (!clip) throw new Error(`Real source clip missing: ${stage.sourceClip}`);
  if (mixerController) {
    const next = stage.interruptible
      ? mixerController.interruptWith(stage, clipTimeScale(stage))
      : mixerController.play(stage, clipTimeScale(stage));
    currentAction = next;
    currentClip = stage.sourceClip;
    return;
  }
  const next = mixer.clipAction(clip);
  next.enabled = true;
  next.reset();
  next.setEffectiveWeight(1);
  next.setEffectiveTimeScale(clipTimeScale(stage));
  next.clampWhenFinished = !stage.loop;
  next.setLoop(stage.loop ? THREE.LoopRepeat : THREE.LoopOnce, stage.loop ? Infinity : 1);
  next.play();
  if (currentAction && currentAction !== next) currentAction.crossFadeTo(next, fade, true);
  currentAction = next;
  currentClip = stage.sourceClip;
}

function directionYaw(from, to) {
  const direction = new THREE.Vector3().subVectors(to, from);
  return Math.atan2(direction.x, direction.z);
}
const enterYaw = directionYaw(ENTER_START, NOTICE_POSITION);
const boxYaw = directionYaw(APPROACH_POSITION, BOX_POSITION);
const exitYaw = directionYaw(BACK_POSITION, EXIT_POSITION);

function lerpConstant(out, from, to, progress) {
  out.lerpVectors(from, to, THREE.MathUtils.clamp(progress, 0, 1));
}

function updateCharacterTransform(time) {
  const stage = STAGES[currentStage];
  const progress = stageProgress(time, stage);
  if (directorPlan) {
    characterHolder.visible = stage.characterVisibility !== 'offscreen';
    if (stage.movement) {
      lerpConstant(characterHolder.position, vec(stage.startPosition), vec(stage.endPosition), progress);
    } else {
      characterHolder.position.copy(vec(stage.endPosition));
    }
    const targetYaw = Number(stage.facingYaw) || 0;
    if (stage.turnFromPrevious) {
      const turnWindow = Number(stage.turnDurationRatio) || 0.35;
      const turnProgress = ease(Math.min(1, progress / turnWindow));
      const delta = Math.atan2(Math.sin(targetYaw - stage.startFacingYaw), Math.cos(targetYaw - stage.startFacingYaw));
      characterHolder.rotation.y = stage.startFacingYaw + delta * turnProgress;
    } else {
      characterHolder.rotation.y = targetYaw;
    }
    return;
  }
  characterHolder.visible = !['establish_forest', 'box_aftermath'].includes(stage.id);
  switch (stage.id) {
    case 'establish_forest':
      characterHolder.position.copy(ENTER_START);
      characterHolder.rotation.y = enterYaw;
      break;
    case 'enter_path':
      lerpConstant(characterHolder.position, stage.movement ? vec(stage.movement.from) : ENTER_START,
        stage.movement ? vec(stage.movement.to) : NOTICE_POSITION, progress);
      characterHolder.position.z += Math.sin(progress * Math.PI) * 0.08;
      characterHolder.rotation.y = enterYaw;
      break;
    case 'notice_box':
      characterHolder.position.copy(NOTICE_POSITION);
      characterHolder.rotation.y = THREE.MathUtils.lerp(enterYaw, boxYaw, ease(progress));
      break;
    case 'cautious_approach':
      lerpConstant(characterHolder.position, stage.movement ? vec(stage.movement.from) : NOTICE_POSITION,
        stage.movement ? vec(stage.movement.to) : APPROACH_POSITION, progress);
      characterHolder.rotation.y = boxYaw;
      break;
    case 'reach_and_contact':
      characterHolder.position.copy(stage.interaction ? vec(stage.interaction.characterPosition) : APPROACH_POSITION);
      characterHolder.rotation.y = stage.interaction?.facingYaw ?? boxYaw;
      break;
    case 'surprised_reaction':
      characterHolder.position.copy(CONTACT_STAGE?.interaction
        ? vec(CONTACT_STAGE.interaction.characterPosition)
        : APPROACH_POSITION);
      characterHolder.rotation.y = CONTACT_STAGE?.interaction?.facingYaw ?? boxYaw;
      break;
    case 'step_backward':
      lerpConstant(characterHolder.position, stage.movement ? vec(stage.movement.from) : APPROACH_POSITION,
        stage.movement ? vec(stage.movement.to) : BACK_POSITION, progress);
      characterHolder.rotation.y = boxYaw;
      break;
    case 'point_warning':
      characterHolder.position.copy(BACK_POSITION);
      characterHolder.rotation.y = boxYaw;
      break;
    case 'quick_exit':
      lerpConstant(characterHolder.position, stage.movement ? vec(stage.movement.from) : BACK_POSITION,
        stage.movement ? vec(stage.movement.to) : EXIT_POSITION, progress);
      characterHolder.rotation.y = THREE.MathUtils.lerp(boxYaw, exitYaw, ease(Math.min(1, progress * 3.4)));
      break;
    default:
      characterHolder.position.copy(EXIT_POSITION);
      characterHolder.rotation.y = exitYaw;
  }
}

function applySafeAdditives(time) {
  const stage = STAGES[currentStage];
  const progress = stageProgress(time, stage);
  let lookWeight = 0;
  if (directorPlan && stage.lookMode === 'head_only') {
    lookWeight = stage.purpose === 'prop_reveal' ? ease(Math.min(1, progress * 2)) : 0.45;
  } else if (stage.id === 'notice_box') lookWeight = ease(Math.min(1, progress * 2));
  else if (stage.id === 'cautious_approach') lookWeight = 0.65;
  else if (stage.id === 'reach_and_contact') lookWeight = 0.5;
  else if (stage.id === 'point_warning') lookWeight = 0.35;
  if (headBone && lookWeight) {
    const offset = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), 0.045 * lookWeight);
    headBone.quaternion.multiply(offset);
  }
  if (chestBone && (directorPlan ? !stage.movement : ['notice_box', 'point_warning'].includes(stage.id))) {
    const breath = 1 + Math.sin(time * 2.25) * 0.0035;
    chestBone.scale.multiplyScalar(breath);
  }
}

function groundCharacter() {
  characterRoot.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(characterRoot);
  const correction = THREE.MathUtils.clamp(-bounds.min.y, -0.045, 0.045);
  characterRoot.position.y += correction;
  characterRoot.updateMatrixWorld(true);
}

function updateProp(time) {
  suspiciousBox.anchor.position.copy(BOX_POSITION);
  suspiciousBox.visual.position.set(0, 0, 0);
  suspiciousBox.visual.rotation.set(0, 0, 0);
  suspiciousBox.lidPivot.rotation.x = 0;
  suspiciousBox.contactGlow.intensity = 0.06 + Math.sin(time * 2.4) * 0.03;
  suspiciousBox.rune.emissiveIntensity = 0.64 + Math.sin(time * 2.1) * 0.18;
  propMotionAmount = 0;
  visibleBurstParticles = 0;

  const eventTime = PROP_TRIGGER_TIME;
  const elapsed = time - eventTime;
  if (elapsed >= 0 && elapsed < 1.65) {
    const decay = Math.exp(-elapsed * 1.75);
    const shake = Math.sin(elapsed * 58) * 0.072 * decay;
    const bounce = Math.abs(Math.sin(elapsed * 13)) * 0.11 * decay;
    suspiciousBox.visual.position.set(shake, bounce, Math.sin(elapsed * 41) * 0.025 * decay);
    suspiciousBox.visual.rotation.z = shake * 0.32;
    suspiciousBox.visual.rotation.y = -shake * 0.45;
    let lidAngle;
    if (elapsed < 0.32) lidAngle = THREE.MathUtils.lerp(0, -1.08, ease(elapsed / 0.32));
    else if (elapsed < 0.92) lidAngle = -1.08 + Math.sin((elapsed - 0.32) * 17) * 0.08 * decay;
    else lidAngle = THREE.MathUtils.lerp(-1.08, -0.18, ease((elapsed - 0.92) / 0.73));
    suspiciousBox.lidPivot.rotation.x = lidAngle;
    suspiciousBox.contactGlow.intensity = 1.7 * decay;
    suspiciousBox.rune.emissiveIntensity = 1.5 * decay + 0.5;
    propMotionAmount = Math.abs(shake) + bounce + Math.abs(lidAngle);
  }

  const aftermath = time - PROP_AFTERMATH_TIME;
  if (aftermath >= 0 && aftermath < 0.9) {
    const envelope = Math.sin(Math.PI * THREE.MathUtils.clamp(aftermath / 0.9, 0, 1));
    suspiciousBox.lidPivot.rotation.x = -0.26 * envelope;
    suspiciousBox.visual.rotation.z = Math.sin(aftermath * 28) * 0.035 * envelope;
    suspiciousBox.contactGlow.intensity = 0.45 * envelope;
    propMotionAmount = Math.abs(suspiciousBox.lidPivot.rotation.x) + Math.abs(suspiciousBox.visual.rotation.z);
  }

  for (const particle of burstParticles) {
    const local = elapsed - particle.delay;
    if (local >= 0 && local < 1.45) {
      particle.mesh.visible = true;
      particle.mesh.material.opacity = Math.max(0, 1 - local / 1.45);
      particle.mesh.position.copy(BOX_POSITION).add(new THREE.Vector3(0, 0.7, 0));
      particle.mesh.position.addScaledVector(particle.velocity, local);
      particle.mesh.position.y -= 1.55 * local * local * 0.5;
      particle.mesh.rotation.set(local * particle.spin, local * particle.spin * 0.7, local * particle.spin * 0.4);
      visibleBurstParticles++;
    } else {
      particle.mesh.visible = false;
      particle.mesh.material.opacity = 0;
    }
  }
}

function updateEnvironment(time) {
  let checksum = 0;
  const windStrength = directorPlan?.environment?.config?.windStrength ?? 0.62;
  for (let i = 0; i < windObjects.length; i++) {
    const item = windObjects[i];
    const gust = 0.6 + 0.4 * Math.sin(time * 0.23 + item.phase * 0.4);
    item.holder.rotation.z = Math.sin(time * item.speed + item.phase) * item.amplitude * gust * windStrength;
    item.holder.rotation.x = Math.sin(time * item.speed * 0.57 + item.phase) * item.amplitude * 0.28 * windStrength;
    checksum += (i + 1) * (item.holder.rotation.z * 7 + item.holder.rotation.x * 3);
  }
  for (let i = 0; i < ambientLeaves.length; i++) {
    const leaf = ambientLeaves[i];
    const cycle = (time * leaf.fall + leaf.phase * 0.17) % 1;
    leaf.mesh.position.set(
      leaf.x + time * leaf.drift - Math.floor((leaf.x + time * leaf.drift + 8) / 16) * 16,
      0.35 + (1 - cycle) * leaf.y,
      leaf.z + Math.sin(time * 0.8 + leaf.phase) * 0.52,
    );
    leaf.mesh.rotation.set(time * leaf.spin, time * leaf.spin * 0.63 + leaf.phase, Math.sin(time + leaf.phase));
    checksum += leaf.mesh.position.y * (i + 1) * 0.01;
  }
  for (let i = 0; i < birds.length; i++) {
    const bird = birds[i];
    bird.mesh.position.x = -7 + ((time * (0.72 + i * 0.08) + bird.phase) % 15);
    bird.mesh.position.y = bird.baseY + Math.sin(time * 1.7 + bird.phase) * 0.15;
    bird.mesh.position.z = bird.baseZ;
    bird.mesh.scale.y = 0.65 + Math.abs(Math.sin(time * 7.4 + bird.phase)) * 0.65;
    checksum += bird.mesh.position.x * (i + 1) * 0.02;
  }
  for (let i = 0; i < clouds.length; i++) {
    clouds[i].position.x = clouds[i].userData.baseX + Math.sin(time * 0.035 + clouds[i].userData.phase) * 1.2;
    checksum += clouds[i].position.x * 0.005;
  }
  return checksum;
}

function vec(values) {
  return new THREE.Vector3(...values);
}

function updateCamera(time) {
  const stage = STAGES[currentStage];
  const p = ease(stageProgress(time, stage));
  const character = characterHolder.position;
  let start;
  let end;
  let targetStart;
  let targetEnd;
  let fov = 36;
  switch (stage.camera?.type || stage.id) {
    case 'establishing_wide':
    case 'establish_forest':
      start = vec([6.9, 4.2, 8.6]); end = vec([6.1, 3.85, 7.7]);
      targetStart = vec([-0.25, 0.72, -0.35]); targetEnd = vec([0.05, 0.72, -0.2]); fov = 39;
      break;
    case 'tracking_medium':
    case 'enter_path':
      start = vec([-2.3, 1.82, 3.6]); end = vec([-0.8, 1.72, 3.2]);
      targetStart = vec([-3.55, 0.92, 0.42]); targetEnd = vec([-1.75, 0.94, 0.3]); fov = 36;
      break;
    case 'prop_detail_close':
    case 'notice_box':
      start = vec([2.35, 0.82, 1.78]); end = vec([1.92, 0.68, 1.45]);
      targetStart = BOX_POSITION.clone().add(vec([-0.05, 0.42, 0]));
      targetEnd = BOX_POSITION.clone().add(vec([0, 0.39, 0])); fov = 31;
      break;
    case 'motivated_two_shot':
    case 'cautious_approach':
      start = vec([3.7, 1.82, 3.75]); end = vec([3.0, 1.58, 3.05]);
      targetStart = character.clone().lerp(BOX_POSITION, 0.53).add(vec([0, 0.82, 0]));
      targetEnd = character.clone().lerp(BOX_POSITION, 0.58).add(vec([0, 0.78, 0])); fov = 35;
      break;
    case 'contact_oblique_close':
    case 'reach_and_contact':
      start = vec([2.45, 1.34, 2.45]); end = vec([2.12, 1.18, 2.08]);
      targetStart = vec([0.58, 0.82, 0.26]); targetEnd = vec([0.67, 0.72, 0.25]); fov = 32;
      break;
    case 'body_reaction_medium_close':
    case 'surprised_reaction':
      start = vec([1.95, 1.62, 2.15]); end = vec([1.75, 1.55, 1.95]);
      targetStart = vec([0.18, 1.02, 0.31]); targetEnd = vec([0.16, 1.0, 0.3]); fov = 34;
      break;
    case 'reverse_medium':
    case 'step_backward':
      start = vec([3.05, 1.78, 3.15]); end = vec([2.82, 1.72, 3.0]);
      targetStart = vec([0.38, 0.9, 0.3]); targetEnd = vec([-0.1, 0.9, 0.35]); fov = 36;
      break;
    case 'over_shoulder_prop':
    case 'point_warning':
      start = vec([-2.52, 1.62, 1.86]); end = vec([-2.26, 1.54, 1.68]);
      targetStart = vec([0.42, 0.84, 0.28]); targetEnd = vec([0.56, 0.8, 0.27]); fov = 34;
      break;
    case 'tracking_exit_wide':
    case 'quick_exit':
      start = vec([-2.55, 1.82, 3.25]); end = vec([-3.05, 2.18, 4.55]);
      targetStart = vec([-1.85, 0.92, 0.25]); targetEnd = vec([-3.65, 0.82, -0.08]); fov = 38;
      break;
    default:
      start = vec([2.55, 0.94, 1.95]); end = vec([2.18, 0.82, 1.58]);
      targetStart = BOX_POSITION.clone().add(vec([0, 0.42, 0]));
      targetEnd = BOX_POSITION.clone().add(vec([0, 0.38, 0])); fov = 30;
  }
  camera.position.lerpVectors(start, end, p);
  const target = new THREE.Vector3().lerpVectors(targetStart, targetEnd, p);
  camera.fov = fov;
  camera.updateProjectionMatrix();
  camera.lookAt(target);
  lastShot = stage.shot;
}

function currentBounds() {
  characterRoot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(characterRoot);
  const size = new THREE.Vector3(); box.getSize(size);
  return { min: box.min.toArray(), max: box.max.toArray(), size: size.toArray() };
}

function boneChecksum() {
  let value = 0;
  for (let i = 0; i < bones.length; i++) {
    const q = bones[i].quaternion;
    value += (i + 1) * (q.x * 1.7 + q.y * 2.3 + q.z * 3.1 + q.w * 0.19);
  }
  return value;
}

function worldPosition(object) {
  const value = new THREE.Vector3();
  object?.getWorldPosition(value);
  return value;
}

function projected(position) {
  return position.clone().project(camera).toArray();
}

async function initialize() {
  await Promise.all([
    placeNature('../quaternius_poc/assets/nature/CommonTree_1.gltf', 3.5, [
      [-6.5,-3.2,1.1,.2],[-3.7,-3.8,.92,-.4],[-0.8,-4.5,1.05,.35],[2.7,-4.0,.94,-.25],[5.8,-3.2,1.15,.45],
      [-5.6,3.5,1.2,-.2,true],[4.8,3.4,1.25,.25,true],[-8.0,0.1,.85,.4],[7.8,-.2,.9,-.35],
    ], 'tree'),
    placeNature('../quaternius_poc/assets/nature/Rock_Medium_1.gltf', 0.72, [
      [-5.1,-1.2,.65,.2],[-3.0,1.35,.48,-.4],[-0.9,-1.35,.62,.2],[2.6,-1.05,.75,.45],[4.2,1.25,.58,-.3],[6.0,-1.0,.8,.1],
    ], 'rock'),
    placeNature('../quaternius_poc/assets/nature/Bush_Common.gltf', 0.8, [
      [-6.2,-2.3,.9,0],[-2.1,-1.7,.72,-.2],[0.2,-1.65,.78,.2],[2.3,1.58,.8,-.2],[5.7,1.8,.86,.1],
    ], 'bush'),
    placeNature('../quaternius_poc/assets/nature/Flower_3_Group.gltf', 0.4, [
      [-5.7,1.2,1,0],[-4.1,-1.15,.9,.3],[-2.8,1.08,.85,-.2],[-1.2,-1.08,.8,.1],[0.4,1.1,.9,.2],[1.9,-1.05,.78,-.2],[3.3,1.12,.92,.3],[5.0,-1.1,1,0],
    ], 'flower'),
  ]);

  const characterAssetPath = directorPlan?.character?.assetPath
    ? `/${directorPlan.character.assetPath.replace(/^\/+/, '')}`
    : '../../assets/characters/quaternius_master/master_character.glb';
  const gltf = await load(characterAssetPath);
  characterRoot = gltf.scene;
  enableShadows(characterRoot);
  characterRoot.traverse(object => {
    if (object.isBone) {
      bones.push(object);
      boneByName.set(normalizeBoneName(object.name), object);
    }
    if (object.isSkinnedMesh) object.skeleton?.pose();
  });
  characterRoot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(characterRoot);
  const center = new THREE.Vector3(); box.getCenter(center);
  characterRoot.position.x -= center.x;
  characterRoot.position.y -= box.min.y;
  characterRoot.position.z -= center.z;
  characterHolder = new THREE.Group();
  characterHolder.add(characterRoot);
  scene.add(characterHolder);
  characterHolder.position.copy(directorPlan ? vec(STAGES[0].startPosition) : ENTER_START);
  characterHolder.rotation.y = directorPlan ? STAGES[0].startFacingYaw : enterYaw;

  const skeletonMap = directorPlan?.character?.skeletonMapping || {};
  headBone = boneByName.get(normalizeBoneName(skeletonMap.head || 'head')) || null;
  chestBone = boneByName.get(normalizeBoneName(skeletonMap.chest || 'chest'))
    || boneByName.get('torso') || null;
  leftWrist = boneByName.get(normalizeBoneName(skeletonMap.leftHand || 'wristl')) || null;
  rightWrist = boneByName.get(normalizeBoneName(skeletonMap.rightHand || 'wristr')) || null;
  clips = Object.fromEntries(gltf.animations.map(clip => [clip.name, clip]));
  if (directorPlan) {
    if (bones.length !== directorPlan.character.skeleton.boneCount) {
      throw new Error(`Registry bone count mismatch: expected ${directorPlan.character.skeleton.boneCount}, got ${bones.length}`);
    }
    for (const [name, metadata] of Object.entries(directorPlan.character.authoredClips)) {
      const clip = clips[name];
      if (!clip) throw new Error(`Registry authored clip missing from GLB: ${name}`);
      if (Math.abs(clip.duration - metadata.durationSeconds) > 0.0011) {
        throw new Error(`Registry clip duration mismatch for ${name}`);
      }
    }
  }
  for (const stage of STAGES) if (!clips[stage.sourceClip]) throw new Error(`Storyboard references missing source clip: ${stage.sourceClip}`);
  mixer = new THREE.AnimationMixer(characterRoot);
  if (productionMode) mixerController = new MixerClipController({ mixer, clips, three: THREE });
  currentStage = 0;
  playStage(STAGES[0], 0);
  mixer.update(0);
  updateCharacterTransform(0);
  updateProp(0);
  updateEnvironment(0);
  updateCamera(0);
  groundCharacter();
  renderer.render(scene, camera);

  window.__meta = {
    title: storyboard.title,
    clips: gltf.animations.map(clip => ({ name: clip.name, duration: clip.duration })),
    storyboardClips: [...new Set(STAGES.map(stage => stage.sourceClip))],
    bones: bones.map(bone => bone.name),
    headLookAdditive: Boolean(headBone),
    eyeTarget: false,
    facialAnimation: false,
    environmentObjects: windObjects.length,
    ambientLeaves: ambientLeaves.length,
    birds: birds.length,
    shadows: renderer.shadowMap.enabled,
    renderer: 'Three.js WebGLRenderer + GLTFLoader + AnimationMixer',
    blenderUsedAtRuntime: false,
    productionMode,
    capabilityTier: directorPlan?.character?.tier || 'PHASE2_PROOF',
    facialReady: directorPlan?.character?.facial?.ready ?? false,
    directorGeneratedBy: directorPlan?.generatedBy || null,
    characterAssetPath: directorPlan?.character?.assetPath || null,
    adventurerSpecificProductionBranching: false,
    mixerPolicy: directorPlan?.mixerPolicy || null,
    shotPlan: directorPlan?.beats?.map(beat => ({ id: beat.id, type: beat.camera.type, purpose: beat.camera.purpose })) || [],
    interactionPlan: directorPlan?.beats?.filter(beat => beat.interaction).map(beat => beat.interaction) || [],
    environmentPlan: directorPlan?.environment || null,
    instancedMeshes: scene.children.filter(object => object.isInstancedMesh)
      .map(object => ({ name: object.name, count: object.count })),
  };
  window.__ready = true;
}

let environmentChecksum = 0;
window.__renderFrame = frame => {
  if (!window.__ready) return;
  if (frame < lastFrame) throw new Error('Phase 2 renderer expects monotonic frame order');
  const time = frame / FPS;
  const nextStage = stageIndex(time);
  if (nextStage !== currentStage) {
    currentStage = nextStage;
    playStage(STAGES[currentStage], 0.24);
  }
  if (frame > lastFrame) mixer.update((frame - Math.max(lastFrame, 0)) / FPS);
  updateCharacterTransform(time);
  applySafeAdditives(time);
  groundCharacter();
  updateProp(time);
  environmentChecksum = updateEnvironment(time);
  updateCamera(time);
  renderer.render(scene, camera);
  lastFrame = frame;
};

window.__sample = () => {
  const time = Math.max(0, lastFrame) / FPS;
  const stage = STAGES[currentStage];
  const left = worldPosition(leftWrist);
  const right = worldPosition(rightWrist);
  const contact = CONTACT_STAGE?.interaction?.target?.position
    ? vec(CONTACT_STAGE.interaction.target.position)
    : suspiciousBox.anchor.localToWorld(new THREE.Vector3(-0.28, 1.1, 0.16));
  const characterWorld = characterHolder.position.clone();
  const bounds = currentBounds();
  return {
    frame: lastFrame,
    time,
    beatId: stage?.id || '',
    storyAction: stage?.storyAction || '',
    shot: lastShot,
    clip: currentClip,
    clipIsRealSourceName: Boolean(clips[currentClip]),
    planted: ['establish_forest', 'notice_box', 'reach_and_contact', 'surprised_reaction', 'point_warning', 'box_aftermath'].includes(stage?.id),
    characterPosition: characterHolder.position.toArray(),
    characterYaw: characterHolder.rotation.y,
    characterNdc: projected(characterWorld.clone().add(new THREE.Vector3(0, 0.9, 0))),
    cameraPosition: camera.position.toArray(),
    boneChecksum: boneChecksum(),
    bounds,
    leftWrist: left.toArray(),
    rightWrist: right.toArray(),
    propContactPoint: contact.toArray(),
    wristContactDistance: Math.min(left.distanceTo(contact), right.distanceTo(contact)),
    interactionFacingErrorDegrees: CONTACT_STAGE?.interaction
      ? Math.abs(Math.atan2(Math.sin(characterHolder.rotation.y - CONTACT_STAGE.interaction.facingYaw),
        Math.cos(characterHolder.rotation.y - CONTACT_STAGE.interaction.facingYaw))) * 180 / Math.PI
      : null,
    interactionTolerance: CONTACT_STAGE?.interaction?.maximumContactDistance ?? null,
    interactionTriggerFrame: CONTACT_STAGE?.interaction?.triggerFrame ?? null,
    propMotionAmount,
    visibleBurstParticles,
    environmentChecksum,
    propNdc: projected(contact),
    renderInfo: {
      calls: renderer.info.render.calls,
      triangles: renderer.info.render.triangles,
      geometries: renderer.info.memory.geometries,
      textures: renderer.info.memory.textures,
    },
  };
};

window.__error = null;
window.addEventListener('error', event => { window.__error = String(event.error || event.message); });
initialize().catch(error => {
  window.__error = String(error?.stack || error);
  console.error(error);
});

window.__fps = FPS;
window.__totalFrames = TOTAL_FRAMES;
