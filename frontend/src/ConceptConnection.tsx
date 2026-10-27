import { useEffect, useState } from 'react';
import { api, errorMessage } from './api';
import { Markdown } from './Markdown';
import type { Candidate, Concept, ConceptMatch } from './referenceTypes';
import { Button } from './components/ui/button';

export function ConceptConnection({ candidate, original, matches, selected, decided, onSelect, onNew }: {
  candidate: Candidate; original: Candidate; matches: ConceptMatch[]; selected?: Concept; decided: boolean;
  onSelect: (concept: Concept) => void; onNew: () => void;
}) {
  const [found, setFound] = useState<{ lookup: string; matches: ConceptMatch[] }>({ lookup: '', matches: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const lookup = JSON.stringify({ pref_label: original.pref_label, aliases: original.aliases });
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true); setError('');
      api<ConceptMatch[]>('/knowledge/concept-matches', 'POST', JSON.parse(lookup), controller.signal)
        .then(result => { if (!controller.signal.aborted) setFound({ lookup, matches: result }); })
        .catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [lookup, retry]);
  const options = [...matches, ...(found.lookup === lookup ? found.matches : [])].filter((m, i, all) => all.findIndex(x => x.concept.id === m.concept.id) === i).slice(0, 3);
  if (selected && !options.some(m => m.concept.id === selected.id)) options.unshift({ concept: selected, reason: '직접 선택한 기존 개념입니다. 이번 자료의 설명과 비교해주세요.' });
  return <section className="concept-connection" aria-label={`${original.pref_label || '새 개념'}의 기존 개념 비교`}>
    <h4>기존 개념과 비교하기</h4>
    <p className="muted">정의와 범위가 같은 개념에만 연결해주세요. 이름이 비슷해도 의미가 다르면 별개 개념으로 추가하세요.</p>
    <div className="concept-original"><small>이번 자료의 개념</small><strong>{original.pref_label || '아래에서 개념명을 입력해주세요.'}</strong>
      {original.definition && <Markdown language="">{original.definition}</Markdown>}<span>범위 · {original.scope || '미지정'}</span>
    </div>
    {loading && <p role="status">비슷한 이름과 별칭을 찾고 있습니다…</p>}
    {error && <p role="alert">기존 개념 검색을 완료하지 못했습니다. {error} <Button type="button" onClick={() => setRetry(v => v + 1)}>다시 검색</Button></p>}
    {!loading && !error && found.lookup === lookup && !options.length && <p className="muted">현재 추천 후보가 없습니다. 다른 이름으로 저장돼 있을 수 있으니 기존 개념 검색도 확인해주세요.</p>}
    <div className="concept-match-list">{options.map(match => <article className="concept-match" key={match.concept.id}>
      <small>{matches.some(m => m.concept.id === match.concept.id) ? 'AI 연결 제안' : '기존 개념 검색'}</small>
      <strong>{match.concept.pref_label}</strong><Markdown language="">{match.concept.definition}</Markdown>
      <p className="concept-match-scope">범위 · {match.concept.scope || '미지정'}</p>
      {!!match.concept.aliases.length && <p className="muted">별칭 · {match.concept.aliases.join(', ')}</p>}
      <p className="concept-match-reason">{match.reason}</p>
      <Button type="button" aria-pressed={decided && candidate.existing_id === match.concept.id} onClick={() => onSelect(match.concept)}>
        {decided && candidate.existing_id === match.concept.id ? '이 개념에 연결하도록 선택됨' : '기존 개념에 연결'}
      </Button>
    </article>)}</div>
    <div className="concept-choice"><Button type="button" aria-pressed={decided && !candidate.existing_id} onClick={onNew}>별개 개념으로 추가</Button>
      <p role="status">{!decided ? '등록 방식을 선택해주세요.' : candidate.existing_id ? '기존 개념에 이번 자료의 근거를 연결합니다.' : '새 개념을 만들도록 선택했습니다.'}</p>
    </div>
  </section>;
}
