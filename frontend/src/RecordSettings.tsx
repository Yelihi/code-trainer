import { Link } from 'react-router-dom';
export function RecordSettings() {
  return <main className="page narrow-page"><h1>내 기록 보관하기</h1><p>원자료와 버전, 질문과 꼬리질문, 풀이·제출·도움 기록, 복습 초안과 기존 위키·개인 기록을 보존합니다.</p>
    <section className="learning-section"><h2>내 기록 다운로드</h2><p>원래 ID와 연결 정보를 담은 JSON 파일과 이미지가 ZIP으로 저장됩니다. 계정 비밀번호와 외부 서비스 키는 포함하지 않습니다. 개인 자료가 담기므로 안전한 장소에 보관해주세요.</p><a className="button primary" href="/api/records/export" download>내 기록 ZIP 다운로드</a><p className="muted">이 파일은 이동 가능한 기록입니다. 서비스 전체 복구에는 운영자의 SQLite 백업이 필요합니다.</p></section>
    <section className="learning-section"><h2>이전 위키 기록</h2><p>Code Trainer는 기술 학습과 레퍼런스에 집중합니다. 기존 위키와 개인 기록은 삭제하지 않으며 내보낼 수 있습니다.</p><a className="button" href="/api/wiki/export" download>위키 Markdown과 이력 다운로드</a><div className="learning-links"><Link to="/library">학습 자료 열기</Link><Link to="/technical-references">내 레퍼런스 열기</Link></div></section>
  </main>;
}
export function LegacyTransition() {
  return <main className="page narrow-page"><h1>학습 자료와 레퍼런스로 이어갑니다.</h1><p>범용 위키와 개인 탐구 기능은 Code Trainer의 학습 흐름에서 분리했습니다. 기존 원자료와 기록은 보존되어 있습니다.</p><div className="learning-links"><Link to="/settings/records">이전 기록 내보내기</Link><Link to="/library">학습 자료</Link><Link to="/technical-references">내 레퍼런스</Link></div></main>;
}
