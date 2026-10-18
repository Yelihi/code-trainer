import assert from 'node:assert/strict';
import test from 'node:test';
import { buildTrace, visualKinds } from './foundationTrace.ts';

test('all lesson visualizations have valid stable nodes, edges and explanations', () => {
  for (const kind of visualKinds) for (const input of [[], [0], [5, 2, 7, 1], [2, 2, -1, 0, 9, 8, 7, 6]]) {
    const frames = buildTrace(kind, input);
    assert.ok(frames.length > 0, kind);
    for (const frame of frames) {
      const ids = frame.nodes.map(n => n.id);
      assert.equal(new Set(ids).size, ids.length, kind);
      assert.ok(frame.note);
      assert.ok(frame.nodes.every(n => n.x >= 0 && n.x <= 588 && n.y >= 0 && n.y <= 310), kind);
      assert.ok(frame.edges.every(([a, b]) => ids.includes(a) && ids.includes(b)), kind);
    }
  }
});

test('animations show the actual ordering, duplicate search, merge and accumulator semantics', () => {
  const values = [5, 2, 7, 1];
  const stack = buildTrace('stack', values).filter(f => f.note.startsWith('pop()'));
  const queue = buildTrace('queue', values).filter(f => f.note.startsWith('dequeue()'));
  assert.deepEqual(stack.map(f => Number(f.note.split('→ ')[1])), [1, 7, 2, 5]);
  assert.deepEqual(queue.map(f => Number(f.note.split('→ ')[1])), values);
  assert.match(buildTrace('priority-queue', values).at(-1)!.note, /1 → 2 → 5 → 7/);
  assert.match(buildTrace('binary-search', [3, 1, 3], 3).at(-1)!.note, /→ 1/);
  assert.match(buildTrace('binary-search', [], 3).at(-1)!.note, /-1/);
  assert.deepEqual(buildTrace('merge-sort', [2, 2, -1, 0]).at(-1)!.nodes.map(n => Number(n.label)), [-1, 0, 2, 2]);
  assert.equal(buildTrace('reduce', values).at(-1)!.nodes.find(n => n.id === 'acc')!.label, '25');
  assert.match(buildTrace('bfs').at(-1)!.detail, /A → B → C → D/);
  assert.match(buildTrace('dfs').at(-1)!.detail, /A → B → D → C/);
  assert.deepEqual(values, [5, 2, 7, 1]);
});
