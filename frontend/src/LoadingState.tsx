import { LoaderCircle } from 'lucide-react';
import { Badge } from './components/ui/badge';
import './loadingState.css';

export function LoadingState({ title, description, status = '진행 중', compact = false }: {
  title: string; description?: string; status?: string; compact?: boolean;
}) {
  return <div className={`loading-state${compact ? ' loading-state-compact' : ''}`} role="status">
    <span className="loading-state-mark" aria-hidden="true"><LoaderCircle /></span>
    <div className="loading-state-copy"><Badge variant="secondary">{status}</Badge><h3>{title}</h3>{description && <p>{description}</p>}</div>
  </div>;
}
