import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useResource } from './useResource';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
export type LearningTarget = { kind: string; id: string; unit_id: string; title: string; href: string; revision: number | null };
export const targetInput = (target: LearningTarget) => ({ kind: target.kind, id: target.id, unit_id: target.unit_id });
export function LearningTargets({ targets, onChange, disabled = false }: { targets: LearningTarget[]; onChange: (targets: LearningTarget[]) => void; disabled?: boolean }) {
  const [selecting, setSelecting] = useState(false);
  return <div className="learning-targets"><Label>연결된 학습</Label>{targets.map(target => <div className="reference-actions" key={target.kind + target.id + target.unit_id}><Link className="text-link" to={target.href}>{target.title}</Link><Button type="button" disabled={disabled} onClick={() => onChange(targets.filter(item => item !== target))}>연결 해제</Button></div>)}{!targets.length && <p className="muted">연결 없이 독립 질문으로 남깁니다.</p>}<Button type="button" disabled={disabled} onClick={() => setSelecting(!selecting)}>{selecting ? '선택 닫기' : '연결 변경'}</Button>{selecting && <TargetPicker onPick={target => { onChange([target]); setSelecting(false); }} />}</div>;
}
export function TargetPicker({ onPick }: { onPick: (target: LearningTarget) => void }) {
  const [query, setQuery] = useState('');
  const { data, error } = useResource<{ items: LearningTarget[] }>('/learning-targets?q=' + encodeURIComponent(query));
  return <div className="target-picker"><Label>자료·학습·레퍼런스 검색<Input type="search" value={query} maxLength={160} onChange={e => setQuery(e.target.value)} /></Label>{error && <p role="alert">{error}</p>}<div className="target-options">{data?.items.map(target => <Button type="button" key={target.kind + target.id} onClick={() => onPick(target)}>{target.title}</Button>)}{data && !data.items.length && <p>연결할 기록이 없습니다.</p>}</div></div>;
}
