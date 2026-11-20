import { LoadingState } from './LoadingState';
import { FileText, Plus } from 'lucide-react';
import { EmptyState, PageHeading } from './WorkspaceUI';
import { libraryPage } from './libraryTypes';
import { ReferenceSkill } from './ReferenceSkill';
import { useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Markdown } from './Markdown';
import { LearningTargets, TargetPicker, targetInput, type LearningTarget } from './LearningTargets';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { LoadingSkeleton } from './LoadingSkeleton';

type Reference = { id: string; title: string; user_body: string; targets: LearningTarget[]; revision: number; updated_at: string };
type Document = Reference & { ai: Record<string, string | string[]> | null; ai_job: string | null; ai_created_at: string | null; ai_sources: (LearningTarget & { key: string; basis: string; truncated?: boolean; excerpt: string })[]; stale: boolean; jobs: { id: string; kind: string; revision: number; state: string; error: string; created_at: string }[]; versions: { revision: number; created_at: string }[] };
const sections = { purpose: '주제와 사용 목적', explanation: '개념 설명', conditions: '적용 조건과 한계', procedure: '구현과 판단 절차', examples: '예제', cautions: '주의할 점', verification: '검증 방법' };
export function TechnicalReferences() {
  const [params, setParams] = useSearchParams();
  const query = (params.get('q') ?? '').slice(0, 160), page = libraryPage(params.get('page'));
  const { data, error, reload } = useResource<{ items: Reference[]; total: number; page: number; pages: number }>('/technical-references?q=' + encodeURIComponent(query) + '&page=' + page, { preserveData: true });
  return <main className="page technical-references-page"><PageHeading title="레퍼런스" description="내 설명과 학습 근거를 재사용할 문서로 만드세요." actions={<Link className="button primary" to="/technical-references/new"><Plus size={18} aria-hidden="true" />레퍼런스 작성</Link>} /><form key={query} className="reference-search" role="search" onSubmit={e => { e.preventDefault(); setParams({ q: String(new FormData(e.currentTarget).get('q') ?? '') }); }}><Label className="sr-only" htmlFor="reference-search">레퍼런스 검색</Label><Input id="reference-search" type="search" name="q" defaultValue={query} maxLength={160} placeholder="기술 주제와 내 설명에서 찾기" /><Button>검색</Button></form><ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}{!data && !error && <LoadingSkeleton layout="list" label="레퍼런스를 불러오는 중…" />}<div className="reference-document-grid">{data?.items.map(item => <article className="reference-document-card" key={item.id}><div><FileText className="document-card-icon" size={25} strokeWidth={1.6} aria-hidden="true" /><h2><Link to={'/technical-references/' + item.id}>{item.title}</Link></h2><p>{item.user_body.slice(0, 180) || '연결한 학습과 근거를 열어 살펴보세요.'}</p><small>사용자 작성 v{item.revision} · {timestamp(item.updated_at)}</small></div><Link className="button" to={'/technical-references/' + item.id}>읽기</Link></article>)}</div>{data && !data.items.length && <EmptyState icon={FileText} title={query ? '찾는 레퍼런스가 없습니다' : '첫 레퍼런스를 만들어보세요'} description="자료·질문을 연결하고 내 설명부터 작성할 수 있습니다." action={<Link className="button" to="/technical-references/new">새 레퍼런스</Link>} />}{data && data.pages > 1 && <nav className="pagination" aria-label="레퍼런스 페이지"><Button disabled={data.page <= 1} onClick={() => setParams({ q: query, page: String(data.page - 1) })}>이전</Button><span>{data.page} / {data.pages}</span><Button disabled={data.page >= data.pages} onClick={() => setParams({ q: query, page: String(data.page + 1) })}>다음</Button></nav>}</main>;
}
export function TechnicalReferenceRoute() {
  const { id } = useParams();
  const { userId } = useApp();
  return id ? <ReferenceDetail key={userId + id} id={id} /> : <ReferenceEditor key={userId + ':new'} initial={null} />;
}
function ReferenceDetail({ id }: { id: string }) {
  const { data, error, reload } = useResource<Document>('/technical-references/' + id, { preserveData: true });
  const [editing, setEditing] = useState(false), [busy, setBusy] = useState(false), [actionError, setActionError] = useState('');
  const request = useRef({ revision: 0, id: '' });
  const pending = data?.jobs.some(job => job.state === 'queued' || job.state === 'running');
  useEffect(() => { if (!pending) return; const timer = setInterval(reload, 2000); return () => clearInterval(timer); }, [pending, reload]);
  async function generate() {
    if (!data) return;
    if (request.current.revision !== data.revision) request.current = { revision: data.revision, id: crypto.randomUUID() };
    setBusy(true); setActionError('');
    try { await api('/technical-references/' + id + '/generate', 'POST', { request_id: request.current.id, revision: data.revision }); request.current.revision = 0; reload(); }
    catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(false); }
  }
  if (editing && data) return <ReferenceEditor initial={data} onSaved={() => { setEditing(false); reload(); }} onCancel={() => setEditing(false)} />;
  return <main className="page reference-document"><div className="breadcrumb"><Link to="/technical-references">내 레퍼런스</Link></div><ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}{!data && !error && <LoadingSkeleton layout="article" label="레퍼런스를 읽는 중…" />}{data && <><header className="learning-intro"><h1>{data.title}</h1><p>사용자 작성 v{data.revision} · {timestamp(data.updated_at)}</p><div className="reference-actions"><Button onClick={() => setEditing(true)}>내 설명과 근거 수정</Button><Button loading={busy || pending} disabled={busy || pending} onClick={() => void generate()}>{pending ? 'AI 설명 생성 중…' : data.ai ? 'AI 설명 갱신' : 'AI 설명 만들기'}</Button></div></header><div className="reference-layout"><article className="reference-body"><section className="reference-writing"><h2>내가 남긴 설명</h2>{data.user_body ? <Markdown language="text">{data.user_body}</Markdown> : <p className="muted">직접 작성한 설명은 아직 없습니다. AI 내용은 아래 별도 영역에 보관됩니다.</p>}</section>
    <section className="learning-section ai-reference"><header><h2>AI가 정리한 기술 설명</h2>{data.ai_created_at && <small>{timestamp(data.ai_created_at)}</small>}</header><p className="muted">사용자 경험이나 숙달을 인증하는 기록이 아닙니다. AI가 만든 예제는 직접 실행해 검증해야 합니다.</p>{data.stale && <p className="notice" role="status">작성 내용이나 근거가 변경되었습니다. 아래 설명은 이전 버전을 바탕으로 합니다.</p>}{data.jobs.find(job => job.kind === 'reference')?.error && <ErrorNotice error={data.jobs.find(job => job.kind === 'reference')!.error} />}{pending && <LoadingState compact={!!data.ai} status="설명 생성 중" title="학습 근거에서 기술 설명을 정리하고 있어요" />}{data.ai ? <>{Object.entries(sections).map(([key, title]) => <section className="reference-chapter" key={key}><h3>{title}</h3><Markdown language="text">{String(data.ai?.[key] ?? '')}</Markdown></section>)}<details><summary>생성에 사용한 근거와 버전</summary>{data.ai_sources.map(source => <article className="reference-chapter" key={source.key}><h3>{source.title} · {source.revision !== null ? `v${source.revision}` : '연결 시점'}</h3><p className="muted">{source.basis}</p><Markdown language="text">{source.excerpt}</Markdown>{source.truncated && <p className="notice">긴 근거의 일부만 AI 입력에 사용했습니다.</p>}</article>)}</details></> : !pending && <p>내 설명을 저장하거나 근거를 연결한 뒤 AI 설명을 만들 수 있습니다. 사용자 작성 내용은 그대로 유지됩니다.</p>}</section></article><aside className="reference-context" aria-label="연결한 근거와 재사용">
    <section className="learning-section"><h2>연결한 학습과 질문</h2>{data.targets.length ? <ul className="reference-evidence">{data.targets.map(target => <li key={target.kind + target.id + target.unit_id}><Link className="text-link" to={target.href}>{target.title}</Link>{target.revision !== null && <small> · 연결 시 v{target.revision}</small>}</li>)}</ul> : <p className="muted">연결된 학습이 없습니다.</p>}</section>
    <ReferenceSkill id={id} revision={data.revision} jobs={data.jobs} reload={reload} /><section className="learning-section"><h2>변경 이력</h2><p className="muted">사용자 작성 버전과 AI 생성 기록을 따로 보관합니다.</p>{data.versions.map(version => <ReferenceHistory key={version.revision} id={id} revision={version.revision} createdAt={version.created_at} />)}<details><summary>AI 생성 기록</summary>{data.jobs.map(job => <AIHistory key={job.id} id={id} job={job} />)}</details></section></aside></div>
  </>}</main>;
}
function ReferenceHistory({ id, revision, createdAt }: { id: string; revision: number; createdAt: string }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}><summary>사용자 작성 v{revision} · {timestamp(createdAt)}</summary>{open && <ReferenceVersion id={id} revision={revision} />}</details>;
}
function AIHistory({ id, job }: { id: string; job: Document['jobs'][number] }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}><summary>{timestamp(job.created_at)} · 작성 v{job.revision} 기반 · {job.kind === 'skill' ? 'Skill' : 'AI 설명'} · {({ ready: '생성 완료', failed: '실패', queued: '대기 중', running: '생성 중', interrupted: '중단됨' } as Record<string, string>)[job.state] ?? job.state}</summary>{open && <AIHistoryContent id={id} jobId={job.id} />}</details>;
}
function AIHistoryContent({ id, jobId }: { id: string; jobId: string }) {
  const { data, error } = useResource<{ data: Record<string, string | string[]> | null; error: string }>(`/technical-references/${id}/jobs/${jobId}`);
  return <><ErrorNotice error={error || data?.error || ''} />{data?.data && Object.entries(data.data).filter(([key]) => key !== 'source_ids').map(([key, value]) => <section className="reference-chapter" key={key}><h3>{sections[key as keyof typeof sections] ?? ({ name: '이름', description: '설명', when_to_use: '사용할 상황', scope: '적용 범위', exclusions: '제외 범위', inputs: '사전 조건', steps: '작업 절차', decisions: '판단 기준', limitations: '근거의 한계' } as Record<string,string>)[key] ?? key}</h3><Markdown language="text">{String(value)}</Markdown></section>)}</>;
}
function ReferenceVersion({ id, revision }: { id: string; revision: number }) {
  const { data, error } = useResource<Reference>(`/technical-references/${id}/versions/${revision}`);
  return <><ErrorNotice error={error} />{data && <article className="reference-chapter"><h3>{data.title}</h3><Markdown language="text">{data.user_body || '사용자 설명 없음'}</Markdown><ul>{data.targets.map(target => <li key={target.kind + target.id}>{target.title} · v{target.revision ?? '—'}</li>)}</ul></article>}</>;
}
function ReferenceEditor({ initial, onSaved, onCancel }: { initial: Reference | null; onSaved?: () => void; onCancel?: () => void }) {
  const { userId } = useApp(), navigate = useNavigate(), [params] = useSearchParams();
  const storageKey = 'technical-reference:' + userId + ':' + (initial?.id ?? 'new');
  const restored = useRef(false);
  const [draft, setDraft] = useState<Reference & { request_id: string }>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
      if (saved && typeof saved.title === 'string' && typeof saved.user_body === 'string' && typeof saved.request_id === 'string' && Number.isInteger(saved.revision) && Array.isArray(saved.targets) && (!initial || saved.id === initial.id)) { restored.current = true; return saved; }
    } catch { /* A browser draft is optional; server history remains authoritative. */ }
    return { id: initial?.id ?? crypto.randomUUID().replaceAll('-', ''), title: initial?.title ?? '', user_body: initial?.user_body ?? '', targets: initial?.targets ?? [], revision: initial?.revision ?? 0, updated_at: '', request_id: crypto.randomUUID() };
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [storageError, setStorageError] = useState(''), [adding, setAdding] = useState(false);
  const allowNavigation = useRef(false), saving = useRef(false);
  const dirty = draft.title !== (initial?.title ?? '') || draft.user_body !== (initial?.user_body ?? '') || JSON.stringify(draft.targets) !== JSON.stringify(initial?.targets ?? []);
  const blocker = useBlocker(() => dirty && !allowNavigation.current);
  useEffect(() => { if (blocker.state === 'blocked') { if (window.confirm('저장하지 않은 레퍼런스 초안이 있습니다. 초안을 남기고 이동할까요?')) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => {
    if (!dirty) return;
    try { localStorage.setItem(storageKey, JSON.stringify(draft)); } catch { setStorageError('임시 저장을 사용할 수 없습니다. 이동하기 전에 내용을 복사해주세요.'); }
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [dirty, draft, storageKey]);
  const source = params.get('source');
  useEffect(() => {
    if (!source || initial || restored.current) return;
    const controller = new AbortController();
    api<{ target: LearningTarget | null }>('/learning-target?path=' + encodeURIComponent(source), 'GET', undefined, controller.signal).then(value => { if (value.target) setDraft(old => ({ ...old, targets: [value.target!], title: old.title || value.target!.title })); }).catch(cause => { if (!controller.signal.aborted) setError(errorMessage(cause)); });
    return () => controller.abort();
  }, [source, initial]);
  function change(patch: Partial<Reference>) { setDraft(old => ({ ...old, ...patch, request_id: crypto.randomUUID() })); }
  async function save() {
    if (saving.current) return;
    saving.current = true; setBusy(true); setError('');
    try {
      const { id, title, user_body, revision, request_id } = draft;
      const result = await api<Reference>('/technical-references', 'POST', { id, title, user_body, revision, request_id, targets: draft.targets.map(targetInput) });
      allowNavigation.current = true;
      try { localStorage.removeItem(storageKey); } catch { /* The server save succeeded. */ }
      if (onSaved) onSaved(); else await navigate('/technical-references/' + result.id);
    } catch (cause) { setError(errorMessage(cause)); } finally { saving.current = false; setBusy(false); }
  }
  return <main className="page narrow-page technical-reference-editor"><div className="breadcrumb"><Link to="/technical-references">내 레퍼런스</Link></div><h1>{initial ? '레퍼런스 수정' : '새 레퍼런스'}</h1><form onSubmit={e => { e.preventDefault(); void save(); }}><Label>기술 주제<Input required value={draft.title} maxLength={200} disabled={busy} onChange={e => change({ title: e.target.value })} /></Label><Label>내 설명 · 적용 경험 · 아직 궁금한 점<Textarea rows={20} value={draft.user_body} maxLength={60000} disabled={busy} onChange={e => change({ user_body: e.target.value })} /></Label><LearningTargets targets={draft.targets} disabled={busy} onChange={targets => change({ targets })} /><Button type="button" disabled={busy || draft.targets.length >= 10} onClick={() => setAdding(!adding)}>{adding ? '근거 선택 닫기' : '학습 근거 더 연결'}</Button>{adding && <TargetPicker disabled={busy} onPick={target => { if (!draft.targets.some(item => item.kind === target.kind && item.id === target.id && item.unit_id === target.unit_id)) change({ targets: [...draft.targets, target] }); setAdding(false); }} />}{initial && draft.revision !== initial.revision && <p className="notice">다른 탭에서 저장한 버전과 이 초안의 기준이 다릅니다. 내용을 복사한 뒤 최신 내용을 확인해주세요.</p>}<ErrorNotice error={error || storageError} /><div className="reference-actions"><Button className="primary" loading={busy} disabled={busy || !draft.title.trim()}>{busy ? '저장 중…' : '내 설명 저장'}</Button>{onCancel && <Button type="button" disabled={busy} onClick={() => { if (!dirty || window.confirm('초안을 보관하고 읽기로 돌아갈까요?')) onCancel(); }}>읽기로 돌아가기</Button>}</div></form></main>;
}
