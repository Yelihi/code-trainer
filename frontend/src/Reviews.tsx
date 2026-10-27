import { reviewCurve } from './reviewCurve';
import type { SpacedReview } from './SpacedReviews';
import { Link } from 'react-router-dom';
import { LoadingSkeleton } from './LoadingSkeleton';
import { AnimatedDetails } from './AnimatedDetails';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, assistanceLabels, errorMessage, timestamp, type Assistance } from './api';
import { ErrorNotice, useResource } from './App';
import { Button } from './components/ui/button';

type ReviewItem = { exercise_id: string; title: string; context_title: string; kind: string; assistance: Assistance; streak: number; due_at: string; due: boolean; active_review_id: string | null };
export function Reviews() {
  const { data, error, reload } = useResource<{ items: ReviewItem[]; due_count: number }>('/me/reviews');
  const { data: materials, error: materialError, reload: reloadMaterials } = useResource<{ items: SpacedReview[]; due_count: number }>('/spaced-reviews');
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
  return <main className="page narrow-page reviews-page"><div className="breadcrumb">탐구하기 / 다시 검토</div><h1>이해를 다시 꺼내보는 시간.</h1>
    <p className="page-intro">코드와 자료의 복습 기한을 한곳에서 살펴보세요.</p>
    {data && materials && <ReviewCurves codes={data.items} materials={materials.items} />}
    <section className="review-section"><h2>자료 복습 {materials?.due_count ?? 0}개</h2><p>해석·내 답변·노트에서 직접 복습에 추가할 수 있습니다. 스스로 설명 가능하면 3·7·14일 뒤, 다시 확인이 필요하면 다음 날 살펴봅니다.</p><ErrorNotice error={materialError} />{materialError && <Button onClick={reloadMaterials}>자료 일정 다시 불러오기</Button>}{!materials && !materialError && <LoadingSkeleton layout="list" label="자료 복습을 불러오는 중…" />}
      {materials && <>{!materials.items.length && <div className="empty-state">복습에 추가한 자료가 없습니다.<Link className="button" to="/explore">해석 살펴보기</Link></div>}{materials.items.some(x => x.due) && <h3>기한이 된 자료 · 미완료</h3>}<div className="list">{materials.items.filter(x => x.due).map(item => <MaterialReviewRow key={item.id} item={item} />)}</div>{materials.items.some(x => !x.due) && <h3>예정 · 다시 확인할 자료</h3>}<div className="list">{materials.items.filter(x => !x.due).map(item => <MaterialReviewRow key={item.id} item={item} />)}</div></>}
    </section><section className="review-section"><h2>코드 복습</h2>
    <p className="page-intro">이전 풀이를 보지 않고 다시 해결해보세요. 기존 코드와 진도는 그대로 보관됩니다.</p>
    <p className="muted">첫 통과 다음 날부터 시작합니다. 도움 없이 통과하면 3일·7일·14일 뒤, 실패하거나 도움을 참고하면 다음 날 다시 연습합니다. 앱 밖에서 받은 도움은 기록하지 않습니다.</p>
    <ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="list" label="복습 목록을 불러오는 중…" />}
    {data && <><h2>복습할 문제 {data.due_count}개</h2>{!data.items.length && <div className="empty-state">문제를 통과하면 다음 날 복습 목록에 나타납니다.</div>}
      {data.due_count === 0 && data.items.length > 0 && <p className="notice">오늘 예정된 복습을 마쳤습니다.</p>}
      <div className="list">{data.items.map(item => <article className="list-row review-row" key={item.exercise_id}><div><small>{item.context_title} · {item.kind}</small><h3>{item.title}</h3><p>{assistanceLabels[item.assistance]} · {timestamp(item.due_at)} 예정</p></div>
        <Button disabled={!!busy || (!item.due && !item.active_review_id)} onClick={() => void start(item)}>{busy === item.exercise_id ? '준비 중…' : item.active_review_id ? '복습 이어하기' : item.due ? '다시 풀기' : '복습 예정'}</Button></article>)}</div></>}
    </section>
  </main>;
}

