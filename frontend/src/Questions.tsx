import { useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useResource } from './App';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import './questions.css';

type LinkItem = { resource_id: string; excerpt: string };
type Question = { id: string; text: string; context: string; status: 'open' | 'done'; links: LinkItem[]; note_id: string | null; revision: number; updated_at: string };
type Guide = { id: string; state: string; error: string; question_revision: number; result: { title: string; reading: string; checks: string[]; practice: string; expected_output: string; source_ids: string[] } | null };
type Resource = { id: string; name: string; revision: number; state: string };
type Daily = { day: string; recommendation: { id: string; source_kind: 'feed' | 'deep_inside'; source_title: string; source_url: string; text: string; saved_question_id: string | null; state: 'queued' | 'running' | 'ready' | 'failed'; error: string; evidence: string } | null; reason: string };

function LinkedSource({ id, index }: { id: string; index: number }) {
  const { data } = useResource<Resource>('/resources/' + id);
  return <Link className="button" to={'/library/' + id}>{data?.name ?? `자료 ${index + 1}`} 열기</Link>;
}

export function QuickQuestion() {
  const [open, setOpen] = useState(false), [text, setText] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const input = useRef<HTMLInputElement>(null), trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  async function save() {
    if (!text.trim() || busy) return;
    setBusy(true); setError('');
    try { await api('/questions', 'POST', { text, request_id: crypto.randomUUID() }); setText(''); setOpen(false); trigger.current?.focus(); window.dispatchEvent(new Event('questions-changed')); }
    catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); }
  }
  return <div className="quick-question"><Button ref={trigger} onClick={() => setOpen(value => !value)} aria-expanded={open} aria-controls="quick-question-panel">질문 적기</Button>{open && <div id="quick-question-panel" className="quick-question-panel" onKeyDown={e => { if (e.key === 'Escape') { setOpen(false); trigger.current?.focus(); } }}><form onSubmit={e => { e.preventDefault(); void save(); }}><Label htmlFor="quick-question-input">지금 궁금한 것은 무엇인가요?</Label><Input ref={input} id="quick-question-input" value={text} maxLength={500} onChange={e => setText(e.target.value)} placeholder="질문 한 줄을 남겨두세요" /><ErrorNotice error={error} /><div className="reference-actions"><Button className="primary" disabled={busy || !text.trim()}>{busy ? '저장 중…' : '질문 저장'}</Button><Button type="button" onClick={() => { setOpen(false); trigger.current?.focus(); }}>닫기</Button></div></form></div>}</div>;
}

