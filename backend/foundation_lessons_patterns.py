"""Authored interview-pattern, method and maths lessons."""
from .foundation_lessons_core import frame, row


def guide(invariant, steps, pitfall, tradeoff, case_study, experiment):
    return dict(invariant=invariant, steps=steps, pitfall=pitfall, tradeoff=tradeoff,
                case_study=case_study, experiment=experiment)


def scenes(*states):
    return [frame(row(values, active), note, detail, code) for values, active, note, detail, code in states]


PATTERN_LESSONS = [
    dict(
        id='lower-bound', title='경계 이진 탐색 · 첫 위치 찾기', group='알고리즘',
        summary='정렬된 값에서 목표 이상이 처음 나오는 위치를 찾습니다.',
        concept='lower bound는 정렬된 배열에서 target 이상인 첫 인덱스입니다. 없는 값도 삽입 위치로 표현하므로 답은 0부터 length까지 가능합니다. 탐색 범위를 [left,right)로 잡고, 중간 값이 target보다 작으면 그 위치까지 버립니다. 그렇지 않으면 중간 위치를 답 후보로 남깁니다.',
        complexity='한 번 비교할 때 남는 구간이 절반 이하가 되어 시간 O(log n), 추가 공간 O(1). 이 단원은 제공된 valueAt 호출 횟수도 검사합니다.',
        application='정렬된 가격 목록에서 최소 조건을 만족하는 첫 항목을 찾거나, 새 값을 넣을 정렬 위치를 찾습니다.',
        questions=[('목표값이 배열에 없으면 무엇을 반환하나요?', '목표 이상이 처음 나타나는 위치, 즉 정렬 순서를 유지할 삽입 위치를 반환한다. 모두 작으면 length다.'),
                   ('중간 값이 목표와 같을 때 왜 탐색을 멈추지 않나요?', '더 왼쪽에 같은 값이 있을 수 있으므로 right를 middle로 바꿔 첫 위치를 계속 찾는다.')],
        requirements=['`lowerBound(length: number, valueAt: (index: number) => number, target: number): number`를 구현하세요.',
                      '값은 오름차순이며 `valueAt`은 유효한 인덱스에서만 호출하세요. 첫 목표 이상 위치 또는 `length`를 반환하세요.'],
        starter='function lowerBound(length: number, valueAt: (index: number) => number, target: number): number { return 0; }',
        reference='''function lowerBound(length: number, valueAt: (index: number) => number, target: number): number {
  let left = 0, right = length;
  while (left < right) {
    const middle = left + Math.floor((right - left) / 2);
    if (valueAt(middle) < target) left = middle + 1;
    else right = middle;
  }
  return left;
}''',
        public_tests='''const a=[1,3,3,7];
assertEqual(lowerBound(a.length,i=>a[i],3),1);
assertEqual(lowerBound(a.length,i=>a[i],4),3);''',
        hidden_tests='''const a=[1,3,3,7];
assertEqual(lowerBound(0,()=>{throw Error('empty read')},3),0);
assertEqual(lowerBound(a.length,i=>a[i],0),0);
assertEqual(lowerBound(a.length,i=>a[i],9),4);
assertEqual(lowerBound(a.length,i=>a[i],3),1);
assertEqual(lowerBound(1,i=>[5][i],5),0);''',
        cost_tests='''const a=Array.from({length:4096},(_,i)=>i*2);
let reads=0;
const result=lowerBound(a.length,i=>{reads++; return a[i];},777);
assertEqual(result,389); assertEqual(reads<=13,true);''',
        mutations=[('중복 경계', 'valueAt(middle) < target', 'valueAt(middle) <= target'),
                   ('삽입 위치', 'return left;', 'return Math.min(left+1,length);')],
        visualization='lower-bound', prerequisites=['binary-search'], difficulty='보통',
        reading=guide('답 후보는 항상 [left,right] 안에 있으며 left 왼쪽의 값은 모두 target보다 작습니다.',
            [['구간을 반열림으로 둔다','처음에는 전체 범위 [0,length)를 탐색합니다.'],['중간을 비교한다','중간 값이 작으면 왼쪽 절반을 버리고, 같거나 크면 오른쪽 경계를 중간으로 좁힙니다.'],['경계가 만나면 끝낸다','left와 right가 같아질 때 그 인덱스가 첫 target 이상 값의 위치입니다.']],
            '중간 값과 같다고 바로 반환하면 중복의 첫 위치를 놓칩니다. 값이 모두 작으면 length를 반환해야 합니다.',
            '정렬이 전제라서 O(log n)입니다. 정렬되지 않았다면 이진 탐색으로 올바른 위치를 찾을 수 없습니다.',
            '정렬된 시간표에서 원하는 시각 이후 첫 예약을 찾을 때 사용합니다.',
            '1,3,3,7에서 3과 4를 찾고 경계가 어떻게 이동하는지 비교하세요.'),
        hints=['중복된 목표값이 여럿 있을 때 첫 위치를 찾는지 확인하세요.', '모든 값보다 큰 목표와 빈 입력을 함께 검증하세요.'],
        visual_frames=scenes(
            ([1,3,3,7],(), '전체 구간 [0,4)에서 시작합니다.','찾는 값은 3입니다. 오른쪽 경계 4는 배열 밖 위치입니다.','left=0; right=4'),
            ([1,3,3,7],(2,), '중간 인덱스 2의 값 3을 봅니다.','같은 값이 왼쪽에도 있을 수 있어 [0,2)로 줄입니다.','right=2'),
            ([1,3,3,7],(1,), '중간 인덱스 1도 값 3입니다.','[0,1)로 줄여 더 앞의 같은 값이 있는지 봅니다.','right=1'),
            ([1,3,3,7],(0,), '중간 인덱스 0의 값 1은 작습니다.','왼쪽 경계를 1로 옮기면 두 경계가 만납니다.','left=1'),
            ([1,3,3,7],(1,), '첫 3의 위치는 1입니다.','값이 없는 목표 4를 찾으면 삽입 위치 3을 반환합니다.','return 1'))),
    dict(
        id='two-sum', title='두 수의 합 · 보수 찾기', group='알고리즘',
        summary='앞에서 본 값의 위치를 기억해 한 번의 순회로 두 인덱스를 찾습니다.',
        concept='현재 값 x와 합이 target이 되려면 이전에 target-x가 있어야 합니다. Map에 이미 본 값과 인덱스를 저장하고, 현재 원소를 저장하기 전에 보수를 조회합니다. 이렇게 해야 같은 원소를 두 번 사용하지 않습니다. 조건을 만족하는 쌍이 여러 개라면 어느 한 쌍이든 정답입니다.',
        complexity='해시 조회의 평균 비용이 O(1)이면 시간 O(n), Map 저장 공간 O(n). 해시 구현의 병목이나 충돌에 따라 최악 성능은 달라질 수 있습니다.',
        application='거래 두 건을 조합해 정해진 금액을 만드는 간단한 후보 검색에 활용할 수 있습니다.',
        questions=[('현재 값을 Map에 넣기 전에 보수를 찾는 이유는 무엇인가요?', '같은 배열 원소를 두 번 쓰는 것을 막기 위해서다.'),
                   ('답이 여러 쌍인 입력에서는 무엇을 검사해야 하나요?', '특정 인덱스 쌍과 똑같은지가 아니라 서로 다른 유효 인덱스이고 두 값의 합이 target인지 검사한다.')],
        requirements=['`twoSum(values: number[], target: number): [number, number] | null`을 구현하세요.',
                      '서로 다른 두 인덱스 i<j를 반환합니다. 가능한 답이 여러 개면 아무 쌍이나 허용합니다. 답이 없으면 null입니다.'],
        starter='function twoSum(values: number[], target: number): [number, number] | null { return null; }',
        reference='''function twoSum(values: number[], target: number): [number, number] | null {
  const seen = new Map<number, number>();
  for (let i = 0; i < values.length; i++) {
    const previous = seen.get(target - values[i]);
    if (previous !== undefined) return [previous, i];
    seen.set(values[i], i);
  }
  return null;
}''',
        public_tests='''assertEqual(twoSum([2,7,11],9),[0,1]);
assertEqual(twoSum([4],8),null);''',
        hidden_tests='''const values=[3,3,6,0]; const pair=twoSum(values,6);
assertEqual(pair!==null,true);
if (pair) { assertEqual(pair[0]<pair[1],true); assertEqual(values[pair[0]]+values[pair[1]],6); }
assertEqual(twoSum([0,4],4),[0,1]);
assertEqual(twoSum([-2,5,1],3),[0,1]);
assertEqual(twoSum([1,2,3],99),null);''',
        mutations=[('인덱스 0', 'previous !== undefined', 'Boolean(previous)'),
                   ('같은 원소 재사용', 'seen.set(values[i], i);', 'seen.set(values[i], i); if (values[i]*2===target) return [i,i];')],
        visualization='two-sum', prerequisites=['dictionary'], difficulty='입문',
        reading=guide('seen에는 현재 인덱스보다 앞에 있는 원소만 저장됩니다.',
            [['보수를 계산한다','현재 값 x의 짝은 target-x입니다.'],['먼저 조회한다','앞에서 본 값에 짝이 있으면 해당 인덱스와 현재 인덱스를 반환합니다.'],['그다음 저장한다','아직 짝이 없으면 현재 값을 다음 원소를 위해 저장합니다.']],
            'Map.get의 결과가 0인 인덱스일 수 있으므로 truthy 검사로 존재 여부를 판단하면 안 됩니다.',
            'Map을 쓰면 공간을 O(n) 사용해 중첩 반복문의 O(n²) 시간을 평균 O(n)으로 바꿉니다.',
            '두 거래의 합이 결제액과 같은 후보를 빠르게 찾을 수 있습니다.',
            '동일한 값 두 개와 한 개만 있을 때를 비교해보세요.'),
        hints=['첫 번째 원소가 답인 경우를 시험해보세요. 인덱스 0을 잘 처리하나요?',
               '값 하나만 있을 때 자기 자신을 두 번 사용하지 않는지 확인하세요.'],
        visual_frames=scenes(
            ([2,7,11],(0,), '목표 합 9에서 2의 짝은 7입니다.','앞에서 본 값이 없으므로 2의 위치 0을 저장합니다.','seen.set(2,0)'),
            ([2,7,11],(1,), '7의 짝은 2입니다.','이미 저장한 2의 위치 0을 찾았습니다.','seen.get(9-7) → 0'),
            ([2,7,11],(0,1), '인덱스 [0,1]을 반환합니다.','서로 다른 두 위치이고 2+7=9입니다.','return [0,1]'))),
    dict(
        id='sliding-window-sum', title='슬라이딩 윈도 · 구간 합', group='알고리즘',
        summary='고정 길이 구간을 한 칸씩 옮기며 최대 합을 찾습니다.',
        concept='길이 k인 연속 구간의 합을 처음 한 번 계산합니다. 이후 오른쪽으로 한 칸 이동할 때 왼쪽에서 빠진 값은 빼고 오른쪽에 들어온 값은 더합니다. 각 구간을 처음부터 다시 더하지 않아도 됩니다. k가 0이거나 배열보다 길면 유효한 구간이 없습니다.',
        complexity='첫 구간 계산 O(k), 이후 n-k번 이동하여 총 시간 O(n), 추가 공간 O(1). 모든 구간을 다시 합산하면 O(nk)입니다.',
        application='최근 7일 매출 합의 최댓값처럼 길이가 고정된 기간을 비교할 때 사용합니다.',
        questions=[('구간을 한 칸 옮길 때 합을 어떻게 갱신하나요?', '이전 합에서 빠지는 왼쪽 값을 빼고 새로 들어오는 오른쪽 값을 더한다.'),
                   ('음수가 있어도 초기 최댓값을 0으로 두면 되나요?', '안 된다. 모든 값이 음수라면 실제 최댓값도 음수이므로 첫 유효 구간 합으로 시작한다.')],
        requirements=['`maxWindowSum(values: number[], size: number): number | undefined`를 구현하세요.',
                      '`size`는 0 이상의 정수입니다. 0이거나 배열 길이보다 크면 undefined를 반환하세요.'],
        starter='function maxWindowSum(values: number[], size: number): number | undefined { return undefined; }',
        reference='''function maxWindowSum(values: number[], size: number): number | undefined {
  if (size === 0 || size > values.length) return undefined;
  let sum = 0;
  for (let i = 0; i < size; i++) sum += values[i];
  let best = sum;
  for (let right = size; right < values.length; right++) {
    sum += values[right] - values[right - size];
    if (sum > best) best = sum;
  }
  return best;
}''',
        public_tests='assertEqual(maxWindowSum([2,1,5,1,3],2),6); assertEqual(maxWindowSum([],1),undefined);',
        hidden_tests='''assertEqual(maxWindowSum([-5,-2,-8],2),-7);
assertEqual(maxWindowSum([1,2,3],3),6); assertEqual(maxWindowSum([1,2],0),undefined);
assertEqual(maxWindowSum([1,2],3),undefined); assertEqual(maxWindowSum([0,0,0],1),0);''',
        mutations=[('빠진 값', 'values[right - size]', 'values[right - size + 1]'),
                   ('음수 구간', 'let best = sum;', 'let best = 0;')],
        visualization='sliding-window-sum', prerequisites=['array-rotation'], difficulty='입문',
        reading=guide('현재 sum은 항상 정확히 size개 연속 원소의 합입니다.',
            [['첫 구간을 더한다','[2,1]의 합 3을 초기 합과 최댓값으로 둡니다.'],['창을 이동한다','2를 빼고 5를 더하면 [1,5]의 합 6이 됩니다.'],['최댓값을 갱신한다','이동할 때마다 새 합과 지금까지의 최댓값을 비교합니다.']],
            '음수만 있는 입력에서 최댓값을 0으로 초기화하면 실제로 존재하지 않는 구간을 답으로 냅니다.',
            '고정 길이의 모든 구간을 각각 다시 더하는 O(nk) 방법보다 갱신 연산을 재사용합니다.',
            '일정 기간 동안 가장 바빴던 연속 날짜를 찾을 때 사용할 수 있습니다.',
            '모두 음수인 입력과 size가 전체 길이인 입력을 시험하세요.'),
        hints=['모두 음수인 배열에서 반환값이 0으로 바뀌지 않는지 확인하세요.',
               '두 번째 창으로 이동할 때 어떤 원소가 빠지고 어떤 원소가 들어오는지 테스트하세요.'],
        visual_frames=scenes(
            ([2,1,5,1,3],(0,1),'첫 두 값을 더합니다.','현재 창 [2,1]의 합은 3입니다.','sum=3; best=3'),
            ([2,1,5,1,3],(1,2),'한 칸 오른쪽으로 이동합니다.','2를 빼고 5를 더해 [1,5]의 합 6을 만듭니다.','sum=3-2+5=6'),
            ([2,1,5,1,3],(2,3),'다음 창은 [5,1]입니다.','1을 빼고 다음 1을 더해 합은 여전히 6입니다.','sum=6-1+1=6'),
            ([2,1,5,1,3],(3,4),'마지막 창은 [1,3]입니다.','합 4보다 지금까지의 최댓값 6이 큽니다.','return 6'))),
]

