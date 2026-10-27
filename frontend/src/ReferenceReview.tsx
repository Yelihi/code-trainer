import { LoadingSkeleton } from './LoadingSkeleton';
import { AnimatedDetails } from './AnimatedDetails';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp } from './App';
import { Markdown } from './Markdown';
import { clearReferenceDraft, type ReferenceReview as Review } from './referenceTypes';
import './referenceNotes.css';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';

export function ReferenceReview() {
  const { id } = useParams();
  return <ReviewConversation key={id} id={id!} />;
}

function ReviewConversation({ id }: { id: string }) {
  const { userId } = useApp();
  const [draftKey] = useState(`reference-answer:${userId}:${id}`);
  const [draft] = useState(() => {
    try { const v = JSON.parse(localStorage.getItem(draftKey) ?? 'null'); return v && typeof v.answer === 'string' && typeof v.requestId === 'string' ? v as { answer: string; requestId: string } : null; }
    catch { return null; }
  });
  const [review, setReview] = useState<Review | null>(null);
  const [answer, setAnswer] = useState(draft?.answer ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);
  const [requestId, setRequestId] = useState<string>(draft?.requestId ?? crypto.randomUUID());
  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const result = await api<Review>('/reference-reviews/' + id, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setReview(result);
        if (draft && result.turns.some(t => t.role === 'user' && t.request_id === draft.requestId)) {
          setAnswer(''); clearReferenceDraft(draftKey);
        }
        if (result.state === 'running') timer = setTimeout(() => void load(), 1500);
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    }
    void load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [id, version, draft, draftKey]);
  useEffect(() => {
    if (!answer) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [answer]);
  async function send(retry = false) {
    if (!review) return;
    const previous = [...review.turns].reverse().find(t => t.role === 'user');
    const text = retry && previous ? previous.answer : answer;
    const request_id = retry && previous ? previous.request_id : requestId;
    setBusy(true); setError('');
    try {
      const result = await api<Review>('/reference-reviews/' + id + '/answers', 'POST', { revision: review.revision, request_id, answer: text });
      setReview(result); setAnswer(''); clearReferenceDraft(draftKey); setRequestId(crypto.randomUUID()); setVersion(v => v + 1);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <main className="page reference-page reference-review-page">
    <div className="breadcrumb"><Link to="/references">레퍼런스 노트</Link><span>/</span> 내 말로 설명해보기</div>
    <header className="reference-page-heading"><div><span className="eyebrow">THINK IT THROUGH</span><h1>설명에서, 다음 질문으로.</h1><p>내가 이해한 것을 말로 풀어보고, 연결된 기록을 따라 생각을 넓혀보세요.</p></div>{review && <Link className="button" to={'/references/' + review.note_id}>노트로 돌아가기</Link>}</header>
    <ErrorNotice error={error} />{error && <Button onClick={() => setVersion(v => v + 1)}>기록 다시 불러오기</Button>}
    {!review && !error && <LoadingSkeleton layout="conversation" label="복습을 불러오는 중…" />}
    {review && <div className="reference-review-layout"><section className="reference-conversation" aria-label="설명과 꼬리 질문">
      {review.turns.map((turn, i) => <article key={i} className={`reference-turn ${turn.role}`}>
        <span className="eyebrow">{turn.role === 'user' ? '나의 설명' : i === 0 ? '첫 번째 질문' : 'AI 피드백 · 꼬리 질문'}</span>
        {turn.role === 'user' ? <p className="prose">{turn.answer}</p> : <>{turn.feedback && <Markdown language="">{turn.feedback}</Markdown>}<h2>{turn.question}</h2><div className="reference-citations">{turn.citations.map(citation => { const source = review.sources.find(s => s.id === citation); return source && <a key={citation} href={'#source-' + source.id}>{source.title} · v{source.version}</a>; })}</div></>}
      </article>)}
      {review.state === 'running' && <p className="notice" role="status">설명을 저장했습니다. 연결된 노트를 참고해 다음 질문을 준비하고 있습니다…</p>}
      <ErrorNotice error={review.error} />
      {review.state === 'failed' && <Button disabled={busy} onClick={() => void send(true)}>저장한 설명으로 질문 다시 받기</Button>}
      <form className="reference-answer" onSubmit={e => { e.preventDefault(); void send(); }}><Label htmlFor="reference-answer">내 생각을 이어서 설명해보세요</Label><Textarea id="reference-answer" value={answer} onChange={e => {
        const requestId = crypto.randomUUID(); setAnswer(e.target.value); setRequestId(requestId);
        try { localStorage.setItem(draftKey, JSON.stringify({ answer: e.target.value, requestId })); }
        catch { setError('브라우저 임시 저장에 실패했습니다. 작성한 설명을 복사해 보관해주세요.'); }
      }} disabled={busy || review.state !== 'ready'} maxLength={8000} rows={7} placeholder="이렇게 이해했습니다. 예를 들면…" required /><div><small>AI 피드백은 참고용입니다. 설명과 복습 이력은 그래프 등록과 별도로 저장됩니다.</small><Button className="primary" disabled={busy || review.state !== 'ready' || !answer.trim()}>{busy ? '설명 저장 중…' : '설명 저장 · 다음 질문 받기'}</Button></div></form>
    </section><aside className="reference-review-sources"><span className="eyebrow">CONNECTED REFERENCES</span><h2>함께 돌아볼 기록</h2><p>복습을 시작한 시점의 본문 발췌입니다. 먼저 설명한 뒤 펼쳐봐도 좋습니다. 첨부 이미지는 AI가 읽지 않습니다.</p>
      {review.sources.map(source => <AnimatedDetails id={'source-' + source.id} key={source.id} summary={<>{source.title}<small>v{source.version} · {source.relationship}</small></>}>{source.metadata.locator && <p>{source.metadata.locator}</p>}<Markdown language="" images>{source.body}</Markdown>{source.note_id && <Link className="text-link" to={'/references/' + source.note_id}>현재 노트 열기</Link>}</AnimatedDetails>)}
      {review.sources.length === 1 && <p className="reference-state">현재 연결된 다른 기록은 없습니다. 개념 지도에 노트를 연결하면 함께 복습할 수 있습니다.</p>}
    </aside></div>}
  </main>;
}
