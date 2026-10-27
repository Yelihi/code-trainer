import type { ReviewedMaterial } from './KnowledgeCandidates';
import { ConceptConnection } from './ConceptConnection';
import { NativeSelect } from './components/ui/native-select';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ReferenceContentReview } from './ReferenceContentReview';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp } from './App';
import { clearReferenceDraft, registrationBlock, bases, relations, type Assertion, type Candidate, type Concept, type Proposal, type ProposalData, type ReferenceNote } from './referenceTypes';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';

type ConnectionDraft = { data: ProposalData; requestId: string; decisions?: Record<string, boolean>; originals?: Record<string, Candidate>; selected?: Record<string, Concept> };
const unlinked = (data: ProposalData): ProposalData => ({ ...data, concepts: data.concepts.map(c => ({ ...c, existing_id: '' })) });
const blankConcept = (key: string): Candidate => ({ key, existing_id: '', pref_label: '', definition: '', scope: '', aliases: [], quote: '', basis: 'source' });

type NoteKnowledgeProps = { note: ReferenceNote; onNoteChange: (note: ReferenceNote) => void; onNoteApplied: (note: ReferenceNote) => void; onEdit: () => void };
type MaterialKnowledgeProps = { material: Pick<ReviewedMaterial, 'id' | 'revision' | 'state' | 'reason' | 'registration'>; proposal: Proposal; onRegistered: () => void };
export function ReferenceKnowledge(props: NoteKnowledgeProps) { return <KnowledgeEditor {...props} />; }
export function MaterialKnowledge(props: MaterialKnowledgeProps) { return <KnowledgeEditor {...props} />; }
function KnowledgeEditor(props: NoteKnowledgeProps | MaterialKnowledgeProps) {
  const isMaterial = 'material' in props;
  const source = isMaterial ? props.material : props.note;
  const { userId } = useApp();
  const [draftKey] = useState(`${isMaterial ? 'material' : 'reference'}-graph-draft:${userId}:${source.id}:${source.revision}${isMaterial ? ':' + props.proposal.id : ''}`);
  const [restored] = useState(() => {
    try { const v = JSON.parse(localStorage.getItem(draftKey) ?? 'null'); return v && Array.isArray(v.data?.concepts) && Array.isArray(v.data?.assertions) && typeof v.requestId === 'string' ? v as ConnectionDraft : null; }
    catch { return null; }
  });
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [search, setSearch] = useState('');
  const [data, setData] = useState<ProposalData | null>(restored?.data ?? (isMaterial && props.proposal.data ? unlinked(props.proposal.data) : null));
  const [decisions, setDecisions] = useState<Record<string, boolean>>(restored?.decisions ?? {});
  const [originals, setOriginals] = useState<Record<string, Candidate>>(restored?.originals ?? {});
  const [selected, setSelected] = useState<Record<string, Concept>>(restored?.selected ?? {});
  const [proposal, setProposal] = useState<Proposal | null>(isMaterial ? props.proposal : null);
  const [proposalId, setProposalId] = useState(isMaterial ? props.proposal.id : props.note.proposal?.id ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [requestId, setRequestId] = useState<string>(restored?.requestId ?? crypto.randomUUID());
  useEffect(() => {
    const controller = new AbortController();
    api<Concept[]>('/knowledge/concepts?q=' + encodeURIComponent(search), 'GET', undefined, controller.signal).then(setConcepts).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); });
    return () => controller.abort();
  }, [search]);
  useEffect(() => {
    if (isMaterial || !proposalId) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const result = await api<Proposal>('/reference-proposals/' + proposalId, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setProposal(result);
        if (result.state === 'running') timer = setTimeout(() => void load(), 1500);
        else if (result.data && result.revision === source.revision) setData(current => current ?? unlinked(result.data!));
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    };
    void load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [proposalId, source.revision, isMaterial]);
  function change(next: ProposalData, choices = decisions, drafts = originals, selections = selected) {
    const requestId = crypto.randomUUID(); setData(next); setRequestId(requestId); setDecisions(choices); setOriginals(drafts); setSelected(selections);
    try { localStorage.setItem(draftKey, JSON.stringify({ data: next, requestId, decisions: choices, originals: drafts, selected: selections })); }
    catch { setError('후보를 브라우저에 임시 저장하지 못했습니다. 화면을 이동하기 전에 등록해주세요.'); }
  }
  function concept(index: number, patch: Partial<Candidate>) {
    if (!data) return;
    const current = data.concepts[index];
    const identityChanged = !current.existing_id && ['pref_label', 'definition', 'scope', 'aliases'].some(key => key in patch && JSON.stringify(patch[key as keyof Candidate]) !== JSON.stringify(current[key as keyof Candidate]));
    change({ ...data, concepts: data.concepts.map((c, i) => i === index ? { ...c, ...patch } : c) }, identityChanged ? { ...decisions, [current.key]: false } : decisions);
  }
  function connect(index: number, target?: Concept) {
    if (!data) return;
    const current = data.concepts[index];
    if (target && current.existing_id === target.id && decisions[current.key]) return;
    const original = current.existing_id ? originals[current.key] ?? current : current;
    const next = target ? { ...current, existing_id: target.id, pref_label: target.pref_label, definition: target.definition, scope: target.scope, aliases: [] } : { ...original, quote: current.quote, basis: current.basis, existing_id: '' };
    change({ ...data, concepts: data.concepts.map((c, i) => i === index ? next : c) }, { ...decisions, [current.key]: true }, { ...originals, [current.key]: original }, { ...selected, ...(target ? { [current.key]: target } : {}) });
  }
  function assertion(index: number, patch: Partial<Assertion>) { if (data) change({ ...data, assertions: data.assertions.map((a, i) => i === index ? { ...a, ...patch } : a) }); }
  async function analyze() {
    if (isMaterial) return;
    setBusy(true); setError('');
    try { const result = await api<Proposal>(`/reference-notes/${source.id}/proposals`, 'POST', { revision: source.revision }); setData(result.data ? unlinked(result.data) : null); setDecisions({}); setOriginals({}); setSelected({}); setRequestId(crypto.randomUUID()); clearReferenceDraft(draftKey); setProposal(result); setProposalId(result.id); props.onNoteChange({ ...props.note, proposal: { id: result.id, state: result.state, revision: result.revision } }); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function register() {
    const blocked = reviewBlocked;
    if (blocked) { setError(blocked); return; }
    if (data?.concepts.some(c => !decisions[c.key])) { setError('각 개념의 등록 방식을 먼저 선택해주세요.'); return; }
    setBusy(true); setError('');
    try {
      const body = { revision: source.revision, request_id: requestId, proposal_id: proposal?.state === 'ready' ? proposal.id : null, data };
      if (isMaterial) { await api(`/material-reviews/${source.id}/knowledge`, 'POST', body); clearReferenceDraft(draftKey); props.onRegistered(); }
      else { const result = await api<ReferenceNote>(`/reference-notes/${source.id}/knowledge`, 'POST', body); clearReferenceDraft(draftKey); props.onNoteChange(result); }
    }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function applySuggestions(issues: number[]) {
    if (isMaterial || !proposal) return;
    setBusy(true); setError('');
    try {
      const next = await api<ReferenceNote>(`/reference-proposals/${proposal.id}/apply`, 'POST', { revision: source.revision, issues });
      props.onNoteApplied(next);
    } finally { setBusy(false); }
  }
  const pending = busy || proposal?.state === 'running';
  const undecided = data?.concepts.filter(c => !decisions[c.key]).length ?? 0;
  const reviewBlocked = isMaterial && (props.material.state !== 'eligible' || proposal?.state !== 'ready') ? props.material.reason || '현재 자료의 추출·검토를 완료해주세요.' : registrationBlock(proposalId, proposal, source.revision);
  if (source.registration?.version === source.revision && source.registration.state === 'active') return <section className="reference-connected"><span className="eyebrow">CONNECTED</span><h2>개념 지도에 등록했습니다.</h2><p>이 {isMaterial ? '자료' : '노트'} v{source.revision}의 근거와 연결을 보관하고 있습니다.</p><Link className="button" to="/knowledge">지식 그래프 열기</Link></section>;
  return <section className="reference-knowledge">
    <div className="section-heading"><div><span className="eyebrow">CONNECT WITH INTENTION</span><h2>개념 지도에 연결하기</h2></div><span className="reference-version">{isMaterial ? '자료' : '노트'} v{source.revision}</span></div>
    <p>기존 개념, 새로운 주장과 관계를 검토하고 직접 등록하세요. 후보를 준비하는 것만으로 지도에 추가되지는 않습니다.</p>
    {source.registration && <p className="notice">이전 등록은 v{source.registration.version}입니다. 변경된 근거를 확인해 새 버전을 등록해주세요.</p>}
    {!isMaterial && <div className="reference-actions"><Button disabled={pending} onClick={() => void analyze()}>{pending ? '개념 추출·검토 중…' : 'AI로 후보 생성·내용 검토'}</Button><Button disabled={pending} onClick={() => change({ concepts: [blankConcept('c1')], assertions: [] }, {}, {}, {})}>직접 개념 입력</Button></div>}
    <ErrorNotice error={error || proposal?.error || ''} />
    {proposal?.state === 'running' && <p role="status" className="notice">개념과 근거를 추출한 뒤, 별도 검토로 본문과 후보의 정확성을 살피고 있습니다. 다른 페이지로 이동해도 계속 진행됩니다.</p>}
    {!isMaterial && proposal?.review && <ReferenceContentReview key={proposal.id + ':' + source.revision} note={props.note} proposal={proposal} pending={!!pending} onApply={applySuggestions} onEdit={props.onEdit} />}
    {proposal?.state === 'ready' && !proposal.review && <p className="notice">내용 검토 기능 적용 전의 후보입니다. AI 후보를 다시 생성해 검토해주세요.</p>}
    {data && <form onSubmit={e => { e.preventDefault(); void register(); }}>
      <Label className="reference-concept-search">기존 개념 검색<Input value={search} onChange={e => setSearch(e.target.value)} placeholder="개념명 · 정의 · 별칭으로 찾기" maxLength={160} /></Label>
      <fieldset disabled={!!pending}><legend>개념과 근거</legend>
        {data.concepts.map((c, i) => <article className="reference-candidate" key={c.key}>
          <header><strong>개념 {i + 1}</strong><Button type="button" disabled={data.concepts.length === 1} onClick={() => change({ concepts: data.concepts.filter(x => x.key !== c.key), assertions: data.assertions.filter(a => a.subject !== c.key && a.object !== c.key) })}>제외</Button></header>
          <ConceptConnection candidate={c} original={c.existing_id ? originals[c.key] ?? c : c}
            matches={proposal?.revision === source.revision ? (proposal.matches ?? []).filter(m => m.key === c.key) : []}
            selected={c.existing_id ? selected[c.key] ?? concepts.find(x => x.id === c.existing_id) : undefined} decided={!!decisions[c.key]}
            onSelect={target => connect(i, target)} onNew={() => connect(i)} />
          <Label>다른 기존 개념 직접 선택<NativeSelect value={c.existing_id} onChange={e => {
            const found = concepts.find(x => x.id === e.target.value);
            if (found) connect(i, found);
          }}><option value="">검색 결과에서 선택</option>{c.existing_id && !concepts.some(x => x.id === c.existing_id) && <option value={c.existing_id}>{c.pref_label} · 선택된 개념</option>}{concepts.map(x => <option key={x.id} value={x.id}>{x.pref_label} · {x.scope || '범위 미지정'}{x.status === 'provisional' ? ' · 기존 단원' : ''}</option>)}</NativeSelect></Label>
          <div className="reference-fields"><Label>대표명<Input required value={c.pref_label} maxLength={160} readOnly={!!c.existing_id} onChange={e => concept(i, { pref_label: e.target.value })} /></Label><Label>적용 범위<Input maxLength={200} value={c.scope} readOnly={!!c.existing_id && (selected[c.key] ?? concepts.find(x => x.id === c.existing_id))?.status !== 'provisional'} onChange={e => concept(i, { scope: e.target.value })} /></Label></div>
          <Label>정의<Textarea required maxLength={3000} value={c.definition} readOnly={!!c.existing_id && (selected[c.key] ?? concepts.find(x => x.id === c.existing_id))?.status !== 'provisional'} onChange={e => concept(i, { definition: e.target.value })} /></Label>
          {c.existing_id && (selected[c.key] ?? concepts.find(x => x.id === c.existing_id))?.status === 'provisional' && <p className="muted">기존 단원에서 가져온 개념입니다. 이번 근거로 정의를 구체화하면 같은 개념 ID에 반영됩니다.</p>}
          <Label>확인한 별칭 · 쉼표로 구분<Input defaultValue={c.aliases.join(', ')} key={c.key + c.existing_id} maxLength={1200} onBlur={e => concept(i, { aliases: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} /></Label>
          <Label>근거 문장 · 본문에서 그대로 가져오기<Textarea required maxLength={3000} value={c.quote} onChange={e => concept(i, { quote: e.target.value })} /></Label>
          <Label>근거의 성격<NativeSelect value={c.basis} onChange={e => concept(i, { basis: e.target.value as Candidate['basis'] })}>{Object.entries(bases).filter(([k]) => !isMaterial || k !== 'source').map(([k, v]) => <option key={k} value={k}>{isMaterial && k === 'interpretation' ? '해석·설명' : v}</option>)}</NativeSelect></Label>
        </article>)}
        <Button type="button" disabled={data.concepts.length >= 16} onClick={() => change({ ...data, concepts: [...data.concepts, { ...blankConcept('c' + crypto.randomUUID().slice(0, 8)), basis: isMaterial ? 'interpretation' : 'source' }] })}>+ 개념 추가</Button>
      </fieldset>
      <fieldset disabled={!!pending}><legend>주장과 개념 사이의 관계</legend>
        <p className="muted">근거가 있는 관계만 남겨주세요. 상하·선행 관계의 순환은 저장할 수 없습니다.</p>
        {data.assertions.map((a, i) => <article className="reference-candidate" key={i}>
          <header><strong>{relations[a.kind]}</strong><Button type="button" onClick={() => change({ ...data, assertions: data.assertions.filter((_, j) => i !== j) })}>제외</Button></header>
          <Label>관계 종류<NativeSelect value={a.kind} onChange={e => assertion(i, { kind: e.target.value as Assertion['kind'], object: e.target.value === 'CLAIM' ? '' : data.concepts.find(c => c.key !== a.subject)?.key ?? '' })}>{Object.entries(relations).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</NativeSelect></Label>
          <div className="reference-fields"><Label>시작 개념<NativeSelect value={a.subject} onChange={e => assertion(i, { subject: e.target.value })}>{data.concepts.map(c => <option key={c.key} value={c.key}>{c.pref_label || c.key}</option>)}</NativeSelect></Label>
            {a.kind !== 'CLAIM' && <Label>도착 개념<NativeSelect required value={a.object} onChange={e => assertion(i, { object: e.target.value })}><option value="">개념 선택</option>{data.concepts.map(c => <option key={c.key} value={c.key}>{c.pref_label || c.key}</option>)}</NativeSelect></Label>}</div>
          <Label>주장 또는 연결 이유<Textarea required maxLength={3000} value={a.text} onChange={e => assertion(i, { text: e.target.value })} /></Label>
          <Label>적용 조건<Input maxLength={200} value={a.scope} onChange={e => assertion(i, { scope: e.target.value })} /></Label>
          <Label>근거 문장<Textarea required maxLength={3000} value={a.quote} onChange={e => assertion(i, { quote: e.target.value })} /></Label>
          <Label>근거의 성격<NativeSelect value={a.basis} onChange={e => assertion(i, { basis: e.target.value as Assertion['basis'] })}>{Object.entries(bases).filter(([k]) => !isMaterial || k !== 'source').map(([k, v]) => <option key={k} value={k}>{isMaterial && k === 'interpretation' ? '해석·설명' : v}</option>)}</NativeSelect></Label>
          <Label>근거의 방향<NativeSelect value={a.disposition ?? 'supports'} onChange={e => assertion(i, { disposition: e.target.value as Assertion['disposition'] })}><option value="supports">이 주장 / 관계를 지지함</option><option value="refutes">이 주장 / 관계를 반박함</option></NativeSelect></Label>
        </article>)}
        <Button type="button" disabled={data.assertions.length >= 24} onClick={() => change({ ...data, assertions: [...data.assertions, { subject: data.concepts[0].key, kind: 'CLAIM', object: '', text: '', scope: '', quote: '', basis: isMaterial ? 'interpretation' : 'source', disposition: 'supports' }] })}>+ 주장 / 관계 추가</Button>
      </fieldset>
      {undecided > 0 && <p className="notice" role="status">개념 {undecided}개의 등록 방식을 선택해주세요. 기존 개념 연결 또는 별개 개념 추가를 선택하면 등록할 수 있습니다.</p>}
      {reviewBlocked && <div className="notice reference-registration-block" id="reference-registration-block" role="status"><strong>{undecided === 0 ? '개념 선택은 완료됐지만 본문 검토가 남아 있습니다.' : '본문 검토도 완료해야 등록할 수 있습니다.'}</strong><p>{reviewBlocked}</p>{!isMaterial && proposal?.review && <Button type="button" onClick={() => document.getElementById('reference-content-review')?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })}>본문 검토 확인하기 ↑</Button>}</div>}
      <div className="reference-register"><p>선택한 개념 {data.concepts.length}개 · 주장과 관계 {data.assertions.length}개<br /><small>{proposal?.review ? '검토 후 직접 변경한 후보는 등록 전에 다시 확인해주세요.' : 'AI 검토 없이 직접 입력한 내용입니다. 정의와 근거를 확인해주세요.'}</small></p><Button className="primary" aria-describedby={reviewBlocked ? "reference-registration-block" : undefined} disabled={!!pending || !!reviewBlocked || undecided > 0}>검토한 내용으로 개념 지도에 추가하기</Button></div>
    </form>}
  </section>;
}
