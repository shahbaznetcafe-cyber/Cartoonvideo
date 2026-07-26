import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const repo = path.resolve(process.argv[2] || path.join(import.meta.dirname, '..', '..'));
const paths = {
  video: path.join(repo, 'outputs', 'adventurer_directed_production_scene.mp4'),
  metrics: path.join(repo, 'reports', 'adventurer_directed_production_metrics.json'),
  storyboard: path.join(repo, 'reports', 'sbz_adventurer_production_scene.json'),
  registry: path.join(repo, 'assets', 'characters', 'capability_registry.json'),
  regression: path.join(repo, 'reports', 'adventurer_directed_production_regression.json'),
  untouched: path.join(repo, 'reports', 'adventurer_production_untouched_legacy_files.json'),
  pythonRegression: path.join(repo, 'reports', 'adventurer_production_python_regression.json'),
  executionPlan: path.join(repo, 'reports', 'adventurer_directed_execution_plan.json'),
  encodedManifest: path.join(repo, 'reports', 'adventurer_encoded_milestone_manifest.json'),
  encodedVisualReview: path.join(repo, 'reports', 'adventurer_encoded_visual_review.json'),
  encodedMilestones: path.join(repo, 'outputs', 'adventurer_directed_production_encoded_milestones'),
};
for (const file of [paths.video, paths.metrics, paths.storyboard, paths.registry, paths.pythonRegression,
  paths.executionPlan, paths.encodedManifest, paths.encodedVisualReview]) {
  if (!fs.existsSync(file)) throw new Error(`Missing production integration deliverable: ${file}`);
}

const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, { cwd: repo, encoding: 'utf8', ...options });
  return { ok: result.status === 0, status: result.status, stdout: result.stdout || '', stderr: result.stderr || '' };
};
const metrics = JSON.parse(fs.readFileSync(paths.metrics));
const storyboard = JSON.parse(fs.readFileSync(paths.storyboard));
const registry = JSON.parse(fs.readFileSync(paths.registry));
const character = registry.characters[storyboard.characterId];
const pythonRegression = JSON.parse(fs.readFileSync(paths.pythonRegression));
const executionPlan = JSON.parse(fs.readFileSync(paths.executionPlan));
const encodedManifest = JSON.parse(fs.readFileSync(paths.encodedManifest));
const encodedVisualReview = JSON.parse(fs.readFileSync(paths.encodedVisualReview));
const samples = metrics.samples;
const sha256File = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');

const probeResult = run('ffprobe', ['-v', 'error', '-select_streams', 'v:0',
  '-show_entries', 'stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration:format=duration,size',
  '-of', 'json', paths.video]);
if (!probeResult.ok) throw new Error(probeResult.stderr);
const probe = JSON.parse(probeResult.stdout);
const video = probe.streams[0];
const black = run('ffmpeg', ['-hide_banner', '-i', paths.video, '-vf',
  'blackdetect=d=0.04:pix_th=0.02', '-an', '-f', 'null', 'NUL']);
const blackSegments = [...black.stderr.matchAll(/black_start:([\d.]+).*?black_end:([\d.]+)/g)]
  .map(match => ({ start: Number(match[1]), end: Number(match[2]) }));
const tests = run('cmd.exe', ['/d', '/s', '/c', 'npm test'], { cwd: path.join(repo, 'threejs_render') });
const passCount = Number(tests.stdout.match(/(?:^|\n).*?pass\s+(\d+)/)?.[1] || 0);
const failCount = Number(tests.stdout.match(/(?:^|\n).*?fail\s+(\d+)/)?.[1] || 0);

const byBeat = {};
for (const sample of samples) (byBeat[sample.beatId] ||= []).push(sample);
const range = values => Math.max(...values) - Math.min(...values);
const distance = (a, b) => Math.hypot(...a.map((value, index) => value - b[index]));
const minContact = Math.min(...samples.map(sample => sample.wristContactDistance));
const closestContactSample = samples.reduce((closest, sample) =>
  sample.wristContactDistance < closest.wristContactDistance ? sample : closest, samples[0]);
