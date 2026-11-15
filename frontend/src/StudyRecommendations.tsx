import { Waypoints } from 'lucide-react';
import { EmptyState, SectionHeading } from './WorkspaceUI';
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
  const [busy, setBusy] = useState(false), [actionError, setActionError] = useState('');
  const pending = data?.job?.state === 'queued' || data?.job?.state === 'running';
  useEffect(() => { if (!pending) return; const timer = window.setInterval(reload, 2000); return () => clearInterval(timer); }, [pending, reload]);
  async function generate() { setBusy(true); setActionError(''); try { await api('/study/recommendations', 'POST', {}); reload(); } catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(false); } }
  async function choose(key: string, action: string) { setBusy(true); setActionError(''); try { await api('/study/choice', 'POST', { key, action }); reload(); } catch (cause) { setActionError(errorMessage(cause)); } finally { setBusy(false); } }
  return <section className="learning-section"><SectionHeading title="다음 학습 제안" action={<Button disabled={busy || pending} onClick={() => void generate()}>{pending ? '추천 생성 중…' : 'AI 제안 만들기'}</Button>} />
    <details className="recommendation-info"><summary>추천 기준과 AI 사용 안내</summary><p>질문과 최근 학습을 연결합니다. 요청할 때 AI를 사용하며 같은 입력의 결과는 7일 동안 재사용합니다.</p></details>
    <ErrorNotice error={error || actionError || data?.job?.error || ''} />
    {!data && !error && <LoadingSkeleton layout="list" label="저장된 추천을 불러오는 중…" />}
    {pending && !data?.items.length && <LoadingSkeleton layout="list" label="학습 연결을 살펴보는 중…" />}
    {data?.items.map(item => <article className="learning-row" key={item.key}><div><h3>{item.title}</h3><p>{item.reason}</p>{item.uncertain && <p className="notice">기록이 제한적이어서 확인이 필요한 제안입니다.</p>}<details><summary>추천에 사용한 기록</summary><ul>{item.evidence.map(evidence => <li key={evidence.id}><Link className="text-link" to={evidence.href}>{evidence.title}</Link></li>)}</ul></details><div className="reference-actions"><Link className="button primary" to={item.action.href}>시작하기</Link><Button disabled={busy} onClick={() => void choose(item.key, 'snooze')}>나중에 보기</Button><Button disabled={busy} onClick={() => void choose(item.key, 'hide')}>추천 숨기기</Button></div></div></article>)}
    {data && !pending && !data.items.length && <EmptyState icon={Waypoints} title={data.stale ? '학습 기록이 변경됐습니다' : '준비된 제안이 없습니다'} description={data.stale ? '필요할 때 새 제안을 요청하세요.' : '학습과 질문이 쌓이면 다음 활동을 제안받으세요.'} />}
    {data?.generated_at && <small className="muted">추천 생성 · {timestamp(data.generated_at)}</small>}
  </section>;
}
