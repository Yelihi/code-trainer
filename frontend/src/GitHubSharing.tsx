import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { AnimatedDetails } from './AnimatedDetails';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Markdown } from './Markdown';
import './githubSharing.css';

type Connection = { storage_ready: boolean; connection: { id: string; login: string; updated_at: string } | null };
type Repository = { connection_id: string; login: string; repo_id: number; repo: string; url: string; private: boolean; issues_enabled: boolean; active: boolean; can_attempt: boolean; write_permission: 'unverified'; checked_at: string };
type DefaultRepository = Pick<Repository, 'connection_id' | 'repo_id' | 'url' | 'private'>;
type Share = { id: string; kind: string; source_id: string; version: string; repo: string; private: boolean; login: string; title: string; body: string; state: 'sending' | 'published' | 'failed' | 'unknown'; issue_url: string | null; error: string; created_at: string };
type Preview = { kind: string; id: string; version: string; version_label: string; title: string; body: string; has_images: boolean; history: Share[] };
const stateLabels = { sending: '등록 중', published: '등록 완료', failed: '등록 실패', unknown: '결과 확인 필요' };
const tokenHelp = 'https://github.com/settings/personal-access-tokens/new';

function Check({ state, children }: { state: 'ok' | 'warning' | 'error'; children: React.ReactNode }) {
  return <li className={`github-check ${state}`}><span aria-hidden="true">{state === 'ok' ? '✓' : state === 'warning' ? '!' : '×'}</span><div>{children}</div></li>;
}

