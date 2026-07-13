// SBZ AI Video Studio — Electron desktop wrapper (P8)
// Python Flask backend chalata hai + UI window mein load karta hai.
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const PORT = 5050;
let py = null, win = null;

function startBackend() {
  const root = path.join(__dirname, '..');
  const python = path.join(root, '.venv', 'Scripts', 'python.exe');
  py = spawn(python, ['app.py'], {
    cwd: root,
    env: { ...process.env, NO_BROWSER: '1', PYTHONIOENCODING: 'utf-8' },
    windowsHide: true,
  });
  py.stdout.on('data', d => console.log(`[py] ${d}`));
  py.stderr.on('data', d => console.error(`[py] ${d}`));
}

function waitReady(cb, tries = 80) {
  const req = http.get(`http://127.0.0.1:${PORT}/`, () => cb());
  req.on('error', () => {
    if (tries > 0) setTimeout(() => waitReady(cb, tries - 1), 500);
    else cb();
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1440, height: 900, minWidth: 1100, minHeight: 700,
    title: 'SBZ AI Video Studio', backgroundColor: '#0c0f15',
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  win.loadURL(`http://127.0.0.1:${PORT}`);
  win.on('closed', () => { win = null; });
}

app.whenReady().then(() => { startBackend(); waitReady(createWindow); });
app.on('window-all-closed', () => { if (py) try { py.kill(); } catch (e) {} app.quit(); });
app.on('before-quit', () => { if (py) try { py.kill(); } catch (e) {} });
