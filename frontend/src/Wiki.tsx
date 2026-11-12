import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, NavLink, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Markdown } from './Markdown';
import { ReferenceEditor } from './ReferenceEditor';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { NativeSelect } from './components/ui/native-select';
import { Checkbox } from './components/ui/checkbox';
import './projectBrain.css';
import './wiki.css';

type Version = { revision: number; created_at: string };
type DocumentSummary = { id: string; title: string; revision: number; updated_at: string };
type Document = DocumentSummary & { body: string; source_ids: string[]; origin_job: string; versions: Version[] };
type Citation = { document_id: string; revision: number; quote: string };
type Page = { slug: string; revision: number; title: string; summary: string; body: string; citations: Citation[]; links: string[]; updated_at: string; versions?: Version[]; backlinks?: Page[] };
type Compilation = { summary: string; pages: Page[] };
type Answer = { answer: string; insufficient: boolean; citations: { slug: string; revision: number; quote: string }[] };
type Kind = 'ingest' | 'query' | 'lint';
type JobSummary = { id: string; kind: Kind; state: string; error: string; created_at: string };
type Job = JobSummary & { request: { documents: { id: string; revision: number }[]; question: string }; data: Compilation | Answer | null; before?: Page[] };
type Source = { id: string; title: string; body: string; kind: string; resource_revision: number };
type Finding = { slug: string; kind: string; message: string; document_id?: string };
const kindName = { ingest: '문서 반영', query: '위키 질문', lint: '위키 점검' };
const stateName: Record<string, string> = { queued: '대기 중', running: 'AI가 읽는 중', ready: '검토 가능', applied: '반영 완료', failed: '실패', interrupted: '중단됨' };
const uid = () => crypto.randomUUID().replaceAll('-', '');

function Frame({ title, description, children, action }: { title: string; description?: string; children: ReactNode; action?: ReactNode }) {
  return <main className="page brain-page wiki-page">
    <div className="breadcrumb">데이터 쌓기<span>/</span><Link className="wiki-link" to="/project-brain">세컨드 브레인</Link></div>
    <header className="brain-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="brain-actions">{action}</div>}</header>
    <nav className="wiki-nav" aria-label="세컨드 브레인"><NavLink to="/project-brain" end>위키</NavLink><NavLink to="/project-brain/documents">문서</NavLink><NavLink to="/project-brain/activity">활동</NavLink><NavLink to="/project-brain/legacy">기존 프로젝트 기록</NavLink></nav>
    {children}
  </main>;
}

function useStartJob() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const pending = useRef<{ key: string; id: string } | null>(null), lock = useRef(false);
  async function start(kind: Kind, documents: { id: string; revision: number }[] = [], question = '') {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError('');
    const key = JSON.stringify({ kind, documents, question });
    if (pending.current?.key !== key) pending.current = { key, id: uid() };
    try {
      const result = await api<Job>('/wiki/jobs', 'POST', { request_id: pending.current.id, kind, documents, question });
      pending.current = null; navigate('/project-brain/activity/' + result.id);
    } catch (e) { setError(errorMessage(e)); }
    finally { lock.current = false; setBusy(false); }
  }
  return { start, busy, error };
}

function useUnsaved(dirty: boolean) {
  const blocker = useBlocker(dirty);
  useEffect(() => {
    if (blocker.state === 'blocked') {
      if (window.confirm('저장하지 않은 변경이 있습니다. 내용을 버리고 이동할까요?')) blocker.proceed();
      else blocker.reset();
    }
  }, [blocker]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
}

function RequestState({ error, loading, reload }: { error: string; loading: boolean; reload: () => void }) {
  return <><ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}{loading && !error && <LoadingSkeleton layout="list" label="불러오는 중…" />}</>;
}

