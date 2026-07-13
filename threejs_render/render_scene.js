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

// blend->glb, openness json->values, env->url
const chars = specIn.chars.map(c => {
  let op = [0];
  if (c.speaking && c.openness && fs.existsSync(c.openness)) {
    try { op = JSON.parse(fs.readFileSync(c.openness, 'utf-8')).values || [0]; } catch (e) {}
  }
  return { glb: `./assets/chars/${slug(c.blend)}.glb`, slot: c.slot, speaking: !!c.speaking,
           openness: op, emotion: c.emotion || 'neutral',
           costume: c.costume || '', accessory: c.accessory || '', held: c.held || '',
           action: c.action || 'none', target: (c.target == null ? -1 : c.target) };
});
const env = specIn.env ? `./assets/env/${path.basename(specIn.env)}` : '';
const pageSpec = { res: [VW, VH], fps, env, exposure: specIn.exposure || -0.2,
  shot: specIn.shot || 'wide', focus: specIn.focus || 0,
  sceneLook: specIn.sceneLook || 'sunny', chars };
fs.writeFileSync(path.join(HERE, '_spec.json'), JSON.stringify(pageSpec));

const OUT = specIn.out; fs.mkdirSync(OUT, { recursive: true });

// static server
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary',
  '.json': 'application/json', '.wasm': 'application/wasm' };
const server = http.createServer((req, res) => {
  let fp = path.join(HERE, decodeURIComponent(req.url.split('?')[0]));
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

const NF = await page.evaluate(() => window.__nframes);
const t0 = Date.now();
for (let f = 0; f < NF; f++) {
  await page.evaluate(fr => window.__poseFrame(fr), f);
  const data = await page.evaluate(() => document.getElementById('c').toDataURL('image/png'));
  fs.writeFileSync(path.join(OUT, `frame_${String(f + 1).padStart(4, '0')}.png`),
    Buffer.from(data.split(',')[1], 'base64'));
}
const dt = (Date.now() - t0) / 1000;
console.log(`SCENE_DONE ${NF} frames in ${dt.toFixed(1)}s = ${(dt / NF * 1000).toFixed(0)}ms/frame`);
await browser.close();
server.close();
