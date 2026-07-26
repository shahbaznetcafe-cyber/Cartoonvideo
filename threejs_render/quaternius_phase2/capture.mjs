import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import puppeteer from '../node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';

const repo = path.resolve(process.argv[2] || path.join(process.cwd(), '..', '..'));
const mode = process.argv.includes('--preflight') ? 'preflight' : 'capture';
const production = process.argv.includes('--production');
const output = path.join(repo, 'outputs', production
  ? 'adventurer_directed_production_scene.mp4'
  : 'quaternius_phase2_story.mp4');
const metricsPath = mode === 'capture'
  ? path.join(repo, 'reports', production
    ? 'adventurer_directed_production_metrics.json'
    : 'quaternius_phase2_render_metrics.json')
  : path.join(repo, 'work', 'character_poc', production
    ? 'adventurer_directed_production_preflight_metrics.json'
    : 'quaternius_phase2_preflight_metrics.json');
const milestoneDir = mode === 'capture'
  ? path.join(repo, 'outputs', production
    ? 'adventurer_directed_production_milestones'
    : 'quaternius_phase2_milestones')
  : path.join(repo, 'work', 'character_poc', production
    ? 'adventurer_directed_production_preflight_frames'
    : 'quaternius_phase2_preflight_frames');
const storyboardPath = path.join(repo, 'reports', production
  ? 'sbz_adventurer_production_scene.json'
  : 'quaternius_phase2_storyboard.json');
const storySourcePath = path.join(repo, 'threejs_render', 'quaternius_phase2', 'story.js');
const registryPath = path.join(repo, 'assets', 'characters', 'capability_registry.json');
const directorSourcePath = path.join(repo, 'threejs_render', 'production', 'animation_director.js');
const capabilitySourcePath = path.join(repo, 'threejs_render', 'production', 'character_capability_registry.js');
const shotDirectorSourcePath = path.join(repo, 'threejs_render', 'production', 'shot_director.js');
const interactionSourcePath = path.join(repo, 'threejs_render', 'production', 'interaction_system.js');
const environmentSourcePath = path.join(repo, 'threejs_render', 'production', 'environment_motion.js');
const productionPagePath = path.join(repo, 'threejs_render', 'production_scene', 'index.html');
const chrome = fs.existsSync('C:/Program Files/Google/Chrome/Application/chrome.exe')
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe';
const ffmpegPath = 'C:/Program Files/ffmpeg/bin/ffmpeg.exe';
const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.bin': 'application/octet-stream',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.txt': 'text/plain',
};

for (const required of [chrome, ffmpegPath, storyboardPath, storySourcePath,
  ...(production ? [registryPath, directorSourcePath, capabilitySourcePath, shotDirectorSourcePath,
    interactionSourcePath, environmentSourcePath, productionPagePath] : []),
  path.join(repo, 'assets', 'characters', 'quaternius_master', 'master_character.glb')]) {
  if (!fs.existsSync(required)) throw new Error(`Required Phase 2 file missing: ${required}`);
}

