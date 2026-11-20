import { LoadingState } from './LoadingState';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, safeSourceUrl, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Markdown } from './Markdown';
import { NativeSelect } from './components/ui/native-select';
import { ResourceInterpretations } from './Interpretations';
import { libraryPage, readResourceFile, resourceKinds, restoreResourceDraft, type Resource, type ResourceDraft, type ResourceList, type ResourceVersion } from './libraryTypes';
import './referenceNotes.css';
import './library.css';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { FilePlus2, FilePenLine, Link2, Rss, FileWarning } from 'lucide-react';
import { ActionCard, EmptyState, PageHeading } from './WorkspaceUI';

export function Library() {
  const { userId } = useApp();
  return <LibraryList key={userId} />;
}
function LibraryList() {
  const [params, setParams] = useSearchParams();
  const query = (params.get('q') ?? '').slice(0, 160), page = libraryPage(params.get('page'));
  const kind = ['text', 'url', 'note'].includes(params.get('kind') ?? '') ? params.get('kind')! : 'all';
  const archived = params.get('archived') === 'true';
  const { data, error, reload } = useResource<ResourceList>(`/resources?q=${encodeURIComponent(query)}&page=${page}&kind=${kind}&archived=${archived}`, { preserveData: true });
  return <main className="page reference-page library-page">
    <PageHeading title={archived ? '삭제된 자료' : '원자료'} description={archived ? '기록과 출처를 유지한 채 자료를 복원할 수 있습니다.' : '원문과 직접 작성한 노트를 모으세요.'} actions={archived ? <Link className="button" to="/library">원자료로 돌아가기</Link> : undefined} />
    {!archived && <nav className="source-actions" aria-label="자료 추가 방법"><ActionCard to="/library/new/reference" icon={Link2} title="URL · 텍스트" description="링크와 파일 추가" /><ActionCard to="/references/new" icon={FilePenLine} title="직접 작성" description="내 언어로 기록" /><ActionCard to="/inbox" icon={Rss} title="자동 수집" description="RSA 기술 글" /></nav>}
    <div className="reference-library-tools"><form key={query} role="search" onSubmit={e => { e.preventDefault(); setParams({ q: String(new FormData(e.currentTarget).get("q") ?? ""), kind, ...(archived ? { archived: 'true' } : {}) }); }}><Label className="sr-only" htmlFor="library-search">자료 검색</Label><Input id="library-search" type="search" placeholder="제목, 본문, URL에서 찾기" name="q" defaultValue={query} maxLength={160} /><Button>검색</Button></form><Label className="library-filter">자료 종류<NativeSelect value={kind} onChange={e => setParams({ q: query, kind: e.target.value, ...(archived ? { archived: 'true' } : {}) })}><option value="all">모든 자료</option>{Object.entries(resourceKinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</NativeSelect></Label></div>
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="list" label="자료를 불러오는 중…" />}
    {data && <><div className="reference-list-caption"><span>{archived ? '삭제된 원문과 기록' : '나의 원문과 기록'}</span><span>{data.total}개의 자료</span></div>
      {data.items.length ? <div className="reference-list">{data.items.map(item => <Link className="reference-list-item" to={'/library/' + item.id} key={item.id}><div><div className="resource-list-meta"><small>{resourceKinds[item.kind]}</small><Badge variant="secondary" className={'resource-status resource-status-'+item.state}>{archived?'삭제됨':item.state==='failed'?'수집 실패':item.state==='fetching'?'수집 중':item.kind==='url'?'본문 준비됨':'저장됨'}</Badge>{item.revision>0&&<span>v{item.revision}</span>}</div><h2>{item.name}</h2><p>{item.excerpt || item.url || '아직 가져온 본문이 없습니다.'}</p><footer><span>{item.kind === 'note' ? '내 언어로 남긴 기록' : '원자료'}</span><span>{timestamp(item.updated_at)}</span></footer></div></Link>)}</div> : <EmptyState icon={FilePlus2} title={query ? '검색한 자료가 없습니다' : archived ? '삭제된 자료가 없습니다' : '첫 자료를 추가해보세요'} description={query ? '다른 검색어나 자료 종류로 찾아보세요.' : archived ? '삭제한 자료는 이곳에서 복원할 수 있습니다.' : 'URL, 텍스트, 파일을 저장하거나 직접 작성할 수 있습니다.'} action={!archived && !query ? <Link className="button" to="/library/new/reference">자료 추가</Link> : undefined} />}
      {data.pages > 1 && <nav className="pagination" aria-label="자료 페이지"><Button disabled={data.page <= 1} onClick={() => setParams({ q: query, kind, page: String(data.page - 1), ...(archived ? { archived: 'true' } : {}) })}>이전</Button><span>{data.page} / {data.pages}</span><Button disabled={data.page >= data.pages} onClick={() => setParams({ q: query, kind, page: String(data.page + 1), ...(archived ? { archived: 'true' } : {}) })}>다음</Button></nav>}
    </>}
    <div className="library-notes-link"><Link className="text-link" to="/library?archived=true">삭제된 자료 보기</Link></div>
  </main>;
}

export function ResourceRegister() {
  const { id } = useParams();
  const { userId } = useApp();
  const [params] = useSearchParams();
  const post = params.get('post');
  const feed = post ? { id: post, name: (params.get('title') ?? '').slice(0, 160), url: (params.get('url') ?? '').slice(0, 2000) } : undefined;
  return id ? <EditResource key={userId + ':' + id} id={id} /> : <RegistrationForm key={userId + ':' + (post ?? 'new')} initial={null} feed={feed} />;
}
function EditResource({ id }: { id: string }) {
  const { data, error, reload } = useResource<Resource>('/resources/' + id);
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <Button onClick={reload}>다시 불러오기</Button> : <LoadingSkeleton layout="editor" label="자료를 불러오는 중…" />}</main>;
  if (data.kind === 'note' || data.archived) return <main className="page"><p>{data.archived ? '삭제된 자료를 먼저 복원해주세요.' : '직접 작성한 노트는 노트 화면에서 수정할 수 있습니다.'}</p><Link className="button" to={'/library/' + id}>자료로 돌아가기</Link></main>;
  return <RegistrationForm initial={data} />;
}
function RegistrationForm({ initial, feed }: { initial: Resource | null; feed?: { id: string; name: string; url: string } }) {
  const navigate = useNavigate();
  const { userId } = useApp();
  const storageKey = `resource-draft:${userId}:${initial?.id ?? (feed ? 'feed:' + feed.id : 'new')}`;
  const [draft, setDraft] = useState<ResourceDraft>(() => {
    let restored = null;
    try { restored = restoreResourceDraft(localStorage.getItem(storageKey), initial?.id, feed?.id); } catch { /* Storage can be unavailable. */ }
    return restored ?? { request_id: crypto.randomUUID(), kind: initial?.kind === 'url' || feed ? 'url' : 'text', name: initial?.name ?? feed?.name ?? '', url: initial?.url ?? feed?.url ?? '', content: initial?.kind === 'url' ? '' : initial?.content ?? '', revision: initial?.revision ?? 0, ...(initial ? { resource_id: initial.id } : {}), ...(feed ? { feed_post_id: feed.id } : {}) };
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  const alive = useRef(true), allowNavigation = useRef(false), dialog = useRef<HTMLDialogElement>(null);
  const fileInput = useRef<HTMLInputElement>(null), dragDepth = useRef(0);
  const [dragging, setDragging] = useState(false), [fileName, setFileName] = useState('');
  const dirty = draft.name !== (initial?.name ?? feed?.name ?? '') || draft.content !== (initial?.kind === 'url' ? '' : initial?.content ?? '') || draft.url !== (initial?.url ?? feed?.url ?? '');
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
  const update = useCallback((patch: Partial<ResourceDraft>) => {
    setDraft(value => ({ ...value, ...patch, request_id: crypto.randomUUID() }));
    setError('');
  }, []);
  const readFile = useCallback(async (file?: File) => {
    if (!file || busy) return;
    setBusy(true); setError('');
    try {
      const text = await readResourceFile(file);
      if (alive.current) { update({ content: text, name: draft.name || file.name.slice(0, 160) }); setFileName(file.name); }
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
    finally { if (alive.current) setBusy(false); }
  }, [busy, draft.name, update]);
  useEffect(() => {
    if (draft.kind !== 'text') return;
    const hasFile = (event: DragEvent) => event.dataTransfer?.types.includes('Files');
    const enter = (event: DragEvent) => { if (hasFile(event)) { event.preventDefault(); dragDepth.current++; setDragging(true); } };
    const over = (event: DragEvent) => { if (hasFile(event)) event.preventDefault(); };
    const leave = () => { if (dragDepth.current > 0 && --dragDepth.current === 0) setDragging(false); };
    const drop = (event: DragEvent) => { if (!event.dataTransfer?.files.length) return; event.preventDefault(); dragDepth.current = 0; setDragging(false); void readFile(event.dataTransfer.files[0]); };
    window.addEventListener('dragenter', enter); window.addEventListener('dragover', over);
    window.addEventListener('dragleave', leave); window.addEventListener('drop', drop);
    return () => { window.removeEventListener('dragenter', enter); window.removeEventListener('dragover', over); window.removeEventListener('dragleave', leave); window.removeEventListener('drop', drop); };
  }, [draft.kind, readFile]);
  async function save() {
    if (busy || !userId) return;
    setBusy(true); setError('');
    // Prefilled RSA inputs can be unchanged; retain their replay identity before sending.
    try { localStorage.setItem(storageKey, JSON.stringify(draft)); }
    catch { setMessage('브라우저 임시 저장을 사용할 수 없습니다. 이동하기 전에 본문을 복사해주세요.'); }
    try {
      const result = await api<Resource>('/resources', 'POST', { ...draft, url: draft.kind === 'url' ? draft.url : '', content: draft.kind === 'text' ? draft.content : '' });
      if (!alive.current) return;
      if (initial?.kind === 'url' && result.state === 'failed' && draft.url !== initial.url) {
        setDraft(value => ({ ...value, request_id: crypto.randomUUID() }));
        setError(`${result.error || '새 주소에서 원문을 가져오지 못했습니다.'} 기존 URL과 본문은 유지했습니다. 주소를 확인한 뒤 다시 시도해주세요.`);
        return;
      }
      try { localStorage.removeItem(storageKey); } catch { /* Saved on the server. */ }
      allowNavigation.current = true;
      navigate('/library/' + result.id, { replace: true });
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
    finally { if (alive.current) setBusy(false); }
  }
  return <main className="page reference-page library-register">
    <div className="breadcrumb"><Link to="/library">자료 보관함</Link><span>/</span>{initial ? '본문 수정' : '레퍼런스 등록'}</div>
    <span className="eyebrow">KEEP THE ORIGINAL</span><h1>{initial?.kind === 'url' ? '원문 주소를 수정하세요.' : initial ? '원문을 업데이트하세요.' : '배우고 싶은 자료를 담으세요.'}</h1><p>{initial?.kind === 'url' ? '개별 글의 URL을 입력하면 새 본문을 가져옵니다. 이전 본문은 버전 기록에 남습니다.' : '원문을 먼저 저장합니다. AI 해석이나 문제 생성은 실행하지 않습니다.'}</p>
    {feed && <p className="notice">RSA에서 선택한 글입니다. 소개 글이라면 원문 URL로 바꿔주세요. 원문 수집에 성공하면 대기 목록에서 빠집니다.</p>}
    <ErrorNotice error={error} />{message && <p role="status" className="notice">{message}</p>}
    {initial && initial.revision !== draft.revision && <p className="notice">임시 글은 v{draft.revision}에서 작성됐습니다. 서버의 v{initial.revision}과 다르므로 본문을 복사해 비교해주세요. <Link className="button" to={'/library/' + initial.id}>최신 자료 확인</Link></p>}
    {dragging && <div className="library-drop-overlay" aria-hidden="true"><FilePlus2 size={36} strokeWidth={1.5} /><strong>파일 추가</strong><span>.md 또는 .txt 파일을 놓으세요</span></div>}
    <form onSubmit={e => { e.preventDefault(); void save(); }}><fieldset disabled={busy}><legend className="sr-only">레퍼런스 입력</legend>
      {!initial && !feed && <Label>등록 방법<NativeSelect value={draft.kind} onChange={e => update({ kind: e.target.value as ResourceDraft['kind'] })}><option value="text">텍스트 · Markdown · 파일</option><option value="url">URL에서 가져오기</option></NativeSelect></Label>}
      {draft.kind === 'text' && fileName && <div className="library-file-summary" role="status"><FilePlus2 size={18} aria-hidden="true" /><span>추가된 파일 · <strong>{fileName}</strong></span></div>}
      <Label>자료 제목<Input required value={draft.name} maxLength={160} onChange={e => update({ name: e.target.value })} placeholder="나중에 다시 찾을 수 있는 이름" /></Label>
      {draft.kind === 'url' ? <><Label>원문 URL<Input required type="url" value={draft.url} maxLength={2000} onChange={e => update({ url: e.target.value })} placeholder="https://" /></Label><p className="field-hint">목록 주소 대신 개별 글의 URL을 입력하세요.</p></> : <><div className="library-file-actions"><input ref={fileInput} hidden type="file" accept=".md,.txt,text/plain,text/markdown" onChange={e => { void readFile(e.target.files?.[0]); e.target.value = ''; }} /><Button type="button" onClick={() => fileInput.current?.click()}><FilePlus2 size={18} aria-hidden="true" />파일 추가</Button><span>파일을 화면에 끌어다 놓을 수도 있습니다.</span></div><Label>원문 본문<Textarea required rows={16} maxLength={60000} value={draft.content} onChange={e => update({ content: e.target.value })} placeholder="텍스트 또는 Markdown을 붙여넣으세요." /><span className="field-hint field-counter">{draft.content.length.toLocaleString()} / 60,000자</span></Label></>}
      <div className="reference-actions"><Link className="button" to={initial ? '/library/' + initial.id : feed ? '/inbox' : '/library'}>돌아가기</Link><Button className="primary" loading={busy} disabled={!userId || !draft.name.trim() || !(draft.kind === 'url' ? draft.url.trim() : draft.content.trim())}>{busy ? '저장 중…' : initial?.kind === 'url' ? 'URL 변경 · 다시 수집' : initial ? '본문 저장' : '자료 등록'}</Button></div>
    </fieldset></form><p className="reference-state" role="status">{busy ? '원문 저장 중' : '브라우저에 임시 보관 중'}</p>
    <dialog ref={dialog} aria-labelledby="resource-leave-title" className="reference-leave-dialog" onCancel={e => { e.preventDefault(); if (blocker.state === 'blocked') blocker.reset(); }}><h2 id="resource-leave-title">저장하지 않은 내용이 있습니다.</h2><p>이탈하면 입력한 내용과 브라우저 임시 글이 삭제됩니다.</p><div className="reference-actions"><Button className="primary" onClick={() => { if (blocker.state === 'blocked') blocker.reset(); }}>계속 작성</Button><Button onClick={() => { if (blocker.state === 'blocked') { try { localStorage.removeItem(storageKey); } catch { /* Navigation still follows the user's choice. */ } blocker.proceed(); } }}>이탈 · 내용 삭제</Button></div></dialog>
  </main>;
}

export function ResourceDetail() {
  const { id } = useParams();
  const { userId } = useApp();
  return <Detail key={userId + ':' + id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const navigate = useNavigate();
  const { data, error, reload } = useResource<Resource>('/resources/' + id);
  const [result, setResult] = useState<Resource | null>(null), [old, setOld] = useState<ResourceVersion | null>(null);
  const [manual,setManual]=useState(false);
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
      setMessage(next.state === 'failed' ? '' : next.revision === current.revision ? '본문이 같아 기존 버전을 유지했습니다.' : `변경된 본문을 v${next.revision}로 저장했습니다.`);
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
  async function changeArchive(archived: boolean) {
    if (!current || busy) return;
    if (archived && !window.confirm('이 자료를 보관함에서 삭제할까요? 연결된 학습 기록과 이전 본문은 보존되며, 삭제된 자료에서 복원할 수 있습니다.')) return;
    setBusy(true); setActionError('');
    try {
      const next = await api<Resource>(`/resources/${id}/archive`, 'POST', { archived });
      if (!alive.current) return;
      setResult(next);
      if (archived) navigate('/library?archived=true');
      else setMessage('자료를 복원했습니다.');
    } catch (e) { if (alive.current) setActionError(errorMessage(e)); }
    finally { if (alive.current) setBusy(false); }
  }
  const url = safeSourceUrl(current?.url ?? undefined);
  const content=old?old.content:current?.content;
  const hasBody=!!content?.trim();
  return <main className="page reference-page library-detail resource-reader"><div className="breadcrumb"><Link to="/library">원자료</Link><span>/</span> 원문 상세</div>
    <ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!current && !error && <LoadingSkeleton layout="editor" label="자료를 불러오는 중…" />}
    {current && <><PageHeading title={current.name} meta={<div className="resource-heading-meta"><Badge variant="secondary" className={'resource-status resource-status-'+current.state}>{current.archived?'삭제됨':current.state==='failed'?(current.revision?'갱신 실패':'수집 실패'):current.state==='fetching'?'수집 중':current.kind==='url'?'본문 준비됨':'저장됨'}</Badge>{current.feed_pending&&<Badge variant="outline">RSA 등록 대기</Badge>}{current.revision>0&&<span>본문 v{current.revision}</span>}<time>{timestamp(current.updated_at)}</time></div>}
      actions={current.archived?<Button loading={busy} onClick={()=>void changeArchive(false)}>자료 복원</Button>:<>{current.note_id?<Link className="button" to={'/references/'+current.note_id}>노트 수정</Link>:current.kind!=='url'?<Link className="button" to={'/library/'+id+'/edit'}>본문 수정</Link>:hasBody&&<><Link className="button" to={'/library/'+id+'/edit'}>URL 수정</Link><Button loading={busy} disabled={busy} onClick={()=>void refresh()}>다시 가져오기</Button></>}<Button variant="ghost" disabled={busy} onClick={()=>void changeArchive(true)}>자료 삭제</Button></>}/>
      {url&&<div className="resource-origin"><Link2 size={18} aria-hidden="true"/><span>{current.url}</span><a className="button" href={url} target="_blank" rel="noreferrer">원문 열기</a></div>}
      {!!current.archived&&<p className="notice" role="status">삭제된 자료입니다. 복원하면 다시 보관함에 표시됩니다.</p>}
      {message&&<p className="reference-state resource-heading-meta" role="status"><Badge variant="secondary">확인 완료</Badge>{message}</p>}
      {manual?<ManualResourceBody key={id} resource={current} onSaved={next=>{setResult(next);setOld(null);setManual(false);versionRequest.current++;setMessage('직접 입력한 본문을 저장했습니다.');}} onCancel={()=>setManual(false)}/>:
      !hasBody&&current.state==='fetching'?<section className="resource-loading"><LoadingState compact status="수집 중" title="원문을 가져오고 있어요" description="원문 주소는 저장했어요. 수집 상태를 다시 확인할 수 있어요." /><div className="resource-recovery-actions"><Button onClick={()=>{setResult(null);reload();}}>상태 확인</Button>{current.feed_pending&&<Badge variant="outline">RSA 등록 대기</Badge>}</div></section>:!hasBody?<section className="resource-recovery" aria-labelledby="resource-recovery-title"><span className="resource-recovery-icon" aria-hidden="true">{current.state==='failed'?<FileWarning size={28}/>:<FilePlus2 size={28}/>}</span><h2 id="resource-recovery-title">{current.state==='fetching'?'원문을 가져오고 있어요':'본문을 가져오지 못했어요'}</h2><p role={current.state==='failed'?'alert':'status'}>{current.error||'원문 주소는 저장되어 있습니다. 본문 수집 상태를 확인해주세요.'}</p><div className="resource-recovery-actions">{!current.archived&&<>{current.state==='fetching'?<Button onClick={()=>{setResult(null);reload();}}>상태 확인</Button>:<><Button className="primary" loading={busy} disabled={busy} onClick={()=>void refresh()}>다시 가져오기</Button><Button disabled={busy} onClick={()=>setManual(true)}>본문 직접 입력</Button><Link className="button" to={'/library/'+id+'/edit'}>URL 수정</Link></>}</>}</div>{current.feed_pending&&<div className="resource-feed-state"><Badge variant="outline">RSA 등록 대기</Badge><Link className="text-link" to="/inbox">자동 수집 목록</Link></div>}</section>:
      <>{current.state==='fetching'&&<LoadingState compact status="갱신 중" title="새 본문을 가져오고 있어요" description="마지막으로 저장한 본문을 읽을 수 있어요." />}{current.state==='failed'&&<section className="resource-refresh-error" role="alert"><Badge variant="secondary" className="resource-status resource-status-failed">갱신 실패</Badge><span>{current.error} 마지막 저장 본문은 유지했습니다.</span>{!current.archived&&<Button disabled={busy} onClick={()=>setManual(true)}>본문 직접 입력</Button>}</section>}
      <div className="reading-workspace resource-body-layout"><article id="resource-body" className="reference-reading reading-content"><header className="reading-document-heading"><h2>원문</h2><Label className="resource-version-select">본문 버전<NativeSelect aria-label="본문 버전" value={String(old?.revision??current.revision)} onChange={e=>{if(Number(e.target.value)===current.revision){versionRequest.current++;setOld(null);}else void showVersion(Number(e.target.value));}}>{current.versions.map(v=><option key={v.revision} value={String(v.revision)}>v{v.revision}{v.revision===current.revision?' · 최신':''} · {timestamp(v.created_at)}</option>)}</NativeSelect></Label></header>
      {old&&old.url!==current.url&&<p className="library-version-url">당시 원문 URL · {old.url}</p>}<Markdown language="" images={!!current.note_id}>{content!}</Markdown></article><aside className="reading-context" aria-label="이 자료로 탐구하기">{!current.archived&&<ResourceInterpretations resourceId={id} revision={old?.revision??current.revision} content={content??null}/>}</aside></div></>}
    </>}
  </main>;
}
function ManualResourceBody({resource,onSaved,onCancel}:{resource:Resource;onSaved:(value:Resource)=>void;onCancel:()=>void}) {
  const {userId}=useApp(), key='resource-body:'+userId+':'+resource.id;
  const [content,setContent]=useState(()=>{try{return localStorage.getItem(key)??'';}catch{return '';}}),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const request=useRef(crypto.randomUUID());
  const blocker=useBlocker(!!content&&!busy);
  useEffect(()=>{if(blocker.state==='blocked'){if(window.confirm('입력한 본문을 임시 보관하고 이동할까요?'))blocker.proceed();else blocker.reset();}},[blocker]);
  useEffect(()=>{if(!content)return;const leave=(event:BeforeUnloadEvent)=>event.preventDefault();window.addEventListener('beforeunload',leave);return()=>window.removeEventListener('beforeunload',leave);},[content]);
  async function save(){setBusy(true);setError('');try{const result=await api<Resource>('/resources/'+resource.id+'/content','POST',{request_id:request.current,revision:resource.revision,content});try{localStorage.removeItem(key);}catch{/* Server copy is saved. */}onSaved(result);}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}
  return <form className="resource-paste" onSubmit={event=>{event.preventDefault();void save();}}><h2>원문 본문 직접 입력</h2><p>원문에서 복사한 본문을 붙여넣으세요. URL과 이전 본문 버전은 유지합니다.</p><Label htmlFor="resource-pasted-body">본문</Label><Textarea id="resource-pasted-body" required rows={14} maxLength={60000} value={content} disabled={busy} onChange={event=>{setContent(event.target.value);request.current=crypto.randomUUID();try{localStorage.setItem(key,event.target.value);}catch{setError('임시 저장을 사용할 수 없습니다. 이동 전 본문을 복사해주세요.');}}}/><div className="resource-paste-meta"><span>{content.length.toLocaleString()} / 60,000자</span><Badge variant="secondary">직접 입력</Badge></div><ErrorNotice error={error}/><div className="resource-recovery-actions"><Button className="primary" loading={busy} disabled={busy||!content.trim()}>본문 저장</Button><Button type="button" disabled={busy} onClick={onCancel}>취소</Button></div></form>;
}
