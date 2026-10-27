import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorNotice, useResource } from './App';
import { api, errorMessage, timestamp } from './api';
import { Button } from './components/ui/button';

type Schedule = { enabled: boolean; revision: number; next_at: string | null; checked_at: string | null; reason: string; used: number; limit: number; days: number; interval_days: number; output_tokens: number; job: { state: string; error: string; created_at: string } | null };
const reasons: Record<string, string> = { off: '예약 생성 꺼짐', waiting: '첫 확인을 기다립니다.', queued: '자동 생성 요청을 등록했습니다.', pending: '진행 중인 제안이 있어 호출하지 않았습니다.', insufficient: '유효한 근거가 있는 연결이 부족합니다.', unchanged: '마지막 시도 이후 선택된 그래프 근거가 같아 호출하지 않았습니다.', 'ai-unavailable': 'AI 연결이 없어 호출하지 않았습니다.', budget: '최근 30일 자동 호출 한도에 도달했습니다.' };
const states: Record<string, string> = { queued: '대기', running: '생성 중', ready: '완료', failed: '실패', stale: '근거 변경', interrupted: '중단', empty: '새 제안 없음' };
export function InsightSchedule() {
  const { data, error: loadError, reload } = useResource<Schedule>('/insights/schedule');
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const sending = useRef(false);
  async function toggle() {
    if (!data || sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try { await api('/insights/schedule', 'PUT', { revision: data.revision, enabled: !data.enabled }); reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  return <section className="github-card"><span className="eyebrow">DEEP INSIDE</span><h2>연결이 달라지면, 다음 질문을.</h2><p>예약 생성을 켜면 서버가 매주 그래프 근거의 변화를 확인하고 새로운 탐구를 제안합니다. 기본은 꺼짐입니다.</p><ErrorNotice error={error || loadError} />{data && <><p role="status"><strong>{data.enabled ? '예약 생성 켜짐' : '예약 생성 꺼짐'}</strong> · 최근 {data.days}일 자동 호출 {data.used}/{data.limit}회</p><p>확인 간격 {data.interval_days}일 · 요청당 최대 {data.output_tokens.toLocaleString()} 출력 토큰</p><p className="notice">연결한 AI 모델에 따라 비용이 발생합니다. 호출 횟수·출력 토큰 한도는 금액 상한을 보장하지 않습니다. 실패·중단된 시도도 횟수에 포함됩니다.</p><p>다음 확인: {data.next_at ? timestamp(data.next_at) : '예약 없음'}</p><p>{reasons[data.reason] ?? data.reason}{data.checked_at && ' · ' + timestamp(data.checked_at)}</p>{data.job && <p>마지막 자동 작업: {states[data.job.state] ?? data.job.state} · {timestamp(data.job.created_at)}{data.job.error && ' · ' + data.job.error}</p>}<div className="reference-actions"><Button className={data.enabled ? '' : 'primary'} disabled={busy} onClick={() => void toggle()}>{busy ? '설정 중…' : data.enabled ? '예약 생성 끄기' : '예약 생성 켜기'}</Button><Button disabled={busy} onClick={reload}>예약 상태 새로고침</Button><Link to="/apply">Deep Inside 열기</Link></div><p className="github-caption">켜면 첫 확인은 7일 뒤입니다. 서버가 꺼져 있던 기간은 한 번만 확인하며, 바뀌지 않은 근거나 실패한 같은 요청을 자동 재시도하지 않습니다. 끄기 전에 이미 시작한 요청은 완료될 수 있습니다. 수동 생성은 별도 요청입니다.</p></>}{!data && <Button onClick={reload}>예약 상태 불러오기</Button>}</section>;
}
