import { useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useParams } from 'react-router-dom';
import { api, ApiError, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { MaterialReview } from './MaterialReview';
import { Markdown } from './Markdown';
import { AnimatedDetails } from './AnimatedDetails';
import type { Worksheet } from './Worksheets';
import './library.css';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';

type Content = { answers: Record<string, string>; summary: string };
type SavedRecord = Content & { worksheet_id: string; revision: number; source_kind: 'user'; updated_at: string };
type SaveRequest = Content & { revision: number; request_id: string };
type Draft = Content & { revision: number; pending?: SaveRequest };
type RecordData = { worksheet: Worksheet; record: SavedRecord | null; versions: { revision: number; updated_at: string }[] };
const blank: Content = { answers: {}, summary: '' };
function contentKey(content: Content) {
  return JSON.stringify([Object.entries(content.answers).filter(([, value]) => value !== '').sort(([a], [b]) => a.localeCompare(b)), content.summary]);
}
function validContent(value: Content, questions: Set<string>) {
  return value && typeof value.summary === 'string' && value.summary.length <= 50000 && value.answers && typeof value.answers === 'object' && !Array.isArray(value.answers) && Object.entries(value.answers).every(([key, text]) => questions.has(key) && typeof text === 'string' && text.length <= 20000);
}
function readDraft(key: string, worksheet: Worksheet): { draft: Draft | null; warning: string } {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? 'null');
    if (!value) return { draft: null, warning: '' };
    const questions = new Set(worksheet.document!.questions.map(q => q.id));
    if (!validContent(value, questions) || !Number.isInteger(value.revision) || value.revision < 0 || (value.pending && (!validContent(value.pending, questions) || !Number.isInteger(value.pending.revision) || value.pending.revision < 0 || typeof value.pending.request_id !== 'string' || value.pending.request_id.length < 8 || value.pending.request_id.length > 80))) throw new Error('Invalid draft');
    return { draft: value, warning: '' };
  } catch { return { draft: null, warning: '브라우저 임시 글을 읽지 못했습니다. 작성 후 계정에 저장해주세요.' }; }
}

