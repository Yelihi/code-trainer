# 유아이볼 참고 UI 적용 · 2026-11-16

대상 브랜치: `feat/technical-learning-redesign`. [참고 화면과 결정](../../ui-reference-directions.md)을 따른다.

## 확인한 화면

| 화면 | 데스크톱 | 모바일 |
| --- | --- | --- |
| 오늘의 학습 | [1440px](today-1440.png) | [390px](today-390.png) |
| 원자료 | [1440px](library-1440.png) | [390px](library-390.png) |
| 원문 상세 | [1440px](source-1440.png) | [390px](source-390.png) |
| 해석 | [1440px](interpretation-1440.png) | [390px](interpretation-390.png) |
| 레퍼런스 목록 | [1440px](references-1440.png) | [390px](references-390.png) |
| 레퍼런스 상세 | [1440px](reference-1440.png) | [390px](reference-390.png) |
| 질문 상세 | [1440px](question-1440.png) | [390px](question-390.png) |
| 직접 작성 | [1440px](note-1440.png) | [390px](note-390.png) |
| 원자료 등록 | [1440px](source-form-1440.png) | [390px](source-form-390.png) |
| 질문 | [1440px](questions-1440.png) | [390px](questions-390.png) |
| 복습 | [1440px](reviews-1440.png) | [390px](reviews-390.png) |
| 자료기반 코드 실습 목록 | [1440px](courses-1440.png) | [390px](courses-390.png) |
| 단원 목록 | [1440px](course-1440.png) | [390px](course-390.png) |
| 개념 읽기 | [1440px](lesson-1440.png) | [390px](lesson-390.png) |
| 문제집 목록 | [1440px](practice-catalog-1440.png) | [390px](practice-catalog-390.png) |
| 수집 출처 관리 | [1440px](feed-settings-1440.png) | [390px](feed-settings-390.png) |
| 실습 진입 | [1440px](practice-1440.png) | [390px](practice-390.png) |
| 자동 수집 | [1440px](inbox-1440.png) | [390px](inbox-390.png) |

스크린샷의 자료는 모두 예시이다. 실제 계정이나 원문을 사용하지 않았다. 긴 전체 페이지 캡처에서 모바일 하단 메뉴는 촬영 당시 화면 높이에 고정되어 보이며, 실사용에서는 현재 화면 아래에 고정된다.

## 검증

- 프론트엔드 빌드·린트·테스트 33개, 백엔드 study 테스트 6개 통과.
- 1440 / 1024 / 768 / 390px × 17개 페이지: 가로 넘침 없음.
- 오늘의 학습: 이어하기가 240px 미만이고, 복습 제목이 첫 화면에 표시됨.
- 질문 숨기기 요청과 갱신, 복습 시작 이동 확인.
- 과거 원문 선택·당시 URL 표시·최신 본문 복귀, 해석 당시 버전 조회 확인.
- 원문 읽기 실패·재시도와 섹션 이동 확인.
- 학습·자료·레퍼런스·질문·실습의 빈 상태 확인.
- 오늘의 학습 오류를 빈 계정으로 표시하지 않으며 재시도로 회복함.
- 브라우저 예외·누락된 API fixture 없음. 화면 열람으로 AI 생성 요청이 발생하지 않음.

[기계 판독 결과](checks.json) · [API 응답을 격리한 브라우저 검사](check.mjs).

재현: 해당 브랜치의 `frontend`에서 `npm run dev` 실행 후 Playwright가 설치된 Node 환경에서 `node docs/technical-learning-evidence/2026-11-16-uibowl/check.mjs`를 실행한다. 별도 설치 위치를 사용하는 경우 `PLAYWRIGHT_MODULE`에 Playwright 모듈의 절대 경로를 지정한다. 브라우저 검사를 위해 제품 의존성을 추가하지 않았다.

실제 AI 생성·실행 VM·서버 저장·운영 계정·운영 배포는 이번 UI 검증 범위에 포함하지 않았다. 기존 대형 JS 번들 경고와 병렬 SSR 테스트의 HMR 포트 경고는 남아 있으나 빌드·린트·테스트는 성공했다.


추가 검증: 질문 상세 읽기/수정/저장/취소, 저장 중 버튼 중앙 스피너, 입력 1px 포커스와 상위 패널 shadow 없음, 제거한 경로의 실습 리다이렉트, 오늘의 학습/AI 후보에서 기존 수동 문제·질문지 진입 제외 및 저장 이력 보존, 출처 입력 동일 폭/높이를 확인했다. [포커스](focus-1440.png), [출처 입력](metadata-1440.png). 본문 목록의 간격은 토스·Linear 공식 문서도 참고했으며 Mobbin은 유료 플랜 응답으로 화면을 확보하지 못했다.

후속 검사: 관리자 권한 fixture로 수집 출처를 펼쳐 헤더/화살표 border 0px, URL 독립 행, 모바일 가로 넘침 없음을 확인한다. 실습 카드의 데스크톱 2열/모바일 1열과 문제집 목록 이동을 검사한다.
