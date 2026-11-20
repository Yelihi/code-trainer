import { LoadingState } from './LoadingState';
import { ArrowRight, CircleAlert, Compass, History, MousePointer2 } from 'lucide-react';
import { SectionHeading } from './WorkspaceUI';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useResource } from './App';
import { Button } from './components/ui/button';
import { LoadingSkeleton } from './LoadingSkeleton';

type Item = { key: string; title: string; reason: string; uncertain: boolean; evidence: { id: string; title: string; href: string }[]; action: { href: string; title: string } };
type Result = { items: Item[]; job: { state: string; error: string } | null; stale: boolean; generated_at: string | null };
export function StudyRecommendations() {
  const { data, error, reload } = useResource<Result>('/study/recommendations', { preserveData: true });
  const [busy, setBusy] = useState<'generate' | 'choice' | ''>(''), [actionError, setActionError] = useState('');
  const pending = data?.job?.state === 'queued' || data?.job?.state === 'running';
  useEffect(() => { if (!pending) return; const timer = window.setInterval(reload, 2000); return () => clearInterval(timer); }, [pending, reload]);
  async function generate() { setBusy('generate'); setActionError(''); try { await api('/study/recommendations', 'POST', {}); reload(); } catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(''); } }
  async function choose(key: string, action: string) { setBusy('choice'); setActionError(''); try { await api('/study/choice', 'POST', { key, action }); reload(); } catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(''); } }
  const generating = busy === 'generate' || pending;
  const hasItems = !!data?.items.length;
  const failure = error || actionError || data?.job?.error || '';
  const generateButton = <Button variant="default" loading={generating} disabled={!!busy || pending} onClick={() => void generate()}>{generating ? '제안 만드는 중' : 'AI 제안 만들기'}<ArrowRight aria-hidden="true" /></Button>;
  return <section className="learning-section home-recommendations">
    <SectionHeading title="다음 학습 제안" action={hasItems ? generateButton : undefined} />
    {!data && !error && <LoadingSkeleton layout="list" label="저장된 추천을 불러오는 중…" />}
    {generating && <div className="recommendation-loading"><LoadingState compact status="제안 생성 중" title="다음에 배울 내용을 찾고 있어요" description="질문과 최근 학습의 연결을 살펴보고 있어요." />{!hasItems&&generateButton}</div>}
    {!generating && !hasItems && (data || error) && <div className="recommendation-state">
      <div className="recommendation-state-icon" aria-hidden="true">{failure ? <CircleAlert /> : <Compass />}</div>
      <div className="recommendation-state-copy">
        <h3>{generating ? '다음에 배울 내용을 찾고 있어요' : failure ? '학습 제안을 불러오지 못했어요' : data?.stale ? '새 기록에서 다음 학습을 찾아보세요' : '남겨둔 질문, 다음 학습으로 이어가세요'}</h3>
        {failure ? <ErrorNotice error={failure} /> : <p role={generating ? 'status' : undefined}>{generating ? '질문과 최근 학습의 연결을 살펴보고 있어요.' : '질문과 최근 학습을 바탕으로 AI가 다음 할 일을 제안해요.'}</p>}
      </div>
      <div className="recommendation-state-action">{error ? <Button onClick={reload}>다시 불러오기</Button> : generateButton}</div>
    </div>}
    {hasItems && <ErrorNotice error={failure} />}
    {data?.items.map(item => <article className="learning-row" key={item.key}><div><h3>{item.title}</h3><p>{item.reason}</p>{item.uncertain && <p className="notice">기록이 제한적이어서 확인이 필요한 제안입니다.</p>}<div className="recommendation-evidence"><span>연결 기록</span><ul>{item.evidence.map(evidence => <li key={evidence.id}><Link className="text-link" to={evidence.href}>{evidence.title}</Link></li>)}</ul></div><div className="reference-actions"><Link className="button primary" to={item.action.href}>시작하기</Link><Button disabled={!!busy} onClick={() => void choose(item.key, 'snooze')}>나중에 보기</Button><Button disabled={!!busy} onClick={() => void choose(item.key, 'hide')}>추천 숨기기</Button></div></div></article>)}
    {(data || error) && <div className="recommendation-meta">
      <span><MousePointer2 aria-hidden="true" />버튼을 누를 때만 AI 사용</span>
      <span><History aria-hidden="true" />같은 기록은 7일간 제안 재사용</span>
      {data?.generated_at && <span className="recommendation-updated">생성 · {timestamp(data.generated_at)}</span>}
    </div>}
  </section>;
}