PATTERN_LESSONS.extend([
    dict(
        id='prefix-sums', title='누적합 · 구간을 한 번에 계산', group='알고리즘',
        summary='앞에서부터 합을 저장해 여러 구간의 합을 빠르게 구합니다.',
        concept='prefix[i]를 처음 i개 원소의 합으로 정의하면 prefix[0]=0입니다. [start,end) 구간의 합은 prefix[end]-prefix[start]입니다. 처음에 전체 배열을 한 번 순회해 누적합을 만들면 각 질의마다 구간을 다시 더하지 않아도 됩니다.',
        complexity='전처리 O(n), 질의 q개를 처리하는 시간 O(q), 추가 공간 O(n+q)이며 그중 결과 배열 O(q)는 출력입니다.',
        application='날짜별 매출의 누적 총계를 저장해 임의 기간 합을 반복해서 조회할 수 있습니다.',
        questions=[('[1,2,3]의 prefix 배열은 무엇이고 [1,3)의 합은 어떻게 구하나요?', 'prefix는 [0,1,3,6]이고 prefix[3]-prefix[1]=5다.'),
                   ('질의가 많을 때 매번 구간을 직접 더하는 방식과 어떤 차이가 있나요?', '한 번 O(n)으로 전처리하면 각 질의는 두 누적값을 빼는 O(1) 연산으로 처리한다.')],
        requirements=['`rangeSums(values: number[], queries: [number, number][]): number[]`를 구현하세요.',
                      '각 질의는 유효한 반열림 구간 [start,end)입니다. 원본과 질의 배열은 변경하지 마세요.'],
        starter='function rangeSums(values: number[], queries: [number, number][]): number[] { return []; }',
        reference='''function rangeSums(values: number[], queries: [number, number][]): number[] {
  const prefix = [0];
  for (const value of values) prefix.push(prefix[prefix.length - 1] + value);
  return queries.map(([start, end]) => prefix[end] - prefix[start]);
}''',
        public_tests='assertEqual(rangeSums([1,2,3],[[1,3],[0,3]]),[5,6]); assertEqual(rangeSums([],[[0,0]]),[0]);',
        hidden_tests='''const a=[-2,0,5,-1];
assertEqual(rangeSums(a,[[0,0],[0,1],[1,4],[2,3],[0,4]]),[0,-2,4,5,2]);
assertEqual(a,[-2,0,5,-1]); assertEqual(rangeSums([7],[]),[]);''',
        mutations=[('왼쪽 경계', 'prefix[end] - prefix[start]', 'prefix[end] - prefix[start + 1]'),
                   ('누적 갱신', 'prefix.push(prefix[prefix.length - 1] + value)', 'prefix.push(value)')],
        visualization='prefix-sums', prerequisites=['array-rotation'], difficulty='입문',
        reading=guide('prefix[i]는 항상 values의 인덱스 0부터 i-1까지의 합입니다.',
            [['0을 먼저 둔다','빈 구간의 합 prefix[0]=0으로 시작합니다.'],['앞에서부터 쌓는다','1,2,3을 지나면 [0,1,3,6]이 됩니다.'],['앞부분을 뺀다','[1,3)은 처음 3개의 합 6에서 처음 1개의 합 1을 빼 5입니다.']],
            '끝 인덱스를 포함하는지 불명확하면 한 칸 오류가 생깁니다. 이 단원은 [start,end)이며 빈 구간도 합이 0입니다.',
            '질의가 한 번뿐이면 전처리가 이점이 없지만 여러 질의에는 반복 합산을 줄입니다.',
            '매출 기록을 쌓아 두고 임의 기간의 합을 반복 조회할 때 쓰입니다.',
            '[0,0), [0,n), [1,n) 구간을 각각 계산해보세요.'),
        hints=['빈 구간과 전체 구간을 모두 질의해보세요.', '음수가 포함되어도 두 누적값의 차가 맞는지 확인하세요.'],
        visual_frames=scenes(
            ([1,2,3],(), '원본 값 [1,2,3]을 준비합니다.','누적합은 원소 사이의 경계마다 기록합니다.','prefix[0]=0'),
            ([0,1,3,6],(1,2,3), '누적합 [0,1,3,6]을 만듭니다.','인덱스 i는 처음 i개 원소의 합을 나타냅니다.','prefix[i+1]=prefix[i]+values[i]'),
            ([0,1,3,6],(1,3), '[1,3) 구간을 조회합니다.','prefix[3]=6에서 prefix[1]=1을 빼면 5입니다.','6-1=5'))),
    dict(
        id='gcd', title='최대공약수 · 나머지로 줄이기', group='수학',
        summary='두 수의 공약수 문제를 더 작은 두 수로 반복해서 바꿉니다.',
        concept='유클리드 알고리즘은 gcd(a,b)=gcd(b,a%b)를 이용합니다. 나머지가 0이 될 때 남은 수가 최대공약수입니다. 한 수가 0이면 다른 수가 답이며, 이 단원에서는 gcd(0,0)=0으로 정합니다.',
        complexity='나머지 연산 횟수는 O(log min(a,b)) 수준이며 추가 공간 O(1)입니다. 정수 계산 비용은 고정 크기 숫자 범위라고 가정합니다.',
        application='분수를 기약분수로 줄이거나 두 반복 주기의 공통 단위를 구할 때 사용합니다.',
        questions=[('gcd(48,18)은 어떤 나머지 순서로 구하나요?', '(48,18)→(18,12)→(12,6)→(6,0)이므로 6이다.'),
                   ('한 수가 0이거나 둘 다 0일 때는 어떻게 하나요?', '나머지 반복이 끝나고 남은 수를 반환한다. 이 단원에서는 gcd(0,0)=0이다.')],
        requirements=['`gcd(a: number, b: number): number`를 구현하세요.', '입력은 0 이상의 안전한 정수이며 gcd(0,0)은 0입니다.'],
        starter='function gcd(a: number, b: number): number { return 0; }',
        reference='''function gcd(a: number, b: number): number {
  while (b !== 0) {
    const next = a % b;
    a = b; b = next;
  }
  return a;
}''',
        public_tests='assertEqual(gcd(48,18),6); assertEqual(gcd(7,0),7);',
        hidden_tests='assertEqual(gcd(0,0),0); assertEqual(gcd(0,9),9); assertEqual(gcd(18,48),6); assertEqual(gcd(13,17),1); assertEqual(gcd(12,12),12);',
        mutations=[('나머지 계산', 'const next = a % b;', 'const next = Math.floor(a / b);'),
                   ('반복 종료', 'return a;', 'return b;')],
        visualization='gcd', prerequisites=[], difficulty='입문',
        reading=guide('매 단계의 두 수는 처음 입력과 최대공약수가 같습니다.',
            [['큰 문제를 줄인다','48을 18로 나눈 나머지 12를 구합니다.'],['두 수를 바꾼다','이제 (18,12)에 같은 규칙을 적용합니다.'],['0이 되면 끝낸다','(6,0)에 도착하면 6을 반환합니다.']],
            '몫을 다음 수로 넣거나 0으로 나머지를 계산하면 안 됩니다. 처음부터 b가 0일 수 있습니다.',
            '모든 약수를 검사하는 방법보다 빠르게 나머지 연산만 반복합니다.',
            '분모와 분자의 최대공약수로 양쪽을 나누면 분수를 간단하게 표현할 수 있습니다.',
            '입력 순서를 바꾸거나 한쪽을 0으로 놓고 과정을 따라가세요.'),
        hints=['a보다 b가 큰 경우에도 결과가 같은지 확인하세요.', '둘 다 0일 때의 약속과 한쪽만 0일 때를 확인하세요.'],
        visual_frames=scenes(
            ([48,18],(0,1),'48과 18에서 시작합니다.','48=18×2+12입니다.','48 % 18 = 12'),
            ([18,12],(0,1),'문제를 (18,12)로 줄입니다.','공약수 집합은 바뀌지 않습니다.','18 % 12 = 6'),
            ([12,6],(0,1),'다시 (12,6)으로 줄입니다.','12는 6으로 나누어 떨어집니다.','12 % 6 = 0'),
            ([6,0],(0,),'나머지가 0이 되었습니다.','남은 6이 최대공약수입니다.','return 6'))),
    dict(
        id='prime-test', title='소수 판별 · 제곱근까지만', group='수학',
        summary='합성수의 약수 한 쌍 중 작은 쪽만 검사합니다.',
        concept='n이 합성수라면 n=a×b인 약수 쌍이 있습니다. 두 약수가 모두 √n보다 클 수 없으므로 2부터 d×d≤n인 d까지만 검사하면 됩니다. n<2는 소수가 아닙니다.',
        complexity='나눗셈을 최악 O(√n)번 하고 추가 공간 O(1)을 사용합니다.',
        application='소수에 기반한 간단한 입력 검증이나 소인수분해의 준비 단계로 사용합니다.',
        questions=[('왜 n의 제곱근보다 큰 수는 새로 검사할 필요가 없나요?', '그런 큰 약수가 있다면 짝을 이루는 다른 약수는 제곱근 이하이므로 앞에서 이미 발견된다.'),
                   ('1과 완전제곱수는 어떻게 처리해야 하나요?', '1은 소수가 아니다. 9처럼 제곱근 자체가 약수일 수 있으므로 d×d≤n을 검사한다.')],
        requirements=['`isPrime(n: number): boolean`을 구현하세요.', 'n은 0 이상의 안전한 정수입니다.'],
        starter='function isPrime(n: number): boolean { return false; }',
        reference='''function isPrime(n: number): boolean {
  if (n < 2) return false;
  for (let d = 2; d * d <= n; d++) if (n % d === 0) return false;
  return true;
}''',
        public_tests='assertEqual(isPrime(2),true); assertEqual(isPrime(9),false);',
        hidden_tests='assertEqual(isPrime(0),false); assertEqual(isPrime(1),false); assertEqual(isPrime(3),true); assertEqual(isPrime(49),false); assertEqual(isPrime(97),true); assertEqual(isPrime(100),false);',
        mutations=[('제곱수', 'd * d <= n', 'd * d < n'),
                   ('작은 수', 'if (n < 2) return false;', 'if (n < 1) return false;')],
        visualization='prime-test', prerequisites=['gcd'], difficulty='입문',
        reading=guide('d-1까지 약수가 없었다면 아직 소수 후보이고, 남은 검사는 d×d≤n인 약수뿐입니다.',
            [['1 이하를 제외한다','0과 1은 정의상 소수가 아닙니다.'],['작은 약수부터 본다','2,3,...을 검사하되 d×d가 n을 넘으면 멈춥니다.'],['약수를 찾으면 끝낸다','나머지가 0이면 합성수, 끝까지 없으면 소수입니다.']],
            'd×d<n으로 쓰면 49의 7처럼 정확히 제곱근인 약수를 놓칩니다.',
            '모든 수를 n-1까지 검사하는 대신 제곱근까지만 검사합니다.',
            '해시 버킷 수 후보를 고를 때 소수 여부를 확인할 수 있으나 좋은 해시 설계에는 다른 조건도 필요합니다.',
            '49를 시험하며 d=7이 왜 반드시 검사 대상인지 확인하세요.'),
        hints=['49처럼 소수의 제곱을 넣어보세요.', '0, 1, 2가 각각 어떻게 분류되는지 확인하세요.'],
        visual_frames=scenes(
            ([49,2],(1,),'49를 2부터 나눠봅니다.','나머지가 0이 아니므로 다음 후보로 갑니다.','49 % 2 = 1'),
            ([49,3],(1,),'3도 약수가 아닙니다.','d×d≤49인 동안 계속 검사합니다.','49 % 3 = 1'),
            ([49,7],(1,),'7은 정확히 제곱근입니다.','49 % 7 = 0이므로 49는 소수가 아닙니다.','7×7 = 49'))),
    dict(
        id='find-index', title='findIndex · 첫 일치 위치', group='메서드',
        summary='조건을 만족하는 첫 원소의 인덱스를 찾습니다.',
        concept='findIndex는 배열 앞에서부터 조건 함수를 호출하고, 참인 첫 위치를 반환합니다. 조건을 만족하지 않으면 -1입니다. 이 학습용 구현은 빈 슬롯이 없는 숫자 배열에 값과 인덱스를 전달하며 원본을 변경하지 않습니다.',
        complexity='최악 시간 O(n), 추가 공간 O(1)입니다. 첫 일치가 앞에 있으면 일찍 종료합니다.',
        application='재고 목록에서 처음 품절된 항목의 위치를 찾거나 로그에서 첫 오류의 위치를 확인합니다.',
        questions=[('조건을 만족하는 항목이 없으면 무엇을 반환하나요?', '-1을 반환한다.'),
                   ('첫 일치를 찾은 뒤에도 나머지 원소에 조건 함수를 호출해야 하나요?', '아니다. 바로 반환해 불필요한 호출을 막는다.')],
        requirements=['`findIndexValues(values: number[], predicate: (value: number, index: number) => boolean): number`를 구현하세요.',
                      '빈 슬롯이 없는 숫자 배열만 다루고 조건 함수에는 값과 원본 인덱스를 전달합니다. 첫 일치 후 호출을 멈추세요.'],
        starter='function findIndexValues(values: number[], predicate: (value: number, index: number) => boolean): number { return -1; }',
        reference='''function findIndexValues(values: number[], predicate: (value: number, index: number) => boolean): number {
  for (let i = 0; i < values.length; i++) if (predicate(values[i], i)) return i;
  return -1;
}''',
        public_tests='assertEqual(findIndexValues([4,7,9],v=>v>5),1); assertEqual(findIndexValues([],()=>true),-1);',
        hidden_tests='''const values=[5,5,8]; let calls=0;
assertEqual(findIndexValues(values,(v,i)=>{calls++;return i===1 && v===5;}),1);
assertEqual(calls,2); assertEqual(findIndexValues([3,4],()=>false),-1);
assertEqual(findIndexValues([0],v=>v===0),0); assertEqual(values,[5,5,8]);''',
        mutations=[('콜백 인덱스', 'predicate(values[i], i)', 'predicate(values[i], 0)'),
                   ('첫 위치', 'return i;', 'return i+1;')],
        visualization='find-index', prerequisites=['filter'], difficulty='입문',
        sources=[{'title':'MDN · Array.findIndex','url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/findIndex'}],
        reading=guide('인덱스 i 이전의 모든 원소는 조건을 만족하지 않습니다.',
            [['왼쪽부터 호출한다','값과 원래 인덱스를 조건 함수에 전달합니다.'],['참이면 곧바로 반환한다','첫 참의 위치만 필요하므로 뒤의 원소는 확인하지 않습니다.'],['끝까지 없으면 -1','빈 배열도 호출 없이 -1을 반환합니다.']],
            '값 자체가 아니라 인덱스를 돌려줍니다. 앞쪽 값이 탈락해도 콜백 인덱스는 원본 위치입니다.',
            '가장 앞에서 일치하면 O(1)이지만 최악에는 모든 원소를 확인합니다.',
            '목록에서 조건에 맞는 첫 항목의 위치를 찾아 수정 버튼을 연결할 수 있습니다.',
            '첫 위치, 마지막 위치, 미일치 입력을 비교하세요.'),
        hints=['조건 함수가 인덱스를 사용하게 해보세요.', '첫 일치 후 조건 함수 호출 횟수가 더 늘지 않는지 확인하세요.'],
        visual_frames=scenes(
            ([4,7,9],(0,),'4에 조건 v>5를 적용합니다.','거짓이므로 다음 원소로 이동합니다.','predicate(4,0) → false'),
            ([4,7,9],(1,),'7에 조건을 적용합니다.','참이므로 인덱스 1을 반환합니다.','predicate(7,1) → true'),
            ([4,7,9],(1,),'9는 검사하지 않습니다.','첫 일치만 필요합니다.','return 1'))),
])

