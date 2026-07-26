// Three.js headless scene render — blender3d spec le kar frames banata (animate_scene.py ka replacement).
// Run: node render_scene.js <spec.json>
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import http from 'http';
import path from 'path';

const CHROME = fs.existsSync('C:/Program Files/Google/Chrome/Application/chrome.exe')
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe';
const HERE = process.cwd();

function slug(p) { return path.basename(p).replace(/\.(blend|glb)$/i, ''); }

const specIn = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
const [VW, VH] = (specIn.res || '960x540').split('x').map(Number);
const fps = specIn.fps || 24;

// blend->glb, openness/viseme JSON->values, env->url
const chars = specIn.chars.map(c => {
  let op = [0];
  let visemes = null;
  if (c.speaking && c.openness && fs.existsSync(c.openness)) {
    try { op = JSON.parse(fs.readFileSync(c.openness, 'utf-8')).values || [0]; } catch (e) {}
  }
  if (c.speaking && c.visemes && fs.existsSync(c.visemes)) {
    try {
      const candidate = JSON.parse(fs.readFileSync(c.visemes, 'utf-8'));
      if (candidate && Array.isArray(candidate.frames)) visemes = candidate;
    } catch (e) {}
  }
  return { id: c.id || `slot_${c.slot}`, glb: `./assets/chars/${slug(c.blend)}.glb`,
           slot: c.slot, speaking: !!c.speaking,
           capabilityId: c.capabilityId || '', animationTier: c.animationTier || 'LEGACY',
           facialTier: c.facialTier || '', speechMode: c.speechMode || 'body_only',
           lipSyncMode: c.lipSyncMode || 'none', facialReady: !!c.facialReady,
           library: c.library || 'sbz',
           openness: op, visemes, emotion: c.emotion || 'neutral',
           costume: c.costume || '', accessory: c.accessory || '', held: c.held || '',
           action: c.action || 'none', sourceClip: c.sourceClip || '',
           baseClip: c.baseClip || '', crossfadeSeconds: Number(c.crossfadeSeconds) || .22,
           blocking: c.blocking || {}, interaction: c.interaction || null,
           target: (c.target == null ? -1 : c.target),
           acting: c.acting || {}, traits: c.traits || {} };
});
const env = specIn.env ? `./assets/env/${path.basename(specIn.env)}` : '';
const backgroundSource = specIn.backgroundImage && fs.existsSync(specIn.backgroundImage)
  ? path.resolve(specIn.backgroundImage) : '';
// Production scene assets are read only sources selected by scene_assets.py.
// Give every GLTF a scoped URL so its .bin and texture siblings resolve
// locally, without exposing arbitrary filesystem paths to the browser.
const sceneAssetRoots = new Map();
const props = (Array.isArray(specIn.props) ? specIn.props : []).map((prop, index) => {
  const asset = prop && prop.asset;
  if (!asset || !asset.source || !fs.existsSync(asset.source)) return prop;
  const source = path.resolve(asset.source);
  const key = `asset_${index}`;
  sceneAssetRoots.set(key, path.dirname(source));
  return { ...prop, asset: { ...asset, url: `/scene-assets/${key}/${encodeURIComponent(path.basename(source))}` } };
});
const pageSpec = { res: [VW, VH], fps, env, exposure: specIn.exposure || -0.2,
  frameCount: Math.max(2, Math.ceil((Number(specIn.duration) || 0) * fps)),
  shot: specIn.shot || 'wide', focus: specIn.focus || 0,
  sceneLook: specIn.sceneLook || 'sunny', timeOffset: Number(specIn.timeOffset) || 0,
  direction: specIn.direction || {}, environmentMotion: specIn.environmentMotion || {},
  backgroundImage: backgroundSource ? '/background-image.png' : '',
  props,
  animationStateSchema: Number(specIn.animationStateSchema) || 0,
  features: {
    facialRuntime: specIn.features?.facialRuntime !== false,
    persistentActing: specIn.features?.persistentActing !== false,
  }, chars };
fs.writeFileSync(path.join(HERE, '_spec.json'), JSON.stringify(pageSpec));

const OUT = specIn.out; fs.mkdirSync(OUT, { recursive: true });

// static server
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.bin': 'application/octet-stream',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.ktx2': 'image/ktx2', '.json': 'application/json', '.wasm': 'application/wasm' };
const server = http.createServer((req, res) => {
  const requestPath = decodeURIComponent(req.url.split('?')[0]);
  let fp;
  const assetMatch = requestPath.match(/^\/scene-assets\/([^/]+)\/(.+)$/);
  if (assetMatch && sceneAssetRoots.has(assetMatch[1])) {
    const root = sceneAssetRoots.get(assetMatch[1]);
    const relative = assetMatch[2].replace(/\\/g, '/');
    const candidate = path.resolve(root, relative);
    // GLTF child resources must remain inside this exact local source folder.
    if (candidate !== root && !candidate.startsWith(root + path.sep)) {
      res.writeHead(403); res.end(); return;
    }
    fp = candidate;
  } else {
    fp = requestPath === '/background-image.png' && backgroundSource
      ? backgroundSource : path.join(HERE, requestPath);
  }
  if (req.url === '/') fp = path.join(HERE, 'render_scene.html');
  fs.readFile(fp, (e, d) => {
    if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
    res.end(d);
  });
});
await new Promise(r => server.listen(0, r));
const PORT = server.address().port;

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=default', '--enable-webgl',
         '--ignore-gpu-blocklist', '--no-sandbox', '--disable-dev-shm-usage'],
});
const page = await browser.newPage();
page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 200)));
await page.setViewport({ width: VW, height: VH });
await page.goto(`http://localhost:${PORT}/render_scene.html`, { waitUntil: 'load' });
await page.waitForFunction('window.__ready===true || window.__error', { timeout: 60000 });
const err = await page.evaluate(() => window.__error);
if (err) { console.log('SCENE_ERROR:', err); await browser.close(); server.close(); process.exit(1); }
const debug = await page.evaluate(() => window.__debug);
console.log(`SCENE_DEBUG ${JSON.stringify(debug)}`);

const NF = await page.evaluate(() => window.__nframes);
const t0 = Date.now();
for (let f = 0; f < NF; f++) {
  await page.evaluate(fr => window.__poseFrame(fr), f);
  const data = await page.evaluate(() => document.getElementById('c').toDataURL('image/png'));
  fs.writeFileSync(path.join(OUT, `frame_${String(f + 1).padStart(4, '0')}.png`),
    Buffer.from(data.split(',')[1], 'base64'));
}
const dt = (Date.now() - t0) / 1000;
console.log(`SCENE_DONE ${NF} frames in ${dt.toFixed(3)}s = ${(dt / NF * 1000).toFixed(3)}ms/frame`);
const metrics = await page.metrics();
console.log(`SCENE_METRICS js_heap_mb=${(metrics.JSHeapUsedSize / 1048576).toFixed(2)}`);
await browser.close();
server.close();
