import { Navigation } from './Navigation';
import { Select } from './Select';
import { LoadingSkeleton } from './LoadingSkeleton';
import { AnimatedDetails } from './AnimatedDetails';
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { FoundationRecords } from './Foundations';
import { UsagePanel } from './Reviews';
import { Link, Outlet, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom';
import { api, errorMessage, isPending, languages, difficulties, difficultyDescriptions, timestamp, type Difficulty, type Generation, type Health, type History, type Language, type LearningContext, type Session } from './api';

type AppContext = { isAdmin: boolean; userId: string; health: Health | null; refreshHealth: () => void };
export function useApp() { return useOutletContext<AppContext>(); }
export function ErrorNotice({ error }: { error: string }) { return error ? <p className="notice error" role="alert">{error}</p> : null; }

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion(value => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError('');
    api<T>(path, 'GET', undefined, controller.signal).then(setData).catch(error => { if (!controller.signal.aborted) setError(errorMessage(error)); });
    return () => controller.abort();
  }, [path, version]);
  return { data, error, reload };
}

export function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [opened, setOpened] = useState(false);
  const [error, setError] = useState('');
  const [health, setHealth] = useState<Health | null>(null);
  const [menu, setMenu] = useState(false);
  const menuToggle = useRef<HTMLButtonElement>(null);
  function closeMenu() {
    setMenu(false);
    if (menuToggle.current?.offsetParent) menuToggle.current.focus();
  }
  const refreshHealth = useCallback(() => { api<Health>('/health').then(setHealth).catch(() => setHealth(null)); }, []);
  const refreshSession = useCallback(() => {
    setError('');
    api<Session>('/session').then(value => { setSession(value); if (value.user) setOpened(true); }).catch(error => setError(errorMessage(error)));
  }, []);
  useEffect(() => {
    refreshSession(); refreshHealth();
    const expired = (event: Event) => {
      // Keep the editor mounted under the login dialog so unsaved work survives expiry.
      setSession(previous => ({ user: null, setup_required: false, auth_mode: (event as CustomEvent).detail === 'access' ? 'access' : previous?.auth_mode }));
    };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, [refreshSession, refreshHealth]);
  async function logout() {
    if (!window.confirm('저장하지 않은 코드가 있다면 먼저 저장해주세요. 로그아웃할까요?')) return;
    try {
      await api('/logout', 'POST', {});
      setOpened(false);
      if (session?.auth_mode === 'access') window.location.assign('/cdn-cgi/access/logout');
      else setSession({ user: null, setup_required: false });
    } catch (error) { setError(errorMessage(error)); }
  }
  return <div className="app-shell" onKeyDown={event => {
    if (menu && event.key === 'Escape' && !event.defaultPrevented && !(event.target as HTMLElement).closest('dialog')) {
      event.preventDefault(); closeMenu();
    }
  }}>
    <a className="skip-link" href="#workspace">본문으로 이동</a>
    <header className="topbar">
      <button ref={menuToggle} className="icon-button menu-toggle" aria-label={menu ? '메뉴 닫기' : '메뉴 열기'} aria-controls="workspace-navigation" aria-expanded={menu} onClick={() => setMenu(!menu)}>☰</button>
      <Link className="brand" to="/">code<span>trainer</span><span className="version">{session?.auth_mode === 'access' ? 'PRIVATE' : 'LOCAL'}</span></Link>
      <div className="topbar-center">YOUR SECOND BRAIN</div>
      <div className="account">{session?.user && <><span className="avatar">{session.user.username.slice(0, 1).toUpperCase()}</span><span>{session.user.username}</span><button className="text-button" onClick={logout}>로그아웃</button></>}</div>
    </header>
    <aside id="workspace-navigation" className={`sidebar ${menu ? 'open' : ''}`}>
      <Navigation isAdmin={!!session?.user?.admin} onNavigate={closeMenu} />
      <div className="sidebar-bottom"><span className={`status-dot ${health?.sandbox ? 'online' : ''}`} /><span>{health === null ? '실행 환경 확인 필요' : health.sandbox ? '샌드박스 연결됨' : '샌드박스 연결 필요'}</span><button className="icon-button" aria-label="실행 환경 다시 확인" onClick={refreshHealth}>↻</button></div>
    </aside>
    <div className="workspace" id="workspace">
      {error && <div className="page"><ErrorNotice error={error} /><button onClick={refreshSession}>다시 연결</button></div>}
      {opened && <Outlet context={{ health, refreshHealth, isAdmin: !!session?.user?.admin, userId: session?.user?.id ?? '' } satisfies AppContext} />}
      {!session && !error && <main className="page"><LoadingSkeleton layout="cards" label="학습 공간을 여는 중…" heading /></main>}
    </div>
    {session && !session.user && <Login access={session.auth_mode === 'access'} setup={session.setup_required} onSuccess={() => { refreshSession(); refreshHealth(); }} />}
  </div>;
}

