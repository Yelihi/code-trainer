"""Authored, versioned TypeScript lessons. Private answers never enter catalog responses."""
from copy import deepcopy
from .foundation_guides import HINTS, READINGS

MIT = {'title': 'MIT 6.006 · 강의 자료', 'url': 'https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/'}
MDN = 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/'
LESSONS = []


def lesson(id, title, group, summary, concept, complexity, application, questions, requirements,
           starter, reference, public_tests, hidden_tests, mutations, visualization, prerequisites=(),
           priority=1, difficulty='입문', cost_tests='', reading=None, hints=None,
           visual_frames=None, sources=None, visual_round=False):
    LESSONS.append(dict(id=id, version=1, title=title, group=group, priority=priority,
        difficulty=difficulty, summary=summary, concept=concept,
        complexity=complexity, application=application, prerequisites=list(prerequisites),
        questions=[{'id': f'q{i+1}', 'prompt': q, 'answer': a} for i, (q, a) in enumerate(questions)],
        requirements=requirements, starter=starter.strip(), reference=reference.strip(),
        public_tests=public_tests.strip(), hidden_tests=hidden_tests.strip(), cost_tests=cost_tests.strip(),
        test_starter='// assertEqual(실제 값, 예상 값)을 사용하세요.\n// 정상 동작과 경계 조건을 포함해 2개 이상 검증하세요.\n',
        mutations=[{'label': label, 'code': reference.strip().replace(old, new)} for label, old, new in mutations],
        visualization=visualization, visual_frames=visual_frames, visual_round=visual_round,
        sources=sources if sources is not None else ([{'title': f'MDN · Array.{id}', 'url': MDN+id}] if group == '메서드' else [MIT])))
    if reading is not None:
        READINGS[id] = reading
    if hints is not None:
        HINTS[id] = hints


lesson('stack', '스택 · 마지막 작업부터', '자료구조', 'LIFO와 상태를 가진 객체를 구현합니다.',
    '스택은 마지막에 넣은 값을 먼저 꺼내는 LIFO 구조입니다. `push`는 맨 위에 추가하고 `pop`은 맨 위를 제거합니다. `peek`는 제거 없이 확인합니다. 배열의 끝을 스택의 위로 정하면 앞쪽 원소를 이동할 필요가 없습니다.',
    '배열 기반 `push`는 분할 상환 `O(1)`, `pop`·`peek`·`size`는 `O(1)`. 저장 공간 `O(n)`.',
    '편집기의 실행 취소: 작업을 `push`하고 취소할 때 가장 최근 작업을 `pop`해 되돌립니다. 실제 편집기는 반대 작업 정보와 다시 실행용 스택도 관리합니다.',
    [('10, 20을 넣고 한 번 꺼내면 어떤 값이 나오며 왜 그런가요?', '20. 나중에 넣은 값부터 꺼내는 LIFO이기 때문이다.'),
     ('빈 스택과 `peek`의 동작을 설명해주세요.', '빈 `pop`과 `peek`는 `undefined`를 반환한다. `peek`는 값을 제거하지 않으므로 `size`가 변하지 않는다.')],
    ['숫자 전용 `Stack`의 API: `push(value): void, pop(): number | undefined, peek(): number | undefined, size(): number`.',
     '빈 `pop`/`peek`는 `undefined`. 각 인스턴스의 상태는 독립적입니다. 배열의 `push`/`pop`을 사용해도 됩니다.'],
    '''class Stack {
  push(value: number): void { /* 구현 */ }
  pop(): number | undefined { return undefined; }
  peek(): number | undefined { return undefined; }
  size(): number { return 0; }
}''',
    '''class Stack {
  private items: number[] = [];
  push(value: number): void { this.items.push(value); }
  pop(): number | undefined { return this.items.pop(); }
  peek(): number | undefined { return this.items[this.items.length - 1]; }
  size(): number { return this.items.length; }
}''',
    '''const s = new Stack(); s.push(10); s.push(20);
assertEqual(s.pop(), 20); assertEqual(s.peek(), 10); assertEqual(s.size(), 1);''',
    '''const s = new Stack(); assertEqual(s.pop(), undefined); assertEqual(s.peek(), undefined);
s.push(0); s.push(-1); s.push(-1); assertEqual(s.size(), 3);
assertEqual(s.pop(), -1); assertEqual(s.pop(), -1); assertEqual(s.pop(), 0); assertEqual(s.size(), 0);
assertEqual(new Stack().size(), 0);''',
    [('꺼내는 순서', 'return this.items.pop()', 'return this.items.shift()'),
     ('peek의 상태 보존', 'return this.items[this.items.length - 1]', 'return this.items.pop()')], 'stack')

