import type { Frame, VisualNode } from './foundationTrace';

export function linkedListTrace(doubly: boolean): Frame[] {
  const nodes: VisualNode[] = [
    { id: 'A', label: '10', x: 20, y: 45, next: 'B', prev: null },
    { id: 'B', label: '20', x: 200, y: 45, next: 'C', prev: 'A' },
    { id: 'C', label: '30', x: 390, y: 45, next: 'D', prev: 'B' },
    { id: 'D', label: '40', x: 500, y: 235, next: null, prev: 'C' },
  ];
  const frames: Frame[] = [];
  let head = 'A';
  const snapshot = (note: string, code: string, active = '', array = ['10', '20', '30', '40'], detail = '') => {
    frames.push({ nodes: nodes.map(n => ({ ...n, active: n.id === active, ...(doubly ? {} : { prev: undefined }) })),
      edges: nodes.filter(n => n.next).map(n => [n.id, n.next!]), note, code, head,
      detail: detail || '노드 ID는 객체의 정체성입니다. 그림의 위치는 메모리 주소가 아닌 배치 예시이며, 순서는 next 참조로 결정됩니다.',
      shelves: [{ label: '배열에서 같은 순서를 만들면 · [index]의 값', values: array }] });
  };
  snapshot('값과 참조를 따로 보세요. head는 A를 가리킵니다.', 'head = A');
  snapshot('중간 위치 B를 찾으려면 head부터 따라갑니다.', 'cursor = head', 'A');
  snapshot('A.next를 따라 B에 도착했습니다.', 'cursor = cursor.next', 'B', undefined, '위치를 찾는 순회는 O(n). 배열의 인덱스 접근은 O(1)입니다.');
  nodes.push({ id: 'X', label: '25', x: 200, y: 235, next: null, prev: null });
  snapshot('B와 C 사이에 넣을 새 노드 X를 준비합니다.', 'X = { value: 25, next: null }', 'X');
  nodes[4].next = 'C';
  snapshot('기존 뒤쪽 연결부터 보관합니다.', 'X.next = B.next', 'X');
  if (doubly) {
    nodes[4].prev = 'B'; nodes[2].prev = 'X';
    snapshot('이중 연결은 역방향 참조도 함께 갱신합니다.', 'X.prev = B; C.prev = X', 'C');
  }
  nodes[1].next = 'X';
  snapshot('삽입 완료. 기존 노드의 값과 위치는 그대로입니다.', 'B.next = X', 'B', ['10', '20', '25', '30', '40'], '연결 위치를 알면 참조 갱신은 O(1). 배열 중간 삽입은 뒤의 30, 40을 한 칸씩 이동해야 하므로 O(n)입니다.');
  nodes[4].next = 'D';
  if (doubly) nodes[3].prev = 'X';
  snapshot('C를 건너뛰도록 연결해 중간 노드를 제거합니다.', doubly ? 'X.next = C.next; D.prev = X' : 'X.next = C.next', 'X', ['10', '20', '25', '40'], 'C 객체가 즉시 사라지는 것은 아닙니다. head에서 도달할 수 없고 다른 참조도 없어야 나중에 메모리가 회수될 수 있습니다.');
  nodes.splice(2, 1);
  snapshot('남은 노드는 복사하지 않았습니다.', 'head → A → B → X → D', 'X', ['10', '20', '25', '40']);
  nodes.find(n => n.id === 'X')!.next = null;
  snapshot('마지막 D를 맨 앞으로 옮기기: 먼저 이전 연결을 끊습니다.', 'X.next = null', 'X', ['10', '20', '25', '40'], '단일 연결은 D만 알아서는 앞 노드를 찾을 수 없습니다. 이전 노드 X를 알고 있거나 다시 순회해야 합니다. 이중 연결은 D.prev로 바로 찾습니다.');
  nodes.find(n => n.id === 'D')!.next = 'A';
  if (doubly) { nodes.find(n => n.id === 'D')!.prev = null; nodes[0].prev = 'D'; }
  head = 'D';
  snapshot('head를 D로 바꾸면 같은 객체들의 순서가 달라집니다.', doubly ? 'D.next = A; A.prev = D; D.prev = null; head = D' : 'D.next = A; head = D', 'D', ['40', '10', '20', '25'], '이중 연결은 역방향 이동이 쉽지만 노드마다 prev 저장 공간과 갱신 작업이 더 필요합니다. 이 단원의 구현 과제는 next만 있는 단일 연결 리스트입니다.');
  return frames;
}

