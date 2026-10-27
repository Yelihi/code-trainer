import './loadingSkeleton.css';
import { Skeleton } from './components/ui/skeleton';

type Layout = 'cards' | 'catalog' | 'list' | 'article' | 'editor' | 'graph' | 'conversation' | 'summary';

function Lines() {
  return <div className="skeleton-lines"><Skeleton /><Skeleton /><Skeleton /></div>;
}

function Panel({ editor = false }: { editor?: boolean }) {
  return <div className="skeleton-panel"><Skeleton className="skeleton-bar skeleton-subtitle" /><Lines />
    {editor ? <div className="skeleton-code"><Lines /><Lines /><Lines /></div> : <><Lines /><Lines /></>}
  </div>;
}

export function LoadingSkeleton({ layout = 'list', label = '내용을 불러오는 중', heading = false }: {
  layout?: Layout; label?: string; heading?: boolean;
}) {
  return <div className={`loading-skeleton skeleton-${layout}`} role="status">
    <span className="skeleton-status">{label}</span>
    <div className="skeleton-shapes" aria-hidden="true">
      {heading && <div className="skeleton-heading"><Skeleton className="skeleton-bar skeleton-caption" /><Skeleton className="skeleton-bar skeleton-title" /><Lines /></div>}
      {(layout === 'cards' || layout === 'catalog') && <div className="skeleton-grid">{Array.from({ length: layout === 'catalog' ? 6 : 4 }, (_, i) =>
        <div className="skeleton-panel" key={i}><Skeleton className="skeleton-bar skeleton-caption" /><Skeleton className="skeleton-bar skeleton-subtitle" /><Lines /><div className="skeleton-chips"><Skeleton /><Skeleton /></div></div>)}</div>}
      {layout === 'list' && <div className="skeleton-list">{[0, 1, 2].map(i => <div className="skeleton-row" key={i}><div><Skeleton className="skeleton-bar skeleton-caption" /><Skeleton className="skeleton-bar skeleton-subtitle" /><Lines /></div><Skeleton className="skeleton-bar skeleton-action" /></div>)}</div>}
      {layout === 'summary' && <div className="skeleton-panel"><div className="skeleton-chips"><Skeleton /><Skeleton /><Skeleton /></div><Lines /></div>}
      {layout === 'article' && <div className="skeleton-article"><Panel /><Panel /></div>}
      {(layout === 'editor' || layout === 'conversation') && <div className="skeleton-columns"><Panel editor /><Panel editor={layout === 'editor'} /></div>}
      {layout === 'graph' && <div className="skeleton-graph"><div className="skeleton-graph-tools"><Skeleton className="skeleton-bar" /><Skeleton className="skeleton-bar" /></div>
        <svg viewBox="0 0 800 440" fill="none" focusable="false"><path d="M150 140 340 220 540 100M340 220 600 300M340 220 220 350M540 100 600 300 710 170" />{[[150, 140], [340, 220], [540, 100], [600, 300], [220, 350], [710, 170]].map(([cx, cy]) => <circle key={cx} cx={cx} cy={cy} r={cx === 340 ? 30 : 20} />)}</svg>
      </div>}
    </div>
  </div>;
}
