import { useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { cpp } from '@codemirror/lang-cpp';
import { rust } from '@codemirror/lang-rust';

export function codeExtensions(language: string) {
  switch (language.toLowerCase()) {
    case 'js': case 'javascript': return [javascript()];
    case 'jsx': return [javascript({ jsx: true })];
    case 'ts': case 'typescript': return [javascript({ typescript: true })];
    case 'tsx': return [javascript({ typescript: true, jsx: true })];
    case 'py': case 'python': return [python()];
    case 'c': case 'c++': case 'cpp': return [cpp()];
    case 'rs': case 'rust': return [rust()];
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
