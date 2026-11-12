import { useEffect, useRef, useState } from 'react';
import { api, errorMessage } from './api';
import { ErrorNotice } from './App';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import './questions.css';

export function QuickQuestion() {
  const [open, setOpen] = useState(false), [text, setText] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const input = useRef<HTMLInputElement>(null), trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  async function save() {
    if (!text.trim() || busy) return;
    setBusy(true); setError('');
    try { await api('/questions', 'POST', { text, request_id: crypto.randomUUID() }); setText(''); setOpen(false); trigger.current?.focus(); window.dispatchEvent(new Event('questions-changed')); }
    catch (cause) { setError(errorMessage(cause)); } finally { setBusy(false); }
  }
  return <div className="quick-question"><Button ref={trigger} onClick={() => setOpen(value => !value)} aria-expanded={open} aria-controls="quick-question-panel">질문 적기</Button>{open && <div id="quick-question-panel" className="quick-question-panel" onKeyDown={e => { if (e.key === 'Escape') { setOpen(false); trigger.current?.focus(); } }}><form onSubmit={e => { e.preventDefault(); void save(); }}><Label htmlFor="quick-question-input">지금 궁금한 것은 무엇인가요?</Label><Input ref={input} id="quick-question-input" value={text} maxLength={500} onChange={e => setText(e.target.value)} placeholder="질문 한 줄을 남겨두세요" /><ErrorNotice error={error} /><div className="reference-actions"><Button className="primary" disabled={busy || !text.trim()}>{busy ? '저장 중…' : '질문 저장'}</Button><Button type="button" onClick={() => { setOpen(false); trigger.current?.focus(); }}>닫기</Button></div></form></div>}</div>;
}
