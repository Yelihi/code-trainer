import { AddToReview } from './SpacedReviews';
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Button } from './components/ui/button';

type Kind = 'interpretation' | 'practice';
type Status = { material: { state: string; reason: string }; review: { id: string } | null };
export function MaterialReview({ kind, id, revision, disabled = false }: { kind: Kind; id: string; revision: number; disabled?: boolean }) {
  const { userId } = useApp();
  return <Review key={`${userId}:${kind}:${id}:${revision}`} kind={kind} id={id} revision={revision} disabled={disabled} />;
}
function Review({ kind, id, revision, disabled }: { kind: Kind; id: string; revision: number; disabled: boolean }) {
  const path = `/materials/${kind}/${id}`;
  const { data, error: loadError, reload } = useResource<Status>(path + '?revision=' + revision);
  const [confirmed, setConfirmed] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const sending = useRef(false);
  async function confirm() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try { const result = await api<{ id: string }>(path + '/review', 'POST', { revision }); setConfirmed(result.id); reload(); }
    catch (e) { setError(errorMessage(e)); reload(); }
    finally { sending.current = false; setBusy(false); }
  }
  const reviewId = confirmed || data?.review?.id;
  return <><section className="interpretation-entry"><div><span className="eyebrow">KEEP WHAT YOU UNDERSTAND</span><h2>{kind === 'interpretation' ? '해석을 확인했나요?' : '내 작성분을 검토했나요?'}</h2><p>{kind === 'interpretation' ? '원문과 비교하며 읽은 이 해석을' : '계정에 저장한 답변·요약을'} 확인하고 추출 가능 자료에 추가합니다. AI 추출과 복습 등록은 별도로 진행합니다.</p></div><div className="interpretation-entry-actions">
    <ErrorNotice error={error || loadError} />{loadError && <Button onClick={reload}>확인 상태 다시 불러오기</Button>}
    {disabled && <p role="status">변경한 내용을 먼저 저장하고 검토해주세요.</p>}
    {data?.material.reason && <p className="notice">{data.material.reason}</p>}
    {reviewId ? <><p role="status">이 버전은 검토 완료로 표시했습니다.</p><Link to={'/knowledge/candidates/' + reviewId}>검토한 버전 보기</Link></> : <Button disabled={disabled || busy || !data || data.material.state !== 'eligible'} onClick={() => void confirm()}>{busy ? '확인 중…' : kind === 'interpretation' ? '이 버전 정리 확인' : '이 버전 검토 완료'}</Button>}
    <Link to="/knowledge/candidates">추출 가능 자료 목록</Link>
  </div></section><AddToReview kind={kind} id={id} revision={revision} disabled={disabled || !data || data.material.state !== 'eligible'} /></>;
}
