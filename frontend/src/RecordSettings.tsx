import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { AnimatedDetails } from './AnimatedDetails';
import { PageHeading } from './WorkspaceUI';
export function RecordSettings() {
  return <main className="page settings-page export-settings-page">
    <div className="breadcrumb">설정<span>/</span>기록 내보내기</div><PageHeading title="기록 내보내기" />
    <section className="settings-section"><header className="section-heading"><h2>내 학습 기록</h2><span className="settings-format">ZIP</span></header>
      <dl className="settings-facts"><div><dt>포함 기록</dt><dd>원자료·버전·질문·풀이·제출·도움 기록·복습 초안·이전 기록</dd></div><div><dt>파일 형식</dt><dd>원래 ID와 연결 정보를 담은 JSON · 첨부 이미지</dd></div><div><dt>제외 정보</dt><dd>계정 비밀번호 · 외부 서비스 키</dd></div></dl>
      <footer className="settings-section-footer"><p>개인 자료가 포함됩니다. 안전한 장소에 보관하세요.</p><a className="button primary" href="/api/records/export" download><Download size={18} aria-hidden="true" />내 기록 다운로드</a></footer>
    </section>
    <p className="settings-help">기록 이동용 파일입니다. 서비스 전체 복구에는 운영자의 SQLite 백업이 필요합니다.</p>
    <AnimatedDetails className="settings-legacy" summary="이전 위키 기록"><p>기존 위키와 개인 기록을 Markdown과 이력으로 내려받습니다.</p><a className="button" href="/api/wiki/export" download>위키 기록 다운로드</a></AnimatedDetails>
  </main>;
}
export function LegacyTransition() {
  return <main className="page narrow-page"><h1>학습 자료와 레퍼런스로 이어갑니다.</h1><p>범용 위키와 개인 탐구 기능은 Code Trainer의 학습 흐름에서 분리했습니다. 기존 원자료와 기록은 보존되어 있습니다.</p><div className="learning-links"><Link to="/settings/records">이전 기록 내보내기</Link><Link to="/library">학습 자료</Link><Link to="/technical-references">내 레퍼런스</Link></div></main>;
}
