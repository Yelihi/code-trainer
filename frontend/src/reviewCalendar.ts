export function reviewWeek(dates: string[], now = new Date()) {
  const first = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Array.from({ length: 7 }, (_, index) => {
    const start = new Date(first), end = new Date(first);
    start.setDate(first.getDate() + index); end.setDate(first.getDate() + index + 1);
    return { date: start, count: dates.filter(value => { const at = new Date(value); return at >= start && at < end; }).length };
  });
}
