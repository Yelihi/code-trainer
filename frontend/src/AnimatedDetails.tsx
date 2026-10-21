import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

export function AnimatedDetails({ summary, children, className = '', initiallyOpen = false, id }: {
  summary: ReactNode; children: ReactNode; className?: string; initiallyOpen?: boolean; id?: string;
}) {
  const panelId = useId();
  const [expanded, setExpanded] = useState(initiallyOpen);
  const animation = useRef<Animation | null>(null);
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => () => animation.current?.cancel(), []);
  return <details id={id} className={`learning-disclosure ${className}`} open={initiallyOpen}>
    <summary aria-expanded={expanded} aria-controls={panelId} onClick={event => {
      event.preventDefault();
      const details = event.currentTarget.parentElement as HTMLDetailsElement;
      const panel = content.current!;
      const opening = details.dataset.expanded === undefined ? !details.open : details.dataset.expanded !== 'true';
      const from = details.open ? panel.getBoundingClientRect().height : 0;
      const opacity = details.open ? getComputedStyle(panel).opacity : '0';
      animation.current?.cancel();
      animation.current = null;
      panel.style.height = '';
      setExpanded(opening);
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        details.open = opening;
        delete details.dataset.expanded;
        return;
      }
      details.open = true;
      const to = opening ? panel.getBoundingClientRect().height : 0;
      details.dataset.expanded = String(opening);
      panel.style.height = `${from}px`;
      const next = panel.animate({ height: [`${from}px`, `${to}px`], opacity: [opacity, opening ? '1' : '0'] }, {
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
    }}><span className="disclosure-label">{summary}</span><span className="disclosure-indicator" aria-hidden="true">
      <svg viewBox="0 0 20 20" fill="none"><path d="m7.5 5 5 5-5 5" /></svg>
    </span></summary>
    <div id={panelId} ref={content} className="disclosure-content" inert={!expanded}><div className="disclosure-body">{children}</div></div>
  </details>;
}
