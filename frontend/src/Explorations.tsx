import { useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useParams } from 'react-router-dom';
import { ErrorNotice, useApp, useResource } from './App';
import { api, errorMessage, timestamp } from './api';
import { InsightGuide, type Insight, type InsightContext } from './DeepInside';
import { Markdown } from './Markdown';
import { LoadingSkeleton } from './LoadingSkeleton';

type Exploration = { id: string; data: Insight; context: InsightContext; state: string; model: string; notes: string; revision: number; created_at: string; updated_at: string };
export function Explorations() {
  const [page, setPage] = useState(1);
  const { data, error, reload } = useResource<{ items: { id: string; title: string; updated_at: string; revision: number }[]; total: number }>('/explorations?page=' + page);
  return <main className="page reference-page"><div className="breadcrumb">응용하기 / 나의 탐구</div><h1>질문을, 나의 경험으로.</h1><p>채택한 가이드에 직접 예상하고 관찰한 내용을 남겨보세요.</p><Link to="/apply">새로운 탐구 제안 보기 →</Link><ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}{!data && !error && <LoadingSkeleton layout="cards" label="탐구 기록을 불러오는 중…" />}{data && <><div className="context-grid">{data.items.map(item => <Link className="context-card" key={item.id} to={'/apply/explorations/' + item.id}><h2>{item.title}</h2><p>{item.revision ? '내 기록 v' + item.revision : '아직 작성한 기록 없음'}</p><small>{timestamp(item.updated_at)}</small></Link>)}</div>{!data.total && <p className="notice">Deep Inside에서 제안을 채택하면 이곳에 보관됩니다.</p>}<div className="reference-actions"><button disabled={page === 1} onClick={() => setPage(page - 1)}>이전</button><span>{page} 페이지</span><button disabled={page * 30 >= data.total} onClick={() => setPage(page + 1)}>다음</button></div></>}</main>;
}
export function ExplorationRoute() {
  const { id } = useParams(), { userId } = useApp();
  const { data, error, reload } = useResource<Exploration>('/explorations/' + id);
  if (!data) return <main className="page"><ErrorNotice error={error} />{error ? <button onClick={reload}>다시 불러오기</button> : <LoadingSkeleton layout="cards" label="채택한 탐구를 불러오는 중…" />}</main>;
  return <ExplorationEditor key={userId + ':' + id} initial={data} />;
}
function ExplorationEditor({ initial }: { initial: Exploration }) {
  const [saved, setSaved] = useState(initial), [notes, setNotes] = useState(initial.notes);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [latest, setLatest] = useState<Exploration | null>(null);
  const sending = useRef(false), dialog = useRef<HTMLDialogElement>(null);
  const dirty = notes !== saved.notes, blocker = useBlocker(dirty || busy);
  useEffect(() => { if (blocker.state === 'blocked') dialog.current?.showModal(); else dialog.current?.close(); }, [blocker.state]);
  useEffect(() => { if (!dirty && !busy) return; const warn = (event: BeforeUnloadEvent) => event.preventDefault(); window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn); }, [dirty, busy]);
  async function save(revision = saved.revision) {
    if (sending.current) return; sending.current = true; setBusy(true); setError('');
    try { const result = await api<Exploration>('/explorations/' + saved.id, 'PUT', { notes, revision }); setSaved(result); setLatest(null); }
    catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  async function compare() { setError(''); try { setLatest(await api<Exploration>('/explorations/' + saved.id)); } catch (e) { setError(errorMessage(e)); } }
  return <main className="page reference-page"><div className="breadcrumb"><Link to="/apply/explorations">나의 탐구</Link> / 채택한 탐구</div><h1>{saved.data.title}</h1><p>채택일 {timestamp(saved.created_at)} · AI 제안 · {saved.model}</p>{saved.state === 'stale' && <p className="notice">채택 당시 근거가 변경되거나 보관됐습니다. 아래 가이드는 당시 기록이며 현재 사실을 보장하지 않습니다.</p>}<InsightGuide item={saved.data} context={saved.context} index={0} /><section className="practice-summary"><h2><label htmlFor="exploration-notes">내 예상·관찰·질문</label></h2><p>직접 설명하거나 실습한 결과를 기록하세요. 저장만으로 지식 그래프나 숙달 상태가 바뀌지 않습니다.</p><textarea id="exploration-notes" rows={12} maxLength={50000} disabled={busy} value={notes} onChange={e => setNotes(e.target.value)} /><ErrorNotice error={error} /><div className="reference-actions"><span role="status">{dirty ? '저장하지 않은 작성분' : '내 기록 v' + saved.revision + ' · ' + timestamp(saved.updated_at)}</span><button className="primary" disabled={!dirty || busy} onClick={() => void save()}>{busy ? '저장 중…' : '내 기록 저장'}</button>{error && <button disabled={busy} onClick={() => void compare()}>최신 저장본과 비교</button>}</div>{latest && <section className="notice"><h3>서버 최신본 v{latest.revision}</h3><Markdown language="">{latest.notes || '작성한 내용이 없습니다.'}</Markdown><p>내 작성분은 위 입력란에 유지됩니다. 비교한 최신본을 덮어써도 된다면 저장해주세요.</p><button disabled={busy} onClick={() => void save(latest.revision)}>내 작성분으로 최신본 갱신</button></section>}</section><dialog ref={dialog} className="reference-leave-dialog" aria-labelledby="exploration-leave-title" onCancel={e => { e.preventDefault(); if (blocker.state === 'blocked') blocker.reset(); }}><h2 id="exploration-leave-title">저장하지 않은 작성분이 있습니다.</h2><p>이동하면 저장하지 않은 내용은 사라집니다.</p><div className="reference-actions"><button autoFocus onClick={() => { if (blocker.state === 'blocked') blocker.reset(); }}>계속 작성</button><button disabled={busy} onClick={() => { if (blocker.state === 'blocked') blocker.proceed(); }}>저장하지 않고 이동</button></div></dialog></main>;
}
