# Release 완결 작업 — 2026-10-25

사용자 요청: “Release 배포 해주시고 앞으로 남은 작업도 진행 후 release 배포 진행해주세요. 다 완결된 release 기반으로 테스트 해보겠습니다”
후속 답변: “릴리즈 병합 / 추천 방향으로 / 네 포함해주세요”

확정된 방향:
- release/second-brain-redesign에만 흐름별 PR을 병합한다. main 병합·서버 배포는 하지 않는다.
- 전체 release 완성 후 사용자 테스트. 기능별 구현 피드백 대기는 이 요청으로 대체하지만 검증·리뷰는 유지한다. 확인하지 않은 구현 피드백을 기록하지 않는다.
- 검토 완료한 버전만 추출 가능하다. 일반 자료 복습은 별도 추가로 시작한다. 간격은 1·3·7·14일, 다시 확인 필요는 다음 날이다.
- action은 실제 수행한 설명·풀이·실험의 관찰 기록으로 관리한다.
- 사용자별 AI 키와 Deep Inside 예약 생성도 이번 범위에 포함한다. 예약 생성의 주기·비용·보관 세부 정책은 해당 흐름 설계에서 명시한다.

진행 순서: GitHub 기본 저장소(P16) → 사용자별 AI 설정(P12) → 해석 기반 코드 실습(P7) → 검토 완료·추출·그래프(P8–P10) → 일반 자료 복습(P11) → Deep Inside 생성·채택·예약(P13–P15). 기존 원문·해석·질문지·답변 저장(P1–P6)은 release444fa35에 반영됐다.

## P16: GitHub 기본 저장소 등록

설정 화면에서 기존 저장소 조회를 수행하고 명시적으로 기본 저장소 등록 버튼을 누른다. 현재 GitHub 연결과 저장소 ID/공개 범위/주소가 조회 결과와 일치하는지 서버가 재확인한 뒤 owner별 하나를 저장한다. 외부 GitHub 쓰기는 발생하지 않는다. 계정/토큰 교체와 연결 해제 시 기본 대상을 해제한다. 실패·동시 연결 변경 시 이전 기본값을 덮어쓰지 않는다.

공유 화면은 저장한 주소를 초기값으로 보여준다. 사용자가 먼저 주소를 수정한 경우 늦게 온 기본값으로 덮어쓰지 않는다. 저장한 ID·공개 범위가 달라졌으면 다시 등록하도록 안내한다. 기존 권한 확인과 본문 확인 및 명시적 게시 버튼을 그대로 유지한다. 저장소를 등록했다고 쓰기 권한이 검증됐다고 표시하지 않는다.

변경 경계: backend/github_sharing.py의 기본 대상 저장/읽기와 연결 변경, backend/github_schema.py 입력, backend/api.py 인증 경로, frontend/src/GitHubSharing.tsx 설정/공유 호출자, 관련 테스트. 새 의존성·새 전역 상태·외부 게시 자동화 없음.

검증: owner 격리, 조회만 발생, 저장 응답 유실 재전송, 잘못된 URL/상태, 조회 도중 계정 교체·해제, 저장소 ID/공개 범위 변경, 기존 공유 회귀를 격리 DB/MockTransport로 확인한다. frontend test/typecheck/lint/build 및 실제 임시 브라우저에서 등록→재열기→공유 초기값→수정/실패 흐름과390px 배치를 확인한다. 실제 사용자 토큰/저장소로 이슈를 게시하지 않는다.

## 2026-10-25 구현·병합 기록

아래 PR의 통합 대상은 모두 `release/second-brain-redesign`이다. main 병합과 운영 서버 배포는 별도 최종 확인 이후 진행한다.

| 범위 | PR |
| --- | --- |
| P1 원문 수명 분리·이행 | [#22](https://github.com/Yelihi/code-trainer/pull/22) |
| P2 본문 버전·자료 보관함 | [#23](https://github.com/Yelihi/code-trainer/pull/23) |
| P5 다섯 영역 탐색 | [#24](https://github.com/Yelihi/code-trainer/pull/24) |
| P3 RSA 원문 등록 | [#25](https://github.com/Yelihi/code-trainer/pull/25) |
| P4 독립 해석 문서 | [#26](https://github.com/Yelihi/code-trainer/pull/26) |
| P6 질문지·사용자 답변/요약 | [#27](https://github.com/Yelihi/code-trainer/pull/27), [#28](https://github.com/Yelihi/code-trainer/pull/28) |
| P16 GitHub 기본 저장소 | [#29](https://github.com/Yelihi/code-trainer/pull/29) |
| P12 개인 AI 연결 | [#30](https://github.com/Yelihi/code-trainer/pull/30) |
| P7 해석 기반 코드 실습 | [#31](https://github.com/Yelihi/code-trainer/pull/31) |
| P8 검토 완료 자료 | [#32](https://github.com/Yelihi/code-trainer/pull/32) |
| P9 후보 추출 | [#33](https://github.com/Yelihi/code-trainer/pull/33) |
| P10 그래프 등록·근거·설명 관찰 | [#34](https://github.com/Yelihi/code-trainer/pull/34) |
| P11 일반 자료 복습·주간 일정 | [#35](https://github.com/Yelihi/code-trainer/pull/35) |
| P13 근거 기반 Deep Inside | [#36](https://github.com/Yelihi/code-trainer/pull/36) |
| P14 채택한 탐구·내 기록 | [#37](https://github.com/Yelihi/code-trainer/pull/37) |
| P15 기본 꺼짐 예약 생성·호출 한도 | [#38](https://github.com/Yelihi/code-trainer/pull/38) |

개발 환경, 사용자 테스트 순서, 유지보수 경계와 검증 한계는 [release 테스트 안내](release-testing.md)에 정리했다. 최초 P0의 전체 저장소 분석 상태는 FS 보고서에 별도로 남기며 기능별 구현 완료와 혼동하지 않는다.
