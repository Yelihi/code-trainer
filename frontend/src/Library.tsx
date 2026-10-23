import { useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, safeSourceUrl, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Markdown } from './Markdown';
import { Select } from './Select';
import { libraryPage, readResourceFile, resourceKinds, restoreResourceDraft, type Resource, type ResourceDraft, type ResourceList, type ResourceVersion } from './libraryTypes';
import './referenceNotes.css';
import './library.css';

export function Library() {
  const { userId } = useApp();
  return <LibraryList key={userId} />;
}
function LibraryList() {
  const [params, setParams] = useSearchParams();
  const query = (params.get('q') ?? '').slice(0, 160), page = libraryPage(params.get('page'));
  const kind = ['text', 'url', 'note'].includes(params.get('kind') ?? '') ? params.get('kind')! : 'all';
  const { data, error, reload } = useResource<ResourceList>(`/resources?q=${encodeURIComponent(query)}&page=${page}&kind=${kind}`);
  return <main className="page reference-page library-page">
    <div className="breadcrumb"><Link to="/">Workspace</Link><span>/</span> 자료 보관함</div>
    <header className="reference-page-heading"><div><span className="eyebrow">COLLECT. UNDERSTAND. CONNECT.</span><h1>배움의 시작, 원문부터.</h1><p>읽고 싶은 레퍼런스와 직접 쓴 노트를 한곳에 모으세요.</p></div><div className="reference-actions"><Link className="button" to="/references/new">직접 노트 작성</Link><Link className="button primary" to="/library/new/reference">+ 레퍼런스 등록</Link></div></header>
    <div className="reference-library-tools"><form key={query} role="search" onSubmit={e => { e.preventDefault(); setParams({ q: String(new FormData(e.currentTarget).get("q") ?? ""), kind }); }}><label className="sr-only" htmlFor="library-search">자료 검색</label><input id="library-search" type="search" placeholder="제목, 본문, URL에서 찾기" name="q" defaultValue={query} maxLength={160} /><button>검색</button></form><label className="library-filter">자료 종류<Select value={kind} onChange={e => setParams({ q: query, kind: e.target.value })}><option value="all">모든 자료</option>{Object.entries(resourceKinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></label></div>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="list" label="자료를 불러오는 중…" />}
    {data && <><div className="reference-list-caption"><span>나의 원문과 기록</span><span>{data.total}개의 자료</span></div>
      {data.items.length ? <div className="reference-list">{data.items.map(item => <Link className="reference-list-item" to={'/library/' + item.id} key={item.id}><div className="reference-list-mark" aria-hidden="true">{item.kind === 'url' ? '↗' : 'Aa'}</div><div><small>{resourceKinds[item.kind]} · {item.state === 'failed' ? '수집 실패 · 다시 가져오기 가능' : item.state === 'fetching' ? '원문 수집 중' : `본문 v${item.revision}`}</small><h2>{item.name}</h2><p>{item.excerpt || item.url || '아직 가져온 본문이 없습니다.'}</p><footer><span>{item.kind === 'note' ? '내 언어로 남긴 기록' : '해석 전 원문'}</span><span>{timestamp(item.updated_at)}</span></footer></div><span aria-hidden="true">→</span></Link>)}</div> : <section className="reference-empty"><span aria-hidden="true">↳</span><h2>{query ? '검색한 자료가 없습니다.' : '다음 배움의 재료를 모아보세요.'}</h2><p>URL, 텍스트, Markdown 파일을 등록하거나<br />직접 노트를 작성할 수 있습니다.</p><Link className="button" to="/library/new/reference">레퍼런스 등록</Link></section>}
      {data.pages > 1 && <nav className="pagination" aria-label="자료 페이지"><button disabled={data.page <= 1} onClick={() => setParams({ q: query, kind, page: String(data.page - 1) })}>이전</button><span>{data.page} / {data.pages}</span><button disabled={data.page >= data.pages} onClick={() => setParams({ q: query, kind, page: String(data.page + 1) })}>다음</button></nav>}
    </>}
    <p className="reference-state"><Link to="/references">기존 노트 관리 · 보관한 노트 보기 →</Link></p>
  </main>;
}

export function ResourceRegister() {
  const { id } = useParams();
  const { userId } = useApp();
  return id ? <EditResource key={userId + ':' + id} id={id} /> : <RegistrationForm key={userId} initial={null} />;
}
function EditResource({ id }: { id: string }) {
  const { data, error, reload } = useResource<Resource>('/resources/' + id);
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <button onClick={reload}>다시 불러오기</button> : <LoadingSkeleton layout="editor" label="자료를 불러오는 중…" />}</main>;
  if (data.kind !== 'text') return <main className="page"><p>텍스트 자료만 이 화면에서 수정할 수 있습니다.</p><Link to={'/library/' + id}>자료로 돌아가기</Link></main>;
  return <RegistrationForm initial={data} />;
}
function RegistrationForm({ initial }: { initial: Resource | null }) {
  const navigate = useNavigate();
  const { userId } = useApp();
  const storageKey = `resource-draft:${userId}:${initial?.id ?? 'new'}`;
  const [draft, setDraft] = useState<ResourceDraft>(() => {
    let restored = null;
    try { restored = restoreResourceDraft(localStorage.getItem(storageKey), initial?.id); } catch { /* Storage can be unavailable. */ }
    return restored ?? { request_id: crypto.randomUUID(), kind: 'text', name: initial?.name ?? '', url: '', content: initial?.content ?? '', revision: initial?.revision ?? 0, ...(initial ? { resource_id: initial.id } : {}) };
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  const alive = useRef(true), allowNavigation = useRef(false), dialog = useRef<HTMLDialogElement>(null);
  const dirty = draft.name !== (initial?.name ?? '') || draft.content !== (initial?.content ?? '') || !!draft.url;
  const blocker = useBlocker(() => dirty && !allowNavigation.current);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (blocker.state === 'blocked') dialog.current?.showModal(); else dialog.current?.close();
  }, [blocker.state]);
  useEffect(() => {
    if (!dirty) return;
    try { localStorage.setItem(storageKey, JSON.stringify(draft)); }
    catch { setMessage('브라우저 임시 저장을 사용할 수 없습니다. 이동하기 전에 본문을 복사해주세요.'); }
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [draft, dirty, storageKey]);
  function update(patch: Partial<ResourceDraft>) {
    setDraft(value => ({ ...value, ...patch, request_id: crypto.randomUUID() }));
    setError('');
  }
  async function readFile(file?: File) {
    if (!file) return;
    setBusy(true); setError('');
    try {
      const text = await readResourceFile(file);
      if (alive.current) update({ content: text, name: draft.name || file.name.slice(0, 160) });
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
    finally { if (alive.current) setBusy(false); }
  }
  async function save() {
    if (busy || !userId) return;
    setBusy(true); setError('');
    try {
      const result = await api<Resource>('/resources', 'POST', { ...draft, url: draft.kind === 'url' ? draft.url : '', content: draft.kind === 'text' ? draft.content : '' });
      if (!alive.current) return;
      try { localStorage.removeItem(storageKey); } catch { /* Saved on the server. */ }
      allowNavigation.current = true;
      navigate('/library/' + result.id, { replace: true });
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
    finally { if (alive.current) setBusy(false); }
  }
  return <main className="page reference-page library-register">
    <div className="breadcrumb"><Link to="/library">자료 보관함</Link><span>/</span>{initial ? '본문 수정' : '레퍼런스 등록'}</div>
    <span className="eyebrow">KEEP THE ORIGINAL</span><h1>{initial ? '원문을 업데이트하세요.' : '배우고 싶은 자료를 담으세요.'}</h1><p>원문을 먼저 저장합니다. AI 해석이나 문제 생성은 실행하지 않습니다.</p>
    <ErrorNotice error={error} />{message && <p role="status" className="notice">{message}</p>}
    {initial && initial.revision !== draft.revision && <p className="notice">임시 글은 v{draft.revision}에서 작성됐습니다. 서버의 v{initial.revision}과 다르므로 본문을 복사해 비교해주세요. <Link to={'/library/' + initial.id}>최신 자료 확인</Link></p>}
    <form onSubmit={e => { e.preventDefault(); void save(); }}><fieldset disabled={busy}><legend className="sr-only">레퍼런스 입력</legend>
      {!initial && <label>등록 방법<Select value={draft.kind} onChange={e => update({ kind: e.target.value as ResourceDraft['kind'] })}><option value="text">텍스트 · Markdown · 파일</option><option value="url">URL에서 가져오기</option></Select></label>}
      <label>자료 제목<input required value={draft.name} maxLength={160} onChange={e => update({ name: e.target.value })} placeholder="나중에 다시 찾을 수 있는 이름" /></label>
      {draft.kind === 'url' ? <><label>원문 URL<input required type="url" value={draft.url} maxLength={2000} onChange={e => update({ url: e.target.value })} placeholder="https://" /></label><p className="reference-state">같은 URL은 하나의 자료로 관리합니다. 가져온 본문이 달라졌을 때만 새 버전을 추가합니다. 수집에 실패해도 주소와 마지막 정상 본문은 남습니다.</p></> : <><label>파일에서 불러오기 <input type="file" accept=".md,.txt,text/plain,text/markdown" onChange={e => { void readFile(e.target.files?.[0]); e.target.value = ''; }} /></label><label>원문 본문<textarea required rows={16} maxLength={60000} value={draft.content} onChange={e => update({ content: e.target.value })} placeholder="텍스트 또는 Markdown을 붙여넣으세요." /></label><p className="reference-state">{draft.content.length.toLocaleString()} / 60,000자 · 원문 서식과 공백을 보존합니다.</p></>}
      <div className="reference-actions"><Link className="button" to={initial ? '/library/' + initial.id : '/library'}>돌아가기</Link><button className="primary" disabled={!userId || !draft.name.trim() || !(draft.kind === 'url' ? draft.url.trim() : draft.content.trim())}>{busy ? '저장 중…' : initial ? '본문 저장' : '자료 등록'}</button></div>
    </fieldset></form><p className="reference-state" role="status">{busy ? '원문을 저장하고 있습니다. URL 수집에는 잠시 시간이 걸릴 수 있습니다.' : '작성 중인 내용은 이 브라우저에 임시 보관됩니다.'}</p>
    <dialog ref={dialog} aria-labelledby="resource-leave-title" className="reference-leave-dialog" onCancel={e => { e.preventDefault(); if (blocker.state === 'blocked') blocker.reset(); }}><h2 id="resource-leave-title">저장하지 않은 내용이 있습니다.</h2><p>계정에 저장하려면 작성 화면에서 저장해주세요.</p><div className="reference-actions"><button className="primary" onClick={() => { if (blocker.state === 'blocked') blocker.reset(); }}>계속 작성</button><button onClick={() => { if (blocker.state === 'blocked') blocker.proceed(); }}>임시 글을 남기고 이동</button></div></dialog>
  </main>;
}

export function ResourceDetail() {
  const { id } = useParams();
  const { userId } = useApp();
  return <Detail key={userId + ':' + id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const { data, error, reload } = useResource<Resource>('/resources/' + id);
  const [result, setResult] = useState<Resource | null>(null), [old, setOld] = useState<ResourceVersion | null>(null);
  const [busy, setBusy] = useState(false), [actionError, setActionError] = useState(''), [message, setMessage] = useState('');
  const alive = useRef(true), requestId = useRef(crypto.randomUUID()), versionRequest = useRef(0);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const current = result ?? data;
  async function refresh() {
    if (!current || busy) return;
    setBusy(true); setActionError('');
    try {
      const next = await api<Resource>('/resources', 'POST', { request_id: requestId.current, resource_id: id, revision: 0, kind: 'url', name: current.name, url: current.url, content: '' });
      if (!alive.current) return;
      setResult(next); setOld(null); versionRequest.current++;
      setMessage(next.state === 'failed' ? '주소를 보존했습니다. 잠시 후 다시 가져와주세요.' : next.revision === current.revision ? '본문이 같아 기존 버전을 유지했습니다.' : `변경된 본문을 v${next.revision}로 저장했습니다.`);
      requestId.current = crypto.randomUUID();
    } catch (e) { if (alive.current) setActionError(errorMessage(e)); }
    finally { if (alive.current) setBusy(false); }
  }
  async function showVersion(revision: number) {
    const token = ++versionRequest.current;
    setActionError('');
    try {
      const next = await api<ResourceVersion>(`/resources/${id}/versions/${revision}`);
      if (alive.current && token === versionRequest.current) setOld(next);
    } catch (e) { if (alive.current && token === versionRequest.current) setActionError(errorMessage(e)); }
  }
  const url = safeSourceUrl(current?.url ?? undefined);
  return <main className="page reference-page library-detail"><div className="breadcrumb"><Link to="/library">자료 보관함</Link><span>/</span> 원문 상세</div>
    <ErrorNotice error={error || actionError} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!current && !error && <LoadingSkeleton layout="editor" label="자료를 불러오는 중…" />}
    {current && <><header className="reference-page-heading"><div><span className="eyebrow">{resourceKinds[current.kind]}</span><h1>{current.name}</h1><p>본문 {current.revision ? `v${current.revision}` : '수집 대기'} · {timestamp(current.updated_at)}</p></div><div className="reference-actions">{current.note_id ? <Link className="button primary" to={'/references/' + current.note_id}>노트 열기 · 편집</Link> : current.kind === 'url' ? <button className="primary" disabled={busy} onClick={() => void refresh()}>{busy ? '가져오는 중…' : '다시 가져오기'}</button> : <Link className="button primary" to={'/library/' + id + '/edit'}>본문 수정</Link>}</div></header>
      {url && <p className="library-source"><a href={url} target="_blank" rel="noreferrer">{current.url} ↗</a></p>}
      {current.state === 'failed' && <p className="notice error" role="alert">{current.error || '아직 가져온 본문이 없습니다.'}{current.revision > 0 && ' 마지막으로 저장한 본문을 표시합니다.'}</p>}
      {current.state === 'fetching' && <p role="status" className="notice">원문 수집 중입니다. <button onClick={() => { setResult(null); reload(); }}>상태 확인</button></p>}
      {message && <p className="reference-state" role="status">{message}</p>}
      {current.content !== null ? <article className="reference-reading"><Markdown language="" images={!!current.note_id}>{current.content}</Markdown></article> : <section className="reference-empty"><h2>아직 수집된 본문이 없습니다.</h2><p>원문 주소는 저장되어 있습니다. 다시 가져오기를 눌러 재시도하세요.</p></section>}
      <section className="library-versions"><h2>본문 버전 · {current.versions.length}</h2>{current.kind !== 'note' && <p>본문이 변경된 경우에만 새 버전이 추가됩니다. 이전 원문은 그대로 보존됩니다.</p>}<div className="reference-version-list">{current.versions.map(v => <button key={v.revision} onClick={() => void showVersion(v.revision)}>v{v.revision} · {timestamp(v.created_at)}</button>)}</div></section>
      {old && <section className="reference-old-version"><header><h2>저장된 원문 v{old.revision} · {old.name}</h2><button onClick={() => { versionRequest.current++; setOld(null); }}>닫기</button></header><Markdown language="" images={!!current.note_id}>{old.content ?? '이 버전에는 수집된 본문이 없습니다.'}</Markdown></section>}
    </>}
  </main>;
}
