import { Select } from './Select';
import { AnimatedDetails } from './AnimatedDetails';
import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { Link } from 'react-router-dom';
import { InlineMarkdown } from './Markdown';
import { assistanceLabels, languages, type Language } from './api';
import { layoutGraph, neighbors, zoomView, type GraphSource, type GraphEvidence, type KnowledgeGraph, type Point, type ViewBox } from './knowledgeGraph';

const kindLabels = { concept: '정리한 개념', foundation: '기초 학습', unit: '자료 학습', note: '레퍼런스 노트' };

function SourceLink({ source }: { source: GraphSource }) {
  return source.material_review_id ? <Link className="text-link" to={'/knowledge/candidates/' + source.material_review_id}>{source.authorship === 'ai' ? 'AI 해석' : '내 답변·요약'} · 원문 v{source.raw_revision} · 검토한 자료 열기 ↗</Link> : source.note_id ? <Link className="text-link" to={'/references/' + source.note_id}>근거 노트 열기 ↗</Link> : null;
}

function ExerciseLinks({ exercises }: { exercises: GraphEvidence[] }) {
  return <ul className="graph-exercises">{exercises.map(exercise => <li key={exercise.id}>
    <small>{exercise.kind === 'FOUNDATION' ? '기초 구현' : exercise.kind} · {assistanceLabels[exercise.assistance ?? 'unknown']}</small>
    <strong>{exercise.title}</strong>
    {exercise.deleted ? <span className="muted">학습 자료가 삭제되었습니다.</span> : exercise.withdrawn ? <span className="muted">제공이 중단된 문제입니다.</span> : <div>
      <Link className="text-link" to={exercise.kind === 'FOUNDATION' ? `/foundations/${exercise.unit_id}/practice` : `/practice/${exercise.set_id}?exercise=${exercise.id}`}>풀었던 문제 열기 ↗</Link>
      <Link className="text-link" to={exercise.kind === 'FOUNDATION' ? `/foundations/${exercise.unit_id}` : exercise.unit_id ? `/learn/${exercise.context_id}/units/${exercise.unit_id}` : `/learn/${exercise.context_id}`}>개념 다시 읽기</Link>
    </div>}
  </li>)}</ul>;
}