PATTERN_LESSONS.extend([
    dict(
        id='some', title='some · 하나라도 만족하는가', group='메서드',
        summary='조건을 만족하는 첫 원소에서 검사를 멈춥니다.',
        concept='some은 배열 원소를 왼쪽부터 검사해 하나라도 조건 함수가 참이면 true입니다. 첫 참을 만나면 남은 원소는 검사하지 않습니다. 빈 배열에는 만족하는 원소가 없으므로 false입니다. 이 학습용 구현은 빈 슬롯 없는 숫자 배열만 다룹니다.',
        complexity='최악 시간 O(n), 추가 공간 O(1). 첫 원소가 조건에 맞으면 O(1)입니다.',
        application='입력 목록에 오류나 품절 항목이 하나라도 있는지 확인할 때 사용합니다.',
        questions=[('빈 배열에 some을 적용하면 왜 false인가요?', '조건을 만족하는 원소가 하나도 없으므로 false다.'),
                   ('첫 원소가 참이면 남은 원소에 콜백을 호출하나요?', '아니다. 결과가 이미 true로 정해져 호출을 멈춘다.')],
        requirements=['`someValues(values: number[], predicate: (value: number, index: number) => boolean): boolean`을 구현하세요.',
                      '빈 슬롯 없는 숫자 배열에만 적용하고 값과 원본 인덱스를 전달합니다. 첫 참에서 바로 멈추세요.'],
        starter='function someValues(values: number[], predicate: (value:number,index:number)=>boolean): boolean { return false; }',
        reference='''function someValues(values: number[], predicate: (value:number,index:number)=>boolean): boolean {
  for (let i=0;i<values.length;i++) if (predicate(values[i],i)) return true;
  return false;
}''',
        public_tests='assertEqual(someValues([1,3,4],v=>v%2===0),true); assertEqual(someValues([],()=>true),false);',
        hidden_tests='''let calls=0;
assertEqual(someValues([5,6,7],(v,i)=>{calls++;return i===1 && v===6;}),true);
assertEqual(calls,2); assertEqual(someValues([1,3],v=>v<0),false);
assertEqual(someValues([0],v=>v===0),true);''',
        mutations=[('콜백 인덱스', 'predicate(values[i],i)', 'predicate(values[i],0)'),
                   ('빈 배열', 'return false;', 'return true;')],
        visualization='some', prerequisites=['find-index'], difficulty='입문',
        sources=[{'title':'MDN · Array.some','url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/some'}],
        reading=guide('현재 위치 이전의 모든 원소는 조건에 맞지 않았습니다.',
            [['왼쪽에서 시작한다','각 값과 원래 인덱스를 조건 함수에 전달합니다.'],['참이면 멈춘다','하나만 찾으면 true가 확정됩니다.'],['끝까지 거짓이면 false','빈 배열도 이 경우에 포함됩니다.']],
            '콜백을 모두 호출하거나 결과를 반대로 뒤집지 마세요. 빈 배열은 false입니다.',
            '조건을 만족하는 값이 앞에 있을수록 일찍 종료합니다.',
            '작업 목록에 실패 항목이 하나라도 있는지 확인할 수 있습니다.',
            '콜백 호출 횟수를 기록해 첫 참 뒤에서 멈추는지 보세요.'),
        hints=['빈 배열의 결과를 확인하세요.', '중간 원소에서 참이 되는 콜백의 호출 횟수를 세어보세요.'],
        visual_frames=scenes(
            ([1,3,4],(0,),'1은 짝수가 아닙니다.','다음 원소를 확인합니다.','predicate(1,0) → false'),
            ([1,3,4],(1,),'3도 짝수가 아닙니다.','아직 true를 반환할 수 없습니다.','predicate(3,1) → false'),
            ([1,3,4],(2,),'4는 짝수입니다.','하나를 찾았으므로 true를 반환합니다.','return true'))),
    dict(
        id='every', title='every · 모두 만족하는가', group='메서드',
        summary='조건에 맞지 않는 첫 원소에서 검사를 멈춥니다.',
        concept='every는 모든 원소가 조건을 만족할 때 true입니다. 첫 거짓을 만나면 false가 확정됩니다. 빈 배열에는 조건을 위반하는 원소가 없으므로 true입니다. 이 학습용 구현은 빈 슬롯 없는 숫자 배열만 다룹니다.',
        complexity='최악 시간 O(n), 추가 공간 O(1). 첫 원소가 거짓이면 O(1)입니다.',
        application='여러 입력이 모두 유효한지 확인하거나 모든 작업이 완료되었는지 검사할 수 있습니다.',
        questions=[('빈 배열에서 every가 true인 이유는 무엇인가요?', '조건을 위반하는 원소가 없기 때문이다.'),
                   ('첫 거짓 이후 콜백을 계속 호출해야 하나요?', '아니다. 전체가 참일 수 없으므로 즉시 false를 반환한다.')],
        requirements=['`everyValues(values: number[], predicate: (value:number,index:number)=>boolean): boolean`을 구현하세요.',
                      '빈 슬롯 없는 숫자 배열에만 적용하고 값과 원본 인덱스를 전달합니다. 첫 거짓에서 멈추세요.'],
        starter='function everyValues(values: number[], predicate: (value:number,index:number)=>boolean): boolean { return false; }',
        reference='''function everyValues(values: number[], predicate: (value:number,index:number)=>boolean): boolean {
  for (let i=0;i<values.length;i++) if (!predicate(values[i],i)) return false;
  return true;
}''',
        public_tests='assertEqual(everyValues([2,4,6],v=>v%2===0),true); assertEqual(everyValues([],()=>false),true);',
        hidden_tests='''let calls=0;
assertEqual(everyValues([2,3,4],(v,i)=>{calls++;return i===0 && v===2;}),false);
assertEqual(calls,2); assertEqual(everyValues([0],v=>v>0),false);
assertEqual(everyValues([1,2],(v,i)=>v===i+1),true);''',
        mutations=[('콜백 인덱스', 'predicate(values[i],i)', 'predicate(values[i],0)'),
                   ('빈 배열', 'return true;', 'return false;')],
        visualization='every', prerequisites=['some'], difficulty='입문',
        sources=[{'title':'MDN · Array.every','url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/every'}],
        reading=guide('현재 위치 이전의 모든 원소는 조건을 만족했습니다.',
            [['각 원소를 검사한다','값과 원래 인덱스를 순서대로 전달합니다.'],['첫 거짓에서 멈춘다','하나라도 위반하면 전체 결과가 false입니다.'],['끝까지 참이면 true','빈 배열도 위반자가 없어 true입니다.']],
            '빈 배열 결과를 some과 똑같이 false로 처리하면 안 됩니다.',
            '검사를 일찍 멈추므로 위반 항목이 앞에 있을수록 비용이 적습니다.',
            '모든 입력 필드의 유효성을 검사하는 조건식에 사용할 수 있습니다.',
            '빈 배열과 중간에 위반 원소가 있는 배열을 비교하세요.'),
        hints=['빈 배열의 결과가 some과 어떻게 다른지 확인하세요.', '두 번째 원소가 조건을 위반할 때 세 번째 원소를 검사하지 않는지 확인하세요.'],
        visual_frames=scenes(
            ([2,4,5],(0,),'2는 짝수입니다.','다음 원소도 확인해야 전체 조건을 알 수 있습니다.','predicate(2,0) → true'),
            ([2,4,5],(1,),'4도 짝수입니다.','아직 결과는 정해지지 않았습니다.','predicate(4,1) → true'),
            ([2,4,5],(2,),'5는 짝수가 아닙니다.','하나의 위반을 찾았으므로 false입니다.','return false'))),
    dict(
        id='slice', title='slice · 구간 복사', group='메서드',
        summary='반열림 구간을 복사하며 음수 인덱스를 끝 기준으로 바꿉니다.',
        concept='slice(start,end)는 start를 포함하고 end를 제외한 새 배열을 만듭니다. 음수 인덱스는 배열 끝에서 센 위치입니다. 이 학습용 구현은 정수 인덱스와 빈 슬롯 없는 숫자 배열만 다루며, 시작이 끝 이상이면 빈 새 배열을 반환합니다.',
        complexity='복사하는 원소 수 k에 대해 시간 O(k), 결과 배열 공간 O(k)입니다.',
        application='긴 목록에서 현재 페이지에 보여줄 항목 범위를 원본 변경 없이 선택합니다.',
        questions=[('[1,2,3,4].slice(1,3)의 결과와 경계 규칙은 무엇인가요?', '[2,3]이며 시작 1은 포함하고 끝 3은 제외한다.'),
                   ('slice(-2)는 어떤 위치부터 시작하고 원본은 변하나요?', '길이에서 2를 뺀 위치부터 새 배열로 복사하며 원본은 그대로다.')],
        requirements=['`sliceValues(values: number[], start: number, end?: number): number[]`를 구현하세요.',
                      'start/end는 정수이며 끝 생략은 배열 끝입니다. 음수 인덱스와 범위 밖 인덱스를 처리하고 원본은 변경하지 마세요.'],
        starter='function sliceValues(values: number[], start: number, end?: number): number[] { return []; }',
        reference='''function sliceValues(values: number[], start: number, end = values.length): number[] {
  const n=values.length;
  const index=(value:number)=>value<0?Math.max(n+value,0):Math.min(value,n);
  const from=index(start), to=index(end), result:number[]=[];
  for (let i=from;i<to;i++) result.push(values[i]);
  return result;
}''',
        public_tests='assertEqual(sliceValues([1,2,3,4],1,3),[2,3]); assertEqual(sliceValues([1,2,3,4],-2),[3,4]);',
        hidden_tests='''const a=[0,1,2];
assertEqual(sliceValues(a,0,0),[]); assertEqual(sliceValues(a,-99,99),[0,1,2]);
assertEqual(sliceValues(a,3,1),[]); assertEqual(sliceValues(a,0),[0,1,2]);
assertEqual(sliceValues(a,0)===a,false); assertEqual(a,[0,1,2]); assertEqual(sliceValues([],0),[]);''',
        mutations=[('음수 위치', 'Math.max(n+value,0)', 'Math.max(value,0)'),
                   ('끝 경계', 'i<to', 'i<=to')],
        visualization='slice', prerequisites=['array-rotation'], difficulty='입문',
        sources=[{'title':'MDN · Array.slice','url':'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/slice'}],
        reading=guide('복사하는 인덱스는 항상 정규화한 start 이상이고 end 미만입니다.',
            [['경계를 정규화한다','음수는 배열 끝에서 세고 범위 밖은 0 또는 길이로 제한합니다.'],['시작을 포함한다','start 위치부터 새 배열에 값을 붙입니다.'],['끝을 제외한다','end 위치에 도착하면 멈춥니다.']],
            'slice는 원본을 변경하지 않습니다. end를 포함하면 한 칸을 더 복사합니다.',
            '복사한 값이 k개면 O(k) 공간을 새로 차지합니다.',
            '페이지 단위 목록 표시에서 시작·끝 인덱스를 계산한 뒤 항목을 복사합니다.',
            '양수·음수·생략된 끝 경계를 각각 시험하세요.'),
        hints=['end를 생략하거나 start가 음수인 경우를 확인하세요.', 'start와 end가 같거나 순서가 거꾸로일 때도 새 빈 배열을 반환하나요?'],
        visual_frames=scenes(
            ([1,2,3,4],(1,2),'[1,3) 구간을 선택합니다.','인덱스 1과 2는 포함하고 3은 제외합니다.','start=1; end=3'),
            ([2,3],(0,1),'선택한 값을 새 배열에 복사합니다.','원본 [1,2,3,4]는 그대로 남습니다.','return [2,3]'),
            ([1,2,3,4],(2,3),'start=-2이면 끝에서 둘째부터입니다.','길이 4에서 2를 빼 인덱스 2로 바꿉니다.','4 + (-2) = 2'))),
])

