import { useEffect, useRef, type ReactNode } from 'react';

export function AnimatedDetails({ summary, children, className = '', initiallyOpen = false }: {
  summary: ReactNode; children: ReactNode; className?: string; initiallyOpen?: boolean;
}) {
  const animation = useRef<Animation | null>(null);
  useEffect(() => () => animation.current?.cancel(), []);
  return <details className={`learning-disclosure ${className}`} open={initiallyOpen}>
    <summary onClick={event => {
      event.preventDefault();
      const details = event.currentTarget.parentElement as HTMLDetailsElement;
      const opening = details.dataset.expanded === undefined ? !details.open : details.dataset.expanded !== 'true';
      const from = details.getBoundingClientRect().height;
      animation.current?.cancel();
      animation.current = null;
      details.style.height = '';
      details.style.overflow = '';
      delete details.dataset.expanded;
      details.open = opening;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const to = details.getBoundingClientRect().height;
      details.open = true;
      details.dataset.expanded = String(opening);
      details.style.overflow = 'clip';
      details.style.height = `${from}px`;
      const next = details.animate({ height: [`${from}px`, `${to}px`] }, {
        duration: 260, easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      });
      animation.current = next;
      next.onfinish = () => {
        if (animation.current !== next) return;
        details.open = opening;
        details.style.height = '';
        details.style.overflow = '';
        delete details.dataset.expanded;
        animation.current = null;
      };
    }}>{summary}</summary>
    {children}
  </details>;
}
