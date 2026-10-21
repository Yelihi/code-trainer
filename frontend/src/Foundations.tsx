import { LoadingSkeleton } from './LoadingSkeleton';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom';
import CodeMirror from '@uiw/react-codemirror';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useResource } from './App';
import { CodeBlock, codeExtensions } from './CodeBlock';
import { FoundationCardArt } from './FoundationCardArt';
import { FoundationVisual } from './FoundationVisual';
import type { Frame } from './foundationTrace';
import { InlineMarkdown } from './Markdown';
import { AnimatedDetails } from './AnimatedDetails';
import { FoundationTestHelp } from './FoundationTestHelp';
import { AddToKnowledge } from './AddToKnowledge';

type Feedback = { question_id: string; understood: string; missing: string; correction: string };
type Check = { label: string; passed: boolean; status: string; detail: string };
type Job = { id: string; lesson_id: string; version: number; state: string; created_at: string; error: string; payload: { answers?: string[]; code?: string; test_code?: string }; result: { items?: Feedback[]; model_answers?: { id: string; prompt: string; answer: string }[]; checks?: Check[] } };
type Draft = { answers: string[]; code: string; test_code: string };
type Unit = { id: string; version: number; title: string; group: string; priority: 1 | 2 | 3; difficulty: '입문' | '보통' | '어려움'; summary: string; prerequisites: string[]; state: string; can_resume: boolean; running: boolean; revision: number };
type Lesson = Unit & { knowledge_added_at?: string | null; reading: { invariant: string; steps: [string, string][]; pitfall: string; tradeoff: string; case_study: string; experiment: string }; concept: string; complexity: string; application: string; requirements: string[]; test_hints: string[]; questions: { id: string; prompt: string }[]; starter: string; public_tests: string; test_starter: string; visualization: string; visual_frames?: Frame[]; visual_round?: boolean; sources: { title: string; url: string }[]; progress: (Draft & { revision: number }) | null; review: Job | null; attempt: Job | null; unlocked: boolean; completed: boolean; ai_available: boolean };
const statusLabels: Record<string, string> = { passed: '통과', ready: '검토 완료', failed: '보완 필요', error: '처리 중단', running: '진행 중', assertion_failed: '예상 값과 다름', insufficient_assertions: 'assertEqual 검증을 2개 이상 실행해주세요', invalid_tests: '검증 결과를 확인할 수 없습니다', compile_error: '컴파일 오류', runtime_error: '실행 오류', time_limit: '시간 초과', compile_time_limit: '컴파일 시간 초과' };

