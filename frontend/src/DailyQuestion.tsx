import { memo, useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { Button } from './components/ui/button';
import { Skeleton } from './components/ui/skeleton';
import { QuestionTextSkeleton } from './QuestionSkeletons';
import type { Daily, Question } from './questionTypes';

export const DailyQuestion = memo(function DailyQuestion() {
  const { data, error: loadError, loading, reload, update } = useResource<Daily>('/questions/daily', { preserveData: true });
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [expansion, setExpansion] = useState({ id: '', expanded: false });
  const recommendation = data?.recommendation, day = data?.day;
  const generating = recommendation?.state === 'queued' || recommendation?.state === 'running';
  useEffect(() => {
    if (!day) return;
    const nextMidnight = Date.parse(day + 'T15:00:00Z');
    const timer = window.setTimeout(reload, Math.max(1000, nextMidnight - Date.now() + 1000));
    window.addEventListener('focus', reload);
    return () => { window.clearTimeout(timer); window.removeEventListener('focus', reload); };
  }, [day, reload]);
  useEffect(() => {
    if (!generating || loading) return;
    const timer = window.setTimeout(reload, 2500);
    return () => window.clearTimeout(timer);
  }, [generating, loading, reload]);
  async function save() {
    if (!data || !recommendation || busy) return;
    setBusy(true); setError('');
    try {
      const saved = await api<Question>('/questions/daily/save', 'POST', { recommendation_id: recommendation.id });
      update({ ...data, recommendation: { ...recommendation, saved_question_id: saved.id } });
      window.dispatchEvent(new Event('questions-changed'));
    } catch (cause) { setError(errorMessage(cause)); reload(); }
    finally { setBusy(false); }
  }
  return <DailyQuestionCard data={data} error={error || loadError} loading={loading} busy={busy} expanded={expansion.id === recommendation?.id && expansion.expanded} onExpand={() => setExpansion({ id: recommendation?.id ?? '', expanded: !(expansion.id === recommendation?.id && expansion.expanded) })} onSave={() => void save()} onReload={reload} />;
});

export function DailyQuestionCard({ data, error, loading, busy, expanded, onExpand, onSave, onReload }: {
  data: Daily | null; error: string; loading: boolean; busy: boolean; expanded: boolean;
  onExpand: () => void; onSave: () => void; onReload: () => void;
}) {
  const recommendation = data?.recommendation;
  const ready = recommendation?.state === 'ready';
  const generating = recommendation?.state === 'queued' || recommendation?.state === 'running';
  const text = useRef<HTMLParagraphElement>(null);
  const [hasMore, setHasMore] = useState(false);
  useEffect(() => {
    const element = text.current;
    if (!element) { setHasMore(false); return; }
    const measure = () => setHasMore(expanded || element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [recommendation?.text, ready, expanded]);
  const sourceLabel = recommendation?.source_kind === 'deep_inside' ? 'Deep Inside 보기' : '포스팅 보기';
  return <section className="daily-question" aria-labelledby="daily-question-heading" aria-busy={loading || busy || generating}>
    <div className="daily-question-heading"><h2 id="daily-question-heading">오늘의 질문</h2><div className="daily-question-date">{data ? <time dateTime={data.day}>{data.day.replaceAll('-', '.')}</time> : <Skeleton aria-hidden="true" />}</div></div>
    <div className="daily-question-feedback" role="status">{error ? <><ErrorNotice error={error} /><Button onClick={onReload}>다시 불러오기</Button></> : <span>{busy ? '질문을 저장하고 있습니다…' : generating ? '본문에서 질문을 만들고 있습니다…' : loading && data ? '추천을 새로 확인하고 있습니다…' : ''}</span>}</div>
    <div className="daily-question-source">{recommendation ? <p title={recommendation.source_title}><span>{recommendation.source_kind === 'feed' ? '구독 포스팅' : 'Deep Inside'}</span><span aria-hidden="true"> · </span>{recommendation.source_title}</p> : !data ? <Skeleton aria-hidden="true" /> : <p>추천할 자료가 아직 없습니다.</p>}</div>
    <div className="daily-question-copy"><div className={`daily-question-content${expanded ? ' is-expanded' : ''}`}>
      {ready ? <p ref={text} className={`daily-question-text${expanded ? '' : ' is-condensed'}`}>{recommendation.text}</p> : (!data || generating) ? <QuestionTextSkeleton label={generating ? '본문에서 질문을 만들고 있습니다' : undefined} /> : <p className="daily-question-status">{recommendation?.error || data.reason || '추천을 불러오지 못했습니다. 다시 시도해주세요.'}</p>}
    </div><Button type="button" variant="ghost" className={`daily-question-expand${!ready || !hasMore ? ' is-placeholder' : ''}`} aria-hidden={!ready || !hasMore || undefined} tabIndex={ready && hasMore ? 0 : -1} disabled={!ready || !hasMore} aria-expanded={expanded} onClick={onExpand}>{expanded ? '질문 접기' : '질문 전체 보기'} <ChevronDown aria-hidden="true" size={16} /></Button></div>
    <div className="daily-question-actions"><div className="daily-question-primary">{data && !recommendation ? <Link className="button" to="/inbox">포스팅 보기</Link> : ready && recommendation.saved_question_id ? <Link className="button" to={'/questions/' + recommendation.saved_question_id}>저장한 질문 열기</Link> : <Button className="primary" disabled={!ready || busy} onClick={onSave}>질문함에 저장</Button>}</div><div className="daily-question-source-action">{data && !recommendation ? <Link className="button" to="/apply">Deep Inside 보기</Link> : recommendation?.source_kind === 'feed' ? <a className="button" href={recommendation.source_url} target="_blank" rel="noreferrer">{sourceLabel}</a> : <Link className="button" to={recommendation ? '/apply' : '/inbox'}>{sourceLabel}</Link>}</div></div>
    <div className="daily-question-evidence-slot">{ready && recommendation.evidence ? <details className="daily-question-source-detail"><summary>질문의 본문 근거 <ChevronDown aria-hidden="true" size={16} /></summary><p>{recommendation.evidence}</p></details> : <div className="daily-question-source-detail" aria-hidden="true"><div className="daily-question-evidence-placeholder">{(!data || generating) && <Skeleton />}</div></div>}</div>
  </section>;
}