export const traversalGraph: Record<string, string[]> = {
  A: ['B', 'C'], B: ['D', 'E'], C: ['E'], D: ['B', 'F'], E: ['F'], F: ['C'], G: [],
};
export function graphTrace(kind: 'bfs' | 'dfs', start: string): Frame[] {
  const positions = [[25, 125], [180, 35], [180, 235], [350, 35], [350, 235], [510, 125], [510, 290]];
  const nodes = Object.keys(traversalGraph).map((id, i) => ({ id, label: id, x: positions[i][0], y: positions[i][1] }));
  const edges = Object.entries(traversalGraph).flatMap(([a, next]) => next.map(b => [a, b] as [string, string]));
  const discovered = new Set<string>(), finished = new Set<string>(), order: string[] = [], frames: Frame[] = [];
  const capture = (note: string, active: string, pending: string[], code: string, focus?: [string, string]) => frames.push({
    nodes: nodes.map(n => ({ ...n, active: n.id === active, state: finished.has(n.id) ? 'finished' : discovered.has(n.id) ? 'discovered' : 'unseen' })),
    edges, focus, note, code, detail: `방문: ${order.join(' → ') || '아직 없음'} · 이웃은 인접 목록에 적힌 순서로 검사합니다.`,
    shelves: [{ label: kind === 'bfs' ? '대기 큐 · 왼쪽부터 꺼냄' : '호출 스택 · 오른쪽이 top', values: [...pending] }, { label: '방문 순서', values: [...order] }],
  });
  capture(`${start}에서 시작합니다. G는 다른 정점과 연결되지 않았습니다.`, '', [], `start = '${start}'`);
  if (kind === 'bfs') {
    const queue = [start]; discovered.add(start);
    capture('큐에 넣는 순간 발견 표시를 해 중복 예약을 막습니다.', start, queue, 'visited.add(start); queue.push(start)');
    while (queue.length) {
      const node = queue.shift()!; order.push(node);
      capture(`${node}를 큐 앞에서 꺼내 처리합니다.`, node, queue, 'node = queue.shift()');
      for (const next of traversalGraph[node]) {
        const seen = discovered.has(next);
        if (!seen) { discovered.add(next); queue.push(next); }
        capture(`${node} → ${next}: ${seen ? '이미 발견했으므로 건너뜁니다.' : '처음 발견한 이웃을 큐 뒤에 넣습니다.'}`, node, queue, seen ? 'visited.has(next) → true' : 'visited.add(next); queue.push(next)', [node, next]);
      }
      finished.add(node);
      capture(`${node}의 모든 이웃을 검사했습니다.`, '', queue, '다음 대기 정점으로 이동');
    }
  } else {
    const visit = (node: string, stack: string[]) => {
      discovered.add(node); order.push(node); const path = [...stack, node];
      capture(`${node}로 들어가 호출 스택에 쌓습니다.`, node, path, 'visited.add(node); order.push(node)');
      for (const next of traversalGraph[node]) {
        const seen = discovered.has(next);
        capture(`${node} → ${next}: ${seen ? '이미 방문했으므로 순환·중복 경로를 건너뜁니다.' : '이 갈래를 끝까지 먼저 탐색합니다.'}`, node, path, seen ? 'visited.has(next) → true' : 'visit(next)', [node, next]);
        if (!seen) visit(next, path);
      }
      finished.add(node);
      capture(`${node} 탐색을 마치고 호출한 정점으로 돌아갑니다.`, stack.at(-1) ?? '', stack, 'return');
    };
    visit(start, []);
  }
  capture('시작점에서 도달 가능한 정점의 탐색이 끝났습니다.', '', [], 'return order');
  return frames;
}
