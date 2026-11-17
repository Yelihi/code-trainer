import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { LoadingSkeleton } from './LoadingSkeleton';
import { PageHeading } from './WorkspaceUI';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';

export type QuestionPolicy = { question_age_days: number; resurfacing_days: number; snooze_days: number; question_limit: number };
const fields: { key: keyof QuestionPolicy; label: string; description: string; unit: string; max: number }[] = [
  { key: 'question_age_days', label: '처음 다시 볼 때', description: '질문을 남긴 날부터', unit: '일 후', max: 365 },
  { key: 'resurfacing_days', label: '다시 보여주는 간격', description: '이전에 본 질문을 다시 살펴볼 때', unit: '일', max: 365 },
  { key: 'snooze_days', label: '나중에 보기', description: '‘나중에’를 누른 질문을 쉬어두는 기간', unit: '일 후', max: 90 },
  { key: 'question_limit', label: '한 번에 보여줄 질문', description: '홈에 표시할 최대 질문 수', unit: '개', max: 10 },
];
export function QuestionPolicySettings() {
  const { data, error, reload } = useResource<{ policy: QuestionPolicy }>('/study/today');
  return <main className="page settings-page question-policy-page">
    <div className="breadcrumb"><Link to="/">오늘의 학습</Link><span>/</span>질문 다시보기 설정</div>
    <PageHeading title="질문 다시보기 설정" />
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="editor" label="질문 설정을 불러오는 중…" />}
    {data && <QuestionPolicyForm initial={data.policy} />}
  </main>;
}
export function QuestionPolicyForm({ initial }: { initial: QuestionPolicy }) {
  const [policy, setPolicy] = useState<Record<keyof QuestionPolicy, number | ''>>(initial), [saved, setSaved] = useState(initial);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [message, setMessage] = useState('');
  const dirty = fields.some(field => policy[field.key] !== saved[field.key]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try { const next = await api<QuestionPolicy>('/study/policy', 'PUT', policy); setPolicy(next); setSaved(next); setMessage('질문 다시보기 설정을 저장했어요.'); }
    catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); }
  }
  return <form className="question-policy-form" onSubmit={event => void submit(event)}>
    <section className="policy-rows" aria-label="질문 표시 주기">{fields.map(field => <div className="policy-row" key={field.key}>
      <div><Label htmlFor={'policy-' + field.key}>{field.label}</Label><p id={'policy-' + field.key + '-hint'}>{field.description}</p></div>
      <div className="policy-value"><Input id={'policy-' + field.key} aria-describedby={'policy-' + field.key + '-hint'} type="number" inputMode="numeric" min={1} max={field.max} step={1} required value={policy[field.key]} disabled={busy} onChange={event => { setPolicy({ ...policy, [field.key]: event.target.value === '' ? '' : event.target.valueAsNumber }); setMessage(''); }} /><span>{field.unit}</span></div>
    </div>)}</section>
    <p className="settings-help">한국 시간 기준이에요. 질문을 미루거나 숨겨도 질문함의 기록은 남아요.</p>
    <ErrorNotice error={error} />{message && <p className="policy-saved" role="status">{message}</p>}
    <footer className="policy-footer"><Link className="button" to="/">홈으로</Link><Button className="primary" loading={busy} disabled={busy || !dirty}>변경 저장</Button></footer>
  </form>;
}
