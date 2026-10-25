import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reviewWeek } from './reviewCalendar.ts';

test('review week groups local dates including midnight and month boundary, not elapsed24h buckets', () => {
  const now = new Date(2026, 9, 29, 18), end = new Date(2026, 10, 5);
  const rows = reviewWeek([new Date(2026, 9, 29, 0).toISOString(), new Date(2026, 9, 29, 23, 59).toISOString(), new Date(2026, 9, 30).toISOString(), new Date(2026, 10, 4, 23).toISOString(), end.toISOString(), new Date(2026, 9, 28).toISOString()], now);
  assert.deepEqual(rows.map(x => x.count), [2,1,0,0,0,0,1]);
  assert.equal(rows[6].date.getDate(),4);
});
