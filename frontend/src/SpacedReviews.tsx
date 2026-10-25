import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Markdown } from './Markdown';
import { LoadingSkeleton } from './LoadingSkeleton';

type Kind = 'interpretation' | 'practice' | 'note';
export type SpacedReview = { id: string; kind: Kind; origin_id: string; source_revision: number; revision: number; due_at: string; due: boolean; state: string; reason: string; snapshot: { title: string; body: string; authorship: 'ai' | 'user' }; responses: { response: string; due_at: string; created_at: string }[] };
export function reviewOrigin(kind: Kind, id: string) { return kind === 'note' ? '/references/' + id : kind === 'interpretation' ? '/interpretations/' + id : '/worksheets/' + id + '/practice'; }
export function AddToReview({ kind, id, revision, disabled = false }: { kind: Kind; id: string; revision: number; disabled?: boolean }) {
  const { userId } = useApp();
  return <Enrollment key={`${userId}:${kind}:${id}:${revision}`} kind={kind} id={id} revision={revision} disabled={disabled} />;
}
function Enrollment({ kind, id, revision, disabled }: { kind: Kind; id: string; revision: number; disabled: boolean }) {
  const { data, error: loadError, reload } = useResource<{ review: SpacedReview | null }>(`/spaced-reviews/source/${kind}/${id}?revision=${revision}`);
  const [saved, setSaved] = useState<SpacedReview | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const sending = useRef(false);
  async function add() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try { setSaved(await api<SpacedReview>('/spaced-reviews', 'POST', { kind, origin_id: id, revision })); reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  const item = saved ?? data?.review;
  return <section className="interpretation-entry"><div><span className="eyebrow">RETURN TO UNDERSTANDING</span><h2>시간을 두고 다시 살펴보세요.</h2><p>복습에 추가하면 다음 날부터 스스로 설명할 수 있는지 확인합니다. 추출·그래프 등록과 별도이며, AI를 호출하지 않습니다.</p></div><div className="interpretation-entry-actions"><ErrorNotice error={error || loadError} />{loadError && <button onClick={reload}>복습 상태 다시 불러오기</button>}{disabled && <p>변경한 내용을 저장하고 최신 자료를 확인해주세요.</p>}{item ? <Link to={'/reviews/material/' + item.id}>등록한 복습 · {timestamp(item.due_at)} →</Link> : <button disabled={disabled || busy || !data} onClick={() => void add()}>{busy ? '추가 중…' : '이 버전 복습에 추가'}</button>}</div></section>;
}
export function SpacedReviewRoute() {
  const { id } = useParams(), { userId } = useApp();
  return <Detail key={userId + ':' + id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const { data, error: loadError, reload } = useResource<SpacedReview>('/spaced-reviews/' + id);
  const [response, setResponse] = useState(''), [requestId, setRequestId] = useState(crypto.randomUUID()), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  const sending = useRef(false);
  async function submit() {
    if (sending.current || !data || !response) return;
    sending.current = true; setBusy(true); setError('');
    try { const result = await api<{ due_at: string }>('/spaced-reviews/' + id + '/responses', 'POST', { request_id: requestId, revision: data.revision, response }); setMessage('응답을 저장했습니다. 다음 복습은 ' + timestamp(result.due_at) + '입니다.'); setResponse(''); setRequestId(crypto.randomUUID()); reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  return <main className="page narrow-page"><div className="breadcrumb"><Link to="/reviews">다시 검토</Link> / 자료 복습</div><ErrorNotice error={loadError || error} />{loadError && <button onClick={reload}>다시 불러오기</button>}{!data && !loadError && <LoadingSkeleton layout="article" label="복습 자료를 불러오는 중…" />}
    {data && <><span className="eyebrow">RECALL. REFLECT. RETURN.</span><h1>{data.snapshot.title}</h1><p>{data.snapshot.authorship === 'ai' ? 'AI 해석' : '내가 작성한 자료'} · v{data.source_revision} · {timestamp(data.due_at)} 예정</p><p>등록 당시 본문입니다. 읽는 것만으로 복습이 완료되지는 않습니다.</p><Link to={reviewOrigin(data.kind, data.origin_id)}>원래 자료 열기 →</Link>{data.reason && <p className="notice">{data.reason} 최신 버전은 원래 화면에서 별도로 복습에 추가해주세요.</p>}
      <article className="interpretation-section"><Markdown language="" images={data.kind === 'note'}>{data.snapshot.body}</Markdown></article>
      <form onSubmit={e => { e.preventDefault(); void submit(); }}><fieldset disabled={busy || !data.due}><legend>자료를 보지 않고 핵심을 설명할 수 있나요?</legend>{[['can_explain', '스스로 설명 가능'], ['needs_review', '다시 확인 필요']].map(([value, label]) => <label key={value}><input type="radio" name="review-response" value={value} checked={response === value} onChange={() => { setResponse(value); setRequestId(crypto.randomUUID()); }} />{label}</label>)}</fieldset><p className="muted">내 판단을 기록합니다. 정답 판정이나 숙달 점수가 아닙니다.</p><button disabled={busy || !data.due || !response}>{busy ? '저장 중…' : '복습 응답 저장'}</button>{!data.due && data.state === 'eligible' && <p>예정 시각에 응답할 수 있습니다.</p>}</form>
      {message && <p role="status">{message}</p>}{data.responses.length > 0 && <section><h2>최근 복습 기록</h2><ul>{data.responses.map((r, i) => <li key={i}>{timestamp(r.created_at)} · {r.response === 'can_explain' ? '스스로 설명 가능' : '다시 확인 필요'} · 다음 {timestamp(r.due_at)}</li>)}</ul></section>}
    </>}
  </main>;
}
