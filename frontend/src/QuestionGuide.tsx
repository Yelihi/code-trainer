import { memo, useEffect, useState } from 'react';
import { api, errorMessage } from './api';
import { ErrorNotice } from './App';
import { useResource } from './useResource';
import { Button } from './components/ui/button';
import { QuestionGuideSkeleton } from './QuestionSkeletons';
import { LinkedQuestionSource } from './QuestionSources';
import type { Guide } from './questionTypes';

export const QuestionGuide = memo(function QuestionGuide({ id, revision, canStart }: { id: string; revision: number; canStart: boolean }) {
  const { data, error: loadError, loading, reload, update } = useResource<{ guide: Guide | null }>('/questions/' + id + '/guide', { preserveData: true });
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [lastReady, setLastReady] = useState<Guide | null>(null);
  const guide = data?.guide;
  const generating = guide?.state === 'queued' || guide?.state === 'running';
  useEffect(() => { if (guide?.state === 'ready' && guide.result) setLastReady(guide); }, [guide]);
  useEffect(() => {
    if (!generating || loading) return;
    const timer = setTimeout(reload, 2500);
    return () => clearTimeout(timer);
  }, [generating, loading, reload]);
  async function start() {
    if (busy || generating || !canStart) return;
    setBusy(true); setError('');
    try {
      const created = await api<Guide>('/questions/' + id + '/guide', 'POST', { revision, request_id: crypto.randomUUID() });
      update({ guide: created });
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  const visible = guide?.result ? guide : lastReady;
  return <section className="question-section"><h2>AI 탐구 가이드</h2><p>연결한 자료의 현재 본문만 사용해 다시 읽을 부분과 직접 해볼 활동을 제안합니다. 질문의 답을 대신 작성하지 않습니다.</p><Button className="primary question-guide-start" disabled={!canStart || busy || generating || loading} onClick={() => void start()}>AI 탐구 시작</Button>
    <div className="question-feedback"><ErrorNotice error={error || loadError || guide?.error || ''} />{loadError && <Button onClick={reload}>가이드 다시 불러오기</Button>}<span role="status">{busy || generating ? (visible ? '이전 가이드를 유지하면서 새 가이드를 준비하고 있습니다…' : '가이드를 준비하고 있습니다…') : loading && data ? '가이드를 새로 확인하고 있습니다…' : ''}</span></div>
    <QuestionGuideContent guide={visible ?? null} revision={revision} pending={busy || generating || (loading && !data)} />
  </section>;
});

export const QuestionGuideContent = memo(function QuestionGuideContent({ guide, revision, pending }: { guide: Guide | null; revision: number; pending: boolean }) {
  const result = guide?.result;
  return <div className="question-guide" aria-busy={pending}>{result ? <><p className="question-guide-version">{guide.question_revision !== revision ? '질문이 변경된 이전 가이드입니다.' : ''}</p><h3>{result.title}</h3><p><strong>다시 읽기</strong> {result.reading}</p><h4>확인할 쟁점</h4><ul>{result.checks.map((item, index) => <li key={index}>{item}</li>)}</ul><p><strong>직접 해보기</strong> {result.practice}</p><p><strong>남길 결과</strong> {result.expected_output}</p><div className="question-guide-sources">{result.source_ids.map(sourceId => <LinkedQuestionSource key={sourceId} id={sourceId} />)}</div></> : pending ? <QuestionGuideSkeleton /> : <p>관련 자료를 연결하고 질문을 저장한 뒤 AI 탐구를 시작하세요.</p>}</div>;
});
