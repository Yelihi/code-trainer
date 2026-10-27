import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Markdown } from './Markdown';
import { StartWorksheet } from './InterpretationPractice';
import { libraryPage } from './libraryTypes';
import './library.css';
import { Button } from './components/ui/button';

type WorksheetDocumentData = { title: string; questions: { id: string; section_id: string; prompt: string }[] };
export type Worksheet = { id: string; interpretation_id: string; interpretation_title: string; resource_id: string; revision: number;
  current_revision: number; source_name: string; state: 'queued' | 'running' | 'ready' | 'failed' | 'interrupted';
  document: WorksheetDocumentData | null; error: string; created_at: string };
type History = { items: (Pick<Worksheet, 'id' | 'interpretation_id' | 'revision' | 'source_name' | 'state' | 'created_at'> & { title: string })[]; total: number; page: number; pages: number };
const states = { queued: '생성 대기', running: '질문지 생성 중', ready: '질문지 준비 완료', failed: '생성 실패', interrupted: '생성 중단' };

export function WorksheetList() {
  const { userId } = useApp();
  const [params] = useSearchParams();
  return <List key={userId + ':' + params.toString()} />;
}
function List() {
  const [params, setParams] = useSearchParams();
  const interpretation = params.get('interpretation') ?? '', page = libraryPage(params.get('page'));
  const { data, error, reload } = useResource<History>(`/worksheets?page=${page}${interpretation ? '&interpretation_id=' + encodeURIComponent(interpretation) : ''}`);
  return <section className="worksheet-list"><header className="reference-page-heading"><div><span className="eyebrow">FROM READING TO QUESTIONS</span><h2>해석 자료의 실습 질문지</h2><p>AI가 제안한 질문을 따라, 이해한 내용을 자신의 말로 생각해보세요.</p></div><Link className="button" to="/explore">해석 자료 선택</Link></header>
    {interpretation && <div className="interpretation-list-links"><Link to={'/interpretations/' + interpretation}>선택한 해석 보기</Link><Link to="/explore/practice">전체 질문지 보기</Link></div>}
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="list" label="질문지 기록을 불러오는 중…" />}
    {data && <><div className="reference-list-caption"><span>{interpretation ? '선택한 해석의 질문지' : '나의 질문지'}</span><span>{data.total}개의 기록</span></div>
      {data.items.length ? <div className="reference-list">{data.items.map(item => <Link className="reference-list-item" key={item.id} to={'/worksheets/' + item.id + (item.state === 'ready' ? '/practice' : '')}><div><small>{states[item.state]} · 원문 v{item.revision}</small><h3>{item.title}</h3><p>{item.source_name}</p><footer><span>{item.state === 'ready' ? '질문과 내 작성분 열기' : 'AI 실습 질문'}</span><span>{timestamp(item.created_at)}</span></footer></div></Link>)}</div> : <div className="reference-empty"><h3>아직 질문지가 없습니다.</h3><p>완료된 해석에서 ‘실습용 질문지 만들기’를 눌러 시작하세요.</p></div>}
      {data.items.some(item => item.state === 'queued' || item.state === 'running') && <Button onClick={reload}>생성 상태 새로 확인</Button>}
      {data.pages > 1 && <nav className="pagination" aria-label="질문지 기록 페이지"><Button disabled={data.page <= 1} onClick={() => setParams({ ...(interpretation ? { interpretation } : {}), page: String(data.page - 1) })}>이전</Button><span>{data.page} / {data.pages}</span><Button disabled={data.page >= data.pages} onClick={() => setParams({ ...(interpretation ? { interpretation } : {}), page: String(data.page + 1) })}>다음</Button></nav>}</>}
  </section>;
}

export function WorksheetDetail() {
  const { id } = useParams(), { userId } = useApp();
  return <Detail key={userId + ':' + id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const [data, setData] = useState<Worksheet | null>(null), [error, setError] = useState(''), [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const result = await api<Worksheet>('/worksheets/' + id, 'GET', undefined, controller.signal);
        if (controller.signal.aborted) return;
        setData(result); setError('');
        if (result.state === 'queued' || result.state === 'running') timer = setTimeout(() => void load(), 2000);
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [id, reload]);
  return <main className="page reference-page interpretation-page"><div className="breadcrumb"><Link to="/explore/practice">실습하기</Link><span>/</span> 질문지</div>
    <ErrorNotice error={error} />{error && <Button onClick={() => setReload(n => n + 1)}>상태 다시 불러오기</Button>}
    {!data && !error && <LoadingSkeleton layout="editor" label="질문지를 불러오는 중…" />}
    {data && <><header className="reference-page-heading"><div><span className="eyebrow">{states[data.state]}</span><h1>{data.document?.title ?? data.interpretation_title}</h1><p>원문 v{data.revision} 기준 · {timestamp(data.created_at)}</p></div><Link className="button" to={'/interpretations/' + data.interpretation_id}>관련 해석 보기</Link></header>
      <aside className="interpretation-provenance"><strong>{data.source_name} · 원문 v{data.revision}</strong><p>이 질문지는 「{data.interpretation_title}」 해석을 바탕으로 AI가 만들었습니다.{data.current_revision !== data.revision && ` 원문에는 최신 v${data.current_revision}가 있지만, 이 질문지는 원래 해석에 연결되어 있습니다.`}</p><Link to={'/library/' + data.resource_id}>원문과 버전 보기</Link></aside>
      {(data.state === 'queued' || data.state === 'running') && <section className="reference-empty" role="status"><h2>{states[data.state]}입니다.</h2><p>다른 화면으로 이동해도 실습하기에서 다시 확인할 수 있습니다.</p></section>}
      {(data.state === 'failed' || data.state === 'interrupted') && <section className="interpretation-recovery"><p role="alert">{data.error}</p><p>이 기록을 보존하고 같은 해석에서 새 질문지를 만듭니다.</p><StartWorksheet interpretationId={data.interpretation_id} retryId={data.id} /></section>}
      {data.document && <><WorksheetDocument document={data.document} interpretationId={data.interpretation_id} /><Link className="button primary" to={'/worksheets/' + data.id + '/practice'}>내 답변·요약 작성하기</Link></>}
      <Link className="text-link" to={'/explore/practice?interpretation=' + data.interpretation_id}>이 해석의 질문지 기록</Link>
    </>}
  </main>;
}

export function WorksheetDocument({ document, interpretationId }: { document: WorksheetDocumentData; interpretationId: string }) {
  return <section className="worksheet-questions"><h2>AI가 만든 질문</h2><p>먼저 자신의 말과 예시로 설명해보세요. 필요하면 관련 해석을 다시 읽을 수 있습니다.</p>
    <ol>{document.questions.map(question => <li key={question.id}><Markdown language="">{question.prompt}</Markdown><Link to={'/interpretations/' + interpretationId + '#' + question.section_id}>관련 개념 다시 보기</Link></li>)}</ol>
  </section>;
}
