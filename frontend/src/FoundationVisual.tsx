import { useEffect, useId, useMemo, useState } from 'react';
import { buildTrace } from './foundationTrace';

export function FoundationVisual({ kind }: { kind: string }) {
  const [input, setInput] = useState('5, 2, 7, 1');
  const [target, setTarget] = useState('7');
  const [values, setValues] = useState([5, 2, 7, 1]);
  const [search, setSearch] = useState(7);
  const [applied, setApplied] = useState(false);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const marker = useId().replaceAll(':', '');
  const frames = useMemo(() => buildTrace(kind, values, search), [kind, values, search]);
  const frame = frames[Math.min(step, frames.length - 1)];
  const previous = frames[Math.max(0, step - 1)];
  const removed = previous.nodes.filter(node => !frame.nodes.some(current => current.id === node.id));
  const fixed = ['dictionary', 'bfs', 'dfs'].includes(kind);
  const heap = kind === 'priority-queue';
  const round = heap || kind === 'bfs' || kind === 'dfs';
  const atEnd = step >= frames.length - 1;
  useEffect(() => {
    if (!playing || atEnd) return;
    const timer = window.setInterval(() => setStep(previousStep => Math.min(previousStep + 1, frames.length - 1)), 1300);
    return () => window.clearInterval(timer);
  }, [playing, frames.length, atEnd]);
  return <section className={`foundation-visual visual-${kind}`} aria-label="개념 시각화">
    <div className="section-heading"><div><span className="eyebrow">SEE IT MOVE</span><h2>움직임으로 이해하기</h2></div><span className="visual-counter">{String(step + 1).padStart(2, '0')} <small>/ {frames.length}</small></span></div>
    <div className="visual-stage-layout"><div className="visual-stage" tabIndex={0} role="region" aria-label="시각화 그림 · 넓은 그림은 좌우로 스크롤할 수 있습니다">
    <div className="visual-legend"><span><i />현재 살펴보는 원소</span><span>{heap ? '완전 이진 트리 · 최소 힙' : fixed ? '정해진 예시를 단계별로 탐색합니다' : '값을 바꿔 동작을 비교해보세요'}</span></div>
    <svg viewBox={kind === 'stack' ? '240 0 200 340' : '0 0 640 340'} role="img" aria-label={`${frame.note} ${frame.detail}`}>
      <defs><marker id={marker} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="currentColor" /></marker></defs>
      {kind === 'stack' && <path className="structure-outline" d="M265,30 V325 H347 V30" />}
      {kind === 'queue' && <><path className="structure-outline" d="M20,130 H615 M20,180 H615" /><text className="diagram-label" x="30" y="115">FRONT</text><text className="diagram-label" x="560" y="200">BACK</text></>}
      {frame.edges.map(([from, to]) => {
        const a = frame.nodes.find(node => node.id === from)!, b = frame.nodes.find(node => node.id === to)!;
        const dx = b.x - a.x, dy = b.y - a.y, distance = Math.hypot(dx, dy);
        const offset = round ? 26 : Math.min(Math.abs(dx) ? 29 * distance / Math.abs(dx) : Infinity, Math.abs(dy) ? 19 * distance / Math.abs(dy) : Infinity);
        const x1 = a.x + 26 + dx / distance * offset, y1 = a.y + 15 + dy / distance * offset;
        const x2 = b.x + 26 - dx / distance * offset, y2 = b.y + 15 - dy / distance * offset;
        const curve = heap ? `M${x1},${y1} C${x1},${(y1+y2)/2} ${x2},${(y1+y2)/2} ${x2},${y2}` : round ? `M${x1},${y1} Q${(x1+x2)/2 + (dy < 0 ? -120 : 18)},${(y1+y2)/2} ${x2},${y2}` : `M${x1},${y1} L${x2},${y2}`;
        return <path className={`visual-edge ${b.active || a.active ? 'active' : ''}`} key={`${from}-${to}`} d={curve} markerEnd={heap ? undefined : `url(#${marker})`} />;
      })}
      {removed.map(node => <g key={`removed-${step}-${node.id}`} transform={`translate(${node.x},${node.y})`} aria-hidden="true"><g className="visual-exit"><rect width="52" height="30" rx="8" /><text x="26" y="20" textAnchor="middle">{node.label}</text></g></g>)}
      {frame.nodes.map((node, index) => <g key={node.id} className={`visual-node ${node.active ? 'active' : ''} ${node.muted ? 'muted-node' : ''}`} style={{ transform: `translate(${node.x}px, ${node.y}px)` }}><g className="visual-node-content">{round ? <circle cx="26" cy="15" r="24" /> : <rect width="52" height="30" rx="8" />}<text x="26" y="20" textAnchor="middle">{node.label}</text>{heap && <text className="diagram-index" x="26" y="51" textAnchor="middle">[{index}]</text>}</g></g>)}
      {kind === 'stack' && frame.nodes.length > 0 && <text className="diagram-label" x="364" y={frame.nodes.at(-1)!.y + 20}>← TOP</text>}
    </svg>
    {heap && <div className="heap-array"><span>같은 상태를 배열로 보면</span><div>{frame.nodes.length ? frame.nodes.map((node, index) => <span className={node.active ? 'active' : ''} key={node.id}><b>{node.label}</b><small>{index}</small></span>) : <code>[]</code>}</div></div>}
    </div><div className="visual-console">
    {!fixed && <form className="visual-inputs" onSubmit={event => {
      event.preventDefault();
      const parts = input.trim() ? input.split(',').map(value => value.trim()) : [];
      const next = parts.map(Number);
      if (parts.some(value => !/^-?\d+$/.test(value)) || next.some(value => !Number.isSafeInteger(value) || Math.abs(value) > 99) || next.length > 8 || !/^-?\d+$/.test(target) || Math.abs(Number(target)) > 99) {
        setError('−99~99 정수를 쉼표로 나눠 최대 8개 입력하세요. 비워두면 빈 배열입니다.'); setApplied(false); return;
      }
      setError(''); setPlaying(false); setStep(0); setValues(next); setSearch(Number(target)); setApplied(true);
    }}><label>입력 값<input value={input} onChange={event => { setInput(event.target.value); setApplied(false); }} maxLength={60} /></label>
      {kind === 'binary-search' && <label>찾을 값<input value={target} onChange={event => { setTarget(event.target.value); setApplied(false); }} maxLength={3} /></label>}
      <button className={applied ? 'is-applied' : ''}>{applied ? '✓ 적용됨' : '값 적용'}</button></form>}
    {!fixed && <p className={`visual-applied ${applied ? 'success-text' : 'muted'}`} role="status">{applied ? '✓ 입력값이 적용되었습니다.' : '현재 재생 값'} <span>[{values.join(', ')}]{kind === 'binary-search' && ` · 찾을 값 ${search}`}</span></p>}
    {error && <p role="alert" className="notice error">{error}</p>}
    <div key={step} className="visual-caption" aria-live={playing && !atEnd ? 'off' : 'polite'}><span className="eyebrow">STEP {String(step + 1).padStart(2, '0')}</span><strong>{frame.note}</strong><p>{frame.detail || '한 단계씩 이동하며 상태 변화를 확인하세요.'}</p></div>
    <label className="visual-timeline">단계 탐색<input type="range" min={0} max={frames.length - 1} value={step} aria-valuetext={`${step + 1} / ${frames.length}: ${frame.note}`} onChange={event => { setPlaying(false); setStep(Number(event.target.value)); }} /></label>
    <div className="visual-controls"><button aria-label="시각화 처음으로" onClick={() => { setStep(0); setPlaying(false); }}>↺ 처음</button><button disabled={step === 0} onClick={() => { setPlaying(false); setStep(step - 1); }}>← 이전</button><button className="primary" onClick={() => { if (atEnd) { setStep(0); setPlaying(true); } else setPlaying(!playing); }}>{playing && !atEnd ? '일시정지' : atEnd ? '다시 재생' : '재생'}</button><button disabled={atEnd} onClick={() => { setPlaying(false); setStep(step + 1); }}>다음 →</button></div>
    </div></div>
  </section>;
}