function Login({ setup, access, onSuccess }: { setup: boolean; access: boolean; onSuccess: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const fields = new FormData(event.currentTarget);
    try { await api('/auth', 'POST', { username: fields.get('username'), password: fields.get('password'), ...(setup ? { admin_password: fields.get('admin_password') || '' } : {}) }); onSuccess(); }
    catch (error) { setError(errorMessage(error)); } finally { setBusy(false); }
  }
  if (access) return <dialog ref={dialog} className="login-dialog" aria-labelledby="auth-title" aria-describedby="auth-description" onCancel={event => event.preventDefault()}><section className="auth-card access-card">
    <span className="eyebrow">PRIVATE WORKSPACE</span><h1 id="auth-title">다시 로그인해주세요.</h1>
    <p id="auth-description">새 탭에서 허용된 이메일로 인증한 뒤,<br />이 화면으로 돌아와 다시 연결해주세요.</p>
    <div className="auth-actions">
      <a className="button primary" href="/" target="_blank" rel="noreferrer">새 탭에서 이메일 인증</a>
      <button onClick={onSuccess}>인증 완료 · 다시 연결</button>
    </div>
    <p className="auth-preservation">작성 중인 코드는 이 화면에 유지됩니다.</p>
  </section></dialog>;
  return <dialog ref={dialog} className="login-dialog" aria-labelledby="auth-title" onCancel={event => event.preventDefault()}><section className="auth-card">
    <span className="eyebrow">YOUR LOCAL WORKSPACE</span><h1 id="auth-title">이해는 코드에서<br />시작됩니다.</h1>
    <p>{setup ? '이 컴퓨터에서 사용할 계정을 만드세요. 코드와 풀이 기록이 로컬에 저장됩니다.' : '다시 만나 반갑습니다. 로그인하고 연습을 이어가세요.'}</p>
    <form onSubmit={submit}><label>사용자 이름<input name="username" required minLength={1} pattern={".*\\S.*"} title="공백을 제외한 글자를 한 글자 이상 입력해주세요." autoComplete="username" autoFocus /></label><label>비밀번호<input name="password" type="password" required minLength={8} maxLength={128} autoComplete={setup ? 'new-password' : 'current-password'} /></label>{setup && <><label>관리자 비밀번호 (선택)<input name="admin_password" type="password" maxLength={128} autoComplete="off" aria-describedby="admin-help" /></label><small id="admin-help">입력하면 관리자 계정으로 생성합니다. 비워두면 일반 계정입니다.</small></>}<ErrorNotice error={error} /><button className="primary" disabled={busy}>{busy ? '연결 중…' : setup ? '내 학습 공간 만들기' : '로그인'}</button></form>
  </section></dialog>;
}

