import { useEffect, useRef, type ReactNode } from 'react';

export function AnimatedDetails({ summary, children, className = '', initiallyOpen = false }: {
  summary: ReactNode; children: ReactNode; className?: string; initiallyOpen?: boolean;
}) {
  const animation = useRef<Animation | null>(null);
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => () => animation.current?.cancel(), []);
  return <details className={`learning-disclosure ${className}`} open={initiallyOpen}>
    <summary onClick={event => {
      event.preventDefault();
      const details = event.currentTarget.parentElement as HTMLDetailsElement;
      const panel = content.current!;
      const opening = details.dataset.expanded === undefined ? !details.open : details.dataset.expanded !== 'true';
      const from = details.open ? panel.getBoundingClientRect().height : 0;
      animation.current?.cancel();
      animation.current = null;
      panel.style.height = '';
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        details.open = opening;
        delete details.dataset.expanded;
        return;
      }
      details.open = true;
      const to = opening ? panel.getBoundingClientRect().height : 0;
      details.dataset.expanded = String(opening);
      panel.style.height = `${from}px`;
      const next = panel.animate({ height: [`${from}px`, `${to}px`] }, {
        duration: 260, easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      });
      animation.current = next;
      next.onfinish = () => {
        if (animation.current !== next) return;
        details.open = opening;
        panel.style.height = '';
        delete details.dataset.expanded;
        animation.current = null;
      };
    }}><span className="disclosure-label">{summary}</span></summary>
    <div ref={content} className="disclosure-content"><div className="disclosure-body">{children}</div></div>
  </details>;
}