export function Foundations() {
  const { data, error, reload } = useResource<{ items: Unit[] }>('/foundations');
  const navigate = useNavigate();
  const [group, setGroup] = useState('전체');
  const [query, setQuery] = useState('');
  const [starting, setStarting] = useState('');
  const [startError, setStartError] = useState('');
  const visible = data?.items.filter(item => (group === '전체' || item.group === group) &&
    `${item.title} ${item.summary}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())) ?? [];
  async function startFresh(item: Unit) {
    setStarting(item.id); setStartError('');
    try {
      await api(`/foundations/${item.id}/restart`, 'POST', { version: item.version, revision: item.revision });
      navigate(`/foundations/${item.id}/practice`);
    } catch (e) { setStartError(errorMessage(e)); reload(); }
    finally { setStarting(''); }
  }
  return <main className="page foundations-page"><div className="breadcrumb">실험 기능 <span>/</span> 기초 구현 학습</div>
    <header className="foundation-heading"><div><span className="eyebrow">FOUNDATIONS / TYPESCRIPT</span><h1>설명하고,<br /><em>직접 구현하세요.</em></h1><p>자료구조부터 익숙한 메서드까지.<br />움직임을 살펴보고, 내 말과 코드로 이해를 확인합니다.</p></div><div className="foundation-path"><span><b>01</b> 내 말로 설명 <small>AI 피드백</small></span><span><b>02</b> 구현과 테스트 <small>직접 실행 · 검증</small></span><small>{data ? `${data.items.filter(i => i.state === 'passed').length} / ${data.items.length}개 단원 완료` : '—'}</small></div></header>
    <ErrorNotice error={error || startError} />{error && <button onClick={reload}>다시 불러오기</button>}
    <p className="muted foundation-start-note">새로 진행하면 작성 중인 답변·코드가 초기화됩니다. 제출·완료 기록은 그대로 보관됩니다.</p>
    {!data && !error && <LoadingSkeleton layout="catalog" label="단원을 불러오는 중…" />}
    {data && <div className="foundation-filters"><div className="foundation-filter-groups" role="group" aria-label="주제 선택">{['전체', '자료구조', '알고리즘', '메서드', '수학'].map(name => <button key={name} type="button" aria-pressed={group === name} onClick={() => setGroup(name)}>{name}</button>)}</div><label>단원 검색<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="개념이나 구현 주제" /></label></div>}
    {data && !visible.length && <p role="status" className="foundation-empty">일치하는 단원이 없습니다.</p>}
    {([1, 2, 3] as const).map(priority => {
      const items = visible.filter(item => item.priority === priority);
      if (!items.length) return null;
      const label = priority === 1 ? '핵심' : priority === 2 ? '확장' : '전문';
      return <section key={priority} className="foundation-category" aria-label={`${priority}단계 ${label}`}><div className="section-heading"><h2>{priority}단계 · {label}</h2><span className="muted">{items.filter(item => item.state === 'passed').length} / {items.length}개 완료</span></div><div className="foundation-catalog">{items.map(item => <article className="foundation-card" key={item.id} aria-label={item.title}>
        <div className="card-top"><span className="language-tag">{item.group} · {item.difficulty}</span><span className={item.state === 'passed' ? 'success-text' : 'muted'}>{item.running ? '검토 중' : item.state === 'passed' ? '✓ 완료 기록 있음' : item.can_resume ? '진행 중' : '시작 전'}</span></div>
        <div className="foundation-card-heading"><FoundationCardArt kind={item.id} /><h3><Link to={`/foundations/${item.id}`}>{item.title.split(' · ')[0]}</Link></h3></div><p>{item.title.includes(' · ') && <span className="foundation-card-description">{item.title.split(' · ').slice(1).join(' · ')}</span>}{item.summary}</p>
        <small>{item.prerequisites.length ? <>추천 선행: {item.prerequisites.map((id, index) => <span key={id}>{index > 0 && ', '}<Link to={`/foundations/${id}`}>{data?.items.find(i => i.id === id)?.title.split(' · ')[0] ?? id}</Link></span>)}</> : '바로 시작할 수 있어요'}</small>
        <div className="foundation-card-actions"><button disabled={!!starting || item.running} onClick={() => void startFresh(item)}>{starting === item.id ? '준비 중…' : '새로 진행'}</button>{item.can_resume && !starting ? <Link className="button primary" to={`/foundations/${item.id}/practice`}>이어 진행</Link> : <button disabled>이어 진행</button>}</div>
        <Link className="text-link foundation-concept-link" to={`/foundations/${item.id}`}>개념 먼저 살펴보기</Link>
      </article>)}</div></section>})}
  </main>;
}

export function FoundationLesson({ practice = false }: { practice?: boolean }) {
  const { id } = useParams();
  const { data, error, reload } = useResource<Lesson>(`/foundations/${id}`);
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <button onClick={reload}>다시 불러오기</button> : <LoadingSkeleton layout={practice ? "editor" : "article"} label="단원을 불러오는 중…" heading />}</main>;
  if (!practice) return <ConceptPage key={`${data.id}-${data.version}`} lesson={data} />;
  return <LessonWorkspace key={`${data.id}-${data.version}`} lesson={data} />;
}

function ConceptPage({ lesson }: { lesson: Lesson }) {
  return <main className="page foundation-lesson foundation-concept">
    <div className="breadcrumb"><Link to="/foundations">실험 기능 · 기초 구현 학습</Link><span>/</span>개념 탐구</div>
    <header className="foundation-lesson-heading"><div><span className="eyebrow">EXPLORE / {lesson.group}</span><h1>{lesson.title}</h1><p>{lesson.summary}</p></div><Link className="button primary" to={`/foundations/${lesson.id}/practice`}>{lesson.unlocked ? '실습 이어하기' : '설명·구현 시작'}</Link></header>
    <nav className="foundation-mode" aria-label="단원 화면"><span aria-current="page">개념 탐구</span><Link to={`/foundations/${lesson.id}/practice`}>설명과 구현</Link></nav>
    <div className="concept-intro"><span className="eyebrow">기억할 핵심 규칙</span><p><InlineMarkdown>{lesson.reading.invariant}</InlineMarkdown></p></div>
    <FoundationVisual kind={lesson.visualization} scenes={lesson.visual_frames} roundNodes={lesson.visual_round} />
    <p className="visual-experiment"><strong>이렇게 실험해보세요</strong><InlineMarkdown>{lesson.reading.experiment}</InlineMarkdown></p>
    <section className="concept-chapter"><div className="chapter-label"><span>01</span><h2>왜 이렇게 동작할까요?</h2></div><p className="concept-lead"><InlineMarkdown>{lesson.concept}</InlineMarkdown></p><div className="concept-steps">{lesson.reading.steps.map(([title, body], i) => <article key={title}><span className="concept-number">{i + 1}</span><h3>{title}</h3><p><InlineMarkdown>{body}</InlineMarkdown></p></article>)}</div></section>
    <section className="concept-chapter concept-cost"><div className="chapter-label"><span>02</span><h2>비용과 선택 기준</h2></div><div className="concept-cost-body"><strong><InlineMarkdown>{lesson.complexity}</InlineMarkdown></strong><p><InlineMarkdown>{lesson.reading.tradeoff}</InlineMarkdown></p></div></section>
    <aside className="concept-caution"><span className="eyebrow">자주 놓치는 부분</span><p><InlineMarkdown>{lesson.reading.pitfall}</InlineMarkdown></p></aside>
    <section className="concept-chapter"><div className="chapter-label"><span>03</span><h2>실제로 어디에 쓸까요?</h2></div><p className="concept-lead"><InlineMarkdown>{lesson.application}</InlineMarkdown></p><p><InlineMarkdown>{lesson.reading.case_study}</InlineMarkdown></p></section>
    <div className="foundation-sources">참고 자료 {lesson.sources.map(source => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title}</a>)}</div>
    <p className="muted">개념 학습만으로도 지도에 추가할 수 있습니다. 문제 통과 여부는 별도로 기록됩니다.</p>
    <AddToKnowledge path={`/foundations/${lesson.id}/knowledge?version=${lesson.version}`} addedAt={lesson.knowledge_added_at} />
    <footer className="concept-start"><div><h2>이제 내 말과 코드로 확인해볼까요?</h2><p className="muted">설명 피드백을 받고, 직접 구현한 코드와 테스트를 실행합니다.</p></div><Link className="button primary" to={`/foundations/${lesson.id}/practice`}>실습으로 이동</Link></footer>
  </main>;
}

function FeedbackView({ job }: { job: Job }) {
  return <div className="explanation-feedback"><ErrorNotice error={job.error} />{job.result.items?.map(item => <section key={item.question_id}>
    <h3><InlineMarkdown>{job.result.model_answers?.find(q => q.id === item.question_id)?.prompt ?? item.question_id}</InlineMarkdown></h3>
    {(['understood', 'missing', 'correction'] as const).map(key => item[key] && <p key={key}><strong>{key === 'understood' ? '이해한 내용' : key === 'missing' ? '보충할 내용' : '바로잡을 내용'}</strong><InlineMarkdown>{item[key]}</InlineMarkdown></p>)}
    <AnimatedDetails className="reference-answer" summary="기준 설명 보기"><div><span className="eyebrow">핵심을 이렇게 연결해보세요</span><p><InlineMarkdown>{job.result.model_answers?.find(q => q.id === item.question_id)?.answer ?? ''}</InlineMarkdown></p></div></AnimatedDetails>
  </section>)}</div>;
}

function ResultView({ job }: { job: Job }) {
  return <section className="foundation-result" aria-label="구현 검증 결과"><h3>{job.state === 'passed' ? '✓ 구현과 테스트를 모두 통과했습니다' : statusLabels[job.state] ?? job.state}</h3><ErrorNotice error={job.error} />
    {job.result.checks?.map(check => <div className="foundation-check" key={check.label}><span className={check.passed ? 'success-text' : 'error-text'}>{check.passed ? '✓' : '×'}</span><div><strong>{check.label}</strong><small>{check.passed ? '통과' : check.label.startsWith('오답 감지') && check.status === 'passed' ? '이 오류를 발견할 테스트를 추가해주세요.' : statusLabels[check.status] ?? check.status}</small>{check.detail && <pre>{check.detail}</pre>}</div></div>)}
    {job.state === 'passed' && <p><Link className="text-link" to="/me">나의 학습 기록에 저장되었습니다</Link></p>}
    {job.state === 'failed' && <p className="muted">{(job.result.checks?.length ?? 0) < 6 && '앞선 검사에서 중단되어 이후 항목은 실행하지 않았습니다. '}연산 비용은 해당 검사가 있는 단원에서만 확인합니다. 일반적인 시간·공간 복잡도는 자동 판정하지 않습니다.</p>}
  </section>;
}

function LessonWorkspace({ lesson }: { lesson: Lesson }) {
  const initial: Draft = { answers: lesson.progress?.answers ?? ['', ''], code: lesson.progress?.code ?? lesson.starter, test_code: lesson.progress?.test_code ?? lesson.test_starter };
  const [draft, setDraft] = useState(initial);
  const [saved, setSaved] = useState(JSON.stringify(initial));
  const revision = useRef(lesson.progress?.revision ?? 0);
  const [review, setReview] = useState(lesson.review);
  const [attempt, setAttempt] = useState(lesson.attempt);
  const [unlocked, setUnlocked] = useState(lesson.unlocked);
  const [step, setStep] = useState(lesson.unlocked ? 2 : 1);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [solution, setSolution] = useState('');
  const request = useRef({ key: '', id: '' });
  const extensions = useMemo(() => codeExtensions('typescript', true), []);
  const dirty = JSON.stringify(draft) !== saved;
  const blocker = useBlocker(dirty);
  const pending = review?.state === 'running' || attempt?.state === 'running';
  const oversized = draft.code.length > 24000 || draft.test_code.length > 12000;
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        if (review?.state === 'running') {
          const job = await api<Job>(`/foundation-reviews/${review.id}`, 'GET', undefined, controller.signal);
          setReview(job); if (job.state === 'ready') setUnlocked(true);
          if (job.state !== 'running') { request.current = { key: '', id: '' }; }
        }
        if (attempt?.state === 'running') {
          const job = await api<Job>(`/foundation-attempts/${attempt.id}`, 'GET', undefined, controller.signal);
          setAttempt(job); if (job.state !== 'running') { request.current = { key: '', id: '' }; }
        }
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
      if (!controller.signal.aborted) timer = setTimeout(poll, 2000);
    };
    timer = setTimeout(poll, 1000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [pending, review, attempt]);
  async function save() {
    const result = await api<{ revision: number }>(`/foundations/${lesson.id}/progress`, 'PUT', { ...draft, version: lesson.version, revision: revision.current });
    revision.current = result.revision; setSaved(JSON.stringify(draft));
  }
  async function act(action: 'save' | 'explain' | 'submit' | 'solution') {
    setBusy(action); setError('');
    try {
      await save();
      if (action === 'save') return;
      if (action === 'solution') { setSolution((await api<{ code: string }>(`/foundations/${lesson.id}/solution`)).code); return; }
      const payload = action === 'explain' ? { answers: draft.answers } : { code: draft.code, test_code: draft.test_code };
      const key = JSON.stringify({ action, ...payload });
      if (request.current.key !== key) request.current = { key, id: crypto.randomUUID() };
      const job = await api<Job>(`/foundations/${lesson.id}/${action}`, 'POST', { ...payload, version: lesson.version, request_id: request.current.id });
      if (action === 'explain') { setReview(job); if (job.state === 'ready') setUnlocked(true); } else setAttempt(job);
      if (job.state !== 'running') request.current = { key: '', id: '' };
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(''); }
  }
  const setAnswer = (index: number, text: string) => setDraft({ ...draft, answers: draft.answers.map((a, i) => i === index ? text : a) });
  return <main className="page foundation-lesson"><div className="breadcrumb"><Link to="/foundations">실험 기능 · 기초 구현 학습</Link><span>/</span>{lesson.group}</div>
    <header className="foundation-lesson-heading"><div><span className="eyebrow">TYPESCRIPT / {lesson.group}</span><h1>{lesson.title}</h1><p>{lesson.summary}</p></div><button disabled={!!busy || oversized} onClick={() => void act('save')}>{busy === 'save' ? '저장 중…' : dirty ? '변경 내용 저장' : '저장됨'}</button></header>
    <ErrorNotice error={error} />{oversized && <p className="notice error">구현은 24,000자, 테스트는 12,000자까지 저장할 수 있습니다.</p>}
    {blocker.state === 'blocked' && <div className="notice" role="alert"><p>저장하지 않은 내용이 있습니다.</p><button onClick={() => blocker.reset()}>계속 작성</button><button disabled={!!busy} onClick={async () => { setBusy('save'); try { await save(); blocker.proceed(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(''); } }}>저장하고 이동</button><button onClick={() => blocker.proceed()}>저장하지 않고 이동</button></div>}
    <nav className="foundation-mode" aria-label="단원 화면"><Link to={`/foundations/${lesson.id}`}>개념 탐구</Link><span aria-current="page">설명과 구현</span></nav>
    <div className="foundation-practice">
      <section className="foundation-work"><div className="foundation-steps" role="group" aria-label="학습 단계"><button aria-pressed={step === 1} onClick={() => setStep(1)}><b>01</b> 내 말로 설명 {unlocked && '✓'}</button><button aria-pressed={step === 2} disabled={!unlocked} onClick={() => setStep(2)}><b>02</b> 구현과 테스트 {(lesson.completed || attempt?.state === 'passed') && '✓'}</button></div>
      {step === 1 ? <><h2>어떻게 동작하는지 설명해보세요.</h2><p className="page-intro">문장 표현보다 개념을 봅니다. 피드백을 받으면 구현으로 넘어갈 수 있어요.</p>
        <form onSubmit={e => { e.preventDefault(); void act('explain'); }}>{lesson.questions.map((q, index) => <label className="explanation-question" key={q.id}><span>{index + 1}. <InlineMarkdown>{q.prompt}</InlineMarkdown></span><textarea value={draft.answers[index]} maxLength={3000} required rows={4} disabled={!!busy} onChange={e => setAnswer(index, e.target.value)} placeholder="이해한 내용을 내 말로 적어주세요." /><small>{draft.answers[index].length} / 3,000</small></label>)}
          <button className="primary" disabled={!!busy || pending || oversized || draft.answers.some(a => !a.trim())}>{review?.state === 'running' ? '설명을 검토하고 있어요…' : '설명 제출 · AI 피드백 받기'}</button>
        </form>
        {!lesson.ai_available && <p className="notice">AI 연결 후 설명을 검토할 수 있습니다. 지금 작성한 내용은 저장해둘 수 있어요.</p>}
        {review && <><p className="muted">{timestamp(review.created_at)} 제출 기준{JSON.stringify(review.payload.answers) !== JSON.stringify(draft.answers.map(a => a.trim())) && ' · 현재 입력과 다른 이전 설명의 피드백입니다.'}</p><FeedbackView job={review} /></>}
        {unlocked && <button className="primary foundation-next" onClick={() => setStep(2)}>피드백 확인 · 구현으로</button>}
      </> : <><h2>직접 구현하고 검증하세요.</h2><ol className="foundation-requirements">{lesson.requirements.map(text => <li key={text}><InlineMarkdown>{text}</InlineMarkdown></li>)}</ol>
        <AnimatedDetails className="foundation-examples" summary={<><span>공개 예제 살펴보기<small>호출 방법과 반환값 확인</small></span></>}><CodeBlock language="typescript" code={lesson.public_tests} /></AnimatedDetails>
        <div className="foundation-editor"><h3>구현 <small>TypeScript</small></h3><CodeMirror value={draft.code} theme="dark" extensions={extensions} height="330px" editable={!busy} onChange={code => setDraft(previous => ({ ...previous, code }))} onCreateEditor={view => view.contentDOM.setAttribute('aria-label', '구현 코드')} /></div>
        <div className="foundation-editor"><div className="foundation-editor-heading"><h3>내가 작성하는 테스트</h3><FoundationTestHelp starter={lesson.starter} example={lesson.public_tests} /></div><p className="muted">위 클래스·함수를 바로 호출하세요. import는 필요하지 않습니다. <code>assertEqual(실제 값, 예상 값)</code>을 2개 이상 작성하고, 정상 동작과 경계 조건을 확인하세요.</p><AnimatedDetails className="test-design-hints" summary={<><span>어떤 테스트를 작성할까요?<small>제출 전에 확인하는 테스트 설계 힌트</small></span></>}><p>정답 코드 대신 확인할 상황을 안내합니다. 예상 결과는 위 요구사항에서 직접 계산해보세요.</p><ol>{lesson.test_hints.map(hint => <li key={hint}><InlineMarkdown>{hint}</InlineMarkdown></li>)}</ol><p>빈 입력·최소 크기·연속 호출도 확인하고, 서로 다른 상황마다 시작 상태를 새로 준비하세요.</p></AnimatedDetails><CodeMirror value={draft.test_code} theme="dark" extensions={extensions} height="240px" editable={!busy} onChange={test_code => setDraft(previous => ({ ...previous, test_code }))} onCreateEditor={view => view.contentDOM.setAttribute('aria-label', '테스트 코드')} /></div>
        <p className="muted">동작과 테스트의 오류 감지 능력을 검사합니다. 시간 복잡도·내부 구현 방식은 자동 판정하지 않습니다.</p>
        <div className="foundation-actions"><button className="primary" disabled={!!busy || pending || oversized || !draft.test_code.trim() || !draft.code.trim()} onClick={() => void act('submit')}>{attempt?.state === 'running' ? '격리 환경에서 검증 중…' : '구현과 테스트 제출'}</button><button disabled={!!busy || pending || oversized} onClick={() => void act('solution')}>참고 풀이 보기</button></div>
        <small className="muted">참고 풀이를 열면 학습 기록에 ‘풀이 참고’로 남습니다.</small>
        {solution && <AnimatedDetails initiallyOpen summary="참고 풀이"><CodeBlock language="typescript" code={solution} /></AnimatedDetails>}
        {attempt && <><p className="muted">{timestamp(attempt.created_at)} 제출 기준{(attempt.payload.code !== draft.code || attempt.payload.test_code !== draft.test_code.trim()) && ' · 현재 편집 내용과 다릅니다.'}</p><ResultView job={attempt} /></>}
      </>}
      {pending && <p className="notice" role="status">검토가 끝나면 이 화면에 표시됩니다. 다른 페이지로 이동해도 제출은 계속 처리됩니다.</p>}
      </section>
    </div>
  </main>;
}

export function FoundationRecords() {
  const { data, error, reload } = useResource<{ items: { id: string; lesson_id: string; version: number; title: string; created_at: string; assistance: string; feedback: Job['result'] }[] }>('/me/foundations');
  return <section className="foundation-records"><div className="section-heading"><div><span className="eyebrow">FOUNDATIONS</span><h2>기초 구현 학습 기록</h2></div><Link className="text-link" to="/foundations">단원 보기</Link></div><p className="muted">구현과 테스트를 통과하면 자동으로 쌓입니다. 설명 피드백도 함께 보관합니다.</p><ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="list" label="기록을 불러오는 중…" />}
    {data?.items.length === 0 && <p className="muted">완료한 기초 구현 단원이 아직 없습니다.</p>}
    {data?.items.map(item => <article className="foundation-record" key={item.id}><div><Link to={`/foundations/${item.lesson_id}`}>{item.title}</Link><small>{timestamp(item.created_at)} · v{item.version} · {item.assistance === 'solution' ? '풀이 참고' : '설명 피드백 참고'}</small></div><AnimatedDetails summary="설명에서 보완한 내용">{item.feedback.items?.map(f => <p key={f.question_id}><InlineMarkdown>{[f.missing, f.correction].filter(Boolean).join(' ') || '이 항목에서 추가로 지적된 내용이 없습니다.'}</InlineMarkdown></p>)}</AnimatedDetails></article>)}
  </section>;
}
