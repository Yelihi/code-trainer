import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { Button } from './components/ui/button';

export function AddToKnowledge({ path, addedAt, disabled = false }: { path: string; addedAt?: string | null; disabled?: boolean }) {
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function add() {
    setBusy(true); setError('');
    try {
      const result = await api<{ knowledge_added_at: string }>(path, 'POST', {});
      setSaved(result.knowledge_added_at);
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <div className="knowledge-save">
    {saved || addedAt ? <><span role="status">✓ 개념 지도에 추가됨</span><Link className="text-link" to="/knowledge">지도에서 보기</Link></> :
      <Button disabled={busy || disabled} onClick={() => void add()}>{busy ? '추가 중…' : '개념 지도에 추가하기'}</Button>}
    {error && <p className="notice error" role="alert">{error}</p>}
  </div>;
}
