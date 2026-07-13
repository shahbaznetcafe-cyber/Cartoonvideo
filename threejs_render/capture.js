// Headless Chrome (Puppeteer) se Three.js frames capture + speed measure.
// Run: node capture.js [frames] [wide|closeup]
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import http from 'http';
import path from 'path';

// chhota static server (file:// CORS se bachne ke liye — ES modules http se load hon)
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary',
  '.wasm': 'application/wasm', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  let fp = path.join(process.cwd(), decodeURIComponent(req.url.split('?')[0]));
  if (req.url === '/') fp = path.join(process.cwd(), 'render.html');
  fs.readFile(fp, (e, data) => {
    if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
    res.end(data);
  });
});
await new Promise(r => server.listen(0, r));
const PORT = server.address().port;

const CHROME = fs.existsSync('C:/Program Files/Google/Chrome/Application/chrome.exe')
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe';

const N = parseInt(process.argv[2] || '120');
const SHOT = process.argv[3] || 'wide';
const OUT = './frames_' + SHOT;
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=default', '--enable-webgl',
         '--ignore-gpu-blocklist', '--no-sandbox', '--disable-dev-shm-usage'],
});
const page = await browser.newPage();
page.on('console', m => console.log('  [page]', m.text()));
page.on('pageerror', e => console.log('  [pageerror]', String(e).slice(0, 200)));
await page.setViewport({ width: 960, height: 540 });
await page.goto(`http://localhost:${PORT}/render.html`, { waitUntil: 'load' });
await page.waitForFunction('window.__ready===true || window.__error', { timeout: 40000 });
const err = await page.evaluate(() => window.__error);
if (err) { console.log('LOAD ERROR:', err); await browser.close(); process.exit(1); }

const fps = 24, t0 = Date.now();
for (let f = 0; f < N; f++) {
  const t = f / fps;
  const op = Math.abs(Math.sin(t * 6)) * 0.9;          // synthetic "talking"
  await page.evaluate((op, t, shot) => window.__pose(op, t, shot), op, t, SHOT);
  const data = await page.evaluate(() => document.getElementById('c').toDataURL('image/png'));
  fs.writeFileSync(`${OUT}/frame_${String(f).padStart(4, '0')}.png`,
    Buffer.from(data.split(',')[1], 'base64'));
}
const dt = (Date.now() - t0) / 1000;
console.log(`RENDERED ${N} frames [${SHOT}] in ${dt.toFixed(1)}s = ${(dt / N * 1000).toFixed(0)}ms/frame (${(N / dt).toFixed(1)} fps)`);
await browser.close();
server.close();
