import { LoadingState } from './LoadingState';
import { GraduationCap } from 'lucide-react';
import { EmptyState, MaterialsNavigation, PageHeading } from './WorkspaceUI';
import { ContextQuestions } from './ContextQuestions';
import { StudyLocation } from './Today';
import { ReadingPosition } from './ReadingPosition';
import { Navigation } from './Navigation';
import { QuickQuestion } from './QuickQuestion';
import { useResource } from './useResource';
export { useResource } from './useResource';
import { NativeSelect } from './components/ui/native-select';
import { LoadingSkeleton } from './LoadingSkeleton';
import { AnimatedDetails } from './AnimatedDetails';
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { FoundationRecords } from './Foundations';
import { UsagePanel } from './Reviews';
import { Link, Outlet, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom';
import { api, errorMessage, isPending, languages, difficulties, difficultyDescriptions, timestamp, type Difficulty, type Generation, type Health, type History, type Language, type LearningContext, type Session } from './api';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { Badge } from './components/ui/badge';

type AppContext = { isAdmin: boolean; userId: string; health: Health | null; refreshHealth: () => void };
export function useApp() { return useOutletContext<AppContext>(); }
export function ErrorNotice({ error }: { error: string }) { return error ? <p className="notice error" role="alert">{error}</p> : null; }

export function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [opened, setOpened] = useState(false);
  const [error, setError] = useState('');
  const [health, setHealth] = useState<Health | null>(null);
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
  return <div className="app-shell">
    <ReadingPosition />
    <a className="skip-link" href="#workspace">본문으로 이동</a>
    <header className="topbar">
      <Link className="brand" to="/">code<span>trainer</span><span className="version">{session?.auth_mode === 'access' ? 'PRIVATE' : 'LOCAL'}</span></Link>
      <div className="account">{session?.user && <><QuickQuestion key={session.user.id} userId={session.user.id} /><span className="avatar">{session.user.username.slice(0, 1).toUpperCase()}</span><span>{session.user.username}</span>{session.auth_mode !== 'preview' && <Button className="text-button" onClick={logout}>로그아웃</Button>}</>}</div>
    </header>
    <div className="workspace-navigation"><Navigation isAdmin={!!session?.user?.admin} onNavigate={() => undefined} onLogout={session?.auth_mode === 'preview' ? undefined : () => void logout()} /></div>
    <div className="workspace" id="workspace">
      {error && <div className="page"><ErrorNotice error={error} /><Button onClick={refreshSession}>다시 연결</Button></div>}
      {opened && <><StudyLocation /><MaterialsNavigation /><Outlet context={{ health, refreshHealth, isAdmin: !!session?.user?.admin, userId: session?.user?.id ?? '' } satisfies AppContext} /><ContextQuestions /></>}
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
      <Button onClick={onSuccess}>인증 완료 · 다시 연결</Button>
    </div>
    <p className="auth-preservation">작성 중인 코드는 이 화면에 유지됩니다.</p>
  </section></dialog>;
  return <dialog ref={dialog} className="login-dialog" aria-labelledby="auth-title" onCancel={event => event.preventDefault()}><section className="auth-card">
    <span className="eyebrow">YOUR LOCAL WORKSPACE</span><h1 id="auth-title">이해는 코드에서<br />시작됩니다.</h1>
    <p>{setup ? '이 컴퓨터에서 사용할 계정을 만드세요. 코드와 풀이 기록이 로컬에 저장됩니다.' : '다시 만나 반갑습니다. 로그인하고 연습을 이어가세요.'}</p>
    <form onSubmit={submit}><Label>사용자 이름<Input name="username" required minLength={1} pattern={".*\\S.*"} title="공백을 제외한 글자를 한 글자 이상 입력해주세요." autoComplete="username" autoFocus /></Label><Label>비밀번호<Input name="password" type="password" required minLength={8} maxLength={128} autoComplete={setup ? 'new-password' : 'current-password'} /></Label>{setup && <><Label>관리자 비밀번호 (선택)<Input name="admin_password" type="password" maxLength={128} autoComplete="off" aria-describedby="admin-help" /></Label><small id="admin-help">입력하면 관리자 계정으로 생성합니다. 비워두면 일반 계정입니다.</small></>}<ErrorNotice error={error} /><Button loading={!!(busy)} className="primary" disabled={busy}>{busy ? '연결 중…' : setup ? '내 학습 공간 만들기' : '로그인'}</Button></form>
  </section></dialog>;
}