lesson('queue', '큐 · 먼저 온 작업부터', '자료구조', 'FIFO와 앞쪽 인덱스로 대기열을 구현합니다.',
    '큐는 먼저 들어온 값을 먼저 꺼내는 FIFO 구조입니다. 뒤에 추가하고 앞에서 제거합니다. 배열에서 매번 `shift`하면 나머지 원소를 옮길 수 있습니다. `head` 인덱스를 증가시키면 앞 원소 이동을 피할 수 있습니다. 모두 꺼냈을 때 배열과 `head`를 초기화하면 이전 저장 공간을 정리할 수 있습니다.',
    '`head`를 이용한 `dequeue`·`peek`·`size`는 `O(1)`, `enqueue`는 배열 기준 분할 상환 `O(1)`. 단순 `head` 방식은 완전히 비우기 전까지 이전 슬롯을 보유합니다.',
    '순서대로 처리해야 하는 작업 대기열이나 BFS의 다음 방문 목록에 사용합니다. 네트워크 작업은 별도로 실패·재시도 정책이 필요합니다.',
    [('10, 20을 넣고 한 번 꺼내면 어떤 값이 나오며 왜 그런가요?', '10. 먼저 들어온 값부터 꺼내는 FIFO이기 때문이다.'),
     ('빈 큐 처리와 `head` 인덱스의 이점을 설명해주세요.', '빈 `dequeue`와 `peek`는 `undefined`를 반환한다. `head`를 이동하면 배열 앞의 원소를 매번 이동하지 않아도 된다.')],
    ['숫자 전용 `Queue`의 API: `enqueue(value): void, dequeue(): number | undefined, peek(): number | undefined, size(): number`.',
     '빈 `dequeue`/`peek`는 `undefined`. 제거 후에도 다시 추가할 수 있어야 합니다. `head` 인덱스 방식을 연습하세요.'],
    '''class Queue {
  enqueue(value: number): void { /* 구현 */ }
  dequeue(): number | undefined { return undefined; }
  peek(): number | undefined { return undefined; }
  size(): number { return 0; }
}''',
    '''class Queue {
  private items: number[] = [];
  private head = 0;
  enqueue(value: number): void { this.items.push(value); }
  dequeue(): number | undefined {
    if (this.size() === 0) return undefined;
    const value = this.items[this.head++];
    if (this.head === this.items.length) { this.items = []; this.head = 0; }
    return value;
  }
  peek(): number | undefined { return this.items[this.head]; }
  size(): number { return this.items.length - this.head; }
}''',
    '''const q = new Queue(); q.enqueue(10); q.enqueue(20);
assertEqual(q.dequeue(), 10); assertEqual(q.peek(), 20); assertEqual(q.size(), 1);''',
    '''const q = new Queue(); assertEqual(q.dequeue(), undefined); assertEqual(q.peek(), undefined);
q.enqueue(0); q.enqueue(-2); assertEqual(q.dequeue(), 0); q.enqueue(5);
assertEqual(q.dequeue(), -2); assertEqual(q.dequeue(), 5); assertEqual(q.size(), 0);
q.enqueue(7); assertEqual(q.dequeue(), 7); assertEqual(new Queue().size(), 0);''',
    [('FIFO 순서', 'const value = this.items[this.head++];', 'const value = this.items.pop();'),
     ('제거 후 크기', 'return this.items.length - this.head;', 'return this.items.length;')], 'queue', ['stack'])