export function KnowledgeExplorer({ data }: { data: KnowledgeGraph }) {
  const layout = useMemo(() => layoutGraph(data.nodes, data.edges), [data.nodes, data.edges]);
  const [view, setView] = useState<ViewBox>(layout.bounds);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'graph' | 'relations'>('graph');
  const [relationKind, setRelationKind] = useState('all');
  const [compact, setCompact] = useState(() => window.matchMedia('(max-width: 900px)').matches);
  const svg = useRef<SVGSVGElement>(null);
  const panel = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLElement | SVGElement | null>(null);
  const search = useRef<HTMLInputElement>(null);
  const drag = useRef<{ pointerId: number; start: Point; view: ViewBox; scale: number } | null>(null);
  const edges = useMemo(() => data.edges.filter(edge => relationKind === 'all' || edge.kind === relationKind), [data.edges, relationKind]);
  const active = hovered ?? selected;
  const connected = active ? neighbors(active, edges) : null;
  const node = data.nodes.find(item => item.id === selected);
  const matches = data.nodes.filter(item => `${item.label} ${item.scope}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const matching = new Set(matches.map(item => item.id));
  const nodeEdges = edges.filter(edge => edge.source === selected || edge.target === selected);
  const labels = new Map(data.nodes.map(item => [item.id, item.label]));

  function choose(id: string, element?: HTMLElement | SVGElement) {
    if (element && !panel.current?.contains(element)) trigger.current = element;
    setSelected(id); setHovered(null);
  }
  function close() {
    setSelected(null); setHovered(null);
    requestAnimationFrame(() => {
      if (trigger.current?.isConnected) trigger.current.focus({ preventScroll: true });
      else search.current?.focus({ preventScroll: true });
    });
  }
  useEffect(() => {
    if (selected) { panel.current?.focus({ preventScroll: true }); panel.current?.scrollTo(0, 0); }
  }, [selected]);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 900px)');
    const update = () => setCompact(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    setView(layout.bounds);
  }, [layout]);
  useEffect(() => {
    const element = svg.current;
    if (!element || mode !== 'graph') return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      const matrix = element.getScreenCTM();
      if (!matrix) return;
      const anchor = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
      setView(current => zoomView(current, Math.exp(Math.max(-200, Math.min(200, event.deltaY)) * .002), anchor, layout.bounds));
    };
    element.addEventListener('wheel', wheel, { passive: false });
    return () => element.removeEventListener('wheel', wheel);
  }, [layout.bounds, mode]);

  function zoom(factor: number) {
    setView(current => zoomView(current, factor, { x: current.x + current.width / 2, y: current.y + current.height / 2 }, layout.bounds));
  }
  function startPan(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.button !== 0 || (event.target as Element).closest('[data-node]')) return;
    drag.current = { pointerId: event.pointerId, start: { x: event.clientX, y: event.clientY }, view, scale: svg.current?.getScreenCTM()?.a || 1 };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pan(event: ReactPointerEvent<SVGSVGElement>) {
    const start = drag.current;
    if (!start || start.pointerId !== event.pointerId) return;
    setView({ ...start.view, x: start.view.x - (event.clientX - start.start.x) / start.scale, y: start.view.y - (event.clientY - start.start.y) / start.scale });
  }

  return <section className="graph-explorer" aria-label="지식과 학습의 연결" onKeyDown={event => { if (event.key === 'Escape' && selected) { event.stopPropagation(); close(); } }}>
    <div className="graph-toolbar">
      <div className="graph-view-switch" aria-label="보기 방식">
        <button aria-pressed={mode === 'graph'} onClick={() => setMode('graph')}>지식 그래프</button>
        <button aria-pressed={mode === 'relations'} onClick={() => setMode('relations')}>관계 목록 <span>{data.edges.length}</span></button>
      </div>
      <label className="graph-search"><span className="sr-only">노드 검색</span><span aria-hidden="true">⌕</span><input ref={search} type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="개념이나 단원 찾기" /></label>
      <label className="graph-filter"><span className="sr-only">관계 종류</span><Select value={relationKind} onChange={event => setRelationKind(event.target.value)}><option value="all">모든 관계</option><option value="coverage">다루는 개념</option><option value="evidence">풀이 근거</option><option value="prerequisite">선행 단원</option><option value="PREREQUISITE_OF">선행 개념</option><option value="BROADER_THAN">상하 개념</option><option value="USED_IN">활용 관계</option><option value="RELATED_TO">연관 개념</option></Select></label>
    </div>
    {query.trim() && <div className="graph-search-results" aria-live="polite"><small>{matches.length}개 노드</small>{matches.map(item => <button key={item.id} onClick={event => choose(item.id, event.currentTarget)}>{item.label}</button>)}{!matches.length && <span>일치하는 개념이나 단원이 없습니다.</span>}</div>}
    <div className={`graph-body ${node ? 'with-drawer' : ''}`}>
      <div className="graph-surface" inert={!!node && compact}>
        {mode === 'graph' ? <>
          <div className="graph-canvas-caption"><span className="eyebrow">YOUR KNOWLEDGE, CONNECTED</span><span>{data.nodes.length}개 노드 · {edges.length}개 연결</span></div>
          <svg ref={svg} className="knowledge-canvas" viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`} role="group" aria-label="지식 그래프. 노드를 선택하면 상세 내용을 볼 수 있습니다." aria-describedby="graph-instructions" tabIndex={0}
            onPointerDown={startPan} onPointerMove={pan} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }} onLostPointerCapture={() => { drag.current = null; }}
            onKeyDown={event => {
              if (event.key === '+' || event.key === '=') { event.preventDefault(); zoom(.8); }
              else if (event.key === '-') { event.preventDefault(); zoom(1.25); }
              else if (event.key === 'Home') { event.preventDefault(); setView(layout.bounds); }
              else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
                event.preventDefault();
                setView(current => ({ ...current, x: current.x + (event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0) * current.width * .1,
                  y: current.y + (event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0) * current.height * .1 }));
              }
            }}>
            <defs><marker id="graph-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="#716681" strokeWidth="1.5" /></marker><marker id="graph-arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="#8ce6ce" strokeWidth="1.5" /></marker></defs>
            <g aria-hidden="true">{edges.map(edge => {
              const a = layout.positions.get(edge.source)!, b = layout.positions.get(edge.target)!;
              const distance = Math.hypot(b.x - a.x, b.y - a.y) || 1, dx = (b.x - a.x) / distance, dy = (b.y - a.y) / distance;
              const highlighted = active === edge.source || active === edge.target;
              const dimmed = (!!active && !highlighted) || (!!query.trim() && !matching.has(edge.source) && !matching.has(edge.target));
              return <path key={edge.id} className={`graph-edge ${edge.kind} ${highlighted ? 'highlighted' : ''} ${dimmed ? 'dimmed' : ''}`} d={`M ${a.x + dx * 26} ${a.y + dy * 26} L ${b.x - dx * 30} ${b.y - dy * 30}`} markerEnd={edge.kind === 'RELATED_TO' ? undefined : `url(#graph-arrow${highlighted ? '-active' : ''})`} />;
            })}</g>
            {data.nodes.map(item => {
              const point = layout.positions.get(item.id)!;
              const dimmed = (connected && !connected.has(item.id)) || (query.trim() && !matching.has(item.id));
              const chars = Array.from(item.label), lines = [chars.slice(0, 13).join(''), chars.length > 26 ? chars.slice(13, 25).join('') + '…' : chars.slice(13).join('')];
              return <g key={item.id} data-node={item.id} role="button" tabIndex={0} aria-label={`${item.label} · ${kindLabels[item.kind]} · 통과 문제 ${item.exercise_ids.length}개`} aria-pressed={selected === item.id}
                className={`graph-node ${item.kind} ${active === item.id ? 'active' : ''} ${connected?.has(item.id) ? 'connected' : ''} ${dimmed ? 'dimmed' : ''}`} transform={`translate(${point.x} ${point.y})`}
                onMouseEnter={() => setHovered(item.id)} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered(item.id)} onBlur={() => setHovered(null)}
                onClick={event => choose(item.id, event.currentTarget)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(item.id, event.currentTarget); } }}>
                <title>{item.label}</title><circle className="node-halo" r="35" />
                {item.kind === 'concept' ? <circle className="node-core" r="21" /> : <rect className="node-core" x="-20" y="-20" width="40" height="40" rx={item.kind === 'foundation' ? 12 : 5} />}
                <text className="node-symbol" textAnchor="middle" y="5" aria-hidden="true">{item.kind === 'concept' ? '◈' : item.kind === 'foundation' ? '⌘' : '≡'}</text>
                <text className="node-label" textAnchor="middle" y="47" aria-hidden="true">{lines.map((line, i) => <tspan key={i} x="0" dy={i ? 19 : 0}>{line}</tspan>)}</text>
              </g>;
            })}
          </svg>
          <div className="graph-controls" aria-label="그래프 배율"><button aria-label="확대" onClick={() => zoom(.8)}>＋</button><output aria-label="현재 배율">{Math.round(layout.bounds.width / view.width * 100)}%</output><button aria-label="축소" onClick={() => zoom(1.25)}>−</button><button onClick={() => setView(layout.bounds)}>전체 보기</button></div>
        </> : <div className="graph-relations"><h2>관계를 따라 읽기</h2><p>선의 방향과 연결한 이유를 확인하세요.</p>{edges.filter(edge => !query.trim() || matching.has(edge.source) || matching.has(edge.target)).map(edge => <article key={edge.id}>
          <div><button onClick={event => choose(edge.source, event.currentTarget)}>{labels.get(edge.source)}</button><span aria-label="방향">{edge.kind === 'RELATED_TO' ? '↔' : '→'}</span><button onClick={event => choose(edge.target, event.currentTarget)}>{labels.get(edge.target)}</button></div><small>{edge.label}</small><p>{edge.description}</p>
        </article>)}{!edges.some(edge => !query.trim() || matching.has(edge.source) || matching.has(edge.target)) && <p className="notice">표시할 관계가 없습니다. 다른 관계 종류를 선택하거나 개념 정리를 실행해주세요.</p>}</div>}
      </div>
      {node && <aside className="graph-drawer" ref={panel} tabIndex={-1} aria-labelledby="graph-node-title">
        <header><span className={`graph-kind ${node.kind}`}>{kindLabels[node.kind]}</span><button className="icon-button" aria-label="상세 패널 닫기" onClick={close}>×</button></header>
        <h2 id="graph-node-title">{node.label}</h2><p className="graph-node-meta">{languages[node.scope as Language] ?? node.scope} · 통과 문제 {node.exercise_ids.length}개</p>
        {node.added_at && <p>직접 추가한 학습 · {new Date(node.added_at).toLocaleDateString('ko-KR')}</p>}
        {node.note_id && <Link className="button" to={'/references/' + node.note_id}>레퍼런스 노트 · 설명 복습 열기 ↗</Link>}
        {(node.note_id || node.ontology_status || node.added_at && node.source_available) && <Link className="button" to={`/github/share?kind=${node.note_id ? 'note' : node.ontology_status ? 'concept' : 'learning'}&id=${encodeURIComponent(node.note_id ?? node.id)}`}>GitHub 이슈로 공유 ↗</Link>}
        {node.needs_review && <p className="notice">등록 이후 노트가 변경되었습니다. 근거를 다시 검토해주세요.</p>}
        {!!node.aliases?.length && <p>별칭 · {node.aliases.join(', ')}</p>}
        {node.ontology_status === 'provisional' && <p className="muted">기존 단원에서 옮긴 개념입니다. 다른 노트와 연결할 때 정의와 적용 범위를 확인해주세요.</p>}
        {node.unit_id && (node.source_available ? <Link className="text-link" to={node.kind === 'foundation' ? `/foundations/${node.unit_id}` : `/learn/${node.context_id}/units/${node.unit_id}`}>개념 다시 읽기 ↗</Link> : <p>원본 자료를 열 수 없습니다. 추가 당시의 개념 설명은 보관되어 있습니다.</p>)}
        <section><h3>{node.kind === 'concept' ? '학습한 내용' : '개념 설명'}</h3>{node.descriptions.length ? node.descriptions.map((description, i) => <p className="prose" key={i}><InlineMarkdown>{description}</InlineMarkdown></p>) : <p>이 단원에서 통과한 문제를 모았습니다. 개념 정리를 실행하면 학습한 내용을 연결해 볼 수 있습니다.</p>}</section>
        {!!node.claims?.length && <section><h3>기록한 주장과 근거</h3>{node.claims.map((claim, i) => <div key={i}><p>{claim.text}{claim.scope && <small> · {claim.scope}</small>}{claim.contested && <small> · 반박 근거 있음</small>}</p>{claim.sources.map((source, j) => <AnimatedDetails key={source.id + j} summary={<>{source.disposition === 'refutes' ? '반박' : '지지'} · {source.title} v{source.version}</>}><p>{source.quote}</p><SourceLink source={source} /></AnimatedDetails>)}</div>)}</section>}
        {!!node.sources?.length && <section><h3>출처와 근거</h3><ul className="graph-neighbors">{node.sources.map((source, i) => <li key={source.id + ':' + i}><strong>{source.title}</strong><small>v{source.version} · {source.state === 'active' ? '등록한 근거' : source.state === 'deleted' ? '보관·삭제된 출처' : '변경됨 · 재검토 필요'}{source.basis === 'interpretation' ? source.authorship === 'ai' ? ' · AI 해석' : ' · 내 해석·설명' : source.basis === 'question' ? ' · 미해결 질문' : ''}</small><p>{source.quote}</p>{source.metadata?.locator && <small>{source.metadata.locator}</small>}<SourceLink source={source} /></li>)}</ul></section>}
        <section><h3>연결된 노드 <span>{nodeEdges.length}</span></h3>{nodeEdges.length ? <ul className="graph-neighbors">{nodeEdges.map(edge => {
          const outgoing = edge.source === node.id, other = outgoing ? edge.target : edge.source;
          return <li key={edge.id}><small>{edge.label} · {edge.kind === 'RELATED_TO' ? '양방향 ↔' : outgoing ? '나가는 연결 →' : '들어오는 연결 ←'}</small><button onClick={() => choose(other)}>{labels.get(other)} <span>↗</span></button><p>{edge.description}</p>{edge.sources?.map((source, i) => <div key={source.id + ':' + i}><small>{source.disposition === 'refutes' ? '반박 · ' : ''}{source.title} · v{source.version}</small><p>{source.quote}</p><SourceLink source={source} /></div>)}</li>;
        })}</ul> : <p>이 기록에는 아직 연결된 노드가 없습니다.</p>}</section>
        {!!node.observations?.length && <section><h3>직접 설명한 기록</h3><p>설명을 작성한 기록이며 숙달 점수는 아닙니다. 최근 설명 기록을 표시합니다.</p><ul>{node.observations.map(observation => <li key={observation.id}><span>{new Date(observation.created_at).toLocaleString('ko-KR')} · 설명 작성</span>{observation.material_review_id ? <Link to={'/knowledge/candidates/' + observation.material_review_id}>확인한 작성분 보기 →</Link> : observation.review_id && <Link to={'/reference-reviews/' + observation.review_id}>내 설명 보기 →</Link>}</li>)}</ul></section>}
        <section><h3>풀었던 문제 · 복습</h3><p>{node.exercise_ids.length ? '이전에 통과한 문제를 열어 복습할 수 있습니다.' : '개념 학습으로 추가되었습니다. 아직 통과한 문제는 없으며, 문제 풀이 없이도 지도에 보관됩니다.'}</p><ExerciseLinks exercises={data.exercises.filter(exercise => node.exercise_ids.includes(exercise.id))} /></section>
      </aside>}
    </div>
    <footer className="graph-footer"><div className="graph-legend">{Object.entries(kindLabels).map(([kind, label]) => <span key={kind}><i className={kind} />{label}</span>)}</div><p id="graph-instructions">드래그로 이동 · 휠 또는 +/−로 확대·축소 · 노드 선택으로 상세 보기 · Esc로 닫기</p></footer>
    <p className="graph-evidence-note">연결을 선택해 종류·방향·근거를 확인하세요. 연관 개념은 양방향이며, 점선은 선행 단원입니다. 등록과 연결은 숙달을 뜻하지 않습니다.</p>
  </section>;
}