export function PracticeRecordRoute() {
  const { id } = useParams(), { userId } = useApp();
  return <PracticeRecordEditor key={userId + ':' + id} worksheetId={id!} />;
}
export function PracticeRecordEditor({ worksheetId }: { worksheetId: string }) {
  const { data, error, reload } = useResource<RecordData>('/worksheets/' + worksheetId + '/practice');
  if (!data) return <main className="page reference-page"><ErrorNotice error={error} />{error ? <Button onClick={reload}>다시 불러오기</Button> : <LoadingSkeleton layout="editor" label="학습 기록을 불러오는 중…" />}</main>;
  if (data.worksheet.state !== 'ready' || !data.worksheet.document) return <main className="page"><h1>질문지가 아직 준비되지 않았습니다.</h1><Link to={'/worksheets/' + worksheetId}>생성 상태 확인</Link></main>;
  return <Editor initial={data} />;
}
function Editor({ initial }: { initial: RecordData }) {
  const { userId } = useApp(), worksheet = initial.worksheet;
  const path = '/worksheets/' + worksheet.id + '/practice', storageKey = `practice-draft:${userId}:${worksheet.id}`;
  const [restored] = useState(() => readDraft(storageKey, worksheet));
  const [draft, setDraft] = useState<Draft>(restored.draft ?? { ...(initial.record ?? blank), revision: initial.record?.revision ?? 0 });
  const current = useRef(draft), alive = useRef(true), sending = useRef(false);
  const [saved, setSaved] = useState(initial.record), [versions, setVersions] = useState(initial.versions);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [warning, setWarning] = useState(restored.warning);
  const [message, setMessage] = useState(restored.draft ? '이 브라우저의 임시 작성분을 복원했습니다.' : '');
  const [latest, setLatest] = useState<SavedRecord | null>(null), [oldVersion, setOldVersion] = useState<SavedRecord | null>(null);
  const [conflict, setConflict] = useState(false);
  const dirty = contentKey(draft) !== contentKey(saved ?? blank);
  const blocker = useBlocker(dirty || !!draft.pending);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (blocker.state === 'blocked') dialog.current?.showModal(); else dialog.current?.close();
  }, [blocker.state]);
  useEffect(() => {
    if (!dirty && !draft.pending) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty, draft.pending]);
  function update(next: Draft, baseline: SavedRecord | null = saved) {
    current.current = next; setDraft(next);
    // Persist before any request can expire the session and unmount this editor.
    try {
      if (!next.pending && contentKey(next) === contentKey(baseline ?? blank)) localStorage.removeItem(storageKey);
      else localStorage.setItem(storageKey, JSON.stringify(next));
    }
    catch { setWarning('브라우저에 임시 저장할 수 없습니다. 이 화면을 닫기 전에 계정에 저장하거나 작성분을 복사해주세요.'); }
  }
  async function save() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(''); setMessage('');
    const value = current.current;
    const request = value.pending ?? { request_id: crypto.randomUUID(), revision: value.revision, answers: value.answers, summary: value.summary };
    update({ ...value, pending: request });
    try {
      const result = await api<SavedRecord>(path, 'POST', request);
      if (!alive.current) return;
      setSaved(result); setConflict(false); setLatest(null);
      setVersions(items => items.some(v => v.revision === result.revision) ? items : [{ revision: result.revision, updated_at: result.updated_at }, ...items]);
      // A receipt advances the saved baseline, never the learner's newer text.
      update({ ...current.current, revision: result.revision, pending: undefined }, result);
      setMessage(`v${result.revision} 저장 완료.${contentKey(current.current) !== contentKey(result) ? ' 이후 작성한 내용이 남아 있습니다. 다시 저장해주세요.' : ''}`);
    } catch (e) {
      if (!alive.current) return;
      setError(errorMessage(e));
      if (e instanceof ApiError && (e.status === 409 || e.status === 422)) {
        update({ ...current.current, pending: undefined });
        if (e.status === 409) setConflict(true);
      }
    } finally { sending.current = false; if (alive.current) setBusy(false); }
  }
  async function inspectLatest() {
    setError('');
    try {
      const result = await api<RecordData>(path);
      if (alive.current) { setLatest(result.record); setVersions(result.versions); }
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
  }
  async function inspectVersion(revision: number) {
    try { const result = await api<SavedRecord>(path + '/versions/' + revision); if (alive.current) setOldVersion(result); }
    catch (e) { if (alive.current) setError(errorMessage(e)); }
  }
  return <main className="page reference-page interpretation-page practice-record-page">
    <div className="breadcrumb"><Link to="/explore/practice">실습하기</Link><span>/</span><Link to={'/worksheets/' + worksheet.id}>질문지</Link><span>/</span> 내 작성분</div>
    <header className="reference-page-heading"><div><span className="eyebrow">THINK IN YOUR OWN WORDS</span><h1>{worksheet.document!.title}</h1><p>모든 질문에 답하지 않아도 괜찮습니다. 이해한 만큼 답하고, 남은 궁금증도 기록하세요.</p></div></header>
    <aside className="interpretation-provenance"><strong>{worksheet.source_name} · 원문 v{worksheet.revision}</strong><p>질문은 AI가 만들고, 아래 답변과 요약은 내가 작성합니다.{worksheet.current_revision !== worksheet.revision && ` 원문 최신본은 v${worksheet.current_revision}이며, 이 실습은 원래 해석을 기준으로 합니다.`}</p><Link to={'/interpretations/' + worksheet.interpretation_id}>관련 해석 읽기</Link></aside>
    <ErrorNotice error={error} />{warning && <p role="alert" className="notice">{warning}</p>}{message && <p role="status">{message}</p>}
    {(conflict || draft.revision !== (saved?.revision ?? 0)) && <section className="interpretation-recovery"><p>서버 기록과 작성 기준이 다릅니다. 내 작성분은 유지됩니다. 최신본을 확인하고 이어갈 내용을 선택해주세요.</p><Button disabled={busy} onClick={() => void inspectLatest()}>서버 최신본 확인</Button></section>}
    {latest && <section className="practice-comparison"><h2>서버 최신본 v{latest.revision}</h2><PracticeRecordText content={latest} worksheet={worksheet} /><p>아래 선택은 아직 서버에 저장하지 않습니다.</p><div className="reference-actions"><Button disabled={busy} onClick={() => { setSaved(latest); update({ ...current.current, revision: latest.revision, pending: undefined }, latest); setLatest(null); setConflict(false); setError(''); setMessage('내 작성분을 유지했습니다. 비교·수정한 뒤 저장해주세요.'); }}>내 작성분을 유지하고 계속 수정</Button><Button disabled={busy} onClick={() => { if (window.confirm('현재 임시 작성분을 서버 최신본으로 바꿀까요?')) { setSaved(latest); update({ answers: latest.answers, summary: latest.summary, revision: latest.revision }, latest); setLatest(null); setConflict(false); setError(''); } }}>서버 내용으로 바꾸기</Button></div></section>}
    <form onSubmit={event => { event.preventDefault(); void save(); }}>
      <section className="worksheet-questions"><h2>질문을 따라 생각하기</h2><ol>{worksheet.document!.questions.map((question, index) => <li key={question.id}><small>AI 질문 {index + 1}</small><Markdown language="">{question.prompt}</Markdown><Link to={'/interpretations/' + worksheet.interpretation_id + '#' + question.section_id}>관련 개념 다시 보기</Link><Label htmlFor={'answer-' + question.id}>내 답변 {index + 1}</Label><Textarea id={'answer-' + question.id} rows={5} maxLength={20000} value={draft.answers[question.id] ?? ''} onChange={e => update({ ...current.current, answers: { ...current.current.answers, [question.id]: e.target.value } })} /></li>)}</ol></section>
      <section className="practice-summary"><h2><Label htmlFor="practice-summary">내 말로 쓴 요약</Label></h2><p>핵심 개념, 새롭게 이해한 점, 더 알아볼 내용을 남겨보세요.</p><Textarea id="practice-summary" rows={8} maxLength={50000} value={draft.summary} onChange={e => update({ ...current.current, summary: e.target.value })} /></section>
      <footer className="practice-save"><div><p aria-live="polite">{draft.pending ? '저장 결과 확인 중 · 작성분 유지' : dirty ? '계정에 저장하지 않은 변경사항' : saved ? `v${saved.revision} · ${timestamp(saved.updated_at)} 저장` : '아직 작성한 내용이 없습니다.'}</p><small>이 브라우저의 임시 글과 별도로, 저장 버튼을 눌러 계정에 보관하세요.</small></div><Button className="primary" disabled={busy || conflict || (!dirty && !draft.pending)}>{busy ? '저장 중…' : draft.pending ? '저장 결과 다시 확인' : '답변·요약 저장'}</Button></footer>
    </form>
    {saved && <MaterialReview kind="practice" id={worksheet.id} revision={saved.revision} disabled={dirty || busy || !!draft.pending || conflict} />}
    <AnimatedDetails summary="내 작성분 미리보기"><PracticeRecordText content={draft} worksheet={worksheet} /></AnimatedDetails>
    {!!versions.length && <AnimatedDetails summary={`저장 이력 · ${versions.length}`}><div className="reference-version-list">{versions.map(v => <Button key={v.revision} onClick={() => void inspectVersion(v.revision)}>v{v.revision} · {timestamp(v.updated_at)}</Button>)}</div></AnimatedDetails>}
    {oldVersion && <section className="practice-comparison"><header className="reference-page-heading"><h2>저장 이력 v{oldVersion.revision}</h2><Button onClick={() => setOldVersion(null)}>닫기</Button></header><PracticeRecordText content={oldVersion} worksheet={worksheet} /></section>}
    <dialog ref={dialog} className="reference-leave-dialog" aria-labelledby="practice-leave-title" onCancel={event => { event.preventDefault(); if (blocker.state === 'blocked') blocker.reset(); }}><h2 id="practice-leave-title">계정에 저장하지 않은 작성분이 있습니다.</h2><p>{warning || '임시 글은 이 브라우저에 남습니다. 다른 기기에서도 보려면 저장해주세요.'}</p><div className="reference-actions"><Button autoFocus onClick={() => { if (blocker.state === 'blocked') blocker.reset(); }}>계속 작성</Button><Button onClick={() => { if (blocker.state === 'blocked') blocker.proceed(); }}>이동하기</Button></div></dialog>
  </main>;
}
export function PracticeRecordText({ content, worksheet }: { content: Content; worksheet: Worksheet }) {
  return <div className="practice-record-text"><p>내가 작성한 학습 기록</p>{worksheet.document!.questions.map((q, index) => <section key={q.id}><h3>내 답변 {index + 1}</h3><Markdown language="">{content.answers[q.id] || '아직 작성하지 않았습니다.'}</Markdown></section>)}<h3>내 말로 쓴 요약</h3><Markdown language="">{content.summary || '아직 작성하지 않았습니다.'}</Markdown></div>;
}
