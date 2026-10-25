import { InsightSchedule } from './InsightSchedule';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { LoadingSkeleton } from './LoadingSkeleton';
import './githubSharing.css';

type Settings = { revision: number; source: 'personal' | 'environment' | 'disabled' | 'unconfigured'; model: string; provider_url: string; saved_provider_url: string; storage_ready: boolean; available: boolean; error: string };

export function AISettings() {
  const { userId } = useApp();
  return userId ? <SettingsLoader key={userId} /> : null;
}

function SettingsLoader() {
  const { data, error, reload } = useResource<Settings>('/ai/settings');
  return <main className="page github-page">
    <div className="breadcrumb">설정 <span>/</span> AI 연결</div>
    <span className="eyebrow">YOUR TOOLS FOR EXPLORATION</span><h1>나의 AI 연결.</h1>
    <p className="page-intro">자료 해석과 실습, 지식 정리를 도울 API 키와 모델을 등록하세요.</p>
    <ErrorNotice error={error} />{error && <button onClick={reload}>다시 불러오기</button>}
    {!data && !error && <LoadingSkeleton layout="editor" label="AI 연결을 불러오는 중…" />}
    {data && <SettingsForm initial={data} onReload={reload} />}
    <InsightSchedule />
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
  async function save(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const value = await api<Settings>('/ai/settings', 'PUT', { revision: data.revision, api_key: key, model, provider_url: data.provider_url });
      setData(value); setKey(''); refreshHealth();
      setMessage('AI 연결을 저장했습니다. 다음 AI 요청부터 적용됩니다. 제공자 인증은 아직 확인하지 않았습니다.');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function disconnect() {
    if (!window.confirm('저장된 AI 키를 삭제하고 연결을 해제할까요? 공통 키로 자동 전환하지 않습니다. 이미 전송된 요청은 완료될 수 있습니다.')) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const value = await api<Settings>('/ai/settings', 'DELETE', { revision: data.revision });
      setData(value); setKey(''); setModel(''); refreshHealth(); setMessage('AI 연결을 해제했습니다. 저장한 자료와 기존 실습은 계속 이용할 수 있습니다.');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <div className="github-stack">
    <section className="github-card">
      <h2>{data.source === 'personal' ? '개인 설정 저장됨' : data.source === 'environment' ? '서버 환경설정 사용 중' : 'AI 연결 해제됨'}</h2>
      <p>{data.source === 'environment' ? '현재 로컬 서버의 공통 연결을 사용합니다. 개인 키를 등록하면 본인의 설정으로 전환합니다.' : data.source === 'personal' ? `모델 ${data.model} · 설정 v${data.revision}` : '키와 모델을 등록하면 AI 기능을 사용할 수 있습니다.'}</p>
      {data.saved_provider_url && <p>저장된 API 주소 · {data.saved_provider_url}</p>}
      <p className="github-caption">설정 저장은 인증 성공을 보장하지 않습니다. 실제 요청 시 제공자의 키·모델 권한과 사용량에 따라 처리됩니다.</p>
      <ErrorNotice error={error || data.error} />
      {error && <button type="button" disabled={busy} onClick={onReload}>최신 설정 다시 불러오기 · 입력 초기화</button>}
      {message && <p role="status" className="notice">{message}</p>}
      <form onSubmit={event => void save(event)}>
        <p>새 연결의 API 주소 · <strong>{data.provider_url || '서버 설정 필요'}</strong></p>
        <label htmlFor="ai-model">모델 ID</label><input id="ai-model" value={model} onChange={event => setModel(event.target.value)} required maxLength={200} disabled={busy} spellCheck={false} autoComplete="off" />
        <label htmlFor="ai-key">{data.source === 'personal' ? '새 API 키' : 'API 키'}</label><input id="ai-key" type="password" value={key} onChange={event => setKey(event.target.value)} required maxLength={1000} disabled={busy} spellCheck={false} autoComplete="off" />
        <p className="github-caption">입력한 키는 암호화해 저장하고 다시 표시하지 않습니다. 화면을 떠나면 미저장 키 입력이 사라집니다.</p>
        <button className="primary" disabled={busy || !data.storage_ready || !data.provider_url || !key || !model}>{busy ? '처리 중…' : 'AI 연결 저장'}</button>
      </form>
      {(data.source === 'personal' || data.source === 'environment') && <button type="button" disabled={busy} onClick={() => void disconnect()}>AI 연결 해제</button>}
    </section>
    <p>키 교체·삭제는 다음 요청부터 적용합니다. 이미 제공자에게 보낸 요청은 완료될 수 있습니다. 개인 설정을 등록한 뒤에는 키를 삭제하거나 인증에 실패해도 공통 키로 대체하지 않습니다.</p>
    <Link className="text-link" to="/me">나의 기록에서 AI 사용량 확인 ↗</Link>
  </div>;
}
