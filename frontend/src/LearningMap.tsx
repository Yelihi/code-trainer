import { useEffect, useState } from 'react';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { KnowledgeExplorer } from './KnowledgeExplorer';
import type { KnowledgeGraph } from './knowledgeGraph';
import './knowledgeGraph.css';

function recordDate(value: string) {
  return new Date(value).toLocaleString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function LearningMap() {
  const [data, setData] = useState<KnowledgeGraph | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const [recordId, setRecordId] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setError(''); setData(null);
    async function load() {
      try {
        const value = await api<KnowledgeGraph>(`/me/knowledge-graph${recordId ? '?record_id=' + encodeURIComponent(recordId) : ''}`, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setData(value);
        if (value.state === 'running') timer = setTimeout(() => void load(), 2000);
      } catch (error) { if (!controller.signal.aborted) setError(errorMessage(error)); }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [recordId, revision]);

  async function summarize() {
    setStarting(true); setError('');
    try {
      await api('/me/learning-summary', 'POST', {});
      setRecordId(''); setRevision(value => value + 1);
    } catch (error) { setError(errorMessage(error)); }
    finally { setStarting(false); }
  }
  const pending = starting || data?.state === 'running';
  const concepts = data?.nodes.filter(node => node.kind === 'concept').length ?? 0;
  return <main className="page graph-page">
    <div className="breadcrumb"><Link to="/">Workspace</Link><span>/</span> 관계<span>/</span> 지식 그래프</div>
    <header className="graph-page-heading"><div><span className="eyebrow">A MAP OF WHAT YOU KNOW</span><h1>배움은, 서로 연결됩니다.</h1><p>학습 화면에서 직접 추가한 개념을 따라 나만의 지식 지도를 탐색하세요.</p></div>
      <button className="primary" disabled={!data?.current_passed_count || pending || !data.ai_available || data.state === 'ready'} onClick={() => void summarize()}>{pending ? '풀이 기록 정리 중…' : data?.state === 'ready' ? '최신 풀이 기록 반영됨' : 'AI로 풀이 기록 정리'}</button>
    </header>
    <div className="graph-overview"><dl><div><dt>정리한 개념</dt><dd>{data ? concepts : '—'}</dd></div><div><dt>학습 단원 · 노트</dt><dd>{data ? data.nodes.length - concepts : '—'}</dd></div><div><dt>연결</dt><dd>{data?.edges.length ?? '—'}</dd></div><div><dt>통과 문제</dt><dd>{data?.exercises.length ?? '—'}</dd></div></dl>
      <label className="graph-record-picker">학습 기록<select value={recordId} disabled={starting} onChange={event => setRecordId(event.target.value)}><option value="">현재까지의 배움</option>{data?.records.map(record => <option key={record.id} value={record.id}>{recordDate(record.created_at)}</option>)}</select></label>
    </div>
    {error && <p className="notice error" role="alert">{error} <button onClick={() => setRevision(value => value + 1)}>다시 불러오기</button></p>}
    {data?.error && <p className="notice error" role="alert">{data.error} 이전 기록은 보관되어 있습니다.</p>}
    {pending && <p className="notice" role="status">통과한 풀이에서 개념을 정리하고 있습니다. 다른 페이지로 이동해도 계속 진행됩니다.</p>}
    {data?.state === 'stale' && <p className="graph-state-note">아직 정리하지 않은 통과 기록이 있습니다. AI 요약은 보관되며, 현재 지도에는 직접 추가한 단원과 연결된 풀이만 표시됩니다.</p>}
    {data && !data.ai_available && <p className="graph-state-note">AI 연결 후 새로운 개념을 정리할 수 있습니다. 저장된 기록과 학습 단원은 계속 탐색할 수 있습니다.</p>}
    {!data && !error && <LoadingSkeleton layout="graph" label="지식 지도를 불러오는 중…" />}
    {data && (data.nodes.length ? <KnowledgeExplorer key={`${recordId}:${data.record_id ?? 'live'}`} data={data} /> : <section className="graph-empty"><div aria-hidden="true">◌ — ◈ — ◌</div><span className="eyebrow">YOUR FIRST CONNECTION</span><h2>첫 배움이 지도의 시작입니다.</h2><p>학습 화면에서 ‘개념 지도에 추가하기’를 눌러주세요.<br />문제를 만들거나 풀지 않아도 괜찮습니다.</p><Link className="button primary" to="/foundations">기초 구현 학습하기</Link><Link className="text-link" to="/">내 학습 자료 보기 ↗</Link></section>)}
  </main>;
}