lesson('linked-list', '연결 리스트 · 연결 바꾸기', '자료구조', '노드와 다음 참조를 연결하고 끊습니다.',
    '단일 연결 리스트는 각 노드가 값과 다음 노드 참조를 가집니다. `head`는 첫 노드입니다. 앞에 추가할 때 새 노드의 `next`를 이전 `head`로 정하고 `head`를 새 노드로 바꿉니다. 뒤쪽 접근에는 앞에서부터 참조를 따라가야 합니다.',
    '앞 삽입·제거 `O(1)`, 전체 순회 `O(n)`, 저장 공간 `O(n)`. 임의 위치 접근은 배열과 달리 `O(n)`.',
    'LRU 캐시는 해시 테이블과 양방향 연결 리스트를 함께 써서 최근 사용 순서를 갱신할 수 있습니다. 여기서는 그 기초인 단일 연결 리스트를 구현합니다.',
    [('앞에 새 노드를 추가할 때 참조를 어떤 순서로 바꾸나요?', '새 노드의 `next`를 기존 `head`로 연결한 뒤 `head`를 새 노드로 바꾼다. 기존 연결을 잃지 않는다.'),
     ('앞 제거와 전체 순회의 비용은 왜 다른가요?', '앞 제거는 `head`를 `next`로 바꾸면 되므로 `O(1)`, 전체 순회는 모든 노드를 방문하므로 `O(n)`이다.')],
    ['숫자 전용 `LinkedList`의 API: `prepend(value): void, removeFirst(): number | undefined, toArray(): number[]`.',
     '빈 `removeFirst`는 `undefined`, 빈 `toArray`는 []. 실제 노드의 `next` 참조를 사용해 구현해보세요.'],
    '''class LinkedList {
  prepend(value: number): void { /* 구현 */ }
  removeFirst(): number | undefined { return undefined; }
  toArray(): number[] { return []; }
}''',
    '''type ListNode = { value: number; next: ListNode | null };
class LinkedList {
  private head: ListNode | null = null;
  prepend(value: number): void { this.head = { value, next: this.head }; }
  removeFirst(): number | undefined {
    if (!this.head) return undefined;
    const value = this.head.value; this.head = this.head.next; return value;
  }
  toArray(): number[] {
    const values: number[] = [];
    for (let node = this.head; node; node = node.next) values.push(node.value);
    return values;
  }
}''',
    '''const l = new LinkedList(); l.prepend(1); l.prepend(2);
assertEqual(l.toArray(), [2,1]); assertEqual(l.removeFirst(), 2); assertEqual(l.toArray(), [1]);''',
    '''const l = new LinkedList(); assertEqual(l.removeFirst(), undefined); assertEqual(l.toArray(), []);
l.prepend(0); l.prepend(0); assertEqual(l.removeFirst(), 0); assertEqual(l.removeFirst(), 0);
l.prepend(-3); assertEqual(l.toArray(), [-3]); assertEqual(new LinkedList().toArray(), []);''',
    [('기존 노드 연결', 'next: this.head', 'next: null'), ('제거 후 head', 'this.head = this.head.next;', 'this.head = null;')], 'linked-list', ['stack'])

lesson('dictionary', 'Dictionary와 Set · 키로 찾기', '자료구조', '버킷과 충돌 처리를 가진 작은 해시 테이블입니다.',
    '`Dictionary`는 키를 값에 대응시킵니다. 해시 함수가 키를 버킷 번호로 바꾸지만 서로 다른 키가 같은 번호를 가질 수 있습니다. 이 충돌은 버킷 안에서 원래 키까지 비교해 해결합니다. `Set`은 값 대신 키의 존재 여부에 집중하는 집합입니다.',
    '해시가 고르게 분산되고 버킷 수가 데이터에 맞춰 늘면 평균 `O(1)`. 이 연습은 고정 8개 버킷이므로 데이터가 많아지면 탐색·삽입·삭제 모두 최악 `O(n)`.',
    '사용자 ID로 정보를 조회하거나, 이미 처리한 이벤트 ID를 `Set`에 저장해 중복 처리를 막는 데 활용합니다. 키가 없다는 상태와 0이라는 값을 구분해야 합니다.',
    [('해시 충돌이 있어도 두 키의 값을 보존하려면 어떻게 해야 하나요?', '같은 버킷에 여러 키-값 쌍을 두고 원래 키를 비교해 찾거나 갱신한다.'),
     ('키가 없는 경우와 값이 0인 경우, `Dictionary`와 `Set`의 차이를 설명해주세요.', '없는 키는 `undefined`이고 0도 유효한 값이다. `Dictionary`는 키-값 대응, `Set`은 키의 존재와 중복 제거에 사용한다.')],
    ['`Dictionary`의 API: `set(key: string, value: number): void, get(key): number | undefined, has(key): boolean, delete(key): boolean, size(): number`.',
     '빈 문자열을 포함한 문자열 키. 같은 키는 갱신하고 크기는 유지. 없는 키 삭제는 `false`. `hash(key)`를 사용한 8개 버킷으로 연습합니다.'],
    '''function hash(key: string): number { return Array.from(key).reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % 8; }
class Dictionary {
  set(key: string, value: number): void { /* 구현 */ }
  get(key: string): number | undefined { return undefined; }
  has(key: string): boolean { return false; }
  delete(key: string): boolean { return false; }
  size(): number { return 0; }
}''',
    '''function hash(key: string): number { return Array.from(key).reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % 8; }
class Dictionary {
  private buckets: [string, number][][] = Array.from({length: 8}, () => []);
  private count = 0;
  set(key: string, value: number): void {
    const bucket = this.buckets[hash(key)]; const entry = bucket.find(e => e[0] === key);
    if (entry) entry[1] = value; else { bucket.push([key, value]); this.count++; }
  }
  get(key: string): number | undefined { return this.buckets[hash(key)].find(e => e[0] === key)?.[1]; }
  has(key: string): boolean { return this.get(key) !== undefined; }
  delete(key: string): boolean {
    const bucket = this.buckets[hash(key)]; const i = bucket.findIndex(e => e[0] === key);
    if (i < 0) return false; bucket.splice(i, 1); this.count--; return true;
  }
  size(): number { return this.count; }
}''',
    '''const d = new Dictionary(); d.set('a', 1); d.set('i', 2);
assertEqual(d.get('a'), 1); assertEqual(d.get('i'), 2); d.set('a', 3); assertEqual(d.size(), 2);
assertEqual(d.get('a'), 3);''',
    '''const d = new Dictionary(); d.set('', 0); d.set('__proto__', 4);
assertEqual(d.has(''), true); assertEqual(d.get(''), 0); assertEqual(d.has('missing'), false);
assertEqual(d.delete('missing'), false); assertEqual(d.delete(''), true); assertEqual(d.get(''), undefined);
assertEqual(d.get('__proto__'), 4); assertEqual(d.size(), 1);
d.set('a',1); d.set('i',2); d.delete('a'); assertEqual(d.get('i'),2);''',
    [('같은 키 갱신', 'if (entry) entry[1] = value;', 'if (entry) { entry[1] = value; this.count++; }'),
     ('0인 값의 존재', 'return this.get(key) !== undefined;', 'return Boolean(this.get(key));')], 'dictionary', ['linked-list'])

