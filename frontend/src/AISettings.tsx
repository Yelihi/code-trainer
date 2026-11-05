import { InsightSchedule } from './InsightSchedule';
import { CircleCheck, CircleOff, ServerCog, TriangleAlert } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import './githubSharing.css';
import './aiSettings.css';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';

type Settings = { revision: number; source: 'personal' | 'environment' | 'disabled' | 'unconfigured'; model: string; provider_url: string; saved_provider_url: string; storage_ready: boolean; available: boolean; error: string };

export function AISettings() {
  const { userId } = useApp();
  return userId ? <SettingsLoader key={userId} /> : null;
}

function SettingsLoader() {
  const { data, error, reload } = useResource<Settings>('/ai/settings');
  return <main className="page github-page ai-settings-page">
    <div className="breadcrumb">설정 <span>/</span> AI 연결</div>
    <header className="ai-settings-page-heading"><h1>나의 AI 연결</h1><p>자료 해석과 실습, 지식 정리에 사용할 모델을 관리합니다.</p></header>
    <ErrorNotice error={error} />{error && <Button onClick={reload}>다시 불러오기</Button>}
    <div className="ai-settings-sections">
      {!data && !error && <LoadingSkeleton layout="editor" label="AI 연결을 불러오는 중…" />}
      {data && <SettingsForm key={data.revision} initial={data} onReload={reload} />}
      <InsightSchedule />
    </div>
  </main>;
}

function SettingsForm({ initial, onReload }: { initial: Settings; onReload: () => void }) {
  const { refreshHealth } = useApp();
  const [data, setData] = useState(initial);
  const [key, setKey] = useState('');
  const [model, setModel] = useState(initial.model);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [savedRevision, setSavedRevision] = useState<number | null>(null);
  const unsaved = model !== data.model || key.length > 0;
  const state = data.source === 'personal' ? (data.available ? 'saved' : 'warning') : data.source === 'environment' ? 'environment' : 'off';
  const status = state === 'saved' ? '계정에 저장됨' : state === 'warning' ? '저장된 연결 확인 필요' : state === 'environment' ? '서버 설정 사용 중' : '연결 없음';
  async function save(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const value = await api<Settings>('/ai/settings', 'PUT', { revision: data.revision, api_key: key, model, provider_url: data.provider_url });
      setData(value); setKey(''); setSavedRevision(value.revision); refreshHealth();
      setMessage('AI 설정이 저장됐습니다.');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function disconnect() {
    if (!window.confirm('저장된 AI 키를 삭제하고 연결을 해제할까요? 공통 키로 자동 전환하지 않습니다. 이미 전송된 요청은 완료될 수 있습니다.')) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const value = await api<Settings>('/ai/settings', 'DELETE', { revision: data.revision });
      setData(value); setKey(''); setModel(''); setSavedRevision(null); refreshHealth(); setMessage('AI 연결을 해제했습니다.');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <section className="github-card ai-connection-card" aria-labelledby="ai-connection-title">
      <div className="ai-connection-heading"><h2 id="ai-connection-title">현재 연결</h2>{unsaved && <span className="ai-unsaved-badge">미저장 변경</span>}</div>
      <div className={`ai-connection-state${savedRevision === data.revision ? ' is-fresh' : ''}`} data-state={state} role="status">
        <span className="ai-connection-icon" aria-hidden="true">{state === 'saved' ? <CircleCheck /> : state === 'warning' ? <TriangleAlert /> : state === 'environment' ? <ServerCog /> : <CircleOff />}</span>
        <div><strong>{status}</strong><p>{state === 'saved' ? 'API 키를 암호화해 보관하고 있습니다.' : state === 'warning' ? '저장된 설정을 사용할 수 없습니다.' : state === 'environment' ? '개인 키 대신 서버 설정을 사용합니다.' : 'API 키와 모델을 저장하면 사용할 수 있습니다.'}</p></div>
      </div>
      <dl className="ai-connection-details"><div><dt>현재 모델</dt><dd>{data.model || '없음'}</dd></div><div><dt>API 키</dt><dd>{state === 'saved' ? '계정에 보관됨' : state === 'warning' ? '확인 필요' : state === 'environment' ? '서버 설정 사용' : '없음'}</dd></div><div className="ai-provider-row"><dt>API 주소</dt><dd>{state === 'off' ? '없음' : data.saved_provider_url || data.provider_url}</dd></div></dl>
      <p className="ai-connection-caveat">저장 여부와 제공자 인증은 별개입니다. 키·모델 사용 권한은 실제 AI 요청에서 확인됩니다.</p>
      <ErrorNotice error={error || data.error} />
      {error && <Button type="button" disabled={busy} onClick={onReload}>최신 설정 다시 불러오기 · 입력 초기화</Button>}
      {message && <p role="status" className="ai-settings-message">{message}</p>}
      <form className="ai-connection-form" onSubmit={event => void save(event)}>
        <div className="ai-connection-form-heading"><h3>연결 변경</h3><p>API 주소 · {data.provider_url || '서버 설정 필요'}</p></div>
        <div className="ai-connection-fields"><div><Label htmlFor="ai-model">모델 ID</Label><Input id="ai-model" value={model} onChange={event => { setModel(event.target.value); setMessage(''); }} required maxLength={200} disabled={busy} spellCheck={false} autoComplete="off" /></div>
        <div><Label htmlFor="ai-key">{data.source === 'personal' ? '새 API 키' : 'API 키'}</Label><Input id="ai-key" type="password" value={key} onChange={event => { setKey(event.target.value); setMessage(''); }} required maxLength={1000} disabled={busy} spellCheck={false} autoComplete="off" /></div></div>
        <p className="ai-key-hint">저장된 키는 다시 표시하지 않습니다. 입력칸이 비어 있어도 현재 연결은 유지되며, 모델을 바꿔 저장할 때는 키를 다시 입력해야 합니다.</p>
        <div className="flex flex-wrap items-center gap-3">
          <Button className="primary" disabled={busy || !data.storage_ready || !data.provider_url || !key || !model}>{busy ? '처리 중…' : 'AI 연결 저장'}</Button>
          {(data.source === 'personal' || data.source === 'environment') && <Button type="button" disabled={busy} onClick={() => void disconnect()}>AI 연결 해제</Button>}
        </div>
      </form>
      <footer className="ai-settings-footer"><p>키 교체·삭제는 다음 요청부터 적용합니다. 개인 설정이 실패해도 서버 공통 키로 자동 전환하지 않습니다.</p><Link className="button" to="/me">AI 사용량 확인</Link></footer>
  </section>;
}
