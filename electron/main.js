// SBZ AI Video Studio — Electron desktop wrapper.
// Own exactly one Flask process tree and reuse a healthy existing backend.
const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const PORT = 5050;
const HEALTH_URL = `http://127.0.0.1:${PORT}/api/health`;
let py = null;
let win = null;
let backendOwned = false;
let quitting = false;

function checkBackend(callback) {
  const req = http.get(HEALTH_URL, { timeout: 1500 }, response => {
    let raw = '';
    response.setEncoding('utf8');
    response.on('data', chunk => { raw += chunk; });
    response.on('end', () => {
      try {
        const data = JSON.parse(raw);
        callback(response.statusCode === 200 && data.app === 'sbz-ai-video-studio', data);
      } catch (_) {
        callback(false, null);
      }
    });
  });
  req.on('timeout', () => req.destroy());
  req.on('error', () => callback(false, null));
}

function waitReady(callback, tries = 80) {
  checkBackend(ok => {
    if (ok) return callback();
    if (tries > 0) return setTimeout(() => waitReady(callback, tries - 1), 500);
    dialog.showErrorBox(
      'SBZ Studio could not start',
      'The local video engine did not become ready. Close duplicate SBZ/Python processes and try again.'
    );
    app.quit();
  });
}

function startBackend(callback) {
  checkBackend(ok => {
    if (ok) {
      backendOwned = false;
      return callback();
    }
    const root = path.join(__dirname, '..');
    const python = path.join(root, '.venv', 'Scripts', 'python.exe');
    backendOwned = true;
    py = spawn(python, ['-u', 'app.py'], {
      cwd: root,
      env: { ...process.env, NO_BROWSER: '1', PYTHONIOENCODING: 'utf-8' },
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    py.stdout.on('data', data => console.log(`[py] ${data}`));
    py.stderr.on('data', data => console.error(`[py] ${data}`));
    py.on('error', error => console.error('[py start error]', error));
    waitReady(callback);
  });
}

function stopBackend() {
  if (!backendOwned || !py || !py.pid) return;
  try {
    if (process.platform === 'win32') {
      // The venv launcher can create a child Python process. Kill the owned tree,
      // otherwise an orphan Flask server survives and competes on port 5050.
      spawn('taskkill', ['/pid', String(py.pid), '/T', '/F'], {
        windowsHide: true,
        stdio: 'ignore',
      });
    } else {
      py.kill('SIGTERM');
    }
  } catch (_) {}
  py = null;
}

function createWindow() {
  if (win) return;
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    title: 'SBZ AI Video Studio',
    backgroundColor: '#0c0f15',
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  win.loadURL(`http://127.0.0.1:${PORT}`);
  win.on('closed', () => { win = null; });
}

const singleInstance = app.requestSingleInstanceLock();
if (!singleInstance) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!win) return;
    if (win.isMinimized()) win.restore();
    win.focus();
  });
  app.whenReady().then(() => startBackend(createWindow));
}

app.on('window-all-closed', () => {
  quitting = true;
  stopBackend();
  app.quit();
});
app.on('before-quit', () => {
  if (quitting) return;
  quitting = true;
  stopBackend();
});
