import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage, languages, type Language } from './api';

type Evidence = { id: string; root_key: string; root_label: string; framework: boolean; set_id: string; context_id: string; unit_id: string | null; withdrawn: boolean; deleted?: boolean; title: string; kind: string };
type Summary = {
  state: 'empty' | 'stale' | 'running' | 'ready' | 'failed'; error: string; updated_at: string | null; ai_available: boolean;
  exercises: Evidence[]; current_passed_count: number; created_at: string | null; record_id: string | null; records: { id: string; created_at: string }[];
  concepts: { root_key: string; name: string; outcomes: { summary: string; exercise_ids: string[] }[] }[];
};

function recordDate(value: string) {
  return new Date(value).toLocaleString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function AnimatedDetails({ summary, children, className = '', initiallyOpen = false }: {
  summary: ReactNode; children: ReactNode; className?: string; initiallyOpen?: boolean;
}) {
  const animation = useRef<Animation | null>(null);
  useEffect(() => () => animation.current?.cancel(), []);
  return <details className={`learning-disclosure ${className}`} open={initiallyOpen}>
    <summary onClick={event => {
      event.preventDefault();
      const details = event.currentTarget.parentElement as HTMLDetailsElement;
      const opening = details.dataset.expanded === undefined ? !details.open : details.dataset.expanded !== 'true';
      const from = details.getBoundingClientRect().height;
      animation.current?.cancel();
      animation.current = null;
      details.style.height = '';
      details.style.overflow = '';
      delete details.dataset.expanded;
      details.open = opening;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const to = details.getBoundingClientRect().height;
      details.open = true;
      details.dataset.expanded = String(opening);
      details.style.overflow = 'clip';
      details.style.height = `${from}px`;
      const next = details.animate({ height: [`${from}px`, `${to}px`] }, {
        duration: 260, easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      });
      animation.current = next;
      next.onfinish = () => {
        if (animation.current !== next) return;
        details.open = opening;
        details.style.height = '';
        details.style.overflow = '';
        delete details.dataset.expanded;
        animation.current = null;
      };
    }}>{summary}</summary>
    {children}
  </details>;
}

function ProblemLinks({ exercises }: { exercises: Evidence[] }) {
  return <ul>{exercises.map(exercise => <li key={exercise.id}>
    <span className="success-text">✓ 통과</span>{exercise.deleted || exercise.withdrawn ? <span>{exercise.kind} · {exercise.title} ({exercise.deleted ? '학습 자료 삭제됨' : '제공 중단'})</span> :
      <Link to={`/practice/${exercise.set_id}?exercise=${exercise.id}`}>{exercise.kind} · {exercise.title} →</Link>}
    {!exercise.deleted && <Link className="text-link" to={exercise.unit_id ? `/learn/${exercise.context_id}/units/${exercise.unit_id}` : `/learn/${exercise.context_id}`}>개념 다시 읽기</Link>}
  </li>)}</ul>;
}

export function LearningMap() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const [recordId, setRecordId] = useState('');
  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const value = await api<Summary>(`/me/learning-summary${recordId ? '?record_id=' + encodeURIComponent(recordId) : ''}`, 'GET', undefined, signal);
      setData(value); setError('');
    } catch (error) { if (!signal?.aborted) setError(errorMessage(error)); }
  }, [recordId]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  useEffect(() => {
    if (data?.state !== 'running') return;
    const controller = new AbortController();
    const timer = window.setInterval(() => { void load(controller.signal); }, 2000);
    return () => { window.clearInterval(timer); controller.abort(); };
  }, [data?.state, load]);
  async function summarize() {
    setStarting(true); setError('');
    try { setData(await api<Summary>('/me/learning-summary', 'POST', {})); setRecordId(''); }
    catch (error) { setError(errorMessage(error)); }
    finally { setStarting(false); }
  }
  const pending = starting || data?.state === 'running';
  const roots = [...new Map((data?.exercises ?? []).map(item => [item.root_key, item])).values()];
  const cited = new Set(data?.concepts.flatMap(concept => concept.outcomes.flatMap(outcome => outcome.exercise_ids)));
  const remaining = data?.exercises.filter(exercise => !cited.has(exercise.id)) ?? [];
  return <>
    <p className="page-intro learning-map-intro">문제를 풀며 쌓은 배움을, 연결된 개념으로 돌아보세요.</p>
    <section className="learning-record-panel" aria-labelledby="learning-record-heading" aria-busy={pending}>
      <header className="learning-record-header">
        <div><h2 id="learning-record-heading">학습 기록</h2><p>통과한 풀이에서 확인한 내용을 AI가 정리했어요.</p></div>
        {data?.state === 'ready' && !pending ? <span className="learning-record-status"><span aria-hidden="true">✓</span> 최신 기록 반영됨</span> :
          !!data?.current_passed_count && <button className="primary" disabled={pending || !data.ai_available} onClick={() => void summarize()}>
            {pending ? '배운 내용 정리 중…' : data.state === 'failed' ? '정리 다시 시도' : 'AI로 배운 내용 정리'}
          </button>}
      </header>
      <div className="learning-record-body">
        {data?.records.length ? <div className="learning-record-picker">
          <label htmlFor="learning-record-select">기록 선택 <span>{data.records.length}개의 기록</span></label>
          <div className="learning-record-select">
            <select id="learning-record-select" value={recordId} onChange={event => setRecordId(event.target.value)} aria-describedby="learning-record-date">
              <option value="">최근 기록 · {recordDate(data.records[0].created_at)}</option>
              {data.records.slice(1).map(record => <option key={record.id} value={record.id}>{recordDate(record.created_at)}</option>)}
            </select>
            <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="m6 9 6 6 6-6" /></svg>
          </div>
        </div> : <p className="learning-record-placeholder">{data ? '첫 학습 기록을 기다리고 있어요.' : '학습 기록을 불러오는 중…'}</p>}
        <dl className="learning-record-stats" aria-label="선택한 기록의 학습 현황">
          <div><dt>통과한 문제</dt><dd>{data?.exercises.length ?? '—'}<span>개</span></dd></div>
          <div><dt>정리한 개념</dt><dd>{data?.concepts.length ?? '—'}<span>개</span></dd></div>
        </dl>
      </div>
      <footer className="learning-record-footer">
        <p id="learning-record-date">{data?.created_at ? <>기록 생성일 <time dateTime={data.created_at}>{recordDate(data.created_at)}</time></> : '정리가 완료되면 생성 날짜와 함께 저장됩니다.'}</p>
        <span>자료를 삭제해도 이 기록은 보관됩니다.</span>
      </footer>
    </section>
    {error && <p className="notice error" role="alert">{error} <button onClick={() => void load()}>다시 불러오기</button></p>}
    {data?.error && <p className="notice error" role="alert">{data.error} 통과 기록은 그대로 보관되어 있습니다.</p>}
    {!data && !error && <p role="status">학습 기록을 불러오는 중…</p>}
    {pending && <p role="status">비슷한 개념을 연결하고 문제별 학습 내용을 정리하고 있습니다. 다른 페이지로 이동해도 계속 진행됩니다.</p>}
    {data?.state === 'stale' && <p className="muted">아직 정리하지 않은 통과 기록이 있습니다. 위 버튼으로 학습 지도를 만들어보세요.</p>}
    {data && !data.ai_available && <p className="muted">AI 설정 후 학습 내용을 정리할 수 있습니다. 통과한 문제는 아래에서 확인하세요.</p>}
    {data?.exercises.some(exercise => exercise.deleted) && <p className="muted">삭제된 학습 자료의 내용도 기록에 보관되어 있습니다. 삭제된 문제로는 이동할 수 없습니다.</p>}
    {data?.state === 'empty' && !data.record_id && <div className="empty-state"><h2>아직 통과한 문제가 없습니다</h2><p>문제를 풀고 Submit을 통과하면 배운 내용을 정리할 수 있습니다.</p><Link className="button" to="/">학습 공간으로 →</Link></div>}
    <div className="knowledge-tree" key={data?.record_id ?? 'pending'}>{roots.map(root => {
      const concepts = data?.concepts.filter(concept => concept.root_key === root.root_key) ?? [];
      if (!concepts.length) return null;
      return <AnimatedDetails className="knowledge-root" initiallyOpen key={root.root_key} summary={<><span aria-hidden="true">▤ </span>{root.framework ? root.root_label : languages[root.root_label as Language] ?? root.root_label}<small>{root.framework ? '프레임워크 · 분류' : '언어'} · {concepts.length}개 개념</small></>}>
        <ul>{concepts.map(concept => <li key={concept.name}><AnimatedDetails initiallyOpen summary={<>{concept.name}<small>{concept.outcomes.length}가지 학습 내용</small></>}>
          {concept.outcomes.map((outcome, index) => <section className="knowledge-unit" key={index}>
            <p className="learning-outcome">{outcome.summary}</p>
            <AnimatedDetails summary={<>근거가 된 통과 문제 · {outcome.exercise_ids.length}개</>}>
              <ProblemLinks exercises={data!.exercises.filter(exercise => outcome.exercise_ids.includes(exercise.id))} />
            </AnimatedDetails>
          </section>)}
        </AnimatedDetails></li>)}</ul>
      </AnimatedDetails>;
    })}</div>
    {!!remaining.length && <AnimatedDetails className="knowledge-root knowledge-unit" summary={<>{data?.state === 'ready' ? '아직 요약에 연결되지 않은 통과 문제' : '통과한 문제'} · {remaining.length}개</>}><ProblemLinks exercises={remaining} /></AnimatedDetails>}
  </>;
}