function RepositoryCheck({ onChecked, disabled = false, registration = false }: { onChecked?: (value: Repository | null) => void; disabled?: boolean; registration?: boolean }) {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<Repository | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<DefaultRepository | null>(null);
  const [loadError, setLoadError] = useState('');
  const [loadVersion, setLoadVersion] = useState(0);
  const [message, setMessage] = useState('');
  const edited = useRef(false);
  const defaultRequest = useRef<AbortController | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController(); defaultRequest.current = controller;
    api<{ repository: DefaultRepository | null }>('/github/default-repository', 'GET', undefined, controller.signal).then(({ repository: value }) => {
      if (controller.signal.aborted) return;
      setSaved(value); setLoadError('');
      if (!edited.current && value) setUrl(value.url);
    }).catch(e => { if (!controller.signal.aborted) setLoadError(errorMessage(e)); });
    return () => controller.abort();
  }, [loadVersion]);
  useEffect(() => () => request.current?.abort(), []);
  function change(value: string) {
    edited.current = true;
    request.current?.abort(); setUrl(value); setResult(null); setError(''); setMessage(''); setBusy(false); onChecked?.(null);
  }
  async function check() {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    edited.current = true;
    setBusy(true); setError(''); setMessage(''); setResult(null); onChecked?.(null);
    try {
      const value = await api<Repository>('/github/repository-check', 'POST', { url }, controller.signal);
      if (!registration && saved && value.url.toLowerCase() === saved.url.toLowerCase()
          && (value.repo_id !== saved.repo_id || value.private !== saved.private || value.connection_id !== saved.connection_id)) {
        throw new Error('기본 저장소의 계정 또는 공개 범위가 변경되었습니다. 설정에서 다시 등록해주세요.');
      }
      if (!controller.signal.aborted) { setResult(value); onChecked?.(value); }
    } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function register() {
    if (!result || busy) return;
    defaultRequest.current?.abort();
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(''); setMessage('');
    try {
      const { url, connection_id, repo_id, private: isPrivate } = result;
      const value = await api<DefaultRepository>('/github/default-repository', 'PUT', { url, connection_id, repo_id, private: isPrivate }, controller.signal);
      if (!controller.signal.aborted) { setSaved(value); setMessage('기본 저장소를 등록했습니다. 공유할 때 주소를 미리 채웁니다.'); }
    } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="github-card">
    <div className="github-section-title"><span className="github-step">02</span><div><h2>공유할 저장소</h2><p>주소는 공유할 때마다 바꿀 수 있습니다.</p></div></div>
    {saved && <p className="github-caption">기본 저장소 · <a href={saved.url} target="_blank" rel="noreferrer">{saved.url}</a> · {saved.private ? '비공개' : '공개'}로 등록됨</p>}
    <ErrorNotice error={loadError} />{loadError && <button type="button" onClick={() => setLoadVersion(v => v + 1)}>기본 저장소 다시 불러오기</button>}
    <label htmlFor="github-repo">GitHub 저장소 주소</label><div className="github-repo-input"><input id="github-repo" type="url" value={url} onChange={e => change(e.target.value)} placeholder="https://github.com/owner/repository" maxLength={500} disabled={disabled} spellCheck={false} /><button type="button" disabled={disabled || busy || !url.trim()} onClick={() => void check()}>{busy ? '확인 중…' : '권한 확인'}</button></div>
    {busy && <p className="github-checking" role="status"><span aria-hidden="true" />계정과 저장소를 확인하고 있습니다.</p>}
    <ErrorNotice error={error} />
    {message && <p role="status" className="notice">{message}</p>}
    {result && <div aria-live="polite"><div className="github-repo-heading"><a href={result.url} target="_blank" rel="noreferrer">{result.repo} ↗</a><span className={`github-badge ${result.private ? '' : 'public'}`}>{result.private ? '비공개 저장소' : '공개 저장소'}</span></div>
      <ul className="github-checks">
        <Check state="ok">작성 계정 <strong>@{result.login}</strong></Check>
        <Check state="ok">저장소 정보 조회 가능</Check>
        <Check state={result.issues_enabled ? 'ok' : 'error'}>{result.issues_enabled ? 'Issues 사용 중' : '이슈 기능이 꺼져 있습니다.'}</Check>
        <Check state={result.active ? 'ok' : 'error'}>{result.active ? '활성 저장소' : '보관되었거나 제한된 저장소입니다.'}</Check>
        <Check state="warning"><strong>Issues 쓰기 권한 · 설정 확인 필요</strong><small>조회 성공만으로 쓰기 권한은 확인되지 않습니다. 토큰의 대상 저장소와 Issues: Read and write, 조직 승인 상태를 확인해주세요.</small></Check>
      </ul><p className="github-caption">{timestamp(result.checked_at)} 확인 · 테스트 이슈를 만들지 않습니다.</p>
      {registration && <><button type="button" className="primary" disabled={disabled || busy || !result.can_attempt} onClick={() => void register()}>기본 저장소 등록</button><p className="github-caption">주소만 저장하며, 이슈는 공유 화면에서 내용을 확인한 뒤 등록합니다. 토큰 교체·연결 해제 시 기본 저장소도 해제됩니다.</p></>}
    </div>}
  </section>;
}

export function GitHubSettings() {
  const { data, error, reload } = useResource<Connection>('/github/connection');
  const history = useResource<Share[]>('/github/shares');
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [message, setMessage] = useState('');
  async function connect() {
    setBusy(true); setActionError(''); setMessage('');
    try { await api('/github/connection', 'PUT', { token: token.trim() }); setToken(''); reload(); setMessage('GitHub 계정을 연결했습니다. 아래에서 저장소를 확인해보세요.'); }
    catch (e) { setActionError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function disconnect() {
    if (!window.confirm('GitHub 연결을 해제할까요? 기존 이슈와 공유 기록은 유지됩니다. 토큰 자체는 GitHub 설정에서 취소할 수 있습니다.')) return;
    setBusy(true); setActionError('');
    try { await api('/github/connection', 'DELETE', {}); setToken(''); reload(); setMessage('저장된 토큰을 삭제했습니다.'); }
    catch (e) { setActionError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <main className="page github-page">
    <div className="breadcrumb"><span>설정</span><span>/</span>GitHub 연동</div><span className="eyebrow">KNOWLEDGE, SHARED WITH INTENT.</span><h1>배운 내용을, 함께 나누기.</h1>
    <p className="page-intro">레퍼런스 노트와 연결된 지식을 GitHub 이슈로 공유하세요.<br />공유할 때 저장소와 내용을 직접 확인한 뒤 등록합니다.</p>
    <ErrorNotice error={error || actionError} />{error && <button onClick={reload}>다시 불러오기</button>}{message && <p role="status" className="notice">{message}</p>}
    {!data && !error && <LoadingSkeleton layout="editor" label="GitHub 연결을 불러오는 중…" />}
    {data && <div className="github-settings-grid"><div className="github-stack"><section className="github-card">
      <div className="github-section-title"><span className="github-step">01</span><div><h2>GitHub 계정 연결</h2><p>Fine-grained personal access token</p></div></div>
      {!data.storage_ready && <p className="notice">서버의 암호화 키 설정이 필요합니다. 관리자가 설정한 후 토큰을 연결할 수 있습니다.</p>}
      {data.connection && <div className="github-identity"><div className="github-avatar" aria-hidden="true">{data.connection.login[0].toUpperCase()}</div><div><strong>@{data.connection.login}</strong><small>{timestamp(data.connection.updated_at)} 연결 · 공유 시 유효성 재확인</small></div><button disabled={busy} onClick={() => void disconnect()}>연결 해제</button></div>}
      <form onSubmit={e => { e.preventDefault(); void connect(); }}>
        <label htmlFor="github-token">{data.connection ? '토큰 교체' : 'Fine-grained 토큰'}</label><input id="github-token" type="password" autoComplete="off" spellCheck={false} placeholder="github_pat_…" value={token} onChange={e => setToken(e.target.value)} minLength={31} maxLength={251} disabled={busy || !data.storage_ready} required />
        <p className="github-caption">서버에서 암호화해 저장합니다. 저장한 토큰은 화면이나 브라우저 저장소에 보관하지 않습니다.</p>
        <button className="primary" disabled={busy || !data.storage_ready || !/^github_pat_[A-Za-z0-9_]{20,240}$/.test(token.trim())}>{busy ? '연결 확인 중…' : data.connection ? '새 토큰으로 연결' : 'GitHub 연결'}</button>
      </form>
    </section><RepositoryCheck key={data.connection?.id ?? 'disconnected'} registration disabled={!data.connection || !data.storage_ready || busy} /></div>
    <aside className="github-guide"><span className="eyebrow">BEFORE YOU CONNECT</span><h2>필요한 권한만 선택하세요.</h2><ol><li><strong>Resource owner 선택</strong><p>공유할 저장소의 개인 또는 조직을 선택합니다.</p></li><li><strong>대상 저장소 선택</strong><p>Only select repositories에서 공유할 저장소를 지정합니다.</p></li><li><strong>Issues → Read and write</strong><p>Repository permissions에 설정합니다. Contents 쓰기 권한은 필요하지 않습니다.</p></li><li><strong>만료일과 조직 승인 확인</strong><p>조직에서 승인을 요구하면 승인 완료 후 사용할 수 있습니다.</p></li></ol><a className="button" href={tokenHelp} target="_blank" rel="noreferrer">GitHub에서 토큰 만들기 ↗</a><p>토큰이 허용하는 저장소 안에서 매번 다른 주소를 사용할 수 있습니다.</p>
      <div className="github-guide-footer"><h3>공유는 어디에서 하나요?</h3><p>저장된 레퍼런스 노트 또는 지식 그래프의 상세 패널에서 <strong>GitHub 이슈로 공유</strong>를 선택하세요.</p><Link className="text-link" to="/references">레퍼런스 노트로 ↗</Link></div>
    </aside></div>}
    <section className="github-history"><h2>최근 공유 기록</h2><ErrorNotice error={history.error} />{history.error && <button onClick={history.reload}>기록 다시 불러오기</button>}{!history.data && !history.error && <LoadingSkeleton layout="list" label="공유 기록을 불러오는 중…" />}{history.data?.length === 0 && <p className="muted">아직 공유한 지식이 없습니다. 첫 이슈를 등록하면 이곳에 기록됩니다.</p>}{history.data?.map(item => <ShareRecord key={item.id} item={item} onRecovered={history.reload} />)}</section>
  </main>;
}

export function GitHubShare() {
  const [params] = useSearchParams();
  const kind = params.get('kind') ?? '', id = params.get('id') ?? '';
  return <ShareLoader key={kind + ':' + id} kind={kind} id={id} />;
}

function ShareLoader({ kind, id }: { kind: string; id: string }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<Preview>('/github/preview', 'POST', { kind, id }, controller.signal).then(value => { if (!controller.signal.aborted) setPreview(value); }).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); });
    return () => controller.abort();
  }, [kind, id, version]);
  if (!preview) return <main className="page github-page"><ErrorNotice error={error} />{error ? <button onClick={() => { setError(''); setVersion(v => v + 1); }}>다시 불러오기</button> : <LoadingSkeleton layout="editor" label="공유할 지식을 준비하는 중…" heading />}</main>;
  return <ShareEditor initial={preview} />;
}

