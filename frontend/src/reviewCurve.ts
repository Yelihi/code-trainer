const day = 24 * 60 * 60 * 1000;
const width = 560;
const intervals = [1, 3, 7, 14];

export function reviewCurve(dueAt: string, streak: number, now = new Date()) {
  const due = Date.parse(dueAt);
  const interval = (intervals[Math.max(0, Math.min(3, streak))] ?? 1) * day;
  const xAtDue = Number.isFinite(due) ? Math.max(0, Math.min(width, (due - now.getTime()) / (14 * day) * width)) : 0;
  const yAt = (x: number) => {
    if (!Number.isFinite(due)) return 45;
    const elapsed = Math.max(0, (now.getTime() + x / width * 14 * day - (due - interval)) / interval);
    return 7 + 38 * (1 - Math.exp(-1.1 * elapsed));
  };
  return {
    path: Array.from({ length: 57 }, (_, index) => `${index ? 'L' : 'M'}${index * 10} ${yAt(index * 10).toFixed(1)}`).join(' '),
    dueX: xAtDue,
    dueY: yAt(xAtDue),
  };
}
