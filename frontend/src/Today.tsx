import { StudyRecommendations } from './StudyRecommendations';
import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import type { LearningTarget } from './LearningTargets';

type Policy = { question_age_days: number; resurfacing_days: number; snooze_days: number; question_limit: number };
type TodayData = { day: string; resume: (LearningTarget & { updated_at: string })[]; reviews: { key: string; title: string; due_at: string; href: string; exercise_id?: string; in_progress: boolean }[]; review_count: number; questions: { key: string; id: string; title: string; created_at: string; href: string }[]; policy: Policy };
export function StudyLocation() {
  const { pathname, search } = useLocation();
  useEffect(() => { void api('/study/visit', 'POST', { path: (pathname + search).slice(0, 300) }).catch(() => undefined); }, [pathname, search]);
  return null;
}
export function Today() {
  const { data, error, reload } = useResource<TodayData>('/study/today', { preserveData: true });
  const [busy, setBusy] = useState(''), [actionError, setActionError] = useState('');
  const navigate = useNavigate();
  useEffect(() => { window.addEventListener('questions-changed', reload); return () => window.removeEventListener('questions-changed', reload); }, [reload]);
  async function review(item: TodayData['reviews'][number]) {
    setBusy(item.key); setActionError('');
    try { const href = item.href || '/reviews/' + (await api<{ id: string }>(`/exercises/${item.exercise_id}/reviews`, 'POST', {})).id; await navigate(href); }
    catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(''); }
  }
  async function choose(key: string, action: string) {
    setBusy(key); setActionError('');
    try { await api('/study/choice', 'POST', { key, action }); reload(); }
    catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(''); }
  }
  return <main className="page today-page"><header className="learning-intro"><time>{data ? new Date(data.day + 'T12:00:00+09:00').toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' }) : '오늘'}</time><h1>배우던 곳에서,<br />다음 이해로.</h1><p>읽고, 질문하고, 직접 다뤄보세요. 오늘 이어갈 학습을 골라 시작할 수 있습니다.</p><div className="learning-links"><Link to="/library">학습 자료 찾아보기</Link><Link to="/questions">질문 모아보기</Link><Link to="/explore/practice">실습 선택</Link></div></header>
    <div className="today-feedback"><ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}</div>
    {!data && !error && <LoadingSkeleton layout="list" label="이어서 할 학습을 불러오는 중…" />}
    {data && <><section className="learning-section"><header><h2>이어서 하기</h2><Link className="text-link" to="/courses">모든 개념 과정</Link></header>{data.resume.length ? data.resume.map(item => <div className="learning-row" key={item.href}><div><h3>{item.title}</h3><small>마지막 학습 위치 · {timestamp(item.updated_at)}</small></div><Link className="button primary" to={item.href}>이어서 하기</Link></div>) : <div className="learning-row"><div><h3>관심 있는 자료부터 시작하세요.</h3><p>자료를 저장한 뒤 필요한 개념을 읽고, 질문이나 실습을 남길 수 있습니다.</p></div><Link className="button" to="/library">자료 고르기</Link></div>}</section>
    <section className="learning-section"><header><h2>오늘의 복습</h2><Link className="text-link" to="/reviews">전체 복습 {data.review_count > 10 ? `(${data.review_count})` : ''}</Link></header>{data.reviews.map(item => <div className="learning-row" key={item.key}><div><h3>{item.title}</h3><small>{item.in_progress ? '진행 중인 복습' : '복습 예정'} · {timestamp(item.due_at)}</small></div><Button disabled={!!busy} onClick={() => void review(item)}>{busy === item.key ? '여는 중…' : item.in_progress ? '복습 이어서 하기' : '복습 시작'}</Button></div>)}{!data.reviews.length && <p className="muted">지금 예정된 복습이 없습니다. 학습과 질문을 이어가도 좋습니다.</p>}</section>
    <section className="learning-section"><header><h2>다시 살펴볼 질문</h2><Link className="text-link" to="/questions">모든 질문</Link></header>{data.questions.map(item => <div className="learning-row" key={item.key}><div><h3>{item.title}</h3><p>예전에 남긴 질문입니다. 최근 학습과 함께 다시 살펴보세요.</p></div><div className="reference-actions"><Link className="button" to={item.href}>질문 열기</Link><Button disabled={!!busy} onClick={() => void choose(item.key, 'snooze')}>나중에 보기</Button><Button disabled={!!busy} onClick={() => void choose(item.key, 'hide')}>추천 숨기기</Button></div></div>)}{!data.questions.length && <p className="muted">지금 다시 볼 질문은 없습니다. 떠오르는 질문은 상단에서 바로 남기세요.</p>}<PolicySettings initial={data.policy} onSaved={reload} /></section>
    </>}
    <StudyRecommendations />
  </main>;
}
function PolicySettings({ initial, onSaved }: { initial: Policy; onSaved: () => void }) {
  const [policy, setPolicy] = useState(initial), [error, setError] = useState(''), [busy, setBusy] = useState(false), [message, setMessage] = useState('');
  const fields: { key: keyof Policy; label: string; max: number }[] = [{ key: 'question_age_days', label: '질문 작성 후 추천까지 (일)', max: 365 }, { key: 'resurfacing_days', label: '다시 추천하는 간격 (일)', max: 365 }, { key: 'snooze_days', label: '나중에 보기 기간 (일)', max: 90 }, { key: 'question_limit', label: '한 번에 볼 질문 수', max: 10 }];
  return <details className="learning-policy"><summary>질문 추천 설정</summary><form onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { await api('/study/policy', 'PUT', policy); setMessage('추천 설정을 저장했습니다.'); onSaved(); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }}><p>날짜는 한국 시간 기준입니다. 추천을 숨기거나 미뤄도 질문은 미해결 상태로 남습니다.</p>{fields.map(field => <Label key={field.key}>{field.label}<Input type="number" min={1} max={field.max} required value={policy[field.key]} onChange={e => setPolicy({ ...policy, [field.key]: Number(e.target.value) })} /></Label>)}<ErrorNotice error={error} /><p role="status">{message}</p><Button disabled={busy}>설정 저장</Button></form></details>;
}
