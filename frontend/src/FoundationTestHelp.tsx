import { useId, useRef, useState } from 'react';
import { CodeBlock } from './CodeBlock';

export function FoundationTestHelp({ starter, example }: { starter: string; example: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  const [kind, setKind] = useState(/\bclass\s+\w+/.test(starter) ? 'class' : 'function');
  return <><button className="help-button" type="button" aria-label="테스트 작성 도움말" aria-haspopup="dialog" onClick={() => dialog.current?.showModal()}>?</button>
    <dialog ref={dialog} className="foundation-help" aria-labelledby={title}>
      <header><div><span className="eyebrow">TESTING GUIDE</span><h2 id={title}>테스트, 이렇게 작성하세요</h2></div><button type="button" aria-label="도움말 닫기" onClick={() => dialog.current?.close()}>닫기</button></header>
      <p>구현 코드와 테스트는 함께 실행됩니다. <strong>import나 테스트 라이브러리 설치 없이</strong> 구현한 클래스·함수를 이름으로 바로 사용할 수 있어요.</p>
      <div className="help-flow" aria-label="테스트의 세 단계"><span><b>1</b> 준비<small>새 상태·입력</small></span><span><b>2</b> 실행<small>메서드·함수 호출</small></span><span><b>3</b> 검증<small>실제 값과 예상 값 비교</small></span></div>
      <div className="foundation-steps" role="group" aria-label="작성 방식"><button type="button" aria-pressed={kind === 'class'} onClick={() => setKind('class')}>클래스 테스트</button><button type="button" aria-pressed={kind === 'function'} onClick={() => setKind('function')}>함수 테스트</button></div>
      {kind === 'class' ? <section><h3>객체를 만들고, 같은 객체의 변화를 관찰하세요.</h3><p><code>new 클래스명()</code>으로 시작합니다. 메서드를 호출한 뒤 반환값과 남은 상태를 확인하세요. 독립적인 상황은 새 객체로 준비하면 앞 테스트의 영향을 받지 않습니다.</p><CodeBlock language="typescript" code={'// 작성 방식 예시: Stack 단원의 공개 API\nconst sample = new Stack(); // 1. 준비\nsample.push(10);            // 2. 상태를 바꾸는 호출\nassertEqual(sample.size(), 1); // 3. 상태 확인\nassertEqual(sample.pop(), 10); // 호출 결과 확인\n\n// 별도 상황은 새 인스턴스로 시작\nconst empty = new Stack();\nassertEqual(empty.pop(), undefined);'} /><p className="muted">클래스 이름과 메서드는 단원마다 다릅니다. 아래 현재 단원의 예제에 맞춰 작성하세요. 반환형이 void인 메서드는 호출 후 다른 조회 메서드로 상태를 확인합니다.</p></section>
        : <section><h3>입력을 준비하고, 반환값을 비교하세요.</h3><p>함수에는 <code>new</code>를 붙이지 않습니다. 입력을 전달하고 결과를 <code>assertEqual</code>의 첫 번째 인자에 넣습니다. 콜백을 받는 함수는 요구사항의 인자 순서도 확인하세요.</p><CodeBlock language="typescript" code={'// 작성 방식 예시: 이진 탐색 단원의 공개 API\nconst values = [2, 5, 9]; // 1. 준비: 정렬된 입력\nconst actual = binarySearch(values, 5); // 2. 실행\nassertEqual(actual, 1); // 3. 예상 인덱스와 비교\nassertEqual(binarySearch([], 5), -1); // 빈 입력\n\n// 원본 유지가 요구된다면 호출 후에도 확인\nassertEqual(values, [2, 5, 9]);'} /><p className="muted">이 예시는 작성 형식을 설명합니다. 현재 단원에서 정의한 함수 이름·매개변수·반환형으로 바꿔 사용하세요.</p></section>}
      <section className="help-current"><h3>현재 단원의 실행 예시</h3><CodeBlock language="typescript" code={example} /><p>이 공개 예제를 출발점으로 다른 입력과 호출 순서를 추가하세요. 예제를 복사하는 것만으로 모든 오류를 발견할 수는 없습니다.</p></section>
      <section><h3>assertEqual의 두 인자</h3><CodeBlock language="typescript" code={'assertEqual(실제로_계산된_값, 요구사항에서_예상한_값);\n// 숫자·boolean·문자열·undefined·숫자 배열을 비교할 수 있어요.\n// 예: assertEqual([1, 2], [1, 2]);'} /><p>숫자와 문자열은 구분하고, 배열은 순서와 내용으로 비교합니다. 객체 자체나 함수 참조 대신 반환값·크기·배열처럼 관찰 가능한 결과를 비교하세요. 예상 값에 같은 구현을 다시 호출하면 그 구현의 오류를 발견하기 어렵습니다.</p></section>
      <section><h3>어떤 테스트가 충분한가요?</h3><ul><li>실제로 실행되는 <code>assertEqual</code>이 최소 2개 필요합니다.</li><li>정상 입력에 더해 빈 상태, 중복값, 연속 호출 등 요구사항의 경계를 확인하세요.</li><li>테스트는 내 구현과 기준 구현에서 모두 통과해야 합니다.</li><li>의도적으로 잘못된 구현에서는 실패해야 합니다. 테스트 입력창 위의 설계 힌트에서 확인할 상황을 살펴보세요.</li></ul><p>개수만 늘리는 것보다 서로 다른 동작을 구별하는 테스트가 중요합니다. <code>console.log</code>나 주석은 검증 횟수에 포함되지 않습니다.</p></section>
      <footer><button type="button" className="primary" onClick={() => dialog.current?.close()}>이해했어요 · 작성으로 돌아가기</button></footer>
    </dialog>
  </>;
}
