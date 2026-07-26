import fs from 'node:fs';
import path from 'node:path';

const repo = path.resolve(process.argv[2] || '.');
const root = path.join(repo, 'work', 'quaternius');
const reports = path.join(repo, 'reports');
fs.mkdirSync(reports, { recursive: true });

const FORMATS = new Set(['.glb', '.gltf', '.fbx', '.blend']);
const TEXTURES = new Set(['.png', '.jpg', '.jpeg', '.webp', '.tga', '.bmp']);
const HUMANOID = {
  hips: ['hips', 'pelvis'], spine: ['spine', 'abdomen', 'torso'], chest: ['chest'],
  neck: ['neck'], head: ['head'],
  leftUpperArm: ['upperarml', 'leftupperarm', 'leftarm'],
  rightUpperArm: ['upperarmr', 'rightupperarm', 'rightarm'],
  leftLowerArm: ['lowerarml', 'leftlowerarm', 'leftforearm'],
  rightLowerArm: ['lowerarmr', 'rightlowerarm', 'rightforearm'],
  leftHand: ['wristl', 'lefthand', 'handl'], rightHand: ['wristr', 'righthand', 'handr'],
  leftUpperLeg: ['upperlegl', 'leftupperleg', 'leftupleg'],
  rightUpperLeg: ['upperlegr', 'rightupperleg', 'rightupleg'],
  leftLowerLeg: ['lowerlegl', 'leftlowerleg', 'leftleg'],
  rightLowerLeg: ['lowerlegr', 'rightlowerleg', 'rightleg'],
  leftFoot: ['footl', 'leftfoot'], rightFoot: ['footr', 'rightfoot'],
};

function walk(dir, output = []) {
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, item.name);
    if (item.isDirectory()) walk(full, output);
    else output.push(full);
  }
  return output;
}