function ShareEditor({ initial }: { initial: Preview }) {
  const { userId } = useApp();
  const [draftOwner] = useState(userId);
  const storageKey = `github-share:${draftOwner}:${initial.kind}:${initial.id}`;
  const [saved] = useState(() => {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
      return value && typeof value.title === 'string' && typeof value.body === 'string' && typeof value.version === 'string' && /^[a-f0-9]{32}$/.test(value.request_id) ? value as { title: string; body: string; version: string; request_id: string } : null;
    } catch { return null; }
  });
  const [title, setTitle] = useState(saved?.title ?? initial.title);
  const [body, setBody] = useState(saved?.body ?? initial.body);
  const [sourceVersion, setSourceVersion] = useState(saved?.version ?? initial.version);
  const [requestId, setRequestId] = useState(saved?.request_id ?? crypto.randomUUID().replaceAll('-', ''));
  const [repo, setRepo] = useState<Repository | null>(null);
  const [permissions, setPermissions] = useState(false);
  const [content, setContent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Share | null>(null);
  const [storageError, setStorageError] = useState('');
  const [history, setHistory] = useState(initial.history);
  const inFlight = useRef(false);
  const locked = busy || !!result && result.state !== 'failed';
  const stale = sourceVersion !== initial.version;
  useEffect(() => {
    try {
      if (result?.state === 'published') localStorage.removeItem(storageKey);
      else localStorage.setItem(storageKey, JSON.stringify({ title, body, version: sourceVersion, request_id: requestId }));
    }
    catch { setStorageError('브라우저에 임시 저장하지 못했습니다. 이동하기 전에 본문을 복사해주세요.'); }
  }, [title, body, sourceVersion, requestId, result, storageKey]);
  function checked(value: Repository | null) { setRepo(value); setPermissions(false); setContent(false); setRequestId(crypto.randomUUID().replaceAll('-', '')); }
  async function publish() {
    if (!repo || inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError('');
    try {
      const value = await api<Share>('/github/shares', 'POST', { kind: initial.kind, id: initial.id, version: sourceVersion,
        url: repo.url, connection_id: repo.connection_id, repo_id: repo.repo_id, private: repo.private,
        request_id: requestId, title, body, permissions_confirmed: permissions, content_confirmed: content });
      setResult(value); setHistory(previous => [value, ...previous.filter(r => r.id !== value.id)]);
      if (value.state === 'failed') { setRequestId(crypto.randomUUID().replaceAll('-', '')); setPermissions(false); }
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); inFlight.current = false; }
  }
  return <main className="page github-page github-share-page"><div className="breadcrumb"><Link to={initial.kind === 'note' ? '/references/' + initial.id : '/knowledge'}>원본 지식</Link><span>/</span>GitHub 이슈로 공유</div><span className="eyebrow">REVIEW BEFORE SHARING</span><h1>공유할 내용을 확인하세요.</h1><p className="page-intro">{initial.version_label}와 연결된 개념·출처의 스냅샷입니다. 이슈를 편집해도 원본 노트와 그래프는 바뀌지 않습니다.</p>
    <div className="github-share-top"><span className="github-badge">01 · 원본 준비됨</span><Link to="/settings/github" className="text-link">GitHub 연결 설정 ↗</Link></div>
    {saved && <p className="notice">이 브라우저에 남아 있던 공유 초안을 복원했습니다.</p>}
    {stale && <p className="notice">초안을 만든 이후 원본이 변경되었습니다. 현재 글을 복사해 보관한 뒤 새로 시작해주세요. <button disabled={busy} onClick={() => { if (window.confirm('현재 공유 초안을 최신 원본 내용으로 교체할까요?')) { setTitle(initial.title); setBody(initial.body); setSourceVersion(initial.version); setRequestId(crypto.randomUUID().replaceAll('-', '')); } }}>최신 원본으로 새로 작성</button></p>}
    {initial.has_images && <p className="notice">앱에 첨부한 이미지는 비공개라 GitHub로 전송하지 않습니다. 이슈 등록 후 GitHub 에디터에서 별도로 첨부해주세요.</p>}
    <RepositoryCheck onChecked={checked} disabled={locked} />
    <section className="github-card"><div className="github-section-title"><span className="github-step">03</span><div><h2>이슈 미리보기</h2><p>공개할 문장과 출처를 확인하고 필요한 부분만 남기세요.</p></div></div>
      <label htmlFor="github-issue-title">이슈 제목</label><input id="github-issue-title" value={title} onChange={e => { setTitle(e.target.value); setContent(false); }} maxLength={256} disabled={locked} />
      <div className="github-editor-grid"><div><label htmlFor="github-issue-body">Markdown 본문</label><textarea id="github-issue-body" value={body} onChange={e => { setBody(e.target.value); setContent(false); }} disabled={locked} spellCheck={false} /><p className={`github-caption ${body.length > 60000 ? 'github-over-limit' : ''}`}>{body.length.toLocaleString()} / 60,000자{body.length > 60000 ? ' · 필요한 내용만 남겨 길이를 줄여주세요.' : ' · 이 브라우저에 초안 보관'}</p></div><div><span className="github-preview-label">미리보기</span><article className="github-markdown-preview"><h2>{title}</h2><Markdown language="">{body}</Markdown></article></div></div>
    </section>
    <ErrorNotice error={error || storageError} />
    <section className="github-publish"><div><h2>확인한 내용으로 등록</h2>{repo && <p><strong>@{repo.login}</strong> 계정으로 <strong>{repo.repo}</strong>에 등록합니다.</p>}{repo && <p className={repo.private ? '' : 'github-public-notice'}>{repo.private ? '저장소에 접근할 수 있는 구성원에게 공유됩니다.' : '공개 저장소입니다. 등록한 내용은 누구나 볼 수 있습니다.'}</p>}
      <label className="github-consent"><input type="checkbox" checked={permissions} onChange={e => setPermissions(e.target.checked)} disabled={locked || !repo?.can_attempt} /><span>토큰에 이 저장소와 <strong>Issues: Read and write</strong>를 설정했고, 필요한 조직 승인을 받았습니다.</span></label>
      <label className="github-consent"><input type="checkbox" checked={content} onChange={e => setContent(e.target.checked)} disabled={locked || !repo?.can_attempt} /><span>본문·개념 데이터·출처와 위 공개 범위를 확인했습니다.</span></label></div>
      <button className="primary" disabled={locked || stale || !repo?.can_attempt || !permissions || !content || !title.trim() || !body.trim() || body.length > 60000 || draftOwner !== userId} onClick={() => void publish()}>{busy ? '권한 재확인 · 등록 중…' : result?.state === 'published' ? '등록 완료' : 'GitHub 이슈 등록'}</button><p className="github-caption">등록 직전에 계정과 저장소 상태를 다시 확인합니다. 같은 원본 버전은 같은 저장소에 한 번만 등록합니다.</p>
    </section>
    <section className="github-history"><h2>이 지식의 공유 기록</h2>{history.map(item => <ShareRecord key={item.id + item.state} item={item} onRecovered={value => { setHistory(h => h.map(r => r.id === value.id ? value : r)); if (result?.id === value.id) setResult(value); }} />)}</section>
  </main>;
}

