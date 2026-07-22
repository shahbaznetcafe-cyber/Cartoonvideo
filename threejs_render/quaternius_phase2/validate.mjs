import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repoRoot = path.resolve(process.argv[2] || path.join(import.meta.dirname, '..', '..'));
const metricsPath = path.join(repoRoot, 'reports', 'quaternius_phase2_render_metrics.json');
const storyboardPath = path.join(repoRoot, 'reports', 'quaternius_phase2_storyboard.json');
const mappingPath = path.join(repoRoot, 'reports', 'quaternius_phase2_clip_mapping.json');
const videoPath = path.join(repoRoot, 'outputs', 'quaternius_phase2_story.mp4');
const milestonesPath = path.join(repoRoot, 'outputs', 'quaternius_phase2_milestones');
const outputPath = path.join(repoRoot, 'reports', 'quaternius_phase2_regression.json');

for (const required of [metricsPath, storyboardPath, mappingPath, videoPath, milestonesPath]) {
  if (!fs.existsSync(required)) throw new Error(`Missing Phase 2 deliverable: ${required}`);
}

const metrics = JSON.parse(fs.readFileSync(metricsPath, 'utf8'));
const storyboard = JSON.parse(fs.readFileSync(storyboardPath, 'utf8'));
const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));
const samples = metrics.samples || [];

const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, { encoding: 'utf8', ...options });
  return {
    ok: result.status === 0,
    status: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
  };
};

const ffprobe = run('ffprobe', [
  '-v', 'error', '-select_streams', 'v:0',
  '-show_entries', 'stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration:format=duration,size',
  '-of', 'json', videoPath,
]);
if (!ffprobe.ok) throw new Error(`ffprobe failed: ${ffprobe.stderr}`);
const media = JSON.parse(ffprobe.stdout);
const video = media.streams[0];

const blackdetect = run('ffmpeg', [
  '-hide_banner', '-i', videoPath,
  '-vf', 'blackdetect=d=0.04:pix_th=0.02',
  '-an', '-f', 'null', 'NUL',
]);
const blackSegments = [...blackdetect.stderr.matchAll(/black_start:([\d.]+).*?black_end:([\d.]+)/g)]
  .map(match => ({ start: Number(match[1]), end: Number(match[2]) }));

const tests = run('cmd.exe', ['/d', '/s', '/c', 'npm test'], {
  cwd: path.join(repoRoot, 'threejs_render'),
});
const passMatch = tests.stdout.match(/ℹ pass (\d+)/);
const failMatch = tests.stdout.match(/ℹ fail (\d+)/);

const byBeat = Object.groupBy(samples, sample => sample.beatId);
const distance = (a, b) => Math.hypot(...a.map((value, index) => value - b[index]));
const range = values => values.length ? Math.max(...values) - Math.min(...values) : 0;
const plantedBeats = storyboard.beats.filter(beat =>
  ['establish_forest', 'notice_box', 'reach_and_contact', 'surprised_reaction', 'point_warning', 'box_aftermath'].includes(beat.id));
const plantedRootDrift = Object.fromEntries(plantedBeats.map(beat => {
  const beatSamples = byBeat[beat.id] || [];
  const origin = beatSamples[0]?.characterPosition || [0, 0, 0];
  return [beat.id, Math.max(0, ...beatSamples.map(sample => distance(origin, sample.characterPosition)))];
}));
const environmentMotion = Object.fromEntries(storyboard.beats.map(beat => [
  beat.id,
  range((byBeat[beat.id] || []).map(sample => sample.environmentChecksum)),
]));
const clipSequence = samples
  .filter((sample, index) => index === 0 || sample.clip !== samples[index - 1].clip)
  .map(sample => ({ frame: sample.frame, beatId: sample.beatId, sourceClip: sample.clip }));
const expectedClips = [...new Set(storyboard.beats.map(beat => beat.sourceClip))];
const embeddedClips = new Set(metrics.meta.clips.map(clip => clip.name));
const milestoneFiles = fs.readdirSync(milestonesPath).filter(name => /\.(jpg|png)$/i.test(name)).sort();
const enterSamples = byBeat.enter_path || [];
const exitSamples = byBeat.quick_exit || [];
const minContactDistance = Math.min(...samples.map(sample => sample.wristContactDistance));
const maxPropMotion = Math.max(...samples.map(sample => sample.propMotionAmount));
const maxBurstParticles = Math.max(...samples.map(sample => sample.visibleBurstParticles));
const maxGroundError = Math.max(...samples.map(sample => Math.abs(sample.bounds.min[1])));

