import { ConceptConnection } from './ConceptConnection';
import { Select } from './Select';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Markdown } from './Markdown';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp } from './App';
import { clearReferenceDraft, bases, relations, type Assertion, type Candidate, type Concept, type Proposal, type ProposalData, type ReferenceNote } from './referenceTypes';

type ConnectionDraft = { data: ProposalData; requestId: string; decisions?: Record<string, boolean>; originals?: Record<string, Candidate>; selected?: Record<string, Concept> };
const unlinked = (data: ProposalData): ProposalData => ({ ...data, concepts: data.concepts.map(c => ({ ...c, existing_id: '' })) });
const blankConcept = (key: string): Candidate => ({ key, existing_id: '', pref_label: '', definition: '', scope: '', aliases: [], quote: '', basis: 'source' });

export function ReferenceKnowledge({ note, onNoteChange, onEdit }: { note: ReferenceNote; onNoteChange: (note: ReferenceNote) => void; onEdit: () => void }) {
  const { userId } = useApp();
  const [draftKey] = useState(`reference-graph-draft:${userId}:${note.id}:${note.revision}`);
  const [restored] = useState(() => {
    try { const v = JSON.parse(localStorage.getItem(draftKey) ?? 'null'); return v && Array.isArray(v.data?.concepts) && Array.isArray(v.data?.assertions) && typeof v.requestId === 'string' ? v as ConnectionDraft : null; }
    catch { return null; }
  });
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [search, setSearch] = useState('');
  const [data, setData] = useState<ProposalData | null>(restored?.data ?? null);
  const [decisions, setDecisions] = useState<Record<string, boolean>>(restored?.decisions ?? {});
  const [originals, setOriginals] = useState<Record<string, Candidate>>(restored?.originals ?? {});
  const [selected, setSelected] = useState<Record<string, Concept>>(restored?.selected ?? {});
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [proposalId, setProposalId] = useState(note.proposal?.id ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [requestId, setRequestId] = useState<string>(restored?.requestId ?? crypto.randomUUID());
  useEffect(() => {
    const controller = new AbortController();
    api<Concept[]>('/knowledge/concepts?q=' + encodeURIComponent(search), 'GET', undefined, controller.signal).then(setConcepts).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); });
    return () => controller.abort();
  }, [search]);
  useEffect(() => {
    if (!proposalId) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const result = await api<Proposal>('/reference-proposals/' + proposalId, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setProposal(result);
        if (result.state === 'running') timer = setTimeout(() => void load(), 1500);
        else if (result.data && result.revision === note.revision) setData(current => current ?? unlinked(result.data!));
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    };
    void load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [proposalId, note.revision]);
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
    setBusy(true); setError('');
    try { const result = await api<Proposal>(`/reference-notes/${note.id}/proposals`, 'POST', { revision: note.revision }); setData(result.data ? unlinked(result.data) : null); setDecisions({}); setOriginals({}); setSelected({}); setRequestId(crypto.randomUUID()); clearReferenceDraft(draftKey); setProposal(result); setProposalId(result.id); onNoteChange({ ...note, proposal: { id: result.id, state: result.state, revision: result.revision } }); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function register() {
    if (data?.concepts.some(c => !decisions[c.key])) { setError('각 개념의 등록 방식을 먼저 선택해주세요.'); return; }
    setBusy(true); setError('');
    try { const result = await api<ReferenceNote>(`/reference-notes/${note.id}/knowledge`, 'POST', { revision: note.revision, request_id: requestId, proposal_id: proposal?.state === 'ready' ? proposal.id : null, data }); clearReferenceDraft(draftKey); onNoteChange(result); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const pending = busy || proposal?.state === 'running';
  const undecided = data?.concepts.filter(c => !decisions[c.key]).length ?? 0;
  const reviewBlocked = !!proposalId && (!proposal?.review || proposal.state !== 'ready' || proposal.revision !== note.revision || proposal.review.issues.length > 0);
  if (note.registration?.version === note.revision && note.registration.state === 'active') return <section className="reference-connected"><span className="eyebrow">CONNECTED</span><h2>개념 지도에 등록했습니다.</h2><p>이 노트 v{note.revision}의 근거와 연결을 보관하고 있습니다.</p><Link className="button" to="/knowledge">지식 그래프 열기 ↗</Link></section>;
  return <section className="reference-knowledge">
    <div className="section-heading"><div><span className="eyebrow">CONNECT WITH INTENTION</span><h2>개념 지도에 연결하기</h2></div><span className="reference-version">노트 v{note.revision}</span></div>
    <p>기존 개념, 새로운 주장과 관계를 검토하고 직접 등록하세요. 후보를 준비하는 것만으로 지도에 추가되지는 않습니다.</p>
    {note.registration && <p className="notice">이전 등록은 v{note.registration.version}입니다. 변경된 근거를 확인해 새 버전을 등록해주세요.</p>}
    <div className="reference-actions"><button disabled={pending} onClick={() => void analyze()}>{pending ? '개념 추출·검토 중…' : 'AI로 후보 생성·내용 검토'}</button><button disabled={pending} onClick={() => change({ concepts: [blankConcept('c1')], assertions: [] }, {}, {}, {})}>직접 개념 입력</button></div>
    <ErrorNotice error={error || proposal?.error || ''} />
    {proposal?.state === 'running' && <p role="status" className="notice">개념과 근거를 추출한 뒤, 별도 검토로 본문과 후보의 정확성을 살피고 있습니다. 다른 페이지로 이동해도 계속 진행됩니다.</p>}
    {proposal?.review && <section className="reference-content-review" aria-label="AI 내용 검토" aria-live="polite">
      <header><span className="eyebrow">CONTENT REVIEW · v{proposal.revision}</span><h3>{proposal.review.issues.length ? '본문에서 먼저 확인할 내용이 있습니다.' : '검토 범위에서 수정할 오류를 발견하지 못했습니다.'}</h3></header>
      <Markdown language="">{proposal.review.summary}</Markdown>
      <p className="muted">AI의 지식에 기반한 검토입니다. 원문 자료나 최신 정보를 외부에서 확인한 결과는 아니며, 정확성을 보장하지 않습니다.</p>
      {proposal.revision !== note.revision && <p className="notice">이전 v{proposal.revision}의 검토입니다. 저장한 v{note.revision}에서 AI 후보 생성·내용 검토를 다시 진행해주세요.</p>}
      {proposal.review.issues.map((issue, i) => <article className="reference-review-issue" key={i}>
        <h4><span>{i + 1}</span>{issue.kind === 'correction_needed' ? '수정 필요' : '추가 확인 필요'}</h4>
        <blockquote>{issue.quote}</blockquote>
        <dl><dt>검토 이유</dt><dd><Markdown language="">{issue.explanation}</Markdown></dd><dt>수정·확인 제안</dt><dd><Markdown language="">{issue.suggestion}</Markdown></dd></dl>
      </article>)}
      {proposal.review.issues.length > 0 && <footer><p>제안을 검토해 본문을 수정하고 저장한 뒤 다시 검토해주세요. 수정한 내용을 근거로 개념 지도에 등록합니다.</p><button type="button" onClick={onEdit}>본문 수정하러 가기</button></footer>}
    </section>}
    {proposal?.state === 'ready' && !proposal.review && <p className="notice">내용 검토 기능 적용 전의 후보입니다. AI 후보를 다시 생성해 검토해주세요.</p>}
    {data && <form onSubmit={e => { e.preventDefault(); void register(); }}>
      <label className="reference-concept-search">기존 개념 검색<input value={search} onChange={e => setSearch(e.target.value)} placeholder="개념명 · 정의 · 별칭으로 찾기" maxLength={160} /></label>
      <fieldset disabled={!!pending}><legend>개념과 근거</legend>
        {data.concepts.map((c, i) => <article className="reference-candidate" key={c.key}>
          <header><strong>개념 {i + 1}</strong><button type="button" disabled={data.concepts.length === 1} onClick={() => change({ concepts: data.concepts.filter(x => x.key !== c.key), assertions: data.assertions.filter(a => a.subject !== c.key && a.object !== c.key) })}>제외</button></header>
          <ConceptConnection candidate={c} original={c.existing_id ? originals[c.key] ?? c : c}
            matches={proposal?.revision === note.revision ? (proposal.matches ?? []).filter(m => m.key === c.key) : []}
            selected={c.existing_id ? selected[c.key] ?? concepts.find(x => x.id === c.existing_id) : undefined} decided={!!decisions[c.key]}
            onSelect={target => connect(i, target)} onNew={() => connect(i)} />
          <label>다른 기존 개념 직접 선택<Select value={c.existing_id} onChange={e => {
            const found = concepts.find(x => x.id === e.target.value);
            if (found) connect(i, found);
          }}><option value="">검색 결과에서 선택</option>{c.existing_id && !concepts.some(x => x.id === c.existing_id) && <option value={c.existing_id}>{c.pref_label} · 선택된 개념</option>}{concepts.map(x => <option key={x.id} value={x.id}>{x.pref_label} · {x.scope || '범위 미지정'}{x.status === 'provisional' ? ' · 기존 단원' : ''}</option>)}</Select></label>
          <div className="reference-fields"><label>대표명<input required value={c.pref_label} maxLength={160} readOnly={!!c.existing_id} onChange={e => concept(i, { pref_label: e.target.value })} /></label><label>적용 범위<input maxLength={200} value={c.scope} readOnly={!!c.existing_id && (selected[c.key] ?? concepts.find(x => x.id === c.existing_id))?.status !== 'provisional'} onChange={e => concept(i, { scope: e.target.value })} /></label></div>
          <label>정의<textarea required maxLength={3000} value={c.definition} readOnly={!!c.existing_id && (selected[c.key] ?? concepts.find(x => x.id === c.existing_id))?.status !== 'provisional'} onChange={e => concept(i, { definition: e.target.value })} /></label>
          {c.existing_id && (selected[c.key] ?? concepts.find(x => x.id === c.existing_id))?.status === 'provisional' && <p className="muted">기존 단원에서 가져온 개념입니다. 이번 근거로 정의를 구체화하면 같은 개념 ID에 반영됩니다.</p>}
          <label>확인한 별칭 · 쉼표로 구분<input defaultValue={c.aliases.join(', ')} key={c.key + c.existing_id} maxLength={1200} onBlur={e => concept(i, { aliases: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} /></label>
          <label>근거 문장 · 본문에서 그대로 가져오기<textarea required maxLength={3000} value={c.quote} onChange={e => concept(i, { quote: e.target.value })} /></label>
          <label>근거의 성격<Select value={c.basis} onChange={e => concept(i, { basis: e.target.value as Candidate['basis'] })}>{Object.entries(bases).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></label>
        </article>)}
        <button type="button" disabled={data.concepts.length >= 16} onClick={() => change({ ...data, concepts: [...data.concepts, blankConcept('c' + crypto.randomUUID().slice(0, 8))] })}>+ 개념 추가</button>
      </fieldset>
      <fieldset disabled={!!pending}><legend>주장과 개념 사이의 관계</legend>
        <p className="muted">근거가 있는 관계만 남겨주세요. 상하·선행 관계의 순환은 저장할 수 없습니다.</p>
        {data.assertions.map((a, i) => <article className="reference-candidate" key={i}>
          <header><strong>{relations[a.kind]}</strong><button type="button" onClick={() => change({ ...data, assertions: data.assertions.filter((_, j) => i !== j) })}>제외</button></header>
          <label>관계 종류<Select value={a.kind} onChange={e => assertion(i, { kind: e.target.value as Assertion['kind'], object: e.target.value === 'CLAIM' ? '' : data.concepts.find(c => c.key !== a.subject)?.key ?? '' })}>{Object.entries(relations).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></label>
          <div className="reference-fields"><label>시작 개념<Select value={a.subject} onChange={e => assertion(i, { subject: e.target.value })}>{data.concepts.map(c => <option key={c.key} value={c.key}>{c.pref_label || c.key}</option>)}</Select></label>
            {a.kind !== 'CLAIM' && <label>도착 개념<Select required value={a.object} onChange={e => assertion(i, { object: e.target.value })}><option value="">개념 선택</option>{data.concepts.map(c => <option key={c.key} value={c.key}>{c.pref_label || c.key}</option>)}</Select></label>}</div>
          <label>주장 또는 연결 이유<textarea required maxLength={3000} value={a.text} onChange={e => assertion(i, { text: e.target.value })} /></label>
          <label>적용 조건<input maxLength={200} value={a.scope} onChange={e => assertion(i, { scope: e.target.value })} /></label>
          <label>근거 문장<textarea required maxLength={3000} value={a.quote} onChange={e => assertion(i, { quote: e.target.value })} /></label>
          <label>근거의 성격<Select value={a.basis} onChange={e => assertion(i, { basis: e.target.value as Assertion['basis'] })}>{Object.entries(bases).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></label>
          <label>근거의 방향<Select value={a.disposition ?? 'supports'} onChange={e => assertion(i, { disposition: e.target.value as Assertion['disposition'] })}><option value="supports">이 주장 / 관계를 지지함</option><option value="refutes">이 주장 / 관계를 반박함</option></Select></label>
        </article>)}
        <button type="button" disabled={data.assertions.length >= 24} onClick={() => change({ ...data, assertions: [...data.assertions, { subject: data.concepts[0].key, kind: 'CLAIM', object: '', text: '', scope: '', quote: '', basis: 'source', disposition: 'supports' }] })}>+ 주장 / 관계 추가</button>
      </fieldset>
      {undecided > 0 && <p className="notice" role="status">개념 {undecided}개의 등록 방식을 선택해주세요. 기존 개념 연결 또는 별개 개념 추가를 선택하면 등록할 수 있습니다.</p>}
      <div className="reference-register"><p>선택한 개념 {data.concepts.length}개 · 주장과 관계 {data.assertions.length}개<br /><small>{proposal?.review ? '검토 후 직접 변경한 후보는 등록 전에 다시 확인해주세요.' : 'AI 검토 없이 직접 입력한 내용입니다. 정의와 근거를 확인해주세요.'}</small></p><button className="primary" disabled={!!pending || reviewBlocked || undecided > 0}>검토한 내용으로 개념 지도에 추가하기</button></div>
    </form>}
  </section>;
}
