"""Hand-authored baseline. Human semantic review is still pending; see docs/validation.md."""
from .schema import ContextDraft, SetDraft

READ = '''function counter(start) {
  let value = start;
  return () => ++value;
}
const a = counter(0);
const b = counter(10);
console.log(a(), a(), b(), a());
'''

HINTS = {
    'READ': [
        'counter를 호출할 때마다 새로운 value가 만들어집니다. a와 b는 각각 자신이 만들어진 호출의 value를 기억합니다. 두 변수의 값을 따로 적어두고 추적해보세요.',
        'console.log의 인수는 왼쪽부터 계산됩니다. 처음 a()를 부르면 a가 기억하는 0이 1로 바뀌고, 다음 a()는 그 값을 이어받습니다. 이때 아직 호출하지 않은 b의 값도 바뀌었을까요?',
        '++value는 먼저 1을 더한 뒤 바뀐 값을 반환합니다. a용 칸과 b용 칸을 만들고, 호출할 때 해당 칸만 갱신해보세요. 네 번의 반환값을 호출 순서대로 공백으로 구분해 답하면 됩니다.',
    ],
    'FIX': [
        '현재 value는 makeCounter 바깥에 한 번만 선언되어 있습니다. a와 b가 반환하는 함수 모두 같은 변수를 바라봅니다. 카운터를 새로 만들 때 어느 코드가 기존 값을 덮어쓰는지 찾아보세요.',
        '공개 테스트에서 a를 만들면 value는 0이지만, b를 만드는 순간 10으로 바뀝니다. 그래서 아직 한 번도 부르지 않은 a()도 10부터 증가하게 됩니다. a의 시작값을 b 생성 후에도 지키려면 두 값이 어디에 있어야 할까요?',
        '상태를 만들고 초기화하는 위치를 카운터 생성 함수 안으로 옮기는 방향을 생각해보세요. 반환된 함수가 호출될 때마다 초기화하면 누적이 끊기므로, 생성 시 한 번 초기화하고 호출 시에는 증가·반환만 해야 합니다. a → b → a 순서로 불러 독립성을 확인하세요.',
    ],
    'MODIFY': [
        '기존 코드는 ++value로 항상 1만 더합니다. 새 요구사항에서는 카운터를 만들 때 받은 step이 매 호출의 변화량입니다. 상태를 기억하는 방식은 유지하면서 증가 연산을 살펴보세요.',
        '공개 테스트의 a는 0에서 2씩, b는 10에서 3씩 변해야 합니다. a() 한 번 뒤 a의 값은 2가 되고, b()를 불러도 a의 값은 그대로입니다. 다음 a()에서는 어떤 값을 기준으로 얼마를 더해야 할까요?',
        '반환된 함수 안에서 현재 값에 step을 반영한 뒤 갱신된 값을 반환하는 순서로 생각해보세요. 0을 특별히 다른 값으로 바꾸거나 음수의 부호를 없애지 않아야 합니다. Run에서 step을 0과 음수로 바꿔 확인해보세요.',
    ],
    'BUILD': [
        'makeAccount(start) 호출과 그 결과인 travel(amount) 호출은 역할이 다릅니다. 첫 호출은 저금통을 만들고 시작 잔액을 정하며, 이후 호출은 그 저금통의 잔액을 바꿉니다. 바깥 함수가 숫자 대신 무엇을 반환해야 할지 생각해보세요.',
        '공개 테스트에서 travel(3) 이후 travel의 잔액은 3입니다. books(-4)는 books의 10만 바꾸므로 travel은 여전히 3을 기억해야 합니다. 이어지는 travel(2)가 앞선 저축을 잊지 않게 하려면 어떤 상태가 유지되어야 할까요?',
        '생성할 때 잔액을 한 번 준비하고, 증감액을 받는 함수를 반환하는 두 단계로 나눠보세요. 안쪽 함수는 기억한 잔액에 amount를 더하고 새 잔액을 반환합니다. amount가 0이어도 잔액을 반환하고, 음수라고 계산을 막거나 0으로 보정하지 마세요.',
    ],
}


