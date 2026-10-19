import test from 'node:test';
import assert from 'node:assert/strict';
import { layoutGraph, neighbors, zoomView, type GraphNode, type GraphEdge } from './knowledgeGraph.ts';

const nodes: GraphNode[] = ['a', 'b', 'c', 'isolated'].map(id => ({ id, kind: 'concept', label: id, scope: 'typescript', descriptions: [], exercise_ids: [] }));
const edges: GraphEdge[] = [['a', 'b'], ['b', 'c'], ['c', 'a']].map(([source, target]) => ({ id: source + target, source, target, kind: 'evidence', label: '학습 근거', description: '', exercise_ids: [] }));

test('graph layout keeps cyclic and disconnected nodes visible and stable across input order', () => {
  const first = layoutGraph(nodes, edges), second = layoutGraph([...nodes].reverse(), edges);
  assert.deepEqual(first, second);
  assert.equal(first.positions.size, nodes.length);
  for (const point of first.positions.values()) {
    assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y));
    assert.ok(point.x > first.bounds.x && point.x < first.bounds.x + first.bounds.width);
    assert.ok(point.y > first.bounds.y && point.y < first.bounds.y + first.bounds.height);
  }
  assert.equal(new Set([...first.positions.values()].map(p => `${p.x},${p.y}`)).size, nodes.length);
  assert.ok(layoutGraph([], []).bounds.width > 0);
});

test('hover includes incoming and outgoing neighbors, but not disconnected nodes', () => {
  assert.deepEqual(neighbors('b', edges), new Set(['b', 'a', 'c']));
  assert.deepEqual(neighbors('isolated', edges), new Set(['isolated']));
});

test('zoom preserves the cursor anchor and aspect ratio while limiting extreme zoom', () => {
  const base = { x: 0, y: 0, width: 1000, height: 500 }, anchor = { x: 250, y: 100 };
  const zoomed = zoomView(base, .5, anchor, base);
  assert.equal((anchor.x - zoomed.x) / zoomed.width, .25);
  assert.equal((anchor.y - zoomed.y) / zoomed.height, .2);
  assert.equal(zoomed.width / zoomed.height, 2);
  assert.equal(zoomView(base, .001, anchor, base).width, 200);
  assert.equal(zoomView(base, 1000, anchor, base).width, 2000);
});
