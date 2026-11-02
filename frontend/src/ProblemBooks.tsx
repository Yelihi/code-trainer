import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import CodeMirror from '@uiw/react-codemirror';
import { api, errorMessage, languages, timestamp, type Language } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Markdown } from './Markdown';
import { codeExtensions } from './CodeBlock';
import { Button } from './components/ui/button';
import { Checkbox } from './components/ui/checkbox';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { NativeSelect } from './components/ui/native-select';
import { Textarea } from './components/ui/textarea';
import './problemBooks.css';

type TestCase = { stdin: string; expected: string; public: boolean };
type Check = TestCase & { passed: boolean; status: string; actual: string };
type Verification = { status: string; stderr: string; tests: (Check | { passed: boolean; status: string; public: false })[] };
type Problem = { id: string; revision: number; current_revision: number; archived: boolean; title: string; kind: 'text' | 'code'; language: Language | null; prompt: string; answer?: string; explanation?: string; cases: TestCase[]; verified: boolean; source_name: string; source_location: string; resource_id: string | null };
type ProblemDraft = Omit<Problem, 'id' | 'current_revision' | 'archived'>;
type Book = { id: string; title: string; description: string; language: Language | null; revision: number; archived: boolean; problem_ids: string[]; problems: Problem[] };
type CatalogItem = { id: string; title: string; language: Language | null; source: 'manual' | 'generated' | 'foundation' | 'worksheet'; href: string; count: number; solved?: number; due?: number; archived: boolean };
type Attempt = { id: string; answer: string; problem_revision: number; assessment: 'understood' | 'retry' | null; result?: Verification | null; created_at: string };
const sourceLabels = { manual: '직접 구성', generated: '생성된 코드 문제', foundation: '자료구조 · 알고리즘', worksheet: 'AI 질문지' };
const emptyProblem: ProblemDraft = { title: '', kind: 'text', language: null, prompt: '', answer: '', cases: [], verified: false, explanation: '', source_name: '', source_location: '', resource_id: null, revision: 0 };

export function ProblemBookCatalog() {
  const { userId } = useApp();
  return <Catalog key={userId} />;
}
function Catalog() {
  const { data, error, reload } = useResource<{ items: CatalogItem[] }>('/problem-books/catalog');
  const [params, setParams] = useSearchParams();
  const language = params.get('language') ?? 'all';
  const visible = data?.items.filter(item => !item.archived && (language === 'all' || (language === 'general' ? !item.language : item.language === language))) ?? [];
  return <main className="page problem-books-page"><div className="breadcrumb">탐구하기<span>/</span>문제집</div>
    <header className="reference-page-heading"><div><h1>문제집</h1><p>만든 문제와 기존 학습 문제를 언어별로 찾아 풀어보세요.</p></div><div className="reference-actions"><Link className="button" to="/problem-books/problems">문제 보관함</Link><Link className="button primary" to="/problem-books/new">문제집 구성</Link></div></header>
    <div className="problem-books-filter"><Label htmlFor="problem-language">언어</Label><NativeSelect id="problem-language" value={language} onChange={e => setParams(e.target.value === 'all' ? {} : { language: e.target.value })}><option value="all">전체</option>{Object.entries(languages).map(([key, label]) => <option value={key} key={key}>{label}</option>)}<option value="general">언어 무관</option></NativeSelect></div>
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}{!data && !error && <p role="status">문제집을 불러오는 중…</p>}
    {data && (!visible.length ? <section className="reference-empty"><h2>해당 언어의 문제집이 없습니다.</h2><p>문제를 만든 뒤 문제집에 담거나 다른 언어를 선택해보세요.</p></section> : <div className="problem-books-list">{visible.map(item => <Link className="problem-book-row" key={item.source + item.id} to={item.href}><div><small>{sourceLabels[item.source]} · {item.language ? languages[item.language] : '언어 무관'}</small><h2>{item.title}</h2><p>{item.source === 'worksheet' ? '질문지 열기' : `${item.count}개 문제`}{item.source === 'manual' && ` · ${item.solved}개 풀이 · 복습 ${item.due}개`}</p></div><span>열기</span></Link>)}</div>)}
  </main>;
}