export function Home() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const { data, error, reload } = useResource<{ items: LearningContext[]; page: number; pages: number; total: number }>(`/contexts?page=${Math.floor(page)}`);
  const { health } = useApp();
  return <main className="page home-page">
    <div className="breadcrumb">탐구하기 <span>/</span> 해석하기</div>
    <section className="hero brain-hero"><div><span className="eyebrow">COLLECT. UNDERSTAND. CONNECT.</span><h1>자료를 모으고,<br /><em>이해를 연결하세요.</em></h1><p>컴퓨터와 개발에 관한 레퍼런스를 저장하고,<br />탐구한 내용을 나만의 지식으로 쌓아가세요.</p><div className="brain-actions"><Link className="button primary" to="/library/new/reference">레퍼런스 등록</Link><Link className="button" to="/library">자료 보관함</Link></div></div>
      <ol className="brain-journey" aria-label="자료에서 창조까지">
        <li><span>01</span><div><strong>등록하기</strong><p>원문과 생각을 한곳에 모으기</p></div></li>
        <li><span>02</span><div><strong>탐구하기</strong><p>개념을 이해하고 직접 실습하기</p></div></li>
        <li><span>03</span><div><strong>데이터 쌓기</strong><p>개념과 관계를 지식 그래프로 연결하기</p></div></li>
        <li><span>04</span><div><strong>응용하기</strong><p>연결에서 새로운 질문 찾기 · 준비 중</p></div></li>
      </ol>
    </section>
    <div className="section-heading"><div><span className="eyebrow">YOUR COLLECTION</span><h2>해석한 학습 자료 <span className="count">{data?.total ?? '—'}</span></h2></div><div className="brain-actions"><Link className="text-link" to="/create">기존 자료 분석</Link><Link className="text-link" to="/me">학습 기록 보기</Link></div></div>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="cards" label="자료를 불러오는 중…" />}
    {data?.total === 0 && <div className="empty-state"><h3>아직 해석한 학습 자료가 없습니다.</h3><p>자료 보관함에 원문을 먼저 모아보세요.<br />보관함에서 해석을 시작하는 연결은 준비 중이며, 기존 자료 분석은 계속 사용할 수 있습니다.</p><Link className="button" to="/create">기존 자료 분석 열기</Link></div>}
    <div className="context-grid">{data?.items.map(context => <Link className="context-card" key={context.id} to={`/learn/${context.id}`}><div className="card-top"><span className="language-tag">{languages[context.language]} · {difficulties[context.difficulty ?? 'beginner']}</span></div><h3>{context.title}</h3><p>{context.description}</p><div className="chips">{context.concepts.slice(0, 3).map(concept => <span key={concept}>{concept}</span>)}</div><div className="card-footer"><span>{context.completed} / {context.total} 완료</span><span>{timestamp(context.created_at)}</span></div></Link>)}</div>
    {data && data.total > 0 && <nav className="pagination" aria-label="학습 자료 페이지"><button disabled={data.page <= 1} onClick={() => setParams({ page: String(data.page - 1) })}>이전</button><span aria-live="polite">{data.page} / {data.pages} 페이지 · {data.total}개 자료</span><button disabled={data.page >= data.pages} onClick={() => setParams({ page: String(data.page + 1) })}>다음</button></nav>}
    {health && !health.sandbox && <p className="notice">실행 환경이 아직 연결되지 않았습니다. 문제 생성 검증과 코드 실행에는 샌드박스가 필요합니다.</p>}
  </main>;
}