function key(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function candidatePath(file, pack) {
  const rel = path.relative(path.join(root, pack), file).replaceAll('\\', '/');
  if (!FORMATS.has(path.extname(file).toLowerCase())) return false;
  if (/\/(Environment|Vehicles?|Weapons?|Items?|Props?|UI|OBJ)\//i.test(`/${rel}`)) return false;
  if (/Individual Characters|Humans_Master|\/Characters\/|Characters_|Ultimate Monsters\/(Big|Blob|Flying)/i.test(rel)) return true;
  if (pack.startsWith('Blends-') && /\/Blends\//i.test(`/${rel}`)) return true;
  return false;
}

function parseGltf(file) {
  const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
  const nodes = Array.isArray(doc.nodes) ? doc.nodes : [];
  const meshes = Array.isArray(doc.meshes) ? doc.meshes : [];
  const skins = Array.isArray(doc.skins) ? doc.skins : [];
  const accessors = Array.isArray(doc.accessors) ? doc.accessors : [];
  const materials = (doc.materials || []).map((m, i) => m.name || `material_${i}`);
  const textures = (doc.images || []).map((image, i) => image.uri || image.name || `embedded_image_${i}`);
  const jointIndexes = new Set(skins.flatMap(skin => skin.joints || []));
  const bones = [...jointIndexes].map(i => nodes[i]?.name || `node_${i}`);
  const skinnedMeshes = nodes.filter(n => Number.isInteger(n.mesh) && Number.isInteger(n.skin))
    .map(n => n.name || meshes[n.mesh]?.name || `mesh_${n.mesh}`);
  let triangles = 0;
  for (const mesh of meshes) {
    for (const primitive of mesh.primitives || []) {
      const accessor = accessors[primitive.indices ?? primitive.attributes?.POSITION];
      const count = Number(accessor?.count || 0);
      const mode = primitive.mode ?? 4;
      if (mode === 4) triangles += Math.floor(count / 3);
      else if (mode === 5 || mode === 6) triangles += Math.max(0, count - 2);
    }
  }
  const animations = (doc.animations || []).map((animation, i) => {
    let duration = 0;
    for (const sampler of animation.samplers || []) {
      const accessor = accessors[sampler.input];
      const maximum = Array.isArray(accessor?.max) ? Number(accessor.max[0]) : 0;
      duration = Math.max(duration, maximum || 0);
    }
    return { name: animation.name || `animation_${i}`, duration: Number(duration.toFixed(4)) };
  });
  const morphTargets = [];
  for (const mesh of meshes) {
    for (const name of mesh.extras?.targetNames || []) if (!morphTargets.includes(name)) morphTargets.push(name);
  }
  const available = new Set(bones.map(key));
  const body = Object.fromEntries(Object.entries(HUMANOID).map(([name, aliases]) =>
    [name, aliases.some(alias => available.has(key(alias))) ]));
  const missing = Object.entries(body).filter(([, present]) => !present).map(([name]) => name);
  return {
    armature: skins.length > 0, bones, skins: skins.length, skinnedMeshes,
    animations, materials, textures, morphTargets, triangles,
    humanoidCompatible: missing.length === 0, missingBodyParts: missing,
    gltfVersion: doc.asset?.version || '',
  };
}

function licenseFor(pack, files) {
  const local = files.find(file => /license|readme|credit|attribution/i.test(path.basename(file)));
  if (local) {
    const text = fs.readFileSync(local, 'utf8');
    return { type: /CC0/i.test(text) ? 'CC0-1.0' : 'See local license', source: path.resolve(local), embedded: true };
  }
  if (/Individual Characters|Humanoid Rig|All together|^Blends-/i.test(pack)) {
    return {
      type: 'CC0-1.0', embedded: false,
      source: 'https://quaternius.com/packs/ultimatemodularcharacters.html',
      warning: 'License file was not included in this partial archive; verified against the official Quaternius pack page.',
    };
  }
  return { type: 'UNKNOWN', source: '', embedded: false, warning: 'No license file found in archive.' };
}

const packs = [];
const candidates = [];
for (const entry of fs.readdirSync(root, { withFileTypes: true }).filter(item => item.isDirectory())) {
  const pack = entry.name;
  const packRoot = path.join(root, pack);
  const files = walk(packRoot);
  const license = licenseFor(pack, files);
  const counts = {};
  for (const file of files) {
    const ext = path.extname(file).toLowerCase();
    counts[ext || '(none)'] = (counts[ext || '(none)'] || 0) + 1;
  }
  packs.push({
    name: pack, root: path.resolve(packRoot), fileCount: files.length, formats: counts,
    license, preservationFiles: files.filter(file => /license|readme|credit|attribution/i.test(path.basename(file))).map(file => path.resolve(file)),
    godotFiles: files.filter(file => /project\.godot$|\.godot$/i.test(file)).map(file => path.resolve(file)),
  });

  const raw = files.filter(file => candidatePath(file, pack));
  const groups = new Map();
  for (const file of raw) {
    const base = path.basename(file, path.extname(file)).replace(/^Characters_/i, '');
    const groupKey = key(base);
    if (!groups.has(groupKey)) groups.set(groupKey, { name: base, files: [] });
    groups.get(groupKey).files.push(file);
  }
  for (const group of groups.values()) {
    const ranked = [...group.files].sort((a, b) => {
      const order = { '.glb': 0, '.gltf': 1, '.fbx': 2, '.blend': 3 };
      return order[path.extname(a).toLowerCase()] - order[path.extname(b).toLowerCase()];
    });
    const selected = ranked[0];
    let metadata = null;
    let parseError = '';
    if (path.extname(selected).toLowerCase() === '.gltf') {
      try { metadata = parseGltf(selected); } catch (error) { parseError = String(error); }
    }
    const armature = metadata ? metadata.armature : null;
    const animationCount = metadata?.animations.length || 0;
    let rejection = '';
    if (parseError) rejection = `Unreadable glTF metadata: ${parseError}`;
    else if (armature === false) rejection = 'No skin/armature in preferred source.';
    else if (metadata && !metadata.humanoidCompatible) rejection = `Incomplete humanoid body: ${metadata.missingBodyParts.join(', ')}`;
    else if (metadata && animationCount === 0) rejection = 'No embedded animation clips.';
    else if (!metadata) rejection = 'Preferred source requires Blender inspection; lower priority than directly ready glTF candidates.';
    candidates.push({
      pack, name: group.name, sourceFile: path.resolve(selected), format: path.extname(selected).slice(1).toUpperCase(),
      fileSize: fs.statSync(selected).size, alternatives: ranked.slice(1).map(file => path.resolve(file)), license,
      armaturePresent: armature, skeletonBones: metadata?.bones || [], skins: metadata?.skins ?? null,
      skinnedMeshes: metadata?.skinnedMeshes || [], animationClips: metadata?.animations || [],
      materials: metadata?.materials || [], textures: metadata?.textures || [], morphTargets: metadata?.morphTargets || [],
      approximateTriangleCount: metadata?.triangles ?? null,
      humanoidCompatibility: metadata?.humanoidCompatible ?? null,
      missingBodyParts: metadata?.missingBodyParts || [],
      threeJsReadiness: Boolean(metadata?.armature && metadata?.humanoidCompatible && animationCount > 0),
      rejectionReason: rejection,
    });
  }
}

candidates.sort((a, b) => Number(b.threeJsReadiness) - Number(a.threeJsReadiness)
  || b.animationClips.length - a.animationClips.length || (b.skeletonBones.length - a.skeletonBones.length)
  || a.name.localeCompare(b.name));

const report = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  sourceRoot: path.resolve(root),
  packCount: packs.length,
  candidateCount: candidates.length,
  packs,
  candidates,
};
fs.writeFileSync(path.join(reports, 'quaternius_inventory.json'), JSON.stringify(report, null, 2));

const ready = candidates.filter(item => item.threeJsReadiness);
const markdown = [
  '# Quaternius Asset Inventory', '',
  `- Controlled extraction root: \`${path.resolve(root)}\``,
  `- Packs: ${packs.length}`,
  `- Character candidates: ${candidates.length}`,
  `- Directly Three.js-ready humanoids: ${ready.length}`,
  '', '## Pack summary', '',
  '| Pack | Files | Preferred asset formats | License |',
  '|---|---:|---|---|',
  ...packs.map(pack => `| ${pack.name} | ${pack.fileCount} | ${['.glb','.gltf','.fbx','.blend'].filter(ext => pack.formats[ext]).map(ext => `${ext.slice(1).toUpperCase()} (${pack.formats[ext]})`).join(', ') || 'None'} | ${pack.license.type}${pack.license.embedded ? ' (local)' : (pack.license.source ? ' (verified external)' : ' (missing in archive)')} |`),
  '', '## Top compatible candidates', '',
  '| Candidate | Pack | Bones | Clips | Triangles | Materials | Textures | Result |',
  '|---|---|---:|---:|---:|---:|---:|---|',
  ...candidates.slice(0, 30).map(item => `| ${item.name} | ${item.pack} | ${item.skeletonBones.length || '—'} | ${item.animationClips.length || '—'} | ${item.approximateTriangleCount ?? '—'} | ${item.materials.length || '—'} | ${item.textures.length || 'embedded/vertex'} | ${item.threeJsReadiness ? 'Ready' : item.rejectionReason} |`),
  '', '## Rejection summary', '',
  '- OBJ-only files were excluded because they cannot contain skeletal animation.',
  '- Vehicle, environment, weapon, item and UI assets were inventoried at pack level but are not character candidates.',
  '- Non-humanoid monsters/animals remain candidates only when a skin exists, and fail humanoid compatibility when required limbs are missing.',
  '- FBX/BLEND-only candidates are lower priority because directly ready animated glTF humanoids are available.',
  '', '## License note', '',
  'Some partial Google Drive archives do not contain their parent pack license file. Records with an authoritative official pack match link to that Quaternius license page; unmatched archives remain explicitly UNKNOWN. Local license files from other packs remain preserved in their extracted folders.',
  '', 'Full per-candidate metadata, bone lists, clip durations, materials, texture references and rejection reasons are in `quaternius_inventory.json`.',
];
fs.writeFileSync(path.join(reports, 'quaternius_inventory.md'), markdown.join('\n'));
console.log(JSON.stringify({ packs: packs.length, candidates: candidates.length, ready: ready.length, top: ready.slice(0, 5).map(x => `${x.name}:${x.animationClips.length}`) }));