lesson('priority-queue', '우선순위 큐 · 가장 작은 값부터', '자료구조', '최소 힙으로 우선순위에 따라 꺼냅니다.',
    '최소 힙은 부모 값이 자식 값보다 크지 않은 완전 이진 트리입니다. 배열의 i번째 노드의 자식은 2i+1, 2i+2입니다. 삽입은 끝에서 위로, 제거는 마지막 값을 루트로 옮긴 뒤 작은 자식 방향으로 내려가며 규칙을 회복합니다. 전체 배열이 정렬되어 있을 필요는 없습니다.',
    '`push`·`pop` `O(log n)`, `peek` `O(1)`, 저장 공간 `O(n)`. 같은 우선순위끼리의 순서는 여기서 보장하지 않습니다.',
    '다음 실행 시각이 가장 빠른 작업을 꺼내는 예약 처리나 최단 경로 탐색에 사용합니다. 이 문제에서는 숫자가 작을수록 먼저 나옵니다.',
    [('최소 힙의 규칙과 정렬된 배열의 차이를 설명해주세요.', '모든 부모가 자식보다 작거나 같다. 형제나 다른 부분 트리끼리 정렬될 필요는 없지만 루트는 최솟값이다.'),
     ('루트 제거 후 어떤 값으로 채우고 어떻게 복구하나요?', '마지막 값을 루트로 옮기고 더 작은 자식과 교환하며 아래로 내려간다. 높이만큼 이동하므로 `O(log n)`.')],
    ['`MinHeap`의 API: `push(value: number): void, pop(): number | undefined, peek(): number | undefined`.',
     '중복·음수 허용. 빈 `pop`/`peek`는 `undefined`. 최소 힙의 위로/아래로 이동을 구현해보세요.'],
    '''class MinHeap {
  push(value: number): void { /* 구현 */ }
  pop(): number | undefined { return undefined; }
  peek(): number | undefined { return undefined; }
}''',
    '''class MinHeap {
  private a: number[] = [];
  push(value: number): void {
    this.a.push(value); let i = this.a.length - 1;
    while (i > 0) { const p = Math.floor((i - 1) / 2); if (this.a[p] <= this.a[i]) break;
      [this.a[p], this.a[i]] = [this.a[i], this.a[p]]; i = p; }
  }
  pop(): number | undefined {
    if (!this.a.length) return undefined;
    const min = this.a[0], last = this.a.pop()!;
    if (this.a.length) {
      this.a[0] = last; let i = 0;
      while (true) {
        const l = 2*i+1, r = l+1; let s = i;
        if (l < this.a.length && this.a[l] < this.a[s]) s = l;
        if (r < this.a.length && this.a[r] < this.a[s]) s = r;
        if (s === i) break;
        [this.a[i], this.a[s]] = [this.a[s], this.a[i]]; i = s;
      }
    }
    return min;
  }
  peek(): number | undefined { return this.a[0]; }
}''',
    '''const h = new MinHeap(); [5,2,7,1].forEach(n => h.push(n));
assertEqual(h.peek(), 1); assertEqual([h.pop(),h.pop(),h.pop(),h.pop()], [1,2,5,7]);''',
    '''const h = new MinHeap(); assertEqual(h.pop(), undefined); assertEqual(h.peek(), undefined);
[0,-4,-4,8,3,1].forEach(n=>h.push(n)); assertEqual(h.pop(),-4); h.push(-5);
assertEqual([h.pop(),h.pop(),h.pop(),h.pop(),h.pop(),h.pop()],[-5,-4,0,1,3,8]);
assertEqual(h.pop(),undefined);''',
    [('삽입 시 위로 이동', 'if (this.a[p] <= this.a[i]) break;', 'if (true) break;'),
     ('제거 시 오른쪽 자식', 'if (r < this.a.length && this.a[r] < this.a[s]) s = r;', 'if (false) s = r;')], 'priority-queue', ['queue'])

