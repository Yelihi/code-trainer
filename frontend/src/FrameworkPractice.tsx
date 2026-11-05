import { useEffect, useRef, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { Link } from 'react-router-dom';
import { api, errorMessage } from './api';
import { codeExtensions } from './CodeBlock';
import { Button } from './components/ui/button';
import { NativeSelect } from './components/ui/native-select';
import { Label } from './components/ui/label';
import { frameworkDocument } from './frameworkDocument';
import './frameworkPractice.css';

type Framework = 'react' | 'vue';
type Preview = { status: string; error: string; warnings: string; html: string; css: string; client: string };
const examples: Record<Framework, string> = {
  react: `export default function App() {
  const topics = ['상태', '컴포넌트', '렌더링'];
  return <main><h1>React 실습</h1><ul>{topics.map(topic => <li key={topic}>{topic}</li>)}</ul></main>;
}`,
  vue: `<script setup>
const topics = ['반응성', '컴포넌트', '템플릿']
</script>

<template>
  <main><h1>Vue 실습</h1><ul><li v-for="topic in topics" :key="topic">{{ topic }}</li></ul></main>
</template>

<style>
main { font-family: system-ui; padding: 24px; }
</style>`,
};

export function FrameworkPractice() {
  const [framework, setFramework] = useState<Framework>('react');
  const [code, setCode] = useState(examples.react);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [clientError, setClientError] = useState(''), [ready, setReady] = useState(false);
  const [vendorSource, setVendorSource] = useState('');
  const frame = useRef<HTMLIFrameElement>(null);
  useEffect(() => {
    function receive(event: MessageEvent) {
      if (event.source !== frame.current?.contentWindow || !event.data || typeof event.data !== 'object') return;
      if (event.data.type === 'framework-preview-ready') setReady(true);
      if (event.data.type === 'framework-preview-error') setClientError(String(event.data.message).slice(0, 2000));
    }
    window.addEventListener('message', receive);
    return () => window.removeEventListener('message', receive);
  }, []);
  async function run() {
    setBusy(true); setError(''); setClientError(''); setReady(false); setPreview(null);
    try {
      const result = await api<Preview>('/framework-preview', 'POST', { framework, code });
      if (result.status === 'ok') {
        const asset = await fetch(`/framework-runtime/${framework}-v1.js`);
        if (!asset.ok || !asset.headers.get('content-type')?.includes('javascript')) throw new Error('프레임워크 실행 파일을 불러오지 못했습니다.');
        setVendorSource(await asset.text());
      }
      setPreview(result);
    }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  const document = preview?.status === 'ok' && vendorSource ? frameworkDocument(preview, vendorSource) : '';
  return <main className="page framework-practice-page">
    <div className="breadcrumb"><Link to="/explore/practice">실습하기</Link><span>/</span> 프레임워크 실습</div>
    <header><h1>React · Vue 실행</h1><p>컴포넌트를 격리된 실행 환경에서 렌더링하고 결과를 확인합니다.</p></header>
    <div className="framework-practice-controls"><div className="framework-practice-field"><Label htmlFor="framework-select">프레임워크</Label><NativeSelect id="framework-select" value={framework} disabled={busy} onChange={event => { const next = event.target.value as Framework; setFramework(next); setCode(examples[next]); setPreview(null); setError(''); setClientError(''); setReady(false); }}><option value="react">React · TSX / JSX</option><option value="vue">Vue · 단일 파일 컴포넌트</option></NativeSelect></div><Button className="primary" disabled={busy || !code.trim()} onClick={() => void run()}>{busy ? '렌더링 중…' : '실행해서 미리보기'}</Button></div>
    <div className="framework-practice-grid"><section><h2>컴포넌트 코드</h2><CodeMirror value={code} theme="dark" extensions={codeExtensions(framework === 'react' ? 'tsx' : 'javascript', true)} editable={!busy} height="440px" onChange={value => { setCode(value.slice(0, 24000)); setPreview(null); setError(''); setClientError(''); setReady(false); }} onCreateEditor={view => view.contentDOM.setAttribute('aria-label', '프레임워크 컴포넌트 코드')} /></section>
      <section><h2>화면 미리보기</h2>{error && <p role="alert" className="error-text">{error}</p>}{preview?.error && <pre role="alert" className="framework-practice-error">{preview.error}</pre>}{preview?.warnings && <pre role="status" className="framework-practice-warning">{preview.warnings}</pre>}{clientError && <pre role="alert" className="framework-practice-error">{clientError}</pre>}{document && <p role="status" className="framework-practice-state">{ready ? '브라우저 실행 중' : '브라우저 실행 준비 중…'}</p>}{document ? <iframe ref={frame} title="프레임워크 실행 결과" sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={document} /> : <div className="framework-practice-empty">코드를 실행하면 렌더링 결과가 여기에 표시됩니다.</div>}</section></div>
    <p className="muted">한 파일로 작성하세요. React에서는 react, Vue에서는 vue 모듈을 사용할 수 있습니다. 미리보기는 앱 데이터와 외부 네트워크에 접근하지 못합니다.</p>
  </main>;
}