export function Home() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const { data, error, reload } = useResource<{ items: LearningContext[]; page: number; pages: number; total: number }>(`/contexts?page=${Math.floor(page)}`);
  const { health } = useApp();
  return <main className="page home-page">
    <div className="breadcrumb"><Link to="/library">학습 자료</Link><span>/</span>자료기반 코드 실습</div>
    <PageHeading title="자료기반 코드 실습" description="필요한 단원부터 읽고, 코드 문제로 이해를 확인하세요." actions={<><Link className="button" to="/library">원자료 열기</Link><Link className="button primary" to="/create">자료 기반 실습문제 생성</Link></>} />
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="cards" label="자료를 불러오는 중…" />}
    {data?.total === 0 && <EmptyState icon={GraduationCap} title="아직 생성한 실습이 없습니다" description="자료를 분석해 개념과 단원별 코드 학습을 시작해보세요." action={<Link className="button" to="/create">실습문제 생성</Link>} />}
    <div className="context-grid">{data?.items.map(context => <Link className="context-card" key={context.id} to={`/learn/${context.id}`}><div className="card-top"><Badge variant="language" className="language-tag">{languages[context.language]} · {difficulties[context.difficulty ?? 'beginner']}</Badge></div><h3>{context.title}</h3><p>{context.description}</p><div className="chips">{context.concepts.slice(0, 3).map(concept => <Badge variant="outline" key={concept} className="rounded-[5px] border-border bg-secondary px-2 py-[3px] text-[var(--text-caption)] text-secondary-foreground">{concept}</Badge>)}</div><div className="card-footer"><span>{context.completed} / {context.total} 완료</span><span>{timestamp(context.created_at)}</span></div></Link>)}</div>
    {data && data.total > 0 && <nav className="pagination" aria-label="학습 자료 페이지"><Button disabled={data.page <= 1} onClick={() => setParams({ page: String(data.page - 1) })}>이전</Button><span aria-live="polite">{data.page} / {data.pages} 페이지 · {data.total}개 자료</span><Button disabled={data.page >= data.pages} onClick={() => setParams({ page: String(data.page + 1) })}>다음</Button></nav>}
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
    {isPending(generation) ? <LoadingState compact status={generation.state === 'queued' ? '생성 대기' : '생성 중'} title="연습을 준비하고 있어요" description={generation.stage} /> : <div role="status"><span className={`status-dot ${generation.state === 'ready' ? 'online' : ''}`} /><strong>{generation.state === 'ready' ? generation.set_id ? '문제 준비가 끝났습니다' : '개념 학습 준비가 끝났습니다' : failed ? '생성을 완료하지 못했습니다' : '연습을 준비하고 있습니다'}</strong>
      <p>{failed && events.length ? `중단 단계: ${generation.stage}${lastPhase?.phase === '단원별 세트 생성' && lastPhase.kind ? ` · ${lastPhase.kind}` : ''}` : generation.stage}</p>
    </div>}
    <div className="generation-steps">{stages.map((stage, index) => <span key={stage}>{index + 1}. {stage}</span>)}</div>
    {generation.error && <ErrorNotice error={generation.error} />}
    {failed && <div className="generation-help">
      {!!issueEvent?.issues?.length && <ul>{issueEvent.issues.map((issue, index) => <li key={index}>{issue.label || '학습 항목'}: {issue.reason}</li>)}</ul>}
      {!!validationFailures.length && <ul>{validationFailures.map((event, index) => <li key={index}>{event.kind} · {event.check === 'reference' ? '기준 풀이' : event.check === 'alternative' ? '대안 풀이' : event.check === 'starter' ? '시작 코드' : event.check === 'starter_setup' ? '시작 코드의 예시 출력' : event.check?.startsWith('wrong:') ? '대표 오답' : '예측 출력'}: {event.message}</li>)}</ul>}
      {!events.length && <p>이전 버전에서 생성된 기록이라 상세 원인이 남아 있지 않습니다. 다시 생성하면 단계별 진단 로그가 저장됩니다.</p>}
      <p>{generation.context_id ? '개념 학습과 준비된 문제는 그대로 이용할 수 있습니다. 해당 단원에서 문제 생성을 다시 시도해주세요.' : '학습 과정이 아직 저장되지 않았습니다. 위 안내를 확인한 뒤 다시 생성해주세요.'}</p>
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
  async function generate() {
    setError(''); setBusy(true);
    const payload = { ...(feedPost ? { feed_post_id: feedPost } : {}), source_kind: kind, source, language, difficulty, source_name: sourceName };
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
  return <main className="page narrow-page"><div className="breadcrumb"><Link to="/">Workspace</Link><span>/</span> 실습문제 생성</div><h1>자료 기반 실습문제 생성</h1>
    {feedPost && <p className="notice">대기 포스팅: <strong>{params.get('title')}</strong><br />공개된 원문 URL로 바꿔 등록할 수 있습니다. 생성에 실패하면 대기 목록에 남습니다. <Link to="/inbox">목록으로</Link></p>}
    <form className="source-form" onSubmit={event => { event.preventDefault(); void generate(); }}><div className="input-tabs"><Button type="button" className={kind === 'text' ? 'selected' : ''} onClick={() => { setKind('text'); setSource(''); setSourceName(''); }} disabled={pending || !!feedPost}>텍스트 · Markdown</Button><Button type="button" className={kind === 'url' ? 'selected' : ''} onClick={() => { setKind('url'); setSource(''); setSourceName(''); }} disabled={pending}>URL</Button><Label className="upload-button">파일 불러오기<Input type="file" accept=".md,.txt,text/plain,text/markdown" disabled={pending || !!feedPost} onChange={event => void upload(event.target.files?.[0])} /></Label></div>
      <Label className="source-label" htmlFor="source">{kind === 'text' ? '학습할 자료' : '자료 주소'}</Label>{kind === 'text' ? <Textarea id="source" className="source-input" rows={10} value={source} onChange={event => setSource(event.target.value)} placeholder="실습문제를 만들 텍스트나 Markdown을 붙여넣으세요." minLength={20} maxLength={60000} required disabled={pending} /> : <Input id="source" type="url" value={source} onChange={event => setSource(event.target.value)} placeholder="https://developer.mozilla.org/…" required maxLength={2000} disabled={pending} />}
      <div className="source-footer"><span>{source.length.toLocaleString()} / {kind === 'text' ? '60,000' : '2,000'}자</span><span>원본 자료는 관리자 전용으로 보관합니다</span></div><Label htmlFor="practice-language">연습 언어</Label><NativeSelect id="practice-language" value={language} onChange={event => setLanguage(event.target.value as Language)} disabled={pending}>{Object.entries(languages).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</NativeSelect><Label htmlFor="practice-difficulty">난이도</Label><NativeSelect id="practice-difficulty" value={difficulty} onChange={event => setDifficulty(event.target.value as Difficulty)} disabled={pending}>{Object.entries(difficulties).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</NativeSelect><p className="muted">{difficultyDescriptions[difficulty]}</p><ErrorNotice error={error} />
      {health && !health.ai && <p className="notice">실습문제를 생성하려면 <Link to="/settings/ai">AI 연결을 설정해주세요.</Link></p>}<Button className="primary" loading={pending} disabled={pending || health?.ai === false}>{busy ? '요청 중…' : '실습문제 생성'}</Button>
    </form>
    {generation && <GenerationStatus generation={generation} />}
    {health?.sandbox === false && <p className="notice">개념 학습 과정은 먼저 만들 수 있습니다. 문제 생성과 예제 검증에는 샌드박스 연결이 필요합니다.</p>}
    {!!previous?.length && <section><h2>최근 생성 작업</h2><div className="list">{previous.slice(0, 8).map(item => <Button className="list-row" key={item.id} onClick={() => setGeneration(item)}><span>{item.stage || '연습 생성'}</span><span className="muted">{item.state === 'ready' ? '준비됨' : item.state === 'failed' ? '실패 · 확인' : '진행 중 · 확인'}</span></Button>)}</div></section>}
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
  return <section className="admin-reports"><h2 className="spaced-heading">제보 검토 · 로컬 관리자</h2><ErrorNotice error={error || actionError} /><div className="list">{data?.map(report => <div className="list-row" key={report.id}><div><small>{report.exercise_title} · {report.status}</small><p className="prose">{report.message}</p>{report.generation && <AnimatedDetails summary="생성 진단 보기"><GenerationStatus generation={report.generation} /></AnimatedDetails>}</div><div className="review-actions"><Button disabled={!!busy} onClick={() => void review(report.id, false)}>검토 완료</Button>{report.set_id && <Button disabled={!!busy} onClick={() => void review(report.id, true)}>문제 제공 중단</Button>}</div></div>)}</div></section>;
}

export function Me() {
  const { data, error, reload } = useResource<History>('/me');
  const { isAdmin } = useApp();
  return <main className="page knowledge-page settings-page records-page"><div className="breadcrumb">기록<span>/</span> 학습 기록</div>
    <PageHeading title="학습 기록" />
    <FoundationRecords />
    <UsagePanel />
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!!data?.reports.length && <AnimatedDetails className="report-history" summary={<>내 문제 제보 · {data.reports.length}개</>}>{data.reports.map(report => <div className="list-row" key={report.id}><div><small>{report.exercise_title}</small><p>{report.message}</p></div><span>{report.status}<small>{timestamp(report.created_at)}</small></span></div>)}</AnimatedDetails>}
    {isAdmin && <AdminReports />}
  </main>;
}
