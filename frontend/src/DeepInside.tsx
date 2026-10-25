import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ErrorNotice, useApp, useResource } from './App';
import { api, errorMessage, timestamp } from './api';
import { Markdown } from './Markdown';
import { AnimatedDetails } from './AnimatedDetails';
import { LoadingSkeleton } from './LoadingSkeleton';

export type Insight = { title: string; connection_kind: 'known_relation' | 'hypothesis'; why: string; concept_ids: string[]; assertion_ids: string[]; evidence_ids: string[]; question: string; reading_guide: string; practice_guide: string; expected_output: string };
type Source = { id: string; kind: string; origin_id: string; version: number; title: string; authorship: string; review_id: string | null };
export type InsightContext = { concepts: { id: string; pref_label: string; definition: string; scope: string }[]; assertions: { id: string; subject: string; object: string; kind: string; text: string; scope: string }[]; sources: Source[]; evidence: { id: string; source_id: string; concept_id: string | null; assertion_id: string | null; basis: string; quote: string }[] };
export type Bundle = { choices: Record<string, { action: 'adopt' | 'skip'; id?: string }>; id: string; state: 'current' | 'stale'; data: { suggestions: Insight[] }; context: InsightContext; model: string; created_at: string; expires_at: string };
type Status = { bundle: Bundle | null; job: { id: string; state: string; error: string } | null; eligible: boolean; reason: string };
const states: Record<string, string> = { queued: '생성 대기', running: '연결을 살펴보는 중', ready: '제안 준비됨', failed: '생성 실패', stale: '근거 변경됨', interrupted: '생성 중단됨', empty: '새로운 연결 없음' };
export function DeepInside() {
  const { userId } = useApp();
  return <Inside key={userId} storageKey={'deep-inside-request:' + userId} />;
}
function Inside({ storageKey }: { storageKey: string }) {
  const navigate = useNavigate();
  const { data, error: loadError, reload } = useResource<Status>('/insights');
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [requestId, setRequestId] = useState(() => { try { return localStorage.getItem(storageKey) || crypto.randomUUID(); } catch { return crypto.randomUUID(); } });
  const sending = useRef(false);
  const pending = data?.job?.state === 'queued' || data?.job?.state === 'running';
  useEffect(() => { if (!pending) return; const timer = setTimeout(reload, 1500); return () => clearTimeout(timer); }, [pending, data, reload]);
  async function generate() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try { localStorage.setItem(storageKey, requestId); await api('/insights', 'POST', { request_id: requestId }); setRequestId(crypto.randomUUID()); try { localStorage.removeItem(storageKey); } catch { /* Server receipt already protects successful request. */ } reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  async function choose(index: number, action: 'adopt' | 'skip') {
    if (sending.current || !data?.bundle) return;
    sending.current = true; setBusy(true); setError('');
    try { const result = await api<{ id?: string }>('/insights/' + data.bundle.id + '/choice', 'POST', { index, action }); if (result.id) navigate('/apply/explorations/' + result.id); else reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  return <main className="page reference-page insight-page"><div className="breadcrumb">응용하기 / Deep Inside</div><header className="reference-page-heading"><div><span className="eyebrow">CONNECTIONS BECOME QUESTIONS</span><h1>연결에서, 다음 질문으로.</h1><p>쌓아둔 개념을 다른 각도에서 살펴보세요.<br />설명하고, 비교하고, 직접 확인할 작은 탐구를 제안합니다.</p></div><Link className="text-link" to="/knowledge">나의 지식 그래프 ↗</Link></header>
    <section className="insight-request"><div><h2>생각을 이어갈 실마리</h2><Link to="/apply/explorations">채택한 나의 탐구 →</Link><p>유효한 근거가 있는 연결 일부를 AI가 살펴봅니다. 제안은 답이나 검증된 사실이 아니며, 지식 그래프에 자동 등록되지 않습니다.</p></div><button className="primary" disabled={busy || pending || !data?.eligible} onClick={() => void generate()}>{busy || pending ? '제안을 준비하는 중…' : data?.bundle ? '새 묶음 제안 받기' : '탐구 제안 받기'}</button></section>
    <p className="muted">현재 묶음은 생성 후30일 임시 보관하며 새 묶음으로 교체됩니다. 요청당 최대4,000 출력 토큰이며 실제 비용은 연결한 모델에 따라 다릅니다.</p><ErrorNotice error={error || loadError} />{loadError && <button onClick={reload}>제안 다시 불러오기</button>}{!data && !loadError && <LoadingSkeleton layout="cards" label="탐구 제안을 불러오는 중…" />}
    {data?.reason && <section className="empty-state"><h2>연결의 근거부터 쌓아보세요.</h2><p>{data.reason}</p><Link to="/knowledge/candidates">검토한 자료에서 개념 찾기 →</Link></section>}
    {data?.job && <div role="status"><p>{states[data.job.state] ?? data.job.state}</p><ErrorNotice error={data.job.error} /></div>}
    {data?.bundle && <><div className="section-heading"><h2>이번에 탐구할 방향</h2><small>{timestamp(data.bundle.created_at)} · {data.bundle.model}</small></div>{data.bundle.state === 'stale' && <p className="notice">이 묶음의 근거가 변경되거나 보관됐습니다. 원래 자료를 다시 확인하고 새 제안을 받아주세요.</p>}
      <div className="insight-list">{data.bundle.data.suggestions.map((item, index) => data.bundle!.choices[String(index)]?.action === 'skip' ? <p key={index} className="muted">건너뛴 연결 · 30일간 같은 연결의 제안을 제외합니다.</p> : <div key={data.bundle!.id + ':' + index}><InsightGuide item={item} context={data.bundle!.context} index={index} /><div className="reference-actions">{data.bundle!.choices[String(index)]?.action === 'adopt' ? <Link to={'/apply/explorations/' + data.bundle!.choices[String(index)].id}>채택한 탐구 열기 →</Link> : <><button className="primary" disabled={busy || data.bundle!.state !== 'current'} onClick={() => void choose(index, 'adopt')}>이 제안 채택하기</button><button disabled={busy || data.bundle!.state !== 'current'} onClick={() => void choose(index, 'skip')}>건너뛰기</button></>}</div></div>)}</div><p className="muted">{timestamp(data.bundle.expires_at)}까지 임시 보관 · 선택된 근거 일부에 기반한 AI 제안입니다.</p>
    </>}
  </main>;
}
export function InsightGuide({ item, context, index }: { item: Insight; context: InsightContext; index: number }) {
  const names = item.concept_ids.map(id => context.concepts.find(c => c.id === id)?.pref_label).filter(Boolean);
  return <article className="insight-guide"><header><span className="eyebrow">{String(index + 1).padStart(2, '0')} · {item.connection_kind === 'hypothesis' ? '직접 검증할 가설' : '등록한 관계에서 출발'}</span><h2>{item.title}</h2><p className="muted">{names.join(' · ')}</p></header><Markdown language="">{item.why}</Markdown><section className="insight-question"><h3>내가 답할 질문</h3><Markdown language="">{item.question}</Markdown></section><div className="insight-steps"><section><h3>01 다시 찾아볼 근거</h3><Markdown language="">{item.reading_guide}</Markdown></section><section><h3>02 직접 해볼 작은 실습</h3><Markdown language="">{item.practice_guide}</Markdown></section><section><h3>03 남길 결과물</h3><Markdown language="">{item.expected_output}</Markdown></section></div>
    <AnimatedDetails summary="어떤 연결과 근거에서 나왔나요?"><h3>사용한 관계</h3>{item.assertion_ids.map(id => <p key={id}>{context.assertions.find(a => a.id === id)?.text}</p>)}<h3>인용한 근거</h3>{item.evidence_ids.map(id => { const proof = context.evidence.find(e => e.id === id), source = context.sources.find(s => s.id === proof?.source_id); if (!proof || !source) return null; return <div className="insight-evidence" key={id}><strong>{source.title} · v{source.version}</strong><p className="muted">{source.authorship === 'ai' ? 'AI가 작성한 자료' : '사용자가 작성·정리한 자료'} · {proof.basis === 'source' ? '출처에서 정리한 근거' : '해석·설명'}</p><blockquote>{proof.quote}</blockquote><Link to={source.review_id ? '/knowledge/candidates/' + source.review_id : source.kind === 'note' ? '/references/' + source.origin_id : '/knowledge'}>근거 자료 확인 →</Link></div>; })}</AnimatedDetails>
  </article>;
}
