import { BookOpen, CalendarCheck2, ChevronRight, MessageCircle, RotateCcw } from 'lucide-react';
import { ActionCard, ActivityItem, EmptyState, PageHeading, SectionHeading } from './WorkspaceUI';
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
  const resume = data?.resume[0];
  return <main className="page today-page">
    <PageHeading title="오늘의 학습" meta={<time>{data ? new Date(data.day + 'T12:00:00+09:00').toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' }) : '오늘'}</time>} />
    <ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    <div className="today-launch">
      <section className="resume-card" aria-labelledby="resume-heading">
        {!data && !error ? <LoadingSkeleton layout="summary" label="마지막 학습을 불러오는 중…" /> : <><h2 id="resume-heading">{resume?.title ?? '새로운 학습을 시작하세요'}</h2><p>{resume ? '마지막 학습 · ' + timestamp(resume.updated_at) : '관심 있는 자료를 저장하거나 문제집을 골라보세요.'}</p><Link className="button resume-action" to={resume?.href ?? '/library'}>{resume ? '학습 이어서 하기' : '학습 자료 열기'}<ChevronRight size={19} aria-hidden="true" /></Link></>}
      </section>
      <nav className="quick-access" aria-label="학습 바로가기"><ActionCard to="/problem-books" icon={BookOpen} title="문제집" description="문제 선택 · 풀이" accent /><ActionCard to="/reviews" icon={RotateCcw} title="복습" description="예정된 학습 확인" /><ActionCard to="/questions" icon={MessageCircle} title="내 질문" description="기록한 궁금증 보기" /></nav>
    </div>
    {!data && !error && <LoadingSkeleton layout="list" label="학습 활동을 불러오는 중…" />}
    {data && <>
      {data.resume.length > 1 && <section className="learning-section"><SectionHeading title="진행 중인 다른 학습" /><div className="activity-list">{data.resume.slice(1).map(item => <ActivityItem key={item.href} title={item.title} meta={timestamp(item.updated_at)}><Link className="button" to={item.href}>계속하기<ChevronRight size={17} aria-hidden="true" /></Link></ActivityItem>)}</div></section>}
      <div className="today-columns">
        <section className="learning-section"><SectionHeading title="오늘의 복습" action={<Link className="section-more" to="/reviews">전체 보기<ChevronRight size={16} aria-hidden="true" /></Link>} />{data.reviews.length ? <div className="activity-list">{data.reviews.map(item => <ActivityItem key={item.key} title={item.title} meta={<><span className="status-label">{item.in_progress ? '진행 중' : '복습 예정'}</span><time>{timestamp(item.due_at)}</time></>}><Button disabled={!!busy} onClick={() => void review(item)}>{busy === item.key ? '여는 중…' : item.in_progress ? '이어서 하기' : '복습 시작'}</Button></ActivityItem>)}</div> : <EmptyState icon={CalendarCheck2} title="예정된 복습이 없습니다" description="학습한 내용의 복습 일정이 여기에 표시됩니다." />}</section>
        <section className="learning-section"><SectionHeading title="다시 살펴볼 질문" action={<Link className="section-more" to="/questions">전체 보기<ChevronRight size={16} aria-hidden="true" /></Link>} />{data.questions.length ? <div className="activity-list">{data.questions.map(item => <ActivityItem key={item.key} title={item.title} meta="미해결 질문"><Link className="button" to={item.href}>질문 열기</Link><Button disabled={!!busy} onClick={() => void choose(item.key, 'snooze')}>나중에</Button><Button className="text-button" disabled={!!busy} onClick={() => void choose(item.key, 'hide')}>숨기기</Button></ActivityItem>)}</div> : <EmptyState icon={MessageCircle} title="지금 다시 볼 질문이 없습니다" description="떠오르는 질문은 상단의 질문 적기로 남기세요." />}<PolicySettings initial={data.policy} onSaved={reload} /></section>
      </div>
    </>}
    <StudyRecommendations />
  </main>;

}
function PolicySettings({ initial, onSaved }: { initial: Policy; onSaved: () => void }) {
  const [policy, setPolicy] = useState(initial), [error, setError] = useState(''), [busy, setBusy] = useState(false), [message, setMessage] = useState('');
  const fields: { key: keyof Policy; label: string; max: number }[] = [{ key: 'question_age_days', label: '질문 작성 후 추천까지 (일)', max: 365 }, { key: 'resurfacing_days', label: '다시 추천하는 간격 (일)', max: 365 }, { key: 'snooze_days', label: '나중에 보기 기간 (일)', max: 90 }, { key: 'question_limit', label: '한 번에 볼 질문 수', max: 10 }];
  return <details className="learning-policy"><summary>질문 추천 설정</summary><form onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { await api('/study/policy', 'PUT', policy); setMessage('추천 설정을 저장했습니다.'); onSaved(); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }}><p>날짜는 한국 시간 기준입니다. 추천을 숨기거나 미뤄도 질문은 미해결 상태로 남습니다.</p>{fields.map(field => <Label key={field.key}>{field.label}<Input type="number" min={1} max={field.max} required value={policy[field.key]} onChange={e => setPolicy({ ...policy, [field.key]: Number(e.target.value) })} /></Label>)}<ErrorNotice error={error} /><p role="status">{message}</p><Button disabled={busy}>설정 저장</Button></form></details>;
}