function MaterialReviewRow({ item }: { item: SpacedReview }) {
  return <article className="list-row review-row"><div><small>{item.kind === 'note' ? '직접 쓴 노트' : item.kind === 'interpretation' ? 'AI 해석' : '내 답변·요약'} · v{item.source_revision}</small><h3>{item.snapshot.title}</h3><p>{item.state !== 'eligible' ? item.reason : (item.due ? '기한 경과 · ' : '예정 · ') + timestamp(item.due_at)}</p></div><Link className="button" to={'/reviews/material/' + item.id}>{item.due ? '다시 검토' : '자료·일정 보기'}</Link></article>;
}
type CurveEntry = { id: string; kind: 'material' | 'code'; title: string; dueAt: string; streak: number; due: boolean; requirement: string };
function ReviewCurves({ codes, materials }: { codes: ReviewItem[]; materials: SpacedReview[] }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const now = new Date();
  const entries: CurveEntry[] = [
    ...materials.filter(item => item.state === 'eligible').map(item => ({ id: 'material:' + item.id, kind: 'material' as const, title: item.snapshot.title, dueAt: item.due_at, streak: item.streak, due: item.due, requirement: item.due ? '원문을 보지 않고 핵심을 설명한 뒤 스스로 설명 가능한지 기록하세요.' : '예정일이 되면 원문 없이 핵심을 설명하고 복습 결과를 기록하세요.' })),
    ...codes.map(item => ({ id: 'code:' + item.exercise_id, kind: 'code' as const, title: item.title, dueAt: item.due_at, streak: item.streak, due: item.due, requirement: item.active_review_id ? '진행 중인 복습 문제를 이어서 풀어보세요.' : item.due ? '이전 풀이를 보지 않고 문제를 다시 풀고 테스트를 통과하세요.' : '예정일이 되면 이전 풀이 없이 문제를 다시 풀어보세요.' })),
  ].sort((a, b) => Date.parse(a.dueAt) - Date.parse(b.dueAt));
  const active = entries.find(item => item.id === activeId);
  return <section className="review-curves" aria-labelledby="review-curves-title">
    <div className="review-curves-heading"><div><h2 id="review-curves-title">복습 곡선</h2><p>각 항목의 복습 간격과 예정일을 그렸습니다. 실제 기억률을 측정한 값은 아닙니다.</p></div><span>{entries.length}개 항목</span></div>
    {entries.length ? <>
      <div className="review-curve-axis" aria-hidden="true"><span>오늘</span><span>3일</span><span>7일</span><span>14일</span></div>
      <div className="review-curve-list" role="group" aria-label="복습 항목별 곡선">{entries.map(item => {
        const curve = reviewCurve(item.dueAt, item.streak, now);
        return <button key={item.id} type="button" className="review-curve-row" data-kind={item.kind} aria-pressed={activeId === item.id} aria-label={`${item.kind === 'material' ? '자료' : '코드'} ${item.title}, ${timestamp(item.dueAt)} 복습 예정`} onMouseEnter={() => setActiveId(item.id)} onFocus={() => setActiveId(item.id)} onClick={() => setActiveId(item.id)}>
          <span className="review-curve-name"><small>{item.kind === 'material' ? '자료 복습' : '코드 복습'}</small><strong>{item.title}</strong></span>
          <svg viewBox="0 0 560 52" preserveAspectRatio="none" aria-hidden="true"><path d={curve.path} /><line x1={curve.dueX} x2={curve.dueX} y1="4" y2="48" /><circle cx={curve.dueX} cy={curve.dueY} r="4" /></svg>
        </button>;
      })}</div>
      <div className="review-curve-detail" aria-live="polite">{active ? <><strong>{active.title}</strong><span>{active.due ? '복습 필요' : '복습 예정'} · {timestamp(active.dueAt)}</span><p>{active.requirement}</p></> : <p>곡선에 마우스를 올리거나 Tab 키로 선택하면 복습 요구사항을 볼 수 있습니다.</p>}</div>
    </> : <p className="review-curve-empty">아직 예정된 복습이 없습니다. 자료를 복습에 추가하거나 코드 문제를 통과하면 이곳에 항목별 곡선이 나타납니다.</p>}
  </section>;
}

