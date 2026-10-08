import ReactMarkdown from 'react-markdown';
import { CodeBlock } from './CodeBlock';

export function Markdown({ children, language }: { children: string; language: string }) {
  return <div className="prose markdown"><ReactMarkdown components={{
    // Lessons already have page and section headings; prose headings sit below them.
    h1: ({ children }) => <h3>{children}</h3>,
    h2: ({ children }) => <h3>{children}</h3>,
    a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
    img: ({ alt }) => <span>{alt}</span>,
    pre: ({ node, children }) => {
      const block = node?.children[0];
      if (block?.type !== 'element' || block.tagName !== 'code') return <pre>{children}</pre>;
      const classNames = String(block.properties.className ?? '');
      const codeLanguage = /language-([^\s,]+)/.exec(classNames)?.[1] ?? language;
      const code = block.children.map(child => child.type === 'text' ? child.value : '').join('');
      return <CodeBlock code={code.replace(/\n$/, '')} language={codeLanguage} />;
    },
  }}>{children}</ReactMarkdown></div>;
}
