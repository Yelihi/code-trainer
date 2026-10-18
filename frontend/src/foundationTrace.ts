import { graphTrace, linkedListTrace } from './foundationStructures.ts';
export type VisualNode = { id: string; label: string; x: number; y: number; active?: boolean; muted?: boolean; next?: string | null; prev?: string | null; annotation?: string; state?: string };
export type Frame = { nodes: VisualNode[]; edges: [string, string][]; note: string; detail: string; code?: string; focus?: [string, string]; head?: string; shelves?: { label: string; values: string[] }[] };
export const visualKinds = ['stack', 'queue', 'linked-list', 'dictionary', 'priority-queue', 'binary-search', 'merge-sort', 'bfs', 'dfs', 'map', 'filter', 'reduce'];

export function buildTrace(kind: string, values = [5, 2, 7, 1], target = 7, options: { doubly?: boolean; start?: string } = {}): Frame[] {
  if (kind === 'linked-list') return linkedListTrace(options.doubly ?? false);
  if (kind === 'bfs' || kind === 'dfs') return graphTrace(kind, options.start ?? 'A');
  const frames: Frame[] = [];
  const add = (nodes: VisualNode[], note: string, detail = '', edges: [string, string][] = []) => frames.push({ nodes: nodes.map(n => ({ ...n })), note, detail, edges: [...edges] });
  const row = (a: { id: string; value: number }[], y = 115, active = '') => a.map((v, i) => ({ id: v.id, label: String(v.value), x: 30 + i * 73, y, active: v.id === active }));
  const input = values.map((value, i) => ({ id: `v${i}`, value }));
  if (['stack', 'queue'].includes(kind)) {
    const state: typeof input = [];
    const drawStructure = (note: string, active = '') => {
      const nodes = row(state, 140, active);
      if (kind === 'stack') nodes.forEach((n, i) => { n.x = 280; n.y = 285 - i * 34; });
      if (kind === 'queue') nodes.forEach(n => { n.x = 30 + Number(n.id.slice(1)) * 73; });
      add(nodes, note, kind === 'stack' ? '실행 취소: 마지막 작업부터 되돌립니다. peek는 제거 없이 맨 위를 봅니다.' : '작업 대기열: 앞 원소를 옮기지 않고 head 인덱스를 이동합니다. 모두 비우면 저장 공간을 초기화합니다.');
      frames.at(-1)!.code = kind === 'stack' ? `size = ${state.length}` : `head = ${state.length ? state[0].id.slice(1) : 0}; size = ${state.length}`;
    };
    drawStructure('빈 구조에서 시작합니다.');
    for (const v of input) {
      state.push(v);
      drawStructure(`${kind === 'queue' ? 'enqueue' : 'push'}(${v.value})`, v.id);
    }
    if (state.length) drawStructure(`peek() → ${kind === 'stack' ? state.at(-1)!.value : state[0].value} · 조회해도 크기는 그대로입니다.`, kind === 'stack' ? state.at(-1)!.id : state[0].id);
    while (state.length) {
      const v = kind === 'stack' ? state.pop()! : state.shift()!;
      drawStructure(`${kind === 'queue' ? 'dequeue' : 'pop'}() → ${v.value}`);
    }
    drawStructure('비어 있습니다. 다시 꺼내면 undefined를 반환합니다.');
  } else if (kind === 'priority-queue') {
    const heap: typeof input = [];
    const drawHeap = (note: string, active = '') => {
      const nodes = heap.map((v, i) => {
        const depth = Math.floor(Math.log2(i + 1)), first = 2 ** depth - 1;
        return { id: v.id, label: String(v.value), x: (i - first + .5) * (640 / 2 ** depth) - 25, y: 25 + depth * 78, active: v.id === active };
      });
      add(nodes, note, '부모 ≤ 자식 · 배열 인덱스의 자식: 2i+1, 2i+2', nodes.slice(1).map((n, i) => [nodes[Math.floor(i / 2)].id, n.id]));
    };
    drawHeap('빈 최소 힙에서 시작합니다.');
    for (const v of input) {
      heap.push(v); let i = heap.length - 1; drawHeap(`${v.value}를 마지막 위치에 추가합니다.`, v.id);
      while (i > 0) {
        const p = Math.floor((i - 1) / 2);
        drawHeap(`부모 ${heap[p].value}와 새 값 ${heap[i].value}를 비교합니다.`, v.id);
        frames.at(-1)!.code = `parent[${p}] <= child[${i}] → ${heap[p].value <= heap[i].value}`;
        if (heap[p].value <= heap[i].value) break;
        [heap[p], heap[i]] = [heap[i], heap[p]]; i = p; drawHeap('부모보다 작으므로 위로 교환합니다.', v.id);
      }
    }
    if (heap.length) drawHeap(`peek() → ${heap[0].value} · 루트만 최소이며 형제끼리는 정렬되지 않아도 됩니다.`, heap[0].id);
    const removed: number[] = [];
    while (heap.length) {
      const min = heap[0]; removed.push(min.value); const last = heap.pop()!;
      if (heap.length) heap[0] = last;
      drawHeap(`pop() → ${min.value}. 마지막 원소로 루트를 채웁니다.`, last.id);
      let i = 0;
      while (heap.length) {
        let s = i; const l = i * 2 + 1, r = l + 1;
        if (l < heap.length && heap[l].value < heap[s].value) s = l;
        if (r < heap.length && heap[r].value < heap[s].value) s = r;
        drawHeap('부모·왼쪽·오른쪽 중 가장 작은 값을 찾습니다.', heap[s].id);
        frames.at(-1)!.code = `parent=${heap[i].value}; left=${heap[l]?.value ?? '없음'}; right=${heap[r]?.value ?? '없음'}`;
        if (s === i) break;
        [heap[i], heap[s]] = [heap[s], heap[i]]; i = s; drawHeap('더 작은 자식과 교환해 힙 규칙을 복구합니다.', last.id);
      }
    }
    drawHeap(`꺼낸 순서: ${removed.join(' → ')}`);
  } else if (kind === 'dictionary') {
    const buckets: { id: string; label: string }[][] = Array.from({ length: 8 }, () => []);
    const drawBuckets = (note: string, active = '') => {
      const nodes: VisualNode[] = buckets.map((_, i) => ({ id: `bucket${i}`, label: `#${i}`, x: 20 + i * 77, y: 40, muted: active !== `bucket${i}`, active: active === `bucket${i}` }));
      const edges: [string, string][] = [];
      buckets.forEach((bucket, i) => bucket.forEach((entry, j) => {
        nodes.push({ ...entry, x: 20 + i * 77, y: 100 + j * 65, active: entry.id === active });
        edges.push([j ? bucket[j - 1].id : `bucket${i}`, entry.id]);
      }));
      add(nodes, note, 'hash = 문자 코드 합 % 8 · 같은 버킷에서도 원래 키를 비교합니다.', edges);
    };
    drawBuckets('8개 버킷을 준비합니다.');
    for (const [key, value] of [['a', 1], ['i', 2], ['a', 3]] as const) {
      drawBuckets(`문자 '${key}'를 해시해 버킷을 선택합니다.`, `bucket${key.charCodeAt(0) % 8}`);
      frames.at(-1)!.code = `hash('${key}') = ${key.charCodeAt(0)} % 8 = ${key.charCodeAt(0) % 8}`;
      const bucket = buckets[key.charCodeAt(0) % 8]; const old = bucket.find(n => n.id === key);
      if (old) old.label = `${key}: ${value}`; else bucket.push({ id: key, label: `${key}: ${value}` });
      drawBuckets(`set('${key}', ${value}) · ${old ? '같은 키의 값만 갱신합니다.' : bucket.length > 1 ? '충돌: 같은 버킷에 별도 키로 보관합니다.' : '키와 값을 저장합니다.'}`, key);
    }
    drawBuckets("get('i'): 같은 버킷의 a는 다른 키라 건너뜁니다.", 'a');
    drawBuckets("get('i') → 2 · a와 다른 키임을 확인합니다.", 'i');
    buckets[1].shift(); drawBuckets("delete('a') → true · 같은 버킷의 i는 남습니다.", 'i');
  } else if (kind === 'binary-search') {
    const sorted = [...input].sort((a, b) => a.value - b.value);
    let l = 0, r = sorted.length - 1, found = -1;
    add(row(sorted), '먼저 오름차순 배열을 준비합니다.', `찾을 값: ${target}`);
    while (l <= r) {
      const mid = Math.floor((l + r) / 2);
      const nodes = row(sorted, 140, sorted[mid].id).map((n, i) => ({ ...n, muted: i < l || i > r, annotation: [i === l ? 'L' : '', i === mid ? 'M' : '', i === r ? 'R' : ''].filter(Boolean).join(' · ') || `[${i}]` }));
      add(nodes, `중간 값 ${sorted[mid].value}와 ${target}을 비교합니다.`, `left=${l} · mid=${mid} · right=${r}`);
      if (sorted[mid].value >= target) { if (sorted[mid].value === target) found = mid; r = mid - 1; }
      else l = mid + 1;
      add(row(sorted, 140).map((n, i) => ({ ...n, muted: i < l || i > r })), `다음 탐색 범위: [${l}, ${r}]`, found < 0 ? '비교 결과로 불가능한 절반을 제외합니다.' : `일치 위치 ${found}를 보관하고 더 왼쪽의 중복값을 확인합니다.`);
    }
    add(row(sorted, 140, sorted[found]?.id), found < 0 ? '찾는 값이 없습니다. → -1' : `첫 일치 인덱스 → ${found}`, '정렬된 배열의 인덱스 기준입니다.');
  } else if (kind === 'merge-sort') {
    const current = [...input];
    add(row(current), '배열을 작은 구간으로 나눕니다.');
    const sort = (left: number, right: number) => {
      if (right - left < 2) return;
      const mid = Math.floor((left + right) / 2);
      add(row(current).map((n, i) => ({ ...n, active: i >= left && i < right, y: i >= mid && i < right ? 200 : 100 })), `[${left}, ${right})를 ${mid}에서 나눕니다.`);
      sort(left, mid); sort(mid, right);
      const a = current.slice(left, mid), b = current.slice(mid, right), merged: typeof input = [];
      while (a.length || b.length) {
        const chosen = !b.length || (a.length && a[0].value <= b[0].value) ? a.shift()! : b.shift()!;
        merged.push(chosen);
        add([...row(a, 60), ...row(b, 150), ...row(merged, 250, chosen.id)], `${chosen.value}를 결과에 붙입니다.`, '위: 왼쪽 구간 · 가운데: 오른쪽 구간 · 아래: 병합 결과. 같은 값이면 왼쪽을 먼저 선택합니다.');
      }
      current.splice(left, right - left, ...merged, ...a, ...b);
      add(row(current).map((n, i) => ({ ...n, active: i >= left && i < right })), `[${left}, ${right})를 작은 값부터 병합했습니다.`, '한쪽이 비면 다른 쪽의 나머지를 모두 붙입니다.');
    };
    sort(0, current.length); add(row(current), '모든 구간의 병합이 끝났습니다.');
  } else if (['map', 'filter', 'reduce'].includes(kind)) {
    const output: typeof input = []; let acc = 10;
    const operation = kind === 'map' ? 'value × 2' : kind === 'filter' ? 'value % 2 === 0' : 'acc + value · 초기값 10';
    const drawMethod = (note: string, active = '') => add([...row(input, 70, active), ...row(output, 220), ...(kind === 'reduce' ? [{ id: 'acc', label: String(acc), x: 280, y: 220, active: true }] : [])], note, `위: 입력 · 아래: ${kind === 'reduce' ? '누적값' : '결과'} · ${operation}`);
    drawMethod('입력을 왼쪽부터 순회합니다.');
    for (const [index, v] of input.entries()) {
      const before = acc;
      if (kind === 'map') output.push({ id: `out-${v.id}`, value: v.value * 2 });
      if (kind === 'filter' && v.value % 2 === 0) output.push({ id: `out-${v.id}`, value: v.value });
      if (kind === 'reduce') acc += v.value;
      drawMethod(`입력[${index}] = ${v.value} 처리 · ${kind === 'filter' ? v.value % 2 === 0 ? '조건에 맞아 남깁니다.' : '조건에 맞지 않아 건너뜁니다.' : operation}`, v.id);
      frames.at(-1)!.code = kind === 'reduce' ? `fn(${before}, ${v.value}, ${index}) → ${acc}` : `fn(${v.value}, ${index}) → ${kind === 'map' ? v.value * 2 : v.value % 2 === 0}`;
    }
    drawMethod('완료. 원본 배열은 바뀌지 않았습니다.');
  }
  return frames;
}
