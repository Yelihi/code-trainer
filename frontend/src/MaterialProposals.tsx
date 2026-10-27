import { MaterialKnowledge } from './ReferenceKnowledge';
import { useEffect, useRef, useState } from 'react';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Markdown } from './Markdown';
import { NativeSelect } from './components/ui/native-select';
import { type ProposalData, type NoteContentReview, type ConceptMatch } from './referenceTypes';
import type { ReviewedMaterial } from './KnowledgeCandidates';
import { Button } from './components/ui/button';
import { Label } from './components/ui/label';

export type MaterialProposal = { id: string; state: 'queued' | 'running' | 'ready' | 'failed' | 'stale' | 'interrupted'; error: string; created_at: string; material: ReviewedMaterial; data: (ProposalData & { review: NoteContentReview }) | null; matches: (ConceptMatch & { key: string; pref_label: string; definition: string; scope: string; reason: string })[] };
const states = { queued: '대기', running: '추출·검토 중', ready: '후보 준비됨', failed: '실패', stale: '자료 변경됨', interrupted: '중단됨' };
export function MaterialProposals({ material }: { material: ReviewedMaterial }) {
  const { userId } = useApp();
  return <Proposals key={userId + ':' + material.id} material={material} storageKey={`material-proposal:${userId}:${material.id}`} />;
}
function Proposals({ material, storageKey }: { material: ReviewedMaterial; storageKey: string }) {
  const path = '/material-reviews/' + material.id + '/proposals';
  const { data: history, error: loadError, reload } = useResource<MaterialProposal[]>(path);
  const [selected, setSelected] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [requestId, setRequestId] = useState(() => { try { return localStorage.getItem(storageKey) || crypto.randomUUID(); } catch { return crypto.randomUUID(); } });
  const sending = useRef(false);
  const pending = history?.some(p => p.state === 'queued' || p.state === 'running');
  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(reload, 1500);
    return () => clearTimeout(timer);
  }, [pending, history, reload]);
  async function generate() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try {
      localStorage.setItem(storageKey, requestId);
      const result = await api<MaterialProposal>(path, 'POST', { request_id: requestId });
      setSelected(result.id); setRequestId(crypto.randomUUID());
      try { localStorage.removeItem(storageKey); } catch { /* Successful request is already durable on server. */ }
      reload();
    } catch (e) { setError(errorMessage(e)); }
    finally { sending.current = false; setBusy(false); }
  }
  const proposal = history?.find(p => p.id === selected) ?? history?.[0];
  const eligible = material.state === 'eligible' && (!proposal || proposal.material.state === 'eligible');
  return <section className="reference-knowledge">
    <div className="section-heading"><div><span className="eyebrow">EXTRACT WITH EVIDENCE</span><h2>연결할 개념 찾기</h2></div></div>
    <p>확인한 이 버전에서 개념과 관계를 추출하고 내용을 검토합니다. 후보 생성만으로 지식 그래프에 추가되지는 않습니다.</p>
    <p className="muted">근거는 {material.authorship === 'ai' ? 'AI가 작성한 해석' : '내가 작성한 답변·요약'}입니다. 원문 자체의 주장과 구분해 살펴보세요.</p>
    <Button disabled={busy || !!pending || !history || !eligible} onClick={() => void generate()}>{busy || pending ? '후보 추출·검토 중…' : 'AI로 후보 생성·내용 검토'}</Button>
    <ErrorNotice error={error || loadError} />{loadError && <Button onClick={reload}>추출 기록 다시 불러오기</Button>}
    {!eligible && <p className="notice">자료가 변경되거나 보관되었습니다. 원래 학습 화면에서 최신 자료를 확인해주세요.</p>}
    {history && history.length > 0 && <Label>최근 추출 기록<NativeSelect value={proposal?.id ?? ''} onChange={e => setSelected(e.target.value)}>{history.map(p => <option key={p.id} value={p.id}>{timestamp(p.created_at)} · {states[p.state]}</option>)}</NativeSelect></Label>}
    {proposal && <><p role="status">{states[proposal.state]}</p><ErrorNotice error={proposal.error} />
      {proposal.data && <><section className="interpretation-provenance"><h3>본문과 후보 검토</h3><Markdown language="">{proposal.data.review.summary}</Markdown>{proposal.data.review.issues.map((issue, i) => <article key={i}><h4>{issue.kind === 'correction_needed' ? '수정 필요' : '확인 필요'}</h4><blockquote>{issue.quote}</blockquote><Markdown language="">{issue.explanation}</Markdown><Markdown language="">{issue.suggestion}</Markdown></article>)}<p>AI가 문제를 찾지 못했어도 사실이 검증된 것은 아닙니다. 수정이 필요하면 원래 학습 화면에서 새 작성분을 저장하거나 해석을 다시 진행해주세요.</p></section>
        <MaterialKnowledge key={proposal.id + ':' + proposal.material.registration?.id + ':' + proposal.material.state} material={proposal.material}
          proposal={{ id: proposal.id, state: proposal.state, revision: material.revision, error: proposal.error, review: proposal.data.review, matches: proposal.matches, data: { concepts: proposal.data.concepts, assertions: proposal.data.assertions } }} onRegistered={reload} />
      </>}
    </>}
  </section>;
}