const storyboard = JSON.parse(fs.readFileSync(storyboardPath, 'utf8'));
const totalFrames = storyboard.totalFrames || Math.round(storyboard.durationSeconds * storyboard.fps);
if (storyboard.durationSeconds !== 30 || storyboard.fps !== 24 || totalFrames !== 720) {
  throw new Error('Storyboard must declare exactly 30 seconds, 24 FPS and 720 frames');
}
const milestoneByFrame = new Map();
for (const beat of storyboard.beats) {
  const milestoneFrame = Number.isInteger(beat.milestoneFrame)
    ? beat.milestoneFrame
    : Math.round((Number(beat.start) + (Number(beat.end) - Number(beat.start)) * 0.5) * storyboard.fps);
  milestoneByFrame.set(milestoneFrame, { beat, label: 'beat' });
  if (Number.isInteger(beat.consequenceFrame)) milestoneByFrame.set(beat.consequenceFrame, { beat, label: 'consequence' });
  if (production && beat.id === 'reach_and_contact') milestoneByFrame.set(342, { beat, label: 'consequence' });
}
let requiredClipNames;
if (production) {
  const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
  const character = registry.characters[storyboard.characterId];
  requiredClipNames = new Set(storyboard.beats.map(beat => {
    const mapping = character?.storyActionClips?.[beat.storyAction];
    if (!mapping?.realClip) throw new Error(`Unresolved production story action: ${beat.storyAction}`);
    return mapping.realClip;
  }));
} else {
  requiredClipNames = new Set(storyboard.beats.map(beat => beat.sourceClip));
}
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.mkdirSync(path.dirname(metricsPath), { recursive: true });
if (fs.existsSync(milestoneDir)) fs.rmSync(milestoneDir, { recursive: true, force: true });
fs.mkdirSync(milestoneDir, { recursive: true });

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function processWorkingSet(pid) {
  if (!pid) return 0;
  try {
    const outputText = execFileSync('tasklist.exe', ['/FI', `PID eq ${pid}`, '/FO', 'CSV', '/NH'], {
      encoding: 'utf8', windowsHide: true, timeout: 4000, stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    if (!outputText || outputText.startsWith('INFO:')) return 0;
    const columns = outputText.match(/("(?:[^"]|"")*"|[^,]+)/g) || [];
    const memoryText = (columns[4] || '').replaceAll('"', '').replace(/[^0-9]/g, '');
    return Number(memoryText || 0) * 1024;
  } catch {
    return 0;
  }
}

const server = http.createServer((request, response) => {
  const raw = decodeURIComponent(request.url.split('?')[0]);
  const relative = raw === '/'
    ? (production ? '/threejs_render/production_scene/index.html' : '/threejs_render/quaternius_phase2/index.html')
    : raw;
  const file = path.resolve(repo, `.${relative}`);
  if (!file.startsWith(repo)) { response.writeHead(403); response.end(); return; }
  fs.readFile(file, (error, data) => {
    if (error) { response.writeHead(404); response.end(); return; }
    response.writeHead(200, {
      'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-store',
    });
    response.end(data);
  });
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: 'new',
  args: [
    '--use-gl=angle', '--use-angle=default', '--enable-webgl', '--ignore-gpu-blocklist', '--no-sandbox',
    '--disable-dev-shm-usage', '--hide-scrollbars', '--force-device-scale-factor=1',
    `--user-data-dir=${path.join(repo, 'work', 'character_poc', production ? 'production_director_chrome_profile' : 'phase2_chrome_profile')}`,
  ],
});
const page = await browser.newPage();
const pageErrors = [];
const consoleErrors = [];
page.on('pageerror', error => { pageErrors.push(String(error)); process.stderr.write(`PAGE_ERROR ${error}\n`); });
page.on('console', message => {
  if (message.type() === 'error') {
    consoleErrors.push(message.text());
    process.stderr.write(`CONSOLE_ERROR ${message.text()}\n`);
  }
});
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
const pagePath = production ? '/threejs_render/production_scene/index.html' : '/threejs_render/quaternius_phase2/index.html';
await page.goto(`http://127.0.0.1:${server.address().port}${pagePath}`, { waitUntil: 'load' });
await page.waitForFunction('window.__ready === true || window.__error', { timeout: 60000 });
const initializationError = await page.evaluate(() => window.__error);
if (initializationError) throw new Error(`Phase 2 Three.js initialization failed: ${initializationError}`);
const meta = await page.evaluate(() => window.__meta);
const exportedClips = new Set(meta.clips.map(clip => clip.name));
for (const clip of requiredClipNames) {
  if (!exportedClips.has(clip)) throw new Error(`Storyboard references unavailable real source clip: ${clip}`);
}
if (meta.facialAnimation !== false || meta.blenderUsedAtRuntime !== false) {
  throw new Error('Phase 2 capability boundary was violated');
}
if (production && (meta.productionMode !== true || meta.capabilityTier !== 'SKELETAL_INTERACTIVE' ||
  meta.facialReady !== false || meta.directorGeneratedBy !== 'SBZ Animation Director')) {
  throw new Error('Production capability/director boundary was violated');
}

const samples = [];
const memorySamples = [];
let peakNodeRss = 0;
let peakBrowserMainWorkingSet = 0;
let peakFfmpegWorkingSet = 0;
let peakBrowserJsHeap = 0;
let peakTrackedBytes = 0;
const started = performance.now();
let ffmpeg = null;
let ffmpegArgs = [];
if (mode === 'capture') {
  ffmpegArgs = [
    '-hide_banner', '-loglevel', 'warning', '-y', '-fflags', '+genpts',
    '-f', 'image2pipe', '-vcodec', 'png', '-framerate', '24', '-i', '-',
    '-frames:v', '720', '-vf', 'scale=1920:1080:flags=lanczos,setsar=1',
    '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-r', '24', '-fps_mode', 'cfr', '-movflags', '+faststart', output,
  ];
  ffmpeg = spawn(ffmpegPath, ffmpegArgs, { stdio: ['pipe', 'inherit', 'inherit'], windowsHide: true });
}

function writePipe(stream, buffer) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = error => {
      if (settled) return;
      settled = true;
      error ? reject(error) : resolve();
    };
    const writable = stream.write(buffer, finish);
    if (!writable) stream.once('drain', () => finish());
  });
}

