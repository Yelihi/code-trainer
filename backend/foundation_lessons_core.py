"""Original TypeScript foundation lessons; no source article or exercise text is copied."""


def row(values, active=(), y=130):
    return [{'id': f'v{i}', 'label': str(value), 'x': 35 + i * 105, 'y': y,
             'active': i in active, 'annotation': f'[{i}]'} for i, value in enumerate(values)]


def frame(nodes, note, detail, code='', shelves=None):
    result = {'nodes': nodes, 'edges': [], 'note': note, 'detail': detail}
    if code:
        result['code'] = code
    if shelves is not None:
        result['shelves'] = shelves
    return result


CORE_LESSONS = [
    dict(
        id='array-rotation', title='배열 회전 · 인덱스 옮기기', group='자료구조',
        summary='원소의 상대 순서를 유지하며 뒤쪽 k개를 앞으로 옮깁니다.',
        concept='배열 회전은 맨 뒤의 원소들이 앞으로 이어지는 순환 이동입니다. 길이 n에서 k번 오른쪽으로 회전한 결과는 마지막 k개와 앞쪽 n-k개를 이은 것과 같습니다. k가 n보다 크면 k % n번만 이동하면 됩니다. 새 배열을 만들면 원본을 건드리지 않습니다.',
        complexity='새 배열을 만드는 시간 O(n), 추가 공간 O(n). k번씩 실제로 밀면 O(nk)가 될 수 있습니다. 빈 배열에서는 나머지 연산 전에 길이를 확인해야 합니다.',
        application='시간대별 수치를 원형 순서로 표시하거나 순번을 바꿀 때 사용합니다. 인덱스가 끝에서 처음으로 이어지는 규칙을 연습하기 좋습니다.',
        questions=[('배열 [1,2,3,4]를 오른쪽으로 2칸 회전하면 어떤 순서인가요?', '[3,4,1,2]. 뒤의 두 원소가 앞에 오고, 각각의 상대 순서는 유지된다.'),
                   ('k가 배열 길이보다 크거나 배열이 비어 있으면 어떻게 처리하나요?', '길이 n이 양수이면 k % n으로 줄인다. 빈 배열은 나머지를 계산하지 않고 빈 새 배열을 반환한다.')],
        requirements=['`rotateRight(values: number[], steps: number): number[]`를 구현하세요.',
                      '`steps`는 0 이상의 정수입니다. 원본 배열은 변경하지 않고, 빈 입력에는 새 빈 배열을 반환하세요.'],
        starter='function rotateRight(values: number[], steps: number): number[] { return []; }',
        reference='''function rotateRight(values: number[], steps: number): number[] {
  const n = values.length;
  if (n === 0) return [];
  const k = steps % n;
  return values.slice(n - k).concat(values.slice(0, n - k));
}''',
        public_tests='''assertEqual(rotateRight([1,2,3,4], 2), [3,4,1,2]);
assertEqual(rotateRight([1,2,3], 0), [1,2,3]);''',
        hidden_tests='''const original = [1,2,3,4];
assertEqual(rotateRight(original, 6), [3,4,1,2]);
assertEqual(rotateRight(original, 10), [3,4,1,2]);
assertEqual(original, [1,2,3,4]);
assertEqual(rotateRight([], 20), []);
assertEqual(rotateRight([7], 999), [7]);
assertEqual(rotateRight([1,1,2], 1), [2,1,1]);
assertEqual(rotateRight(original, 0) === original, false);''',
        mutations=[('회전 방향', 'values.slice(n - k).concat(values.slice(0, n - k))', 'values.slice(k).concat(values.slice(0, k))'),
                   ('길이 초과', 'const k = steps % n;', 'const k = steps;')],
        visualization='array-rotation', prerequisites=['map'], difficulty='입문',
        reading={
            'invariant': '각 원소가 한 번씩 나타나며, 회전 전후 원소 사이의 원형 순서는 같습니다.',
            'steps': [['이동 횟수를 줄인다', '길이 4를 6번 돌리면 두 바퀴를 제외한 2번 회전과 같습니다.'],
                      ['경계를 찾는다', '오른쪽 2칸 회전이면 앞에 놓일 마지막 두 원소의 시작은 인덱스 2입니다.'],
                      ['두 구간을 잇는다', '뒤 구간 [3,4]와 앞 구간 [1,2]를 새 배열에 순서대로 넣습니다.']],
            'pitfall': '빈 배열에서는 steps % 0을 계산하지 마세요. 원본을 직접 잘라 붙이면 이후 원본을 사용하는 코드에 영향을 줄 수 있습니다.',
            'tradeoff': '새 배열은 구현이 단순하고 원본을 보존합니다. 추가 공간을 줄여야 한다면 세 구간을 뒤집는 제자리 방식도 가능하지만 경계 처리가 더 어렵습니다.',
            'case_study': '교대표에서 시작 순번을 다음 사람으로 옮길 때 원형 인덱스를 사용합니다. 원본 순번을 보존하면 이전 표와 새 표를 비교할 수 있습니다.',
            'experiment': '4개 원소에 0, 2, 6을 각각 적용해 보세요. 2와 6의 결과가 같은 이유를 확인하세요.'},
        hints=['배열 길이보다 큰 회전 횟수를 사용해보세요. 같은 결과를 내는 작은 횟수는 무엇인가요?',
               '입력이 비었거나 원소가 하나뿐일 때 원본 참조까지 그대로 반환하지 않는지 확인해보세요.'],
        visual_frames=[
            frame(row([1,2,3,4]), '원본 배열과 인덱스를 확인합니다.', '각 원소의 순서는 1 → 2 → 3 → 4입니다.'),
            frame(row([1,2,3,4], (2,3)), '마지막 두 원소를 선택합니다.', '6칸 회전은 길이 4로 나눈 나머지인 2칸과 같습니다.', 'k = 6 % 4 = 2'),
            frame([{**node, 'x': 35 + [2,3,0,1][i] * 105, 'active': i in (2,3)} for i, node in enumerate(row([1,2,3,4]))],
                  '뒤쪽 두 원소를 앞에 놓습니다.', '원소 자체를 바꾸지 않고 새 배열에서 차지할 위치만 이동합니다.', 'result = [3, 4, 1, 2]'),
            frame([{**node, 'x': 35 + [2,3,0,1][i] * 105} for i, node in enumerate(row([1,2,3,4]))],
                  '회전이 끝났습니다.', '각 원소가 한 번씩 포함되고 원형 순서는 그대로입니다.')]),
    dict(
        id='circular-queue', title='원형 큐 · 고정 공간 재사용', group='자료구조',
        summary='앞 포인터가 배열 끝에 도착해도 빈 칸을 다시 사용합니다.',
        concept='원형 큐는 고정 길이 배열에서 head와 count로 현재 항목의 위치를 기록합니다. 새 값은 (head + count) % capacity 위치에 씁니다. 제거할 때 head를 한 칸 옮기고 count를 줄입니다. 빈 칸과 찬 칸을 count로 구분하므로, 앞쪽에 비워진 자리를 다시 사용할 수 있습니다.',
        complexity='enqueue, dequeue, peek 모두 O(1), 저장 공간 O(capacity). 공간을 늘리지 않으므로 가득 찬 상태의 삽입은 실패합니다.',
        application='크기가 정해진 최근 이벤트 보관함이나 스트리밍 처리 버퍼에서 오래된 슬롯을 다시 사용할 때 유용합니다.',
        questions=[('용량 3에 10,20,30을 넣고 하나를 꺼낸 뒤 40을 넣으면 내부 배열의 어느 자리에 40이 들어가나요?', '첫 슬롯을 비운 뒤 다시 그 자리에 40을 쓴다. 논리적 꺼내기 순서는 20,30,40이다.'),
                   ('빈 큐와 가득 찬 큐를 어떻게 구별하나요?', 'count가 0이면 비어 있고 capacity와 같으면 가득 찬 상태다. head 위치만으로는 두 상태를 구별할 수 없다.')],
        requirements=['`CircularQueue` 생성자는 양의 정수 `capacity`를 받습니다. `enqueue(value): boolean`, `dequeue(): number | undefined`, `peek(): number | undefined`, `size(): number`를 구현하세요.',
                      '가득 차면 `enqueue`는 `false`이고 상태는 유지됩니다. 빈 큐에서 `dequeue`와 `peek`는 `undefined`입니다.'],
        starter='''class CircularQueue {
  constructor(capacity: number) {}
  enqueue(value: number): boolean { return false; }
  dequeue(): number | undefined { return undefined; }
  peek(): number | undefined { return undefined; }
  size(): number { return 0; }
}''',
        reference='''class CircularQueue {
  private data: (number | undefined)[];
  private head = 0;
  private count = 0;
  constructor(private capacity: number) { this.data = Array(capacity); }
  enqueue(value: number): boolean {
    if (this.count === this.capacity) return false;
    this.data[(this.head + this.count) % this.capacity] = value;
    this.count++;
    return true;
  }
  dequeue(): number | undefined {
    if (this.count === 0) return undefined;
    const value = this.data[this.head];
    this.data[this.head] = undefined;
    this.head = (this.head + 1) % this.capacity;
    this.count--;
    return value;
  }
  peek(): number | undefined { return this.count ? this.data[this.head] : undefined; }
  size(): number { return this.count; }
}''',
        public_tests='''const q = new CircularQueue(3);
assertEqual(q.enqueue(10), true); assertEqual(q.enqueue(20), true); assertEqual(q.enqueue(30), true);
assertEqual(q.dequeue(), 10); assertEqual(q.enqueue(40), true);
assertEqual([q.dequeue(), q.dequeue(), q.dequeue()], [20,30,40]);''',
        hidden_tests='''const q = new CircularQueue(2);
assertEqual(q.dequeue(), undefined); assertEqual(q.peek(), undefined);
assertEqual(q.enqueue(0), true); assertEqual(q.enqueue(-2), true); assertEqual(q.enqueue(99), false);
assertEqual(q.size(), 2); assertEqual(q.peek(), 0);
assertEqual(q.dequeue(), 0); assertEqual(q.enqueue(7), true);
assertEqual(q.dequeue(), -2); assertEqual(q.dequeue(), 7); assertEqual(q.size(), 0);
const single = new CircularQueue(1);
assertEqual(single.enqueue(4), true); assertEqual(single.dequeue(), 4);
assertEqual(single.enqueue(5), true); assertEqual(single.peek(), 5);''',
        mutations=[('가득 찬 상태', 'if (this.count === this.capacity) return false;', 'if (this.count > this.capacity) return false;'),
                   ('되감기', 'this.head = (this.head + 1) % this.capacity;', 'this.head = this.head + 1;')],
        visualization='circular-queue', prerequisites=['queue'], difficulty='보통',
        reading={
            'invariant': 'count개의 유효 원소는 head부터 시계 방향으로 연속된 슬롯에 있습니다.',
            'steps': [['저장 위치를 계산한다', '맨 뒤 슬롯은 (head + count) % capacity로 계산합니다. 끝을 넘으면 0으로 돌아옵니다.'],
                      ['앞 값을 꺼낸다', 'head가 가리키는 값을 읽고 슬롯을 비운 다음 head를 다음 슬롯로 옮깁니다.'],
                      ['빈 슬롯을 재사용한다', '앞에서 비운 자리에 새 값을 넣어도 논리적 FIFO 순서는 유지됩니다.']],
            'pitfall': 'head와 tail이 같은 값인 상황은 빈 상태와 가득 찬 상태 모두에서 생길 수 있습니다. count나 별도 플래그가 필요합니다.',
            'tradeoff': '고정 크기라 각 연산은 O(1)이지만, 가득 찬 뒤 자동 확장하지 않습니다. 확장이 필요한 일반 큐와 용도가 다릅니다.',
            'case_study': '센서가 최근 측정값만 보관한다면 고정 공간 버퍼를 사용할 수 있습니다. 이 실습은 가득 차면 덮어쓰지 않고 삽입을 거절합니다.',
            'experiment': '용량 3을 모두 채운 뒤 하나를 빼고 다시 넣어보세요. 새 값은 어느 슬롯에 저장되나요?'},
        hints=['가득 찬 상태에서 추가로 넣으면 기존 값이 바뀌지 않는지 확인하세요.',
               '앞에서 하나 제거하고 새 값을 넣으면 배열의 첫 슬롯을 다시 사용할 수 있는지 확인하세요.'],
        visual_frames=[
            frame(row(['∅']*3), '세 슬롯이 모두 비어 있습니다.', 'head = 0, count = 0이며 새 값의 위치는 0입니다.', 'capacity = 3'),
            frame(row([10,20,30], (0,)), '10, 20, 30을 차례대로 넣었습니다.', '가득 찬 상태에서는 추가 삽입이 실패하고 값은 유지됩니다.', 'head = 0; count = 3'),
            frame(row(['∅',20,30], (1,)), '10을 꺼내고 head를 옮깁니다.', '슬롯 0은 비었지만 FIFO에서 다음 값은 20입니다.', 'head = 1; count = 2'),
            frame(row([40,20,30], (0,)), '40을 처음 슬롯에 다시 씁니다.', '삽입 위치는 (head + count) % 3 = 0입니다. 논리적 순서는 20, 30, 40입니다.', '(1 + 2) % 3 = 0'),
            frame(row([40,20,30], (1,)), '다음에 꺼낼 값은 20입니다.', '물리적 슬롯 순서와 논리적 큐 순서는 다릅니다.', 'dequeue() → 20')]),
]