lesson('binary-search', '이진 탐색 · 범위를 절반으로', '알고리즘', '정렬 조건과 탐색 범위의 경계를 다룹니다.',
    '오름차순 배열에서 중간 값과 목표를 비교해 불가능한 절반을 제외합니다. `left`와 `right`를 모두 포함하는 범위로 정했다면 `left` <= `right` 동안 검사하고, 다음 범위는 `mid`+1 또는 `mid`-1로 줄입니다. 같은 값이 여러 개면 왼쪽을 더 탐색해 첫 위치를 찾을 수 있습니다.',
    '탐색 `O(log n)`, 반복문 구현의 추가 공간 `O(1)`. 입력 배열의 정렬 비용은 별도입니다.',
    '정렬된 시간 기록에서 특정 시각의 위치를 찾거나, 조건을 만족하는 최소 설정값을 좁히는 데 활용합니다. 이 단원은 정확히 일치하는 첫 인덱스를 찾습니다.',
    [('이진 탐색에 정렬이 필요한 이유를 설명해주세요.', '중간 값과 비교한 결과로 한쪽 절반에 목표가 없다고 확신하려면 정렬되어 있어야 한다.'),
     ('동일한 값이 여러 개일 때 첫 위치를 찾으려면 어떻게 하나요?', '일치한 위치를 저장하고 `right`를 `mid`-1로 옮겨 왼쪽에도 일치 값이 있는지 계속 탐색한다.')],
    ['`binarySearch(values: number[], target: number): number`. 오름차순 배열에서 첫 일치 인덱스, 없으면 -1.',
     '빈 배열·중복 값 포함. 입력을 변경하지 마세요.'],
    'function binarySearch(values: number[], target: number): number { return -1; }',
    '''function binarySearch(values: number[], target: number): number {
  let left = 0, right = values.length - 1, found = -1;
  while (left <= right) {
    const mid = Math.floor((left+right)/2);
    if (values[mid] >= target) { if (values[mid] === target) found = mid; right = mid - 1; }
    else left = mid + 1;
  }
  return found;
}''',
    'assertEqual(binarySearch([1,3,3,5],3),1); assertEqual(binarySearch([1,3,5],4),-1);',
    '''assertEqual(binarySearch([],2),-1); assertEqual(binarySearch([2],2),0);
assertEqual(binarySearch([2,2,2,2],2),0); assertEqual(binarySearch([-5,0,7],7),2);
const a=[1,2,3]; binarySearch(a,2); assertEqual(a,[1,2,3]);''',
    [('한 원소 범위', 'while (left <= right)', 'while (left < right)'),
     ('첫 일치 위치', 'if (values[mid] === target) found = mid;', 'if (values[mid] === target) return mid;')], 'binary-search')

