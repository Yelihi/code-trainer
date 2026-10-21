import { Select } from './Select';
import { LoadingSkeleton } from './LoadingSkeleton';
import { AnimatedDetails } from './AnimatedDetails';
import { useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Markdown } from './Markdown';
import { ReferenceEditor } from './ReferenceEditor';
import { ReferenceKnowledge } from './ReferenceKnowledge';
import { clearReferenceDraft, newReferenceId, referenceKinds, type ReferenceMetadata, type ReferenceNote } from './referenceTypes';
import './referenceNotes.css';

type NoteList = { items: (Pick<ReferenceNote, 'id' | 'title' | 'metadata' | 'revision' | 'updated_at'> & { excerpt: string })[]; total: number; page: number; pages: number };
const emptyMetadata: ReferenceMetadata = { kind: 'other', title: '', author: '', url: '', locator: '' };

export function ReferenceNotes() {
  const [params, setParams] = useSearchParams();
  const query = params.get('q') ?? '', page = Math.max(1, Number(params.get('page')) || 1), archived = params.get('archived') === 'true';
  const { data, error, reload } = useResource<NoteList>(`/reference-notes?q=${encodeURIComponent(query)}&page=${page}&archived=${archived}`);
  const [search, setSearch] = useState(query);
  return <main className="page reference-page">
    <div className="breadcrumb"><Link to="/">Workspace</Link><span>/</span> 레퍼런스 노트</div>
    <header className="reference-page-heading"><div><span className="eyebrow">READ. REFLECT. CONNECT.</span><h1>내 언어로 쌓는 배움.</h1><p>책에서 읽은 문장, 강의에서 얻은 생각, 직접 발견한 답을 남겨보세요.</p></div><Link className="button primary" to="/references/new">+ 새 노트 작성</Link></header>
    <div className="reference-library-tools"><form role="search" onSubmit={e => { e.preventDefault(); setParams({ q: search, archived: String(archived) }); }}><label className="sr-only" htmlFor="reference-search">노트 검색</label><input id="reference-search" type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="제목이나 본문에서 찾기" maxLength={160} /><button>검색</button></form><button aria-pressed={archived} onClick={() => setParams({ q: query, archived: String(!archived) })}>{archived ? '작성한 노트 보기' : '보관한 노트'}</button></div>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="list" label="노트를 불러오는 중…" />}
    {data && <><div className="reference-list-caption"><span>{archived ? '보관한 노트' : '나의 레퍼런스'}</span><span>{data.total}개의 기록</span></div>
      {data.items.length ? <div className="reference-list">{data.items.map(note => <Link className="reference-list-item" to={'/references/' + note.id} key={note.id}><div className="reference-list-mark" aria-hidden="true">↳</div><div><small>{referenceKinds[note.metadata.kind]}{note.metadata.title ? ' · ' + note.metadata.title : ''}</small><h2>{note.title}</h2><p>{note.excerpt.replace(/!\[[^\]]*\]\([^)]*\)/g, '[이미지]')}</p><footer><span>{note.metadata.locator || '자유롭게 남긴 기록'}</span><span>{timestamp(note.updated_at)} · v{note.revision}</span></footer></div><span aria-hidden="true">↗</span></Link>)}</div>
        : <section className="reference-empty"><span aria-hidden="true">Aa</span><h2>{query ? '검색한 내용을 찾지 못했습니다.' : archived ? '보관한 노트가 없습니다.' : '한 문장부터 시작해보세요.'}</h2><p>완성된 정리가 아니어도 괜찮습니다.<br />기록을 남기고, 준비됐을 때 개념 지도에 연결하세요.</p>{!archived && <Link className="button" to="/references/new">첫 노트 작성</Link>}</section>}
      {data.pages > 1 && <nav className="pagination" aria-label="노트 페이지"><button disabled={page <= 1} onClick={() => setParams({ q: query, archived: String(archived), page: String(page - 1) })}>이전</button><span>{data.page} / {data.pages}</span><button disabled={page >= data.pages} onClick={() => setParams({ q: query, archived: String(archived), page: String(page + 1) })}>다음</button></nav>}
    </>}
  </main>;
}

