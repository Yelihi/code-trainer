import { Link, matchPath, useLocation } from 'react-router-dom';
import { Button } from './components/ui/button';
import { WorksheetList } from './Worksheets';

const primary = [
  { label: '오늘의 학습', to: '/', paths: ['/', '/questions/*', '/reviews/*', '/learn/*', '/practice/*', '/foundations/*', '/explore/practice', '/worksheets/*'] },
  { label: '학습 자료', to: '/library', paths: ['/library/*', '/references/*', '/inbox', '/explore', '/interpretations/*', '/create', '/courses', '/problem-books/*'] },
  { label: '내 레퍼런스', to: '/technical-references', paths: ['/technical-references/*'] },
];
export function Navigation({ isAdmin, onNavigate, onLogout }: { isAdmin: boolean; onNavigate: () => void; onLogout?: () => void }) {
  const { pathname } = useLocation();
  const active = primary.find(item => item.to === pathname) ?? primary.find(item => item.paths.some(path => matchPath(path, pathname)));
  return <div className="learning-navigation">
    <nav aria-label="주요 메뉴">{primary.map(item => <Link key={item.to} to={item.to} aria-current={active === item ? 'page' : undefined} onClick={onNavigate}>{item.label}</Link>)}</nav>
    <details className="workspace-settings"><summary>설정과 기록</summary><nav aria-label="설정과 기록">
      <Link to="/questions" onClick={onNavigate}>질문 모아보기</Link><Link to="/me" onClick={onNavigate}>학습 기록</Link>
      <Link to="/settings/ai" onClick={onNavigate}>AI 연결과 사용량</Link><Link to="/settings/github" onClick={onNavigate}>GitHub 연동</Link>
      <Link to="/settings/records" onClick={onNavigate}>기록 내보내기</Link>
      {isAdmin && <><Link to="/admin/operations" onClick={onNavigate}>운영 상태</Link><Link to="/admin/sources" onClick={onNavigate}>원본 자료 관리</Link></>}
      {onLogout && <Button className="text-button" onClick={onLogout}>로그아웃</Button>}
    </nav></details>
  </div>;
}

export function PracticeEntry() {
  return <main className="page journey-page">
    <div className="breadcrumb">탐구하기<span>/</span>실습하기</div>
    <span className="eyebrow">LEARN BY DOING</span><h1>이해한 내용을 직접 다뤄보세요.</h1>
    <p>해석을 바탕으로 질문지를 만들고, 코드 실습과 기초 구현 학습을 이어가세요.</p>
    <WorksheetList />
    <div className="context-grid">
      <Link className="context-card" to="/"><h2>자료 기반 코드 실습</h2><p>기존 학습 자료를 열고 단원별 개념과 코드 문제를 이어갑니다.</p><span className="text-link">학습 자료 선택</span></Link>
      <Link className="context-card" to="/foundations"><h2>자료구조 · 알고리즘</h2><p>준비된 기초 구현 과정을 선택하고 직접 코드를 작성합니다.</p><span className="text-link">기초 구현 학습</span></Link>
      <Link className="context-card" to="/framework-practice"><h2>React · Vue 컴포넌트</h2><p>TSX 또는 Vue 컴포넌트를 작성하고 렌더링 결과를 확인합니다.</p><span className="text-link">프레임워크 실행</span></Link>
    </div>
    <p className="notice">질문지를 열어 내 답변과 요약을 남겨보세요. 일부만 작성해도 저장하고 이어서 수정할 수 있습니다.</p>
    <Link className="text-link" to="/me">나의 실습 기록 보기</Link>
  </main>;
}
