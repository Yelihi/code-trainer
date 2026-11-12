import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage } from './api';

export function useResource<T>(path: string, { preserveData = false }: { preserveData?: boolean } = {}) {
  const [state, setState] = useState<{ path: string; data: T | null; error: string; loading: boolean }>({ path, data: null, error: '', loading: true });
  const [version, setVersion] = useState(0);
  const active = useRef<AbortController | null>(null);
  const reload = useCallback(() => setVersion(value => value + 1), []);
  const update = useCallback((data: T) => {
    active.current?.abort();
    setState({ path, data, error: '', loading: false });
  }, [path]);
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    setState(previous => ({ path, data: preserveData && previous.path === path ? previous.data : null, error: '', loading: true }));
    api<T>(path, 'GET', undefined, controller.signal).then(data => {
      if (controller.signal.aborted) return;
      setState(previous => ({ path, data: preserveData && previous.path === path && JSON.stringify(previous.data) === JSON.stringify(data) ? previous.data : data, error: '', loading: false }));
    }).catch(error => {
      if (!controller.signal.aborted) setState(previous => ({ ...previous, error: errorMessage(error), loading: false }));
    });
    return () => controller.abort();
  }, [path, version, preserveData]);
  return { data: state.path === path ? state.data : null, error: state.path === path ? state.error : '', loading: state.path !== path || state.loading, reload, update };
}
