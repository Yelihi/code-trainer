import { useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { completeAnyWord } from '@codemirror/autocomplete';
import { javascript, javascriptLanguage } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { cpp, cppLanguage } from '@codemirror/lang-cpp';
import { rust, rustLanguage } from '@codemirror/lang-rust';
import { standardApiCompletions } from './codeCompletions';

export function codeExtensions(language: string, editing = false) {
  const api = editing ? [javascriptLanguage.data.of({ autocomplete: standardApiCompletions })] : [];
  switch (language.toLowerCase()) {
    case 'js': case 'javascript': return [javascript(), ...api];
    case 'jsx': return [javascript({ jsx: true }), ...api];
    case 'ts': case 'typescript': return [javascript({ typescript: true }), ...api];
    case 'tsx': return [javascript({ typescript: true, jsx: true }), ...api];
    case 'py': case 'python': return [python()];
    case 'c': case 'c++': case 'cpp': return [cpp(), ...(editing ? [cppLanguage.data.of({ autocomplete: completeAnyWord })] : [])];
    case 'rs': case 'rust': return [rust(), ...(editing ? [rustLanguage.data.of({ autocomplete: completeAnyWord })] : [])];
    default: return [];
  }
}

export function CodeBlock({ code, language }: { code: string; language: string }) {
  const extensions = useMemo(() => codeExtensions(language), [language]);
  return <div className="code-snippet">
    <CodeMirror value={code} theme="dark" extensions={extensions} editable={false} readOnly
      onCreateEditor={view => view.contentDOM.setAttribute('aria-label', '코드 예제 (읽기 전용)')}
      basicSetup={{ lineNumbers: false, foldGutter: false, highlightActiveLine: false, highlightActiveLineGutter: false }} />
  </div>;
}
