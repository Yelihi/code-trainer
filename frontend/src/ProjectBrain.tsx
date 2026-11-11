import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, safeSourceUrl, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { layoutGraph } from './knowledgeGraph';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { NativeSelect } from './components/ui/native-select';
import { Label } from './components/ui/label';
import './projectBrain.css';

type SourceSummary = { id: string; kind: 'resource' | 'excerpt' | 'github_pr'; title: string; url: string; resource_id: string; resource_revision: number; created_at: string };
type Source = SourceSummary & { body: string };
type Claim = { text: string; attribution: 'observed' | 'user_statement' | 'ai_inference'; source_id: string; quote: string };
type RecordBody = { kind: 'observation' | 'decision' | 'lesson'; title: string; summary: string; body: string; claims: Claim[] };
type RecordSummary = Pick<Record, 'id' | 'revision' | 'review' | 'lifecycle' | 'kind' | 'title' | 'summary' | 'updated_at'>;
type Relation = { id: string; source_id: string; target_id: string; kind: 'related' | 'contradicts' | 'derived' | 'supersedes'; reason: string };
type Record = RecordBody & { id: string; revision: number; review: 'unreviewed' | 'confirmed'; lifecycle: 'current' | 'superseded'; archived: number; updated_at: string; links: Relation[]; versions: { revision: number; created_at: string }[] };
type Draft = { id: string; state: 'queued' | 'running' | 'ready' | 'failed' | 'interrupted'; error: string; data: RecordBody | null };
type GraphNode = { id: string; kind: string; label: string; status: string; record_id: string; url: string };
type GraphEdge = { id: string; source: string; target: string; kind: string; label: string; reason: string; quote: string };
type Graph = { nodes: GraphNode[]; edges: GraphEdge[] };
type LibraryResult = { items: { id: string; name: string; revision: number; state: string }[] };
const kindLabel = { observation: '관찰', decision: '결정', lesson: '교훈' };
const claimLabel = { observed: '관찰한 사실', user_statement: '사용자 진술', ai_inference: 'AI 추론' };
const relationLabel = { related: '연관', contradicts: '반박', derived: '도출', supersedes: '대체' };