lesson('merge-sort', '병합 정렬 · 나누고 합치기', '알고리즘', '작은 정렬 결과를 합쳐 전체 순서를 만듭니다.',
    '배열을 절반으로 나눠 각각 정렬한 뒤 두 배열의 앞부분을 비교하며 작은 값을 결과에 옮깁니다. 한쪽이 비면 다른 쪽의 남은 값을 모두 붙입니다. 길이가 0이나 1이면 이미 정렬된 상태이므로 재귀를 멈춥니다.',
    '시간 `O(n log n)`, 배열 병합을 위한 최대 추가 공간 `O(n)`, 재귀 깊이 `O(log n)`.',
    '이미 정렬된 로그 두 개를 시간순으로 합칠 때 병합 연산을 활용할 수 있습니다. 큰 파일의 외부 정렬도 작은 정렬 묶음을 병합하는 접근을 사용합니다.',
    [('재귀 종료 조건과 병합 과정의 역할을 설명해주세요.', '길이 0 또는 1에서 종료한다. 정렬된 두 부분에서 작은 앞 원소를 차례로 선택해 전체를 정렬한다.'),
     ('한쪽 배열을 다 소비하면 나머지는 어떻게 처리하나요?', '다른 쪽에 남은 원소를 모두 붙인다. 중복 값도 버리지 않고 보존한다.')],
    ['`mergeSort(values: number[]): number[]`. 오름차순의 새 배열을 반환하며 중복 값을 보존합니다.',
     '원본 배열을 변경하지 마세요. 분할과 병합을 직접 연습하세요.'],
    'function mergeSort(values: number[]): number[] { return []; }',
    '''function mergeSort(values: number[]): number[] {
  if (values.length <= 1) return values.slice();
  const mid = Math.floor(values.length/2), left = mergeSort(values.slice(0,mid)), right = mergeSort(values.slice(mid));
  const result: number[] = []; let i=0,j=0;
  while (i<left.length && j<right.length) {
    if (left[i] <= right[j]) result.push(left[i++]); else result.push(right[j++]);
  }
  return result.concat(left.slice(i), right.slice(j));
}''',
    'assertEqual(mergeSort([4,1,3,2]),[1,2,3,4]); assertEqual(mergeSort([]),[]);',
    '''assertEqual(mergeSort([3,1,1,-2,0]),[-2,0,1,1,3]); assertEqual(mergeSort([1]),[1]);
const a=[3,2,1]; const b=mergeSort(a); assertEqual(a,[3,2,1]); assertEqual(b===a,false);''',
    [('남은 원소 보존', 'return result.concat(left.slice(i), right.slice(j));', 'return result;'),
     ('비교 방향', 'left[i] <= right[j]', 'left[i] >= right[j]')], 'merge-sort', ['binary-search'])

for traversal in ('bfs', 'dfs'):
    bfs = traversal == 'bfs'
    reference = ('''function bfs(graph: Record<string, string[]>, start: string): string[] {
  const visited = new Set<string>([start]), queue = [start], order: string[] = [];
  for (let head=0; head<queue.length; head++) {
    const node = queue[head]; order.push(node);
    for (const next of Object.hasOwn(graph, node) ? graph[node] : []) if (!visited.has(next)) { visited.add(next); queue.push(next); }
  }
  return order;
}''' if bfs else '''function dfs(graph: Record<string, string[]>, start: string): string[] {
  const visited = new Set<string>(), order: string[] = [];
  function visit(node: string): void {
    if (visited.has(node)) return;
    visited.add(node); order.push(node);
    for (const next of Object.hasOwn(graph, node) ? graph[node] : []) visit(next);
  }
  visit(start); return order;
}''')
    lesson(traversal, 'BFS · 가까운 곳부터' if bfs else 'DFS · 한 경로를 깊게', '알고리즘',
        '방문 기록과 큐로 그래프를 탐색합니다.' if bfs else '방문 기록과 재귀로 그래프를 탐색합니다.',
        ('BFS는 시작점부터 간선 수가 가까운 순서로 탐색합니다. 큐에 넣는 시점에 방문 처리하면 같은 정점이 여러 번 대기열에 들어가는 것을 막습니다. 모든 간선의 비용이 같을 때 최소 간선 수 경로를 찾는 데 사용할 수 있습니다.' if bfs else
         'DFS는 한 이웃으로 깊이 들어갔다가 더 갈 곳이 없으면 되돌아옵니다. 재귀 호출 스택이 돌아올 위치를 기억합니다. 방문 처리를 먼저 해야 순환이 있는 그래프에서도 멈춥니다. 일반적으로 최단 경로를 보장하지는 않습니다.'),
        '인접 리스트 기준 시간 `O(V+E)`, 방문 기록과 큐/재귀 스택 공간 `O(V)`. 여기서는 시작점에서 도달 가능한 부분을 탐색합니다.',
        '격자에서 최소 이동 횟수를 찾는 길찾기에 활용합니다.' if bfs else '폴더의 하위 항목을 재귀적으로 방문하거나 의존 관계를 순회할 때 활용합니다.',
        [('방문 순서와 사용하는 자료구조를 설명해주세요.', '큐로 먼저 발견한 정점부터 처리해 가까운 정점부터 방문한다.' if bfs else '재귀 호출 스택으로 한 이웃을 끝까지 방문하고 돌아와 다음 이웃으로 간다.'),
         ('순환과 연결되지 않은 정점은 어떻게 다루나요?', '방문 집합으로 중복 방문을 막는다. 시작점에서 도달할 수 없는 정점은 결과에 포함하지 않는다.')],
        [f'`{traversal}(graph: Record<string, string[]>, start: string): string[]`. 이웃 배열 순서대로 탐색한 방문 순서를 반환합니다.',
         '방향 그래프이며 순환·중복 간선을 허용합니다. 키가 없는 정점은 이웃이 없습니다. 시작점은 항상 결과에 포함합니다. 입력은 바꾸지 마세요.'],
        f'function {traversal}(graph: Record<string, string[]>, start: string): string[] {{ return []; }}', reference,
        f"const graph = {{A:['B','C'],B:['D'],C:[],D:[]}}; assertEqual({traversal}(graph,'A'), {repr(['A','B','C','D'] if bfs else ['A','B','D','C'])});\nassertEqual({traversal}({{}},'X'),['X']);",
        f"assertEqual({traversal}({{A:['B','B'],B:['A'],Z:[]}},'A'),['A','B']);\nassertEqual({traversal}({{A:['A']}},'A'),['A']);\nassertEqual({traversal}({{}},'toString'),['toString']);\nassertEqual({traversal}({{A:['constructor']}},'A'),['A','constructor']);\nconst g={{A:['B'],B:[]}}; {traversal}(g,'A'); assertEqual(g,{{A:['B'],B:[]}});",
        [('탐색 순서', 'return order;', 'return order.reverse();'),
         ('시작 정점 기록', 'order.push(node);', 'if (node !== start) order.push(node);')], traversal,
        ['queue' if bfs else 'stack'], priority=2, difficulty='보통')

