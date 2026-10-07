import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorNotice, useResource } from './App';
import { api, errorMessage, safeSourceUrl, timestamp } from './api';

type Post = { id: string; title: string; url: string; summary: string; published: string; generation_state: string | null };
type Inbox = { items: Post[]; total: number; page: number; pages: number; feed_name: string; feed_url: string; succeeded: string | null; error: string };

export function FeedInbox() {
  const [page, setPage] = useState(1);
  const { data, error, reload } = useResource<Inbox>(`/feed-posts?page=${page}`);
  const [refreshing, setRefreshing] = useState(false);
  const [actionError, setActionError] = useState('');
  async function refresh() {
    setRefreshing(true); setActionError('');
    try { await api('/feed-posts/refresh', 'POST', {}); reload(); }
    catch (error) { setActionError(errorMessage(error)); }
    finally { setRefreshing(false); }
  }
  return <main className="page narrow-page">
    <div className="breadcrumb">Workspace<span>/</span> 등록 대기 포스팅</div>
    <span className="eyebrow">READ. CHOOSE. LEARN.</span><h1>등록 대기 포스팅</h1>
    <p className="page-intro">Korean FE Article의 새 글을 한 시간마다 모읍니다.<br />읽어보고 선택한 글만 학습 자료로 만들어보세요.</p>
    <div className="feed-toolbar"><div><strong>{data ? `${data.total}개의 대기 포스팅` : '목록 불러오는 중…'}</strong><p className="muted">{data?.succeeded ? `마지막 수집 ${timestamp(data.succeeded)}` : '아직 수집 기록이 없습니다.'}</p></div><button onClick={() => void refresh()} disabled={refreshing}>{refreshing ? '가져오는 중…' : '새 글 확인'}</button></div>
    <p className="muted">수집에는 AI를 사용하지 않습니다. 학습 과정 생성이 완료되면 대기 목록에서 빠집니다. 소개 글에 원문 링크가 있다면, 다음 화면에서 원문 URL로 바꿀 수 있습니다.</p>
    <ErrorNotice error={error || actionError || data?.error || ''} />
    {error && <button onClick={reload}>다시 불러오기</button>}
    {data && !data.items.length && <div className="empty-state"><h2>대기 중인 글이 없습니다</h2><p>새 글이 수집되면 이곳에 표시됩니다. 처음이라면 ‘새 글 확인’을 눌러주세요.</p></div>}
    <div className="feed-list">{data?.items.map(post => {
      const pending = post.generation_state === 'generating' || post.generation_state === 'validating';
      const query = new URLSearchParams({ post: post.id, url: post.url, title: post.title });
      return <article className="feed-card" key={post.id}>
        <small className="muted">{data.feed_name}{post.published && ` · ${timestamp(post.published)}`}</small><h2>{post.title}</h2>
        <p className="feed-summary">{post.summary || '본문은 포스팅에서 확인해주세요.'}</p>
        {post.generation_state === 'failed' && <p className="notice">이전 생성이 완료되지 않았습니다. 자료 주소를 확인하고 다시 시도할 수 있습니다.</p>}
        <div className="feed-actions"><a href={safeSourceUrl(post.url)} target="_blank" rel="noreferrer">포스팅 읽기 ↗</a>{pending ? <Link to="/create">생성 중 · 진행 확인 →</Link> : <Link className="button primary" to={`/create?${query}`}>학습 자료로 등록 →</Link>}</div>
      </article>;
    })}</div>
    {data && data.pages > 1 && <div className="feed-pagination"><button disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}>이전</button><span>{data.page} / {data.pages}</span><button disabled={data.page >= data.pages} onClick={() => setPage(data.page + 1)}>다음</button></div>}
  </main>;
}