const maxPropMotion = Math.max(...samples.map(sample => sample.propMotionAmount));
const maxParticles = Math.max(...samples.map(sample => sample.visibleBurstParticles));
const groundError = Math.max(...samples.map(sample => Math.abs(sample.bounds.min[1])));
const environmentSpan = Object.fromEntries(storyboard.beats.map(beat => [beat.id,
  range(byBeat[beat.id].map(sample => sample.environmentChecksum))]));
const plantedIds = ['establish_forest', 'notice_box', 'reach_and_contact', 'surprised_reaction', 'point_warning', 'box_aftermath'];
const plantedDrift = Object.fromEntries(plantedIds.map(id => {
  const origin = byBeat[id][0].characterPosition;
  return [id, Math.max(...byBeat[id].map(sample => distance(origin, sample.characterPosition)))];
}));
const entry = byBeat.enter_path;
const exit = byBeat.quick_exit;
const observedClips = [...new Set(samples.map(sample => sample.clip))];
const forbiddenShots = new Set(['dialogue_close_up', 'facial_close_up']);
const instanced = new Map((metrics.meta.instancedMeshes || []).map(item => [item.name, item.count]));
const movementPlans = executionPlan.beats.filter(beat => beat.movement).map(beat => ({
  beatId: beat.id,
  sourceClip: beat.sourceClip,
  ...beat.movement,
}));
const interactionBeat = executionPlan.beats.find(beat => beat.interaction);
const encodedEntriesValid = encodedManifest.entries.length === 11 && encodedManifest.entries.every(entry => {
  const file = path.join(paths.encodedMilestones, entry.file);
  return fs.existsSync(file) && sha256File(file) === entry.sha256;
});
const requiredSkeletonMappings = ['root', 'hips', 'spine', 'chest', 'neck', 'head',
  'leftUpperArm', 'leftLowerArm', 'leftHand', 'rightUpperArm', 'rightLowerArm', 'rightHand',
  'leftUpperLeg', 'leftLowerLeg', 'leftFoot', 'rightUpperLeg', 'rightLowerLeg', 'rightFoot'];

const legacyFiles = [
  'blender3d.py',
  'char3d_lib.py',
  'threejs_render/render_scene.html',
  'threejs_render/render_scene.js',
  'threejs_render/facial_runtime.js',
  'threejs_render/acting_state_runtime.js',
  'threejs_render/bone_pose_runtime.js',
  'threejs_render/humanoid_motion_runtime.js',
];
const untouchedEntries = legacyFiles.map(file => {
  const head = run('git', ['rev-parse', `HEAD:${file}`]);
  const current = run('git', ['hash-object', file]);
  return { file, headBlob: head.stdout.trim(), currentBlob: current.stdout.trim(),
    unchanged: head.ok && current.ok && head.stdout.trim() === current.stdout.trim() };
});
const untouchedReport = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  statement: 'These legacy/facial production-path files are byte-identical to their HEAD versions.',
  files: untouchedEntries,
  allUnchanged: untouchedEntries.every(entry => entry.unchanged),
};
fs.writeFileSync(paths.untouched, `${JSON.stringify(untouchedReport, null, 2)}\n`);

