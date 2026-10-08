import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage, isPending, languages, difficulties, safeSourceUrl, type Generation, type LearningContext } from './api';
import { ErrorNotice, GenerationStatus, useApp, useResource } from './App';
import { CodeBlock } from './CodeBlock';
import { Markdown } from './Markdown';

function useCourse(id?: string) {
  const resource = useResource<LearningContext>(`/contexts/${id}`);
  const [requested, setRequested] = useState<Generation | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const requestId = useRef({ unit: '', id: crypto.randomUUID() });
  const jobs = [resource.data?.generation, ...(resource.data?.unit_generations ?? [])].filter((job): job is Generation => !!job);
  if (requested && requested.context_id === id) {
    const index = jobs.findIndex(job => job.unit_id === requested.unit_id);
    if (index >= 0) jobs[index] = requested; else jobs.push(requested);
  }
  const pending = jobs.find(isPending);
  const { reload } = resource;
  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController();
    const timer = setInterval(() => {
      api<Generation>(`/generations/${pending.id}`, 'GET', undefined, controller.signal)
        .then(value => { setRequested(value); if (!isPending(value)) reload(); })
        .catch(error => { if (!controller.signal.aborted) setActionError(errorMessage(error)); });
    }, 2000);
    return () => { clearInterval(timer); controller.abort(); };
  }, [pending, reload]);
  async function generate(unitId?: string) {
    if (!resource.data) return;
    if (requestId.current.unit !== (unitId ?? '')) requestId.current = { unit: unitId ?? '', id: crypto.randomUUID() };
    setBusy(true); setActionError('');
    try {
      setRequested(await api<Generation>('/generations', 'POST', { request_id: requestId.current.id, source_kind: 'context', context_id: id, unit_id: unitId, language: resource.data.language }));
      requestId.current.id = crypto.randomUUID();
    } catch (error) { setActionError(errorMessage(error)); } finally { setBusy(false); }
  }
  return { ...resource, jobs, pending, busy, actionError, setActionError, generate };
}

function UnitPractice({ course, unitId, disabled = false }: { course: ReturnType<typeof useCourse>; unitId: string; disabled?: boolean }) {
  const { health } = useApp();
  const [message, setMessage] = useState('');
  const [reporting, setReporting] = useState(false);
  const [reported, setReported] = useState('');
  const [error, setError] = useState('');
  const set = course.data?.sets?.find(set => set.unit_id === unitId);
  const generation = course.jobs.find(job => job.unit_id === unitId);
  async function report() {
    if (!generation) return;
    setReporting(true); setError('');
    try {
      await api(`/generations/${generation.id}/reports`, 'POST', { message });
      setReported(generation.id);
    } catch (error) { setError(errorMessage(error)); } finally { setReporting(false); }
  }
  if (set) return <div className="unit-practice">{set.withdrawn ? <p className="muted">문제 제공 중단</p> : <Link className="button" to={`/practice/${set.id}`}>연습 {set.completed} / {set.total} →</Link>}</div>;
  return <section className="unit-practice" aria-label="단원 문제 생성">
    <button className="primary" disabled={disabled || course.busy || !!course.pending || health?.ai === false || health?.sandbox === false} onClick={() => void course.generate(unitId)}>
      {generation && isPending(generation) ? '문제 생성 중…' : generation?.state === 'failed' ? '문제 생성 다시 시도 →' : '이 단원 문제 생성 →'}
    </button>
    {course.pending && course.pending.unit_id !== unitId && <p className="muted">다른 단원을 생성 중입니다. 개념 학습은 계속할 수 있습니다.</p>}
    {health && (!health.ai || !health.sandbox) && <p className="notice">문제를 생성하려면 AI와 실행 환경을 연결해주세요.</p>}
    {generation && (isPending(generation) || generation.state === 'failed') && <GenerationStatus generation={generation} />}
    {generation?.state === 'failed' && <details className="generation-report"><summary>문제 생성 오류 제보</summary>
      {reported === generation.id ? <p role="status">제보를 저장했습니다. 나의 기록에서 확인할 수 있습니다.</p> : <form onSubmit={event => { event.preventDefault(); void report(); }}>
        <label>어떤 문제가 있었나요?<textarea required minLength={5} maxLength={2000} value={message} onChange={event => setMessage(event.target.value)} /></label>
        <p className="muted">작업 ID와 진단 로그를 함께 저장합니다. 나의 기록에서 확인할 수 있습니다.</p>
        <button disabled={reporting}>{reporting ? '저장 중…' : '제보 보내기'}</button><ErrorNotice error={error} />
      </form>}
    </details>}
  </section>;
}

