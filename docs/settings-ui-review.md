# 설정 메뉴와 연결 화면 점검 · 2026-11-16

브랜치: `feat/technical-learning-redesign`. 현재 산세리프, 회색 바탕·흰 표면, 보라·분홍 강조, 공통 호버/포커스를 유지한다. 새 설정 항목이나 통계는 만들지 않는다.

## 참고

- [토스 ListRow](https://tossmini-docs.toss.im/tds-mobile/components/ListRow/list-row-overview/): 항목 설명과 오른쪽 상태/동작 구분. 연결 정보와 운영 상태를 레이블·값 행으로 정리했다.
- [Linear Preferences](https://linear.app/docs/account-preferences): 목적에 따른 설정 그룹. GitHub의 계정·저장소와 권한 안내를 구분했다.
- [Linear Display options](https://linear.app/docs/display-options): 메뉴 바깥 클릭으로 메뉴를 벗어나는 동작 참고. 네이티브 details를 유지하며 바깥 pointerdown, Esc와 초점 복귀, 링크 선택 시 닫힘을 추가했다.

공식 문서의 구성과 동작을 참고했으며 화면 픽셀 복제는 아니다. 기존 Mobbin 유료 플랜 제한 때문에 추가 Mobbin 조회를 실행하지 않았다.

## 확인 및 수정

| 목적지 | 확인한 문제와 처리 |
| --- | --- |
| 질문 모아보기 | 기존 행 목록·검색·필터 구성 유지. 설정 메뉴에서 이동 시 닫힘 확인 |
| 학습 기록 | 서로 다른 표면과 평문 사용량을 흰 섹션과 항목별 값으로 정리. 빈 기록은 문제집 선택 동작 제공 |
| AI 연결과 사용량 | 과도한 여백 축소. 연결 상태/현재 값/변경 입력 구분, 모델·키 필드 정렬. 실제 인증 여부와 키 보관 안내 유지 |
| GitHub 연동 | 기능명 제목, 계정/저장소 입력 구분. 권한 안내는 펼쳐서 확인. 삭제된 개념 지도 안내와 이전 노트 목록 링크 수정 |
| 기록 내보내기 | 포함 기록/파일 형식/제외 정보 행, 다운로드 동작과 보관 안내. 이전 위키 다운로드는 펼침 안에 보존 |
| 운영 상태 | 큰 테두리 박스를 레이블/값 행으로 변경. 정상/실패/오래됨 구분, 수집 정보가 없으면 빈 상태 |
| 원본 자료 관리 | 기능명 제목, 자료 수, 흰 행 목록과 이동 표시. 긴 제목/주소, 빈 목록, 원문 상세 확인 |

각 페이지의 저장·연결 해제·관리자 권한·다운로드 API는 유지한다. 검증 중 외부 연결, 키 저장/삭제, 내보내기를 실행하지 않았다.

## 화면과 재현

이미지의 계정·연결·운영 정보는 격리한 API fixture다. 실제 비밀번호나 토큰을 사용하지 않는다.

| 화면 | 이전 | 수정 후 | 모바일 |
| --- | --- | --- | --- |
| AI | [이전](technical-learning-evidence/2026-11-16-uibowl/settings-before-ai-1440.png) | [수정](technical-learning-evidence/2026-11-16-uibowl/settings-ai-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/settings-ai-390.png) |
| GitHub | [이전](technical-learning-evidence/2026-11-16-uibowl/settings-before-github-1440.png) | [수정](technical-learning-evidence/2026-11-16-uibowl/settings-github-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/settings-github-390.png) |
| 기록 내보내기 | [이전](technical-learning-evidence/2026-11-16-uibowl/settings-before-export-1440.png) | [수정](technical-learning-evidence/2026-11-16-uibowl/settings-export-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/settings-export-390.png) |
| 학습 기록 | [이전](technical-learning-evidence/2026-11-16-uibowl/settings-before-history-1440.png) | [수정](technical-learning-evidence/2026-11-16-uibowl/settings-history-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/settings-history-390.png) |
| 운영 상태 | [이전](technical-learning-evidence/2026-11-16-uibowl/settings-before-operations-1440.png) | [수정](technical-learning-evidence/2026-11-16-uibowl/settings-operations-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/settings-operations-390.png) |
| 원본 자료 | [이전](technical-learning-evidence/2026-11-16-uibowl/settings-before-sources-1440.png) | [수정](technical-learning-evidence/2026-11-16-uibowl/settings-sources-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/settings-sources-390.png) |

[검사 코드](technical-learning-evidence/2026-11-16-uibowl/settings-check.mjs) · [기계 판독 결과](technical-learning-evidence/2026-11-16-uibowl/settings-checks.json)

Vite 5173 실행 후 Playwright 설치 환경에서 `node docs/technical-learning-evidence/2026-11-16-uibowl/settings-check.mjs`. 별도 위치는 `PLAYWRIGHT_MODULE` 지정. 8화면 × 4너비(1440/1024/768/390), 메뉴 4가지 동작, 오류 재시도·빈 상태·연결 해제 상태·오래된 운영 상태를 확인한다. 검증 스크립트는 GET 외에 방문 기록 fixture만 허용한다.
