import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reviewCurve } from './reviewCurve.ts';

test('review curves place the scheduled point on a fourteen day axis and decay more slowly for longer intervals', () => {
  const now = new Date('2026-10-27T00:00:00Z');
  const tomorrow = reviewCurve('2026-10-28T00:00:00Z', 0, now);
  const nextWeek = reviewCurve('2026-11-03T00:00:00Z', 2, now);
  assert.equal(tomorrow.dueX, 40);
  assert.equal(nextWeek.dueX, 280);
  assert.ok(tomorrow.dueY > 30 && tomorrow.dueY < 35);
  assert.ok(nextWeek.dueY > 30 && nextWeek.dueY < 35);
  assert.ok(Number(tomorrow.path.match(/L40 ([\d.]+)/)?.[1]) > Number(nextWeek.path.match(/L40 ([\d.]+)/)?.[1]));
  assert.equal(reviewCurve('2026-10-26T00:00:00Z', 0, now).dueX, 0);
  assert.equal(reviewCurve('2026-11-20T00:00:00Z', 3, now).dueX, 560);
});
