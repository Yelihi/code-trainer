import { ArrowRight, BookOpen, Code2, CalendarDays, FolderOpen, NotebookPen, Settings2 } from 'lucide-react';
import { materialSection, PageHeading } from './WorkspaceUI';
import { useEffect, useRef } from 'react';
import { Link, matchPath, useLocation } from 'react-router-dom';
import { Button } from './components/ui/button';

const primary = [
  { label: '오늘의 학습', to: '/', icon: CalendarDays, paths: ['/', '/questions/*', '/reviews/*', '/me'] },
  { label: '자료', to: '/library', icon: FolderOpen, paths: [] },
  { label: '레퍼런스', to: '/technical-references', icon: NotebookPen, paths: ['/technical-references/*'] },
];
export function Navigation({ isAdmin, onNavigate, onLogout }: { isAdmin: boolean; onNavigate: () => void; onLogout?: () => void }) {
  const { pathname } = useLocation();
  const settings = useRef<HTMLDetailsElement>(null);
  function navigate() { if (settings.current) settings.current.open = false; onNavigate(); }
  useEffect(() => {
    if (settings.current) settings.current.open = false;
  }, [pathname]);
  useEffect(() => {
    const outside = (event: PointerEvent) => { if (event.target instanceof Node && !settings.current?.contains(event.target) && settings.current) settings.current.open = false; };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && settings.current?.open && !event.defaultPrevented) {
        settings.current.open = false; settings.current.querySelector('summary')?.focus(); event.preventDefault();
      }
    };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, []);
  const active = primary.find(item => item.to === pathname) ?? (materialSection(pathname) ? primary[1] : primary.find(item => item.paths.some(path => matchPath(path, pathname))));
  return <div className="learning-navigation">
    <nav aria-label="주요 메뉴">{primary.map(({ icon: Icon, ...item }) => <Link key={item.to} to={item.to} aria-current={active?.to === item.to ? 'page' : undefined} onClick={navigate}><Icon size={22} strokeWidth={1.7} aria-hidden="true" /><span>{item.label}</span></Link>)}</nav>
    <details ref={settings} className="workspace-settings"><summary><Settings2 size={21} strokeWidth={1.7} aria-hidden="true" /><span>설정</span></summary><nav aria-label="설정과 기록">
      <Link to="/questions" onClick={navigate}>질문 모아보기</Link><Link to="/me" onClick={navigate}>학습 기록</Link>
      <Link to="/settings/questions" onClick={navigate}>질문 다시보기 설정</Link>
      <Link to="/settings/ai" onClick={navigate}>AI 연결과 사용량</Link><Link to="/settings/github" onClick={navigate}>GitHub 연동</Link>
      <Link to="/settings/records" onClick={navigate}>기록 내보내기</Link>
      {isAdmin && <><Link to="/admin/operations" onClick={navigate}>운영 상태</Link><Link to="/admin/sources" onClick={navigate}>원본 자료 관리</Link></>}
      {onLogout && <Button className="text-button" onClick={onLogout}>로그아웃</Button>}
    </nav></details>
  </div>;
}

export function PracticeEntry() {
  return <main className="page journey-page">
    <PageHeading title="실습" actions={<Link className="text-link" to="/me">실습 기록</Link>} />
    <div className="practice-options">
      <Link className="practice-path" to="/explore/practice/catalog"><span className="practice-path-icon"><BookOpen size={28} aria-hidden="true" /></span><h2>사전 생성 문제집</h2><p>준비된 주제를 골라 설명하고 구현해보세요.</p><div className="practice-path-tags"><span>문제집별 학습</span><span>단원 선택</span></div><span className="practice-path-action">문제집 선택<ArrowRight size={18} aria-hidden="true" /></span></Link>
      <Link className="practice-path" to="/courses"><span className="practice-path-icon"><Code2 size={28} aria-hidden="true" /></span><h2>자료기반 코드 실습</h2><p>내 자료에서 실습문제를 생성하고 풀어보세요.</p><div className="practice-path-tags"><span>자료 기반 생성</span><span>코드 실행</span></div><span className="practice-path-action">실습 열기<ArrowRight size={18} aria-hidden="true" /></span></Link>
    </div>
  </main>;
}


export function PracticeCatalog() {
  return <main className="page journey-page practice-catalog-page">
    <div className="breadcrumb"><Link to="/explore/practice">실습</Link><span>/</span>사전 생성 문제집</div>
    <PageHeading title="사전 생성 문제집" />
    <section className="practice-book-list" aria-label="학습할 문제집">
      <Link className="practice-book" to="/foundations"><span className="practice-path-icon"><BookOpen size={28} aria-hidden="true" /></span><div><span className="practice-book-language">TypeScript</span><h2>자료구조 · 알고리즘</h2><p>자료구조 구현부터 알고리즘과 기본 메서드까지</p></div><span className="practice-book-action">단원 보기<ArrowRight size={18} aria-hidden="true" /></span></Link>
    </section>
  </main>;
}