PATTERN_LESSONS.extend([
    dict(
        id='sorted-two-pointer', title='투 포인터 · 양끝에서 좁히기', group='알고리즘',
        summary='정렬된 배열의 양끝을 움직여 목표 합을 만드는 두 수를 찾습니다.',
        concept='오름차순 배열에서 양끝 값의 합이 목표보다 작으면 왼쪽을 오른쪽으로 옮겨 더 큰 합을 시도합니다. 크면 오른쪽을 왼쪽으로 옮겨 더 작은 합을 시도합니다. 한 번에 불가능한 후보 구간을 버릴 수 있는 이유는 배열이 정렬되어 있기 때문입니다.',
        complexity='양쪽 포인터는 최대 n번 이동하므로 시간 O(n), 추가 공간 O(1)입니다.',
        application='정렬된 가격 목록에서 목표 예산과 같은 두 가격을 찾을 때 사용할 수 있습니다.',
        questions=[('합이 목표보다 작으면 어느 포인터를 움직이고 왜 그런가요?', '왼쪽 포인터를 오른쪽으로 옮긴다. 정렬되어 있으므로 오른쪽을 줄이면 합은 더 작아질 뿐이다.'),
                   ('정렬되지 않은 배열에도 같은 규칙을 바로 적용할 수 있나요?', '아니다. 포인터 이동이 합의 증감과 연결된다는 보장이 사라진다.')],
        requirements=['`sortedPair(values: number[], target: number): [number, number] | null`을 구현하세요.',
                      '입력은 오름차순입니다. 서로 다른 두 인덱스 i<j를 반환합니다. 여러 답이 있으면 어느 유효 쌍이나 허용합니다.'],
        starter='function sortedPair(values: number[], target: number): [number, number] | null { return null; }',
        reference='''function sortedPair(values: number[], target: number): [number, number] | null {
  let left=0, right=values.length-1;
  while (left<right) {
    const sum=values[left]+values[right];
    if (sum===target) return [left,right];
    if (sum<target) left++; else right--;
  }
  return null;
}''',
        public_tests='assertEqual(sortedPair([1,4,7,9],10),[0,3]); assertEqual(sortedPair([4],8),null);',
        hidden_tests='''const values=[-5,0,3,3,8]; const pair=sortedPair(values,3);
assertEqual(pair!==null,true);
if (pair) { assertEqual(pair[0]<pair[1],true); assertEqual(values[pair[0]]+values[pair[1]],3); }
assertEqual(sortedPair([1,4,7],5),[0,1]);
assertEqual(sortedPair([1,4,7],11),[1,2]);
assertEqual(sortedPair([1,2,3],99),null); assertEqual(sortedPair([],0),null);''',
        mutations=[('작은 합', 'if (sum<target) left++;', 'if (sum<target) right--;'),
                   ('큰 합', 'else right--;', 'else left++;')],
        visualization='sorted-two-pointer', prerequisites=['two-sum'], difficulty='입문',
        reading=guide('현재 [left,right] 바깥의 인덱스는 더 이상 답에 포함될 수 없습니다.',
            [['양끝에서 시작한다','가장 작은 값과 가장 큰 값을 더합니다.'],['작으면 왼쪽을 올린다','왼쪽 값을 키워야 합을 키울 수 있습니다.'],['크면 오른쪽을 내린다','오른쪽 값을 줄여야 합을 줄일 수 있습니다.']],
            '같은 원소를 두 번 사용하지 않도록 left<right를 유지합니다. 정렬 전제가 깨지면 포인터 이동 근거도 사라집니다.',
            '해시를 쓰는 two-sum보다 입력 정렬이 필요하지만 추가 저장 공간은 O(1)입니다.',
            '금액순 가격표에서 두 가격의 합이 할인권 목표 금액인지 찾을 수 있습니다.',
            '합이 너무 크거나 작은 경우 양 포인터가 각각 어디로 움직이는지 따라가세요.'),
        hints=['정확히 목표가 된 두 값이 양끝에 있는 입력을 테스트하세요.', '목표가 현재 합보다 큰 경우와 작은 경우를 모두 확인하세요.'],
        visual_frames=scenes(
            ([1,4,7,9],(0,3),'목표 11에서 양끝 1과 9를 고릅니다.','합 10이 작으므로 왼쪽을 움직입니다.','left=1'),
            ([1,4,7,9],(1,3),'4와 9의 합은 13입니다.','목표보다 크므로 오른쪽을 움직입니다.','right=2'),
            ([1,4,7,9],(1,2),'4와 7의 합은 11입니다.','서로 다른 두 인덱스 [1,2]가 답입니다.','return [1,2]'))),
    dict(
        id='quick-sort', title='퀵 정렬 · 피벗으로 나누기', group='알고리즘',
        summary='피벗보다 작은 값과 큰 값을 분할해 재귀적으로 정렬합니다.',
        concept='퀵 정렬은 피벗을 한 자리로 옮기고 그 왼쪽에 작은 값, 오른쪽에 크거나 같은 값이 오도록 분할합니다. 그 후 양쪽 구간을 독립적으로 정렬합니다. 이 단원은 마지막 원소를 피벗으로 고르며 입력을 복사해 원본을 보존합니다.',
        complexity='평균 O(n log n)이지만 이미 정렬된 입력에서 마지막 원소 피벗은 O(n²)까지 악화됩니다. 복사한 결과 O(n)에 재귀 호출 스택 평균 O(log n), 최악 O(n)이 더해집니다.',
        application='원소의 순서만 중요하고 안정성이 필요 없는 정렬 상황에서 분할 정복을 이해하는 기초가 됩니다.',
        questions=[('분할 직후 피벗의 왼쪽과 오른쪽에 어떤 값이 있나요?', '왼쪽은 피벗보다 작은 값, 오른쪽은 피벗보다 크거나 같은 값이다.'),
                   ('마지막 원소를 피벗으로 선택할 때 이미 정렬된 입력은 왜 불리한가요?', '한쪽 구간만 거의 전체 크기로 남아 분할 균형이 나빠지고 O(n²)이 될 수 있다.')],
        requirements=['`quickSort(values: number[]): number[]`를 구현하세요.', '중복·음수를 허용하고 입력을 변경하지 않은 새 정렬 배열을 반환하세요. 이 단원은 마지막 원소를 피벗으로 사용합니다.'],
        starter='function quickSort(values: number[]): number[] { return []; }',
        reference='''function quickSort(values: number[]): number[] {
  const a=[...values];
  function sort(left:number,right:number):void {
    if (left>=right) return;
    const pivot=a[right]; let next=left;
    for (let i=left;i<right;i++) {
      if (a[i]<pivot) { [a[i],a[next]]=[a[next],a[i]]; next++; }
    }
    [a[next],a[right]]=[a[right],a[next]];
    sort(left,next-1); sort(next+1,right);
  }
  sort(0,a.length-1); return a;
}''',
        public_tests='assertEqual(quickSort([4,1,3,2]),[1,2,3,4]); assertEqual(quickSort([]),[]);',
        hidden_tests='''const a=[3,-2,3,0,-2]; assertEqual(quickSort(a),[-2,-2,0,3,3]);
assertEqual(a,[3,-2,3,0,-2]); assertEqual(quickSort([5]),[5]);
assertEqual(quickSort([1,2,3]),[1,2,3]); assertEqual(quickSort([3,2,1]),[1,2,3]);
assertEqual(quickSort(a)===a,false);''',
        mutations=[('분할 방향', 'if (a[i]<pivot)', 'if (a[i]>pivot)'),
                   ('마지막 위치', 'sort(0,a.length-1);', 'sort(0,a.length-2);')],
        visualization='quick-sort', prerequisites=['merge-sort'], difficulty='보통',
        reading=guide('분할을 마치면 피벗의 최종 위치가 정해지고 양쪽은 독립적인 정렬 구간입니다.',
            [['피벗을 정한다','마지막 값 2를 피벗으로 고릅니다.'],['한 번 분할한다','2보다 작은 값은 앞쪽에, 나머지는 뒤쪽에 둡니다.'],['양쪽을 다시 정렬한다','피벗을 제외한 왼쪽과 오른쪽 구간에 같은 과정을 적용합니다.']],
            '분할 종료 인덱스가 잘못되면 피벗을 다시 포함해 무한 재귀가 되거나 마지막 원소를 놓칠 수 있습니다.',
            '피벗 선택에 따라 성능이 크게 달라집니다. 이 문제의 마지막 피벗은 설명이 쉽지만 정렬된 입력에서 불리합니다.',
            '대량 목록 정렬에서 분할 정복 아이디어를 쓰지만 실제 라이브러리 정렬은 별도 최적화와 안정성 규칙을 가질 수 있습니다.',
            '역순과 이미 정렬된 입력에서 분할 크기가 어떻게 달라지는지 보세요.'),
        hints=['중복값과 음수가 있는 입력을 정렬해보세요.', '첫 호출에서 마지막 원소까지 분할에 포함되는지 확인하세요.'],
        visual_frames=scenes(
            ([4,1,3,2],(3,),'마지막 값 2를 피벗으로 고릅니다.','아직 다른 원소의 상대 위치는 정해지지 않았습니다.','pivot=2'),
            ([4,1,3,2],(1,3),'1은 2보다 작습니다.','작은 값 1을 왼쪽 구간으로 이동시킵니다.','1<2'),
            ([1,2,3,4],(1,),'피벗 2가 최종 위치에 놓입니다.','왼쪽 [1]과 오른쪽 [3,4]를 각각 정렬합니다.','sort(left); sort(right)'),
            ([1,2,3,4],(),'모든 구간의 정렬이 끝났습니다.','같은 값은 모두 남고 원본 배열은 보존됩니다.','return [1,2,3,4]'))),
    dict(
        id='digit-count', title='자릿수 · 10으로 나누기', group='수학',
        summary='양의 정수를 반복해서 10으로 나눠 십진 자릿수를 셉니다.',
        concept='10진 자릿수는 10으로 나눌 때마다 하나씩 제거됩니다. Math.floor(n/10)을 0이 될 때까지 반복해 횟수를 셉니다. 0은 한 자리 숫자이므로 별도 처리합니다.',
        complexity='숫자 n의 자릿수만큼 반복하므로 시간 O(log₁₀ n), 추가 공간 O(1)입니다.',
        application='숫자 ID를 자릿수 기준으로 표시하거나 입력 길이를 확인할 때 사용합니다.',
        questions=[('120을 반복해서 10으로 나누면 몇 번 만에 0이 되나요?', '120→12→1→0으로 세 번이고 자릿수는 3이다.'),
                   ('0을 같은 while 반복문만으로 처리하면 어떤 문제가 생기나요?', '반복문에 한 번도 들어가지 않아 0자리로 세게 된다. 0은 한 자리로 처리해야 한다.')],
        requirements=['`digitCount(value: number): number`를 구현하세요.', '입력은 0 이상의 안전한 정수입니다. 0의 자릿수는 1입니다.'],
        starter='function digitCount(value: number): number { return 0; }',
        reference='''function digitCount(value: number): number {
  if (value===0) return 1;
  let count=0;
  while (value>0) { value=Math.floor(value/10); count++; }
  return count;
}''',
        public_tests='assertEqual(digitCount(120),3); assertEqual(digitCount(0),1);',
        hidden_tests='assertEqual(digitCount(1),1); assertEqual(digitCount(9),1); assertEqual(digitCount(10),2); assertEqual(digitCount(1000),4); assertEqual(digitCount(1000000000000000),16);',
        mutations=[('0 처리', 'if (value===0) return 1;', 'if (value===0) return 0;'),
                   ('나누는 수', 'value/10', 'value/100')],
        visualization='digit-count', prerequisites=[], difficulty='입문',
        reading=guide('count는 지금까지 제거한 십진 자릿수입니다.',
            [['0을 구분한다','0도 십진수로 한 자리입니다.'],['마지막 자리를 버린다','120을 10으로 나눈 몫은 12입니다.'],['끝까지 반복한다','12→1→0을 지나며 세 번 셉니다.']],
            'Math.floor가 없으면 소수부가 남아 반복이 끝나지 않을 수 있습니다. 한 번에 100으로 나누면 두 자리를 버립니다.',
            '문자열로 바꿔 길이를 구할 수도 있지만 이 실습은 숫자 연산과 반복 횟수를 이해합니다.',
            '상품 번호의 자릿수를 확인할 때 값을 문자열로 변환하지 않아도 셀 수 있습니다.',
            '9와 10, 99와 100 사이에서 결과가 언제 늘어나는지 확인하세요.'),
        hints=['0과 10의 거듭제곱을 각각 넣어보세요.', '한 번에 정확히 한 자릿수만 제거하는지 확인하세요.'],
        visual_frames=scenes(
            ([120],(0,),'120에서 시작합니다.','아직 제거한 자릿수는 0개입니다.','count=0'),
            ([12],(0,),'맨 뒤의 0을 버립니다.','10으로 나눈 몫 12를 다음 값으로 사용합니다.','count=1'),
            ([1],(0,),'다음 자릿수도 제거합니다.','남은 값은 1입니다.','count=2'),
            ([0],(0,),'더 남은 자릿수가 없습니다.','총 3번 제거했으므로 120은 세 자리입니다.','return 3'))),
])