CORE_LESSONS.extend([
    dict(
        id='string-codepoints', title='문자열 · 코드 포인트 순회', group='자료구조',
        summary='문자열을 앞뒤로 읽으며 코드 포인트 단위로 순서를 뒤집습니다.',
        concept='JavaScript 문자열의 인덱스는 UTF-16 코드 단위입니다. 화면에 한 글자로 보이는 일부 문자는 두 코드 단위를 쓰므로 text[i]로 순회해 뒤집으면 문자가 깨질 수 있습니다. Array.from(text)는 코드 포인트 단위로 순회합니다. 다만 결합 문자나 이모지 조합을 하나의 사용자 인식 글자로 묶는 기능은 아닙니다.',
        complexity='코드 포인트 수 n에 대해 시간 O(n), 새 배열과 반환 문자열에 추가 공간 O(n).',
        application='입력 문자를 한 개씩 검사하는 파서나 정규화 전 처리에서 순회 단위가 무엇인지 분명히 해야 합니다.',
        questions=[('이모지 한 개를 text[i]로 뒤집으면 왜 깨질 수 있나요?', '일부 문자는 UTF-16 코드 단위 두 개로 표현된다. 인덱스로 각각을 옮기면 서로 분리될 수 있다.'),
                   ('Array.from으로 뒤집어도 사용자에게 보이는 모든 글자 묶음이 유지되나요?', '아니다. 코드 포인트는 결합 문자나 여러 코드 포인트로 이뤄진 이모지 조합과 다르다.')],
        requirements=['`reverseCodePoints(text: string): string`을 구현하세요.',
                      '코드 포인트 단위로 순서를 뒤집습니다. 결합 문자 단위 처리는 이 단원의 범위가 아닙니다.'],
        starter="function reverseCodePoints(text: string): string { return ''; }",
        reference='''function reverseCodePoints(text: string): string {
  return Array.from(text).reverse().join('');
}''',
        public_tests="assertEqual(reverseCodePoints('abc'), 'cba'); assertEqual(reverseCodePoints(''), '');",
        hidden_tests="assertEqual(reverseCodePoints('A😀B'), 'B😀A'); assertEqual(reverseCodePoints('가나'), '나가'); assertEqual(reverseCodePoints('aa'), 'aa'); assertEqual(reverseCodePoints('🙂'), '🙂');",
        mutations=[('인덱스 순회', 'Array.from(text)', 'text.split(\'\')'),
                   ('뒤집기 누락', '.reverse().join', '.join')],
        visualization='string-codepoints', prerequisites=['array-rotation'], difficulty='입문',
        sources=[{'title':'MDN · Array.from', 'url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/from'},
                 {'title':'MDN · String iterator', 'url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/Symbol.iterator'}],
        reading={
            'invariant': '순회로 얻은 각 코드 포인트는 결과에 정확히 한 번 등장합니다.',
            'steps': [['순회 단위를 확인한다', 'A, 😀, B를 인덱스로 보면 😀는 내부 코드 단위 두 개로 나뉩니다.'],
                      ['코드 포인트 배열을 만든다', 'Array.from으로 [A, 😀, B]를 얻습니다.'],
                      ['순서를 바꾸어 연결한다', '[B, 😀, A]를 이어서 결과를 만듭니다.']],
            'pitfall': 'split(\'\')은 UTF-16 코드 단위로 분리합니다. Array.from도 결합 문자를 완전한 글자 묶음으로 인식하지는 않습니다.',
            'tradeoff': '배열을 만들기 때문에 추가 메모리가 필요합니다. 코드 포인트 단위의 정확한 범위를 요구사항에 밝히는 것이 중요합니다.',
            'case_study': '입력 정제에서 글자 수를 제한할 때 코드 단위와 사용자에게 보이는 글자 수를 혼동하면 예상과 다른 제한이 생깁니다.',
            'experiment': 'A😀B와 결합 악센트가 들어간 문자열을 각각 뒤집고, 어느 경우가 다르게 보이는지 비교하세요.'},
        hints=['영문자뿐 아니라 UTF-16에서 두 코드 단위를 쓰는 문자도 넣어보세요.',
               '입력이 빈 문자열일 때와 한 코드 포인트일 때 결과를 확인하세요.'],
        visual_frames=[
            frame(row(['A','😀','B']), '보이는 글자 세 개를 놓습니다.', '이 예시는 코드 포인트 세 개지만 UTF-16 코드 단위는 네 개입니다.'),
            frame(row(['A','😀','B'], (1,)), '가운데 문자를 한 단위로 순회합니다.', 'Array.from은 😀를 분리된 두 코드 단위로 다루지 않습니다.', "Array.from('A😀B')"),
            frame([{**node, 'x': 35 + (2-i)*105} for i,node in enumerate(row(['A','😀','B']))], '코드 포인트의 순서를 뒤집습니다.', '결과는 B😀A입니다. 가운데 문자는 깨지지 않습니다.', "reverse().join('')")]),
    dict(
        id='matrix-transpose', title='행렬 · 행과 열 바꾸기', group='자료구조',
        summary='직사각형 격자를 순회하며 행·열 인덱스를 교환합니다.',
        concept='행렬은 행마다 값을 담은 이중 배열로 표현할 수 있습니다. 전치에서는 원래 (row, column)의 값을 새 (column, row)에 둡니다. 원래 크기가 r×c이면 결과는 c×r입니다. 빈 행렬과 열이 0개인 행렬을 따로 다룹니다.',
        complexity='모든 원소를 한 번 읽어 시간 O(r×c), 새 행렬의 저장 공간 O(r×c). 출력 자체가 그만큼 필요합니다.',
        application='표에서 항목별 기록을 날짜별 기록으로 바꾸거나, 행 기준 데이터를 열 기준으로 계산할 때 사용합니다.',
        questions=[('2행 3열 행렬을 전치하면 크기와 각 값의 위치가 어떻게 달라지나요?', '3행 2열이 되고 원래 (row,column)의 값이 (column,row)로 옮겨진다.'),
                   ('빈 행렬에서는 왜 첫 행의 길이를 곧바로 읽으면 안 되나요?', '첫 행이 없으므로 접근 결과가 undefined다. 빈 입력을 먼저 확인해야 한다.')],
        requirements=['`transpose(matrix: number[][]): number[][]`를 구현하세요.',
                      '입력은 직사각형이며 빈 행렬도 허용합니다. 새 행렬을 반환하고 입력은 변경하지 마세요.'],
        starter='function transpose(matrix: number[][]): number[][] { return []; }',
        reference='''function transpose(matrix: number[][]): number[][] {
  if (matrix.length === 0) return [];
  const columns = matrix[0].length;
  return Array.from({ length: columns }, (_, col) => matrix.map(row => row[col]));
}''',
        public_tests='assertEqual(transpose([[1,2,3],[4,5,6]]), [[1,4],[2,5],[3,6]]); assertEqual(transpose([]), []);',
        hidden_tests='''const m = [[1,2],[3,4],[5,6]];
assertEqual(transpose(m), [[1,3,5],[2,4,6]]); assertEqual(m, [[1,2],[3,4],[5,6]]);
assertEqual(transpose([[]]), []); assertEqual(transpose([[0]]), [[0]]);
assertEqual(transpose([[7,7,8]]), [[7],[7],[8]]);''',
        mutations=[('행·열 혼동', 'matrix.map(row => row[col])', 'matrix.map(row => row[0])'),
                   ('열 개수', 'const columns = matrix[0].length;', 'const columns = matrix.length;')],
        visualization='matrix-transpose', prerequisites=['array-rotation'], difficulty='입문',
        reading={
            'invariant': '결과의 열 하나는 원본의 행 하나에 대응하며, 모든 원소가 그대로 한 번씩 옮겨집니다.',
            'steps': [['결과 크기를 정한다', '2행 3열을 전치하면 3행 2열의 새 격자를 만듭니다.'],
                      ['좌표를 교환한다', '원본 (0,2)의 값 3을 결과 (2,0)에 씁니다.'],
                      ['모든 칸에 반복한다', '원본의 모든 행과 열을 방문해 누락된 칸이 없는지 확인합니다.']],
            'pitfall': '정사각형 입력만 검사하면 결과 크기를 잘못 잡은 구현을 놓칩니다. 빈 행렬은 첫 행 접근 전에 처리해야 합니다.',
            'tradeoff': '새 행렬은 원본을 보존합니다. 정사각형 행렬에서는 제자리 교환도 가능하지만 직사각형에는 같은 접근을 바로 적용할 수 없습니다.',
            'case_study': '행이 날짜이고 열이 센서인 측정표를 전치하면 센서별 날짜 기록으로 볼 수 있습니다.',
            'experiment': '2×3과 3×2 표를 각각 전치하고 결과의 모양을 비교하세요.'},
        hints=['정사각형이 아닌 2×3 또는 3×2 입력을 사용하세요.', '빈 행렬과 열이 비어 있는 한 행을 구별해보세요.'],
        visual_frames=[
            frame(row([1,2,3], y=55)+[{**node, 'id': f'v{i+3}'} for i,node in enumerate(row([4,5,6], y=140))], '원본은 2행 3열입니다.', '위 행은 [1,2,3], 아래 행은 [4,5,6]입니다.'),
            frame(row([1,2,3], (2,), y=55)+[{**node, 'id': f'v{i+3}'} for i,node in enumerate(row([4,5,6], y=140))], '(0,2)의 값 3을 고릅니다.', '결과의 (2,0)에 들어갑니다.', 'result[col][row] = matrix[row][col]'),
            frame([{'id': f'v{i}', 'label': str(value), 'x': 40+(i//3)*105, 'y': 35+(i%3)*75, 'active': i==2} for i,value in enumerate([1,2,3,4,5,6])],
                  '행과 열이 서로 바뀌었습니다.', '세 행 [1,4], [2,5], [3,6]이 새 결과입니다.')]),
])

CORE_LESSONS.append(dict(
    id='hash-set', title='집합 · 중복 없이 보관하기', group='자료구조',
    summary='해시 충돌을 처리하며 문자열의 존재 여부를 저장합니다.',
    concept='Set은 값이 있는지와 중복이 없는지가 핵심입니다. 문자열을 해시해 버킷을 고르고, 같은 버킷 안에서도 원래 문자열을 비교합니다. 서로 다른 문자열이 같은 해시를 가질 수 있기 때문입니다. 같은 값을 다시 넣으면 크기는 늘지 않습니다.',
    complexity='고정 8개 버킷을 쓰므로 삽입·조회·삭제는 충돌이 많으면 O(n), 전체 저장 공간 O(n)입니다. 버킷 수를 데이터와 함께 늘리고 해시가 고르게 퍼지면 평균 O(1)에 가까워집니다.',
    application='이미 처리한 이벤트 ID를 저장하면 같은 이벤트를 두 번 처리하지 않을 수 있습니다. 아이디가 없는 상태와 빈 문자열 아이디는 구분해야 합니다.',
    questions=[('서로 다른 두 문자열의 해시가 같은 버킷을 가리키면 어떻게 하나요?', '같은 버킷 안에 각각 보관하고 원래 문자열까지 비교한다.'),
               ('같은 값을 다시 넣거나 없는 값을 삭제하면 크기가 어떻게 되나요?', '중복 삽입과 없는 값 삭제 모두 크기를 바꾸지 않는다.')],
    requirements=['문자열 전용 `StringSet`: `add(value): boolean`, `has(value): boolean`, `delete(value): boolean`, `size(): number`를 구현하세요.',
                  '새 값 추가만 `true`, 기존 값 추가와 없는 값 삭제는 `false`입니다. 제공된 `bucketIndex`를 사용하세요.'],
    starter='''function bucketIndex(value: string): number { return Array.from(value).reduce((n, ch) => n + ch.codePointAt(0)!, 0) % 8; }
class StringSet {
  add(value: string): boolean { return false; }
  has(value: string): boolean { return false; }
  delete(value: string): boolean { return false; }
  size(): number { return 0; }
}''',
    reference='''function bucketIndex(value: string): number { return Array.from(value).reduce((n, ch) => n + ch.codePointAt(0)!, 0) % 8; }
class StringSet {
  private buckets: string[][] = Array.from({ length: 8 }, () => []);
  private count = 0;
  add(value: string): boolean {
    const bucket = this.buckets[bucketIndex(value)];
    if (bucket.includes(value)) return false;
    bucket.push(value); this.count++; return true;
  }
  has(value: string): boolean { return this.buckets[bucketIndex(value)].includes(value); }
  delete(value: string): boolean {
    const bucket = this.buckets[bucketIndex(value)];
    const index = bucket.indexOf(value);
    if (index < 0) return false;
    bucket.splice(index, 1); this.count--; return true;
  }
  size(): number { return this.count; }
}''',
    public_tests="const s = new StringSet(); assertEqual(s.add('a'),true); assertEqual(s.add('i'),true); assertEqual(s.add('a'),false); assertEqual(s.size(),2); assertEqual(s.has('i'),true);",
    hidden_tests="""const s = new StringSet();
assertEqual(s.has(''),false); assertEqual(s.add(''),true); assertEqual(s.add('__proto__'),true);
assertEqual(s.delete('missing'),false); assertEqual(s.delete(''),true); assertEqual(s.has('__proto__'),true);
assertEqual(s.add('a'),true); assertEqual(s.add('i'),true); assertEqual(s.delete('a'),true);
assertEqual(s.has('i'),true); assertEqual(s.size(),2);
assertEqual(new StringSet().size(),0);""",
    mutations=[('중복 크기', 'if (bucket.includes(value)) return false;', 'if (bucket.includes(value)) { this.count++; return false; }'),
               ('충돌 처리', 'bucket.push(value); this.count++; return true;', 'bucket.length = 0; bucket.push(value); this.count++; return true;')],
    visualization='hash-set', prerequisites=['dictionary'], difficulty='보통',
    sources=[{'title':'MDN · Set', 'url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set'},
             {'title':'MIT 6.006 · 강의 자료', 'url':'https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/'}],
    reading={
        'invariant': '각 문자열은 계산된 버킷에 최대 한 번만 들어가고, count는 저장된 서로 다른 문자열 수입니다.',
        'steps': [['버킷을 정한다', '문자의 코드 포인트 값을 합해 8로 나눈 나머지를 버킷 번호로 씁니다.'],
                  ['원래 값을 비교한다', 'a와 i는 같은 버킷을 쓰지만 다른 문자열이므로 둘 다 보관합니다.'],
                  ['중복과 삭제를 처리한다', '이미 있는 값은 추가하지 않고, 삭제할 때 같은 버킷의 다른 값은 남깁니다.']],
        'pitfall': '해시값이 같다고 값까지 같은 것은 아닙니다. 버킷 하나당 값 하나만 두면 충돌로 데이터가 사라집니다.',
        'tradeoff': '고정 버킷 8개는 충돌 실습에 좋지만 데이터가 많아질수록 느려집니다. 실제 구현은 부하에 따라 크기를 조정합니다.',
        'case_study': '중복 등록 방지에 사용자 ID 집합을 사용할 수 있습니다. 이 실습은 문자열 존재만 저장하고 별도 사용자 데이터는 보관하지 않습니다.',
        'experiment': 'a와 i가 같은 버킷에 들어간 뒤 a만 삭제해보세요. i가 남아 있는지 살펴보세요.'},
    hints=['충돌하는 서로 다른 값 두 개를 넣고 하나를 삭제해보세요. 다른 값은 남나요?',
           '같은 값을 두 번 넣어도 size가 증가하지 않는지 확인하세요.'],
    visual_frames=[
        frame([{'id':'bucket','label':'#1','x':160,'y':30}], '버킷 1을 준비합니다.', 'a와 i는 문자 코드 합을 8로 나누면 모두 이 버킷에 도착합니다.'),
        frame([{'id':'bucket','label':'#1','x':160,'y':30}, {'id':'a','label':'a','x':95,'y':150,'active':True}], 'a를 저장합니다.', '버킷이 비어 있어 새 문자열을 넣고 크기가 1이 됩니다.', "add('a') → true"),
        frame([{'id':'bucket','label':'#1','x':160,'y':30}, {'id':'a','label':'a','x':95,'y':150}, {'id':'i','label':'i','x':205,'y':150,'active':True}],
              '같은 버킷에 i도 저장합니다.', '해시 충돌은 값 충돌과 다릅니다. 원래 문자열을 비교하면 a와 i는 다릅니다.', "add('i') → true"),
        frame([{'id':'bucket','label':'#1','x':160,'y':30}, {'id':'i','label':'i','x':205,'y':150,'active':True}],
              'a만 삭제합니다.', '버킷을 통째로 비우지 않습니다. i는 여전히 존재합니다.', "delete('a') → true; has('i') → true")],
))
