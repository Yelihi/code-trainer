import { BookOpen, CalendarCheck2, ChevronRight, MessageCircle, RotateCcw, Settings2 } from 'lucide-react';
import { ActivityItem, EmptyState, PageHeading, SectionHeading } from './WorkspaceUI';
import { StudyRecommendations } from './StudyRecommendations';
import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Button } from './components/ui/button';
import type { LearningTarget } from './LearningTargets';

import type { QuestionPolicy } from './QuestionPolicySettings';
type TodayData = { day: string; resume: (LearningTarget & { updated_at: string })[]; reviews: { key: string; title: string; due_at: string; href: string; exercise_id?: string; in_progress: boolean }[]; review_count: number; questions: { key: string; id: string; title: string; created_at: string; href: string }[]; policy: QuestionPolicy };
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
    <PageHeading title="오늘의 학습" meta={<time dateTime={data?.day}>{data ? new Date(data.day + 'T12:00:00+09:00').toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' }) : '오늘'}</time>} actions={<nav className="today-shortcuts" aria-label="학습 바로가기"><Link className="button" to="/explore/practice"><BookOpen size={18} aria-hidden="true" />실습</Link><Link className="button" to="/reviews"><RotateCcw size={18} aria-hidden="true" />복습</Link><Link className="button" to="/questions"><MessageCircle size={18} aria-hidden="true" />내 질문</Link></nav>} />
    <ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="summary" label="마지막 학습을 불러오는 중…" />}
    {data && <section className="resume-card" aria-labelledby="resume-heading"><div className="resume-copy"><span className="resume-label">{resume ? '이어서 학습' : '새 학습'}</span><h2 id="resume-heading">{resume?.title ?? '새로운 학습을 시작하세요'}</h2><p>{resume ? '마지막 학습 · ' + timestamp(resume.updated_at) : '관심 있는 자료를 저장하거나 실습을 골라보세요.'}</p></div><Link className="button resume-action" to={resume?.href ?? '/library'}>{resume ? '학습 이어서 하기' : '학습 자료 열기'}<ChevronRight size={19} aria-hidden="true" /></Link></section>}
    {!data && !error && <LoadingSkeleton layout="list" label="학습 활동을 불러오는 중…" />}
    {data && <>
      <div className="today-board">
        <div className="today-main"><section className="learning-section"><SectionHeading title="오늘의 복습" action={<Link className="section-more" to="/reviews">전체 {data.review_count}개<ChevronRight size={16} aria-hidden="true" /></Link>} />{data.reviews.length ? <div className="activity-list">{data.reviews.map(item => <ActivityItem key={item.key} title={item.title} meta={<><span className="status-label">{item.in_progress ? '진행 중' : '복습 예정'}</span><time dateTime={item.due_at}>{timestamp(item.due_at)}</time></>}><Button loading={!!(busy === item.key)} disabled={!!busy} onClick={() => void review(item)}>{busy === item.key ? '여는 중…' : item.in_progress ? '이어서 하기' : '복습 시작'}</Button></ActivityItem>)}</div> : <EmptyState icon={CalendarCheck2} title="예정된 복습이 없습니다"  />}</section>

        </div>
        <aside className="today-side" aria-label="남겨둔 질문"><section className="learning-section"><SectionHeading title="다시 살펴볼 질문" action={<Link className="question-policy-link" to="/settings/questions" aria-label="질문 다시보기 설정"><Settings2 size={18} aria-hidden="true" /></Link>} />{data.questions.length ? <div className="activity-list">{data.questions.map(item => <ActivityItem key={item.key} title={item.title} meta={<time dateTime={item.created_at}>{timestamp(item.created_at)}</time>}><Link className="button" to={item.href}>질문 열기</Link><Button disabled={!!busy} onClick={() => void choose(item.key, 'snooze')}>나중에</Button><Button className="text-button" disabled={!!busy} onClick={() => void choose(item.key, 'hide')}>숨기기</Button></ActivityItem>)}</div> : <EmptyState icon={MessageCircle} title="지금 다시 볼 질문이 없습니다"  />}<footer className="home-question-footer"><Link className="section-more" to="/questions">질문함 열기<ChevronRight size={16} aria-hidden="true" /></Link><span>{data.policy.question_age_days}일 지난 질문부터</span></footer></section></aside>
        {data.resume.length > 1 && <section className="learning-section home-other-learning"><SectionHeading title="진행 중인 다른 학습" /><div className="activity-list">{data.resume.slice(1).map(item => <ActivityItem key={item.href} title={item.title} meta={timestamp(item.updated_at)}><Link className="button" to={item.href}>계속하기<ChevronRight size={17} aria-hidden="true" /></Link></ActivityItem>)}</div></section>}
      </div>
      <StudyRecommendations />
    </>}
  </main>;

}