export function Context() {
  const { id } = useParams();
  const navigate = useNavigate();
  const course = useCourse(id);
  const { data, error, reload, busy, actionError, setActionError, generate, pending } = course;
  const [deleting, setDeleting] = useState(false);
  const { health } = useApp();
  async function remove() {
    if (!data || !window.confirm(`“${data.title}” 자료를 삭제할까요?\n\n이 자료의 개념 설명, 문제 세트, 저장한 코드, 제출·제보 기록이 함께 삭제됩니다. 나의 기록에 생성해 둔 학습 요약과 생성 날짜는 유지됩니다. 삭제 후에는 되돌릴 수 없습니다.`)) return;
    setDeleting(true); setActionError('');
    try {
      await api(`/contexts/${data.id}`, 'DELETE', {});
      void navigate('/', { replace: true });
    } catch (error) { setActionError(errorMessage(error)); }
    finally { setDeleting(false); }
  }
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <button onClick={reload}>다시 불러오기</button> : <p role="status">학습 과정을 불러오는 중…</p>}</main>;
  const units = data.units ?? [];
  const sets = data.sets ?? [];
  const missing = units.filter(unit => !sets.some(set => set.unit_id === unit.id));
  return <main className="page course-page">
    <div className="breadcrumb"><Link to="/">학습 공간</Link><span>/</span> 학습 과정</div>
    <div className="section-heading"><span className="language-tag">{languages[data.language]} · {difficulties[data.difficulty ?? 'beginner']}</span>
      <button className="delete-material" onClick={() => void remove()} disabled={busy || deleting || !!pending}>{deleting ? '삭제 중…' : '자료 삭제'}</button>
    </div>
    <ErrorNotice error={actionError} />
    <h1>{data.title}</h1><p className="page-intro">{data.description}</p>
    <section className="course-intro"><span className="eyebrow">LEARN, THEN PRACTICE</span><Markdown language={data.language}>{data.summary}</Markdown>
      {safeSourceUrl(data.source_url) && <a className="text-link" href={safeSourceUrl(data.source_url)} target="_blank" rel="noreferrer">학습 자료 출처 ↗</a>}
    </section>
    <div className="section-heading"><div><span className="eyebrow">YOUR LEARNING PATH</span><h2>{units.length ? `${units.length}개 단원으로 이어지는 학습` : '개념별 학습 과정'}</h2></div><span className="muted">{units.length - missing.length} / {units.length} 세트 준비</span></div>
    {!units.length && <p className="notice">이전 방식으로 만든 자료입니다. 저장된 개념을 바탕으로 학습 순서와 상세 설명을 준비할 수 있습니다. 기존 문제와 풀이 기록은 유지됩니다.</p>}
    <ol className="course-units">{units.map((unit, index) => {
      return <li key={unit.id} className="course-unit"><span className="unit-number">{String(index + 1).padStart(2, '0')}</span><div>
        <div className="chips">{unit.concepts.map(concept => <span key={concept}>{concept}</span>)}</div>
        <h3><Link to={`/learn/${data.id}/units/${unit.id}`}>{unit.title}</Link></h3><p>{unit.objective}</p>
        <p className="unit-rationale">{unit.rationale}</p>
        {!!unit.prerequisites.length && <p className="muted">먼저 배울 내용: {unit.prerequisites.map(p => units.find(u => u.id === p)?.title).join(' · ')}</p>}
        <div className="unit-actions"><Link className="button primary" to={`/learn/${data.id}/units/${unit.id}`}>개념 학습 →</Link>

        </div>
        <UnitPractice course={course} unitId={unit.id} disabled={deleting} />
      </div></li>;
    })}</ol>
    {!units.length && <>
      {course.jobs.filter(job => !job.unit_id).map(job => <GenerationStatus key={job.id} generation={job} />)}
      <button className="primary" onClick={() => void generate()} disabled={busy || deleting || !!pending || health?.ai === false}>
        {busy ? '요청 중…' : '학습 과정 구성하기 →'}
      </button>
    </>}
    {!!sets.filter(set => !set.unit_id).length && <section className="legacy-sets"><h2>이전에 만든 연습</h2><div className="set-list">{sets.filter(set => !set.unit_id).map(set => <div className="set-row" key={set.id}><div><h3>{set.title}</h3><span className="muted">{set.completed} / {set.total} 단계 완료</span></div>{!set.withdrawn && <Link className="button" to={`/practice/${set.id}`}>이어서 풀기 →</Link>}</div>)}</div></section>}
  </main>;
}

