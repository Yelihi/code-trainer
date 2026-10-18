export type VisualNode = { id: string; label: string; x: number; y: number; active?: boolean; muted?: boolean };
export type Frame = { nodes: VisualNode[]; edges: [string, string][]; note: string; detail: string };
export const visualKinds = ['stack', 'queue', 'linked-list', 'dictionary', 'priority-queue', 'binary-search', 'merge-sort', 'bfs', 'dfs', 'map', 'filter', 'reduce'];

export function buildTrace(kind: string, values = [5, 2, 7, 1], target = 7): Frame[] {
  const frames: Frame[] = [];
  const add = (nodes: VisualNode[], note: string, detail = '', edges: [string, string][] = []) => frames.push({ nodes: nodes.map(n => ({ ...n })), note, detail, edges: [...edges] });
  const row = (a: { id: string; value: number }[], y = 115, active = '') => a.map((v, i) => ({ id: v.id, label: String(v.value), x: 30 + i * 73, y, active: v.id === active }));
  const input = values.map((value, i) => ({ id: `v${i}`, value }));
  if (['stack', 'queue', 'linked-list'].includes(kind)) {
    const state: typeof input = [];
    const drawStructure = (note: string, active = '') => {
      const nodes = row(state, 140, active);
      if (kind === 'stack') nodes.forEach((n, i) => { n.x = 280; n.y = 285 - i * 34; });
      add(nodes, note, kind === 'stack' ? '위쪽 = top · LIFO' : kind === 'queue' ? '왼쪽 = front · 오른쪽 = back · FIFO' : '왼쪽 = head · 화살표 = next',
        kind === 'linked-list' ? nodes.slice(1).map((n, i) => [nodes[i].id, n.id]) : []);
    };
    drawStructure('빈 구조에서 시작합니다.');
    for (const v of input) {
      if (kind === 'linked-list') state.unshift(v); else state.push(v);
      drawStructure(`${kind === 'queue' ? 'enqueue' : kind === 'stack' ? 'push' : 'prepend'}(${v.value})`, v.id);
    }
    while (state.length) {
      const v = kind === 'stack' ? state.pop()! : state.shift()!;
      drawStructure(`${kind === 'queue' ? 'dequeue' : kind === 'stack' ? 'pop' : 'removeFirst'}() → ${v.value}`);
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
        if (heap[p].value <= heap[i].value) break;
        [heap[p], heap[i]] = [heap[i], heap[p]]; i = p; drawHeap('부모보다 작으므로 위로 교환합니다.', v.id);
      }
    }
    const removed: number[] = [];
    while (heap.length) {
      const min = heap[0]; removed.push(min.value); const last = heap.pop()!;
      if (heap.length) heap[0] = last;
      drawHeap(`pop() → ${min.value}. 마지막 원소로 루트를 채웁니다.`, last.id);
      let i = 0;
      while (true) {
        let s = i; const l = i * 2 + 1, r = l + 1;
        if (l < heap.length && heap[l].value < heap[s].value) s = l;
        if (r < heap.length && heap[r].value < heap[s].value) s = r;
        if (s === i) break;
        [heap[i], heap[s]] = [heap[s], heap[i]]; i = s; drawHeap('더 작은 자식과 교환해 힙 규칙을 복구합니다.', last.id);
      }
    }
    drawHeap(`꺼낸 순서: ${removed.join(' → ')}`);
  } else if (kind === 'dictionary') {
    const buckets: { id: string; label: string }[][] = Array.from({ length: 8 }, () => []);
    const drawBuckets = (note: string, active = '') => {
      const nodes: VisualNode[] = buckets.map((_, i) => ({ id: `bucket${i}`, label: `#${i}`, x: 20 + i * 77, y: 40, muted: true }));
      const edges: [string, string][] = [];
      buckets.forEach((bucket, i) => bucket.forEach((entry, j) => {
        nodes.push({ ...entry, x: 20 + i * 77, y: 100 + j * 65, active: entry.id === active });
        edges.push([j ? bucket[j - 1].id : `bucket${i}`, entry.id]);
      }));
      add(nodes, note, 'hash = 문자 코드 합 % 8 · 같은 버킷에서도 원래 키를 비교합니다.', edges);
    };
    drawBuckets('8개 버킷을 준비합니다.');
    for (const [key, value] of [['a', 1], ['i', 2], ['a', 3]] as const) {
      const bucket = buckets[key.charCodeAt(0) % 8]; const old = bucket.find(n => n.id === key);
      if (old) old.label = `${key}: ${value}`; else bucket.push({ id: key, label: `${key}: ${value}` });
      drawBuckets(`set('${key}', ${value}) · ${old ? '같은 키의 값만 갱신합니다.' : bucket.length > 1 ? '충돌: 같은 버킷에 별도 키로 보관합니다.' : '키와 값을 저장합니다.'}`, key);
    }
    drawBuckets("get('i') → 2 · a와 다른 키임을 확인합니다.", 'i');
    buckets[1].shift(); drawBuckets("delete('a') → true · 같은 버킷의 i는 남습니다.", 'i');
  } else if (kind === 'binary-search') {
    const sorted = [...input].sort((a, b) => a.value - b.value);
    let l = 0, r = sorted.length - 1, found = -1;
    add(row(sorted), '먼저 오름차순 배열을 준비합니다.', `찾을 값: ${target}`);
    while (l <= r) {
      const mid = Math.floor((l + r) / 2);
      const nodes = row(sorted, 140, sorted[mid].id).map((n, i) => ({ ...n, muted: i < l || i > r }));
      add(nodes, `중간 값 ${sorted[mid].value}와 ${target}을 비교합니다.`, `left=${l} · mid=${mid} · right=${r}`);
      if (sorted[mid].value >= target) { if (sorted[mid].value === target) found = mid; r = mid - 1; }
      else l = mid + 1;
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
      while (a.length && b.length) merged.push(a[0].value <= b[0].value ? a.shift()! : b.shift()!);
      current.splice(left, right - left, ...merged, ...a, ...b);
      add(row(current).map((n, i) => ({ ...n, active: i >= left && i < right })), `[${left}, ${right})를 작은 값부터 병합했습니다.`, '한쪽이 비면 다른 쪽의 나머지를 모두 붙입니다.');
    };
    sort(0, current.length); add(row(current), '모든 구간의 병합이 끝났습니다.');
  } else if (kind === 'bfs' || kind === 'dfs') {
    const graph: Record<string, string[]> = { A: ['B', 'C'], B: ['D'], C: ['D'], D: ['A'] };
    const nodes = [{ id: 'A', label: 'A', x: 294, y: 30 }, { id: 'B', label: 'B', x: 148, y: 135 }, { id: 'C', label: 'C', x: 440, y: 135 }, { id: 'D', label: 'D', x: 294, y: 250 }];
    const edges = Object.entries(graph).flatMap(([a, next]) => next.map(b => [a, b] as [string, string]));
    const visited = new Set<string>(), order: string[] = [];
    const drawGraph = (note: string, active: string, pending: string[]) => add(nodes.map(n => ({ ...n, active: n.id === active, muted: visited.has(n.id) && n.id !== active })), note,
      `방문: ${order.join(' → ') || '없음'} · ${kind === 'bfs' ? '큐' : '호출 스택'}: ${pending.join(', ') || '비어 있음'}`, edges);
    drawGraph('A에서 시작합니다. D → A 순환도 있습니다.', '', []);
    if (kind === 'bfs') {
      const queue = ['A']; visited.add('A');
      while (queue.length) {
        const node = queue.shift()!; order.push(node);
        for (const next of graph[node]) if (!visited.has(next)) { visited.add(next); queue.push(next); }
        drawGraph(`${node}를 처리하고 방문하지 않은 이웃을 큐에 넣었습니다.`, node, queue);
      }
    } else {
      const visit = (node: string, stack: string[]) => {
        if (visited.has(node)) { drawGraph(`${node}는 이미 방문했으므로 건너뜁니다.`, node, stack); return; }
        visited.add(node); order.push(node); const path = [...stack, node]; drawGraph(`${node}에 들어왔습니다.`, node, path);
        for (const next of graph[node]) visit(next, path);
        drawGraph(`${node}의 탐색을 마치고 돌아갑니다.`, node, stack);
      };
      visit('A', []);
    }
    drawGraph('도달 가능한 모든 정점을 방문했습니다.', '', []);
  } else if (['map', 'filter', 'reduce'].includes(kind)) {
    const output: typeof input = []; let acc = 10;
    const operation = kind === 'map' ? 'value × 2' : kind === 'filter' ? 'value % 2 === 0' : 'acc + value · 초기값 10';
    const drawMethod = (note: string, active = '') => add([...row(input, 70, active), ...row(output, 220), ...(kind === 'reduce' ? [{ id: 'acc', label: String(acc), x: 280, y: 220, active: true }] : [])], note, `위: 입력 · 아래: ${kind === 'reduce' ? '누적값' : '결과'} · ${operation}`);
    drawMethod('입력을 왼쪽부터 순회합니다.');
    for (const v of input) {
      if (kind === 'map') output.push({ id: `out-${v.id}`, value: v.value * 2 });
      if (kind === 'filter' && v.value % 2 === 0) output.push({ id: `out-${v.id}`, value: v.value });
      if (kind === 'reduce') acc += v.value;
      drawMethod(`${v.value} 처리 · ${kind === 'filter' ? v.value % 2 === 0 ? '조건에 맞아 남깁니다.' : '조건에 맞지 않아 건너뜁니다.' : operation}`, v.id);
    }
    drawMethod('완료. 원본 배열은 바뀌지 않았습니다.');
  }
  return frames;
}
