import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useResource } from './useResource';
export function ContextQuestions() {
  const { pathname, search } = useLocation();
  const { data, reload } = useResource<{ items: { id: string; text: string; status: string }[] }>('/related-questions?path=' + encodeURIComponent((pathname + search).slice(0, 300)), { preserveData: true });
  useEffect(() => { window.addEventListener('questions-changed', reload); return () => window.removeEventListener('questions-changed', reload); }, [reload]);
  if (!data?.items.length || pathname.startsWith('/questions')) return null;
  return <section className="page contextual-questions"><h2>이 학습에 남긴 질문</h2>{data.items.map(item => <div className="learning-row" key={item.id}><Link className="text-link" to={'/questions/' + item.id}>{item.text}</Link><small>{item.status === 'done' ? '해결됨' : '미해결'}</small></div>)}</section>;
}