def sample():
    context = ContextDraft(
        title='클로저: 함수가 기억하는 상태',
        description='독립적인 상태를 읽고, 고치고, 확장한 뒤 작은 누적기를 직접 구현합니다.',
        summary='함수는 자신이 생성된 렉시컬 환경에 접근할 수 있습니다. 팩토리를 호출할 때마다 새로운 지역 변수를 만들면 반환된 함수들이 호출별로 독립적인 상태를 유지합니다.',
        concepts=['클로저', '렉시컬 환경', '독립적인 상태'],
        learning_notes='JavaScript의 결정적인 동기 실행과 수치 누적만 연습한다. 클로저 사용 자체는 출력 테스트로 증명할 수 없으므로 구조적인 구현 방식은 채점하지 않는다. DOM, 비동기, 성능 및 메모리 수명은 다루지 않는다.',
        language='javascript', framework='',
        units=[dict(
            id='u1', title='클로저로 독립적인 상태 만들기',
            objective='함수가 기억하는 변수를 추적하고, 호출 사이에 상태를 유지하면서 서로 다른 함수의 상태를 분리할 수 있습니다.',
            concepts=['클로저', '렉시컬 환경', '독립적인 상태'], prerequisites=[],
            rationale='이 자료의 세 개념은 같은 동작을 서로 다른 관점에서 설명합니다. 변수를 찾는 규칙부터 상태의 수명과 독립성까지 한 단원에서 연결해 학습합니다.',
            lesson=[dict(
                title='함수는 자신이 만들어진 곳을 기억합니다',
                body='함수는 값처럼 변수에 넣거나 다른 함수의 반환값으로 사용할 수 있습니다. 바깥 함수가 안쪽 함수를 반환하면, 반환된 함수를 나중에 다시 호출할 수 있습니다. 이때 안쪽 함수는 선언된 위치에 있는 바깥 변수에도 접근할 수 있습니다. 이렇게 함수와 그 함수가 접근할 수 있는 바깥 환경의 조합을 클로저라고 합니다.\n\n렉시컬 환경은 변수를 찾을 때 참고하는 이름과 값의 연결입니다. 변수는 함수를 호출한 장소가 아니라 함수를 작성한 위치를 기준으로 찾습니다. 아래에서는 makeGreeting이 실행을 마친 뒤에도 greet이 name을 사용할 수 있습니다. makeGreeting("민")은 함수를 만들고, greet()은 그 함수를 실행합니다. 두 괄호는 서로 다른 시점의 호출입니다.',
                code='function makeGreeting(name) {\n  return () => "안녕하세요, " + name;\n}\nconst greet = makeGreeting("민");\nconsole.log(greet());',
                output='안녕하세요, 민',
                walkthrough='1. makeGreeting에 "민"을 전달하면 name에 그 값이 연결됩니다.\n2. 반환되는 화살표 함수는 아직 실행되지 않습니다. greet이 그 함수를 가리킵니다.\n3. greet()을 호출하면 안쪽 함수가 기억하는 name을 읽어 문장을 반환합니다.\n4. console.log가 그 반환값을 출력합니다.'),
                dict(
                title='한 번 만든 상태는 다음 호출로 이어집니다',
                body='클로저가 기억하는 것은 생성 순간의 값만 복사한 사진이 아닙니다. 같은 환경의 변수를 계속 읽고 바꿀 수 있습니다. 상태란 이전 호출의 영향을 다음 호출까지 유지하는 값입니다. 아래 메모장은 호출할 때마다 같은 notes 배열에 메모를 추가합니다.\n\nnotes를 makeNotebook 안에 두면 메모장을 만들 때 한 번만 준비합니다. 반대로 메모를 추가하는 안쪽 함수 안에서 매번 빈 배열을 만들면 이전 메모가 사라집니다. 바깥 함수와 안쪽 함수 중 어느 쪽이 언제 실행되는지를 나누어 생각하는 것이 핵심입니다.',
                code='function makeNotebook() {\n  const notes = [];\n  return text => {\n    notes.push(text);\n    return notes.join(", ");\n  };\n}\nconst travel = makeNotebook();\nconst work = makeNotebook();\nconsole.log(travel("기차"));\nconsole.log(work("회의"));\nconsole.log(travel("숙소"));',
                output='기차\n회의\n기차, 숙소',
                walkthrough='1. makeNotebook을 두 번 부르면 서로 다른 notes 배열 두 개가 생깁니다.\n2. travel("기차")는 첫 번째 배열에만 추가합니다.\n3. work("회의")는 두 번째 배열에만 추가합니다.\n4. travel("숙소")는 첫 번째 배열을 이어서 사용합니다. 전역에 배열 하나만 두었다면 두 메모장의 내용이 섞였을 것입니다.'),
                dict(
                title='상태를 바꾼 시점과 반환한 값을 구분합니다',
                body='숫자 상태도 같은 원리로 유지할 수 있습니다. 현재 값과 변화량을 더해 새 값을 계산하고, 그 새 값을 저장한 다음 반환해야 다음 호출에서 이어갈 수 있습니다. return은 호출자에게 값을 돌려주며, console.log는 값을 출력합니다. 문제에서 함수를 작성하라고 하면 함수는 값을 반환하고, 출력은 테스트 코드가 담당합니다.\n\n++value는 1을 더한 뒤 새 값을 돌려주고, value++는 증가 전 값을 돌려줍니다. 증가 간격이 정해져 있으면 언제나 1을 더하는 연산으로는 부족합니다. 변화량이 0이면 값이 유지되고 음수이면 감소합니다. 상태를 공유하는 전역 변수, 호출할 때마다 하는 재초기화, 갱신 전 값의 반환을 각각 점검하세요.',
                code='let value = 5;\nconsole.log(++value);\nconsole.log(value++);\nconsole.log(value);\nvalue += -2;\nconsole.log(value);',
                output='6\n6\n7\n5',
                walkthrough='첫 줄의 증가는 6으로 바꾼 뒤 6을 반환합니다. 두 번째 증가는 6을 반환한 뒤 저장된 값을 7로 바꿉니다. 따라서 다음 출력은 7입니다. 마지막에는 -2를 더해 5가 됩니다. 반환값과 다음 호출에 남을 값을 따로 추적해보세요.'),
            ],
            pitfalls=['상태를 전역에 하나만 만들면 모든 반환 함수가 공유합니다. 각 생성 호출에 속하는 상태가 필요합니다.', '상태를 안쪽 함수에서 매번 초기화하면 누적되지 않습니다. 생성 시 초기화와 호출 시 갱신을 구분하세요.', '함수 대신 실행 결과를 반환하거나, 반환 없이 출력만 하면 테스트가 기대한 함수를 사용할 수 없습니다.'],
            checkpoints=[dict(question='makeNotebook을 한 번 호출해 얻은 함수를 두 변수에 넣으면 메모장은 두 개가 될까요?', answer='아닙니다. 같은 함수를 두 이름으로 가리킬 뿐이므로 같은 notes를 사용합니다. 독립적인 메모장은 생성 함수를 다시 호출해 만들어야 합니다.'),
                         dict(question='메모장 예제에서 notes를 반환 함수 안으로 옮기면 어떤 일이 생길까요?', answer='메모를 추가할 때마다 빈 배열을 새로 만들기 때문에 직전 호출의 메모가 사라집니다. 상태의 초기화는 생성 시 한 번 이루어져야 합니다.'),
                         dict(question='상태를 바꾸는 함수에서 console.log만 하고 return을 생략하면 호출자가 무엇을 받나요?', answer='JavaScript에서는 undefined를 받습니다. 화면에 출력하는 동작과 호출자에게 값을 반환하는 동작은 다릅니다.')],
        )],
    )
    exercises = [{
        'kind': 'READ', 'title': '두 함수가 기억하는 값',
        'description': '실행하기 전에 console.log가 출력할 한 줄을 예측하세요. 값 사이에 공백을 넣으세요. 마지막 줄바꿈은 채점에 영향을 주지 않습니다.',
        'requirements': [{'id': 'r1', 'text': '각 counter 호출의 독립적인 상태를 고려한 출력 한 줄을 답하세요.'}],
        'starter': READ, 'public_tests': [{'id': 'predict', 'stdin': '', 'expected': '', 'requirements': ['r1']}],
        'hints': HINTS['READ'],
        'evaluation': {'reference': READ, 'alternative': '', 'hidden_tests': [], 'wrong_solutions': [], 'read_answer': '1 2 11 3'},
    }]
    specs = [
        ('FIX', '함수마다 자신의 카운터',
         '공유된 상태 때문에 카운터가 서로 영향을 주고 있습니다. makeCounter(start)를 고쳐주세요. 반환된 함수를 호출할 때마다 자신의 값을 1 증가시키고 새 값을 반환해야 합니다.',
         'let value;\nfunction makeCounter(start) {\n  value = start;\n  return () => ++value;\n}',
         'function makeCounter(start) { let value = start; return () => ++value; }',
         'function makeCounter(start) { const state = [start]; return function () { state[0] += 1; return state[0]; }; }',
         [('basic', 'const a = makeCounter(0);\nconst b = makeCounter(10);\n\nconsole.log(a()); // 1\nconsole.log(a()); // 2\nconsole.log(b()); // 11 — b는 자신의 값에서 시작\nconsole.log(a()); // 3 — a는 이어서 증가', '1\n2\n11\n3'),
          ('negative', 'const a = makeCounter(-3);\nconst b = makeCounter(4);\nconsole.log(b());\nconsole.log(a());\nconsole.log(b());\nconsole.log(a());', '5\n-2\n6\n-1')],
         ['각 호출은 시작값에서 1씩 증가한 값을 반환합니다.', '두 카운터의 상태는 독립적입니다.'],
         ['function makeCounter(start) { return () => start; }', 'let n = 0; function makeCounter(start) { n = start; return () => ++n; }']),
        ('MODIFY', '원하는 간격으로 증가시키기',
         'makeCounter(start, step)에 증가 간격을 추가하세요. 반환된 함수를 호출할 때마다 자신의 값에 step을 더하고 새 값을 반환해야 합니다. step은 0이나 음수일 수도 있습니다.',
         'function makeCounter(start, step) {\n  let value = start;\n  return () => ++value;\n}',
         'function makeCounter(start, step) { let value = start; return () => value += step; }',
         'function makeCounter(start, step) { let count = 0; return () => start + (++count) * step; }',
         [('basic', 'const a = makeCounter(0, 2);\nconst b = makeCounter(10, 3);\n\nconsole.log(a()); // 2\nconsole.log(b()); // 13\nconsole.log(a()); // 4', '2\n13\n4'),
          ('negative', 'const a = makeCounter(3, -2);\nconst b = makeCounter(8, -1);\nconsole.log(a());\nconsole.log(b());\nconsole.log(a());', '1\n7\n-1'),
          ('zero', 'const a = makeCounter(2, 0);\nconst b = makeCounter(7, 0);\nconsole.log(a());\nconsole.log(b());\nconsole.log(a());', '2\n7\n2')],
         ['step이 양수·0·음수인 경우 모두 정확히 누적합니다.', '각 카운터는 다른 카운터 호출에 영향을 받지 않습니다.'],
         ['function makeCounter(start, step) { return () => start += 1; }', 'let n; function makeCounter(start, step) { n = start; return () => n += step; }']),
        ('BUILD', '독립적인 두 개의 저금통',
         'makeAccount(start)를 구현하세요. 시작 잔액을 기억하는 함수를 반환합니다. 반환된 함수에 amount를 전달하면 잔액에 더한 뒤 새 잔액을 반환해야 합니다. 저금통마다 잔액은 독립적이며, 음수 잔액과 음수 증감액도 허용합니다. 함수 내부의 구현 방식은 자유입니다.',
         'function makeAccount(start) {\n  // 증감액을 받아 새 잔액을 반환하는 함수를 만들어주세요.\n}\n',
         'function makeAccount(start) { return amount => start += amount; }',
         'function makeAccount(start) { const balance = [start]; return amount => { balance[0] += amount; return balance[0]; }; }',
         [('basic', 'const travel = makeAccount(0);\nconst books = makeAccount(10);\n\nconsole.log(travel(3)); // 3 — 3만큼 저축\nconsole.log(books(-4)); // 6 — 4만큼 사용\nconsole.log(travel(2)); // 5 — 앞서 저축한 값에 누적', '3\n6\n5'),
          ('negative', 'const a = makeAccount(-2);\nconst b = makeAccount(5);\nconsole.log(b(0));\nconsole.log(a(-3));\nconsole.log(b(2));\nconsole.log(a(10));', '5\n-5\n7\n5')],
         ['양수·0·음수 증감액을 잔액에 정확히 반영합니다.', '두 저금통은 각각 독립적인 잔액을 유지합니다.'],
         ['function makeAccount(start) { return amount => start += Math.abs(amount); }', 'let balance; function makeAccount(start) { balance = start; return amount => balance += amount; }']),
    ]
    for kind, title, description, starter, reference, alternative, cases, requirements, wrong in specs:
        description += '\n\n함수만 작성하세요. 아래 테스트 코드가 작성한 함수 뒤에 붙어서 실행됩니다. 주석은 각 호출의 기대값입니다. 인수는 -1000~1000의 정수이며, 반환된 함수는 1~20회 호출됩니다.'
        tests = [dict(id=i, stdin='', code=code, expected=expected, requirements=['r1', 'r2']) for i, code, expected in cases]
        exercises.append(dict(kind=kind, test_mode='code', title=title, description=description,
            requirements=[dict(id=f'r{i+1}', text=t) for i, t in enumerate(requirements)],
            starter=starter, public_tests=tests[:1],
            hints=HINTS[kind],
            evaluation=dict(reference=reference, alternative=alternative,
                hidden_tests=tests[1:], read_answer='', wrong_solutions=[dict(code=w,
                    requirement=f'r{i+1}', failing_test='basic', reason=requirements[i] + ' 이 조건을 위반합니다.') for i, w in enumerate(wrong)])))
    return context, SetDraft(title='함수가 기억하는 작은 세계 · 함수 테스트', concept='호출별 독립적인 상태', exercises=exercises)