export function ProblemBank() {
  const { data, error, reload } = useResource<{ items: Problem[] }>('/manual-problems');
  const [actionError, setActionError] = useState('');
  async function archive(id: string) { if (!window.confirm('문제를 보관할까요? 이전 풀이 기록은 남습니다.')) return; try { await api('/manual-problems/' + id + '/archive', 'POST', {}); reload(); } catch (e) { setActionError(errorMessage(e)); } }
  return <main className="page problem-books-page"><div className="breadcrumb"><Link to="/problem-books">문제집</Link><span>/</span>문제 보관함</div><header className="reference-page-heading"><div><h1>문제 보관함</h1><p>문제를 먼저 만들고, 필요한 문제집에 골라 담으세요.</p></div><Link className="button primary" to="/problem-books/problems/new">문제 만들기</Link></header><ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    <ErrorNotice error={actionError} /><div className="problem-books-list">{data?.items.filter(p => !p.archived).map(p => <div className="problem-bank-row" key={p.id}><Link className="problem-book-row" to={'/problem-books/problems/' + p.id + '/edit'}><div><small>{p.kind === 'code' ? p.verified ? '코드 · 검증됨' : '코드 · 검증 필요' : '서술'} · {p.language ? languages[p.language] : '언어 무관'} · v{p.revision}</small><h2>{p.title}</h2><p>{p.source_name}{p.source_location && ` · ${p.source_location}`}</p></div><span>편집</span></Link>{(p.kind !== 'code' || p.verified) && <Link className="button" to={'/problem-books/problems/' + p.id + '/solve'}>풀기</Link>}<Button onClick={() => void archive(p.id)}>보관</Button></div>)}</div>{data && !data.items.some(p => !p.archived) && <p className="empty-state">아직 만든 문제가 없습니다.</p>}
  </main>;
}

