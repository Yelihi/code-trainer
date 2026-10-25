import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, difficulties, errorMessage, isPending, languages, timestamp, type Difficulty, type Generation, type Language } from './api';
import { ErrorNotice, GenerationStatus, useApp } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Select } from './Select';
import './library.css';

type History = { source: { title: string; source_name: string; resource_id: string; revision: number; current_revision: number }; items: (Generation & { language: Language; difficulty: Difficulty; created_at: string })[] };

export function InterpretationCode() {
  const { id, sectionId } = useParams(), { userId } = useApp();
  return <CodeSetup key={`${userId}:${id}:${sectionId}`} id={id!} sectionId={sectionId!} />;
}
function CodeSetup({ id, sectionId }: { id: string; sectionId: string }) {
  const { userId, health } = useApp();
  const [data, setData] = useState<History | null>(null), [loadError, setLoadError] = useState(''), [error, setError] = useState(''), [warning, setWarning] = useState('');
  const [version, setVersion] = useState(0), [busy, setBusy] = useState(false);
  const [language, setLanguage] = useState<Language>('javascript'), [difficulty, setDifficulty] = useState<Difficulty>('beginner');
  const sending = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const next = await api<History>(`/interpretations/${id}/code?section_id=${encodeURIComponent(sectionId)}`, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setData(next); setLoadError('');
        if (next.items.some(isPending)) timer = setTimeout(() => void load(), 1800);
      } catch (e) { if (!controller.signal.aborted) setLoadError(errorMessage(e)); }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [id, sectionId, version]);
  async function start(event: FormEvent) {
    event.preventDefault(); if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    const storageKey = `code-request:${userId}:${id}:${sectionId}:${language}:${difficulty}`;
    let requestId = crypto.randomUUID() as string;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored && /^[a-f0-9-]{36}$/.test(stored)) requestId = stored;
      localStorage.setItem(storageKey, requestId);
    } catch { setWarning('요청을 브라우저에 임시 저장하지 못했습니다. 연결이 끊기면 재요청 전에 아래 생성 기록을 확인해주세요.'); }
    try {
      await api<Generation>('/generations', 'POST', { request_id: requestId, source_kind: 'interpretation', interpretation_id: id, section_id: sectionId, language, difficulty });
      try { localStorage.removeItem(storageKey); } catch { /* Existing identity still safely reopens the saved job. */ }
      setVersion(v => v + 1);
    } catch (e) { setError(errorMessage(e)); setVersion(v => v + 1); }
    finally { sending.current = false; setBusy(false); }
  }
  const pending = busy || !!data?.items.some(isPending);
  return <main className="page narrow-page"><div className="breadcrumb"><Link to={`/interpretations/${id}#${sectionId}`}>해석 섹션</Link><span>/</span> 코드 실습</div>
    <span className="eyebrow">FROM CONCEPT TO CODE</span><h1>{data?.source.title ?? '코드 실습 준비'}</h1>
    <p className="page-intro">이 섹션을 코딩 학습 과정으로 준비합니다.<br />과정을 확인한 뒤 원하는 단원에서 검증된 문제 생성을 요청하세요.</p>
    <ErrorNotice error={loadError} />{loadError && <button onClick={() => setVersion(v => v + 1)}>생성 기록 다시 확인</button>}
    {!data && !loadError && <LoadingSkeleton layout="editor" label="실습 출처와 기록을 불러오는 중…" />}
    {data && <aside className="interpretation-provenance"><strong>{data.source.source_name} · 원문 v{data.source.revision}</strong><p>선택한 섹션의 원문 인용과 AI 해석을 구분해 사용합니다. 코딩으로 실습하기 어려운 내용은 이유를 안내합니다.{data.source.current_revision !== data.source.revision && ` 현재 원문은 v${data.source.current_revision}이며, 이 실습은 v${data.source.revision} 해석을 유지합니다.`}</p></aside>}
    <form className="source-form" onSubmit={event => void start(event)}>
      <label htmlFor="code-language">실습 언어</label><Select id="code-language" value={language} disabled={pending} onChange={e => setLanguage(e.target.value as Language)}>{Object.entries(languages).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</Select>
      <label htmlFor="code-difficulty">난이도</label><Select id="code-difficulty" value={difficulty} disabled={pending} onChange={e => setDifficulty(e.target.value as Difficulty)}>{Object.entries(difficulties).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</Select>
      <ErrorNotice error={error} />{warning && <p role="status" className="notice">{warning}</p>}
      <button className="primary" disabled={!data || !!loadError || pending || !userId || !health?.ai}>{pending ? '과정 준비 중…' : '이 섹션으로 코딩 과정 준비'}</button>
      {!health?.ai && <p>과정을 만들려면 <Link to="/settings/ai">AI 연결</Link>이 필요합니다. 기존 실습은 계속 사용할 수 있습니다.</p>}
    </form>
    <h2 className="spaced-heading">이 섹션의 코드 실습 기록</h2><p>최근 20개 과정 · 문제는 과정 안에서 단원별로 생성합니다.</p>
    {data?.items.map(job => <section key={job.id}><p>{languages[job.language]} · {difficulties[job.difficulty]} · {timestamp(job.created_at)}</p><GenerationStatus generation={job} /></section>)}
    {data && !data.items.length && <p className="muted">아직 준비한 코딩 과정이 없습니다.</p>}
  </main>;
}
