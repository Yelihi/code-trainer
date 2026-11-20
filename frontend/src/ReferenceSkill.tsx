import { useEffect, useRef, useState } from 'react';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useResource } from './App';
import { Button } from './components/ui/button';
type Job = { id: string; kind: string; state: string; created_at: string };
type Preview = { id: string; state: string; error: string; markdown: string | null; stale: boolean; reference_revision: number; created_at: string };
export function ReferenceSkill({ id, revision, jobs, reload }: { id: string; revision: number; jobs: Job[]; reload: () => void }) {
  const [selected, setSelected] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const request = useRef({ revision: 0, id: '' });
  const skillJobs = jobs.filter(job => job.kind === 'skill');
  const active = skillJobs.find(job => job.state === 'queued' || job.state === 'running');
  async function generate() {
    if (request.current.revision !== revision) request.current = { revision, id: crypto.randomUUID() };
    setBusy(true); setError('');
    try { const job = await api<Job>(`/technical-references/${id}/skills`, 'POST', { revision, request_id: request.current.id }); setSelected(job.id); request.current.revision = 0; reload(); }
    catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); }
  }
  return <section className="learning-section"><header><h2>AI 작업용 Skill</h2><Button loading={busy || !!active} disabled={busy || !!active} onClick={() => void generate()}>{active ? 'Skill 생성 중…' : 'Skill 만들기'}</Button></header><p className="muted">연결된 학습 근거나 내 설명을 작업 지침으로 바꿉니다. 생성 시 AI를 사용합니다. 내용을 확인한 뒤 다운로드하세요.</p><ErrorNotice error={error} />{skillJobs.length > 0 && <details><summary>이전에 만든 Skill</summary>{skillJobs.map(job => <Button key={job.id} onClick={() => setSelected(job.id)}>{timestamp(job.created_at)} · {job.state === 'ready' ? '미리보기' : job.state === 'failed' ? '생성 실패' : '생성 상태'}</Button>)}</details>}{(selected || skillJobs[0]?.id) && <SkillPreview key={selected || skillJobs[0].id} id={id} jobId={selected || skillJobs[0].id} />}</section>;
}
function SkillPreview({ id, jobId }: { id: string; jobId: string }) {
  const { data, error, reload } = useResource<Preview>(`/technical-references/${id}/skills/${jobId}`, { preserveData: true });
  const pending = data?.state === 'queued' || data?.state === 'running';
  useEffect(() => { if (!pending) return; const timer = setInterval(reload, 2000); return () => clearInterval(timer); }, [pending, reload]);
  return <div className="skill-preview"><ErrorNotice error={error || data?.error || ''} />{pending && <p role="status">Skill을 준비하고 있습니다…</p>}{data?.markdown && <>{data.stale && <p className="notice">이 Skill은 이전 작성 내용이나 근거를 기준으로 만들었습니다.</p>}<p>기준: 사용자 작성 v{data.reference_revision} · {timestamp(data.created_at)}</p><details><summary>SKILL.md 미리보기</summary><pre className="skill-markdown"><code>{data.markdown}</code></pre></details><a className="button primary" href={`/api/technical-references/${id}/skills/${jobId}/download`} download>확인한 Skill ZIP 다운로드</a><p className="muted">SKILL.md와 참고 문서를 포함합니다. 자동 설치나 외부 공개는 하지 않습니다.</p></>}</div>;
}