export function GenerationStatus({ generation }: { generation: Generation }) {
  const stages = generation.unit_id ? ['단원 문제 생성', '코드 검증'] : ['개념 분리 · 학습 순서', '개념 설명 준비'];
  const events = generation.events ?? [];
  const failed = generation.state === 'failed';
  const lastPhase = [...events].reverse().find(event => event.phase);
  const issueEvent = events[events.length - 1];
  const validationFailures = events.slice(events.map(event => event.message).lastIndexOf('코드 검증 시작'))
    .filter(event => event.code === 'code_validation_failed');
  return <div className="generation-status">
    <div role="status"><span className={`status-dot ${isPending(generation) ? 'pulsing' : generation.state === 'ready' ? 'online' : ''}`} /><strong>{generation.state === 'ready' ? generation.set_id ? '문제 준비가 끝났습니다' : '개념 학습 준비가 끝났습니다' : failed ? '생성을 완료하지 못했습니다' : '연습을 준비하고 있습니다'}</strong>
      <p>{failed && events.length ? `중단 단계: ${generation.stage}${lastPhase?.phase === '단원별 세트 생성' && lastPhase.kind ? ` · ${lastPhase.kind}` : ''}` : generation.stage}</p>
    </div>
    <div className="generation-steps">{stages.map((stage, index) => <span key={stage}>{index + 1}. {stage}</span>)}</div>
    {generation.error && <ErrorNotice error={generation.error} />}
    {failed && <div className="generation-help">
      {!!issueEvent?.issues?.length && <ul>{issueEvent.issues.map((issue, index) => <li key={index}>{issue.label || '학습 항목'}: {issue.reason}</li>)}</ul>}
      {!!validationFailures.length && <ul>{validationFailures.map((event, index) => <li key={index}>{event.kind} · {event.check === 'reference' ? '기준 풀이' : event.check === 'alternative' ? '대안 풀이' : event.check === 'starter' ? '시작 코드' : event.check === 'starter_setup' ? '시작 코드의 예시 출력' : event.check?.startsWith('wrong:') ? '대표 오답' : '예측 출력'}: {event.message}</li>)}</ul>}
      {!events.length && <p>이전 버전에서 생성된 기록이라 상세 원인이 남아 있지 않습니다. 다시 생성하면 단계별 진단 로그가 저장됩니다.</p>}
      <p>{generation.context_id ? '개념 학습과 준비된 문제는 그대로 이용할 수 있습니다. 해당 단원에서 문제 생성을 다시 시도해주세요.' : '학습 과정이 아직 저장되지 않았습니다. 위 안내를 확인한 뒤 자료를 다시 입력하여 생성해주세요.'}</p>
    </div>}
    <AnimatedDetails className="generation-log" summary={<>진단 로그 · {events.length}개</>}>
      <p>작업 ID <code>{generation.id}</code></p>
      <p className="muted">서버 로그: data/generation.log · API 키, 원문, 정답 코드는 기록하지 않습니다.</p>
      <ol>{events.map((event, index) => <li key={index} data-level={event.level}>
        <time dateTime={event.time}>{new Date(event.time).toLocaleTimeString('ko-KR')}</time>
        <span>{[event.phase, event.unit && `${event.unit}단원`, event.kind, event.candidate && `${event.candidate}차 시도`].filter(Boolean).join(' · ')}</span>
        <div>{event.message}</div>
        <small>{[event.code, event.model, event.check, event.status, event.elapsed_seconds != null && `${event.elapsed_seconds}초`].filter(Boolean).join(' · ')}</small>
        {event.issues?.map((issue, i) => <div key={i}><code>{issue.path}</code> · {issue.reason} ({issue.type})</div>)}
      </li>)}</ol>
    </AnimatedDetails>
    {generation.context_id && !generation.unit_id && <Link className="button primary" to={`/learn/${generation.context_id}`}>학습 과정 보기</Link>}
  </div>;
}

