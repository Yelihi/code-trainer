import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ErrorNotice, useApp, useResource } from './App';
import { api, errorMessage, safeSourceUrl, timestamp } from './api';

type Feed = { id: string; name: string; url: string; enabled: number; succeeded: string | null; error: string };
type Post = { id: string; title: string; url: string; summary: string; published: string; feed_name: string; generation_state: string | null };
type Inbox = { items: Post[]; total: number; page: number; pages: number; feeds: Feed[]; error: string };

export function FeedInbox() {
  const { isAdmin } = useApp();
  const [page, setPage] = useState(1);
  const [feedId, setFeedId] = useState('');
  const { data, error, reload } = useResource<Inbox>(`/feed-posts?page=${page}&feed_id=${encodeURIComponent(feedId)}`);
  const [busy, setBusy] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const selected = data?.feeds.find(feed => feed.id === feedId);
  async function refresh(id: string) {
    setBusy(id); setActionError(''); setNotice('');
    try {
      const result = await api<{ updated: boolean }>(`/feed-sources/${id}/refresh`, 'POST', {});
      setNotice(result.updated ? '새 글 확인을 마쳤습니다.' : '갱신하지 않았습니다. 수집 상태를 확인하고 마지막 시도로부터 1분 후 다시 시도해주세요.');
      reload();
    } catch (error) { setActionError(errorMessage(error)); }
    finally { setBusy(''); }
  }
  async function add(event: FormEvent) {
    event.preventDefault(); setBusy('add'); setActionError(''); setNotice('');
    try {
      const feed = await api<Feed>('/feed-sources', 'POST', { name, url });
      setName(''); setUrl(''); setFeedId(feed.id); setPage(1); reload();
      setNotice(`${feed.name} 출처를 추가하고 첫 수집을 마쳤습니다.`);
    } catch (error) { setActionError(errorMessage(error)); }
    finally { setBusy(''); }
  }
  async function toggle(feed: Feed) {
    setBusy(feed.id); setActionError(''); setNotice('');
    try { await api(`/feed-sources/${feed.id}`, 'PATCH', { enabled: !feed.enabled }); reload(); }
    catch (error) { setActionError(errorMessage(error)); }
    finally { setBusy(''); }
  }
  return <main className="page narrow-page">
    <div className="breadcrumb">Workspace<span>/</span> 등록 대기 포스팅</div>
    <span className="eyebrow">READ. CHOOSE. LEARN.</span><h1>등록 대기 포스팅</h1>
    <p className="page-intro">등록한 사이트의 새 글을 한 시간마다 모읍니다.<br />읽어보고 선택한 글만 학습 자료로 만들어보세요.</p>
    <details className="feed-settings"><summary>수집 출처 {data ? `· ${data.feeds.length}개` : ''}{isAdmin ? ' · 관리' : ''}</summary>
      <p className="muted">공개 RSS/Atom 주소를 사용합니다. 출처는 함께 사용하고 학습 자료 등록 여부는 사용자별로 기록합니다. 일시정지해도 수집된 글은 남습니다.</p>
      <div className="feed-source-list">{data?.feeds.map(feed => <div className="feed-source" key={feed.id}>
        <div><strong>{feed.name}</strong><span className="muted"> · {feed.enabled ? '수집 중' : '일시정지'}</span><a href={safeSourceUrl(feed.url)} target="_blank" rel="noreferrer">{feed.url}</a><small className="muted">{feed.succeeded ? `마지막 수집 ${timestamp(feed.succeeded)}` : '수집 기록 없음'}</small>{feed.error && <p className="notice error">{feed.error}</p>}</div>
        <div className="feed-actions"><button disabled={!!busy || !feed.enabled} onClick={() => void refresh(feed.id)} aria-label={`${feed.name} 새 글 확인`}>새 글 확인</button>{isAdmin && <button disabled={!!busy} onClick={() => void toggle(feed)} aria-label={`${feed.name} ${feed.enabled ? '수집 일시정지' : '수집 재개'}`}>{feed.enabled ? '일시정지' : '수집 재개'}</button>}</div>
      </div>)}</div>
      {isAdmin && <form className="feed-add-form" onSubmit={event => void add(event)}>
        <h2>출처 추가</h2><label htmlFor="feed-name">출처 이름</label><input id="feed-name" value={name} onChange={event => setName(event.target.value)} maxLength={100} required disabled={!!busy} placeholder="예: 개발 블로그" />
        <label htmlFor="feed-url">RSS / Atom 주소</label><input id="feed-url" type="url" value={url} onChange={event => setUrl(event.target.value)} maxLength={2000} required disabled={!!busy} placeholder="https://example.com/feed.xml" />
        <p className="muted">사이트 홈 주소가 아닌 피드 주소를 입력해주세요. 추가할 때 피드를 확인하고 최근 글을 가져옵니다. 최대 20개 출처를 등록할 수 있습니다.</p>
        <button className="primary" disabled={!!busy}>{busy === 'add' ? '피드 확인 중…' : '출처 추가'}</button>
      </form>}
    </details>
    <div className="feed-filter"><label htmlFor="feed-filter">출처별 보기</label><select id="feed-filter" value={feedId} onChange={event => { setFeedId(event.target.value); setPage(1); setNotice(''); }}><option value="">모든 출처</option>{data?.feeds.map(feed => <option key={feed.id} value={feed.id}>{feed.name}{!feed.enabled && ' · 일시정지'}</option>)}</select></div>
    <div className="feed-toolbar"><div><strong>{data ? `${data.total}개의 대기 포스팅` : '목록 불러오는 중…'}</strong>{selected && <p className="muted">{selected.succeeded ? `마지막 수집 ${timestamp(selected.succeeded)}` : '아직 수집 기록이 없습니다.'}</p>}</div><button onClick={reload} disabled={!!busy}>목록 새로고침</button></div>
    <p className="muted">수집에는 AI를 사용하지 않습니다. 학습 과정 생성이 완료되면 대기 목록에서 빠집니다. 소개 글에 원문 링크가 있다면, 다음 화면에서 원문 URL로 바꿀 수 있습니다.</p>
    <ErrorNotice error={error || actionError || data?.error || ''} />{notice && <p className="notice" role="status">{notice}</p>}
    {error && <button onClick={reload}>다시 불러오기</button>}
    {data && !data.items.length && <div className="empty-state"><h2>대기 중인 글이 없습니다</h2><p>새 글이 수집되면 이곳에 표시됩니다. ‘수집 출처’에서 새 글을 직접 확인할 수도 있습니다.</p></div>}
    <div className="feed-list">{data?.items.map(post => {
      const pending = post.generation_state === 'generating' || post.generation_state === 'validating';
      const query = new URLSearchParams({ post: post.id, url: post.url, title: post.title });
      return <article className="feed-card" key={post.id}>
        <small className="muted">{post.feed_name}{post.published && ` · ${new Date(post.published).toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })}`}</small><h2>{post.title}</h2>
        <p className="feed-summary">{post.summary || '본문은 포스팅에서 확인해주세요.'}</p>
        {post.generation_state === 'failed' && <p className="notice">이전 생성이 완료되지 않았습니다. 자료 주소를 확인하고 다시 시도할 수 있습니다.</p>}
        <div className="feed-actions"><a href={safeSourceUrl(post.url)} target="_blank" rel="noreferrer">포스팅 읽기 ↗</a>{pending ? <Link to="/create">생성 중 · 진행 확인 →</Link> : <Link className="button primary" to={`/create?${query}`}>학습 자료로 등록 →</Link>}</div>
      </article>;
    })}</div>
    {data && data.pages > 1 && <div className="feed-pagination"><button disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}>이전</button><span>{data.page} / {data.pages}</span><button disabled={data.page >= data.pages} onClick={() => setPage(data.page + 1)}>다음</button></div>}
  </main>;
}
