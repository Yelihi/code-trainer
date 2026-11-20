import { Badge } from './components/ui/badge';
import { Rss } from 'lucide-react';
import { EmptyState, PageHeading } from './WorkspaceUI';
import { NativeSelect } from './components/ui/native-select';
import { AnimatedDetails } from './AnimatedDetails';
import { LoadingSkeleton } from './LoadingSkeleton';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ErrorNotice, useApp, useResource } from './App';
import { api, errorMessage, safeSourceUrl, timestamp } from './api';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';

type Feed = { id: string; name: string; url: string; enabled: number; succeeded: string | null; error: string };
type Post = { id: string; title: string; url: string; summary: string; published: string; feed_name: string; generation_state: string | null; resource_id: string | null; raw_url: string | null };
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
    setBusy('refresh:' + id); setActionError(''); setNotice('');
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
    setBusy('toggle:' + feed.id); setActionError(''); setNotice('');
    try { await api(`/feed-sources/${feed.id}`, 'PATCH', { enabled: !feed.enabled }); reload(); }
    catch (error) { setActionError(errorMessage(error)); }
    finally { setBusy(''); }
  }
  return <main className="page narrow-page">
    <div className="breadcrumb">Workspace<span>/</span> 자동 등록 대기 (RSA)</div>
    <PageHeading title="자동 수집" description="읽고 싶은 기술 글을 골라 원자료에 추가하세요." />
    <AnimatedDetails className="feed-settings" summary={<>수집 출처 {data ? `· ${data.feeds.length}개` : ''}{isAdmin ? ' · 관리' : ''}</>}>
      <p className="feed-settings-hint">공개 RSS·Atom 피드를 연결하세요. 일시정지해도 가져온 글은 유지됩니다.</p>
      <div className="feed-source-list">{data?.feeds.map(feed => <div className="feed-source" key={feed.id}>
        <div className="feed-source-info"><div className="feed-source-heading"><strong>{feed.name}</strong><Badge variant="secondary" className={'feed-status' + (feed.enabled ? ' is-active' : '')}>{feed.enabled ? '수집 중' : '일시정지'}</Badge></div><a href={safeSourceUrl(feed.url)} target="_blank" rel="noreferrer">{feed.url}</a><small>{feed.succeeded ? `마지막 수집 ${timestamp(feed.succeeded)}` : '수집 기록 없음'}</small>{feed.error && <p className="notice error">{feed.error}</p>}</div>
        <div className="feed-actions"><Button loading={busy === 'refresh:' + feed.id} disabled={!!busy || !feed.enabled} onClick={() => void refresh(feed.id)} aria-label={`${feed.name} 새 글 확인`}>새 글 확인</Button>{isAdmin && <Button loading={busy === 'toggle:' + feed.id} disabled={!!busy} onClick={() => void toggle(feed)} aria-label={`${feed.name} ${feed.enabled ? '수집 일시정지' : '수집 재개'}`}>{feed.enabled ? '일시정지' : '수집 재개'}</Button>}</div>
      </div>)}</div>
      {isAdmin && <form className="feed-add-form" onSubmit={event => void add(event)}>
        <h2>출처 추가</h2>
        <div className="feed-add-fields"><Label htmlFor="feed-name">출처 이름<Input id="feed-name" value={name} onChange={event => setName(event.target.value)} maxLength={100} required disabled={!!busy} placeholder="예: 개발 블로그" /></Label>
        <Label htmlFor="feed-url">RSS / Atom 주소<Input id="feed-url" type="url" value={url} onChange={event => setUrl(event.target.value)} maxLength={2000} required disabled={!!busy} placeholder="https://example.com/feed.xml" aria-describedby="feed-url-hint" /></Label></div>
        <div className="feed-add-footer"><p id="feed-url-hint">홈 주소 대신 피드 주소 입력 · 최대 20개</p><Button loading={busy === 'add'} className="primary" disabled={!!busy || !name.trim() || !url.trim()}>출처 추가</Button></div>
      </form>}
    </AnimatedDetails>
    <div className="feed-filter"><Label htmlFor="feed-filter">출처별 보기</Label><NativeSelect id="feed-filter" value={feedId} onChange={event => { setFeedId(event.target.value); setPage(1); setNotice(''); }}><option value="">모든 출처</option>{data?.feeds.map(feed => <option key={feed.id} value={feed.id}>{feed.name}{!feed.enabled && ' · 일시정지'}</option>)}</NativeSelect></div>
    <div className="feed-toolbar"><div><strong>{data ? `${data.total}개의 대기 포스팅` : '대기 포스팅'}</strong>{selected && <p className="muted">{selected.succeeded ? `마지막 수집 ${timestamp(selected.succeeded)}` : '아직 수집 기록이 없습니다.'}</p>}</div><Button onClick={reload} disabled={!!busy}>목록 새로고침</Button></div>
    <p className="muted">원문 등록에는 AI를 사용하지 않습니다. 원문 수집에 성공하면 대기 목록에서 빠집니다. 소개 글에 원문 링크가 있다면, 다음 화면에서 원문 URL로 바꿀 수 있습니다.</p>
    <ErrorNotice error={error || actionError || data?.error || ''} />{notice && <p className="notice" role="status">{notice}</p>}
    {error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="list" label="포스팅을 불러오는 중…" />}
    {data && !data.items.length && <EmptyState icon={Rss} title="대기 중인 글이 없습니다" description="등록한 출처에서 새 글을 수집하면 여기에 표시됩니다. 수집 출처에서 직접 확인할 수도 있습니다." />}
    <div className="feed-list">{data?.items.map(post => {
      const pending = post.generation_state === 'generating' || post.generation_state === 'validating';
      const query = new URLSearchParams({ post: post.id, url: post.raw_url || post.url, title: post.title });
      return <article className="feed-card" key={post.id}>
        <small className="muted">{post.feed_name}{post.published && ` · ${new Date(post.published).toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })}`}</small><h2>{post.title}</h2>
        <p className="feed-summary">{post.summary || '본문은 포스팅에서 확인해주세요.'}</p>
        {post.resource_id && <p className="notice">원문 등록이 아직 완료되지 않았습니다. 이전 수집 상태를 확인하거나 URL을 수정해 다시 등록할 수 있습니다.</p>}
        <div className="feed-actions"><a href={safeSourceUrl(post.url)} target="_blank" rel="noreferrer">포스팅 읽기</a>{post.resource_id && <Link to={'/library/' + post.resource_id}>이전 원문 보기</Link>}{pending && <Link to="/create">기존 생성 · 진행 확인</Link>}<Link className="button primary" to={`/library/new/reference?${query}`}>원문 등록</Link></div>
      </article>;
    })}</div>
    {data && data.pages > 1 && <div className="feed-pagination"><Button disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}>이전</Button><span>{data.page} / {data.pages}</span><Button disabled={data.page >= data.pages} onClick={() => setPage(data.page + 1)}>다음</Button></div>}
  </main>;
}
