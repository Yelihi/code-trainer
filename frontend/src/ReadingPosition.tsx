import { useLayoutEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

// History keys distinguish a return visit from another search on the same route.
const positions = new Map<string, number>();
export function ReadingPosition() {
  const location = useLocation(), navigation = useNavigationType();
  useLayoutEffect(() => {
    const top = navigation === 'POP' ? positions.get(location.key) ?? 0 : 0;
    let restored = false;
    const restore = () => {
      if (!restored && document.documentElement.scrollHeight >= top + innerHeight) {
        window.scrollTo({ top, behavior: 'instant' }); restored = true;
      }
    };
    window.scrollTo({ top: 0, behavior: 'instant' });
    restore();
    const observer = new ResizeObserver(restore);
    observer.observe(document.body);
    const save = () => positions.set(location.key, window.scrollY);
    window.addEventListener('scroll', save, { passive: true });
    return () => { observer.disconnect(); window.removeEventListener('scroll', save); };
  }, [location.key, navigation]);
  return null;
}
