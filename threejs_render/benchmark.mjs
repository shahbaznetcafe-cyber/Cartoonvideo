import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { pathToFileURL } from 'node:url';


const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, '$1'));

export function parseRenderMetrics(output) {
  const done = String(output).match(/SCENE_DONE\s+(\d+)\s+frames\s+in\s+([\d.]+)s\s+=\s+([\d.]+)ms\/frame/);
  const memory = String(output).match(/SCENE_METRICS\s+js_heap_mb=([\d.]+)/);
  if (!done) throw new Error(`renderer metrics missing: ${String(output).slice(-400)}`);
  return {
    frames: Number(done[1]),
    renderer_seconds: Number(done[2]),
    milliseconds_per_frame: Number(done[3]),
    js_heap_mb: memory ? Number(memory[1]) : null,
  };
}

function state(seed, role, reaction = 'none') {
  return {
    seed, role, reaction, reactionStrength: role === 'listener' ? 0.46 : 0,
    start: {
      position: { x: 0, y: 0, z: 0 },
      pose: { armL: 8, armR: -8, legL: 0, legR: 0,
        bodyX: 0, bodyY: role === 'listener' ? -7 : 0, bodyZ: 0 },
      scaleY: 1,
    },
    end: {
      position: { x: role === 'speaker' ? 0.24 : 0, y: 0, z: 0 },
      pose: { armL: role === 'speaker' ? 38 : 8, armR: role === 'speaker' ? -38 : -8,
        legL: 0, legR: 0, bodyX: role === 'speaker' ? -4 : 0,
        bodyY: role === 'listener' ? -7 : 0, bodyZ: 0 },
      scaleY: 1,
    },
  };
}

export function buildBenchmarkSpec({ out, openness, characters, environment, enhanced }) {
  const first = characters[0];
  const second = characters[1] || characters[0];
  return {
    out, flimit: 0, fps: 24, res: '960x540', env: environment || '',
    shot: 'wide', focus: 0, exposure: -0.2, sceneLook: 'sunny',
    timeOffset: enhanced ? 3.25 : 0, animationStateSchema: enhanced ? 1 : 0,
    features: { facialRuntime: enhanced, persistentActing: enhanced },
    chars: [
      { id: 'speaker', blend: first, openness, emotion: 'happy', speaking: true,
        slot: 0, action: 'walk', target: 1,
        acting: enhanced ? state(1804289383, 'speaker') : {} },
      { id: 'listener', blend: second, openness: '', emotion: 'neutral', speaking: false,
        slot: 1, action: 'none', target: 0,
        acting: enhanced ? state(846930886, 'listener', 'encourage') : {} },
    ],
  };
}

function runRenderer(label, spec, directory) {
  const specPath = path.join(directory, `${label}.json`);
  fs.writeFileSync(specPath, JSON.stringify(spec));
  const started = performance.now();
  const run = spawnSync(process.execPath, ['render_scene.js', specPath], {
    cwd: HERE, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
  });
  const wallSeconds = (performance.now() - started) / 1000;
  const output = `${run.stdout || ''}${run.stderr || ''}`;
  if (run.status !== 0) throw new Error(`${label} renderer failed:\n${output}`);
  return { ...parseRenderMetrics(output), wall_seconds: Number(wallSeconds.toFixed(3)) };
}

export function runBenchmark() {
  const charDir = path.join(HERE, 'assets', 'chars');
  const envDir = path.join(HERE, 'assets', 'env');
  const characters = fs.readdirSync(charDir).filter(name => name.toLowerCase().endsWith('.glb')).sort();
  if (!characters.length) throw new Error('benchmark requires at least one local GLB in assets/chars');
  const environments = fs.existsSync(envDir)
    ? fs.readdirSync(envDir).filter(name => name.toLowerCase().endsWith('.glb')).sort() : [];
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'sbz-phase5-'));
  try {
    const frameCount = 240;
    const opennessPath = path.join(directory, 'openness.json');
    const values = Array.from({ length: frameCount }, (_, frame) =>
      frame % 48 < 5 ? 0 : Number((0.24 + 0.58 * Math.abs(Math.sin(frame * 0.31))).toFixed(4)));
    fs.writeFileSync(opennessPath, JSON.stringify({ fps: 24, n: frameCount, values }));
    const environment = environments.length ? path.join(envDir, environments[0]) : '';
    const common = { openness: opennessPath,
      characters: characters.slice(0, 2).map(name => path.join(charDir, name)), environment };
    const baseline = runRenderer('baseline', buildBenchmarkSpec({
      ...common, out: path.join(directory, 'baseline_frames'), enhanced: false,
    }), directory);
    const enhanced = runRenderer('enhanced', buildBenchmarkSpec({
      ...common, out: path.join(directory, 'enhanced_frames'), enhanced: true,
    }), directory);
    return {
      schema_version: 1,
      benchmark: 'phase5_same_10_second_scene',
      scene: { duration_seconds: 10, fps: 24, resolution: '960x540',
        frames: frameCount, characters: Math.min(2, characters.length) },
      baseline,
      enhanced,
      comparison: {
        milliseconds_per_frame_delta: Number((enhanced.milliseconds_per_frame - baseline.milliseconds_per_frame).toFixed(3)),
        overhead_percent: Number((((enhanced.milliseconds_per_frame / baseline.milliseconds_per_frame) - 1) * 100).toFixed(2)),
        renderer_seconds_delta: Number((enhanced.renderer_seconds - baseline.renderer_seconds).toFixed(3)),
        wall_seconds_delta: Number((enhanced.wall_seconds - baseline.wall_seconds).toFixed(3)),
        js_heap_mb_delta: enhanced.js_heap_mb == null || baseline.js_heap_mb == null
          ? null : Number((enhanced.js_heap_mb - baseline.js_heap_mb).toFixed(2)),
      },
    };
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(JSON.stringify(runBenchmark(), null, 2));
}