export function Create() {
  const { health } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const feedPost = params.get('post');
  const [kind, setKind] = useState<'text' | 'url'>(feedPost ? 'url' : 'text');
  const [source, setSource] = useState(feedPost ? params.get('url') || '' : '');
  const [sourceName, setSourceName] = useState(feedPost ? (params.get('title') || '').slice(0, 255) : '');
  const [framework, setFramework] = useState('');
  const [language, setLanguage] = useState<Language>('javascript');
  const [difficulty, setDifficulty] = useState<Difficulty>('beginner');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [generation, setGeneration] = useState<Generation | null>(null);
  const request = useRef({ key: '', id: '' });
  const { data: previous, reload } = useResource<Generation[]>('/generations');
  useEffect(() => {
    if (generation?.state === 'ready' && generation.context_id) {
      void navigate(`/learn/${generation.context_id}`, { replace: true });
    }
  }, [generation, navigate]);
  useEffect(() => {
    if (!generation || !isPending(generation)) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try { const value = await api<Generation>(`/generations/${generation!.id}`, 'GET', undefined, controller.signal); setGeneration(value); if (isPending(value)) timer = setTimeout(poll, 1800); else reload(); }
      catch (error) { if (!controller.signal.aborted) { setError(errorMessage(error)); timer = setTimeout(poll, 4000); } }
    }
    timer = setTimeout(poll, 1000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [generation, reload]); // Each poll remains tied to its generation.
  async function generate(sample = false) {
    setError(''); setBusy(true);
    const payload = { ...(feedPost && !sample ? { feed_post_id: feedPost } : {}), source_kind: sample ? 'sample' : kind, source: sample ? '' : source, language: sample ? 'javascript' : language, difficulty: sample ? 'beginner' : difficulty, source_name: sample ? '' : sourceName, framework: sample ? '' : framework };
    const key = JSON.stringify(payload);
    if (request.current.key !== key) request.current = { key, id: crypto.randomUUID() };
    try {
      const result = await api<Generation>('/generations', 'POST', { ...payload, request_id: request.current.id });
      setGeneration(result); request.current = { key: '', id: '' }; reload();
    } catch (error) { setError(errorMessage(error)); } finally { setBusy(false); }
  }
  async function upload(file?: File) {
    if (!file) return;
    if (file.size > 60000 || !/\.(md|txt)$/i.test(file.name)) { setError('60 KB 이하의 .md 또는 .txt 파일을 선택해주세요.'); return; }
    try { setSource(await file.text()); setSourceName(file.name); setKind('text'); setError(''); } catch (error) { setError(errorMessage(error)); }
  }
  const pending = busy || !!(generation && isPending(generation));
  return <main className="page narrow-page"><div className="breadcrumb"><Link to="/">Workspace</Link><span>/</span> 연습 만들기</div><span className="eyebrow">ONE SOURCE. A CONNECTED COURSE.</span><h1>무엇을 배워볼까요?</h1><p className="page-intro">먼저 자료를 단원으로 나누고 개념 학습 페이지를 준비합니다.<br className="desktop-only" /> 개념을 읽은 뒤 원하는 단원에서 문제 생성을 요청하세요.</p>
    {feedPost && <p className="notice">대기 포스팅: <strong>{params.get('title')}</strong><br />공개된 원문 URL로 바꿔 등록할 수 있습니다. 생성에 실패하면 대기 목록에 남습니다. <Link to="/inbox">목록으로</Link></p>}
    <form className="source-form" onSubmit={event => { event.preventDefault(); void generate(); }}><div className="input-tabs"><button type="button" className={kind === 'text' ? 'selected' : ''} onClick={() => { setKind('text'); setSource(''); setSourceName(''); }} disabled={pending || !!feedPost}>텍스트 · Markdown</button><button type="button" className={kind === 'url' ? 'selected' : ''} onClick={() => { setKind('url'); setSource(''); setSourceName(''); }} disabled={pending}>URL</button><label className="upload-button">파일 불러오기<input type="file" accept=".md,.txt,text/plain,text/markdown" disabled={pending || !!feedPost} onChange={event => void upload(event.target.files?.[0])} /></label></div>
      <label className="source-label" htmlFor="source">{kind === 'text' ? '학습할 자료' : '자료 주소'}</label>{kind === 'text' ? <textarea id="source" className="source-input" value={source} onChange={event => setSource(event.target.value)} placeholder={'여기에 학습하고 싶은 글을 붙여넣으세요.\n\n예: 클로저는 함수와 그 함수가 선언된 렉시컬 환경의 조합입니다…'} minLength={20} maxLength={60000} required disabled={pending} /> : <input id="source" type="url" value={source} onChange={event => setSource(event.target.value)} placeholder="https://developer.mozilla.org/…" required maxLength={2000} disabled={pending} />}
      <div className="source-footer"><span>{source.length.toLocaleString()} / {kind === 'text' ? '60,000' : '2,000'}자</span><span>원본 자료는 관리자 전용으로 보관합니다</span></div><label htmlFor="practice-language">연습 언어</label><Select id="practice-language" value={language} onChange={event => setLanguage(event.target.value as Language)} disabled={pending}>{Object.entries(languages).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select><label htmlFor="learning-framework">학습 분류 (선택)</label><input id="learning-framework" value={framework} onChange={event => setFramework(event.target.value)} maxLength={80} placeholder="예: React, Vue — 비워두면 언어별로 정리합니다" disabled={pending} /><label htmlFor="practice-difficulty">난이도</label><Select id="practice-difficulty" value={difficulty} onChange={event => setDifficulty(event.target.value as Difficulty)} disabled={pending}>{Object.entries(difficulties).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select><p className="muted">{difficultyDescriptions[difficulty]}</p><ErrorNotice error={error} />
      {health && !health.ai && <p className="notice">AI 연결이 필요합니다. 먼저 아래 준비된 예제로 흐름을 확인할 수 있습니다.</p>}<button className="primary" disabled={pending || health?.ai === false}>{busy ? '요청 중…' : '학습 과정 생성'}</button>
    </form>
    {generation && <GenerationStatus generation={generation} />}
    <section className="sample-card"><div><span className="eyebrow">QUICK START</span><h3>JavaScript 클로저부터 시작하기</h3><p>함수 호출과 기대값을 읽으며 풀어보세요. 테스트 코드를 직접 바꿔 실행할 수 있고, AI 비용은 들지 않습니다.</p></div><button disabled={pending || health?.sandbox === false} onClick={() => void generate(true)}>예제로 시작</button></section>
    {health?.sandbox === false && <p className="notice">개념 학습 과정은 먼저 만들 수 있습니다. 문제 생성과 예제 검증에는 샌드박스 연결이 필요합니다.</p>}
    {!!previous?.length && <section><h2>최근 생성 작업</h2><div className="list">{previous.slice(0, 8).map(item => <button className="list-row" key={item.id} onClick={() => setGeneration(item)}><span>{item.stage || '연습 생성'}</span><span className="muted">{item.state === 'ready' ? '준비됨' : item.state === 'failed' ? '실패 · 확인' : '진행 중 · 확인'}</span></button>)}</div></section>}
  </main>;
}

export function AdminReports() {
  const { data, error, reload } = useResource<{ id: string; exercise_title: string; message: string; status: string; set_id: string | null; generation?: Generation }[]>('/admin/reports');
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState('');
  async function review(id: string, withdraw: boolean) {
    if (withdraw && !window.confirm('이 문제가 포함된 세트의 새 실행과 제출을 중단할까요? 기존 기록은 보존됩니다.')) return;
    setBusy(id); setActionError('');
    try { await api(`/admin/reports/${id}`, 'PATCH', { status: withdraw ? 'reviewed' : 'resolved', withdraw }); reload(); }
    catch (error) { setActionError(errorMessage(error)); } finally { setBusy(''); }
  }
  if (!data?.length && !error) return null;
  return <section className="admin-reports"><h2 className="spaced-heading">제보 검토 · 로컬 관리자</h2><ErrorNotice error={error || actionError} /><div className="list">{data?.map(report => <div className="list-row" key={report.id}><div><small>{report.exercise_title} · {report.status}</small><p className="prose">{report.message}</p>{report.generation && <AnimatedDetails summary="생성 진단 보기"><GenerationStatus generation={report.generation} /></AnimatedDetails>}</div><div className="review-actions"><button disabled={!!busy} onClick={() => void review(report.id, false)}>검토 완료</button>{report.set_id && <button disabled={!!busy} onClick={() => void review(report.id, true)}>문제 제공 중단</button>}</div></div>)}</div></section>;
}

export function Me() {
  const { data, error, reload } = useResource<History>('/me');
  const { isAdmin } = useApp();
  return <main className="page knowledge-page"><div className="breadcrumb">Workspace<span>/</span> 나의 기록</div>
    <span className="eyebrow">MY LEARNING RECORDS</span><h1>나의 학습 기록</h1>
    <div className="graph-record-link"><div><strong>배운 개념은 지식 그래프에서</strong><p>개념의 연결과 풀었던 문제를 한눈에 탐색하세요.</p></div><Link className="button" to="/knowledge">지식 그래프 열기 ↗</Link></div>
    <FoundationRecords />
    <UsagePanel />
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!!data?.reports.length && <AnimatedDetails className="report-history" summary={<>내 문제 제보 · {data.reports.length}개</>}>{data.reports.map(report => <div className="list-row" key={report.id}><div><small>{report.exercise_title}</small><p>{report.message}</p></div><span>{report.status}<small>{timestamp(report.created_at)}</small></span></div>)}</AnimatedDetails>}
    {isAdmin && <AdminReports />}
  </main>;
}