for (let frame = 0; frame < totalFrames; frame++) {
  await page.evaluate(value => window.__renderFrame(value), frame);
  if (frame % 6 === 0 || milestoneByFrame.has(frame) || frame === totalFrames - 1) {
    samples.push(await page.evaluate(() => window.__sample()));
  }
  if (frame % 24 === 0 || frame === totalFrames - 1) {
    const browserMetrics = await page.metrics();
    const nodeRss = process.memoryUsage().rss;
    const browserMain = processWorkingSet(browser.process()?.pid);
    const ffmpegWorkingSet = processWorkingSet(ffmpeg?.pid);
    const jsHeap = browserMetrics.JSHeapUsedSize || 0;
    const tracked = nodeRss + browserMain + ffmpegWorkingSet + jsHeap;
    peakNodeRss = Math.max(peakNodeRss, nodeRss);
    peakBrowserMainWorkingSet = Math.max(peakBrowserMainWorkingSet, browserMain);
    peakFfmpegWorkingSet = Math.max(peakFfmpegWorkingSet, ffmpegWorkingSet);
    peakBrowserJsHeap = Math.max(peakBrowserJsHeap, jsHeap);
    peakTrackedBytes = Math.max(peakTrackedBytes, tracked);
    memorySamples.push({ frame, nodeRss, browserMainWorkingSet: browserMain, ffmpegWorkingSet, browserJsHeapUsed: jsHeap, trackedBytes: tracked });
  }
  if (mode === 'capture') {
    const png = await page.screenshot({ type: 'png', captureBeyondViewport: false });
    await writePipe(ffmpeg.stdin, png);
  }
  if (milestoneByFrame.has(frame)) {
    const milestone = milestoneByFrame.get(frame);
    const beat = milestone.beat;
    const suffix = milestone.label === 'beat' ? '' : `_${milestone.label}`;
    const file = `${String(storyboard.beats.indexOf(beat) + 1).padStart(2, '0')}_${beat.id}${suffix}_f${String(frame).padStart(3, '0')}.jpg`;
    await page.screenshot({ path: path.join(milestoneDir, file), type: 'jpeg', quality: 92, captureBeyondViewport: false });
  }
}

let ffmpegExit = null;
if (ffmpeg) {
  ffmpeg.stdin.end();
  ffmpegExit = await new Promise((resolve, reject) => {
    ffmpeg.on('error', reject);
    ffmpeg.on('close', resolve);
  });
  if (ffmpegExit !== 0) throw new Error(`FFmpeg exited with code ${ffmpegExit}`);
}
const renderSeconds = (performance.now() - started) / 1000;
const metrics = {
  schemaVersion: 1,
  mode,
  capturedAt: new Date().toISOString(),
  title: storyboard.title,
  width: 1920,
  height: 1080,
  fps: 24,
  frames: 720,
  durationSeconds: 30,
  renderSeconds,
  output: mode === 'capture' ? output : null,
  milestoneDirectory: milestoneDir,
  milestoneFrames: [...milestoneByFrame.keys()],
  ffmpegExit,
  ffmpegCommand: mode === 'capture' ? [ffmpegPath, ...ffmpegArgs] : [],
  deterministicInputs: {
    randomSeed: 20260715,
    storyboardSha256: sha256(storyboardPath),
    storyRuntimeSha256: sha256(storySourcePath),
    capabilityRegistrySha256: production ? sha256(registryPath) : null,
    animationDirectorSha256: production ? sha256(directorSourcePath) : null,
    capabilityRuntimeSha256: production ? sha256(capabilitySourcePath) : null,
    shotDirectorSha256: production ? sha256(shotDirectorSourcePath) : null,
    interactionSystemSha256: production ? sha256(interactionSourcePath) : null,
    environmentMotionSha256: production ? sha256(environmentSourcePath) : null,
    productionPageSha256: production ? sha256(productionPagePath) : null,
    characterGlbSha256: sha256(path.join(repo, 'assets', 'characters', 'quaternius_master', 'master_character.glb')),
  },
  peakMemory: {
    nodeRssBytes: peakNodeRss,
    browserMainWorkingSetBytes: peakBrowserMainWorkingSet,
    ffmpegWorkingSetBytes: peakFfmpegWorkingSet,
    browserJsHeapUsedBytes: peakBrowserJsHeap,
    trackedPeakBytes: peakTrackedBytes,
    trackedPeakMiB: Number((peakTrackedBytes / 1048576).toFixed(2)),
    scope: 'Node RSS + Chrome main-process working set + page JS heap + FFmpeg working set; Chrome child-process native allocations are not included.',
  },
  memorySamples,
  pageErrors,
  consoleErrors,
  meta,
  samples,
  blenderUsedAtRuntime: false,
};
fs.writeFileSync(metricsPath, JSON.stringify(metrics, null, 2));
console.log(`${production ? 'ADVENTURER_PRODUCTION_DIRECTED' : 'QUATERNIUS_PHASE2'}_${mode.toUpperCase()}_OK frames=720 seconds=${renderSeconds.toFixed(2)} milestones=${milestoneByFrame.size} peakTrackedMiB=${metrics.peakMemory.trackedPeakMiB}`);
await browser.close();
server.close();
