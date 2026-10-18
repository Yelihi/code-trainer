import { useEffect, useId, useMemo, useState } from 'react';
import { buildTrace } from './foundationTrace';

export function FoundationVisual({ kind }: { kind: string }) {
  const [input, setInput] = useState('5, 2, 7, 1');
  const [target, setTarget] = useState('7');
  const [values, setValues] = useState([5, 2, 7, 1]);
  const [search, setSearch] = useState(7);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const marker = useId().replaceAll(':', '');
  const frames = useMemo(() => buildTrace(kind, values, search), [kind, values, search]);
  const frame = frames[Math.min(step, frames.length - 1)];
  const fixed = ['dictionary', 'bfs', 'dfs'].includes(kind);
  const atEnd = step >= frames.length - 1;
  useEffect(() => {
    if (!playing || atEnd) return;
    const timer = window.setInterval(() => setStep(previous => Math.min(previous + 1, frames.length - 1)), 1300);
    return () => window.clearInterval(timer);
  }, [playing, frames.length, atEnd]);
  return <section className="foundation-visual" aria-label="개념 시각화">
    <div className="section-heading"><div><span className="eyebrow">SEE IT MOVE</span><h2>움직임으로 이해하기</h2></div><span className="muted">{step + 1} / {frames.length}</span></div>
    {!fixed && <form className="visual-inputs" onSubmit={event => {
      event.preventDefault();
      const parts = input.trim() ? input.split(',').map(v => v.trim()) : [];
      const next = parts.map(Number);
      if (parts.some(v => !/^-?\d+$/.test(v)) || next.some(v => !Number.isSafeInteger(v) || Math.abs(v) > 99) || next.length > 8 || !/^-?\d+$/.test(target) || Math.abs(Number(target)) > 99) {
        setError('−99~99 정수를 쉼표로 나눠 최대 8개 입력하세요. 비워두면 빈 배열입니다.'); return;
      }
      setError(''); setPlaying(false); setStep(0); setValues(next); setSearch(Number(target));
    }}><label>입력 값<input value={input} onChange={e => setInput(e.target.value)} maxLength={60} /></label>
      {kind === 'binary-search' && <label>찾을 값<input value={target} onChange={e => setTarget(e.target.value)} maxLength={3} /></label>}
      <button>값 적용</button></form>}
    {error && <p role="alert" className="notice error">{error}</p>}
    <svg viewBox="0 0 640 340" role="img" aria-label={`${frame.note} ${frame.detail}`}>
      <defs><marker id={marker} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="currentColor" /></marker></defs>
      {frame.edges.map(([from, to]) => { const a = frame.nodes.find(n => n.id === from)!, b = frame.nodes.find(n => n.id === to)!;
        return <line key={`${from}-${to}`} x1={a.x + 25} y1={a.y + 15} x2={b.x + (b.x > a.x ? -4 : b.x < a.x ? 54 : 25)} y2={b.y + (b.y > a.y ? -4 : b.y < a.y ? 34 : 15)} markerEnd={`url(#${marker})`} />;
      })}
      {frame.nodes.map(node => <g key={node.id} className={`visual-node ${node.active ? 'active' : ''} ${node.muted ? 'muted-node' : ''}`} style={{ transform: `translate(${node.x}px, ${node.y}px)` }}><rect width="52" height="30" rx="5" /><text x="26" y="20" textAnchor="middle">{node.label}</text></g>)}
      {!frame.nodes.length && <text x="320" y="170" textAnchor="middle" className="visual-empty">비어 있음</text>}
    </svg>
    <div className="visual-caption" aria-live={playing && !atEnd ? 'off' : 'polite'}><strong>{frame.note}</strong><p>{frame.detail || '한 단계씩 이동하며 상태 변화를 확인하세요.'}</p></div>
    <div className="visual-controls"><button aria-label="시각화 처음으로" onClick={() => { setStep(0); setPlaying(false); }}>↺ 처음</button><button disabled={step === 0} onClick={() => { setPlaying(false); setStep(step - 1); }}>← 이전</button><button className="primary" onClick={() => { if (atEnd) { setStep(0); setPlaying(true); } else setPlaying(!playing); }}>{playing && !atEnd ? '일시정지' : atEnd ? '다시 재생' : '재생'}</button><button disabled={atEnd} onClick={() => { setPlaying(false); setStep(step + 1); }}>다음 →</button></div>
  </section>;
}
