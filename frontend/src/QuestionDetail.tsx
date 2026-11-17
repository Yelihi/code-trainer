import { LearningTargets, targetInput } from './LearningTargets';
import { useEffect, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { FileText } from 'lucide-react';
import { EmptyState } from './WorkspaceUI';
import { LinkedQuestionSource, QuestionSources } from './QuestionSources';
import { QuestionDetailSkeleton } from './QuestionSkeletons';
import type { Question } from './questionTypes';
import { Button } from './components/ui/button';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import './questions.css';

export function QuestionDetail() {
  const { id } = useParams();
  return <QuestionDetailContent key={id} />;
}

function QuestionDetailContent() {
  const { id } = useParams(), navigate = useNavigate();
  const { data, error: loadError, reload, update } = useResource<Question>('/questions/' + id, { preserveData: true });
  const [draft, setDraft] = useState<Question | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const current = draft ?? data;
  const dirty = !!(draft && data && JSON.stringify({ targets: draft.targets, text: draft.text, context: draft.context, links: draft.links, status: draft.status }) !== JSON.stringify({ targets: data.targets, text: data.text, context: data.context, links: data.links, status: data.status }));
  const blocker = useBlocker(dirty);
  useEffect(() => { if (blocker.state === 'blocked') { if (window.confirm('저장하지 않은 질문 변경사항이 있습니다. 이동할까요?')) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { if (!dirty) return; const warn = (event: BeforeUnloadEvent) => event.preventDefault(); window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn); }, [dirty]);
  async function save(next: Question) { setBusy(true); setError(''); try { const { revision, text, context, status, links, note_id } = next; const saved = await api<Question>('/questions/' + id, 'PUT', { revision, text, context, status, links, note_id, targets: next.targets?.map(targetInput) }); update(saved); setDraft(null); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }
  async function remove() { if (!window.confirm('질문을 삭제할까요?')) return; setBusy(true); setError(''); try { await api('/questions/' + id, 'DELETE', {}); navigate('/questions'); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }
  return <main className="page questions-page question-detail-page">
    <div className="breadcrumb"><Link to="/questions">질문함</Link><span>/</span>{draft ? '질문 수정' : '질문 상세'}</div>
    <ErrorNotice error={loadError || error} />{loadError && <Button onClick={reload}>다시 불러오기</Button>}
    {!current && !loadError && <QuestionDetailSkeleton />}
    {current && <>
      <header className="question-detail-heading"><div><span className="question-status">{current.status === 'done' ? '정리 완료' : '열린 질문'}</span><h1>{draft ? '질문 수정' : current.text}</h1><time className="question-detail-meta">{timestamp(current.updated_at)}</time></div>{!draft && <Button onClick={() => setDraft({ ...current })}>수정</Button>}</header>
      {draft ? <div className="question-edit-panel">
        <Label>질문<Textarea aria-label="질문" rows={3} disabled={busy} value={current.text} maxLength={500} onChange={e => setDraft({ ...current, text: e.target.value })} /></Label>
        <Label>설명<Textarea aria-label="설명" disabled={busy} rows={6} value={current.context} maxLength={4000} onChange={e => setDraft({ ...current, context: e.target.value })} /></Label>
        <LearningTargets targets={current.targets ?? []} disabled={busy} onChange={targets => setDraft({ ...current, targets })} />
        <QuestionSources current={current} busy={busy} onDraft={setDraft} />
        <div className="question-edit-footer"><Button disabled={busy} onClick={() => { if (!dirty || window.confirm('변경사항을 취소할까요?')) setDraft(null); }}>취소</Button><Button className="primary" loading={busy} disabled={busy || !current.text.trim() || !dirty || draft.revision !== data?.revision} onClick={() => void save(current)}>변경 저장</Button></div>
      </div> : <QuestionReading question={current} />}
      {!draft && <footer className="question-detail-footer"><Button loading={busy} onClick={() => void save({ ...current, status: current.status === 'done' ? 'open' : 'done' })}>{current.status === 'done' ? '다시 열기' : '정리 완료로 표시'}</Button><Button disabled={busy} className="text-button" onClick={() => void remove()}>질문 삭제</Button></footer>}
    </>}
  </main>;
}

export function QuestionReading({ question }: { question: Question }) {
  const hasReferences = !!(question.links.length || question.targets?.length || question.note_id);
  return <div className="question-reading">
    {question.context && <section className="question-section"><h2>설명</h2><p className="question-description">{question.context}</p></section>}
    <section className="question-section"><h2>참고 자료</h2>
      {hasReferences ? <div className="question-reference-list">
        {question.targets?.map(target => <Link className="question-reference-item" key={target.kind + target.id + target.unit_id} to={target.href}><FileText size={18} aria-hidden="true" />{target.title}</Link>)}
        {question.links.map(link => <div className="question-reference-item" key={link.resource_id}><FileText size={18} aria-hidden="true" /><div><LinkedQuestionSource id={link.resource_id} />{link.excerpt && <blockquote>{link.excerpt}</blockquote>}</div></div>)}
        {question.note_id && <Link className="question-reference-item" to={'/references/' + question.note_id}><FileText size={18} aria-hidden="true" />저장한 기록</Link>}
      </div> : <EmptyState icon={FileText} title="연결된 자료 없음" />}
    </section>
  </div>;
}