function ShareRecord({ item, onRecovered }: { item: Share; onRecovered: (item: Share) => void }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function recover() {
    setBusy(true); setError('');
    try { onRecovered(await api<Share>(`/github/shares/${item.id}/recover`, 'POST', { url })); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <article className="github-share-record"><div className="github-record-heading"><div><small>{item.repo} · @{item.login} · {timestamp(item.created_at)}</small><h3>{item.title}</h3></div><span className={`github-badge ${item.state}`}>{stateLabels[item.state]}</span></div>
    {item.issue_url && <a className="text-link" href={item.issue_url} target="_blank" rel="noreferrer">등록한 이슈 열기 ↗</a>}{item.error && <p className="notice" role="status">{item.error}</p>}
    {item.state === 'sending' && <p>등록 중인 요청입니다. 잠시 후 이 페이지를 다시 열어 결과를 확인해주세요.</p>}
    {item.state === 'unknown' && <><p>먼저 <a href={`https://github.com/${item.repo}/issues`} target="_blank" rel="noreferrer">GitHub 이슈 목록 ↗</a>을 확인해주세요. 등록된 이슈가 없다면 아래 본문을 복사해 GitHub에서 직접 등록할 수 있습니다.</p><AnimatedDetails summary="등록 요청 본문 확인"><p>수동으로 등록할 때 마지막 확인용 표식도 함께 복사해주세요.</p><textarea readOnly aria-label="등록 요청 원문" value={item.body + '\n\n<!-- code-trainer-share:' + item.id + ' -->'} /><button onClick={() => { void navigator.clipboard.writeText(item.body + '\n\n<!-- code-trainer-share:' + item.id + ' -->').then(() => setMessage('본문을 복사했습니다.')).catch(() => setError('복사하지 못했습니다. 위 원문을 직접 선택해 복사해주세요.')); }}>원문 복사</button>{message && <p role="status">{message}</p>}</AnimatedDetails><label>등록된 이슈 주소<input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder={`https://github.com/${item.repo}/issues/123`} maxLength={500} /></label><button disabled={busy || !url.trim()} onClick={() => void recover()}>{busy ? '확인 중…' : '이슈 확인 · 기록 연결'}</button><ErrorNotice error={error} /></>}
  </article>;
}
