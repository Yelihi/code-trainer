import { memo, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useResource } from './useResource';
import { ErrorNotice } from './App';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Skeleton } from './components/ui/skeleton';
import type { Question, Resource } from './questionTypes';

export const LinkedQuestionSource = memo(function LinkedQuestionSource({ id }: { id: string }) {
  const { data } = useResource<Resource>('/resources/' + id, { preserveData: true });
  return <Link className="button question-linked-source" to={'/library/' + id}>{data ? data.name + ' 열기' : <><span className="sr-only">연결 자료 열기</span><Skeleton className="question-source-name-skeleton" aria-hidden="true" /></>}</Link>;
});

export function QuestionSources({ current, busy, onSave, onDraft }: { current: Question; busy: boolean; onSave: (next: Question) => Promise<void>; onDraft: (next: Question) => void }) {
  const [search, setSearch] = useState(''), [query, setQuery] = useState('');
  useEffect(() => { const timer = setTimeout(() => setQuery(search), 250); return () => clearTimeout(timer); }, [search]);
  const { data: resources, error, loading, reload } = useResource<{ items: Resource[] }>('/resources?q=' + encodeURIComponent(query), { preserveData: true });
  return <section className="question-section"><h2>관련 자료</h2><p>탐구할 때 사용할 근거를 선택하세요. 긴 자료는 관련 구절을 입력해야 합니다.</p><div className="question-capture"><Input aria-label="연결할 자료 검색" value={search} onChange={e => setSearch(e.target.value)} placeholder="자료 제목 검색" /></div>
    {search && <div className="question-source-search"><div className="question-feedback"><ErrorNotice error={error} />{error && <Button onClick={reload}>자료 다시 불러오기</Button>}</div><div className="question-resource-results" aria-busy={loading || query !== search}>{loading || query !== search ? <><Skeleton className="question-action-skeleton" aria-hidden="true" /><span className="sr-only" role="status">자료를 찾고 있습니다</span></> : resources?.items.filter(item => item.state === 'ready' && !current.links.some(link => link.resource_id === item.id)).map(item => <Button key={item.id} disabled={current.links.length >= 3 || busy} onClick={() => void onSave({ ...current, links: [...current.links, { resource_id: item.id, excerpt: '' }] })}>{item.name} 연결</Button>)}</div></div>}
    {current.links.map(link => <div className="question-link" key={link.resource_id}><div><LinkedQuestionSource id={link.resource_id} /><Button disabled={busy} onClick={() => void onSave({ ...current, links: current.links.filter(item => item.resource_id !== link.resource_id) })}>연결 해제</Button></div><Label>관련 구절 (긴 자료일 때 필수)<Textarea disabled={busy} rows={3} value={link.excerpt} maxLength={6000} onChange={e => onDraft({ ...current, links: current.links.map(item => item.resource_id === link.resource_id ? { ...item, excerpt: e.target.value } : item) })} /></Label></div>)}
  </section>;
}
