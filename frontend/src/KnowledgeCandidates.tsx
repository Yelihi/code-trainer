import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ErrorNotice, useApp, useResource } from './App';
import { timestamp } from './api';
import { libraryPage } from './libraryTypes';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Markdown } from './Markdown';
import './library.css';

export type ReviewedMaterial = { id: string; kind: 'interpretation' | 'practice'; origin_id: string; revision: number; current_revision: number; title: string; authorship: 'ai' | 'user'; body: string; state: 'eligible' | 'stale' | 'archived' | 'empty'; reason: string; interpretation_id: string; resource_id: string; raw_revision: number; source_name: string; reviewed_at: string };
const states = { eligible: '추출 가능', stale: '변경됨 · 다시 검토', archived: '원문 보관됨', empty: '작성 내용 없음' };
function origin(material: ReviewedMaterial) { return material.kind === 'interpretation' ? '/interpretations/' + material.origin_id : '/worksheets/' + material.origin_id + '/practice'; }

export function KnowledgeCandidates() {
  const { userId } = useApp();
  return <List key={userId} />;
}
function List() {
  const [params, setParams] = useSearchParams(), page = libraryPage(params.get('page'));
  const { data, error, reload } = useResource<{ items: ReviewedMaterial[]; page: number; pages: number; total: number }>('/material-reviews?page=' + page);
  return <main className="page reference-page library-page"><div className="breadcrumb">데이터 쌓기<span>/</span>추출 가능 자료</div>
    <header className="reference-page-heading"><div><span className="eyebrow">UNDERSTANDING, READY TO CONNECT</span><h1>확인한 이해를 모으는 곳.</h1><p>직접 확인한 해석과 내 작성분을 버전별로 보관합니다.<br />원문이나 작성분이 바뀌면 다시 검토할 수 있도록 알려드립니다.</p></div></header>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="list" label="검토한 자료를 불러오는 중…" />}
    {data && <><div className="reference-list-caption"><span>검토한 버전</span><span>{data.total}개</span></div>
      {data.items.length ? <div className="reference-list">{data.items.map(item => <Link className="reference-list-item" key={item.id} to={'/knowledge/candidates/' + item.id}><span className="reference-list-mark" aria-hidden="true">✓</span><div><small>{states[item.state]} · {item.authorship === 'ai' ? 'AI 해석' : '내 답변·요약'}</small><h2>{item.title}</h2><p>{item.source_name} · 원문 v{item.raw_revision}{item.kind === 'practice' && ` · 작성분 v${item.revision}`}</p><footer><span>사용자 확인</span><span>{timestamp(item.reviewed_at)}</span></footer></div><span aria-hidden="true">→</span></Link>)}</div> : <section className="reference-empty"><h2>아직 확인한 자료가 없습니다.</h2><p>해석 문서의 ‘이 버전 정리 확인’이나<br />저장한 답변·요약의 ‘이 버전 검토 완료’로 추가하세요.</p><Link className="button" to="/explore">해석 살펴보기</Link><Link className="button" to="/explore/practice">내 실습 살펴보기</Link></section>}
      {data.pages > 1 && <nav className="pagination" aria-label="검토한 자료 페이지"><button disabled={data.page <= 1} onClick={() => setParams({ page: String(data.page - 1) })}>이전</button><span>{data.page} / {data.pages}</span><button disabled={data.page >= data.pages} onClick={() => setParams({ page: String(data.page + 1) })}>다음</button></nav>}</>}
  </main>;
}

export function KnowledgeCandidateDetail() {
  const { id } = useParams(), { userId } = useApp();
  return <Detail key={userId + ':' + id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const { data, error, reload } = useResource<ReviewedMaterial>('/material-reviews/' + id);
  return <main className="page reference-page interpretation-page"><div className="breadcrumb"><Link to="/knowledge/candidates">추출 가능 자료</Link><span>/</span>검토한 버전</div>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="article" label="검토한 본문을 불러오는 중…" />}
    {data && <><span className="eyebrow">{states[data.state]}</span><h1>{data.title}</h1><p>{data.authorship === 'ai' ? 'AI가 작성한 해석을 사용자가 확인했습니다.' : `내가 작성하고 검토한 답변·요약 v${data.revision}입니다.`} · {timestamp(data.reviewed_at)}</p>
      <aside className="interpretation-provenance"><strong>{data.source_name} · 원문 v{data.raw_revision}</strong><p>{data.reason || '확인한 버전의 본문입니다. 이 확인 자체가 AI 정답 판정이나 숙달 기록은 아닙니다.'}</p><Link to={origin(data)}>원래 학습 화면 보기 →</Link><p><Link to={'/library/' + data.resource_id}>원문과 버전 보기 →</Link></p></aside>
      <article className="interpretation-section"><Markdown language="">{data.body}</Markdown></article>
    </>}
  </main>;
}