export function ReferenceNoteRoute() {
  const { id } = useParams();
  if (!id) return <NoteEditor key="new" initial={null} />;
  return <ExistingNote key={id} id={id} />;
}

function ExistingNote({ id }: { id: string }) {
  const { data, error, reload } = useResource<ReferenceNote>('/reference-notes/' + id);
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <button onClick={reload}>다시 불러오기</button> : <LoadingSkeleton layout="editor" label="노트를 불러오는 중…" heading />}</main>;
  return <NoteEditor initial={data} />;
}

function NoteEditor({ initial }: { initial: ReferenceNote | null }) {
  const navigate = useNavigate();
  const { userId } = useApp();
  const [draftOwner] = useState(userId);
  const storageKey = `reference-draft:${draftOwner}:${initial?.id ?? 'new'}`;
  const [restored] = useState(() => {
    try {
      const draft = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
      return draft && typeof draft.title === 'string' && typeof draft.body === 'string' && typeof draft.revision === 'number' && draft.metadata && Object.keys(emptyMetadata).every(k => typeof draft.metadata[k] === 'string') ? draft as { id?: string; title: string; body: string; metadata: ReferenceMetadata; revision: number } : null;
    } catch { return null; }
  });
  const [note, setNote] = useState(initial);
  const [noteId] = useState(initial?.id ?? (restored?.id && /^[a-f0-9]{32}$/.test(restored.id) ? restored.id : newReferenceId()));
  const [title, setTitle] = useState(restored?.title ?? initial?.title ?? '');
  const [body, setBody] = useState(restored?.body ?? initial?.body ?? '');
  const [metadata, setMetadata] = useState(restored?.metadata ?? initial?.metadata ?? emptyMetadata);
  const [revision, setRevision] = useState(restored?.revision ?? initial?.revision ?? 0);
  const [tab, setTab] = useState<'write' | 'read' | 'connect'>(initial && !restored ? 'read' : 'write');
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState(restored ? '이 브라우저에 남아 있던 임시 글을 복원했습니다.' : '');
  const [oldVersion, setOldVersion] = useState<{ revision: number; body: string; title: string } | null>(null);
  const allowNavigation = useRef(false);
  const snapshot = JSON.stringify({ title, body, metadata });
  const dirty = snapshot !== JSON.stringify({ title: note?.title ?? '', body: note?.body ?? '', metadata: note?.metadata ?? emptyMetadata });
  const blocker = useBlocker(() => dirty && !allowNavigation.current);
  const confirmDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (blocker.state === 'blocked') confirmDialog.current?.showModal();
    else confirmDialog.current?.close();
  }, [blocker.state]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', warn);
    const timer = setTimeout(() => {
      try { localStorage.setItem(storageKey, JSON.stringify({ id: noteId, title, body, metadata, revision })); }
      catch { setMessage('브라우저 임시 저장 공간이 부족합니다. 저장 버튼으로 노트를 저장해주세요.'); }
    }, 400);
    return () => { window.removeEventListener('beforeunload', warn); clearTimeout(timer); };
  }, [dirty, title, body, metadata, revision, storageKey, noteId]);
  function updateMetadata(patch: Partial<ReferenceMetadata>) { setMetadata(v => ({ ...v, ...patch })); }
  async function save() {
    setBusy(true); setError('');
    try {
      const result = await api<ReferenceNote>('/reference-notes', 'POST', { id: noteId, title, body, metadata, revision });
      setNote(result); setTitle(result.title); setBody(result.body); setMetadata(result.metadata); setRevision(result.revision);
      clearReferenceDraft(storageKey); setMessage(`노트 v${result.revision}을 저장했습니다.`); allowNavigation.current = true;
      if (!initial) navigate('/references/' + result.id, { replace: true });
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  useEffect(() => { if (dirty) allowNavigation.current = false; }, [dirty]);
  async function archive() {
    if (!note || !window.confirm(note.archived ? '이 노트를 복원할까요? 그래프 연결은 다시 검토해야 합니다.' : '노트를 보관할까요? 이전 버전과 복습 기록은 유지되며, 현재 그래프의 근거로 사용되지 않습니다.')) return;
    setBusy(true); setError('');
    try { const next = await api<ReferenceNote>(`/reference-notes/${note.id}/archive`, 'POST', { archived: !note.archived }); setNote(next); setRevision(next.revision); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function review() {
    if (!note) return;
    setBusy(true); setError('');
    try { const next = await api<{ id: string }>('/reference-reviews', 'POST', { note_id: note.id, request_id: crypto.randomUUID() }); navigate('/reference-reviews/' + next.id); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <main className="page reference-page reference-detail">
    <div className="breadcrumb"><Link to="/references">레퍼런스 노트</Link><span>/</span>{note ? '나의 기록' : '새 노트'}</div>
    <header className="reference-detail-heading"><div><span className="eyebrow">REFERENCE NOTE</span><p className="reference-save-state" aria-live="polite">{dirty ? '저장하지 않은 변경사항' : note ? `v${note.revision} · ${timestamp(note.updated_at)} 저장` : '새로운 배움을 기록하세요'}</p></div><div className="reference-actions">
      {note && !note.archived && <button disabled={busy || dirty} onClick={() => navigate(`/github/share?kind=note&id=${note.id}`)}>GitHub 이슈로 공유 ↗</button>}
      {note && <button disabled={busy || dirty || !!note.archived} onClick={() => void review()}>내 말로 설명해보기 ↗</button>}
      <button className="primary" disabled={busy || uploading || !!note?.archived || !title.trim() || !body.trim() || (!!note && !dirty)} onClick={() => void save()}>{busy ? '처리 중…' : '노트 저장'}</button>
    </div></header>
    <ErrorNotice error={error} />{message && <p className="reference-state" role="status">{message}</p>}
    {note?.archived ? <p className="notice">보관한 노트입니다. <button onClick={() => void archive()}>복원하기</button></p> : null}
    {note && revision !== note.revision && <p className="notice">임시 글은 v{revision}에서 작성됐고 서버에는 v{note.revision}이 있습니다. 아래 글을 복사해 보관한 후 최신 버전과 비교해주세요.<button onClick={() => { if (window.confirm('임시 글을 버리고 서버의 최신 내용을 불러올까요?')) { setTitle(note.title); setBody(note.body); setMetadata(note.metadata); setRevision(note.revision); clearReferenceDraft(storageKey); } }}>서버 내용 불러오기</button></p>}
    <div className="reference-tabs" role="group" aria-label="노트 작업">
      <button aria-pressed={tab === 'write'} onClick={() => setTab('write')}>작성</button><button aria-pressed={tab === 'read'} onClick={() => setTab('read')}>읽기</button>
      <button aria-pressed={tab === 'connect'} disabled={!note || dirty || !!note.archived} onClick={() => setTab('connect')}>개념 지도에 추가하기</button>
      {dirty && <small>노트를 저장한 후 연결·복습할 수 있습니다.</small>}
    </div>
    {tab === 'write' && <><label className="reference-title"><span className="sr-only">노트 제목</span><input placeholder="어떤 배움을 남길까요?" value={title} maxLength={160} disabled={busy || !!note?.archived} onChange={e => setTitle(e.target.value)} /></label>
      <AnimatedDetails className="reference-metadata" summary={<>출처 기록 <span>{referenceKinds[metadata.kind]}{metadata.title ? ' · ' + metadata.title : ' · 선택 사항'}</span></>}><fieldset disabled={busy || !!note?.archived}><legend className="sr-only">출처 정보</legend>
        <div className="reference-fields"><label>자료 종류<Select value={metadata.kind} onChange={e => updateMetadata({ kind: e.target.value as ReferenceMetadata['kind'] })}>{Object.entries(referenceKinds).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></label><label>책 · 강의 · 자료 이름<input value={metadata.title} maxLength={300} onChange={e => updateMetadata({ title: e.target.value })} /></label><label>저자 · 강사<input value={metadata.author} maxLength={200} onChange={e => updateMetadata({ author: e.target.value })} /></label><label>페이지 · 회차 · 시간<input value={metadata.locator} maxLength={300} placeholder="예: 3장, 42–48쪽 / 4강 12:30" onChange={e => updateMetadata({ locator: e.target.value })} /></label></div><label>출처 URL<input type="url" value={metadata.url} maxLength={2000} placeholder="https://" onChange={e => updateMetadata({ url: e.target.value })} /></label>
      </fieldset></AnimatedDetails>
      <ReferenceEditor value={body} onChange={setBody} disabled={busy || !!note?.archived} onUploading={setUploading} />
      <p className="reference-state">작성 중인 글은 이 브라우저에 임시 보관됩니다. ‘노트 저장’을 눌러 계정에 저장하세요.</p>
    </>}
    {tab === 'read' && <article className="reference-reading"><span className="eyebrow">{referenceKinds[metadata.kind]}</span><h1>{title || '제목 없는 노트'}</h1>{metadata.title && <p className="reference-attribution">{metadata.title}{metadata.author ? ' · ' + metadata.author : ''}{metadata.locator ? ' · ' + metadata.locator : ''}</p>}<Markdown language="" images>{body || '아직 작성한 내용이 없습니다.'}</Markdown></article>}
    {tab === 'connect' && note && !dirty && <ReferenceKnowledge key={note.revision + ':' + note.registration?.id} note={note} onNoteChange={setNote} onEdit={() => setTab('write')} />}
    {note && <footer className="reference-note-footer"><AnimatedDetails summary={<>노트 버전 · {note.versions.length}</>}><div className="reference-version-list">{note.versions.map(v => <button key={v.revision} onClick={() => { void api<{ revision: number; body: string; title: string }>(`/reference-notes/${note.id}/versions/${v.revision}`).then(setOldVersion).catch(e => setError(errorMessage(e))); }}>v{v.revision} · {timestamp(v.created_at)}</button>)}</div></AnimatedDetails>
      <div className="reference-actions"><a className="button" href={`/api/reference-notes/${note.id}/export`} download>Markdown · 이미지 내보내기</a><button disabled={busy || dirty} onClick={() => void archive()}>{note.archived ? '노트 복원' : '노트 보관'}</button></div>
    </footer>}
    {oldVersion && <section className="reference-old-version"><header><h2>이전 버전 v{oldVersion.revision} · {oldVersion.title}</h2><button onClick={() => setOldVersion(null)}>닫기</button></header><Markdown language="" images>{oldVersion.body}</Markdown></section>}
    {!!note?.reviews.length && <section className="reference-past-reviews"><h2>내 말로 설명했던 기록</h2>{note.reviews.map(r => <Link key={r.id} to={'/reference-reviews/' + r.id}>{timestamp(r.created_at)} · {r.state === 'running' ? '질문 준비 중' : r.state === 'failed' ? '설명 저장됨 · 질문 재시도' : '대화 이어보기'} ↗</Link>)}</section>}
    <dialog ref={confirmDialog} className="reference-leave-dialog" onCancel={e => { e.preventDefault(); if (blocker.state === 'blocked') blocker.reset(); }}><h2>저장하지 않은 글이 있습니다.</h2><p>계정에 저장하려면 작성 화면으로 돌아가 ‘노트 저장’을 눌러주세요.</p><div className="reference-actions"><button className="primary" onClick={() => { if (blocker.state === 'blocked') blocker.reset(); }}>계속 작성</button><button onClick={() => { try { localStorage.setItem(storageKey, JSON.stringify({ id: noteId, title, body, metadata, revision })); } catch { /* Leaving remains the user's explicit choice. */ } if (blocker.state === 'blocked') blocker.proceed(); }}>임시 글을 남기고 이동</button></div></dialog>
  </main>;
}
