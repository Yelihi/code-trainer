import { memo, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { timestamp } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Skeleton } from './components/ui/skeleton';
import { QuestionListSkeleton } from './QuestionSkeletons';
import type { Question } from './questionTypes';

type QuestionPage = { items: Question[]; total: number; page: number };

function QuestionSearch({ query, status }: { query: string; status: string }) {
  const [, setParams] = useSearchParams();
  const [search, setSearch] = useState(query);
  return <form className="question-capture" onSubmit={e => { e.preventDefault(); setParams({ q: search, status }); }}><Label className="sr-only" htmlFor="question-search">질문 검색</Label><Input id="question-search" value={search} onChange={e => setSearch(e.target.value)} placeholder="질문 찾기" /><Button>검색</Button></form>;
}

export const QuestionRows = memo(function QuestionRows({ items }: { items: Question[] }) {
  return <>{items.map(item => <Link className="question-row" title={item.text} key={item.id} to={'/questions/' + item.id}><span><strong>{item.text}</strong><small>{timestamp(item.updated_at)} · 연결 자료 {item.links.length}개{item.note_id ? ' · 노트 연결됨' : ''}</small></span><span>열기</span></Link>)}</>;
});

export function QuestionResults({ data, loading, query }: { data: QuestionPage | null; loading: boolean; query: string }) {
  return <div className="question-results" aria-busy={loading}>{data ? <><QuestionRows items={data.items} />{!data.items.length && <p className="empty-state">{query ? '검색 결과가 없습니다.' : '아직 질문이 없습니다. 상단의 ‘질문 적기’로 시작하세요.'}</p>}</> : <QuestionListSkeleton />}</div>;
}

export function QuestionList() {
  const [params, setParams] = useSearchParams();
  const status = params.get('status') === 'done' ? 'done' : 'open', q = params.get('q') ?? '', page = Math.max(1, Math.floor(Number(params.get('page')) || 1));
  const { data, error, loading, reload } = useResource<QuestionPage>(`/questions?status=${status}&q=${encodeURIComponent(q)}&page=${page}`, { preserveData: true });
  useEffect(() => { window.addEventListener('questions-changed', reload); return () => window.removeEventListener('questions-changed', reload); }, [reload]);
  return <section className="question-list-section" aria-label="저장한 질문">
    <QuestionSearch key={q} query={q} status={status} />
    <div className="question-filters"><h2>{status === 'open' ? '남겨둔 질문' : '정리 완료'} · {data ? data.total : <Skeleton className="question-count-skeleton" aria-label="질문 수를 불러오는 중" />}</h2><div><Button aria-pressed={status === 'open'} onClick={() => setParams({ q, status: 'open' })}>열린 질문</Button><Button aria-pressed={status === 'done'} onClick={() => setParams({ q, status: 'done' })}>정리 완료</Button></div></div>
    <div className="question-feedback"><ErrorNotice error={error} />{error ? <Button onClick={reload}>다시 불러오기</Button> : <span role="status">{loading && data ? '질문 목록을 새로 확인하고 있습니다…' : ''}</span>}</div>
    <QuestionResults data={data} loading={loading} query={q} />
    <nav className="question-pages" aria-label="질문 페이지"><Button disabled={!data || page <= 1 || loading} onClick={() => setParams({ q, status, page: String(page - 1) })}>이전</Button><span>{data ? `${page} / ${Math.max(1, Math.ceil(data.total / 30))}` : '페이지 확인 중'}</span><Button disabled={!data || page >= Math.ceil(data.total / 30) || loading} onClick={() => setParams({ q, status, page: String(page + 1) })}>다음</Button></nav>
  </section>;
}
