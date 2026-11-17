import { Tabs } from 'radix-ui';
import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowUpRight, Code2, FileText, type LucideIcon } from 'lucide-react';

export function PageHeading({ title, description, meta, actions }: { title: string; description?: string; meta?: ReactNode; actions?: ReactNode }) {
  return <header className="workspace-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}{meta && <div className="workspace-heading-meta">{meta}</div>}</div>{actions && <div className="workspace-heading-actions">{actions}</div>}</header>;
}

export function ActionCard({ to, icon: Icon, title, description, accent = false }: { to: string; icon: LucideIcon; title: string; description?: string; accent?: boolean }) {
  return <Link className={'action-card' + (accent ? ' action-card-accent' : '')} to={to}><span className="action-card-icon"><Icon size={23} strokeWidth={1.7} aria-hidden="true" /></span><span className="action-card-copy"><strong>{title}</strong>{description && <span>{description}</span>}</span><ArrowUpRight className="action-card-arrow" size={19} aria-hidden="true" /></Link>;
}

export function SectionHeading({ title, action }: { title: string; action?: ReactNode }) {
  return <header className="section-heading"><h2>{title}</h2>{action}</header>;
}

export function EmptyState({ icon: Icon, title, description, action }: { icon: LucideIcon; title: string; description?: string; action?: ReactNode }) {
  return <div className="workspace-empty"><span className="workspace-empty-icon"><Icon size={24} strokeWidth={1.6} aria-hidden="true" /></span><div><h3>{title}</h3>{description && <p>{description}</p>}</div>{action}</div>;
}

const materials = [
  { to: '/library', title: '원자료', icon: FileText, paths: ['/library', '/references', '/inbox', '/interpretations', '/explore'] },
  { to: '/explore/practice', title: '실습', icon: Code2, paths: ['/explore/practice', '/courses', '/learn', '/create', '/foundations', '/practice', '/problem-books', '/framework-practice', '/worksheets'] },
];
const matches = (path: string, prefix: string) => path === prefix || path.startsWith(prefix + '/');
export function materialSection(path: string) {
  return [...materials].reverse().find(item => item.paths.some(prefix => matches(path, prefix)));
}
export function MaterialsNavigation() {
  const { pathname } = useLocation();
  const active = materialSection(pathname);
  if (!active) return null;
  return <nav className="materials-navigation" aria-label="자료 메뉴">{materials.map(({ to, title, icon: Icon }) => <Link to={to} key={to} aria-current={active.to === to ? 'page' : undefined}><Icon size={21} strokeWidth={1.7} aria-hidden="true" /><span>{title}</span></Link>)}</nav>;
}

export function ActivityItem({ title, meta, children }: { title: string; meta?: ReactNode; children: ReactNode }) {
  return <article className="activity-item"><div className="activity-item-copy"><h3>{title}</h3>{meta && <div className="activity-item-meta">{meta}</div>}</div><div className="activity-item-actions">{children}</div></article>;
}

export function WorkspaceTabs({ label, value, onValueChange, items }: { label: string; value: string; onValueChange: (value: string) => void; items: { value: string; label: string; icon: LucideIcon; content: ReactNode }[] }) {
  return <Tabs.Root className="workspace-tabs" value={value} onValueChange={onValueChange} activationMode="automatic"><Tabs.List className="workspace-tab-list" aria-label={label}>{items.map(({ value, label, icon: Icon }) => <Tabs.Trigger key={value} value={value}><Icon size={20} strokeWidth={1.7} aria-hidden="true" /><span>{label}</span></Tabs.Trigger>)}</Tabs.List>{items.map(item => <Tabs.Content className="workspace-tab-panel" key={item.value} value={item.value}>{item.content}</Tabs.Content>)}</Tabs.Root>;
}
