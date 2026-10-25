import { Link, matchPath, useLocation } from 'react-router-dom';
import { WorksheetList } from './Worksheets';

type NavigationItem = { label: string; to: string; paths: string[]; planned?: boolean; admin?: boolean };
const groups: { label: string; items: NavigationItem[] }[] = [
  { label: '등록하기', items: [
    { label: '자료 보관함', to: '/library', paths: ['/library', '/library/:id', '/library/:id/edit', '/references', '/references/:id'] },
    { label: '직접 노트 작성', to: '/references/new', paths: ['/references/new'] },
    { label: '레퍼런스 등록', to: '/library/new/reference', paths: ['/library/new/reference'] },
    { label: '자동 등록 대기 (RSA)', to: '/inbox', paths: ['/inbox'] },
  ] },
  { label: '탐구하기', items: [
    { label: '해석하기', to: '/explore', paths: ['/', '/explore', '/interpretations/*', '/learn/*', '/create'] },
    { label: '실습하기', to: '/explore/practice', paths: ['/explore/practice', '/foundations/*', '/practice/*', '/worksheets/*'] },
    { label: '다시 검토', to: '/reviews', paths: ['/reviews/*', '/reference-reviews/*'] },
    { label: '나의 기록', to: '/me', paths: ['/me'] },
  ] },
  { label: '데이터 쌓기', items: [
    { label: '추출 가능 자료', to: '/knowledge/candidates', paths: ['/knowledge/candidates'], planned: true },
    { label: '지식 그래프', to: '/knowledge', paths: ['/knowledge'] },
  ] },
  { label: '응용하기', items: [
    { label: 'Deep Inside', to: '/apply', paths: ['/apply'], planned: true },
  ] },
  { label: '설정', items: [
    { label: 'GitHub 연동', to: '/settings/github', paths: ['/settings/github', '/github/share'] },
    { label: 'AI 연결', to: '/settings/ai', paths: ['/settings/ai'] },
    { label: '운영 상태', to: '/admin/operations', paths: ['/admin/operations'], admin: true },
    { label: '원본 자료 · 관리자', to: '/admin/sources', paths: ['/admin/sources/*'], admin: true },
  ] },
];

export function Navigation({ isAdmin, onNavigate }: { isAdmin: boolean; onNavigate: () => void }) {
  const { pathname } = useLocation();
  const items = groups.flatMap(group => group.items).filter(item => !item.admin || isAdmin);
  // Exact entry routes win over resource identifiers such as /references/:id.
  const active = items.find(item => item.to === pathname) ?? items.find(item => item.paths.some(path => matchPath(path, pathname)));
  return <div className="navigation-groups">{groups.map((group, index) => <section className="navigation-group" key={group.label}>
    <h2 className="sidebar-label"><span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>{group.label}</h2>
    <nav aria-label={group.label}>{group.items.filter(item => !item.admin || isAdmin).map(item => <Link key={item.to} to={item.to} className={active === item ? 'active' : undefined} aria-current={active === item ? 'page' : undefined} onClick={onNavigate}>
      <span>{item.label}</span>{item.planned && <small className="navigation-badge">예정</small>}
    </Link>)}</nav>
  </section>)}</div>;
}

const planned = {
  candidates: { area: '데이터 쌓기', title: '추출 가능 자료', description: '이해한 내용을, 연결할 지식으로.', detail: '해석과 실습에서 검토한 자료를 모아 개념·관계 후보를 비교하고 지식 그래프에 추가하는 공간입니다. 통합 추출 목록은 아직 준비 중입니다.', available: '지금은 저장한 노트에서 지식 그래프에 추가할 내용을 검토할 수 있습니다.', to: '/references', action: '노트에서 지식 검토하기' },
  inside: { area: '응용하기', title: 'Deep Inside', description: '쌓인 연결에서, 다음 질문을.', detail: '지식 사이의 연결을 바탕으로 더 깊이 탐구할 질문, 참고 자료와 실습 가이드를 제안할 공간입니다. 제안 생성과 채택 기능은 아직 준비 중입니다.', available: '지금은 지식 그래프에서 쌓인 개념과 근거를 직접 살펴볼 수 있습니다.', to: '/knowledge', action: '지식 그래프 살펴보기' },
};
export function PlannedFeature({ feature }: { feature: keyof typeof planned }) {
  const page = planned[feature];
  return <main className="page journey-page">
    <div className="breadcrumb">{page.area}<span>/</span>{page.title}</div>
    <span className="eyebrow">준비 중</span><h1>{page.title}</h1><h2>{page.description}</h2>
    <p>{page.detail}</p><div className="journey-available"><p>{page.available}</p><Link className="button" to={page.to}>{page.action}</Link></div>
  </main>;
}

export function PracticeEntry() {
  return <main className="page journey-page">
    <div className="breadcrumb">탐구하기<span>/</span>실습하기</div>
    <span className="eyebrow">LEARN BY DOING</span><h1>이해한 내용을 직접 다뤄보세요.</h1>
    <p>해석을 바탕으로 질문지를 만들고, 코드 실습과 기초 구현 학습을 이어가세요.</p>
    <WorksheetList />
    <div className="context-grid">
      <Link className="context-card" to="/"><h2>자료 기반 코드 실습</h2><p>기존 학습 자료를 열고 단원별 개념과 코드 문제를 이어갑니다.</p><span className="text-link">학습 자료 선택 →</span></Link>
      <Link className="context-card" to="/foundations"><h2>자료구조 · 알고리즘</h2><p>준비된 기초 구현 과정을 선택하고 직접 코드를 작성합니다.</p><span className="text-link">기초 구현 학습 →</span></Link>
    </div>
    <p className="notice">질문지를 열어 내 답변과 요약을 남겨보세요. 일부만 작성해도 저장하고 이어서 수정할 수 있습니다.</p>
    <Link className="text-link" to="/me">나의 실습 기록 보기 →</Link>
  </main>;
}
