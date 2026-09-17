import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ErrorNotice, useApp, useResource } from './App';
import { safeSourceUrl, timestamp } from './api';

type Source = { id: string; context_id: string | null; title: string; name: string; kind: string; url: string | null; has_content: boolean; state: string; created_at: string; content?: string | null };

export function Sources() {
  const { isAdmin } = useApp();
  const { sourceId } = useParams();
  if (!isAdmin) return <main className="page"><h1>관리자 전용 메뉴입니다</h1><Link to="/">학습 공간으로 돌아가기</Link></main>;
  return sourceId ? <SourceDetail id={sourceId} /> : <SourceList />;
}

function SourceList() {
  const { data, error, reload } = useResource<Source[]>('/admin/sources');
  const [params, setParams] = useSearchParams();
  const pages = Math.max(1, Math.ceil((data?.length ?? 0) / 6));
  const page = Math.min(pages, Math.max(1, Math.floor(Number(params.get('page')) || 1)));
  return <main className="page"><div className="breadcrumb">관리자<span>/</span> 원본 자료</div><span className="eyebrow">SOURCE LIBRARY</span><h1>학습의 출발점</h1>
    <p className="page-intro">등록한 링크와 원본 문서를 모았습니다. 생성에 실패한 자료도 여기서 확인할 수 있습니다.</p>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}{!data && !error && <p role="status">자료를 불러오는 중…</p>}
    {data?.length === 0 && <p className="empty-state">아직 등록한 자료가 없습니다.</p>}
    <div className="source-library">{data?.slice((page - 1) * 6, page * 6).map(item => <Link className="source-card" key={item.id} to={`/admin/sources/${encodeURIComponent(item.id)}`}>
      <small>{item.kind === 'url' ? 'URL' : item.kind === 'text' ? item.name || '텍스트 · Markdown' : '이전 자료'} · {timestamp(item.created_at)}</small><h2>{item.title}</h2><p>{item.url || item.name || '직접 입력한 학습 자료'}</p>
      <span>{item.has_content ? '원문 보기 →' : '출처 확인 →'}{item.state === 'failed' ? ' · 생성 실패' : ''}</span>
    </Link>)}</div>
    {!!data?.length && <nav className="pagination" aria-label="원본 자료 페이지"><button disabled={page === 1} onClick={() => setParams({ page: String(page - 1) })}>← 이전</button><span>{page} / {pages} 페이지 · {data.length}개 자료</span><button disabled={page === pages} onClick={() => setParams({ page: String(page + 1) })}>다음 →</button></nav>}
  </main>;
}

function SourceDetail({ id }: { id: string }) {
  const { data, error, reload } = useResource<Source>(`/admin/sources/${encodeURIComponent(id)}`);
  return <main className="page"><div className="breadcrumb"><Link to="/admin/sources">원본 자료</Link><span>/</span> 원문 보기</div><ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <p role="status">원문을 불러오는 중…</p>}{data && <><h1>{data.title}</h1><p className="muted">{data.name || (data.kind === 'url' ? 'URL에서 가져온 본문' : '학습 자료')} · {timestamp(data.created_at)}</p>
      <div className="unit-actions">{safeSourceUrl(data.url ?? undefined) && <a className="button" href={safeSourceUrl(data.url ?? undefined)} target="_blank" rel="noreferrer">원본 링크 열기 ↗</a>}{data.context_id && <Link className="button" to={`/learn/${data.context_id}`}>학습 과정 보기 →</Link>}</div>
      {data.content != null ? <pre className="source-document">{data.content}</pre> : <p className="notice">저장된 원문이 없습니다. 이전 자료는 원문을 보관하지 않았으며, URL을 가져오지 못한 경우에도 본문이 없습니다. 출처 링크가 있으면 원본 페이지에서 확인해주세요.</p>}
    </>}
  </main>;
}