export function ProjectBrainHome() {
  const navigate = useNavigate();
  const { health } = useApp();
  const [params, setParams] = useSearchParams();
  const query = params.get('q') ?? '', archived = params.get('archived') === 'true';
  const [search, setSearch] = useState(query), [resourceQuery, setResourceQuery] = useState('');
  const { data: records, error: listError, reload: reloadRecords } = useResource<RecordSummary[]>(`/project-brain/records?q=${encodeURIComponent(query)}&archived=${archived}`);
  const { data: sources, error: sourcesError, reload: reloadSources } = useResource<SourceSummary[]>('/project-brain/sources');
  const { data: library } = useResource<LibraryResult>(`/resources?q=${encodeURIComponent(resourceQuery)}&page=1&kind=all`);
  const [mode, setMode] = useState<'excerpt' | 'resource' | 'github_pr'>('excerpt');
  const [title, setTitle] = useState(''), [body, setBody] = useState(''), [url, setUrl] = useState('');
  const [resourceId, setResourceId] = useState(''), [revision, setRevision] = useState(1);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [draftId, setDraftId] = useState('');

  useEffect(() => {
    if (!draftId) return;
    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const draft = await api<Draft>(`/project-brain/drafts/${draftId}`);
        if (!active) return;
        if (draft.state === 'ready') { window.clearInterval(timer); navigate(`/project-brain/new?draft=${draftId}`); }
        if (draft.state === 'failed' || draft.state === 'interrupted') { window.clearInterval(timer); setDraftId(''); setError(draft.error || '초안 생성을 다시 요청해주세요.'); }
      } catch (e) { if (active) { window.clearInterval(timer); setDraftId(''); setError(errorMessage(e)); } }
    }, 2000);
    return () => { active = false; window.clearInterval(timer); };
  }, [draftId, navigate]);

  async function addSource(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError('');
    try {
      const source = await api<Source>('/project-brain/sources', 'POST', {
        id: crypto.randomUUID().replaceAll('-', ''), kind: mode, title, body, url,
        resource_id: mode === 'resource' ? resourceId : '', revision: mode === 'resource' ? revision : 0,
      });
      setTitle(''); setBody(''); setUrl(''); setResourceId(''); reloadSources();
      setSelected(current => [...current, source.id]);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  async function generate() {
    if (busy || draftId || !selected.length) return;
    setBusy(true); setError('');
    try {
      const draft = await api<Draft>('/project-brain/drafts', 'POST', { request_id: crypto.randomUUID(), source_ids: selected });
      setDraftId(draft.id);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <main className="page brain-page">
    <div className="breadcrumb">데이터 쌓기<span>/</span>프로젝트 브레인</div>
    <header className="brain-heading"><div><span className="eyebrow">PROJECT MEMORY</span><h1>판단의 이유를 남기세요.</h1><p>원자료에서 관찰과 결정을 정리하고, 연결을 따라 다시 확인할 수 있습니다.</p></div><div className="brain-actions"><Link className="button" to="/project-brain/graph">연결 그래프</Link><Link className="button primary" to="/project-brain/new">직접 기록</Link></div></header>
    <ErrorNotice error={error || listError || sourcesError} />
    <section className="brain-section"><div className="brain-section-head"><div><h2>기록</h2><p>AI 초안은 저장 전까지 기록이 아닙니다. 확인 상태도 직접 변경합니다.</p></div><Button onClick={() => setParams(archived ? {} : { archived: 'true' })}>{archived ? '현재 기록' : '보관한 기록'}</Button></div>
      <form className="brain-search" onSubmit={event => { event.preventDefault(); setParams({ q: search, ...(archived ? { archived: 'true' } : {}) }); }}><Label className="sr-only" htmlFor="brain-record-search">기록 검색</Label><Input id="brain-record-search" type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="판단·제약·결과 검색" maxLength={160} /><Button>검색</Button></form>
      {!records && !listError && <LoadingSkeleton layout="list" label="프로젝트 기록을 불러오는 중…" />}
      {records && <div className="brain-list">{records.map(item => <Link key={item.id} className="brain-record-card" to={`/project-brain/${item.id}`}><span>{kindLabel[item.kind]} · {item.review === 'confirmed' ? '확인됨' : '미확인'} · {item.lifecycle === 'superseded' ? '대체됨' : '현재'}</span><h3>{item.title}</h3><p>{item.summary}</p><small>{timestamp(item.updated_at)} · v{item.revision}</small></Link>)}{!records.length && <div className="brain-empty">{archived ? '보관한 기록이 없습니다.' : '아직 프로젝트 기록이 없습니다. 원자료를 추가하고 첫 판단을 남겨보세요.'}</div>}</div>}
      {listError && <Button onClick={reloadRecords}>다시 불러오기</Button>}
    </section>
    <section className="brain-section brain-two-column"><div><div className="brain-section-head"><div><h2>원자료 추가</h2><p>선택한 시점의 내용을 보존합니다. URL만으로 근거를 확인한 것으로 표시하지 않습니다.</p></div></div>
      <form className="brain-form" onSubmit={event => void addSource(event)}><Label>종류<NativeSelect value={mode} onChange={event => setMode(event.target.value as typeof mode)}><option value="excerpt">대화·실험 발췌</option><option value="resource">자료 보관함</option><option value="github_pr">GitHub PR</option></NativeSelect></Label>
        {mode === 'excerpt' && <><Label>제목<Input value={title} onChange={event => setTitle(event.target.value)} maxLength={200} required /></Label><Label>원문 발췌<Textarea value={body} onChange={event => setBody(event.target.value)} maxLength={60000} rows={7} required /></Label><Label>원본 링크 (선택)<Input type="url" value={url} onChange={event => setUrl(event.target.value)} maxLength={2000} /></Label></>}
        {mode === 'github_pr' && <Label>PR 주소<Input type="url" value={url} onChange={event => setUrl(event.target.value)} placeholder="https://github.com/owner/repo/pull/123" required /></Label>}
        {mode === 'resource' && <><Label>보관함 검색<Input value={resourceQuery} onChange={event => setResourceQuery(event.target.value)} placeholder="자료 제목 검색" /></Label><Label>원자료<NativeSelect value={resourceId} onChange={event => { const item = library?.items.find(value => value.id === event.target.value); setResourceId(event.target.value); setRevision(item?.revision ?? 1); }} required><option value="">자료 선택</option>{library?.items.filter(item => item.revision > 0 && item.state === 'ready').map(item => <option key={item.id} value={item.id}>{item.name} · v{item.revision}</option>)}</NativeSelect></Label><Label>본문 버전<Input type="number" min={1} value={revision} onChange={event => setRevision(Number(event.target.value))} required /></Label></>}
        <Button className="primary" disabled={busy}>{busy ? '추가 중…' : '원자료 추가'}</Button></form></div>
      <div><div className="brain-section-head"><div><h2>AI로 정리</h2><p>원자료를 선택한 뒤 요청하세요. 제안된 문장은 저장 전에 검토할 수 있습니다.</p></div></div>
        <div className="brain-source-list">{sources?.map(source => <div key={source.id} className="brain-source-choice"><input id={`source-${source.id}`} type="checkbox" checked={selected.includes(source.id)} onChange={event => setSelected(current => event.target.checked ? [...current, source.id] : current.filter(id => id !== source.id))} /><label htmlFor={`source-${source.id}`}><strong>{source.title}</strong><small>{source.kind === 'resource' ? '보관 자료 v' + source.resource_revision : source.kind === 'github_pr' ? 'GitHub PR' : '직접 발췌'}</small></label><Link className="button" to={`/project-brain/sources/${source.id}`}>원본</Link></div>)}{sources && !sources.length && <p className="muted">먼저 원자료를 추가해주세요.</p>}</div>
        <Button className="primary" disabled={!selected.length || selected.length > 5 || !health?.ai || busy || !!draftId} onClick={() => void generate()}>{draftId ? 'AI 초안 생성 중…' : '선택한 자료로 초안 만들기'}</Button><p className="muted">한 번에 최대 5개 자료를 선택합니다. AI 연결이 필요합니다.</p></div></section>
  </main>;
}

export function ProjectBrainSource() {
  const { id } = useParams();
  const { data, error, reload } = useResource<Source>(`/project-brain/sources/${id}`);
  return <main className="page brain-page"><div className="breadcrumb"><Link to="/project-brain">프로젝트 브레인</Link><span>/</span>원자료</div><ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}{!data && !error && <LoadingSkeleton layout="article" label="원자료를 불러오는 중…" />}{data && <article className="brain-article"><span className="eyebrow">SOURCE SNAPSHOT</span><h1>{data.title}</h1><p>저장 시점의 원문 · {timestamp(data.created_at)}</p><div className="brain-actions">{data.resource_id && <Link className="button" to={`/library/${data.resource_id}`}>보관함 원본</Link>}{safeSourceUrl(data.url) && <a className="button" href={data.url} target="_blank" rel="noopener noreferrer">원본 링크</a>}</div><pre className="brain-source-body">{data.body}</pre></article>}</main>;
}

function EmptyRecord(): RecordBody { return { kind: 'observation', title: '', summary: '', body: '', claims: [] }; }
export function ProjectBrainNew() {
  const [params] = useSearchParams();
  const draftId = params.get('draft');
  return draftId ? <DraftEditor id={draftId} /> : <RecordEditor key="new" initial={null} />;
}
function DraftEditor({ id }: { id: string }) {
  const { data, error, reload } = useResource<Draft>(`/project-brain/drafts/${id}`);
  if (!data) return <main className="page brain-page"><ErrorNotice error={error} />{error ? <Button onClick={reload}>다시 불러오기</Button> : <LoadingSkeleton layout="editor" label="AI 초안을 불러오는 중…" />}</main>;
  if (data.state !== 'ready' || !data.data) return <main className="page brain-page"><ErrorNotice error={data.error || '초안이 아직 준비되지 않았습니다.'} /><Link className="button" to="/project-brain">프로젝트 브레인</Link></main>;
  return <RecordEditor key={id} initial={null} draft={data.data} />;
}
export function ProjectBrainEdit() {
  const { id } = useParams();
  const { data, error, reload } = useResource<Record>(`/project-brain/records/${id}`);
  if (!data) return <main className="page brain-page"><ErrorNotice error={error} />{error ? <Button onClick={reload}>다시 불러오기</Button> : <LoadingSkeleton layout="editor" label="기록을 불러오는 중…" />}</main>;
  return <RecordEditor key={`${id}:${data.revision}`} initial={data} />;
}
function RecordEditor({ initial, draft }: { initial: Record | null; draft?: RecordBody }) {
  const navigate = useNavigate();
  const { data: sources } = useResource<SourceSummary[]>('/project-brain/sources');
  const [id] = useState(initial?.id ?? crypto.randomUUID().replaceAll('-', ''));
  const [value, setValue] = useState<RecordBody>(draft ?? initial ?? EmptyRecord());
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const saved = useRef(JSON.stringify(value)), leaving = useRef(false);
  const blocker = useBlocker(() => !leaving.current && JSON.stringify(value) !== saved.current);
  useEffect(() => { if (blocker.state === 'blocked') { if (window.confirm('작성 중인 내용을 지우고 이동할까요?')) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { if (JSON.stringify(value) === saved.current) return; const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); }; window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn); }, [value]);
  function updateClaim(index: number, patch: Partial<Claim>) { setValue(current => ({ ...current, claims: current.claims.map((claim, i) => i === index ? { ...claim, ...patch } : claim) })); }
  async function save(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError('');
    try { const savedRecord = await api<Record>('/project-brain/records', 'POST', { ...value, id, revision: initial?.revision ?? 0 }); leaving.current = true; navigate(`/project-brain/${savedRecord.id}`); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <main className="page brain-page"><div className="breadcrumb"><Link to="/project-brain">프로젝트 브레인</Link><span>/</span>{initial ? '기록 수정' : '새 기록'}</div><header className="brain-heading"><div><span className="eyebrow">{draft ? 'AI DRAFT · REVIEW BEFORE SAVING' : 'PROJECT RECORD'}</span><h1>{initial ? '기록 수정' : draft ? 'AI 초안 검토' : '프로젝트 기록 만들기'}</h1><p>관찰·사용자 진술·AI 추론을 구분하고, 중요한 문장에는 원자료 인용을 연결하세요.</p></div></header>
    <form className="brain-form brain-editor" onSubmit={event => void save(event)}><ErrorNotice error={error} /><Label>기록 종류<NativeSelect value={value.kind} onChange={event => setValue(current => ({ ...current, kind: event.target.value as RecordBody['kind'] }))}><option value="observation">관찰</option><option value="decision">결정</option><option value="lesson">조건부 교훈</option></NativeSelect></Label><Label>제목<Input value={value.title} onChange={event => setValue(current => ({ ...current, title: event.target.value }))} required maxLength={200} /></Label><Label>한 줄 요약<Input value={value.summary} onChange={event => setValue(current => ({ ...current, summary: event.target.value }))} required maxLength={1000} /></Label><Label>상황·판단·결과<Textarea rows={10} value={value.body} onChange={event => setValue(current => ({ ...current, body: event.target.value }))} required maxLength={12000} /></Label>
      <section className="brain-claims"><div className="brain-section-head"><div><h2>주장과 근거</h2><p>관찰·사용자 진술은 원자료의 정확한 인용이 필요합니다. 추론은 명확히 표시됩니다.</p></div><Button type="button" onClick={() => setValue(current => ({ ...current, claims: [...current.claims, { text: '', attribution: 'observed', source_id: '', quote: '' }] }))} disabled={value.claims.length >= 20}>주장 추가</Button></div>{value.claims.map((claim, i) => <div className="brain-claim-editor" key={i}><div className="brain-claim-top"><strong>주장 {i + 1}</strong><Button type="button" onClick={() => setValue(current => ({ ...current, claims: current.claims.filter((_, index) => index !== i) }))}>제거</Button></div><Label>문장<Input value={claim.text} onChange={event => updateClaim(i, { text: event.target.value })} required maxLength={1200} /></Label><Label>구분<NativeSelect value={claim.attribution} onChange={event => updateClaim(i, { attribution: event.target.value as Claim['attribution'] })}><option value="observed">관찰한 사실</option><option value="user_statement">사용자 진술</option><option value="ai_inference">AI 추론</option></NativeSelect></Label><Label>원자료<NativeSelect value={claim.source_id} onChange={event => updateClaim(i, { source_id: event.target.value, quote: event.target.value ? claim.quote : '' })} required={claim.attribution !== 'ai_inference'}><option value="">{claim.attribution === 'ai_inference' ? '근거 없음 · 추론' : '원자료 선택'}</option>{sources?.map(source => <option key={source.id} value={source.id}>{source.title}</option>)}</NativeSelect></Label>{claim.source_id && <><Link className="button" to={`/project-brain/sources/${claim.source_id}`} target="_blank" rel="noopener noreferrer">원자료 확인</Link><Label>원문 그대로 인용<Textarea rows={3} value={claim.quote} onChange={event => updateClaim(i, { quote: event.target.value })} required maxLength={4000} /></Label></>}</div>)}</section>
      <div className="brain-actions"><Link className="button" to={initial ? `/project-brain/${initial.id}` : '/project-brain'}>돌아가기</Link><Button className="primary" disabled={busy}>{busy ? '저장 중…' : '기록 저장'}</Button></div></form></main>;
}

export function ProjectBrainRecord() {
  const { id } = useParams();
  const { data, error, reload } = useResource<Record>(`/project-brain/records/${id}`);
  const { data: allRecords } = useResource<RecordSummary[]>('/project-brain/records');
  const [busy, setBusy] = useState(false), [actionError, setActionError] = useState('');
  const [target, setTarget] = useState(''), [kind, setKind] = useState<Relation['kind']>('related'), [reason, setReason] = useState('');
  const [old, setOld] = useState<Record | null>(null);
  async function action(path: string, payload: object) {
    setBusy(true); setActionError('');
    try { await api(`/project-brain/records/${id}/${path}`, 'POST', payload); reload(); return true; }
    catch (e) { setActionError(errorMessage(e)); return false; }
    finally { setBusy(false); }
  }
  return <main className="page brain-page"><div className="breadcrumb"><Link to="/project-brain">프로젝트 브레인</Link><span>/</span>기록</div><ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}{!data && !error && <LoadingSkeleton layout="article" label="기록을 불러오는 중…" />}{data && <><header className="brain-heading"><div><span className="eyebrow">{kindLabel[data.kind]} · {data.review === 'confirmed' ? '사용자 확인' : '미확인'} · {data.lifecycle === 'superseded' ? '대체됨' : '현재'}</span><h1>{data.title}</h1><p>{data.summary}</p></div><div className="brain-actions"><Link className="button" to={`/project-brain/${id}/edit`}>수정</Link><a className="button" href={`/api/project-brain/records/${id}/export`} download>Markdown 내보내기</a></div></header>
      <div className="brain-status"><span>v{data.revision} · {timestamp(data.updated_at)}</span><div className="brain-actions"><Button disabled={busy || data.review === 'confirmed'} onClick={() => void action('confirm', { revision: data.revision })}>{data.review === 'confirmed' ? '확인됨' : '이 버전 확인'}</Button><Button disabled={busy} onClick={() => void action('archive', { archived: !data.archived })}>{data.archived ? '복원' : '보관'}</Button></div></div>
      <div className="brain-detail-grid"><article className="brain-article"><h2>당시 판단과 결과</h2><p className="brain-prose">{data.body}</p><h2>주장과 근거</h2>{data.claims.length ? data.claims.map((claim, index) => <section className="brain-claim" key={index}><small>{claimLabel[claim.attribution]}</small><p>{claim.text}</p>{claim.source_id ? <div className="brain-evidence"><blockquote>{claim.quote}</blockquote><Link className="button" to={`/project-brain/sources/${claim.source_id}`}>원자료 열기</Link></div> : <span className="muted">근거 미연결 · 추론</span>}</section>) : <p className="muted">연결된 주장이 없습니다. 수정에서 원자료 근거를 추가할 수 있습니다.</p>}</article>
        <aside className="brain-aside"><h2>연결된 기록</h2>{data.links.map(link => <div className="brain-link" key={link.id}><strong>{relationLabel[link.kind]}</strong><p>{link.reason}</p><Link className="button" to={`/project-brain/${link.source_id === id ? link.target_id : link.source_id}`}>연결된 기록 보기</Link></div>)}{!data.links.length && <p className="muted">아직 연결된 기록이 없습니다.</p>}
          <form className="brain-form" onSubmit={event => { event.preventDefault(); void action('links', { target_id: target, kind, reason }).then(ok => { if (ok) { setTarget(''); setReason(''); } }); }}><Label>연결할 기록<NativeSelect value={target} onChange={event => setTarget(event.target.value)} required><option value="">기록 선택</option>{allRecords?.filter(item => item.id !== id).map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</NativeSelect></Label><Label>관계<NativeSelect value={kind} onChange={event => setKind(event.target.value as Relation['kind'])}><option value="related">연관</option><option value="derived">도출</option><option value="contradicts">반박</option><option value="supersedes">이 기록이 선택한 기록을 대체</option></NativeSelect></Label><Label>연결 이유<Input value={reason} onChange={event => setReason(event.target.value)} maxLength={600} required /></Label><Button disabled={busy || !target}>연결 저장</Button></form>
          <h2>이전 버전</h2>{data.versions.map(version => <Button key={version.revision} className="brain-version" onClick={() => void api<Record>(`/project-brain/records/${id}?revision=${version.revision}`).then(setOld).catch(e => setActionError(errorMessage(e)))}>v{version.revision} · {timestamp(version.created_at)}</Button>)}{old && <div className="brain-old"><strong>v{old.revision} · {old.title}</strong><p>{old.body}</p><Button onClick={() => setOld(null)}>닫기</Button></div>}</aside></div></>}</main>;
}

export function ProjectBrainGraph() {
  const { data, error, reload } = useResource<Graph>('/project-brain/graph');
  const [query, setQuery] = useState(''), [kind, setKind] = useState('all'), [selected, setSelected] = useState('');
  const nodes = useMemo(() => data?.nodes.filter(node => !query || node.label.toLocaleLowerCase().includes(query.toLocaleLowerCase())) ?? [], [data, query]);
  const edges = useMemo(() => { const nodeIds = new Set(nodes.map(node => node.id)); return data?.edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target) && (kind === 'all' || edge.kind === kind)) ?? []; }, [data, kind, nodes]);
  const layout = useMemo(() => layoutGraph(nodes, edges), [nodes, edges]);
  const activeNode = data?.nodes.find(node => node.id === selected), activeEdge = data?.edges.find(edge => edge.id === selected);
  const labels = new Map(data?.nodes.map(node => [node.id, node.label]) ?? []);
  return <main className="page brain-page"><div className="breadcrumb"><Link to="/project-brain">프로젝트 브레인</Link><span>/</span>연결 그래프</div><header className="brain-heading"><div><span className="eyebrow">SOURCE → DECISION → LESSON</span><h1>근거를 따라 읽는 그래프.</h1><p>노드와 관계를 선택해 무엇이 어떤 판단으로 이어졌는지 확인하세요.</p></div><Link className="button" to="/project-brain">기록 목록</Link></header><ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}{!data && !error && <LoadingSkeleton layout="graph" label="프로젝트 연결을 불러오는 중…" />}{data && <><div className="brain-graph-tools"><Label>검색<Input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="기록·원자료 제목" /></Label><Label>관계<NativeSelect value={kind} onChange={event => setKind(event.target.value)}><option value="all">모든 관계</option><option value="evidence">근거</option><option value="related">연관</option><option value="derived">도출</option><option value="contradicts">반박</option><option value="supersedes">대체</option></NativeSelect></Label><span>{nodes.length}개 노드 · {edges.length}개 연결</span></div>
      {nodes.length ? <div className="brain-graph-grid"><svg className="brain-graph-svg" viewBox={`${layout.bounds.x} ${layout.bounds.y} ${layout.bounds.width} ${layout.bounds.height}`} role="group" aria-label="프로젝트 기록 연결 그래프">
        <g>{edges.map(edge => {
          const a = layout.positions.get(edge.source), b = layout.positions.get(edge.target);
          return a && b ? <g key={edge.id} role="button" tabIndex={0} aria-label={`${labels.get(edge.source)}에서 ${labels.get(edge.target)}로 ${edge.label}`} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected(edge.id); } }}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className={selected === edge.id ? 'active' : ''} />
            <line className="brain-graph-edge-hit" x1={a.x} y1={a.y} x2={b.x} y2={b.y} onClick={() => setSelected(edge.id)} />
          </g> : null;
        })}</g>
        {nodes.map(node => { const point = layout.positions.get(node.id); return point && <g key={node.id} transform={`translate(${point.x},${point.y})`} className={`brain-graph-node ${node.kind} ${selected === node.id ? 'active' : ''}`} role="button" tabIndex={0} aria-label={`${node.label}, ${node.kind === 'source' ? '원자료' : kindLabel[node.kind as keyof typeof kindLabel]}`} onClick={() => setSelected(node.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected(node.id); } }}><circle r="30" /><text textAnchor="middle" y="54">{node.label.length > 18 ? node.label.slice(0, 18) + '…' : node.label}</text></g>; })}
      </svg><aside className="brain-graph-panel">{activeNode ? <><small>{activeNode.kind === 'source' ? '원자료' : kindLabel[activeNode.kind as keyof typeof kindLabel]} · {activeNode.status}</small><h2>{activeNode.label}</h2><Link className="button" to={activeNode.record_id ? `/project-brain/${activeNode.record_id}` : `/project-brain/sources/${activeNode.id.slice(2)}`}>상세와 근거 보기</Link></> : activeEdge ? <><small>{activeEdge.label}</small><h2>{labels.get(activeEdge.source)} → {labels.get(activeEdge.target)}</h2><p>{activeEdge.reason}</p>{activeEdge.quote && <blockquote>{activeEdge.quote}</blockquote>}</> : <p>노드나 아래 관계를 선택해주세요.</p>}<Button onClick={() => setSelected('')} disabled={!selected}>선택 해제</Button></aside></div> : <div className="brain-empty">연결할 기록이 없습니다. 원자료와 기록을 추가해주세요.</div>}
      <section className="brain-section"><h2>관계 목록</h2><div className="brain-relation-list">{edges.map(edge => <Button key={edge.id} className={selected === edge.id ? 'active' : ''} onClick={() => setSelected(edge.id)}><strong>{edge.label}</strong><span>{labels.get(edge.source)} → {labels.get(edge.target)}</span><small>{edge.reason}</small></Button>)}{!edges.length && <p className="muted">조건에 맞는 관계가 없습니다.</p>}</div></section></>}</main>;
}