export function Lesson() {
  const { id, unitId } = useParams();
  const course = useCourse(id);
  const { data, error, reload, actionError } = course;
  useEffect(() => { window.scrollTo(0, 0); }, [id, unitId]);
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <button onClick={reload}>다시 불러오기</button> : <p role="status">개념을 불러오는 중…</p>}</main>;
  const units = data.units ?? [];
  const index = units.findIndex(unit => unit.id === unitId);
  const unit = units[index];
  if (!unit) return <main className="page"><h1>학습 내용을 찾을 수 없습니다.</h1><Link to={`/learn/${id}`}>학습 과정으로 돌아가기</Link></main>;
  return <main className="page lesson-page">
    <div className="breadcrumb"><Link to={`/learn/${id}`}>{data.title}</Link><span>/</span> 개념 학습</div>
    <div className="lesson-layout"><aside className="lesson-outline"><span className="eyebrow">LEARNING PATH</span>
      <nav aria-label="학습 단원">{units.map((item, i) => <Link key={item.id} to={`/learn/${id}/units/${item.id}`} aria-current={item.id === unit.id ? 'page' : undefined}><span>{String(i + 1).padStart(2, '0')}</span>{item.title}</Link>)}</nav>
      <nav className="lesson-toc" aria-label="이 페이지의 목차">{unit.lesson.map((section, i) => <a key={i} href={`#section-${i}`}>{section.title}</a>)}<a href="#checkpoints">이해 확인</a></nav>
      <Link className="text-link" to={`/learn/${id}`}>← 전체 학습 과정</Link>
    </aside><article className="lesson-article" key={unit.id}>
      <header><span className="eyebrow">LESSON {String(index + 1).padStart(2, '0')} / {String(units.length).padStart(2, '0')}</span><h1>{unit.title}</h1><p className="lesson-objective">{unit.objective}</p>
        {!!unit.prerequisites.length && <div className="lesson-prerequisites">먼저 읽기: {unit.prerequisites.map(p => <Link key={p} to={`/learn/${id}/units/${p}`}>{units.find(u => u.id === p)?.title}</Link>)}</div>}
      </header>
      {unit.lesson.map((section, i) => <section id={`section-${i}`} className="lesson-section" key={i}><span className="eyebrow">{String(i + 1).padStart(2, '0')}</span><h2>{section.title}</h2><Markdown language={data.language}>{section.body}</Markdown>
        {section.code && <figure className="lesson-example"><figcaption>{languages[data.language]} · {difficulties[data.difficulty ?? 'beginner']} · 예제</figcaption><CodeBlock code={section.code} language={data.language} />{section.output && <div className="lesson-output"><small>실행 결과</small><pre>{section.output}</pre></div>}</figure>}
        {section.walkthrough && <div className="lesson-walkthrough"><h3>차근차근 따라가기</h3><Markdown language={data.language}>{section.walkthrough}</Markdown></div>}
      </section>)}
      <section className="lesson-section"><h2>자주 헷갈리는 지점</h2><ul className="lesson-pitfalls">{unit.pitfalls.map(item => <li key={item}><Markdown language={data.language}>{item}</Markdown></li>)}</ul></section>
      <section id="checkpoints" className="lesson-section"><span className="eyebrow">CHECK YOUR UNDERSTANDING</span><h2>문제로 넘어가기 전에</h2><p>먼저 스스로 설명해본 뒤 질문을 열어 해설을 확인하세요.</p>{unit.checkpoints.map((item, i) => <details className="lesson-checkpoint" key={i}><summary>{item.question}</summary><Markdown language={data.language}>{item.answer}</Markdown></details>)}</section>
      <section className="lesson-practice"><span className="eyebrow">PUT IT INTO CODE</span><h2>이제 직접 풀어볼 차례</h2><p>이 단원의 개념을 READ → FIX → MODIFY → BUILD로 연습합니다. 막히면 언제든 이 페이지로 돌아오세요.</p>
        <ErrorNotice error={actionError} /><UnitPractice key={unit.id} course={course} unitId={unit.id} />
      </section>
      <nav className="lesson-pagination" aria-label="이전 다음 단원"><span>{index > 0 && <Link to={`/learn/${id}/units/${units[index - 1].id}`}>← {units[index - 1].title}</Link>}</span><span>{index < units.length - 1 && <Link to={`/learn/${id}/units/${units[index + 1].id}`}>{units[index + 1].title} →</Link>}</span></nav>
    </article></div>
  </main>;
}