export function WikiHome() {
  const { data: pages, error, reload } = useResource<Page[]>('/wiki/pages');
  const { health } = useApp();
  const [search, setSearch] = useState(''), [question, setQuestion] = useState('');
  const request = useStartJob();
  const visible = pages?.filter(p => (p.title + p.summary + p.body).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  return <Frame title="내 문서에서 자라는 위키" description="직접 고르고 보완한 문서를 바탕으로, AI가 기존 설명과 연결을 함께 갱신합니다." action={<><a className="button" href="/api/wiki/export" download>Markdown 내보내기</a><Link className="button primary" to="/project-brain/documents">문서 준비하기</Link></>}>
    <div className="wiki-workspace"><section aria-labelledby="wiki-index-title"><div className="brain-section-head"><div><h2 id="wiki-index-title">위키 목차</h2><p>자료별 기록을 넘어, 주제별로 종합한 설명을 읽어보세요.</p></div><span className="muted">{pages?.length ?? 0}개 페이지</span></div>
      <Label htmlFor="wiki-search" className="sr-only">위키 검색</Label><Input id="wiki-search" type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="주제나 내용으로 찾기" maxLength={160} />
      <RequestState error={error} loading={!pages} reload={reload} />
      {pages?.length === 0 && <div className="wiki-empty"><h3>첫 문서부터 시작하세요.</h3><p>보관한 자료를 고르거나 직접 문서를 작성하세요. 내용을 보완하고 저장한 뒤 ‘위키 변경안 만들기’를 누르면 됩니다.</p><Link className="wiki-link" to="/project-brain/documents/new">첫 문서 작성하기</Link></div>}
      {!!pages?.length && !visible?.length && <p className="wiki-empty">일치하는 페이지가 없습니다. 다른 검색어로 찾아보세요.</p>}
      <div className="wiki-index">{visible?.map(p => <Link className="wiki-link" to={'/project-brain/pages/' + p.slug} key={p.slug}><div><h3>{p.title}</h3><p>{p.summary}</p></div><small>v{p.revision} · 근거 {p.citations.length}개</small></Link>)}</div>
    </section><aside className="wiki-query"><h2>위키에 질문하기</h2><p className="muted">반영된 위키를 읽고, 사용한 페이지와 함께 답합니다. 부족한 근거는 부족하다고 알려줍니다.</p>
      <form className="brain-form" onSubmit={e => { e.preventDefault(); void request.start('query', [], question); }}><Label htmlFor="wiki-question">궁금한 점</Label><Textarea id="wiki-question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="예: 지금까지 정리한 배포 방식과 주의점은?" rows={5} maxLength={2000} required /><Button className="primary" disabled={request.busy || !pages?.length || !health?.ai || !question.trim()}>{request.busy ? '요청 중…' : '위키에서 답 찾기'}</Button></form>
      {!health?.ai && <p className="muted"><Link className="wiki-link" to="/settings/ai">AI를 연결</Link>하면 질문과 문서 반영을 사용할 수 있습니다.</p>}<ErrorNotice error={request.error} />
      <div className="wiki-maintenance"><h3>위키를 가꾸기</h3><p className="muted">문서가 바뀌었거나 설명이 충돌하는지 점검하세요. 결과를 보고 보완할 문서를 고를 수 있습니다.</p><Button disabled={request.busy || !pages?.length || !health?.ai} onClick={() => void request.start('lint')}>위키 점검하기</Button><Link className="wiki-link" to="/project-brain/activity">지난 질문과 반영 이력</Link></div>
    </aside></div>
  </Frame>;
}

export function WikiDocuments() {
  const docs = useResource<DocumentSummary[]>('/wiki/documents');
  const pages = useResource<Page[]>('/wiki/pages');
  const { health } = useApp();
  const [selected, setSelected] = useState<string[]>([]);
  const request = useStartJob();
  const ready = docs.data?.filter(d => selected.includes(d.id)) ?? [];
  return <Frame title="위키에 담을 문서" description="자료를 직접 선택하고, 내 이해와 맥락을 보완해 저장하세요. 저장한 문서만 AI에게 전달합니다." action={<Link className="button primary" to="/project-brain/documents/new">문서 작성하기</Link>}>
    <section className="wiki-documents"><div className="wiki-selection"><div><h2>반영할 문서 선택</h2><p className="muted">최대 10개를 선택하세요. AI가 기존 위키를 읽고 새 페이지와 수정안을 제안합니다.</p></div><Button className="primary" disabled={request.busy || !ready.length || ready.length > 10 || !health?.ai} onClick={() => void request.start('ingest', ready.map(d => ({ id: d.id, revision: d.revision })))}>{request.busy ? '요청 중…' : `위키 변경안 만들기${ready.length ? ` (${ready.length})` : ''}`}</Button></div>
      {!health?.ai && <p className="notice">문서는 AI 없이 작성할 수 있습니다. 변경안을 만들려면 <Link className="wiki-link" to="/settings/ai">AI 연결</Link>이 필요합니다.</p>}
      <ErrorNotice error={request.error} /><RequestState error={docs.error || pages.error} loading={!docs.data} reload={() => { docs.reload(); pages.reload(); }} />
      {!docs.data?.length && docs.data && <div className="wiki-empty"><h3>고르고, 보완하고, 반영하세요.</h3><p>문서 작성에서 자료 보관함·원자료·GitHub PR을 불러오거나 직접 적을 수 있습니다. 위키는 저장만으로 바뀌지 않습니다.</p><Link className="wiki-link" to="/project-brain/documents/new">문서 작성하기</Link></div>}
      <div className="wiki-document-list">{docs.data?.map(d => {
        const used = pages.data?.some(p => p.citations.some(ref => ref.document_id === d.id && ref.revision === d.revision));
        const old = pages.data?.some(p => p.citations.some(ref => ref.document_id === d.id && ref.revision !== d.revision));
        return <div className="wiki-document-row" key={d.id}><Checkbox id={'doc-' + d.id} checked={selected.includes(d.id)} onCheckedChange={checked => setSelected(current => checked ? [...current, d.id] : current.filter(id => id !== d.id))} disabled={!selected.includes(d.id) && selected.length >= 10} /><div><Label htmlFor={'doc-' + d.id}>{d.title}</Label><small>v{d.revision} · {timestamp(d.updated_at)} · {old ? '이전 버전을 인용한 페이지 보완 필요' : used ? '이 버전 반영됨' : '아직 반영하지 않음'}</small></div><Link className="button" to={'/project-brain/documents/' + d.id}>열고 보완하기</Link></div>;
      })}</div>
    </section>
  </Frame>;
}

export function WikiDocumentRoute() {
  const { id } = useParams();
  const [params] = useSearchParams();
  if (id) return <LoadDocument key={id + ':' + params.toString()} id={id} revision={params.get('revision')} />;
  if (params.get('answer')) return <AnswerDocument key={params.get('answer')} id={params.get('answer')!} />;
  if (params.get('record')) return <LegacyDocument key={params.get('record')} id={params.get('record')!} />;
  return <DocumentEditor key="new" />;
}
function LoadDocument({ id, revision }: { id: string; revision: string | null }) {
  const resource = useResource<Document>('/wiki/documents/' + id + (revision ? '?revision=' + encodeURIComponent(revision) : ''));
  return resource.data ? <DocumentEditor initial={resource.data} historical={!!revision} /> : <Frame title="문서 불러오기"><RequestState error={resource.error} loading reload={resource.reload} /></Frame>;
}
function AnswerDocument({ id }: { id: string }) {
  const resource = useResource<Job>('/wiki/jobs/' + id);
  if (!resource.data) return <Frame title="답변 불러오기"><RequestState error={resource.error} loading reload={resource.reload} /></Frame>;
  const answer = resource.data.data as Answer | null;
  if (!answer?.answer) return <Frame title="답변을 문서로 보완"><p>아직 답변이 준비되지 않았습니다.</p><Link className="wiki-link" to={'/project-brain/activity/' + id}>작업 확인하기</Link></Frame>;
  return <DocumentEditor seed={{ title: resource.data.request.question || '위키 점검에서 발견한 내용', body: answer.answer + '\n\n## 참고한 위키\n' + answer.citations.map(ref => `- [${ref.slug} v${ref.revision}](/project-brain/pages/${ref.slug}?revision=${ref.revision})\n  > ${ref.quote}`).join('\n'), source_ids: [], origin_job: id }} />;
}
function LegacyDocument({ id }: { id: string }) {
  const resource = useResource<{ title: string; summary: string; body: string; claims: { source_id: string; text: string; quote: string }[] }>('/project-brain/records/' + id);
  if (!resource.data) return <Frame title="기존 기록 불러오기"><RequestState error={resource.error} loading reload={resource.reload} /></Frame>;
  const old = resource.data;
  return <DocumentEditor seed={{ title: old.title, body: old.summary + '\n\n' + old.body + '\n\n## 기존 근거\n' + old.claims.map(c => `${c.text}\n> ${c.quote}`).join('\n\n') + `\n\n[기존 프로젝트 기록](/project-brain/${id})`, source_ids: [...new Set(old.claims.map(c => c.source_id).filter(Boolean))], origin_job: '' }} />;
}

type DocumentFields = Pick<Document, 'title' | 'body' | 'source_ids' | 'origin_job'>;
function DocumentEditor({ initial, seed, historical = false }: { initial?: Document; seed?: DocumentFields; historical?: boolean }) {
  const navigate = useNavigate();
  const [id] = useState(initial?.id ?? uid());
  const [value, setValue] = useState<DocumentFields>(initial ?? seed ?? { title: '', body: '', source_ids: [], origin_job: '' });
  const [busy, setBusy] = useState(false), [uploading, setUploading] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  const [saved, setSaved] = useState(JSON.stringify(value)), [revision, setRevision] = useState(initial?.revision ?? 0);
  const sources = useResource<Source[]>('/project-brain/sources');
  const dirty = JSON.stringify(value) !== saved || (!revision && !!seed);
  useUnsaved(dirty);
  async function save(e: FormEvent) {
    e.preventDefault(); if (busy || uploading) return;
    setBusy(true); setError('');
    try {
      const result = await api<Document>('/wiki/documents', 'POST', { id, revision, title: value.title, body: value.body, source_ids: value.source_ids, origin_job: value.origin_job });
      setSaved(JSON.stringify(value)); setRevision(result.revision); setMessage(`문서 v${result.revision}을 저장했습니다. 위키에 반영하려면 문서 목록에서 선택해주세요.`);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  async function importSource(source: Source) {
    if (busy || historical) return;
    if (value.body && !window.confirm('작성 중인 본문을 불러온 원자료로 바꿀까요? 원자료 자체는 변경되지 않습니다.')) return;
    setBusy(true); setError('');
    try {
      const full = source.body !== undefined ? source : await api<Source>('/project-brain/sources/' + source.id);
      setValue(current => ({ ...current, title: full.title, body: full.body, source_ids: [full.id], origin_job: '' }));
      sources.reload(); setMessage('원자료를 복사했습니다. 내 맥락을 보완한 뒤 문서를 저장해주세요.');
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <Frame title={historical ? `문서 v${revision} · 이전 버전` : revision ? '문서 보완하기' : '위키에 담을 문서 작성'} description="원자료는 그대로 보존합니다. 여기서 수정·보완한 문서가 위키의 근거가 됩니다." action={<Link className="button" to="/project-brain/documents">문서 목록</Link>}>
    <ErrorNotice error={error || sources.error} />{message && <p role="status" className="notice">{message}</p>}
    {historical && <p className="notice">이 버전은 읽기 전용입니다. <Link className="wiki-link" to={'/project-brain/documents/' + id}>최신 문서를 열어 보완하기</Link></p>}
    {!historical && <SourceImport sources={sources.data ?? []} disabled={busy} onImport={source => void importSource(source)} />}
    <form className="brain-form wiki-document-editor" onSubmit={e => void save(e)}><Label htmlFor="wiki-document-title">문서 제목</Label><Input id="wiki-document-title" value={value.title} onChange={e => setValue(current => ({ ...current, title: e.target.value }))} maxLength={200} required disabled={historical || busy} />
      <Label>문서 본문</Label><ReferenceEditor value={value.body} onChange={body => setValue(current => ({ ...current, body }))} disabled={historical || busy} onUploading={setUploading} />
      <p className="muted">{value.source_ids.length ? '연결한 원자료: ' : '직접 작성한 문서입니다. '}{value.source_ids.map((source, index) => <span key={source}>{index > 0 && ' · '}<Link className="wiki-link" to={'/project-brain/sources/' + source}>{sources.data?.find(s => s.id === source)?.title ?? '원자료 보기'}</Link></span>)} AI는 텍스트와 설명을 읽습니다. 이미지의 중요한 내용은 글로 보완해주세요.</p>
      {!historical && <div className="brain-actions"><Button className="primary" disabled={busy || uploading || !value.title.trim() || !value.body.trim()}>{busy ? '저장 중…' : '문서 저장'}</Button><Button type="button" disabled={dirty || !revision} onClick={() => navigate('/project-brain/documents')}>저장한 문서 반영하러 가기</Button><span className="muted">{dirty ? '저장하지 않은 변경이 있습니다.' : revision ? `저장됨 · v${revision}` : '아직 저장하지 않았습니다.'}</span></div>}
    </form>
    {!!initial?.versions.length && <details className="wiki-history"><summary>문서 버전 이력</summary>{initial.versions.map(v => <Link className="wiki-link" key={v.revision} to={`/project-brain/documents/${id}?revision=${v.revision}`}>v{v.revision} · {timestamp(v.created_at)}</Link>)}</details>}
  </Frame>;
}

function SourceImport({ sources, disabled, onImport }: { sources: Source[]; disabled: boolean; onImport: (source: Source) => void }) {
  const [mode, setMode] = useState('resource'), [search, setSearch] = useState(''), [selected, setSelected] = useState(''), [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [libraryPage, setLibraryPage] = useState(1);
  const library = useResource<{ items: { id: string; name: string; revision: number; state: string }[]; pages: number }>(`/resources?q=${encodeURIComponent(search)}&page=${libraryPage}&kind=all`);
  async function load() {
    if (busy || disabled) return;
    setBusy(true); setError('');
    try {
      if (mode === 'existing') {
        onImport(await api<Source>('/project-brain/sources/' + selected));
      } else {
        const item = library.data?.items.find(r => r.id === selected);
        const source = await api<Source>('/project-brain/sources', 'POST', mode === 'resource'
          ? { id: uid(), kind: 'resource', resource_id: selected, revision: item?.revision ?? 0 }
          : { id: uid(), kind: 'github_pr', url });
        onImport(source);
      }
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <details className="wiki-import"><summary>자료 보관함·원자료·PR에서 불러오기</summary><div className="wiki-import-controls">
    <Label>불러올 곳<NativeSelect value={mode} onChange={e => { setMode(e.target.value); setSelected(''); }} disabled={busy || disabled}><option value="resource">자료 보관함</option><option value="existing">보존된 원자료</option><option value="github_pr">GitHub PR</option></NativeSelect></Label>
    {mode === 'resource' && <><Label>보관함 검색<Input value={search} onChange={e => { setSearch(e.target.value); setLibraryPage(1); setSelected(''); }} maxLength={160} placeholder="자료 제목으로 찾기" /></Label><Label>사용할 자료<NativeSelect value={selected} onChange={e => setSelected(e.target.value)} disabled={!library.data || busy}><option value="">자료 선택</option>{library.data?.items.filter(r => r.revision > 0 && r.state === 'ready').map(r => <option key={r.id} value={r.id}>{r.name} · v{r.revision}</option>)}</NativeSelect></Label>{(library.data?.pages ?? 0) > 1 && <div className="brain-actions"><Button type="button" disabled={libraryPage === 1} onClick={() => { setLibraryPage(p => p - 1); setSelected(''); }}>이전</Button><span>{libraryPage} / {library.data?.pages}</span><Button type="button" disabled={libraryPage >= (library.data?.pages ?? 1)} onClick={() => { setLibraryPage(p => p + 1); setSelected(''); }}>다음</Button></div>}<ErrorNotice error={library.error} />{library.error && <Button type="button" onClick={library.reload}>보관함 다시 불러오기</Button>}</>}
    {mode === 'existing' && <Label>원자료<NativeSelect value={selected} onChange={e => setSelected(e.target.value)}><option value="">원자료 선택</option>{sources.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</NativeSelect></Label>}
    {mode === 'github_pr' && <Label>GitHub PR 주소<Input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repo/pull/123" maxLength={2000} /></Label>}
    <Button type="button" disabled={busy || disabled || (mode === 'github_pr' ? !url : !selected)} onClick={() => void load()}>{busy ? '불러오는 중…' : '본문 불러오기'}</Button><ErrorNotice error={error} />
  </div></details>;
}

export function WikiPage() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const revision = params.get('revision');
  const resource = useResource<Page>('/wiki/pages/' + slug + (revision ? '?revision=' + encodeURIComponent(revision) : ''));
  const all = useResource<Page[]>('/wiki/pages');
  const p = resource.data;
  return <Frame title={p?.title ?? '위키 페이지'} description={p?.summary} action={<Link className="button" to="/project-brain/documents">근거 문서 보완하기</Link>}>
    <RequestState error={resource.error || all.error} loading={!p} reload={() => { resource.reload(); all.reload(); }} />
    {p && <><div className="wiki-reading-status"><span>v{p.revision}{revision ? ' · 이전 버전' : ' · 현재 버전'}</span>{revision && <Link className="wiki-link" to={'/project-brain/pages/' + p.slug}>최신 페이지 보기</Link>}</div>
      <div className="wiki-workspace"><article className="wiki-article"><Markdown language="" images>{p.body}</Markdown><section className="wiki-related"><h2>연결된 페이지</h2>{!p.links.length && <p className="muted">아직 연결된 페이지가 없습니다.</p>}{p.links.map(target => <Link className="wiki-link" key={target} to={'/project-brain/pages/' + target}>{all.data?.find(item => item.slug === target)?.title ?? target}</Link>)}{!!p.backlinks?.length && <><h3>이 페이지를 참고하는 곳</h3>{p.backlinks.map(from => <Link className="wiki-link" key={from.slug} to={'/project-brain/pages/' + from.slug}>{from.title}</Link>)}</>}</section></article>
      <aside className="wiki-evidence"><h2>근거 문서</h2><p className="muted">사용자가 저장한 문서의 해당 버전을 인용합니다.</p>{p.citations.map((ref, index) => <div key={index}><Link className="wiki-link" to={`/project-brain/documents/${ref.document_id}?revision=${ref.revision}`}>근거 문서 · v{ref.revision}</Link><blockquote>{ref.quote}</blockquote></div>)}<details className="wiki-history"><summary>페이지 버전 이력</summary>{p.versions?.map(v => <Link className="wiki-link" key={v.revision} to={`/project-brain/pages/${p.slug}?revision=${v.revision}`}>v{v.revision} · {timestamp(v.created_at)}</Link>)}</details></aside></div></>}
  </Frame>;
}

export function WikiActivity() {
  const resource = useResource<JobSummary[]>('/wiki/jobs');
  const checks = useResource<Finding[]>('/wiki/inspection');
  return <Frame title="위키가 자라온 과정" description="문서 반영, 질문, 점검 결과를 다시 열 수 있습니다. 진행 중인 작업도 여기에서 이어보세요.">
    <RequestState error={resource.error || checks.error} loading={!resource.data} reload={() => { resource.reload(); checks.reload(); }} />
    {!!checks.data?.length && <section className="wiki-checks"><h2>보완할 부분</h2>{checks.data.map((f, i) => <p key={i}><Link className="wiki-link" to={'/project-brain/pages/' + f.slug}>{f.slug}</Link> · {f.message} {f.document_id && <Link className="wiki-link" to={'/project-brain/documents/' + f.document_id}>문서 보완하기</Link>}</p>)}</section>}
    {resource.data?.length === 0 && <div className="wiki-empty"><p>아직 위키 작업이 없습니다. 문서를 준비하고 첫 변경안을 만들어보세요.</p><Link className="wiki-link" to="/project-brain/documents">문서 준비하기</Link></div>}
    <div className="wiki-job-list">{resource.data?.map(j => <Link className="wiki-link" to={'/project-brain/activity/' + j.id} key={j.id}><strong>{kindName[j.kind]}</strong><span>{stateName[j.state] ?? j.state}</span><small>{timestamp(j.created_at)}</small></Link>)}</div>
  </Frame>;
}

export function WikiJob() {
  const { id } = useParams();
  const resource = useResource<Job>('/wiki/jobs/' + id);
  const pending = resource.data?.state === 'queued' || resource.data?.state === 'running';
  useEffect(() => { if (!pending) return; const timer = window.setInterval(resource.reload, 2500); return () => window.clearInterval(timer); }, [pending, resource.reload]);
  const j = resource.data;
  return <Frame title={j ? kindName[j.kind] : '위키 작업'} description={j?.request.question || (j?.kind === 'ingest' ? '기존 위키와 비교하고, 필요한 내용을 보완한 뒤 반영하세요.' : '근거와 함께 결과를 확인하세요.')}>
    <RequestState error={resource.error} loading={!j} reload={resource.reload} />
    {j && <><p className="wiki-reading-status" role="status">{stateName[j.state]} · {timestamp(j.created_at)}</p>
      {(pending || (!j.data && !j.error)) && <p className="notice">AI가 문서와 위키를 읽고 있습니다. 이 화면을 나가도 작업은 계속됩니다. 활동에서 다시 열 수 있습니다.</p>}
      <ErrorNotice error={j.error} />{['failed', 'interrupted'].includes(j.state) && <Link className="button" to={j.kind === 'ingest' ? '/project-brain/documents' : '/project-brain'}>내용을 확인하고 새로 요청하기</Link>}
      {j.kind === 'ingest' && j.data && <CompilationReview key={j.id + ':' + j.state} job={j} onApplied={resource.reload} />}
      {j.kind !== 'ingest' && j.data && <AnswerView job={j} />}
    </>}
  </Frame>;
}

function AnswerView({ job }: { job: Job }) {
  const answer = job.data as Answer;
  return <section className="wiki-answer"><Markdown language="">{answer.answer}</Markdown>{answer.insufficient && <p className="notice">위키의 근거가 부족합니다. 관련 문서를 추가하거나 보완한 뒤 다시 질문해주세요.</p>}<h2>참고한 위키</h2>{!answer.citations.length && <p className="muted">인용할 페이지가 없습니다.</p>}{answer.citations.map((ref, i) => <div className="wiki-answer-citation" key={i}><Link className="wiki-link" to={`/project-brain/pages/${ref.slug}?revision=${ref.revision}`}>{ref.slug} · v{ref.revision}</Link><blockquote>{ref.quote}</blockquote></div>)}<Link className="button primary" to={'/project-brain/documents/new?answer=' + job.id}>답변을 문서로 보완하기</Link><p className="muted">답변을 검토하고 문서로 저장한 뒤 위키에 반영하면, 탐구한 내용이 쌓입니다.</p></section>;
}

function CompilationReview({ job, onApplied }: { job: Job; onApplied: () => void }) {
  const [value, setValue] = useState(job.data as Compilation);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const applied = job.state === 'applied';
  useUnsaved(!applied && JSON.stringify(value) !== JSON.stringify(job.data));
  function update(index: number, patch: Partial<Page>) { setValue(current => ({ ...current, pages: current.pages.map((p, i) => index === i ? { ...p, ...patch } : p) })); }
  async function apply() {
    if (busy || applied) return;
    setBusy(true); setError('');
    try { await api('/wiki/jobs/' + job.id + '/apply', 'POST', value); onApplied(); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <section className="wiki-review"><p>{value.summary}</p>{applied && <p className="notice">변경안을 위키에 반영했습니다. <Link className="wiki-link" to="/project-brain">위키 읽기</Link></p>}
    <div className="wiki-change-list">{value.pages.map((p, index) => {
      const before = job.before?.find(old => old.slug === p.slug);
      return <section key={p.slug} className="wiki-change"><header><h2>{p.title}</h2><span className="muted">{p.revision ? `기존 v${p.revision} 갱신` : '새 페이지'}</span></header>
        {before && <details><summary>반영 전 페이지 보기</summary><h3>{before.title}</h3><p>{before.summary}</p><Markdown language="">{before.body}</Markdown></details>}
        {applied ? <Markdown language="">{p.body}</Markdown> : <div className="brain-form"><Label htmlFor={'change-title-' + index}>페이지 제목</Label><Input id={'change-title-' + index} value={p.title} onChange={e => update(index, { title: e.target.value })} maxLength={200} required disabled={busy} /><Label htmlFor={'change-summary-' + index}>요약</Label><Textarea id={'change-summary-' + index} value={p.summary} onChange={e => update(index, { summary: e.target.value })} maxLength={1000} rows={2} disabled={busy} /><Label htmlFor={'change-body-' + index}>반영할 전체 본문</Label><Textarea id={'change-body-' + index} value={p.body} onChange={e => update(index, { body: e.target.value })} maxLength={20000} rows={12} disabled={busy} /><details><summary>본문 미리보기</summary><Markdown language="">{p.body}</Markdown></details></div>}
        <details className="wiki-change-evidence"><summary>근거 {p.citations.length}개 · 연결 {p.links.length}개</summary>{p.citations.map((ref, i) => <div key={i}><Link className="wiki-link" to={`/project-brain/documents/${ref.document_id}?revision=${ref.revision}`}>근거 문서 v{ref.revision}</Link><blockquote>{ref.quote}</blockquote></div>)}{!!p.links.length && <p>연결할 페이지: {p.links.join(', ')}</p>}</details>
      </section>;
    })}</div><ErrorNotice error={error} />{!applied && <div className="wiki-apply"><p>변경안을 검토한 뒤 반영하세요. 문서나 위키가 바뀌었다면 새 변경안을 생성해야 합니다.</p><Button className="primary" disabled={busy || value.pages.some(p => !p.title.trim() || !p.summary.trim() || !p.body.trim())} onClick={() => void apply()}>{busy ? '반영 중…' : `${value.pages.length}개 페이지에 반영하기`}</Button></div>}
  </section>;
}