function DailyQuestion({ onSaved }: { onSaved: () => void }) {
  const { data, error: loadError, reload } = useResource<Daily>('/questions/daily');
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [expanded, setExpanded] = useState(false);
  const recommendation = data?.recommendation;
  const firstSentence = recommendation?.text.match(/^.*?[.!?](?=\s|$)/)?.[0];
  const preview = recommendation && recommendation.text.length > 145 && firstSentence && firstSentence.length >= 30 ? firstSentence : recommendation?.text;
  const hasMore = preview !== recommendation?.text;
  useEffect(() => setExpanded(false), [recommendation?.id]);
  useEffect(() => {
    if (!data) return;
    const nextMidnight = Date.parse(data.day + 'T15:00:00Z');
    const timer = window.setTimeout(reload, Math.max(1000, nextMidnight - Date.now() + 1000));
    window.addEventListener('focus', reload);
    return () => { window.clearTimeout(timer); window.removeEventListener('focus', reload); };
  }, [data, reload]);
  useEffect(() => {
    if (!data?.recommendation || !['queued', 'running'].includes(data.recommendation.state)) return;
    const timer = window.setInterval(reload, 2500);
    return () => window.clearInterval(timer);
  }, [data, reload]);
  async function save() {
    if (!recommendation || busy) return;
    setBusy(true); setError('');
    try { await api('/questions/daily/save', 'POST', { recommendation_id: recommendation.id }); reload(); onSaved(); }
    catch (cause) { setError(errorMessage(cause)); reload(); }
    finally { setBusy(false); }
  }
  return <section className="daily-question" aria-labelledby="daily-question-heading">
    <div className="daily-question-heading"><h2 id="daily-question-heading">오늘의 질문</h2>{data && <time dateTime={data.day}>{data.day.replaceAll('-', '.')}</time>}</div>
    <ErrorNotice error={error || loadError} />{loadError && <Button onClick={reload}>추천 다시 불러오기</Button>}
    {recommendation ? <>
      <p className="daily-question-source"><span>{recommendation.source_kind === 'feed' ? '구독 포스팅' : 'Deep Inside'}</span><span aria-hidden="true">·</span>{recommendation.source_title}</p>
      {recommendation.state === 'ready'
        ? <div><p className={`daily-question-text${expanded ? '' : ' is-condensed'}`} aria-live="polite">{expanded ? recommendation.text : preview}</p>{recommendation.text.length > 145 && <Button type="button" variant="ghost" className={`daily-question-expand${hasMore ? '' : ' only-mobile'}`} aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? '질문 접기' : '질문 전체 보기'} <ChevronDown aria-hidden="true" size={16} /></Button>}</div>
        : <p className="daily-question-status" role="status">{recommendation.state === 'failed' ? recommendation.error : '본문에서 질문을 만들고 있습니다…'}</p>}
      <div className="reference-actions daily-question-actions">
        {recommendation.state === 'ready' && (recommendation.saved_question_id
          ? <Link className="button" to={'/questions/' + recommendation.saved_question_id}>저장한 질문 열기</Link>
          : <Button className="primary" disabled={busy} onClick={() => void save()}>{busy ? '저장 중…' : '질문함에 저장'}</Button>)}
        {recommendation.source_kind === 'feed'
          ? <a className="button" href={recommendation.source_url} target="_blank" rel="noreferrer">포스팅 보기</a>
          : <Link className="button" to="/apply">Deep Inside 보기</Link>}
      </div>
      {recommendation.state === 'ready' && recommendation.evidence && <details className="daily-question-source-detail"><summary>질문의 본문 근거 <ChevronDown aria-hidden="true" size={16} /></summary><p>{recommendation.evidence}</p></details>}
    </> : data && <><p className="daily-question-status">{data.reason}</p><div className="reference-actions"><Link className="button" to="/inbox">포스팅 보기</Link><Link className="button" to="/apply">Deep Inside 보기</Link></div></>}
  </section>;
}

export function QuestionInbox() {
  const [params, setParams] = useSearchParams();
  const status = params.get('status') === 'done' ? 'done' : 'open', q = params.get('q') ?? '', page = Math.max(1, Math.floor(Number(params.get('page')) || 1));
  const [search, setSearch] = useState(q);
  const { data, error, reload } = useResource<{ items: Question[]; total: number; page: number }>(`/questions?status=${status}&q=${encodeURIComponent(q)}&page=${page}`);
  useEffect(() => setSearch(q), [q]);
  useEffect(() => { window.addEventListener('questions-changed', reload); return () => window.removeEventListener('questions-changed', reload); }, [reload]);
  return <main className="page questions-page"><div className="breadcrumb">등록하기 <span>/</span> 질문함</div><header className="reference-page-heading"><div><h1>궁금한 것을 남겨두세요.</h1><p>질문은 한 줄이면 충분합니다. 나중에 자료를 연결하고 직접 확인해보세요.</p></div></header>
    <DailyQuestion onSaved={reload} />
    <form className="question-capture" onSubmit={e => { e.preventDefault(); setParams({ q: search, status }); }}><Label className="sr-only" htmlFor="question-search">질문 검색</Label><Input id="question-search" value={search} onChange={e => setSearch(e.target.value)} placeholder="질문 찾기" /><Button>검색</Button></form>
    <div className="question-filters"><h2>{status === 'open' ? '남겨둔 질문' : '정리 완료'} · {data?.total ?? 0}</h2><div><Button aria-pressed={status === 'open'} onClick={() => setParams({ q, status: 'open' })}>열린 질문</Button><Button aria-pressed={status === 'done'} onClick={() => setParams({ q, status: 'done' })}>정리 완료</Button></div></div>
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}{data?.items.map(item => <Link className="question-row" key={item.id} to={'/questions/' + item.id}><span><strong>{item.text}</strong><small>{timestamp(item.updated_at)} · 연결 자료 {item.links.length}개{item.note_id ? ' · 노트 연결됨' : ''}</small></span><span>열기</span></Link>)}{data && !data.items.length && <p className="empty-state">{q ? '검색 결과가 없습니다.' : '아직 질문이 없습니다. 상단의 ‘질문 적기’로 시작하세요.'}</p>}{data && data.total > 30 && <nav className="question-pages" aria-label="질문 페이지"><Button disabled={page <= 1} onClick={() => setParams({ q, status, page: String(page - 1) })}>이전</Button><span>{page} / {Math.ceil(data.total / 30)}</span><Button disabled={page >= Math.ceil(data.total / 30)} onClick={() => setParams({ q, status, page: String(page + 1) })}>다음</Button></nav>}
  </main>;
}

