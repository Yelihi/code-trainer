import assert from 'node:assert/strict';
import test from 'node:test';
import { buildTrace, visualKinds, type VisualNode } from './foundationTrace.ts';

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
  assert.match(buildTrace('dfs').at(-1)!.detail, /A → B → D → F → C → E/);
  assert.deepEqual(values, [5, 2, 7, 1]);
});


test('linked-list operations preserve node identity while relinking and expose both reference directions', () => {
  for (const doubly of [false, true]) {
    const frames = buildTrace('linked-list', undefined, undefined, { doubly });
    const first = frames[0], last = frames.at(-1)!;
    const byId = new Map(last.nodes.map(n => [n.id, n]));
    const order: string[] = [];
    let id: string | null | undefined = last.head;
    while (id) {
      assert.ok(!order.includes(id), 'no unintended cycle');
      const node: VisualNode = byId.get(id)!;
      assert.ok(node, 'every reference resolves');
      if (doubly) assert.equal(node.prev, order.at(-1) ?? null);
      else assert.equal(node.prev, undefined);
      order.push(id); id = node.next;
    }
    assert.deepEqual(order, ['D', 'A', 'B', 'X']);
    assert.deepEqual(last.shelves![0].values, ['40', '10', '20', '25']);
    for (const original of first.nodes.filter(n => n.id !== 'C')) {
      const final = byId.get(original.id)!;
      assert.deepEqual([final.label, final.x, final.y], [original.label, original.x, original.y]);
    }
    assert.equal(first.nodes.find(n => n.id === 'B')!.next, 'C', 'snapshots must not mutate');
    for (const frame of frames) for (const node of frame.nodes) {
      if (node.next) assert.ok(frame.nodes.some(n => n.id === node.next));
      if (node.prev) assert.ok(frame.nodes.some(n => n.id === node.prev));
    }
  }
});

test('graph traces handle cycles, shared neighbors and an isolated start without duplicate visits', () => {
  for (const kind of ['bfs', 'dfs']) for (const start of ['A', 'B', 'C', 'D', 'E', 'F', 'G']) {
    const frames = buildTrace(kind, [], 7, { start });
    const order = frames.at(-1)!.shelves![1].values;
    assert.equal(order[0], start);
    assert.equal(new Set(order).size, order.length);
    assert.equal(order.length, start === 'G' ? 1 : start === 'A' ? 6 : ['B', 'D'].includes(start) ? 5 : 3);
    assert.deepEqual(frames.at(-1)!.shelves![0].values, []);
    assert.ok(frames.every(f => !f.focus || f.edges.some(e => e[0] === f.focus![0] && e[1] === f.focus![1])));
    for (const f of frames) assert.equal(new Set(f.shelves![0].values).size, f.shelves![0].values.length);
  }
  assert.deepEqual(buildTrace('bfs').at(-1)!.shelves![1].values, ['A', 'B', 'C', 'D', 'E', 'F']);
  assert.deepEqual(buildTrace('dfs').at(-1)!.shelves![1].values, ['A', 'B', 'D', 'F', 'C', 'E']);
});

test('queue uses stable slots, merges preserve equal-value identity, and callbacks expose the original index', () => {
  const queue = buildTrace('queue', [5, 2, 7]);
  assert.equal(queue.find(f => f.note === 'dequeue() → 5')!.nodes[0].x, 103);
  const sorted = buildTrace('merge-sort', [2, 2, 1]).at(-1)!;
  assert.deepEqual(sorted.nodes.map(n => n.id), ['v2', 'v0', 'v1']);
  const filter = buildTrace('filter', [1, 2, 4]).filter(f => f.code);
  assert.deepEqual(filter.map(f => f.code), ['fn(1, 0) → false', 'fn(2, 1) → true', 'fn(4, 2) → true']);
  assert.equal(buildTrace('reduce', []).at(-1)!.nodes.find(n => n.id === 'acc')!.label, '10');
});
