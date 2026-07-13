import test from 'node:test';
import assert from 'node:assert/strict';

import { buildBenchmarkSpec, parseRenderMetrics } from '../benchmark.mjs';


test('benchmark parser captures frame, timing, and heap metrics', () => {
  const metrics = parseRenderMetrics(
    'SCENE_DONE 240 frames in 22.8s = 95ms/frame\nSCENE_METRICS js_heap_mb=18.42');
  assert.deepEqual(metrics, { frames: 240, renderer_seconds: 22.8,
    milliseconds_per_frame: 95, js_heap_mb: 18.42 });
});

test('baseline and enhanced benchmark specs use the exact same scene contract', () => {
  const common = { out: 'frames', openness: 'open.json',
    characters: ['a.glb', 'b.glb'], environment: 'garden.glb' };
  const baseline = buildBenchmarkSpec({ ...common, enhanced: false });
  const enhanced = buildBenchmarkSpec({ ...common, enhanced: true });
  assert.equal(baseline.fps, enhanced.fps);
  assert.equal(baseline.res, enhanced.res);
  assert.equal(baseline.chars.length, enhanced.chars.length);
  assert.deepEqual(baseline.chars.map(char => char.blend), enhanced.chars.map(char => char.blend));
  assert.equal(baseline.features.facialRuntime, false);
  assert.equal(enhanced.features.facialRuntime, true);
  assert.equal(enhanced.features.persistentActing, true);
});