export function QuestionDetail() {
  const { id } = useParams(), navigate = useNavigate();
  const { data, error: loadError, reload } = useResource<Question>('/questions/' + id);
  const { data: guide, reload: reloadGuide } = useResource<{ guide: Guide | null }>('/questions/' + id + '/guide');
  const [draft, setDraft] = useState<Question | null>(null), [search, setSearch] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const { data: resources } = useResource<{ items: Resource[] }>('/resources?q=' + encodeURIComponent(search));
  const current = draft ?? data;
  const dirty = !!(draft && data && JSON.stringify({ text: draft.text, context: draft.context, links: draft.links, status: draft.status }) !== JSON.stringify({ text: data.text, context: data.context, links: data.links, status: data.status }));
  const blocker = useBlocker(dirty);
  useEffect(() => { if (blocker.state === 'blocked') { if (window.confirm('저장하지 않은 질문 변경사항이 있습니다. 이동할까요?')) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { if (!dirty) return; const warn = (event: BeforeUnloadEvent) => event.preventDefault(); window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn); }, [dirty]);
  useEffect(() => { if (!guide?.guide || !['queued', 'running'].includes(guide.guide.state)) return; const timer = setInterval(reloadGuide, 2500); return () => clearInterval(timer); }, [guide, reloadGuide]);
  async function save(next: Question) { setBusy(true); setError(''); try { const { revision, text, context, status, links, note_id } = next; const saved = await api<Question>('/questions/' + id, 'PUT', { revision, text, context, status, links, note_id }); setDraft(saved); reload(); reloadGuide(); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }
  async function start() { if (!current) return; setBusy(true); setError(''); try { await api('/questions/' + id + '/guide', 'POST', { revision: current.revision, request_id: crypto.randomUUID() }); reloadGuide(); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }
  async function remove() { if (!window.confirm('이 질문과 생성된 가이드를 삭제할까요?')) return; try { await api('/questions/' + id, 'DELETE', {}); navigate('/questions'); } catch (cause) { setError(errorMessage(cause)); } }
  return <main className="page questions-page"><div className="breadcrumb"><Link to="/questions">질문함</Link><span>/</span>질문 상세</div><ErrorNotice error={loadError || error} />{loadError && <Button onClick={reload}>다시 불러오기</Button>}{current && <><header className="reference-page-heading"><div><h1>질문을 살펴보세요.</h1><p>{timestamp(current.updated_at)} · {current.status === 'done' ? '정리 완료' : '열린 질문'}</p></div></header><div className="question-detail-form"><Label>질문<Input value={current.text} maxLength={500} onChange={e => setDraft({ ...current, text: e.target.value })} /></Label><Label>떠오른 맥락 (선택)<Textarea rows={4} value={current.context} maxLength={4000} onChange={e => setDraft({ ...current, context: e.target.value })} /></Label><div className="reference-actions"><Button className="primary" disabled={busy || !current.text.trim() || !dirty || draft?.revision !== data?.revision} onClick={() => void save(current)}>변경 저장</Button><Button disabled={busy} onClick={() => void save({ ...current, status: current.status === 'done' ? 'open' : 'done' })}>{current.status === 'done' ? '다시 열기' : '정리 완료'}</Button><Button disabled={busy} onClick={() => void remove()}>삭제</Button></div></div>
    <section className="question-section"><h2>관련 자료</h2><p>탐구할 때 사용할 근거를 선택하세요. 긴 자료는 관련 구절을 입력해야 합니다.</p><div className="question-capture"><Input aria-label="연결할 자료 검색" value={search} onChange={e => setSearch(e.target.value)} placeholder="자료 제목 검색" /></div>{search && <div className="question-resource-results">{resources?.items.filter(item => item.state === 'ready' && !current.links.some(link => link.resource_id === item.id)).map(item => <Button key={item.id} disabled={current.links.length >= 3 || busy} onClick={() => void save({ ...current, links: [...current.links, { resource_id: item.id, excerpt: '' }] })}>{item.name} 연결</Button>)}</div>}{current.links.map((link, index) => <div className="question-link" key={link.resource_id}><div><LinkedSource id={link.resource_id} index={index} /><Button disabled={busy} onClick={() => void save({ ...current, links: current.links.filter(item => item.resource_id !== link.resource_id) })}>연결 해제</Button></div><Label>관련 구절 (긴 자료일 때 필수)<Textarea rows={3} value={link.excerpt} maxLength={6000} onChange={e => setDraft({ ...current, links: current.links.map(item => item.resource_id === link.resource_id ? { ...item, excerpt: e.target.value } : item) })} /></Label></div>)}</section>
    <section className="question-section"><h2>AI 탐구 가이드</h2><p>연결한 자료의 현재 본문만 사용해 다시 읽을 부분과 직접 해볼 활동을 제안합니다. 질문의 답을 대신 작성하지 않습니다.</p><Button className="primary" disabled={busy || !current.links.length || dirty || ['queued','running'].includes(guide?.guide?.state ?? '')} onClick={() => void start()}>AI 탐구 시작</Button>{guide?.guide && <div className="question-guide" role="status">{guide.guide.question_revision !== current.revision && <p>질문이 변경된 이전 가이드입니다.</p>}{guide.guide.state === 'ready' && guide.guide.result ? <><h3>{guide.guide.result.title}</h3><p><strong>다시 읽기</strong> {guide.guide.result.reading}</p><h4>확인할 쟁점</h4><ul>{guide.guide.result.checks.map((item, index) => <li key={index}>{item}</li>)}</ul><p><strong>직접 해보기</strong> {guide.guide.result.practice}</p><p><strong>남길 결과</strong> {guide.guide.result.expected_output}</p><div className="question-guide-sources">{guide.guide.result.source_ids.map((sourceId, index) => <LinkedSource key={sourceId} id={sourceId} index={index} />)}</div></> : <p>{guide.guide.error || (guide.guide.state === 'queued' || guide.guide.state === 'running' ? '가이드를 준비하고 있습니다…' : guide.guide.state)}</p>}</div>}</section>
    <section className="question-section"><h2>내 언어로 정리</h2><p>정리한 노트는 기존 자료 복습과 지식 그래프 등록 흐름으로 이어집니다.</p>{current.note_id ? <Link className="button" to={'/references/' + current.note_id}>연결된 노트 열기</Link> : <Link className="button" to="/references/new" state={{ questionId: current.id, questionText: current.text }}>노트로 정리</Link>}</section></>}</main>;
}