const checks = {
  exactMediaContract: Number(video.duration) === 30 && Number(probe.format.duration) === 30 &&
    Number(video.nb_frames) === 720 && video.width === 1920 && video.height === 1080 &&
    video.r_frame_rate === '24/1' && video.codec_name === 'h264' && video.pix_fmt === 'yuv420p',
  noBlackFramesAtCuts: black.ok && blackSegments.length === 0,
  registryProvenanceComplete: character.sourcePack === 'Ultimate Modular Men Pack' &&
    character.license?.status === 'verified' && character.license?.name === 'CC0 1.0' &&
    Boolean(character.license?.source) && Boolean(character.assetPath) && Boolean(character.assetSha256),
  registryRigAndClipEvidenceComplete: character.skeleton?.armatureName === 'QuaterniusMasterRig' &&
    character.skeleton?.boneCount === 62 && character.skeleton?.skinnedMeshCount === 5 &&
    requiredSkeletonMappings.every(key => Boolean(character.skeletonMapping?.[key])) &&
    Object.keys(character.authoredClips || {}).length === 28 &&
    character.validation?.status === 'passed_for_skeletal_interactive_single_scene',
  capabilityTierIsInteractive: metrics.meta.capabilityTier === 'SKELETAL_INTERACTIVE',
  notFacialReady: metrics.meta.facialReady === false && metrics.meta.facialAnimation === false,
  directorPlanExecuted: metrics.meta.productionMode === true &&
    metrics.meta.directorGeneratedBy === 'SBZ Animation Director' && metrics.meta.shotPlan.length === 10,
  genericRegistryDrivenExecution: metrics.meta.adventurerSpecificProductionBranching === false &&
    metrics.meta.characterAssetPath === character.assetPath,
  animationMixerOwnsBones: /AnimationMixer owns animated bones/.test(metrics.meta.mixerPolicy),
  onlyRegisteredRealClipsUsed: observedClips.every(clip => Boolean(character.authoredClips[clip])),
  locomotionCyclesMatchDisplacement: movementPlans.length === 4 && movementPlans.every(movement =>
    movement.cycleMatched === true && movement.clipCycles >= 1 &&
    movement.mismatchRatio <= movement.maximumMismatchRatio &&
    character.locomotionProfiles[movement.sourceClip]),
  noForbiddenCloseups: metrics.meta.shotPlan.every(shot => !forbiddenShots.has(shot.type)),
  bodyReactionShotUsed: metrics.meta.shotPlan.some(shot => shot.type === 'body_reaction_medium_close'),
  namedInteractionTargetUsed: metrics.meta.interactionPlan.some(plan =>
    plan.target?.propId === 'suspicious_box' && plan.target?.name === 'reach_handle' && plan.handIK === false),
  contactWithinRegisteredTolerance: minContact <= character.interaction.supported.right_hand_reach.maximumContactDistance,
  interactionTimingAndFacingValidated: interactionBeat?.interaction?.triggerFrame === closestContactSample.frame &&
    closestContactSample.frame === closestContactSample.interactionTriggerFrame &&
    closestContactSample.interactionFacingErrorDegrees <= interactionBeat.interaction.acceptableFacingErrorDegrees,
  propConsequenceVisible: maxPropMotion >= 0.5 && maxParticles >= 1,
  plantedRootStableAndGrounded: Math.max(...Object.values(plantedDrift)) <= 1e-6 && groundError <= 1e-6,
  characterEntersAndExitsFrame: entry[0].characterNdc[0] < -1 && entry.at(-1).characterNdc[0] > -1 &&
    Math.abs(exit[0].characterNdc[0]) < 1 && Math.abs(exit.at(-1).characterNdc[0]) > 1,
  deterministicEnvironmentMovesEveryBeat: Object.values(environmentSpan).every(value => value > 0.001),
  repeatedVegetationUsesInstancing: instanced.get('path_edge_grass_instanced') === 52,
  noRuntimeErrors: metrics.pageErrors.length === 0 && metrics.consoleErrors.length === 0,
  blenderNotUsedAtRuntime: metrics.blenderUsedAtRuntime === false && metrics.meta.blenderUsedAtRuntime === false,
  encodedMilestonesAreFromFinalMp4: encodedManifest.extractedFromEncodedOutput === true &&
    encodedManifest.sourceVideoSha256 === sha256File(paths.video) && encodedEntriesValid,
  encodedMilestonesVisuallyReviewed: encodedVisualReview.reviewed === true &&
    encodedVisualReview.sourceVideoSha256 === encodedManifest.sourceVideoSha256 &&
    encodedVisualReview.reviewedFrames?.length === 11 &&
    encodedVisualReview.checks?.noBlackFrames === true &&
    encodedVisualReview.checks?.noMajorRigDeformation === true &&
    encodedVisualReview.checks?.interactionConsequenceReadable === true &&
    encodedVisualReview.checks?.storyBlockingReadable === true,
  existingAndNewRegressionsPass: tests.ok && passCount === 26 && failCount === 0,
  pythonRepositoryRegressionsPass: pythonRegression.exitCode === 0 &&
    pythonRegression.passed === 96 && pythonRegression.failed === 0 && pythonRegression.errors === 0,
  legacyAndFacialPathsPreservedByRegression: tests.ok && passCount === 26 &&
    pythonRegression.exitCode === 0 && pythonRegression.failed === 0 && pythonRegression.errors === 0,
};

