import test from 'node:test';
import assert from 'node:assert/strict';

import {
  gestureEnvelope,
  listenerReaction,
  sampleActingState,
} from '../acting_state_runtime.js';


const acting = {
  start: {
    position: { x: 0.1, y: 0, z: 0 },
    pose: { armL: 8, armR: -8, legL: 0, legR: 0, bodyX: 0, bodyY: -7, bodyZ: 0 },
    scaleY: 1,
  },
  end: {
    position: { x: 0.5, y: 0, z: 0 },
    pose: { armL: 38, armR: -38, legL: 0, legR: 0, bodyX: -4, bodyY: 0, bodyZ: 0 },
    scaleY: 0.96,
  },
};


test('acting state interpolation preserves exact cut endpoints', () => {
  const start = sampleActingState(acting, 0);
  const end = sampleActingState(acting, 1);
  assert.deepEqual(start, acting.start);
  assert.deepEqual(end, acting.end);
  assert.ok(Math.abs(sampleActingState(acting, 0.5).position.x - 0.3) < 1e-12);
});

test('gestures ease fully in and out instead of snapping at cuts', () => {
  assert.equal(gestureEnvelope(0), 0);
  assert.equal(gestureEnvelope(1), 0);
  assert.ok(gestureEnvelope(0.5) > 0.99);
  assert.ok(gestureEnvelope(0.08) > 0 && gestureEnvelope(0.08) < 1);
  assert.ok(gestureEnvelope(0.9) > 0 && gestureEnvelope(0.9) < 1);
});

test('listener reactions are visible inside the line and neutral at both edges', () => {
  for (const reaction of ['attend', 'encourage', 'concern', 'surprise']) {
    const start = listenerReaction(reaction, 0, 10, 0.5);
    const middle = listenerReaction(reaction, 0.5, 10, 0.5);
    const end = listenerReaction(reaction, 1, 10, 0.5);
    assert.ok(Object.values(start).every(value => value === 0));
    assert.ok(Object.values(end).every(value => value === 0));
    assert.ok(Object.values(middle).some(value => value !== 0));
  }
});

test('sampling does not mutate the reproducibility payload', () => {
  const before = JSON.stringify(acting);
  sampleActingState(acting, 0.37);
  assert.equal(JSON.stringify(acting), before);
});
