import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { spawn } from 'node:child_process';
import puppeteer from '../node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';

const repo = path.resolve(process.argv[2] || path.join(process.cwd(), '..', '..'));
const capture = process.argv.includes('--capture');
const chrome = fs.existsSync('C:/Program Files/Google/Chrome/Application/chrome.exe')
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe';
const ffmpeg = 'C:/Program Files/ffmpeg/bin/ffmpeg.exe';
const output = path.join(repo, 'outputs', 'phase4_multi_character_proof.mp4');
const metricsPath = path.join(repo, 'reports', 'phase4_multi_character_metrics.json');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.glb': 'model/gltf-binary', '.png': 'image/png' };

for (const required of [chrome, path.join(repo, 'threejs_render/phase4_multi_character/index.html'),
  path.join(repo, 'threejs_render/phase4_multi_character/scene.js'),
  path.join(repo, 'assets/characters/capability_registry.json')]) {
  if (!fs.existsSync(required)) throw new Error(`Missing Phase 4 dependency: ${required}`);
}
if (capture && !fs.existsSync(ffmpeg)) throw new Error(`Missing FFmpeg: ${ffmpeg}`);

const server = http.createServer((request, response) => {
  const raw = decodeURIComponent(request.url.split('?')[0]);
  const relative = raw === '/' ? '/threejs_render/phase4_multi_character/index.html' : raw;
  const file = path.resolve(repo, `.${relative}`);
  if (!file.startsWith(repo)) { response.writeHead(403); response.end(); return; }
  fs.readFile(file, (error, data) => {
    if (error) { response.writeHead(404); response.end(); return; }
    response.writeHead(200, { 'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-store' });
    response.end(data);
  });
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));

const browser = await puppeteer.launch({ executablePath: chrome, headless: 'new',
  args: ['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist', '--no-sandbox',
    '--disable-dev-shm-usage', '--hide-scrollbars', '--force-device-scale-factor=1'],
  userDataDir: path.join(repo, 'work/character_phase4/chrome_profile') });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
const pageErrors = [];
const requestErrors = [];
let sceneReady = false;
page.on('pageerror', error => { pageErrors.push(String(error)); console.error(`[pageerror] ${error}`); });
page.on('console', message => {
  if (message.type() === 'error') console.error(`[console] ${message.text()}`);
});
page.on('requestfailed', request => {
  const errorText = request.failure()?.errorText || 'failed';
  // Chromium can cancel a duplicate/no-longer-needed model request after the
  // scene has already loaded. Keep preflight failures strict, but do not turn
  // that harmless post-ready cancellation into a false regression.
  if (sceneReady && errorText === 'net::ERR_ABORTED') return;
  const detail = `${request.url()} :: ${errorText}`;
  requestErrors.push(detail);
  console.error(`[requestfailed] ${detail}`);
});
await page.goto(`http://127.0.0.1:${server.address().port}/threejs_render/phase4_multi_character/index.html`,
  { waitUntil: 'load' });
await page.waitForFunction('window.__ready === true || window.__error', { timeout: 180000 });
const sceneError = await page.evaluate(() => window.__error);
if (sceneError) throw new Error(`Phase 4 scene failed: ${sceneError}`);
const meta = await page.evaluate(() => window.__meta);
sceneReady = true;
if (meta.characterCount !== 3 || meta.mixerCount !== 3 || meta.uniqueRootCount !== 3) {
  throw new Error('Phase 4 independent instance/mixer contract failed');
}
if (meta.sharedSkeletonCorruption || meta.uniqueSkeletonCount < 3) {
  throw new Error('Phase 4 detected a shared or corrupted skeleton');
}
if (meta.blenderUsedAtRuntime || meta.facialAnimationClaimed) {
  throw new Error('Phase 4 capability/runtime boundary failed');
}
if (pageErrors.length || requestErrors.length) {
  throw new Error(`Phase 4 browser errors: ${[...pageErrors, ...requestErrors].join(' | ')}`);
}

const samples = [];
let encoder = null;
const started = performance.now();
if (capture) {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  encoder = spawn(ffmpeg, ['-hide_banner', '-loglevel', 'warning', '-y', '-f', 'image2pipe',
    '-vcodec', 'png', '-framerate', '24', '-i', '-', '-frames:v', '144', '-an',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-r', '24', '-fps_mode', 'cfr', '-movflags', '+faststart', output],
  { stdio: ['pipe', 'inherit', 'inherit'], windowsHide: true });
}

function writeFrame(buffer) {
  return new Promise((resolve, reject) => {
    encoder.stdin.write(buffer, error => error ? reject(error) : resolve());
  });
}

const frames = capture ? Array.from({ length: 144 }, (_, index) => index) : [0, 36, 72, 108, 143];
for (const frame of frames) {
  await page.evaluate(value => window.__renderFrame(value), frame);
  if (!capture || frame % 24 === 0 || frame === 143) {
    samples.push({ frame, ...(await page.evaluate(() => window.__sample())) });
  }
  if (!capture && frame === 72) {
    fs.mkdirSync(path.join(repo, 'outputs'), { recursive: true });
    await page.screenshot({ path: path.join(repo, 'outputs', 'phase4_multi_character_preflight.jpg'),
      type: 'jpeg', quality: 92, captureBeyondViewport: false });
  }
  if (capture) await writeFrame(await page.screenshot({ type: 'png', captureBeyondViewport: false }));
}
if (encoder) {
  encoder.stdin.end();
  await new Promise((resolve, reject) => {
    encoder.once('error', reject);
    encoder.once('close', code => code === 0 ? resolve() : reject(new Error(`FFmpeg exited ${code}`)));
  });
}

for (const sample of samples) {
  for (const character of sample.characters) {
    if (Math.abs(character.groundY) > 0.02) {
      throw new Error(`${character.id} ground offset ${character.groundY} exceeds tolerance`);
    }
  }
}
for (const character of meta.characters) {
  const checksums = samples.map(sample => sample.characters.find(item => item.id === character.id)?.boneChecksum);
  if (new Set(checksums.map(value => Number(value).toFixed(5))).size < 2) {
    throw new Error(`${character.id} animation state did not change`);
  }
  if (!character.materials.length) throw new Error(`${character.id} has no runtime materials`);
}

const metrics = { schemaVersion: 1, status: 'PASS', capture, output: capture ? output : null,
  durationSeconds: 6, fps: 24, totalFrames: 144,
  renderSeconds: Number(((performance.now() - started) / 1000).toFixed(3)),
  meta, samples, pageErrors, requestErrors };
fs.mkdirSync(path.dirname(metricsPath), { recursive: true });
fs.writeFileSync(metricsPath, JSON.stringify(metrics, null, 2));
await browser.close();
await new Promise(resolve => server.close(resolve));
console.log(`PHASE4_MULTI_CHARACTER=${capture ? 'CAPTURED' : 'PREFLIGHT_PASS'}`);