const report = {
  schemaVersion: 1,
  title: 'Adventurer Directed Production Scene — Regression Results',
  generatedAt: new Date().toISOString(),
  verdict: Object.values(checks).every(Boolean) ? 'PASS_FOR_SINGLE_SCENE_REVIEW' : 'FAIL',
  productionReadyClaim: false,
  bulkConversionPerformed: false,
  facialImplementationPerformed: false,
  checks,
  media: { codec: video.codec_name, width: video.width, height: video.height,
    pixelFormat: video.pix_fmt, fps: video.r_frame_rate, frames: Number(video.nb_frames),
    durationSeconds: Number(video.duration), bytes: Number(probe.format.size), blackSegments },
  performance: { renderSeconds: metrics.renderSeconds, peakMemory: metrics.peakMemory },
  capability: { characterId: storyboard.characterId, tier: metrics.meta.capabilityTier,
    facialReady: metrics.meta.facialReady, realClipsObserved: observedClips },
  direction: { shotPlan: metrics.meta.shotPlan, mixerPolicy: metrics.meta.mixerPolicy,
    instancedMeshes: metrics.meta.instancedMeshes },
  interaction: { plan: metrics.meta.interactionPlan, minimumWristTargetDistance: minContact,
    maximumAllowedDistance: character.interaction.supported.right_hand_reach.maximumContactDistance,
    closestContactFrame: closestContactSample.frame,
    facingErrorDegreesAtClosestContact: closestContactSample.interactionFacingErrorDegrees,
    maximumPropMotion: maxPropMotion, maximumVisibleParticles: maxParticles },
  locomotionCycleMatching: movementPlans,
  continuity: { plantedRootDriftWorldUnits: plantedDrift, maximumGroundError: groundError,
    environmentChecksumSpanByBeat: environmentSpan,
    entryNdcX: [entry[0].characterNdc[0], entry.at(-1).characterNdc[0]],
    exitNdcX: [exit[0].characterNdc[0], exit.at(-1).characterNdc[0]] },
  regressions: {
    threejs: { command: 'npm test', passed: passCount, failed: failCount, exitCode: tests.status },
    python: pythonRegression,
    totalPassed: passCount + pythonRegression.passed,
  },
  untouchedLegacyFilesReport: path.relative(repo, paths.untouched).replaceAll('\\', '/'),
  encodedMilestoneManifest: path.relative(repo, paths.encodedManifest).replaceAll('\\', '/'),
  encodedVisualReview: path.relative(repo, paths.encodedVisualReview).replaceAll('\\', '/'),
  deterministicInputs: metrics.deterministicInputs,
};
fs.writeFileSync(paths.regression, `${JSON.stringify(report, null, 2)}\n`);
console.log(`${report.verdict} checks=${Object.values(checks).filter(Boolean).length}/${Object.keys(checks).length} tests=${passCount}`);
if (report.verdict === 'FAIL') {
  console.error(JSON.stringify(Object.fromEntries(Object.entries(checks).filter(([, value]) => !value)), null, 2));
  process.exit(1);
}
