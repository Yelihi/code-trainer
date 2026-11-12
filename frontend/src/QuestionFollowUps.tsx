import { memo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { Button } from './components/ui/button';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Skeleton } from './components/ui/skeleton';
import type { Question } from './questionTypes';

type RelatedQuestion = Pick<Question, 'id' | 'text' | 'status'>;
type Relations = { parent: RelatedQuestion | null; children: RelatedQuestion[] };

export const QuestionFollowUps = memo(function QuestionFollowUps({ id }: { id: string }) {
  const { data, loading, error: loadError, reload, update } = useResource<Relations>(`/questions/${id}/relations`, { preserveData: true });
  const [text, setText] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const request = useRef({ text: '', id: '' });
  async function create() {
    if (busy || !text.trim()) return;
    setBusy(true); setError('');
    if (request.current.text !== text || !request.current.id) request.current = { text, id: crypto.randomUUID() };
    try {
      const child = await api<Question>('/questions', 'POST', { text, parent_id: id, request_id: request.current.id });
      if (data) update({ ...data, children: [...data.children.filter(item => item.id !== child.id), child] });
      else reload();
      setText(''); request.current = { text: '', id: '' };
      window.dispatchEvent(new Event('questions-changed'));
    } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); }
  }
  return <section className="question-section question-follow-ups" aria-labelledby="follow-up-heading">
    <h2 id="follow-up-heading">이어지는 질문</h2>
    <div className="question-relations" aria-busy={loading}>{data ? <>
      {data.parent && <p>상위 질문 · <Link to={'/questions/' + data.parent.id}>{data.parent.text}</Link></p>}
      {data.children.length ? <ul>{data.children.map(child => <li key={child.id}><Link to={'/questions/' + child.id}>{child.text}</Link><small>{child.status === 'done' ? '정리 완료' : '열린 질문'}</small></li>)}</ul> : <p>아직 꼬리질문이 없습니다. 더 알아보고 싶은 점을 이어 적어보세요.</p>}
    </> : <Skeleton className="question-relation-skeleton" aria-label="이어지는 질문을 불러오는 중" />}</div>
    <form onSubmit={event => { event.preventDefault(); void create(); }}>
      <Label htmlFor="follow-up-text">꼬리질문<Textarea id="follow-up-text" value={text} disabled={busy} onChange={event => setText(event.target.value)} maxLength={500} rows={3} placeholder="이 질문에서 더 궁금해진 점은 무엇인가요?" /></Label>
      <div className="question-feedback"><ErrorNotice error={error || loadError} />{loadError && <Button type="button" onClick={reload}>다시 불러오기</Button>}<span role="status">{busy ? '꼬리질문을 저장하고 있습니다…' : ''}</span></div>
      <Button className="primary" disabled={busy || loading || !data || !text.trim()}>꼬리질문 저장</Button>
    </form>
  </section>;
});
