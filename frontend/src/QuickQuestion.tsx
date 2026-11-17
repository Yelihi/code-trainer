import { MessageCirclePlus } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice } from './App';
import { LearningTargets, targetInput, type LearningTarget } from './LearningTargets';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import './questions.css';

type Draft = { text: string; request_id: string; targets: LearningTarget[]; origin: string };
export function QuickQuestion({ userId }: { userId: string }) {
  const location = useLocation(), storageKey = 'quick-question:' + userId;
  const [open, setOpen] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [draft, setDraft] = useState<Draft>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
      if (saved && typeof saved.text === 'string' && saved.text.length <= 500 && typeof saved.request_id === 'string' && Array.isArray(saved.targets) && typeof saved.origin === 'string') return saved;
    } catch { /* A blocked or expired browser draft must not prevent capture. */ }
    return { text: '', targets: [], request_id: crypto.randomUUID(), origin: '' };
  });
  const currentDraft = useRef(draft), targetEdited = useRef(false);
  currentDraft.current = draft;
  const [contextPending, setContextPending] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null), trigger = useRef<HTMLButtonElement>(null), saving = useRef(false);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => {
    const viewport = window.visualViewport;
    if (!open || !viewport) return;
    const fit = () => {
      panel.current?.style.setProperty('--question-height', Math.max(100, viewport.height - 24) + 'px');
      panel.current?.style.setProperty('--question-bottom', Math.max(12, innerHeight - viewport.height - viewport.offsetTop + 12) + 'px');
    };
    fit(); viewport.addEventListener('resize', fit); viewport.addEventListener('scroll', fit);
    return () => { viewport.removeEventListener('resize', fit); viewport.removeEventListener('scroll', fit); };
  }, [open]);
  useEffect(() => {
    if (!open || currentDraft.current.text) return;
    targetEdited.current = false;
    setContextPending(true);
    const controller = new AbortController();
    const origin = (location.pathname + location.search).slice(0, 300);
    api<{ target: LearningTarget | null }>('/learning-target?path=' + encodeURIComponent(origin), 'GET', undefined, controller.signal)
      .then(value => { if (!targetEdited.current) setDraft(old => ({ ...old, origin, targets: value.target ? [value.target] : [] })); })
      .catch(() => undefined).finally(() => { if (!controller.signal.aborted) setContextPending(false); });
    return () => controller.abort();
  }, [open, location.pathname, location.search]);
  useEffect(() => {
    if (!draft.text) return;
    try { localStorage.setItem(storageKey, JSON.stringify(draft)); }
    catch { setError('브라우저 임시 저장을 사용할 수 없습니다. 이동 전에 질문을 저장해주세요.'); }
  }, [draft, storageKey]);
  function change(patch: Partial<Draft>) {
    if (patch.targets) targetEdited.current = true;
    const next = { ...draft, ...patch, request_id: crypto.randomUUID() };
    setDraft(next);
    try { localStorage.setItem(storageKey, JSON.stringify(next)); }
    catch { setError('브라우저 임시 저장을 사용할 수 없습니다. 닫기 전에 질문을 저장해주세요.'); }
  }
  async function save() {
    if (!draft.text.trim() || saving.current || contextPending) return;
    saving.current = true; setBusy(true); setError('');
    try {
      await api('/questions', 'POST', { ...draft, targets: draft.targets.map(targetInput) });
      try { localStorage.removeItem(storageKey); } catch { /* The question is already saved. */ }
      setDraft({ text: '', targets: [], request_id: crypto.randomUUID(), origin: '' }); setOpen(false);
      trigger.current?.focus(); window.dispatchEvent(new Event('questions-changed'));
    } catch (cause) { setError(errorMessage(cause)); }
    finally { saving.current = false; setBusy(false); }
  }
  return <div className="quick-question"><Button ref={trigger} onClick={() => setOpen(value => !value)} aria-expanded={open} aria-controls="quick-question-panel"><MessageCirclePlus size={18} aria-hidden="true" />질문 적기</Button>{open && <div ref={panel} id="quick-question-panel" className="quick-question-panel" onKeyDown={e => { if (e.key === 'Escape' && !e.nativeEvent.isComposing) { setOpen(false); trigger.current?.focus(); } }}><form onSubmit={e => { e.preventDefault(); void save(); }}>
    <Label htmlFor="quick-question-input">지금 궁금한 것은 무엇인가요?</Label><Textarea ref={input} rows={4} wrap="soft" id="quick-question-input" value={draft.text} maxLength={500} disabled={busy} onChange={e => change({ text: e.target.value })} placeholder="질문만 저장하고 학습을 이어가도 좋습니다." />
    <LearningTargets targets={draft.targets} disabled={busy} onChange={targets => change({ targets })} /><ErrorNotice error={error} /><div className="reference-actions"><Button className="primary" loading={busy} disabled={busy || contextPending || !draft.text.trim()}>{busy ? '저장 중…' : '질문 저장'}</Button><Button type="button" onClick={() => { setOpen(false); trigger.current?.focus(); }}>닫기</Button></div>
  </form></div>}</div>;
}