for method in ('map', 'filter', 'reduce'):
    refs = {
      'map': '''function mapValues(values: number[], fn: (value: number, index: number) => number): number[] {
  const result: number[] = [];
  for (let i=0;i<values.length;i++) result.push(fn(values[i],i));
  return result;
}''',
      'filter': '''function filterValues(values: number[], fn: (value: number, index: number) => boolean): number[] {
  const result: number[] = [];
  for (let i=0;i<values.length;i++) if (fn(values[i],i)) result.push(values[i]);
  return result;
}''',
      'reduce': '''function reduceValues(values: number[], fn: (acc: number, value: number, index: number) => number, initial: number): number {
  let acc = initial;
  for (let i=0;i<values.length;i++) acc = fn(acc,values[i],i);
  return acc;
}'''
    }
    reference = refs[method]
    description = {'map':'각 값을 변환한 새 배열', 'filter':'조건에 맞는 원래 값의 새 배열', 'reduce':'누적 결과 하나'}[method]
    lesson(method, f'{method} · '+{'map':'하나씩 변환하기','filter':'조건으로 남기기','reduce':'하나로 누적하기'}[method], '메서드',
        description+('를' if method == 'reduce' else '을')+' 반복문으로 만듭니다.',
        {'map':'`map`은 각 원소에 콜백을 적용한 결과를 같은 순서로 담습니다. 입력이 n개면 결과도 n개입니다. 콜백에 현재 값과 인덱스를 전달하면 위치에 따른 변환도 가능합니다.',
         'filter':'`filter`는 콜백이 `true`인 원소만 원래 값 그대로 모읍니다. 결과의 길이는 줄어들 수 있지만 남은 값의 상대 순서는 유지됩니다. 콜백의 반환값 자체를 결과에 넣는 것이 아닙니다.',
         'reduce':'`reduce`는 누적값과 현재 원소로 다음 누적값을 계산합니다. 초기값이 첫 호출의 누적값입니다. 이 문제에서는 초기값을 항상 전달하고 빈 배열이면 초기값을 그대로 반환합니다.'}[method],
        '콜백 비용 `O(1)` 가정 시 시간 `O(n)`. '+('누적값의 추가 공간 `O(1)`.' if method=='reduce' else '새 결과 배열 공간 `O(n)`.'),
        {'map':'상품 가격에 세금을 적용한 표시 가격 목록을 만듭니다.', 'filter':'목록에서 재고가 있는 상품만 남기거나 조건에 맞는 검색 결과를 추립니다.', 'reduce':'장바구니의 금액을 초기 배송비에 더해 총액을 계산합니다.'}[method],
        [('이 메서드의 입력과 결과의 관계를 설명해주세요.', description+('를' if method == 'reduce' else '을')+' 반환한다. 원본 배열은 변경하지 않는다.'),
         ('빈 배열과 콜백 인덱스는 어떻게 처리하나요?', ('빈 배열이면 초기값을 반환한다.' if method=='reduce' else '빈 배열이면 새 빈 배열을 반환한다.')+' 콜백 인덱스는 원본 기준 0부터 시작한다.')],
        ['`'+reference.split('{')[0].strip()+'`'+'. 숫자 배열 전용입니다.',
         '일반적인 촘촘한 배열만 다룹니다. 희소 배열·`thisArg`·콜백의 배열 변경은 범위 밖입니다. `reduce`는 초기값 필수입니다.' if method=='reduce' else '일반적인 촘촘한 배열만 다룹니다. 희소 배열·`thisArg`·콜백의 배열 변경은 범위 밖입니다.',
         '원본을 변경하지 마세요. 반복문으로 직접 구현해보세요.'],
        reference.split('{')[0]+'{ return '+('0' if method=='reduce' else '[]')+'; }', reference,
        {'map': 'assertEqual(mapValues([2,4],(v,i)=>v+i),[2,5]); assertEqual(mapValues([],v=>v),[]);',
         'filter':'assertEqual(filterValues([1,2,3,4],v=>v%2===0),[2,4]); assertEqual(filterValues([],()=>true),[]);',
         'reduce':'assertEqual(reduceValues([1,2,3],(a,v)=>a+v,10),16); assertEqual(reduceValues([],(a,v)=>a+v,7),7);'}[method],
        {'map': 'const a=[0,-2,3]; assertEqual(mapValues(a,(v,i)=>i-v),[0,3,-1]); assertEqual(a,[0,-2,3]); assertEqual(mapValues(a,v=>v)===a,false);',
         'filter': 'const a=[0,-2,3]; assertEqual(filterValues(a,(v,i)=>i!==1),[0,3]); assertEqual(filterValues(a,()=>false),[]); assertEqual(a,[0,-2,3]); assertEqual(filterValues(a,()=>true)===a,false);',
         'reduce': 'const a=[2,3]; assertEqual(reduceValues(a,(acc,v,i)=>acc*v+i,2),13); assertEqual(a,[2,3]); assertEqual(reduceValues([1],(a,v)=>a+v,0),1);'}[method],
        {'map':[('콜백 인덱스','fn(values[i],i)','fn(values[i],0)'), ('원소 변환','result.push(fn(values[i],i))','result.push(values[i])')],
         'filter':[('조건 판정','if (fn(values[i],i))','if (!fn(values[i],i))'), ('콜백 인덱스','fn(values[i],i)','fn(values[i],0)')],
         'reduce':[('초기값','let acc = initial;','let acc = 0;'), ('콜백 인덱스','fn(acc,values[i],i)','fn(acc,values[i],0)')]}[method], method)

