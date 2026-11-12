import { useEffect, useState } from 'react';
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { QuestionFollowUps } from './QuestionFollowUps';
import { QuestionGuide } from './QuestionGuide';
import { QuestionSources } from './QuestionSources';
import { QuestionDetailSkeleton } from './QuestionSkeletons';
import type { Question } from './questionTypes';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Skeleton } from './components/ui/skeleton';
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
  const dirty = !!(draft && data && JSON.stringify({ text: draft.text, context: draft.context, links: draft.links, status: draft.status }) !== JSON.stringify({ text: data.text, context: data.context, links: data.links, status: data.status }));
  const blocker = useBlocker(dirty);
  useEffect(() => { if (blocker.state === 'blocked') { if (window.confirm('저장하지 않은 질문 변경사항이 있습니다. 이동할까요?')) blocker.proceed(); else blocker.reset(); } }, [blocker]);
  useEffect(() => { if (!dirty) return; const warn = (event: BeforeUnloadEvent) => event.preventDefault(); window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn); }, [dirty]);
  async function save(next: Question) { setBusy(true); setError(''); try { const { revision, text, context, status, links, note_id } = next; const saved = await api<Question>('/questions/' + id, 'PUT', { revision, text, context, status, links, note_id }); update(saved); setDraft(null); } catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); } }
  async function remove() { if (!window.confirm('이 질문과 생성된 가이드를 삭제할까요? 꼬리질문은 남겨두고 상위 질문에 이어집니다.')) return; try { await api('/questions/' + id, 'DELETE', {}); navigate('/questions'); } catch (cause) { setError(errorMessage(cause)); } }
  return <main className="page questions-page"><div className="breadcrumb"><Link to="/questions">질문함</Link><span>/</span>질문 상세</div><header className="reference-page-heading"><div><h1>질문을 살펴보세요.</h1><p className="question-detail-meta">{current ? `${timestamp(current.updated_at)} · ${current.status === 'done' ? '정리 완료' : '열린 질문'}` : <Skeleton className="question-meta-skeleton" />}</p></div></header><div className="question-feedback"><ErrorNotice error={loadError || error} />{loadError && <Button onClick={reload}>다시 불러오기</Button>}</div>{!current && <QuestionDetailSkeleton />}{current && <><div className="question-detail-form"><Label>질문<Input disabled={busy} value={current.text} maxLength={500} onChange={e => setDraft({ ...current, text: e.target.value })} /></Label><Label>떠오른 맥락 (선택)<Textarea disabled={busy} rows={4} value={current.context} maxLength={4000} onChange={e => setDraft({ ...current, context: e.target.value })} /></Label><div className="reference-actions"><Button className="primary" disabled={busy || !current.text.trim() || !dirty || draft?.revision !== data?.revision} onClick={() => void save(current)}>변경 저장</Button><Button disabled={busy} onClick={() => void save({ ...current, status: current.status === 'done' ? 'open' : 'done' })}>{current.status === 'done' ? '다시 열기' : '정리 완료'}</Button><Button disabled={busy} onClick={() => void remove()}>삭제</Button></div></div>
    <QuestionFollowUps id={current.id} />
    <QuestionSources current={current} busy={busy} onSave={save} onDraft={setDraft} />
    <QuestionGuide id={current.id} revision={current.revision} canStart={!busy && !!current.links.length && !dirty} />
    <section className="question-section"><h2>내 언어로 정리</h2><p>정리한 노트는 기존 자료 복습과 지식 그래프 등록 흐름으로 이어집니다.</p>{current.note_id ? <Link className="button" to={'/references/' + current.note_id}>연결된 노트 열기</Link> : <Link className="button" to="/references/new" state={{ questionId: current.id, questionText: current.text }}>노트로 정리</Link>}</section></>}</main>;
}
