import { Select } from './Select';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp } from './App';
import { clearReferenceDraft, bases, relations, type Assertion, type Candidate, type Concept, type Proposal, type ProposalData, type ReferenceNote } from './referenceTypes';

const blankConcept = (key: string): Candidate => ({ key, existing_id: '', pref_label: '', definition: '', scope: '', aliases: [], quote: '', basis: 'source' });

export function ReferenceKnowledge({ note, onRegistered }: { note: ReferenceNote; onRegistered: (note: ReferenceNote) => void }) {
  const { userId } = useApp();
  const [draftKey] = useState(`reference-graph-draft:${userId}:${note.id}:${note.revision}`);
  const [restored] = useState(() => {
    try { const v = JSON.parse(localStorage.getItem(draftKey) ?? 'null'); return v && Array.isArray(v.data?.concepts) && Array.isArray(v.data?.assertions) && typeof v.requestId === 'string' ? v as { data: ProposalData; requestId: string } : null; }
    catch { return null; }
  });
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [search, setSearch] = useState('');
  const [data, setData] = useState<ProposalData | null>(restored?.data ?? null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [proposalId, setProposalId] = useState(note.proposal?.revision === note.revision ? note.proposal.id : '');
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
        else if (result.data) setData(current => current ?? result.data);
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    };
    void load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [proposalId]);
  function change(next: ProposalData) {
    const requestId = crypto.randomUUID(); setData(next); setRequestId(requestId);
    try { localStorage.setItem(draftKey, JSON.stringify({ data: next, requestId })); }
    catch { setError('후보를 브라우저에 임시 저장하지 못했습니다. 화면을 이동하기 전에 등록해주세요.'); }
  }
  function concept(index: number, patch: Partial<Candidate>) { if (data) change({ ...data, concepts: data.concepts.map((c, i) => i === index ? { ...c, ...patch } : c) }); }
  function assertion(index: number, patch: Partial<Assertion>) { if (data) change({ ...data, assertions: data.assertions.map((a, i) => i === index ? { ...a, ...patch } : a) }); }
  async function analyze() {
    setBusy(true); setError('');
    try { const result = await api<Proposal>(`/reference-notes/${note.id}/proposals`, 'POST', { revision: note.revision }); setData(null); clearReferenceDraft(draftKey); setProposal(result); setProposalId(result.id); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function register() {
    setBusy(true); setError('');
    try { const result = await api<ReferenceNote>(`/reference-notes/${note.id}/knowledge`, 'POST', { revision: note.revision, request_id: requestId, proposal_id: proposal?.state === 'ready' ? proposal.id : null, data }); clearReferenceDraft(draftKey); onRegistered(result); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const pending = busy || proposal?.state === 'running';
  if (note.registration?.version === note.revision && note.registration.state === 'active') return <section className="reference-connected"><span className="eyebrow">CONNECTED</span><h2>개념 지도에 등록했습니다.</h2><p>이 노트 v{note.revision}의 근거와 연결을 보관하고 있습니다.</p><Link className="button" to="/knowledge">지식 그래프 열기 ↗</Link></section>;
  return <section className="reference-knowledge">
    <div className="section-heading"><div><span className="eyebrow">CONNECT WITH INTENTION</span><h2>개념 지도에 연결하기</h2></div><span className="reference-version">노트 v{note.revision}</span></div>
    <p>기존 개념, 새로운 주장과 관계를 검토하고 직접 등록하세요. 후보를 준비하는 것만으로 지도에 추가되지는 않습니다.</p>
    {note.registration && <p className="notice">이전 등록은 v{note.registration.version}입니다. 변경된 근거를 확인해 새 버전을 등록해주세요.</p>}
    <div className="reference-actions"><button disabled={pending} onClick={() => void analyze()}>{pending ? '후보 준비 중…' : 'AI로 연결 후보 준비'}</button><button disabled={pending} onClick={() => change({ concepts: [blankConcept('c1')], assertions: [] })}>직접 개념 입력</button></div>
    <ErrorNotice error={error || proposal?.error || ''} />
    {proposal?.state === 'running' && <p role="status" className="notice">노트에서 개념과 근거를 찾고 있습니다. 다른 페이지로 이동해도 계속 진행됩니다.</p>}
    {data && <form onSubmit={e => { e.preventDefault(); void register(); }}>
      <label className="reference-concept-search">기존 개념 검색<input value={search} onChange={e => setSearch(e.target.value)} placeholder="개념명 · 정의 · 별칭으로 찾기" maxLength={160} /></label>
      <fieldset disabled={!!pending}><legend>개념과 근거</legend>
        {data.concepts.map((c, i) => <article className="reference-candidate" key={c.key}>
          <header><strong>개념 {i + 1}</strong><button type="button" disabled={data.concepts.length === 1} onClick={() => change({ concepts: data.concepts.filter(x => x.key !== c.key), assertions: data.assertions.filter(a => a.subject !== c.key && a.object !== c.key) })}>제외</button></header>
          <label>연결할 개념<Select value={c.existing_id} onChange={e => {
            const found = concepts.find(x => x.id === e.target.value);
            concept(i, found ? { existing_id: found.id, pref_label: found.pref_label, definition: found.definition, scope: found.scope, aliases: [] } : { existing_id: '' });
          }}><option value="">새 개념으로 등록</option>{c.existing_id && !concepts.some(x => x.id === c.existing_id) && <option value={c.existing_id}>{c.pref_label} · 선택된 개념</option>}{concepts.map(x => <option key={x.id} value={x.id}>{x.pref_label} · {x.scope || '범위 미지정'}{x.status === 'provisional' ? ' · 기존 단원' : ''}</option>)}</Select></label>
          <div className="reference-fields"><label>대표명<input required value={c.pref_label} maxLength={160} readOnly={!!c.existing_id} onChange={e => concept(i, { pref_label: e.target.value })} /></label><label>적용 범위<input maxLength={200} value={c.scope} readOnly={!!c.existing_id && concepts.find(x => x.id === c.existing_id)?.status !== 'provisional'} onChange={e => concept(i, { scope: e.target.value })} /></label></div>
          <label>정의<textarea required maxLength={3000} value={c.definition} readOnly={!!c.existing_id && concepts.find(x => x.id === c.existing_id)?.status !== 'provisional'} onChange={e => concept(i, { definition: e.target.value })} /></label>
          {concepts.find(x => x.id === c.existing_id)?.status === 'provisional' && <p className="muted">기존 단원에서 가져온 개념입니다. 이번 근거로 정의를 구체화하면 같은 개념 ID에 반영됩니다.</p>}
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
      <div className="reference-register"><p>선택한 개념 {data.concepts.length}개 · 주장과 관계 {data.assertions.length}개<br /><small>등록은 숙달이나 문제 통과를 의미하지 않습니다.</small></p><button className="primary" disabled={!!pending}>검토한 내용으로 개념 지도에 추가하기</button></div>
    </form>}
  </section>;
}