from .foundation_lessons_core import CORE_LESSONS
from .foundation_lessons_patterns import PATTERN_LESSONS
from .foundation_lessons_advanced import ADVANCED_LESSONS
from .foundation_lessons_specialist import SPECIALIST_LESSONS
for specification in CORE_LESSONS + PATTERN_LESSONS + ADVANCED_LESSONS + SPECIALIST_LESSONS:
    lesson(**specification)

CATALOG = {item['id']: item for item in LESSONS}


def public(item):
    keys = ('id', 'version', 'title', 'group', 'priority', 'difficulty', 'summary', 'concept', 'complexity', 'application',
            'prerequisites', 'requirements', 'starter', 'public_tests', 'test_starter', 'visualization', 'sources')
    result = {key: deepcopy(item[key]) for key in keys}
    visual_source = {'stack': 'list', 'queue': 'list', 'linked-list': 'list', 'dictionary': 'hashtable', 'priority-queue': 'heap', 'merge-sort': 'sorting', 'bfs': 'dfsbfs', 'dfs': 'dfsbfs'}.get(item['id'])
    if visual_source:
        result['sources'].append({'title': 'VisuAlgo · 구조와 연산 시각화', 'url': 'https://visualgo.net/en/'+visual_source})
    if item['id'] == 'binary-search':
        result['sources'].append({'title': 'Cornell CS 2110 · 첫 일치 이진 탐색', 'url': 'https://courses.cis.cornell.edu/courses/cs2110/2026sp/lectures/lec05/'})
    result['test_hints'] = deepcopy(HINTS[item['id']])
    result['reading'] = deepcopy(READINGS[item['id']])
    if item['visual_frames'] is not None:
        result['visual_frames'] = deepcopy(item['visual_frames'])
    if item['visual_round']:
        result['visual_round'] = True
    result['questions'] = [{k: q[k] for k in ('id', 'prompt')} for q in item['questions']]
    return result
