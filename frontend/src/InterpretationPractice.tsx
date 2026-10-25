import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp } from './App';

export function StartWorksheet({ interpretationId, retryId = '' }: { interpretationId: string; retryId?: string }) {
  const { userId, health } = useApp();
  const navigate = useNavigate();
  const storageKey = `worksheet-request:${userId}:${interpretationId}:${retryId}`;
  const [requestId] = useState(() => {
    try { const saved = localStorage.getItem(storageKey); if (saved && /^[a-f0-9-]{36}$/.test(saved)) return saved; } catch { /* Memory identity still protects this visit. */ }
    return crypto.randomUUID();
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [warning, setWarning] = useState('');
  const alive = useRef(true), sending = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  async function start() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError('');
    try {
      try { localStorage.setItem(storageKey, requestId); }
      catch { setWarning('브라우저에 요청을 임시 저장하지 못했습니다. 연결이 끊기면 새로 요청하기 전에 질문지 기록을 확인해주세요.'); }
      const job = await api<{ id: string }>('/worksheets', 'POST', { interpretation_id: interpretationId, request_id: requestId });
      if (!alive.current) return;
      try { localStorage.removeItem(storageKey); } catch { /* Replaying an old identity opens its saved job. */ }
      navigate('/worksheets/' + job.id);
    } catch (e) { if (alive.current) setError(errorMessage(e)); }
    finally { sending.current = false; if (alive.current) setBusy(false); }
  }
  return <><ErrorNotice error={error} />{warning && <p role="status" className="notice">{warning}</p>}
    <button className="primary" disabled={busy || !userId || !health?.ai} onClick={() => void start()}>{busy ? '요청 중…' : retryId ? '같은 해석으로 다시 생성' : '실습용 질문지 만들기'}</button>
    {health && !health.ai && <p className="reference-state">질문지를 만들려면 AI 설정이 필요합니다. 기존 기록은 계속 읽을 수 있습니다.</p>}</>;
}

export function InterpretationPractice({ interpretationId }: { interpretationId: string }) {
  const { userId } = useApp();
  return <section className="interpretation-entry"><div><span className="eyebrow">EXPLAIN IN YOUR OWN WORDS</span><h2>읽은 내용을 내 말로.</h2><p>이 해석을 바탕으로 실습용 질문지를 만듭니다.<br />질문을 따라 생각하고, 관련 개념을 다시 살펴보세요.</p></div><div className="interpretation-entry-actions">
    <StartWorksheet key={userId + ':' + interpretationId} interpretationId={interpretationId} />
    <Link to={'/explore/practice?interpretation=' + interpretationId}>이 해석의 질문지 기록 →</Link>
  </div></section>;
}