export function ProblemEditor() {
  const { id } = useParams();
  return <ProblemEditorContent key={id ?? 'new'} id={id} />;
}
function ProblemEditorContent({ id }: { id?: string }) {
  const { data: bank, error } = useResource<{ items: Problem[] }>('/manual-problems');
  const existing = id ? bank?.items.find(p => p.id === id) : null;
  if (!bank || (id && !existing)) return <main className="page"><ErrorNotice error={error || (bank && id ? '문제를 찾을 수 없습니다.' : '')} />{!error && !bank && <p>문제를 불러오는 중…</p>}</main>;
  return <ProblemForm key={id ?? 'new'} initial={existing ?? emptyProblem} id={id} />;
}
function ProblemForm({ initial, id }: { initial: ProblemDraft; id?: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState<ProblemDraft>(initial), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [verification, setVerification] = useState<Verification | null>((location.state as { verification?: Verification } | null)?.verification ?? null);
  const [search, setSearch] = useState('');
  const { data: resources } = useResource<{ items: { id: string; name: string }[] }>('/resources?q=' + encodeURIComponent(search));
  function updateCase(index: number, change: Partial<TestCase>) { setForm(previous => ({ ...previous, cases: previous.cases.map((item, position) => position === index ? { ...item, ...change } : item) })); setVerification(null); }
  async function save(verify = false) {
    if (!form.answer?.trim()) { setError('정답을 입력해주세요.'); return; }
    setBusy(true); setError('');
    const body = { title: form.title, kind: form.kind, language: form.language, prompt: form.prompt, answer: form.answer,
      cases: form.cases, explanation: form.explanation, source_name: form.source_name, source_location: form.source_location,
      resource_id: form.resource_id, revision: form.revision };
    try {
      if (verify && form.kind === 'code') {
        const checked = await api<{ problem: Problem; result: Verification }>('/manual-problems/verify', 'POST', { id, problem: body });
        if (checked.result.status === 'passed') navigate('/problem-books/problems');
        else if (!id) navigate('/problem-books/problems/' + checked.problem.id + '/edit', { replace: true, state: { verification: checked.result } });
        else { setForm(checked.problem); setVerification(checked.result); }
      } else { await api(id ? '/manual-problems/' + id : '/manual-problems', id ? 'PUT' : 'POST', body); navigate('/problem-books/problems'); }
    }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <main className="page problem-books-page problem-form"><div className="breadcrumb"><Link to="/problem-books/problems">문제 보관함</Link><span>/</span>{id ? '문제 수정' : '문제 만들기'}</div><h1>{id ? '문제 수정' : '문제 만들기'}</h1><p>정답은 풀이를 저장한 뒤에만 표시됩니다. 수정 전 풀이에는 이전 버전이 남습니다.</p><ErrorNotice error={error} />
    <form onSubmit={e => { e.preventDefault(); void save(); }}><Label>제목<Input required maxLength={160} value={form.title} onChange={e => { setForm({ ...form, title: e.target.value }); setVerification(null); }} /></Label>
      <div className="problem-form-pair"><div><Label htmlFor="problem-kind">답변 유형</Label><NativeSelect id="problem-kind" value={form.kind} onChange={e => { setForm({ ...form, kind: e.target.value as 'text' | 'code', cases: e.target.value === 'text' ? [] : form.cases }); setVerification(null); }}><option value="text">서술형</option><option value="code">코드형</option></NativeSelect></div><div><Label htmlFor="problem-language-input">언어</Label><NativeSelect id="problem-language-input" value={form.language ?? ''} onChange={e => { setForm({ ...form, language: e.target.value as Language || null }); setVerification(null); }}><option value="">언어 무관</option>{Object.entries(languages).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</NativeSelect></div></div>
      <Label>문제 본문<Textarea required rows={8} maxLength={20000} value={form.prompt} onChange={e => { setForm({ ...form, prompt: e.target.value }); setVerification(null); }} /></Label>
      {form.kind === 'code' ? <div className="problem-code-answer"><Label htmlFor="problem-code-answer">정답 코드 · {form.language ? languages[form.language] : '언어 선택 필요'}</Label><CodeMirror key={form.language} value={form.answer ?? ''} theme="dark" extensions={codeExtensions(form.language ?? '', true)} height="300px" onChange={answer => { setForm(previous => ({ ...previous, answer: answer.slice(0, 20000) })); setVerification(null); }} onCreateEditor={view => { view.contentDOM.id = 'problem-code-answer'; view.contentDOM.setAttribute('aria-label', '정답 코드'); }} /><small>{(form.answer ?? '').length.toLocaleString()} / 20,000자</small></div> : <Label>정답<Textarea required rows={8} maxLength={20000} value={form.answer ?? ''} onChange={e => { setForm({ ...form, answer: e.target.value }); setVerification(null); }} /></Label>}
      {form.kind === 'code' && <section className="problem-test-cases"><div className="problem-test-heading"><div><h2>실행 사례</h2><p>입력을 표준 입력으로 전달하고 출력 결과를 비교합니다. 공개 사례를 포함해 2개 이상 작성하세요.</p></div><Button type="button" disabled={form.cases.length >= 8} onClick={() => { setForm({ ...form, cases: [...form.cases, { stdin: '', expected: '', public: true }] }); setVerification(null); }}>사례 추가</Button></div>{form.cases.map((item, index) => <div className="problem-test-row" key={index}><div className="problem-test-row-heading"><h3>사례 {index + 1}</h3><Button type="button" onClick={() => { setForm({ ...form, cases: form.cases.filter((_, position) => position !== index) }); setVerification(null); }}>삭제</Button></div><div className="problem-form-pair"><Label>입력 (stdin)<Textarea rows={3} maxLength={6000} value={item.stdin} onChange={e => updateCase(index, { stdin: e.target.value })} /></Label><Label>기대 출력 (stdout)<Textarea rows={3} maxLength={6000} value={item.expected} onChange={e => updateCase(index, { expected: e.target.value })} /></Label></div><Label className="problem-test-public"><Checkbox checked={item.public} onCheckedChange={checked => updateCase(index, { public: checked === true })} />풀이 전에 보여줄 공개 사례</Label></div>)}{!form.cases.length && <p className="muted">아직 실행 사례가 없습니다.</p>}{verification && <VerificationView result={verification} author />}</section>}
      <Label>해설 (선택)<Textarea rows={5} maxLength={20000} value={form.explanation ?? ''} onChange={e => setForm({ ...form, explanation: e.target.value })} /></Label>
      <div className="problem-form-pair"><Label>교재·강좌명 (선택)<Input maxLength={255} value={form.source_name} onChange={e => setForm({ ...form, source_name: e.target.value })} /></Label><Label>장·페이지 (선택)<Input maxLength={160} value={form.source_location} onChange={e => setForm({ ...form, source_location: e.target.value })} /></Label></div>
      <div><Label htmlFor="problem-resource-search">보관된 자료 연결 (선택)</Label><Input id="problem-resource-search" type="search" placeholder="자료 제목 검색" value={search} onChange={e => setSearch(e.target.value)} /><Label className="sr-only" htmlFor="problem-resource">연결할 자료</Label><NativeSelect id="problem-resource" value={form.resource_id ?? ''} onChange={e => setForm({ ...form, resource_id: e.target.value || null })}><option value="">연결하지 않음</option>{form.resource_id && !resources?.items.some(r => r.id === form.resource_id) && <option value={form.resource_id}>현재 연결된 자료</option>}{resources?.items.map(r => <option value={r.id} key={r.id}>{r.name}</option>)}</NativeSelect></div>
      <div className="reference-actions"><Link className="button" to="/problem-books/problems">돌아가기</Link><Button disabled={busy}>{busy ? '저장 중…' : form.kind === 'code' ? '초안 저장' : '문제 저장'}</Button>{form.kind === 'code' && <Button type="button" className="primary" disabled={busy} onClick={() => void save(true)}>{busy ? '검증 중…' : '정답 검증·공개'}</Button>}</div></form>
  </main>;
}

function VerificationView({ result, author = false, preview = false }: { result: Verification; author?: boolean; preview?: boolean }) {
  const passed = result.status === 'passed';
  return <div className="problem-verification" role="status"><h3>{passed ? preview ? '공개 사례 통과' : '모든 실행 사례 통과' : result.status === 'incomplete' ? '실행 사례가 더 필요합니다' : result.status === 'unavailable' ? '실행기를 사용할 수 없습니다' : '실행 사례를 통과하지 못했습니다'}</h3>
    {result.stderr && <pre className="problem-execution-error">{result.stderr}</pre>}
    {!!result.tests.length && <ol>{result.tests.map((item, index) => <li key={index}><strong>{item.public ? `사례 ${index + 1}` : `비공개 사례 ${index + 1}`} · {item.passed ? '통과' : item.status === 'not_run' ? '실행 안 됨' : item.status === 'ok' ? '출력 불일치' : item.status}</strong>{(author || item.public) && 'actual' in item && <div className="problem-test-output"><div><span>기대 출력</span><pre>{item.expected || '(출력 없음)'}</pre></div><div><span>실제 출력</span><pre>{item.actual || '(출력 없음)'}</pre></div></div>}</li>)}</ol>}
  </div>;
}

export function BookEditor() {
  const { id } = useParams();
  const { data: book, error: bookError } = useResource<Book>(id ? '/problem-books/' + id : '/problem-books');
  const { data: bank, error: bankError } = useResource<{ items: Problem[] }>('/manual-problems');
  if (!bank || (id && !book)) return <main className="page"><ErrorNotice error={bankError || bookError} />{!bankError && !bookError && <p>에디터를 불러오는 중…</p>}</main>;
  return <BookForm key={id ?? 'new'} id={id} initial={id ? book! : { title: '', description: '', language: null, revision: 0, problem_ids: [] }} problems={bank.items.filter(p => !p.archived)} />;
}
function BookForm({ id, initial, problems }: { id?: string; initial: Pick<Book, 'title' | 'description' | 'language' | 'revision' | 'problem_ids'>; problems: Problem[] }) {
  const navigate = useNavigate();
  const [form, setForm] = useState(initial), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const available = problems.filter(p => !form.problem_ids.includes(p.id) && (p.kind !== 'code' || p.verified) && (!form.language || !p.language || p.language === form.language));
  async function save() {
    setBusy(true); setError('');
    try { const saved = await api<Book>(id ? '/problem-books/' + id : '/problem-books', id ? 'PUT' : 'POST', form); navigate('/problem-books/' + saved.id); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  function move(index: number, delta: number) { const ids = [...form.problem_ids], next = index + delta; [ids[index], ids[next]] = [ids[next], ids[index]]; setForm({ ...form, problem_ids: ids }); }
  return <main className="page problem-books-page"><div className="breadcrumb"><Link to="/problem-books">문제집</Link><span>/</span>{id ? '문제집 편집' : '문제집 구성'}</div><header className="reference-page-heading"><div><h1>문제집 구성</h1><p>보관함의 문제를 골라 순서를 정하세요. 같은 문제를 여러 문제집에 담을 수 있습니다.</p></div><Link className="button" to="/problem-books/problems/new">새 문제 만들기</Link></header><ErrorNotice error={error} />
    <form className="problem-book-editor" onSubmit={e => { e.preventDefault(); void save(); }}><Label>문제집 제목<Input required maxLength={160} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></Label><Label>설명 (선택)<Textarea rows={3} maxLength={2000} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></Label><div><Label htmlFor="book-language-input">언어</Label><NativeSelect id="book-language-input" value={form.language ?? ''} onChange={e => setForm({ ...form, language: e.target.value as Language || null })}><option value="">언어 무관</option>{Object.entries(languages).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</NativeSelect></div>
      <section><h2>담은 문제 · {form.problem_ids.length}</h2><ol className="problem-selected">{form.problem_ids.map((key, index) => <li key={key}><span>{problems.find(p => p.id === key)?.title ?? '보관된 문제'}</span><div><Button type="button" disabled={index === 0} aria-label={`${index + 1}번 문제 위로`} onClick={() => move(index, -1)}>위</Button><Button type="button" disabled={index === form.problem_ids.length - 1} aria-label={`${index + 1}번 문제 아래로`} onClick={() => move(index, 1)}>아래</Button><Button type="button" onClick={() => setForm({ ...form, problem_ids: form.problem_ids.filter(id => id !== key) })}>빼기</Button></div></li>)}</ol>{!form.problem_ids.length && <p>아직 담은 문제가 없습니다.</p>}</section>
      <section><h2>보관함에서 선택</h2><div className="problem-available">{available.map(p => <div key={p.id}><span>{p.title} <small>{p.language ? languages[p.language] : '언어 무관'}</small></span><Button type="button" onClick={() => setForm({ ...form, problem_ids: [...form.problem_ids, p.id] })}>담기</Button></div>)}</div>{!available.length && <p>선택할 문제가 없습니다. 코드 문제는 정답 검증 후 이곳에 표시됩니다.</p>}</section>
      <div className="reference-actions"><Link className="button" to="/problem-books">돌아가기</Link><Button className="primary" disabled={busy}>{busy ? '저장 중…' : '문제집 저장'}</Button></div>
    </form>
  </main>;
}

export function BookDetail() {
  const { id } = useParams();
  const { data, error, reload } = useResource<Book>('/problem-books/' + id);
  const navigate = useNavigate();
  const [actionError, setActionError] = useState('');
  async function archive() { if (!window.confirm('문제집을 보관할까요? 풀이 기록은 남습니다.')) return; try { await api('/problem-books/' + id + '/archive', 'POST', {}); navigate('/problem-books'); } catch (e) { setActionError(errorMessage(e)); } }
  return <main className="page problem-books-page"><div className="breadcrumb"><Link to="/problem-books">문제집</Link><span>/</span>문제집 상세</div><ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}{data && <><header className="reference-page-heading"><div><small>{data.language ? languages[data.language] : '언어 무관'} · {data.problems.length}개 문제</small><h1>{data.title}</h1><p>{data.description || '순서대로 문제를 풀어보세요.'}</p></div><div className="reference-actions"><Link className="button" to={`/problem-books/${id}/edit`}>문제집 편집</Link><Button onClick={() => void archive()}>보관</Button></div></header><ol className="problem-book-contents">{data.problems.map((p, i) => <li key={p.id}><div><small>{String(i + 1).padStart(2, '0')} · {p.kind === 'code' ? p.verified ? '코드' : '코드 · 재검증 필요' : '서술'}{p.archived && ' · 보관됨'}</small><h2>{p.title}</h2><p>{p.source_name}{p.source_location && ` · ${p.source_location}`}</p></div>{!p.archived && (p.kind !== 'code' || p.verified) && <Link className="button" to={`/problem-books/problems/${p.id}/solve?book=${id}`}>풀기</Link>}</li>)}</ol>{!data.problems.length && <p className="empty-state">문제를 담으면 이곳에서 순서대로 풀 수 있습니다.</p>}</>}</main>;
}

export function SolveProblem() {
  const { id } = useParams();
  return <Solve key={id} id={id!} />;
}
function Solve({ id }: { id: string }) {
  const [params] = useSearchParams();
  const { data: problem, error, reload } = useResource<Problem>('/manual-problems/' + id);
  const { data: history, reload: reloadHistory } = useResource<{ items: Attempt[] }>('/manual-problems/' + id + '/attempts');
  const bookId = params.get('book');
  const { data: book } = useResource<Book>(bookId ? '/problem-books/' + bookId : '/problem-books');
  const [answer, setAnswer] = useState(''), [saved, setSaved] = useState<Attempt | null>(null), [solution, setSolution] = useState<{ answer: string; explanation: string } | null>(null), [busy, setBusy] = useState(false), [actionError, setActionError] = useState('');
  const [execution, setExecution] = useState<Verification | null>(null);
  const [snapshot, setSnapshot] = useState<{ attempt: Attempt; problem: Problem } | null>(null);
  const attempt = saved ?? history?.items.find(a => a.problem_revision === problem?.revision && (problem?.kind === 'code' || !a.assessment)) ?? null;
  async function execute(action: 'run' | 'submit') {
    if (!problem || !answer.trim()) return;
    setBusy(true); setActionError(''); setExecution(null);
    try {
      const response = await api<{ result: Verification; attempt: Attempt | null }>('/manual-problems/' + id + '/execute', 'POST', {
        action, code: answer, problem_revision: problem.revision, request_id: crypto.randomUUID(),
      });
      setExecution(action === 'run' ? response.result : null);
      if (response.attempt) { setSaved(response.attempt); setSolution(await api('/manual-problems/' + id + '/solution')); reloadHistory(); }
    } catch (e) { setActionError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function submit() {
    if (!problem || !answer.trim()) return;
    setBusy(true); setActionError('');
    try { const result = await api<Attempt>('/manual-problems/' + id + '/attempts', 'POST', { answer, problem_revision: problem.revision, request_id: crypto.randomUUID() }); setSaved(result); setSolution(await api('/manual-problems/' + id + '/solution')); reloadHistory(); }
    catch (e) { setActionError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function assess(value: 'understood' | 'retry') {
    if (!attempt) return;
    setBusy(true); setActionError('');
    try { await api(`/manual-problems/${id}/attempts/${attempt.id}/assessment`, 'POST', { assessment: value }); setSaved(null); setSolution(null); setAnswer(''); reloadHistory(); }
    catch (e) { setActionError(errorMessage(e)); } finally { setBusy(false); }
  }
  const next = bookId && book ? book.problems.slice(book.problem_ids.indexOf(id) + 1).find(item => !item.archived && (item.kind !== 'code' || item.verified))?.id : undefined;
  return <main className="page problem-books-page solve-page"><div className="breadcrumb"><Link to={bookId ? '/problem-books/' + bookId : '/problem-books'}>문제집</Link><span>/</span>문제 풀이</div><ErrorNotice error={error || actionError} />{error && <Button onClick={reload}>다시 불러오기</Button>}{problem && <><header className="reference-page-heading"><div><small>{problem.kind === 'code' ? '코드' : '서술'} · {problem.language ? languages[problem.language] : '언어 무관'} · v{problem.revision}</small><h1>{problem.title}</h1><p>{problem.source_name}{problem.source_location && ` · ${problem.source_location}`}</p>{problem.resource_id && <Link className="button" to={'/library/' + problem.resource_id}>연결된 자료 보기</Link>}</div></header><article className="problem-prompt"><Markdown language={problem.language ?? ''}>{problem.prompt}</Markdown></article>
      {problem.kind === 'code' && !problem.verified ? <section className="problem-answer"><h2>정답 검증이 필요합니다</h2><p>작성 화면에서 실행 사례를 추가하고 정답을 검증한 뒤 풀 수 있습니다.</p><Link className="button" to={`/problem-books/problems/${id}/edit`}>문제 편집</Link></section> : <section className="problem-answer"><h2>내 풀이</h2>{problem.kind === 'code' ? <CodeMirror value={answer} theme="dark" extensions={codeExtensions(problem.language ?? 'javascript', true)} height="280px" onChange={value => setAnswer(value.slice(0, 24000))} onCreateEditor={view => view.contentDOM.setAttribute('aria-label', '풀이 코드')} /> : <Textarea aria-label="내 답변" rows={9} maxLength={24000} value={answer} onChange={e => setAnswer(e.target.value)} />}{problem.kind === 'code' ? <div className="reference-actions"><Button disabled={busy || !answer.trim()} onClick={() => void execute('run')}>공개 사례 실행</Button><Button className="primary" disabled={busy || !answer.trim()} onClick={() => void execute('submit')}>{busy ? '실행 중…' : '제출·전체 사례 확인'}</Button></div> : <Button className="primary" disabled={busy || !answer.trim()} onClick={() => void submit()}>{busy ? '저장 중…' : '풀이 저장·정답 확인'}</Button>}{execution && <VerificationView result={execution} preview />}</section>}
      {attempt && <section className="problem-comparison"><h2>정답과 비교</h2><p>{problem.kind === 'code' ? `샌드박스 실행 결과: ${attempt.result?.status === 'passed' ? '전체 사례 통과' : '다시 연습 필요'}. 복습 일정에 자동 반영했습니다.` : '저장한 내 풀이를 기준으로 스스로 평가하세요. 자동 채점은 하지 않습니다.'}</p>{problem.kind === 'code' && attempt.result && <VerificationView result={attempt.result} />}<div className="problem-compare-columns"><div><h3>내 풀이</h3><pre>{attempt.answer}</pre></div><div><h3>정답·해설</h3>{solution ? <><Markdown language={problem.language ?? ''}>{solution.answer}</Markdown><Markdown language="">{solution.explanation}</Markdown></> : <Button onClick={() => void api<{ answer: string; explanation: string }>('/manual-problems/' + id + '/solution').then(setSolution).catch(e => setActionError(errorMessage(e)))}>정답 보기</Button>}</div></div>{problem.kind !== 'code' && <div className="reference-actions"><Button disabled={busy} onClick={() => void assess('retry')}>다시 풀기</Button><Button className="primary" disabled={busy} onClick={() => void assess('understood')}>이해함</Button></div>}</section>}
      {!!history?.items.length && <section className="problem-history"><h2>풀이 기록</h2><ul>{history.items.map(a => <li key={a.id}><Button onClick={() => void api<{ attempt: Attempt; problem: Problem }>(`/manual-problems/${id}/attempts/${a.id}/snapshot`).then(setSnapshot).catch(e => setActionError(errorMessage(e)))}>v{a.problem_revision} · {timestamp(a.created_at)} · {a.assessment === 'understood' ? '이해함' : a.assessment === 'retry' ? '다시 풀기' : '평가 대기'}</Button></li>)}</ul>{snapshot && <article className="problem-comparison"><h3>당시 문제 · v{snapshot.problem.revision}</h3><Markdown language={snapshot.problem.language ?? ''}>{snapshot.problem.prompt}</Markdown><h3>내 풀이</h3><pre>{snapshot.attempt.answer}</pre>{snapshot.attempt.result && <VerificationView result={snapshot.attempt.result} />}<h3>당시 정답</h3><Markdown language={snapshot.problem.language ?? ''}>{snapshot.problem.answer ?? ''}</Markdown><Markdown language="">{snapshot.problem.explanation ?? ''}</Markdown><Button onClick={() => setSnapshot(null)}>닫기</Button></article>}</section>}
      {next && <Link className="button" to={`/problem-books/problems/${next}/solve?book=${bookId}`}>다음 문제</Link>}
    </>}</main>;
}