type Usage = { items: { generation_id: string | null; operation: string; model: string; context_title: string | null; unit_id: string | null; calls: number; repair_calls: number; input_tokens: number; output_tokens: number; unknown_usage_calls: number; failed_calls: number }[]; totals: { calls: number; input_tokens: number; output_tokens: number; unknown_usage_calls: number } };
export function UsagePanel() {
  const { data, error, reload } = useResource<Usage>('/me/ai-usage');
  return <section className="usage-panel"><h2>AI 사용량</h2><Button onClick={reload}>사용량 새로고침</Button><p className="muted">이 기능 적용 이후의 제공자 응답 기준입니다. 토큰은 비용 확정액이 아니며, 사용량을 받지 못한 호출은 별도로 표시합니다.</p>
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="summary" label="사용량을 불러오는 중…" />}
    {data && <><p>총 {data.totals.calls}회 · 입력 {data.totals.input_tokens.toLocaleString()} / 출력 {data.totals.output_tokens.toLocaleString()} 토큰 · 사용량 미확인 {data.totals.unknown_usage_calls}회</p>
      <AnimatedDetails summary="작업·단원별 사용량"><div className="list">{data.items.length === 0 && <p>아직 기록된 AI 호출이 없습니다.</p>}{data.items.map((row, index) => <div className="list-row" key={index}><div><strong>{row.context_title ?? (row.operation === 'LearningSummary' ? '학습 정리' : row.operation === 'ExplanationFeedback' ? '기초 구현 · 설명 검토' : '자료 분석 · 삭제된 자료')}</strong><p>{row.unit_id ?? '과정 전체'} · {({ CurriculumDraft: '자료 분석', LearningSummary: '학습 정리', ExplanationFeedback: '설명 피드백', FixStarterRepair: 'FIX 수정', ExerciseCodeRepair: '코드 수정' } as Record<string,string>)[row.operation] ?? row.operation} · {row.model}</p><small>{row.calls}회 호출 / 수정 {row.repair_calls}회 / 실패 {row.failed_calls}회 / 사용량 미확인 {row.unknown_usage_calls}회</small></div><span>입력 {row.input_tokens.toLocaleString()}<br />출력 {row.output_tokens.toLocaleString()}</span></div>)}</div></AnimatedDetails></>}
  </section>;
}

type Status = { services?: { api?: boolean; runner?: boolean }; available: boolean; stale: boolean; warnings: string[]; collected_at?: string; backup_at?: string; internal_free_gib?: number; external_free_gib?: number; certificates?: { name: string; days_left: number | null; expires_at: string | null }[]; checks?: { full_reboot: string; off_device_recovery: string } };
export function Operations() {
  const { data, error, reload } = useResource<Status>('/admin/operations');
  return <main className="page narrow-page"><div className="breadcrumb">Workspace / 관리자</div><h1>운영 상태</h1><p>Mac에서 5분마다 수집합니다. 오래된 정보는 정상 상태로 표시하지 않습니다.</p><Button onClick={reload}>다시 불러오기</Button>
    <ErrorNotice error={error} />{!data && !error && <LoadingSkeleton layout="cards" label="운영 상태를 불러오는 중…" />}
    {data && <>{data.warnings.map(w => <p key={w} className="notice" role="status">{w}</p>)}{data.available && <><p className="muted">수집 시각 {timestamp(data.collected_at!)}</p><dl className="operation-facts">{Object.entries({ api: 'API 응답', runner: '코드 실행기 연결' }).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{data.stale ? '정보 오래됨' : data.services?.[key as 'api' | 'runner'] === true ? '정상' : data.services?.[key as 'api' | 'runner'] === false ? '연결 실패' : '미확인'}</dd></div>)}<div><dt>내장 SSD 여유</dt><dd>{data.internal_free_gib} GiB</dd></div><div><dt>외장 SSD 여유</dt><dd>{data.external_free_gib} GiB</dd></div><div><dt>마지막 백업 성공</dt><dd>{data.backup_at ? timestamp(data.backup_at) : '확인 필요'}</dd></div>{data.certificates?.map(cert => <div key={cert.name}><dt>{cert.name} 인증서</dt><dd>{cert.days_left === null ? '확인 필요' : `${cert.days_left}일 남음`}{cert.expires_at && <small> · {timestamp(cert.expires_at)} 만료</small>}</dd></div>)}<div><dt>Mac 전체 재부팅 복구</dt><dd>{data.checks?.full_reboot ?? '미확인'}</dd></div><div><dt>장치 밖 복구 사본</dt><dd>{data.checks?.off_device_recovery ?? '미확인'}</dd></div></dl><p className="muted">인증서는 자동 갱신되지 않습니다. 내장 디스크 10GiB 미만·백업 36시간 경과·인증서 14일 이내 만료 시 안내합니다.</p></>}</>}
  </main>;
}