const checks = {
  exactDuration30Seconds: Number(video.duration) === 30 && Number(media.format.duration) === 30,
  exactFrameCount720: Number(video.nb_frames) === 720,
  correctOutputFormat: video.codec_name === 'h264' && video.width === 1920 && video.height === 1080 &&
    video.pix_fmt === 'yuv420p' && video.r_frame_rate === '24/1',
  noBlackFramesAtCuts: blackdetect.ok && blackSegments.length === 0,
  sourceClipsExist: expectedClips.every(clip => embeddedClips.has(clip)),
  allSamplesUseRealClipNames: samples.every(sample => sample.clipIsRealSourceName),
  clipChangesVerified: storyboard.beats.every(beat =>
    samples.some(sample => sample.beatId === beat.id && sample.clip === beat.sourceClip)),
  noPlantedRootDrift: Math.max(...Object.values(plantedRootDrift)) <= 1e-6,
  characterRemainsGrounded: maxGroundError <= 1e-6,
  characterPropContactVerified: minContactDistance <= 0.2,
  propConsequenceVisible: maxPropMotion >= 0.5 && maxBurstParticles >= 1,
  environmentMotionVisibleEveryBeat: Object.values(environmentMotion).every(value => value > 0.001),
  characterEntersFromOutsideFrame: enterSamples[0]?.characterNdc[0] < -1 && enterSamples.at(-1)?.characterNdc[0] > -1,
  characterExitsFrame: Math.abs(exitSamples[0]?.characterNdc[0]) < 1 && Math.abs(exitSamples.at(-1)?.characterNdc[0]) > 1,
  motivatedShotCountAtLeastFour: new Set(storyboard.beats.map(beat => beat.shot)).size >= 4,
  everyBeatHasMilestone: milestoneFiles.length === storyboard.beats.length + 1,
  noRuntimeErrors: metrics.pageErrors.length === 0 && metrics.consoleErrors.length === 0,
  noBlenderAtRuntime: metrics.blenderUsedAtRuntime === false && metrics.meta.blenderUsedAtRuntime === false,
  facialAnimationNotClaimed: metrics.meta.facialAnimation === false && /None/.test(mapping.facialClaim),
  existingRegressionTestsPass: tests.ok && Number(passMatch?.[1]) === 18 && Number(failMatch?.[1] || 0) === 0,
};

const report = {
  schemaVersion: 1,
  title: 'Quaternius Animation POC Phase 2 Regression Results',
  generatedAt: new Date().toISOString(),
  verdict: Object.values(checks).every(Boolean) ? 'PASS_FOR_ISOLATED_VISUAL_REVIEW' : 'FAIL',
  productionReadyClaim: false,
  checks,
  media: {
    codec: video.codec_name,
    width: video.width,
    height: video.height,
    pixelFormat: video.pix_fmt,
    fps: video.r_frame_rate,
    frames: Number(video.nb_frames),
    durationSeconds: Number(video.duration),
    bytes: Number(media.format.size),
    blackSegments,
  },
  storyEvidence: {
    shots: storyboard.beats.map(beat => ({ id: beat.id, shot: beat.shot, sourceClip: beat.sourceClip })),
    clipSequence,
    plantedRootDriftWorldUnits: plantedRootDrift,
    maxGroundErrorWorldUnits: maxGroundError,
    minimumWristToPropContactWorldUnits: minContactDistance,
    maximumPropMotionWorldUnits: maxPropMotion,
    maximumVisibleBurstParticles: maxBurstParticles,
    environmentChecksumSpanByBeat: environmentMotion,
    entryNdcX: [enterSamples[0]?.characterNdc[0], enterSamples.at(-1)?.characterNdc[0]],
    exitNdcX: [exitSamples[0]?.characterNdc[0], exitSamples.at(-1)?.characterNdc[0]],
    milestoneFiles,
  },
  runtime: {
    renderer: metrics.meta.renderer,
    renderSeconds: metrics.renderSeconds,
    peakMemory: metrics.peakMemory,
    deterministicInputs: metrics.deterministicInputs,
    blenderUsed: metrics.blenderUsedAtRuntime,
    facialAnimation: metrics.meta.facialAnimation,
    eyeTarget: metrics.meta.eyeTarget,
    headLookAdditive: metrics.meta.headLookAdditive,
  },
  regressions: {
    command: 'npm test',
    passed: Number(passMatch?.[1] || 0),
    failed: Number(failMatch?.[1] || 0),
    exitCode: tests.status,
  },
  validationNotes: [
    'Planted-pose validation proves zero holder/root drift and zero sampled ground-plane penetration.',
    'Hand/prop contact is supported by measured wrist proximity and the dedicated contact/consequence milestone frames.',
    'No IK foot lock or facial system is claimed; remaining visual limitations are reported separately.',
  ],
};

fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`);
console.log(`${report.verdict} checks=${Object.values(checks).filter(Boolean).length}/${Object.keys(checks).length}`);
console.log(outputPath);
if (report.verdict === 'FAIL') {
  console.error(JSON.stringify(Object.fromEntries(Object.entries(checks).filter(([, passed]) => !passed)), null, 2));
  process.exit(1);
}
