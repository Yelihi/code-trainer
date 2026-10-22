import { useState } from 'react';
import { Markdown } from './Markdown';
import { ErrorNotice } from './App';
import { errorMessage } from './api';
import { suggestionBlock, type Proposal, type ReferenceNote } from './referenceTypes';

export function ReferenceContentReview({ note, proposal, pending, onApply, onEdit }: {
  note: ReferenceNote; proposal: Proposal; pending: boolean; onApply: (issues: number[]) => Promise<void>; onEdit: () => void;
}) {
  const [checked, setChecked] = useState<number[]>([]);
  const [error, setError] = useState('');
  const review = proposal.review!;
  const current = proposal.revision === note.revision;
  async function apply() {
    setError('');
    try { await onApply(checked); } catch (e) { setError(errorMessage(e)); }
  }
  return <section id="reference-content-review" className="reference-content-review" aria-label="AI 내용 검토" aria-live="polite">
    <header><span className="eyebrow">CONTENT REVIEW · v{proposal.revision}</span><h3>{review.issues.length ? '본문에서 먼저 확인할 내용이 있습니다.' : '검토 범위에서 수정할 오류를 발견하지 못했습니다.'}</h3></header>
    <Markdown language="">{review.summary}</Markdown>
    <p className="muted">AI의 지식에 기반한 검토입니다. 원문 자료나 최신 정보를 외부에서 확인한 결과는 아니며, 정확성을 보장하지 않습니다.</p>
    {!current && <p className="notice">이전 v{proposal.revision}의 검토입니다. 저장한 v{note.revision}에서 AI 후보 생성·내용 검토를 다시 진행해주세요.</p>}
    {review.issues.map((issue, i) => {
      const blocked = suggestionBlock(note.body, issue);
      return <article className="reference-review-issue" data-selected={checked.includes(i)} key={i}>
        <h4><span>{i + 1}</span>{issue.kind === 'correction_needed' ? '수정 필요' : '추가 확인 필요'}</h4>
        <div className="reference-replacement-comparison">
          <div><h5>현재 문장</h5><blockquote><Markdown language="">{issue.quote}</Markdown></blockquote></div>
          <div className="reference-replacement"><h5>AI 추천 문장</h5>{issue.replacement ? <blockquote><Markdown language="">{issue.replacement}</Markdown></blockquote> : <p className="muted">바로 교체할 문장이 아직 준비되지 않았습니다.</p>}</div>
        </div>
        <dl><dt>검토 이유</dt><dd><Markdown language="">{issue.explanation}</Markdown></dd><dt>수정·확인 안내</dt><dd><Markdown language="">{issue.suggestion}</Markdown></dd></dl>
        {current && <><label className="reference-replacement-choice"><input type="checkbox" checked={checked.includes(i)} disabled={pending || !!blocked} onChange={e => setChecked(e.target.checked ? [...checked, i] : checked.filter(n => n !== i))} /><span>{i + 1}번 추천 문장을 본문에 반영</span></label>{blocked && <p className="muted">{blocked}</p>}</>}
      </article>;
    })}
    {review.issues.length > 0 && <footer><p>체크만으로 본문이 바뀌지는 않습니다. 선택한 변경을 반영하면 새 버전으로 저장되며, 이전 본문은 버전 기록에 남습니다. 이후 새 본문을 다시 검토해주세요.</p><ErrorNotice error={error} /><div className="reference-actions"><button type="button" className="primary" disabled={pending || !current || checked.length === 0} onClick={() => void apply()}>{pending ? '처리 중…' : `선택한 변경 ${checked.length}개 반영`}</button><button type="button" disabled={pending} onClick={onEdit}>본문 직접 수정</button></div></footer>}
  </section>;
}
