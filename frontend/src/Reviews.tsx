import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, assistanceLabels, errorMessage, timestamp, type Assistance } from './api';
import { ErrorNotice, useResource } from './App';

type ReviewItem = { exercise_id: string; title: string; context_title: string; kind: string; assistance: Assistance; due_at: string; due: boolean; active_review_id: string | null };
export function Reviews() {
  const { data, error, reload } = useResource<{ items: ReviewItem[]; due_count: number }>('/me/reviews');
  const [busy, setBusy] = useState('');
  const [actionError, setActionError] = useState('');
  const navigate = useNavigate();
  async function start(item: ReviewItem) {
    setBusy(item.exercise_id); setActionError('');
    try {
      const value = item.active_review_id ? { id: item.active_review_id } : await api<{ id: string }>(`/exercises/${item.exercise_id}/reviews`, 'POST', {});
      await navigate(`/reviews/${value.id}`);
    } catch (error) { setActionError(errorMessage(error)); } finally { setBusy(''); }
  }
  return <main className="page narrow-page"><div className="breadcrumb">Workspace / 복습</div><h1>오늘의 복습</h1>
    <p className="page-intro">이전 풀이를 보지 않고 다시 해결해보세요. 기존 코드와 진도는 그대로 보관됩니다.</p>
    <p className="muted">첫 통과 다음 날부터 시작합니다. 도움 없이 통과하면 3일·7일·14일 뒤, 실패하거나 도움을 참고하면 다음 날 다시 연습합니다. 앱 밖에서 받은 도움은 기록하지 않습니다.</p>
    <ErrorNotice error={error || actionError} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <p role="status">복습 목록을 불러오는 중…</p>}
    {data && <><h2>복습할 문제 {data.due_count}개</h2>{!data.items.length && <div className="empty-state">문제를 통과하면 다음 날 복습 목록에 나타납니다.</div>}
      {data.due_count === 0 && data.items.length > 0 && <p className="notice">오늘 예정된 복습을 마쳤습니다.</p>}
      <div className="list">{data.items.map(item => <article className="list-row review-row" key={item.exercise_id}><div><small>{item.context_title} · {item.kind}</small><h3>{item.title}</h3><p>{assistanceLabels[item.assistance]} · {timestamp(item.due_at)} 예정</p></div>
        <button disabled={!!busy || (!item.due && !item.active_review_id)} onClick={() => void start(item)}>{busy === item.exercise_id ? '준비 중…' : item.active_review_id ? '복습 이어하기' : item.due ? '다시 풀기' : '복습 예정'}</button></article>)}</div></>}
  </main>;
}

type Usage = { items: { generation_id: string | null; operation: string; model: string; context_title: string | null; unit_id: string | null; calls: number; repair_calls: number; input_tokens: number; output_tokens: number; unknown_usage_calls: number; failed_calls: number }[]; totals: { calls: number; input_tokens: number; output_tokens: number; unknown_usage_calls: number } };
export function UsagePanel() {
  const { data, error, reload } = useResource<Usage>('/me/ai-usage');
  return <section className="usage-panel"><h2>AI 사용량</h2><button onClick={reload}>사용량 새로고침</button><p className="muted">이 기능 적용 이후의 제공자 응답 기준입니다. 토큰은 비용 확정액이 아니며, 사용량을 받지 못한 호출은 별도로 표시합니다.</p>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <p role="status">사용량을 불러오는 중…</p>}
    {data && <><p>총 {data.totals.calls}회 · 입력 {data.totals.input_tokens.toLocaleString()} / 출력 {data.totals.output_tokens.toLocaleString()} 토큰 · 사용량 미확인 {data.totals.unknown_usage_calls}회</p>
      <details><summary>작업·단원별 사용량</summary><div className="list">{data.items.length === 0 && <p>아직 기록된 AI 호출이 없습니다.</p>}{data.items.map((row, index) => <div className="list-row" key={index}><div><strong>{row.context_title ?? (row.operation === 'LearningSummary' ? '학습 정리' : '자료 분석 · 삭제된 자료')}</strong><p>{row.unit_id ?? '과정 전체'} · {({ CurriculumDraft: '자료 분석', LearningSummary: '학습 정리', FixStarterRepair: 'FIX 수정', ExerciseCodeRepair: '코드 수정' } as Record<string,string>)[row.operation] ?? row.operation} · {row.model}</p><small>{row.calls}회 호출 / 수정 {row.repair_calls}회 / 실패 {row.failed_calls}회 / 사용량 미확인 {row.unknown_usage_calls}회</small></div><span>입력 {row.input_tokens.toLocaleString()}<br />출력 {row.output_tokens.toLocaleString()}</span></div>)}</div></details></>}
  </section>;
}

type Status = { available: boolean; stale: boolean; warnings: string[]; collected_at?: string; backup_at?: string; internal_free_gib?: number; external_free_gib?: number; certificates?: { name: string; days_left: number | null; expires_at: string | null }[]; checks?: { full_reboot: string; off_device_recovery: string } };
export function Operations() {
  const { data, error, reload } = useResource<Status>('/admin/operations');
  return <main className="page narrow-page"><div className="breadcrumb">Workspace / 관리자</div><h1>운영 상태</h1><p>Mac에서 5분마다 수집합니다. 오래된 정보는 정상 상태로 표시하지 않습니다.</p><button onClick={reload}>다시 불러오기</button>
    <ErrorNotice error={error} />{!data && !error && <p role="status">운영 상태를 불러오는 중…</p>}
    {data && <>{data.warnings.map(w => <p key={w} className="notice" role="status">{w}</p>)}{data.available && <><p className="muted">수집 시각 {timestamp(data.collected_at!)}</p><dl className="operation-facts"><div><dt>내장 SSD 여유</dt><dd>{data.internal_free_gib} GiB</dd></div><div><dt>외장 SSD 여유</dt><dd>{data.external_free_gib} GiB</dd></div><div><dt>마지막 백업 성공</dt><dd>{data.backup_at ? timestamp(data.backup_at) : '확인 필요'}</dd></div>{data.certificates?.map(cert => <div key={cert.name}><dt>{cert.name} 인증서</dt><dd>{cert.days_left === null ? '확인 필요' : `${cert.days_left}일 남음`}{cert.expires_at && <small> · {timestamp(cert.expires_at)} 만료</small>}</dd></div>)}<div><dt>Mac 전체 재부팅 복구</dt><dd>{data.checks?.full_reboot ?? '미확인'}</dd></div><div><dt>장치 밖 복구 사본</dt><dd>{data.checks?.off_device_recovery ?? '미확인'}</dd></div></dl><p className="muted">인증서는 자동 갱신되지 않습니다. 내장 디스크 10GiB 미만·백업 36시간 경과·인증서 14일 이내 만료 시 안내합니다.</p></>}</>}
  </main>;
}
