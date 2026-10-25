import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { InterpretationPractice } from './InterpretationPractice';
import { Markdown } from './Markdown';
import { libraryPage } from './libraryTypes';
import './library.css';

type Document = { title: string; summary: string; concepts: string[]; sections: {
  id: string; title: string; body: string; prerequisites: string[]; source_quotes: string[];
  examples: string[]; extensions: string[]; questions: string[];
}[] };
type Interpretation = { id: string; resource_id: string; revision: number; current_revision: number; source_name: string;
  state: 'queued' | 'running' | 'ready' | 'failed' | 'interrupted'; error: string; document: Document | null; created_at: string; model: string };
type History = { items: (Pick<Interpretation, 'id' | 'resource_id' | 'revision' | 'source_name' | 'state' | 'created_at'> & { title: string })[]; total: number; page: number; pages: number };
const states = { queued: '해석 대기', running: '해석 중', ready: '해석 완료', failed: '해석 실패', interrupted: '해석 중단' };

function StartInterpretation({ resourceId, revision, disabled = false, retryId = '' }: { resourceId: string; revision: number; disabled?: boolean; retryId?: string }) {
  const { userId, health } = useApp();
  const navigate = useNavigate();
  const storageKey = `interpretation-request:${userId}:${resourceId}:${revision}:${retryId}`;
  const [requestId] = useState(() => {
    try { const saved = localStorage.getItem(storageKey); if (saved && /^[a-f0-9-]{36}$/.test(saved)) return saved; } catch { /* Memory identity still protects this visit. */ }
    return crypto.randomUUID();
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const alive = useRef(true), sending = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  async function start() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try {
      // Save before sending so an uncertain response can be replayed after reload.
      try { localStorage.setItem(storageKey, requestId); } catch { /* Server also deduplicates pending work. */ }
      const job = await api<Interpretation>('/interpretations', 'POST', { resource_id: resourceId, revision, request_id: requestId });
      if (!alive.current) return;
      try { localStorage.removeItem(storageKey); } catch { /* Replaying still opens the saved job. */ }
      navigate('/interpretations/' + job.id);
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
    finally { sending.current = false; if (alive.current) setBusy(false); }
  }
  return <><ErrorNotice error={error} /><button className="primary" disabled={disabled || busy || !userId || !health?.ai} onClick={() => void start()}>{busy ? '요청 중…' : `v${revision} ${retryId ? '다시 해석하기' : '해석 시작'}`}</button>
    {health && !health.ai && <p className="reference-state">AI 설정이 필요합니다. 저장한 원문은 그대로 보관됩니다.</p>}</>;
}

export function ResourceInterpretations({ resourceId, revision, content }: { resourceId: string; revision: number; content: string | null }) {
  const { userId } = useApp();
  return <section className="interpretation-entry"><div><span className="eyebrow">EXPLORE THE SOURCE</span><h2>원문에서 이해로.</h2><p>{revision ? `선택한 본문 v${revision}에서 개념과 질문을 정리합니다.` : '본문을 저장한 뒤 해석을 시작할 수 있습니다.'}<br />원문은 보존하고, AI 해석은 별도 문서로 남깁니다.</p></div><div className="interpretation-entry-actions">
    {revision > 0 && <StartInterpretation key={`${userId}:${resourceId}:${revision}`} resourceId={resourceId} revision={revision} disabled={!content?.trim()} />}
    <Link to={'/explore?resource=' + resourceId}>이 자료의 해석 기록 →</Link></div></section>;
}

export function Interpretations() {
  const { userId } = useApp();
  return <InterpretationList key={userId} />;
}
function InterpretationList() {
  const [params, setParams] = useSearchParams();
  const resourceId = params.get('resource') ?? '', page = libraryPage(params.get('page'));
  const { data, error, reload } = useResource<History>(`/interpretations?page=${page}${resourceId ? '&resource_id=' + encodeURIComponent(resourceId) : ''}`);
  return <main className="page reference-page library-page"><div className="breadcrumb"><Link to="/library">자료 보관함</Link><span>/</span> 해석하기</div>
    <header className="reference-page-heading"><div><span className="eyebrow">READ. QUESTION. UNDERSTAND.</span><h1>읽은 것을 이해의 구조로.</h1><p>원문에서 출발한 개념과 질문을 다시 펼쳐보세요.<br />각 해석은 시작할 때 선택한 원문 버전을 기억합니다.</p></div><Link className="button primary" to="/library">해석할 자료 선택</Link></header>
    <div className="interpretation-list-links">{resourceId && <Link to="/explore">전체 해석 보기</Link>}<Link to="/">기존 코딩 학습 과정 →</Link></div>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="list" label="해석 문서를 불러오는 중…" />}
    {data && <><div className="reference-list-caption"><span>{resourceId ? '선택한 자료의 해석 기록' : '나의 해석 문서'}</span><span>{data.total}개의 기록</span></div>
      {data.items.length ? <div className="reference-list">{data.items.map(item => <Link className="reference-list-item" key={item.id} to={'/interpretations/' + item.id}><span className="reference-list-mark" aria-hidden="true">↳</span><div><small>{states[item.state]} · 원문 v{item.revision}</small><h2>{item.title}</h2><p>{item.source_name}</p><footer><span>AI 해석</span><span>{timestamp(item.created_at)}</span></footer></div><span aria-hidden="true">→</span></Link>)}</div> : <section className="reference-empty"><span aria-hidden="true">↳</span><h2>아직 해석한 자료가 없습니다.</h2><p>보관함에서 원문을 열고 해석을 시작해보세요.<br />언어 선택 없이 개념과 질문부터 살펴볼 수 있습니다.</p><Link className="button" to={resourceId ? '/library/' + resourceId : '/library'}>원문 살펴보기</Link></section>}
      {data.pages > 1 && <nav className="pagination" aria-label="해석 기록 페이지"><button disabled={data.page <= 1} onClick={() => setParams({ ...(resourceId ? { resource: resourceId } : {}), page: String(data.page - 1) })}>이전</button><span>{data.page} / {data.pages}</span><button disabled={data.page >= data.pages} onClick={() => setParams({ ...(resourceId ? { resource: resourceId } : {}), page: String(data.page + 1) })}>다음</button></nav>}</>}
  </main>;
}

export function InterpretationDetail() {
  const { id } = useParams(), { userId } = useApp();
  return <Detail key={userId + ':' + id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const [data, setData] = useState<Interpretation | null>(null), [error, setError] = useState(''), [reload, setReload] = useState(0);
  const { hash } = useLocation();
  useEffect(() => {
    // Cross-page section links arrive before the fetched document is rendered.
    if (data?.document && /^#s[1-6]$/.test(hash)) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [data?.document, hash]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const result = await api<Interpretation>('/interpretations/' + id, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setData(result); setError('');
        if (result.state === 'queued' || result.state === 'running') timer = setTimeout(() => void load(), 2000);
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [id, reload]);
  return <main className="page reference-page interpretation-page"><div className="breadcrumb"><Link to="/explore">해석하기</Link><span>/</span> 개념 문서</div>
    <ErrorNotice error={error} />{error && <button onClick={() => setReload(n => n + 1)}>상태 다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="editor" label="해석 문서를 불러오는 중…" />}
    {data && <><header className="reference-page-heading"><div><span className="eyebrow">{states[data.state]} · AI INTERPRETATION</span><h1>{data.document?.title ?? data.source_name}</h1><p>원문 v{data.revision} 기준 · {timestamp(data.created_at)}</p></div><Link className="button" to={'/library/' + data.resource_id}>원문과 버전 보기</Link></header>
      <aside className="interpretation-provenance"><strong>{data.source_name} · 본문 v{data.revision}</strong><p>AI가 작성한 해석입니다. 인용한 원문과 비교하며 읽어보세요.{data.current_revision !== data.revision && ` 원문에는 더 최신인 v${data.current_revision}가 있습니다. 이 문서는 v${data.revision} 해석을 그대로 보존합니다.`}</p></aside>
      {(data.state === 'queued' || data.state === 'running') && <section className="reference-empty" role="status"><h2>{states[data.state]}입니다.</h2><p>개념과 원문 근거를 정리하고 있습니다.<br />다른 화면으로 이동해도 해석 기록에서 다시 확인할 수 있습니다.</p></section>}
      {(data.state === 'failed' || data.state === 'interrupted') && <section className="interpretation-recovery"><p role="alert">{data.error}</p><p>이 기록을 보존하고, 같은 원문 v{data.revision}에서 새 해석을 시도합니다.</p><StartInterpretation resourceId={data.resource_id} revision={data.revision} retryId={data.id} /></section>}
      {data.document && <InterpretationDocument document={data.document} />}
      {data.state === 'ready' && data.document && <InterpretationPractice interpretationId={data.id} />}
    </>}
  </main>;
}

export function InterpretationDocument({ document }: { document: Document }) {
  return <><section className="interpretation-summary"><span className="eyebrow">AI 해석 · 핵심 개념</span><Markdown language="">{document.summary}</Markdown><ul className="interpretation-concepts">{document.concepts.map((concept, i) => <li key={i}>{concept}</li>)}</ul></section>
    <nav className="interpretation-outline" aria-label="해석 섹션">{document.sections.map((section, i) => <a key={section.id} href={'#' + section.id}><span>{String(i + 1).padStart(2, '0')}</span>{section.title}</a>)}</nav>
    {document.sections.map(section => <section className="interpretation-section" id={section.id} key={section.id}>
      <span className="eyebrow">AI 해석</span><h2>{section.title}</h2>
      {!!section.prerequisites.length && <p>먼저 읽기: {section.prerequisites.map(id => <a key={id} href={'#' + id}>{document.sections.find(s => s.id === id)?.title} </a>)}</p>}
      <Markdown language="">{section.body}</Markdown>
      <div className="interpretation-quotes"><h3>원문 근거</h3>{section.source_quotes.map((quote, i) => <blockquote key={i}><p>{quote}</p></blockquote>)}</div>
      {!!section.examples.length && <div className="interpretation-addition"><h3>AI 예시</h3>{section.examples.map((text, i) => <Markdown key={i} language="">{text}</Markdown>)}</div>}
      {!!section.extensions.length && <div className="interpretation-addition"><h3>AI 확장 · 원문 밖의 연결</h3>{section.extensions.map((text, i) => <Markdown key={i} language="">{text}</Markdown>)}</div>}
      <div className="interpretation-questions"><h3>스스로 확인할 질문</h3><p>AI가 제안한 질문입니다. 먼저 자신의 말로 생각해보세요.</p><ol>{section.questions.map((question, i) => <li key={i}>{question}</li>)}</ol></div>
    </section>)}
  </>;
}
